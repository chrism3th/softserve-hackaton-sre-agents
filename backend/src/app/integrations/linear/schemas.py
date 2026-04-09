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


class LinearCreatorDTO(BaseModel):
    id: str
    name: str | None = None
    email: str | None = None


class LinearIssueDataDTO(BaseModel):
    id: str
    identifier: str  # e.g. "TEA-123"
    title: str
    state: LinearStateDTO | None = None
    team: LinearTeamDTO | None = None
    creator: LinearCreatorDTO | None = None


class LinearUpdatedFromDTO(BaseModel):
    """Previous values for fields that changed in an 'update' event.

    Linear sends the *ID* of the previous related entity, not the full
    nested object.  For a state change that means ``stateId`` is present.
    Some integrations also return a nested ``state`` object — we handle
    both so we're resilient to changes in Linear's webhook format.
    """

    # Linear's actual format for a state change: just the previous state ID.
    stateId: str | None = None
    # Occasionally present as a full nested object (integration-dependent).
    state: LinearStateDTO | None = None

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
