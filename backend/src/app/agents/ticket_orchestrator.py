"""Ticket Orchestrator agent.

End-to-end pipeline for the *INGEST → TICKET* leg of the SRE flow:

    1. Guardrails       — flag/sanitize prompt-injection attempts
    2. Triage (LLM)     — clean title, summary, severity, score
    3. Dedup (Linear)   — search existing TEA issues for near-duplicates
    4. Create (Linear)  — open the ticket and return its identifier

Image analysis is a TODO hook (the dataclass already carries images).
"""

from __future__ import annotations

from app.agents.base import Agent, AgentRequest, AgentResponse
from app.agents.guardrail_agent import GuardrailAgent
from app.agents.image_analyzer_agent import ImageAnalyzerAgent
from app.agents.triage_drafter_agent import TriageDrafterAgent
from app.config import get_settings
from app.core.db import session_scope
from app.core.logging import get_logger
from app.core.observability import get_tracer
from app.tickets.linear_client import LinearClient
from app.tickets.models import (
    GuardrailFlag,
    ImageInsight,
    IncidentDTO,
    IncidentSource,
    OrchestratorResult,
    Severity,
)
from app.tickets.repository import log_injection_attempt

logger = get_logger(__name__)

# Linear priority enum: 0 No priority, 1 Urgent, 2 High, 3 Medium, 4 Low
_PRIORITY_MAP = {
    Severity.P0: 1,
    Severity.P1: 2,
    Severity.P2: 3,
    Severity.P3: 4,
}


