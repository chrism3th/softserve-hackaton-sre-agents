"""Agent that creates a GitHub branch when a Linear issue moves to In Progress."""

from __future__ import annotations

from pydantic import BaseModel, ValidationError

from app.agents.base import Agent, AgentRequest, AgentResponse
from app.config import get_settings
from app.core.logging import get_logger
from app.integrations.github.client import GitHubClient, GitHubError

logger = get_logger(__name__)


class _BranchCreatorContext(BaseModel):
    repo: str
    linear_issue_id: str
    linear_branch_name: str
    to_state: str


class BranchCreatorAgent(Agent):
    """Create a feature branch from main when a Linear issue enters In Progress."""

    name = "branch_creator"

    async def run(self, request: AgentRequest) -> AgentResponse:
        context = self._parse_context(request)
        if context is None:
            return AgentResponse(
                output="Skipped branch creation due to missing context",
                agent=self.name,
                iterations=1,
            )

        if context.to_state != "In Progress":
            return AgentResponse(
                output=f"No-op for state {context.to_state}",
                agent=self.name,
                iterations=1,
            )

        settings = get_settings()

        async with GitHubClient() as client:
            try:
                ref = await client.create_branch(
                    repo=context.repo,
                    branch_name=context.linear_branch_name,
                    from_branch=settings.github_base_branch,
                )
            except GitHubError:
                logger.info(
                    "branch_creator.branch_already_exists",
                    repo=context.repo,
                    branch=context.linear_branch_name,
                )
                return AgentResponse(
                    output=f"Branch {context.linear_branch_name} already exists",
                    agent=self.name,
                    iterations=1,
                )

        logger.info(
            "branch_creator.created",
            repo=context.repo,
            branch=context.linear_branch_name,
            sha=ref.object.sha,
        )
        return AgentResponse(
            output=f"Created branch {context.linear_branch_name}",
            agent=self.name,
            iterations=1,
            metadata={
                "branch": context.linear_branch_name,
                "repo": context.repo,
            },
        )

    def _parse_context(self, request: AgentRequest) -> _BranchCreatorContext | None:
        settings = get_settings()
        payload = {
            "repo": request.context.get("repo") or settings.github_repo,
            "linear_issue_id": request.context.get("linear_issue_id"),
            "linear_branch_name": request.context.get("linear_branch_name"),
            "to_state": request.context.get("to_state"),
        }
        try:
            return _BranchCreatorContext.model_validate(payload)
        except ValidationError:
            logger.warning("branch_creator.invalid_context", context=payload)
            return None
