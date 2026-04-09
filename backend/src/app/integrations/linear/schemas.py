"""Pydantic DTOs for the Linear webhook payload.

Only the fields we actually use are modelled — extra fields are ignored.
Never import these outside the ``integrations/linear`` package; callers
should work with domain events instead.

Reference: https://developers.linear.app/docs/graphql/webhooks
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class LinearStateDTO(BaseModel):
    """Workflow state as returned inside a Linear issue payload.

    ``type`` is present in practice (unstarted / started / completed /
    cancelled / triage / backlog) but is not documented in the webhook
    spec, so it is optional.
    """

    id: str | None = None
    name: str
    type: str | None = None


class LinearTeamDTO(BaseModel):
    id: str
    key: str
    name: str


class LinearIssueDataDTO(BaseModel):
    id: str
    identifier: str  # e.g. "TEA-123"
    title: str
    state: LinearStateDTO | None = None
    team: LinearTeamDTO | None = None


class LinearUpdatedFromDTO(BaseModel):
    """Previous values for fields that changed in an 'update' event.

    For a state transition, Linear includes the full previous state object
    (id + name), not just the ID.
    """

    state: LinearStateDTO | None = None

    # Accept other changed-field snapshots we don't care about yet.
    model_config = {"extra": "ignore"}


class LinearWebhookPayload(BaseModel):
    """Top-level Linear webhook envelope."""

    action: str  # "create" | "update" | "remove"
    type: str  # "Issue" | "Comment" | "IssueLabel" | …
    organizationId: str | None = None
    createdAt: datetime | None = None
    # Unix timestamp in milliseconds — used for replay-attack detection.
    webhookTimestamp: int | None = None
    webhookId: str | None = None
    data: LinearIssueDataDTO
    updatedFrom: LinearUpdatedFromDTO | None = None

    # Accept (and discard) any extra fields Linear may add in the future.
    model_config = {"extra": "ignore"}
