"""Async REST client for the GitHub API."""

from __future__ import annotations

from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.config import get_settings
from app.core.logging import get_logger
from app.integrations.github.schemas import (
    GitHubCreatePullRequestRequest,
    GitHubGitCommitDetail,
    GitHubGitCommitResponse,
    GitHubGitRefResponse,
    GitHubIssueCommentRequest,
    GitHubIssueCommentResponse,
    GitHubIssueReference,
    GitHubPullRequestResponse,
    GitHubRequestedReviewersResponse,
    GitHubRequestReviewersRequest,
    GitHubSearchIssuesResponse,
)

logger = get_logger(__name__)


class GitHubError(RuntimeError):
    """Raised when GitHub API calls fail."""


TModel = TypeVar("TModel", bound=BaseModel)


class GitHubClient:
    def __init__(
        self,
        token: str | None = None,
        api_url: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        settings = get_settings()
        self._token = token or settings.github_api_token
        self._api_url = (api_url or settings.github_api_url).rstrip("/")

        if not self._token:
            raise GitHubError("GITHUB_API_TOKEN is not set")

        self._client = httpx.AsyncClient(
            base_url=self._api_url,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

    async def __aenter__(self) -> GitHubClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def find_issue_by_branch_or_title(
        self,
        repo: str,
        linear_issue_id: str,
        linear_title: str | None = None,
        linear_branch_name: str | None = None,
    ) -> GitHubIssueReference | None:
        """Search a repository issue linked to a Linear issue identifier."""
        search_terms = _ordered_terms(
            linear_issue_id,
            linear_title,
            linear_branch_name,
        )

        issue = await self._lookup_first_issue(repo, search_terms, open_only=True)
        if issue:
            return issue

        issue = await self._lookup_first_issue(repo, search_terms, open_only=False)
        if issue:
            return issue

        logger.warning(
            "github.issue_not_found",
            repo=repo,
            linear_issue_id=linear_issue_id,
            linear_title=linear_title,
            linear_branch_name=linear_branch_name,
        )
        return None

    async def _lookup_first_issue(
        self,
        repo: str,
        terms: list[str],
        *,
        open_only: bool,
    ) -> GitHubIssueReference | None:
        state_filter = " is:open" if open_only else ""

        for term in terms:
            query = f'repo:{repo} is:issue{state_filter} in:title,body "{term}"'
            result = await self._search_issues(query)
            if result:
                return result

        return None

    async def create_issue_comment(
        self,
        repo: str,
        issue_number: int,
        body: str,
    ) -> GitHubIssueCommentResponse:
        repo_path = _repo_path(repo)
        payload = GitHubIssueCommentRequest(body=body)
        return await self._request(
            "POST",
            f"/repos/{repo_path}/issues/{issue_number}/comments",
            response_model=GitHubIssueCommentResponse,
            json=payload.model_dump(),
        )

    async def create_pull_request(
        self,
        repo: str,
        title: str,
        head_branch: str,
        base_branch: str = "main",
        body: str = "",
    ) -> GitHubPullRequestResponse:
        repo_path = _repo_path(repo)
        payload = GitHubCreatePullRequestRequest(
            title=title,
            head=head_branch,
            base=base_branch,
            body=body,
        )
        return await self._request(
            "POST",
            f"/repos/{repo_path}/pulls",
            response_model=GitHubPullRequestResponse,
            json=payload.model_dump(),
        )

    async def request_reviewer(
        self,
        repo: str,
        pr_number: int,
        reviewers: list[str],
    ) -> GitHubRequestedReviewersResponse:
        repo_path = _repo_path(repo)
        payload = GitHubRequestReviewersRequest(reviewers=reviewers)
        return await self._request(
            "POST",
            f"/repos/{repo_path}/pulls/{pr_number}/requested_reviewers",
            response_model=GitHubRequestedReviewersResponse,
            json=payload.model_dump(),
        )

    async def create_branch(
        self,
        repo: str,
        branch_name: str,
        from_branch: str = "main",
        commit_message: str | None = None,
    ) -> GitHubGitRefResponse:
        """Create a new branch from an existing branch's HEAD.

        An empty commit is added so the branch differs from the source,
        which is required for opening a pull request.
        """
        repo_path = _repo_path(repo)
        # Get the SHA of the source branch
        source_ref = await self._request(
            "GET",
            f"/repos/{repo_path}/git/ref/heads/{from_branch}",
            response_model=GitHubGitRefResponse,
        )
        base_sha = source_ref.object.sha

        # Create an empty commit (same tree, new commit) so a PR can be opened
        msg = commit_message or f"chore: initialize branch {branch_name}"
        # Get the tree SHA of the base commit
        base_commit = await self._request(
            "GET",
            f"/repos/{repo_path}/git/commits/{base_sha}",
            response_model=GitHubGitCommitDetail,
        )
        tree_sha = base_commit.tree.sha

        empty_commit = await self._request(
            "POST",
            f"/repos/{repo_path}/git/commits",
            response_model=GitHubGitCommitResponse,
            json={
                "message": msg,
                "tree": tree_sha,
                "parents": [base_sha],
            },
        )

        # Create the new branch pointing at the empty commit
        return await self._request(
            "POST",
            f"/repos/{repo_path}/git/refs",
            response_model=GitHubGitRefResponse,
            json={
                "ref": f"refs/heads/{branch_name}",
                "sha": empty_commit.sha,
            },
        )

    async def list_webhooks(self, repo: str) -> list[dict[str, Any]]:
        """List all webhooks configured on a repository."""
        repo_path = _repo_path(repo)
        try:
            response = await self._client.get(f"/repos/{repo_path}/hooks")
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise GitHubError(
                f"GitHub API request failed: {e.response.status_code} GET hooks"
            ) from e
        data = response.json()
        return list(data) if isinstance(data, list) else []

    async def create_webhook(
        self,
        repo: str,
        url: str,
        secret: str,
        events: list[str],
    ) -> dict[str, Any]:
        """Create a new webhook on a repository."""
        repo_path = _repo_path(repo)
        payload = {
            "name": "web",
            "active": True,
            "events": events,
            "config": {
                "url": url,
                "content_type": "json",
                "secret": secret,
                "insecure_ssl": "0",
            },
        }
        try:
            response = await self._client.post(
                f"/repos/{repo_path}/hooks", json=payload
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise GitHubError(
                f"GitHub API request failed: {e.response.status_code} POST hooks"
            ) from e
        return dict(response.json())

    async def _search_issues(self, query: str) -> GitHubIssueReference | None:
        payload = await self._request(
            "GET",
            "/search/issues",
            response_model=GitHubSearchIssuesResponse,
            params={"q": query, "per_page": 10, "sort": "updated", "order": "desc"},
        )

        for item in payload.items:
            if item.pull_request is None:
                return GitHubIssueReference(number=item.number)

        return None

    async def _request(
        self,
        method: str,
        url: str,
        *,
        response_model: type[TModel],
        **kwargs: Any,
    ) -> TModel:
        try:
            response = await self._client.request(method, url, **kwargs)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            body = e.response.text
            logger.error(
                "github.http_error",
                method=method,
                url=url,
                status_code=status_code,
                response_text=body,
            )
            raise GitHubError(
                f"GitHub API request failed: {status_code} {method} {url}"
            ) from e
        except httpx.HTTPError as e:
            logger.error("github.request_error", method=method, url=url, error=str(e))
            raise GitHubError(f"GitHub API transport error: {method} {url}") from e

        data = response.json()
        if not isinstance(data, dict):
            raise GitHubError("GitHub API returned a non-object response")
        try:
            return response_model.model_validate(data)
        except ValidationError as e:
            raise GitHubError("GitHub API returned an invalid response shape") from e


def _repo_path(repo: str) -> str:
    value = repo.strip().strip("/")
    if not value or "/" not in value:
        raise GitHubError(
            "GitHub repository must be provided as 'owner/repo' (for example: octocat/hello-world)"
        )
    return value


def _ordered_terms(
    linear_issue_id: str,
    linear_title: str | None,
    linear_branch_name: str | None,
) -> list[str]:
    terms = [
        linear_issue_id,
        linear_issue_id.lower(),
        linear_title or "",
        linear_branch_name or "",
    ]
    ordered: list[str] = []
    for term in terms:
        normalized = term.strip()
        if normalized and normalized not in ordered:
            ordered.append(normalized)
    return ordered
