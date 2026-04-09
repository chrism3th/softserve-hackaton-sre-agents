"""Internal, provider-agnostic domain event models.

These are the canonical event types that flow through the system.
Linear (and any future provider) maps its raw payload to one of these.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EventType(StrEnum):
    issue_created = "issue.created"
    issue_updated = "issue.updated"
    issue_status_changed = "issue.status_changed"
    issue_removed = "issue.removed"


class IssueState(BaseModel):
    """A single workflow state (e.g. Todo, In Progress, Done)."""

    id: str
    name: str
    # Linear state category: triage | backlog | unstarted | started |
    # completed | cancelled.  May be "unknown" if the webhook omits it.
    type: str = "unknown"


class DomainEvent(BaseModel):
    """Base class for all normalized domain events."""

    event_type: EventType
    issue_id: str
    issue_identifier: str  # e.g. "TEA-123"
    issue_title: str
    team_key: str
    source: str = "linear"
    occurred_at: datetime
    # Raw provider payload kept for debugging / handler edge-cases.
    raw: dict[str, Any] = Field(default_factory=dict)


class IssueStatusChangedEvent(DomainEvent):
    """Fired when an issue moves from one workflow state to another."""

    event_type: EventType = EventType.issue_status_changed
    previous_state: IssueState
    current_state: IssueState
