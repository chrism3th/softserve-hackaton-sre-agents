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
from app.tickets.linear_client import LinearClient

logger = get_logger(__name__)


def _extract_github_issue_url(description: str | None) -> str | None:
    """Extract a GitHub issue URL from a Linear ticket description.

    Looks for the pattern ``**GitHub Issue:** <url>`` that the ticket
    orchestrator inserts when the source is a GitHub issue.  Handles both
    bare URLs and markdown-link forms that Linear may auto-convert:
    ``[url](url)`` or ``[url](<url>)``.
    """
    if not description:
        return None
    match = re.search(
        r"\*\*GitHub Issue:\*\*\s*"
        r"(?:\[.*?\]\(<?(https://github\.com/[^\s>)]+/issues/\d+)>?\)"  # [text](<url>) or [text](url)
        r"|(https://github\.com/[^\s)]+/issues/\d+))",                   # bare url
        description,
    )
    if not match:
        return None
    return match.group(1) or match.group(2)


async def _build_context(event: IssueStatusChangedEvent) -> dict[str, str | None]:
    # Try the description from the webhook payload first.
    github_url = _extract_github_issue_url(event.issue_description)

    # Linear webhooks often omit description on updates — fetch via API.
    if github_url is None:
        try:
            async with LinearClient() as linear:
                description = await linear.get_issue_description(event.issue_id)
                github_url = _extract_github_issue_url(description)
                if github_url:
                    logger.info(
                        "github_automation.url_from_api",
                        issue=event.issue_identifier,
                        github_url=github_url,
                    )
        except Exception:
            logger.warning(
                "github_automation.description_fetch_failed",
                issue=event.issue_identifier,
            )

    return {
        "linear_issue_id": event.issue_identifier,
        "linear_title": event.issue_title,
        "linear_branch_name": _branch_from_identifier(event.issue_identifier),
        "from_state": event.previous_state.name,
        "to_state": event.current_state.name,
        "github_issue_url": github_url,
    }


def _branch_from_identifier(identifier: str) -> str:
    """Derive a branch name from the Linear issue identifier, e.g. TEA-19 → fix/tea-19."""
    return f"fix/{identifier.lower()}"


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

        context = await _build_context(event)
        agent = get_agent("github_issue_commenter")
        request = AgentRequest(
            input=event.issue_title,
            context={"repo": settings.github_repo, **context},
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

        context = await _build_context(event)
        agent = get_agent("qa_handoff")
        request = AgentRequest(
            input=event.issue_title,
            context={"repo": settings.github_repo, **context},
        )
        await agent.run(request)
