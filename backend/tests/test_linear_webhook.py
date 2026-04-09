"""Tests for the Linear webhook ingestion pipeline."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.domain.events import EventType, IssueStatusChangedEvent
from app.integrations.linear.parser import parse_webhook
from app.integrations.linear.schemas import LinearWebhookPayload
from app.main import app

# ── fixtures ─────────────────────────────────────────────────────────────────

WEBHOOK_SECRET = "test-secret-abc123"


def _make_payload(
    action: str = "update",
    entity_type: str = "Issue",
    state_name: str = "In Progress",
    state_id: str = "curr-state-id",
    state_type: str = "started",
    prev_state_name: str = "Todo",
    prev_state_id: str = "prev-state-id",
    include_updated_from: bool = True,
    timestamp_ms: int | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "action": action,
        "type": entity_type,
        "organizationId": "org-123",
        "createdAt": "2026-04-08T10:00:00.000Z",
        "webhookTimestamp": timestamp_ms if timestamp_ms is not None else int(time.time() * 1000),
        "webhookId": "wh-abc",
        "data": {
            "id": "issue-abc",
            "identifier": "TEA-42",
            "title": "Production is on fire",
            "state": {"id": state_id, "name": state_name, "type": state_type},
            "team": {"id": "team-1", "key": "TEA", "name": "Team"},
        },
    }
    if include_updated_from and action == "update":
        payload["updatedFrom"] = {
            "state": {"id": prev_state_id, "name": prev_state_name, "type": "unstarted"},
        }
    return payload


def _sign(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# ── parser tests ──────────────────────────────────────────────────────────────


class TestParseWebhook:
    def test_status_change_returns_correct_event(self) -> None:
        raw = _make_payload()
        payload = LinearWebhookPayload.model_validate(raw)
        event = parse_webhook(payload)

        assert isinstance(event, IssueStatusChangedEvent)
        assert event.event_type == EventType.issue_status_changed
        assert event.issue_identifier == "TEA-42"
        assert event.previous_state.name == "Todo"
        assert event.current_state.name == "In Progress"
        assert event.current_state.type == "started"
        assert event.team_key == "TEA"

    def test_create_action_returns_created_event(self) -> None:
        raw = _make_payload(action="create", include_updated_from=False)
        payload = LinearWebhookPayload.model_validate(raw)
        event = parse_webhook(payload)

        assert event is not None
        assert event.event_type == EventType.issue_created

    def test_remove_action_returns_removed_event(self) -> None:
        raw = _make_payload(action="remove", include_updated_from=False)
        payload = LinearWebhookPayload.model_validate(raw)
        event = parse_webhook(payload)

        assert event is not None
        assert event.event_type == EventType.issue_removed

    def test_non_issue_type_returns_none(self) -> None:
        raw = _make_payload()
        raw["type"] = "Comment"
        payload = LinearWebhookPayload.model_validate(raw)

        assert parse_webhook(payload) is None

    def test_update_without_state_change_returns_updated_event(self) -> None:
        raw = _make_payload(include_updated_from=False)
        payload = LinearWebhookPayload.model_validate(raw)
        event = parse_webhook(payload)

        assert event is not None
        assert event.event_type == EventType.issue_updated

    def test_unknown_action_returns_none(self) -> None:
        raw = _make_payload(action="archive")
        payload = LinearWebhookPayload.model_validate(raw)

        assert parse_webhook(payload) is None


# ── endpoint tests ────────────────────────────────────────────────────────────


@pytest.fixture()
def with_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LINEAR_WEBHOOK_SECRET", WEBHOOK_SECRET)
    # bust the lru_cache so the new env var is picked up
    from app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def no_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LINEAR_WEBHOOK_SECRET", "")
    from app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestLinearWebhookEndpoint:
    async def _post(
        self,
        body: bytes,
        signature: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        headers = {"Content-Type": "application/json"}
        if signature is not None:
            headers["Linear-Signature"] = signature
        if extra_headers:
            headers.update(extra_headers)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.post("/api/v1/webhooks/linear", content=body, headers=headers)

    async def test_valid_payload_returns_204(self, no_secret: None) -> None:
        body = json.dumps(_make_payload()).encode()
        with patch(
            "app.core.event_dispatcher.EventDispatcher.dispatch",
            new_callable=AsyncMock,
        ):
            resp = await self._post(body)
        assert resp.status_code == 204

    async def test_invalid_signature_returns_401(self, with_secret: None) -> None:
        body = json.dumps(_make_payload()).encode()
        resp = await self._post(body, signature="deadbeef")
        assert resp.status_code == 401

    async def test_missing_signature_returns_401(self, with_secret: None) -> None:
        body = json.dumps(_make_payload()).encode()
        resp = await self._post(body, signature=None)
        assert resp.status_code == 401

    async def test_valid_signature_accepted(self, with_secret: None) -> None:
        body = json.dumps(_make_payload()).encode()
        sig = _sign(body)
        with patch(
            "app.core.event_dispatcher.EventDispatcher.dispatch",
            new_callable=AsyncMock,
        ):
            resp = await self._post(body, signature=sig)
        assert resp.status_code == 204

    async def test_stale_timestamp_returns_400(self, no_secret: None) -> None:
        old_ts = int((time.time() - 600) * 1000)  # 10 minutes ago
        body = json.dumps(_make_payload(timestamp_ms=old_ts)).encode()
        resp = await self._post(body)
        assert resp.status_code == 400

    async def test_non_issue_payload_ignored(self, no_secret: None) -> None:
        raw = _make_payload()
        raw["type"] = "Comment"
        body = json.dumps(raw).encode()
        resp = await self._post(body)
        assert resp.status_code == 204

    async def test_dispatch_called_for_status_change(self, no_secret: None) -> None:
        body = json.dumps(_make_payload()).encode()
        mock_dispatch = AsyncMock()
        with patch("app.api.webhooks.event_dispatcher.dispatch", mock_dispatch):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/webhooks/linear",
                    content=body,
                    headers={"Content-Type": "application/json"},
                )
        assert resp.status_code == 204
        # dispatch is scheduled as a background task — it runs during the request
        mock_dispatch.assert_awaited_once()
        event = mock_dispatch.call_args[0][0]
        assert isinstance(event, IssueStatusChangedEvent)
        assert event.issue_identifier == "TEA-42"
