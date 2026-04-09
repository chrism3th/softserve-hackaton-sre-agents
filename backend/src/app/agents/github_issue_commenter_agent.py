"""Agent that mirrors Linear state changes into GitHub issue comments."""

from __future__ import annotations

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

        async with GitHubClient() as client:
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
            body = (
                f"🤖 **Linear Status Update**: This issue transitioned from "
                f"`{context.from_state}` to `{context.to_state}`."
            )
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
        }
        try:
            return _CommentContext.model_validate(payload)
        except ValidationError:
            logger.warning("github_issue_commenter.invalid_context", context=payload)
            return None
