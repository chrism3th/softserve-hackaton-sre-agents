"""Tests for GitHub REST client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.config import get_settings
from app.integrations.github.client import GitHubClient, GitHubError
from app.integrations.github.schemas import (
    GitHubIssueCommentResponse,
    GitHubIssueReference,
    GitHubPullRequestResponse,
    GitHubRequestedReviewersResponse,
)


@pytest.fixture()
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestGitHubClient:
    async def test_find_issue_by_branch_or_title_returns_first_issue(self) -> None:
        async with GitHubClient(token="token", api_url="https://api.github.test") as client:
            with patch.object(
                client,
                "_search_issues",
                new_callable=AsyncMock,
                side_effect=[GitHubIssueReference(number=42), None],
            ) as search:
                issue = await client.find_issue_by_branch_or_title("acme/repo", "TEA-42")

        assert issue is not None
        assert issue.number == 42
        assert search.await_count >= 1

    async def test_find_issue_by_branch_or_title_returns_none(self) -> None:
        async with GitHubClient(token="token", api_url="https://api.github.test") as client:
            with patch.object(
                client,
                "_search_issues",
                new_callable=AsyncMock,
                return_value=None,
            ):
                issue = await client.find_issue_by_branch_or_title("acme/repo", "TEA-42")

        assert issue is None

    async def test_find_issue_by_branch_or_title_falls_back_to_title(self) -> None:
        async with GitHubClient(token="token", api_url="https://api.github.test") as client:
            with patch.object(
                client,
                "_search_issues",
                new_callable=AsyncMock,
                side_effect=[
                    None,
                    None,
                    GitHubIssueReference(number=88),
                ],
            ) as search:
                issue = await client.find_issue_by_branch_or_title(
                    "acme/repo",
                    "TEA-42",
                    linear_title="Investigate outage",
                    linear_branch_name="tea-42",
                )

        assert issue is not None
        assert issue.number == 88
        # First two attempts are issue-id and lowercased issue-id.
        # Third attempt hits title fallback.
        assert search.await_count == 3

    async def test_create_issue_comment_calls_expected_endpoint(self) -> None:
        async with GitHubClient(token="token", api_url="https://api.github.test") as client:
            with patch.object(
                client,
                "_request",
                new_callable=AsyncMock,
                return_value=GitHubIssueCommentResponse(id=1),
            ) as request:
                result = await client.create_issue_comment("acme/repo", 12, "hello")

        assert result.id == 1
        request.assert_awaited_once_with(
            "POST",
            "/repos/acme/repo/issues/12/comments",
            response_model=GitHubIssueCommentResponse,
            json={"body": "hello"},
        )

    async def test_create_pull_request_calls_expected_endpoint(self) -> None:
        async with GitHubClient(token="token", api_url="https://api.github.test") as client:
            with patch.object(
                client,
                "_request",
                new_callable=AsyncMock,
                return_value=GitHubPullRequestResponse(number=55),
            ) as request:
                result = await client.create_pull_request(
                    repo="acme/repo",
                    title="[TEA-42] Title",
                    head_branch="tea-42",
                    base_branch="main",
                    body="body",
                )

        assert result.number == 55
        request.assert_awaited_once_with(
            "POST",
            "/repos/acme/repo/pulls",
            response_model=GitHubPullRequestResponse,
            json={
                "title": "[TEA-42] Title",
                "head": "tea-42",
                "base": "main",
                "body": "body",
            },
        )

    async def test_request_reviewer_calls_expected_endpoint(self) -> None:
        async with GitHubClient(token="token", api_url="https://api.github.test") as client:
            with patch.object(
                client,
                "_request",
                new_callable=AsyncMock,
                return_value=GitHubRequestedReviewersResponse(id=999),
            ) as request:
                result = await client.request_reviewer(
                    repo="acme/repo",
                    pr_number=55,
                    reviewers=["copilot-pull-request-reviewer[bot]"],
                )

        assert result.id == 999
        request.assert_awaited_once_with(
            "POST",
            "/repos/acme/repo/pulls/55/requested_reviewers",
            response_model=GitHubRequestedReviewersResponse,
            json={"reviewers": ["copilot-pull-request-reviewer[bot]"]},
        )

    async def test_request_raises_domain_error_on_http_failure(self) -> None:
        async with GitHubClient(token="token", api_url="https://api.github.test") as client:
            with patch.object(
                client._client,
                "request",
                new_callable=AsyncMock,
            ) as request:
                req = httpx.Request("GET", "https://api.github.test/search/issues")
                res = httpx.Response(500, request=req, text="boom")
                response = MagicMock()
                response.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "github failure",
                    request=req,
                    response=res,
                )
                request.return_value = response

                with pytest.raises(GitHubError):
                    await client._request(
                        "GET",
                        "/search/issues",
                        response_model=GitHubIssueReference,
                    )


class TestGitHubClientInit:
    def test_init_requires_token(
        self,
        monkeypatch: pytest.MonkeyPatch,
        clear_settings_cache: None,
    ) -> None:
        monkeypatch.setenv("GITHUB_API_TOKEN", "")
        with pytest.raises(GitHubError, match="GITHUB_API_TOKEN"):
            GitHubClient()
