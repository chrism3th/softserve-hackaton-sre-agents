"""Tests for TicketOrchestrator description rendering."""

from __future__ import annotations

from app.agents.ticket_orchestrator import TicketOrchestratorAgent
from app.tickets.models import IncidentDTO, IncidentSource


def test_render_description_includes_github_issue_url_for_github_source() -> None:
    incident = IncidentDTO(
        title="Investigate outage",
        body="Service is down",
        reporter="octocat",
        source=IncidentSource.github_issue,
        raw={"github_issue_url": "https://github.com/acme/repo/issues/123"},
    )

    description = TicketOrchestratorAgent._render_description(
        incident=incident,
        summary="Triage summary",
        flags=[],
        insights=[],
    )

    assert "**GitHub Issue:** https://github.com/acme/repo/issues/123" in description


def test_render_description_skips_github_issue_url_when_missing() -> None:
    incident = IncidentDTO(
        title="Investigate outage",
        body="Service is down",
        reporter="octocat",
        source=IncidentSource.github_issue,
    )

    description = TicketOrchestratorAgent._render_description(
        incident=incident,
        summary="Triage summary",
        flags=[],
        insights=[],
    )

    assert "**GitHub Issue:**" not in description
