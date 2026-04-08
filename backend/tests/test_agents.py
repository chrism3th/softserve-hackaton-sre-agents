"""Agent endpoint and base behavior tests."""

from __future__ import annotations

import pytest

from app.agents.base import AgentRequest, EchoAgent
from app.agents.registry import get_agent, list_agents


def test_registry_lists_known_agents():
    names = list_agents()
    assert "echo" in names
    assert "claude" in names


def test_registry_raises_on_unknown_agent():
    with pytest.raises(KeyError):
        get_agent("nonexistent")


@pytest.mark.asyncio
async def test_echo_agent_returns_input():
    agent = EchoAgent()
    response = await agent.run(AgentRequest(input="hello world"))
    assert response.output == "hello world"
    assert response.agent == "echo"
    assert response.iterations == 1


@pytest.mark.asyncio
async def test_list_agents_endpoint(client):
    response = await client.get("/api/v1/agents")
    assert response.status_code == 200
    body = response.json()
    assert "agents" in body
    assert "echo" in body["agents"]


@pytest.mark.asyncio
async def test_invoke_echo_endpoint(client):
    response = await client.post(
        "/api/v1/agents/echo/invoke",
        json={"input": "ping"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["output"] == "ping"
    assert body["agent"] == "echo"


@pytest.mark.asyncio
async def test_invoke_unknown_agent_returns_404(client):
    response = await client.post(
        "/api/v1/agents/ghost/invoke",
        json={"input": "hi"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_invoke_rejects_empty_input(client):
    response = await client.post(
        "/api/v1/agents/echo/invoke",
        json={"input": ""},
    )
    assert response.status_code == 422
