"""Duplicate detection agent.

Compares a new incident against existing Linear tickets and uses an LLM
to decide whether the incident is a genuine duplicate.  Falls back to
simple title comparison when no API key is configured.
"""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ValidationError

from app.agents.base import Agent, AgentRequest, AgentResponse
from app.agents.prompts import load_prompt
from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class DedupResult(BaseModel):
    is_duplicate: bool
    duplicate_of_identifier: str | None = None
    duplicate_of_url: str | None = None
    reason: str | None = None


class DedupAgent(Agent):
    """Decide whether a new incident duplicates an existing ticket."""

    name = "dedup"

    async def run(self, request: AgentRequest) -> AgentResponse:
        result = await self.evaluate(request.context)
        return AgentResponse(
            output=result.reason or ("duplicate" if result.is_duplicate else "not duplicate"),
            agent=self.name,
            iterations=1,
            metadata=result.model_dump(),
        )

    async def evaluate(self, context: dict[str, Any]) -> DedupResult:
        """Compare the new incident against candidates.

        ``context`` must contain:
        - ``new_title``: str
        - ``new_body``: str
        - ``candidates``: list[dict] with keys identifier, title, url, description
        """
        candidates: list[dict[str, Any]] = context.get("candidates", [])
        if not candidates:
            return DedupResult(is_duplicate=False, reason="No candidates to compare")

        settings = get_settings()
        if not settings.anthropic_api_key:
            return self._fallback(context)

        try:
            return await self._evaluate_llm(context, settings)
        except Exception as e:
            logger.warning("dedup_agent.llm_fallback", error=str(e))
            return self._fallback(context)

    async def _evaluate_llm(
        self,
        context: dict[str, Any],
        settings: Any,
    ) -> DedupResult:
        from anthropic import AsyncAnthropic
        from anthropic.types.text_block import TextBlock

        client = AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            timeout=settings.llm_timeout_seconds,
        )

        payload = json.dumps(
            {
                "new_incident": {
                    "title": context.get("new_title", ""),
                    "body": context.get("new_body", ""),
                },
                "candidates": [
                    {
                        "identifier": c.get("identifier", ""),
                        "title": c.get("title", ""),
                        "url": c.get("url", ""),
                        "description": (c.get("description") or "")[:500],
                    }
                    for c in context.get("candidates", [])
                ],
            },
            ensure_ascii=False,
        )

        message = await client.messages.create(
            model=settings.llm_model,
            max_tokens=300,
            system=load_prompt("dedup"),
            messages=[{"role": "user", "content": payload}],
        )

        raw = "".join(b.text for b in message.content if isinstance(b, TextBlock))
        return DedupResult.model_validate_json(_extract_json(raw))

    @staticmethod
    def _fallback(context: dict[str, Any]) -> DedupResult:
        """Simple title comparison when LLM is unavailable."""
        new_title = (context.get("new_title") or "").lower().strip()
        for candidate in context.get("candidates", []):
            cand_title = (candidate.get("title") or "").lower().strip()
            if new_title and cand_title and new_title == cand_title:
                return DedupResult(
                    is_duplicate=True,
                    duplicate_of_identifier=candidate.get("identifier"),
                    duplicate_of_url=candidate.get("url"),
                    reason="Exact title match (fallback mode)",
                )
        return DedupResult(is_duplicate=False, reason="No exact title match (fallback mode)")


def _extract_json(text: str) -> str:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text
