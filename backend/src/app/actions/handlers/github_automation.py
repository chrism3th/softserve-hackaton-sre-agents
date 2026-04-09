"""Actions that trigger GitHub automations from Linear state changes."""

from __future__ import annotations

import re

from app.actions.base import BaseAction
from app.actions.registry import action_registry
from app.agents.base import AgentRequest
from app.agents.registry import get_agent
from app.config import get_settings
from app.core.logging import get_logger
from app.domain.events import DomainEvent, EventType, IssueStatusChangedEvent

logger = get_logger(__name__)


def _build_context(event: IssueStatusChangedEvent) -> dict[str, str]:
    return {
        "linear_issue_id": event.issue_identifier,
        "linear_title": event.issue_title,
        "linear_branch_name": _branch_from_title(event.issue_title),
        "from_state": event.previous_state.name,
        "to_state": event.current_state.name,
    }


def _branch_from_title(issue_title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", issue_title.lower()).strip("-")
    if not slug:
        slug = "issue"
    return f"fix/{slug}"


@action_registry.on(EventType.issue_status_changed)
class GitHubIssueCommentAutomationAction(BaseAction):
    """Post a GitHub issue comment on every Linear state transition."""

    async def execute(self, event: DomainEvent) -> None:
        if not isinstance(event, IssueStatusChangedEvent):
            return

        settings = get_settings()
        if not settings.github_repo:
            logger.warning(
                "github_automation.repo_not_configured",
                action="comment",
                issue=event.issue_identifier,
            )
            return

        agent = get_agent("github_issue_commenter")
        request = AgentRequest(
            input=event.issue_title,
            context={"repo": settings.github_repo, **_build_context(event)},
        )
        await agent.run(request)


@action_registry.on(EventType.issue_status_changed)
class QAHandoffAutomationAction(BaseAction):
    """Create a PR and request Copilot review when state reaches QA."""

    async def execute(self, event: DomainEvent) -> None:
        if not isinstance(event, IssueStatusChangedEvent):
            return

        settings = get_settings()
        if not settings.github_repo:
            logger.warning(
                "github_automation.repo_not_configured",
                action="qa_handoff",
                issue=event.issue_identifier,
            )
            return

        agent = get_agent("qa_handoff")
        request = AgentRequest(
            input=event.issue_title,
            context={"repo": settings.github_repo, **_build_context(event)},
        )
        await agent.run(request)
