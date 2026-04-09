"""Translate a raw Linear webhook payload into a domain event.

This is the only place in the codebase that knows about Linear's payload
structure.  Everything downstream works with ``DomainEvent`` subclasses.

Reference: https://developers.linear.app/docs/graphql/webhooks
"""

from __future__ import annotations

import structlog
from datetime import datetime, timezone

from app.domain.events import (
    DomainEvent,
    EventType,
    IssueState,
    IssueStatusChangedEvent,
)
from app.integrations.linear.schemas import LinearUpdatedFromDTO, LinearWebhookPayload

logger = structlog.get_logger(__name__)


def parse_webhook(payload: LinearWebhookPayload) -> DomainEvent | None:
    """Return the appropriate domain event or ``None`` if not actionable.

    Returns ``None`` for:
    - Non-Issue entities (Comments, Labels, …)
    - Unknown action strings
    - Updates without enough context to build a useful event
    """
    if payload.type != "Issue":
        return None

    data = payload.data
    occurred_at = payload.createdAt or datetime.now(timezone.utc)

    base: dict[str, object] = dict(
        issue_id=data.id,
        issue_identifier=data.identifier,
        issue_title=data.title,
        issue_description=data.description,
        team_key=data.team.key if data.team else "",
        occurred_at=occurred_at,
        raw=payload.model_dump(),
    )

    match payload.action:
        case "create":
            return DomainEvent(event_type=EventType.issue_created, **base)  # type: ignore[arg-type]

        case "update":
            return _parse_update(payload, base)

        case "remove":
            return DomainEvent(event_type=EventType.issue_removed, **base)  # type: ignore[arg-type]

        case _:
            return None


def _parse_update(
    payload: LinearWebhookPayload,
    base: dict[str, object],
) -> DomainEvent:
    """Classify an 'update' action as either a status change or a generic update."""
    updated_from = payload.updatedFrom
    data = payload.data

    logger.debug(
        "linear_parser.update_received",
        issue=data.identifier,
        updated_from=updated_from.model_dump() if updated_from else None,
        current_state=data.state.model_dump() if data.state else None,
    )

    if _is_state_change(updated_from) and data.state:
        prev_state = _resolve_previous_state(updated_from)
        curr = data.state
        return IssueStatusChangedEvent(
            **base,  # type: ignore[arg-type]
            previous_state=prev_state,
            current_state=IssueState(
                id=curr.id or "",
                name=curr.name,
                type=curr.type or "unknown",
            ),
            reporter_email=data.creator.email if data.creator else None,
        )

    return DomainEvent(event_type=EventType.issue_updated, **base)  # type: ignore[arg-type]


def _is_state_change(updated_from: LinearUpdatedFromDTO | None) -> bool:
    """Return True if the payload signals a workflow-state transition.

    Linear sends ``stateId`` (the previous state's UUID) when the state
    changes.  Some integrations also send a nested ``state`` object.
    We accept either form.
    """
    if updated_from is None:
        return False
    return bool(updated_from.stateId or updated_from.state)


def _resolve_previous_state(updated_from: LinearUpdatedFromDTO | None) -> IssueState:
    """Build an IssueState for the previous state from whatever Linear provides.

    If only ``stateId`` is available (the common case), the name is
    'unknown' — Linear doesn't include it in the webhook payload.
    """
    if updated_from is None:
        return IssueState(id="", name="unknown", type="unknown")

    # Full nested object present (some integrations / future format)
    if updated_from.state:
        s = updated_from.state
        return IssueState(
            id=s.id or updated_from.stateId or "",
            name=s.name,
            type=s.type or "unknown",
        )

    # Only the ID — the common Linear format
    return IssueState(
        id=updated_from.stateId or "",
        name="unknown",
        type="unknown",
    )
