"""Translate a raw Linear webhook payload into a domain event.

This is the only place in the codebase that knows about Linear's payload
structure.  Everything downstream works with ``DomainEvent`` subclasses.

Reference: https://developers.linear.app/docs/graphql/webhooks
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.domain.events import (
    DomainEvent,
    EventType,
    IssueState,
    IssueStatusChangedEvent,
)
from app.integrations.linear.schemas import LinearWebhookPayload


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
        team_key=data.team.key if data.team else "",
        occurred_at=occurred_at,
        raw=payload.model_dump(),
    )

    match payload.action:
        case "create":
            return DomainEvent(event_type=EventType.issue_created, **base)  # type: ignore[arg-type]

        case "update":
            updated_from = payload.updatedFrom
            # Linear puts the *previous* state object under updatedFrom.state
            # and the *current* state in data.state.
            if updated_from and updated_from.state and data.state:
                prev = updated_from.state
                curr = data.state
                return IssueStatusChangedEvent(
                    **base,  # type: ignore[arg-type]
                    previous_state=IssueState(
                        id=prev.id or "",
                        name=prev.name,
                        type=prev.type or "unknown",
                    ),
                    current_state=IssueState(
                        id=curr.id or "",
                        name=curr.name,
                        type=curr.type or "unknown",
                    ),
                )
            return DomainEvent(event_type=EventType.issue_updated, **base)  # type: ignore[arg-type]

        case "remove":
            return DomainEvent(event_type=EventType.issue_removed, **base)  # type: ignore[arg-type]

        case _:
            return None
