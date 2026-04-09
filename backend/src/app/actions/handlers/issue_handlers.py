"""Placeholder action handlers for issue events.

Each class is a no-op today but is wired into the registry so the
dispatch path is exercised end-to-end.  Replace the body of ``execute``
to add real behaviour — no other file needs to change.
"""

from __future__ import annotations

from app.actions.base import BaseAction
from app.actions.registry import action_registry
from app.core.logging import get_logger
from app.domain.events import DomainEvent, EventType, IssueStatusChangedEvent

logger = get_logger(__name__)


@action_registry.on(EventType.issue_status_changed)
class LogStatusChangeAction(BaseAction):
    """Log every state transition — placeholder for real integrations."""

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


@action_registry.on(EventType.issue_status_changed)
class NotifyOnQAAction(BaseAction):
    """Placeholder: trigger QA workflow when an issue enters QA state."""

    async def execute(self, event: DomainEvent) -> None:
        if not isinstance(event, IssueStatusChangedEvent):
            return
        if event.current_state.name.lower() not in {"qa", "in qa", "ready for qa"}:
            return
        logger.info(
            "action.notify_on_qa.placeholder",
            issue=event.issue_identifier,
            # TODO: call QA notification service here
        )


@action_registry.on(EventType.issue_status_changed)
class NotifyOnDoneAction(BaseAction):
    """Placeholder: trigger post-completion workflow when an issue is Done."""

    async def execute(self, event: DomainEvent) -> None:
        if not isinstance(event, IssueStatusChangedEvent):
            return
        if event.current_state.type not in {"completed"}:
            return
        logger.info(
            "action.notify_on_done.placeholder",
            issue=event.issue_identifier,
            # TODO: call post-completion service here
        )


@action_registry.on(EventType.issue_created)
class LogIssueCreatedAction(BaseAction):
    """Placeholder: react when a new issue is created."""

    async def execute(self, event: DomainEvent) -> None:
        logger.info(
            "action.issue_created.placeholder",
            issue=event.issue_identifier,
            title=event.issue_title,
        )
