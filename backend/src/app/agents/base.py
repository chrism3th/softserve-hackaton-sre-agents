"""Agent base protocol and a trivial reference implementation.

Keep the abstraction minimal — this is a hackathon, not an SDK.
Add richer features (tool use, memory, streaming) by composition,
not by extending the base protocol.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Request payload sent to an agent."""

    input: str = Field(..., min_length=1, max_length=10_000)
    context: dict[str, Any] = Field(default_factory=dict)
    max_iterations: int = Field(default=5, ge=1, le=20)


class AgentResponse(BaseModel):
    """Response from an agent invocation."""

    output: str
    agent: str
    iterations: int = 1
    tokens_used: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class Agent(ABC):
    """Minimal agent interface.

    Subclasses implement ``run`` and may use any combination of LLM calls,
    tools, memory, retrieval, or deterministic logic.
    """

    name: str

    @abstractmethod
    async def run(self, request: AgentRequest) -> AgentResponse:
        """Execute the agent and return a response."""


class EchoAgent(Agent):
    """Trivial agent that echoes input — used for smoke tests."""

    name = "echo"

    async def run(self, request: AgentRequest) -> AgentResponse:
        return AgentResponse(
            output=request.input,
            agent=self.name,
            iterations=1,
            tokens_used=0,
        )
