"""Agent endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.agents.base import AgentRequest, AgentResponse
from app.agents.registry import get_agent, list_agents

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", summary="List available agents")
async def list_available_agents() -> dict[str, list[str]]:
    return {"agents": list_agents()}


@router.post(
    "/{agent_name}/invoke",
    response_model=AgentResponse,
    summary="Invoke an agent",
)
async def invoke_agent(agent_name: str, request: AgentRequest) -> AgentResponse:
    try:
        agent = get_agent(agent_name)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown agent: {agent_name}",
        ) from e

    return await agent.run(request)
