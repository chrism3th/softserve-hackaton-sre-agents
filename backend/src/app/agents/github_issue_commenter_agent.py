"""Agent that mirrors Linear state changes into GitHub issue comments."""

from __future__ import annotations

import re

from pydantic import BaseModel, ValidationError

from app.agents.base import Agent, AgentRequest, AgentResponse
from app.config import get_settings
from app.core.logging import get_logger
from app.integrations.github.client import GitHubClient

logger = get_logger(__name__)


class _CommentContext(BaseModel):
    repo: str
    linear_issue_id: str
    linear_title: str | None = None
    linear_branch_name: str | None = None
    from_state: str
    to_state: str
    github_issue_url: str | None = None


class GitHubIssueCommenterAgent(Agent):
    """Post a GitHub issue comment for every Linear state transition."""

    name = "github_issue_commenter"

    async def run(self, request: AgentRequest) -> AgentResponse:
        context = self._parse_context(request)
        if context is None:
            return AgentResponse(
                output="Skipped GitHub comment due to missing context",
                agent=self.name,
                iterations=1,
            )

        if self._should_skip(context.to_state):
            return AgentResponse(
                output="Skipped comment for QA state (handled by QAHandoffAgent)",
                agent=self.name,
                iterations=1,
            )

        issue_number = self._parse_issue_number(context.github_issue_url)

        async with GitHubClient() as client:
            if issue_number is None:
                # Fallback: heuristic search by Linear ID / title / branch.
                issue = await client.find_issue_by_branch_or_title(
                    context.repo,
                    context.linear_issue_id,
                    linear_title=context.linear_title,
                    linear_branch_name=context.linear_branch_name,
                )
                if issue is None:
                    logger.warning(
                        "github_issue_commenter.issue_not_found",
                        repo=context.repo,
                        linear_issue_id=context.linear_issue_id,
                    )
                    return AgentResponse(
                        output="No linked GitHub issue found; skipped comment",
                        agent=self.name,
                        iterations=1,
                    )
                issue_number = issue.number

            body = _build_comment(context.from_state, context.to_state)
            await client.create_issue_comment(context.repo, issue_number, body)

        return AgentResponse(
            output=f"Comment posted to issue #{issue_number}",
            agent=self.name,
            iterations=1,
            metadata={"issue_number": issue_number, "repo": context.repo},
        )

    def _parse_context(self, request: AgentRequest) -> _CommentContext | None:
        settings = get_settings()
        payload = {
            "repo": request.context.get("repo") or settings.github_repo,
            "linear_issue_id": request.context.get("linear_issue_id"),
            "linear_title": request.context.get("linear_title"),
            "linear_branch_name": request.context.get("linear_branch_name"),
            "from_state": request.context.get("from_state"),
            "to_state": request.context.get("to_state"),
            "github_issue_url": request.context.get("github_issue_url"),
        }
        try:
            return _CommentContext.model_validate(payload)
        except ValidationError:
            logger.warning("github_issue_commenter.invalid_context", context=payload)
            return None

    @staticmethod
    def _should_skip(to_state: str) -> bool:
        """Skip posting a comment for QA — that flow is handled by QAHandoffAgent."""
        return to_state.strip().lower() == "qa"

    @staticmethod
    def _parse_issue_number(url: str | None) -> int | None:
        """Extract the issue number from a GitHub issue URL."""
        if not url:
            return None
        match = re.search(r"/issues/(\d+)", url)
        return int(match.group(1)) if match else None


_STATE_MESSAGES: dict[str, str] = {
    "backlog": "your ticket has been moved to **Backlog**! We'll get to it soon.",
    "todo": "your ticket is now in **Todo** and queued for work.",
    "in progress": "someone picked this up! Your ticket is now **In Progress**.",
    "in review": "your ticket is now **In Review** — almost there!",
    "done": "your ticket has been marked as **Done**. Thanks for reporting!",
    "cancelled": "your ticket was **Cancelled**. If you think this is wrong, please reopen.",
    "triage": "your ticket is being **triaged** by the team.",
}


def _build_comment(from_state: str, to_state: str) -> str:
    to_lower = to_state.strip().lower()
    message = _STATE_MESSAGES.get(
        to_lower,
        f"your ticket moved from `{from_state}` to `{to_state}`.",
    )
    return f"beep boop, I am a bot :robot:\n\n{message}"
