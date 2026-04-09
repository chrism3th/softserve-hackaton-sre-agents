"""Action: notify the issue reporter when the status reaches a trigger state."""

from __future__ import annotations

from app.actions.base import BaseAction
from app.actions.registry import action_registry
from app.core.logging import get_logger
from app.domain.events import DomainEvent, EventType, IssueStatusChangedEvent
from app.services.email_service import TRIGGER_STATES, notify_status_change

logger = get_logger(__name__)


@action_registry.on(EventType.issue_status_changed)
class NotifyReporterAction(BaseAction):
    """Send an email to the issue reporter when the state enters a trigger state.

    Trigger states: Done, Ready to Start  (see ``email_service.TRIGGER_STATES``).

    To add a new trigger state:
        1. Add the lowercased name to ``email_service.TRIGGER_STATES``.
        2. Add a template branch in ``email_service._render_template``.
        Nothing else needs changing.
    """

    async def execute(self, event: DomainEvent) -> None:
        if not isinstance(event, IssueStatusChangedEvent):
            return

        if event.current_state.name.lower() not in TRIGGER_STATES:
            logger.debug(
                "notify_reporter.state_not_triggered",
                issue=event.issue_identifier,
                state=event.current_state.name,
            )
            return

        if not event.reporter_email:
            logger.info(
                "notify_reporter.no_email",
                issue=event.issue_identifier,
                state=event.current_state.name,
            )
            return

        logger.info(
            "notify_reporter.sending",
            issue=event.issue_identifier,
            to=event.reporter_email,
            state=event.current_state.name,
        )

        await notify_status_change(
            to=event.reporter_email,
            issue_identifier=event.issue_identifier,
            issue_title=event.issue_title,
            new_state=event.current_state.name,
        )
