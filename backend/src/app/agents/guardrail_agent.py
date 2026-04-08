"""Guardrail agent — LLM-based prompt-injection classifier.

Two-stage:

1. **Fast regex pre-filter** ([app.tickets.guardrails][]) — catches the
   obvious cases without burning a token. Its verdict is the floor.
2. **LLM classifier** (Claude) — second opinion that can catch paraphrased
   or multilingual attempts the regex misses, and produces a sanitized
   `cleaned_text` that preserves the legitimate parts of the report.

If the LLM is unavailable (no API key) or returns garbage, we fall back to
the regex verdict — the pipeline never hard-fails on its own.
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field, ValidationError

from app.agents.base import Agent, AgentRequest, AgentResponse
from app.agents.prompts import load_prompt
from app.config import get_settings
from app.core.logging import get_logger
from app.core.observability import get_tracer
from app.tickets.guardrails import scan_for_injection
from app.tickets.models import GuardrailFlag, GuardrailVerdict

logger = get_logger(__name__)


class _LLMVerdict(BaseModel):
    flags: list[GuardrailFlag] = Field(default_factory=list)
    blocked: bool = False
    reasoning: str = ""
    cleaned_text: str


class GuardrailAgent(Agent):
    """Classify untrusted text for prompt-injection attempts."""

    name = "guardrail"

    async def run(self, request: AgentRequest) -> AgentResponse:
        verdict = await self.evaluate(request.input)
        return AgentResponse(
            output=verdict.cleaned_text,
            agent=self.name,
            iterations=1,
            metadata={
                "flags": [f.value for f in verdict.flags],
                "blocked": verdict.blocked,
            },
        )

    async def evaluate(self, text: str) -> GuardrailVerdict:
        tracer = get_tracer()
        with tracer.start_as_current_span("guardrail.evaluate") as span:
            verdict = await self._evaluate_inner(text)
            span.set_attribute(
                "guardrail.flags", ",".join(f.value for f in verdict.flags)
            )
            span.set_attribute("guardrail.blocked", verdict.blocked)
            return verdict

    async def _evaluate_inner(self, text: str) -> GuardrailVerdict:
        # Stage 1 — regex floor.
        base = scan_for_injection(text)

        # Stage 2 — LLM classifier (best effort).
        settings = get_settings()
        if not settings.anthropic_api_key:
            return base

        try:
            llm = await self._llm_classify(text)
        except Exception as e:  # noqa: BLE001
            logger.warning("guardrail.llm_failed", error=str(e))
            return base

        merged_flags = list(dict.fromkeys([*base.flags, *llm.flags]))
        if llm.reasoning:
            logger.info(
                "guardrail.llm_reasoning",
                reasoning=llm.reasoning,
                flags=[f.value for f in merged_flags],
                blocked=base.blocked or llm.blocked,
            )
        return GuardrailVerdict(
            flags=merged_flags,
            cleaned_text=llm.cleaned_text or base.cleaned_text,
            blocked=base.blocked or llm.blocked,
        )

    async def _llm_classify(self, text: str) -> _LLMVerdict:
        from anthropic import AsyncAnthropic

        settings = get_settings()
        client = AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            timeout=settings.llm_timeout_seconds,
        )
        message = await client.messages.create(
            model=settings.llm_model,
            max_tokens=600,
            system=load_prompt("guardrail"),
            messages=[
                {
                    "role": "user",
                    "content": json.dumps({"untrusted_text": text}),
                }
            ],
        )
        raw = "".join(
            b.text for b in message.content if getattr(b, "type", "") == "text"
        )
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        payload = match.group(0) if match else raw
        try:
            return _LLMVerdict.model_validate_json(payload)
        except ValidationError as e:
            raise ValueError(f"invalid guardrail JSON: {e}") from e
