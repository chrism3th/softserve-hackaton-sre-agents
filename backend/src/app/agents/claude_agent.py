"""Reference Claude agent using the Anthropic SDK.

This is a *thin* wrapper. The goal is to show the shape of a real agent
(configuration, structured output, token accounting, error handling)
without coupling the rest of the system to Anthropic-specific types.
"""

from __future__ import annotations

from typing import Any

from anthropic.types.text_block import TextBlock

from app.agents.base import Agent, AgentRequest, AgentResponse
from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = (
    "You are a concise assistant built for a hackathon demo. "
    "Prefer short, direct answers. Decline unsafe requests."
)


class ClaudeAgent(Agent):
    """Single-turn Claude agent.

    Extend with tool use, RAG, or conversation memory as needed.
    """

    name = "claude"

    async def run(self, request: AgentRequest) -> AgentResponse:
        settings = get_settings()

        if not settings.anthropic_api_key:
            logger.warning("claude.no_api_key", hint="set ANTHROPIC_API_KEY")
            return AgentResponse(
                output=(
                    "Claude agent is not configured. Set ANTHROPIC_API_KEY in "
                    "your .env file to enable real responses."
                ),
                agent=self.name,
                metadata={"configured": False},
            )

        # Import lazily so the module remains importable without the SDK
        # (e.g., in unit tests that don't exercise this agent).
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            timeout=settings.llm_timeout_seconds,
        )

        logger.info("claude.invoke", model=settings.llm_model)
        message = await client.messages.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": request.input}],
        )

        text = "".join(block.text for block in message.content if isinstance(block, TextBlock))

        metadata: dict[str, Any] = {
            "model": message.model,
            "stop_reason": message.stop_reason,
        }

        return AgentResponse(
            output=text,
            agent=self.name,
            iterations=1,
            tokens_used=message.usage.input_tokens + message.usage.output_tokens,
            metadata=metadata,
        )
