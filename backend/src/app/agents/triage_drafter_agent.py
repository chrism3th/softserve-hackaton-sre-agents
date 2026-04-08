"""Triage Drafter agent.

Takes a sanitized ``IncidentDTO`` and produces the structured payload that
the orchestrator will use to create a Linear ticket: clean imperative
title, technical summary, severity bucket, numeric score.

This is the LLM-powered "brain" of the ticket pipeline. The orchestrator
remains deterministic; this agent is the only place where the model gets
to author free text that ends up in the ticket.
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
from app.tickets.models import IncidentDTO, Severity

logger = get_logger(__name__)


class TriageDraft(BaseModel):
    title: str = Field(..., max_length=200)
    summary: str = Field(..., max_length=2000)
    severity: Severity
    score: int = Field(ge=0, le=100)


class TriageDrafterAgent(Agent):
    """Triage an incident and draft the Linear ticket content."""

    name = "triage_drafter"

    async def run(self, request: AgentRequest) -> AgentResponse:
        ctx = request.context or {}
        incident = IncidentDTO(
            title=ctx.get("title") or request.input[:120],
            body=ctx.get("body") or request.input,
            reporter=ctx.get("reporter"),
        )
        draft = await self.draft(incident)
        return AgentResponse(
            output=draft.title,
            agent=self.name,
            iterations=1,
            metadata=draft.model_dump(),
        )

    async def draft(self, incident: IncidentDTO) -> TriageDraft:
        tracer = get_tracer()
        with tracer.start_as_current_span("triage_drafter.draft") as span:
            draft = await self._draft_inner(incident)
            span.set_attribute("triage.severity", draft.severity.value)
            span.set_attribute("triage.score", draft.score)
            return draft

    async def _draft_inner(self, incident: IncidentDTO) -> TriageDraft:
        settings = get_settings()
        if not settings.anthropic_api_key:
            return self._fallback(incident)

        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(
                api_key=settings.anthropic_api_key,
                timeout=settings.llm_timeout_seconds,
            )
            user_payload = json.dumps(
                {"title": incident.title, "body": incident.body},
                ensure_ascii=False,
            )
            message = await client.messages.create(
                model=settings.llm_model,
                max_tokens=600,
                system=load_prompt("triage_drafter"),
                messages=[{"role": "user", "content": user_payload}],
            )
            raw = "".join(
                b.text for b in message.content if getattr(b, "type", "") == "text"
            )
            return TriageDraft.model_validate_json(_extract_json(raw))
        except (ValidationError, ValueError, Exception) as e:  # noqa: BLE001
            logger.warning("triage_drafter.fallback", error=str(e))
            return self._fallback(incident)

    @staticmethod
    def _fallback(incident: IncidentDTO) -> TriageDraft:
        body_lower = (incident.title + " " + incident.body).lower()
        if any(k in body_lower for k in ("outage", "down", "500", "data loss", "p0")):
            sev, score = Severity.P0, 90
        elif any(k in body_lower for k in ("error", "fail", "broken", "crash")):
            sev, score = Severity.P1, 70
        elif any(k in body_lower for k in ("slow", "latency", "warning")):
            sev, score = Severity.P2, 40
        else:
            sev, score = Severity.P3, 20
        return TriageDraft(
            title=incident.title[:120],
            summary=(incident.body or incident.title)[:600],
            severity=sev,
            score=score,
        )


def _extract_json(text: str) -> str:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text
