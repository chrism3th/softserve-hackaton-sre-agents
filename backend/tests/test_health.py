"""Health endpoint tests."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_healthz_returns_ok(client):
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readyz_returns_ready(client):
    response = await client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
