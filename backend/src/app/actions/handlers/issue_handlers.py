"""General-purpose action handlers for issue events.

Notification logic (email, etc.) lives in notify_reporter.py.
"""

from __future__ import annotations

from app.actions.base import BaseAction
from app.actions.registry import action_registry
from app.core.logging import get_logger
from app.domain.events import DomainEvent, EventType, IssueStatusChangedEvent

logger = get_logger(__name__)


@action_registry.on(EventType.issue_status_changed)
class LogStatusChangeAction(BaseAction):
    """Log every state transition for observability."""

    async def execute(self, event: DomainEvent) -> None:
        if not isinstance(event, IssueStatusChangedEvent):
            return
        logger.info(
            "action.issue_status_changed",
            issue=event.issue_identifier,
            from_state=event.previous_state.name,
            to_state=event.current_state.name,
            team=event.team_key,
        )


@action_registry.on(EventType.issue_created)
class LogIssueCreatedAction(BaseAction):
    """Log when a new issue is created."""

    async def execute(self, event: DomainEvent) -> None:
        logger.info(
            "action.issue_created",
            issue=event.issue_identifier,
            title=event.issue_title,
        )
