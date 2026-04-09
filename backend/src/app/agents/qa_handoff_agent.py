"""Agent that creates QA pull requests and requests Copilot review."""

from __future__ import annotations

from pydantic import BaseModel, ValidationError

from app.agents.base import Agent, AgentRequest, AgentResponse
from app.config import get_settings
from app.core.logging import get_logger
from app.integrations.github.client import GitHubClient

logger = get_logger(__name__)

_COPILOT_REVIEWER = "copilot-pull-request-reviewer[bot]"


class _QAHandoffContext(BaseModel):
    repo: str
    linear_issue_id: str
    linear_title: str
    linear_branch_name: str
    to_state: str


class QAHandoffAgent(Agent):
    """When a Linear issue reaches QA, open a PR and request Copilot review."""

    name = "qa_handoff"

    async def run(self, request: AgentRequest) -> AgentResponse:
        context = self._parse_context(request)
        if context is None:
            return AgentResponse(
                output="Skipped QA handoff due to missing context",
                agent=self.name,
                iterations=1,
            )

        if context.to_state != "QA":
            return AgentResponse(
                output=f"No-op for state {context.to_state}",
                agent=self.name,
                iterations=1,
            )

        title = f"[{context.linear_issue_id}] {context.linear_title}"
        body = "Auto-created from Linear QA state transition."

        async with GitHubClient() as client:
            pr = await client.create_pull_request(
                repo=context.repo,
                title=title,
                head_branch=context.linear_branch_name,
                base_branch="main",
                body=body,
            )
            pr_number = pr.number
            await client.request_reviewer(
                repo=context.repo,
                pr_number=pr_number,
                reviewers=[_COPILOT_REVIEWER],
            )

        logger.info(
            "qa_handoff.pr_created",
            repo=context.repo,
            pr_number=pr_number,
            branch=context.linear_branch_name,
            reviewer=_COPILOT_REVIEWER,
        )
        return AgentResponse(
            output=f"Created PR #{pr_number} and requested Copilot review",
            agent=self.name,
            iterations=1,
            metadata={"pr_number": pr_number, "repo": context.repo},
        )

    def _parse_context(self, request: AgentRequest) -> _QAHandoffContext | None:
        settings = get_settings()
        payload = {
            "repo": request.context.get("repo") or settings.github_repo,
            "linear_issue_id": request.context.get("linear_issue_id"),
            "linear_title": request.context.get("linear_title"),
            "linear_branch_name": request.context.get("linear_branch_name"),
            "to_state": request.context.get("to_state"),
        }
        try:
            return _QAHandoffContext.model_validate(payload)
        except ValidationError:
            logger.warning("qa_handoff.invalid_context", context=payload)
            return None
