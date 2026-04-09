"""Tests for the GitHub webhook setup endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app


@pytest.fixture()
def _github_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_API_TOKEN", "ghp_test")
    monkeypatch.setenv("GITHUB_REPO", "acme/repo")
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "secret123")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def _no_github_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_API_TOKEN", "ghp_test")
    monkeypatch.setenv("GITHUB_REPO", "")
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestSetupWebhook:
    async def test_creates_webhook_when_none_exists(self, _github_env: None) -> None:
        with patch(
            "app.api.github.GitHubClient.list_webhooks",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "app.api.github.GitHubClient.create_webhook",
            new_callable=AsyncMock,
            return_value={"id": 42},
        ) as create_wh:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/github/setup-webhook",
                    json={"payload_url": "https://example.ngrok.io/api/v1/tickets/github-webhook"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] is True
        assert data["webhook_id"] == 42
        create_wh.assert_awaited_once()

    async def test_detects_existing_webhook(self, _github_env: None) -> None:
        existing_hook = {
            "id": 99,
            "config": {"url": "https://example.ngrok.io/api/v1/tickets/github-webhook"},
        }
        with patch(
            "app.api.github.GitHubClient.list_webhooks",
            new_callable=AsyncMock,
            return_value=[existing_hook],
        ), patch(
            "app.api.github.GitHubClient.create_webhook",
            new_callable=AsyncMock,
        ) as create_wh:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/github/setup-webhook",
                    json={"payload_url": "https://example.ngrok.io/api/v1/tickets/github-webhook"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] is False
        assert data["webhook_id"] == 99
        create_wh.assert_not_awaited()

    async def test_returns_400_when_repo_not_configured(self, _no_github_env: None) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/github/setup-webhook",
                json={"payload_url": "https://example.ngrok.io/hook"},
            )

        assert resp.status_code == 400