class TicketOrchestratorAgent(Agent):
    name = "ticket_orchestrator"

    def __init__(self) -> None:
        self._guardrail = GuardrailAgent()
        self._image_analyzer = ImageAnalyzerAgent()
        self._drafter = TriageDrafterAgent()

    async def run(self, request: AgentRequest) -> AgentResponse:
        incident = self._coerce_incident(request)
        result = await self.orchestrate(incident)
        return AgentResponse(
            output=result.linear_url or result.title,
            agent=self.name,
            iterations=1,
            metadata=result.model_dump(),
        )

    @staticmethod
    def _coerce_incident(request: AgentRequest) -> IncidentDTO:
        ctx = request.context or {}
        return IncidentDTO(
            title=ctx.get("title") or request.input[:120],
            body=ctx.get("body") or request.input,
            reporter=ctx.get("reporter"),
            source=IncidentSource(ctx.get("source", "api")),
        )

    async def orchestrate(self, incident: IncidentDTO) -> OrchestratorResult:
        tracer = get_tracer()
        with tracer.start_as_current_span("ticket_orchestrator.orchestrate") as span:
            span.set_attribute("incident.source", incident.source.value)
            span.set_attribute("incident.reporter", incident.reporter or "anonymous")
            span.set_attribute("incident.title", incident.title[:200])
            result = await self._orchestrate_inner(incident)
            span.set_attribute("ticket.linear_identifier", result.linear_identifier or "")
            span.set_attribute("ticket.severity", result.severity.value)
            span.set_attribute("ticket.score", result.score)
            span.set_attribute("ticket.blocked", result.blocked)
            span.set_attribute(
                "guardrail.flags",
                ",".join(f.value for f in result.guardrail_flags),
            )
            return result

    async def _orchestrate_inner(self, incident: IncidentDTO) -> OrchestratorResult:
        settings = get_settings()

        # 1. Guardrails — delegate to the GuardrailAgent (LLM + regex).
        combined = f"{incident.title}\n\n{incident.body}"
        verdict = await self._guardrail.evaluate(combined)

        if verdict.triggered:
            logger.warning(
                "guardrail.triggered",
                flags=[f.value for f in verdict.flags],
                blocked=verdict.blocked,
                reporter=incident.reporter,
            )
            async with session_scope() as session:
                await log_injection_attempt(
                    session,
                    source=incident.source,
                    reporter=incident.reporter,
                    raw_input=combined,
                    flags=verdict.flags,
                    blocked=verdict.blocked,
                )

        if verdict.blocked:
            return OrchestratorResult(
                severity=Severity.P3,
                score=0,
                guardrail_flags=verdict.flags,
                blocked=True,
                title=incident.title,
                description="Blocked by guardrails (suspected prompt injection).",
            )

        # Sanitized incident continues through the pipeline.
        cleaned = IncidentDTO(
            title=incident.title,
            body=verdict.cleaned_text,
            reporter=incident.reporter,
            source=incident.source,
            images=incident.images,
            raw=incident.raw,
        )

        # 2. Image analysis (Claude Vision over each attachment).
        insights = await self._image_analyzer.analyze(cleaned.images)
        if insights:
            logger.info(
                "image_analyzer.done",
                count=len(insights),
                signals=[s for i in insights for s in i.error_signals],
            )

        # 3. Triage + draft. Enrich the body with visual evidence so the
        # drafter sees everything as text.
        enriched = IncidentDTO(
            title=cleaned.title,
            body=_with_visual_evidence(cleaned.body, insights),
            reporter=cleaned.reporter,
            source=cleaned.source,
            images=cleaned.images,
            raw=cleaned.raw,
        )
        draft = await self._drafter.draft(enriched)

        description = self._render_description(
            cleaned, draft.summary, verdict.flags, insights
        )

        # 3 + 4. Dedup + create in Linear.
        async with LinearClient() as linear:
            team_id = await linear.get_team_id(settings.linear_team_key)
            dups = await linear.search_issues(team_id, term=draft.title[:60], limit=5)
            dedup_of = dups[0]["identifier"] if dups else None

            if dedup_of:
                logger.info("ticket.dedup_hit", existing=dedup_of)
                return OrchestratorResult(
                    linear_identifier=dups[0]["identifier"],
                    linear_url=dups[0]["url"],
                    severity=draft.severity,
                    score=draft.score,
                    dedup_of=dedup_of,
                    guardrail_flags=verdict.flags,
                    title=draft.title,
                    description=description,
                )

            issue = await linear.create_issue(
                team_id=team_id,
                title=draft.title,
                description=description,
                priority=_PRIORITY_MAP[draft.severity],
            )

        logger.info(
            "ticket.created",
            identifier=issue["identifier"],
            severity=draft.severity.value,
            score=draft.score,
            guardrail_flags=[f.value for f in verdict.flags],
        )

        return OrchestratorResult(
            linear_identifier=issue["identifier"],
            linear_url=issue["url"],
            severity=draft.severity,
            score=draft.score,
            dedup_of=None,
            guardrail_flags=verdict.flags,
            title=draft.title,
            description=description,
        )

    @staticmethod
    def _render_description(
        incident: IncidentDTO,
        summary: str,
        flags: list[GuardrailFlag],
        insights: list[ImageInsight],
    ) -> str:
        github_issue_url = ""
        if incident.source is IncidentSource.github_issue:
            github_issue_url = str(incident.raw.get("github_issue_url") or "")

        parts = [
            f"**Source:** {incident.source.value}",
            f"**Reporter:** {incident.reporter or 'unknown'}",
        ]
        if github_issue_url:
            parts += [f"**GitHub Issue:** {github_issue_url}"]

        parts += [
            "",
            "## Summary",
            summary,
            "",
            "## Original report",
            incident.body or "_(empty)_",
        ]
        if insights:
            parts += ["", "## Visual evidence"]
            for ins in insights:
                parts += [f"### {ins.url}"]
                if ins.error:
                    parts += [f"_analysis failed: {ins.error}_"]
                    continue
                if ins.caption:
                    parts += [f"**Caption:** {ins.caption}"]
                if ins.error_signals:
                    parts += [f"**Signals:** {', '.join(ins.error_signals)}"]
                if ins.extracted_text:
                    parts += ["", "```", ins.extracted_text, "```"]
        elif incident.images:
            parts += ["", "## Attachments"]
            parts += [f"- {img.url}" for img in incident.images]
        if flags:
            parts += [
                "",
                "## ⚠ Guardrail flags",
                ", ".join(f.value for f in flags),
            ]
        return "\n".join(parts)


def _with_visual_evidence(body: str, insights: list[ImageInsight]) -> str:
    if not insights:
        return body
    extras = ["", "## Visual evidence (auto-extracted)"]
    for ins in insights:
        if ins.error:
            continue
        if ins.caption:
            extras.append(f"- {ins.caption}")
        if ins.error_signals:
            extras.append(f"  signals: {', '.join(ins.error_signals)}")
        if ins.extracted_text:
            extras.append(f"  text: {ins.extracted_text[:500]}")
    return body + "\n" + "\n".join(extras)
