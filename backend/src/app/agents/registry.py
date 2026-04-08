"""Registry of agent implementations.

Register new agents here by importing and adding them to ``_REGISTRY``.
Keep this simple: a dict is a perfectly good registry for dozens of agents.
"""

from __future__ import annotations

from app.agents.base import Agent, EchoAgent
from app.agents.claude_agent import ClaudeAgent

_REGISTRY: dict[str, Agent] = {
    EchoAgent.name: EchoAgent(),
    ClaudeAgent.name: ClaudeAgent(),
}


def get_agent(name: str) -> Agent:
    """Return the registered agent for ``name``.

    Raises:
        KeyError: if no agent is registered under that name.
    """
    try:
        return _REGISTRY[name]
    except KeyError as e:
        raise KeyError(name) from e


def list_agents() -> list[str]:
    """Return the sorted list of registered agent names."""
    return sorted(_REGISTRY)
