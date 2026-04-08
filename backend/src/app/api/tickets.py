"""Incident ingest endpoints.

Two entry points:
    POST /api/v1/tickets/ingest          — direct API payload
    POST /api/v1/tickets/github-webhook  — GitHub `issues` webhook

Both normalize to an ``IncidentDTO`` and run it through the Ticket
Orchestrator agent.
"""

from __future__ import annotations

import hashlib
import hmac

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.agents.ticket_orchestrator import TicketOrchestratorAgent
from app.config import get_settings
from app.core.logging import get_logger
from app.tickets.models import (
    IncidentDTO,
    IncidentImage,
    IncidentSource,
    OrchestratorResult,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/tickets", tags=["tickets"])
_orchestrator = TicketOrchestratorAgent()


class IngestPayload(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    body: str = Field(default="", max_length=20_000)
    reporter: str | None = None
    images: list[IncidentImage] = Field(default_factory=list)


@router.post(
    "/ingest",
    response_model=OrchestratorResult,
    summary="Ingest an incident report (direct API)",
)
async def ingest(payload: IngestPayload) -> OrchestratorResult:
    incident = IncidentDTO(
        title=payload.title,
        body=payload.body,
        reporter=payload.reporter,
        source=IncidentSource.api,
        images=payload.images,
    )
    return await _orchestrator.orchestrate(incident)


@router.post(
    "/github-webhook",
    response_model=OrchestratorResult | dict,
    summary="GitHub `issues` webhook",
)
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
) -> OrchestratorResult | dict:
    body = await request.body()
    _verify_signature(body, x_hub_signature_256)

    if x_github_event != "issues":
        return {"ignored": True, "event": x_github_event}

    payload = await request.json()
    action = payload.get("action")
    if action not in {"opened", "reopened"}:
        return {"ignored": True, "action": action}

    issue = payload.get("issue", {})
    user = issue.get("user", {})
    incident = IncidentDTO(
        title=issue.get("title", "Untitled GitHub issue"),
        body=issue.get("body") or "",
        reporter=user.get("login"),
        source=IncidentSource.github_issue,
        images=_extract_images(issue.get("body") or ""),
        raw={"github_issue_url": issue.get("html_url")},
    )
    return await _orchestrator.orchestrate(incident)


def _verify_signature(body: bytes, signature: str | None) -> None:
    secret = get_settings().github_webhook_secret
    if not secret:
        # Dev mode: no secret configured → accept (with a warning).
        logger.warning("github_webhook.no_secret_configured")
        return
    if not signature or not signature.startswith("sha256="):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing signature",
        )
    expected = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid signature",
        )


def _extract_images(markdown_body: str) -> list[IncidentImage]:
    """Pull image URLs from a GitHub issue body.

    Handles three real-world cases:
    - markdown ``![alt](url)``
    - HTML ``<img src="url">`` (GitHub's drag-and-drop default)
    - bare ``https://...{png,jpg,gif,webp}`` URLs
    - GitHub user-attachments URLs (no extension):
      ``https://github.com/user-attachments/assets/<uuid>``
    """
    import re

    urls: list[str] = []
    urls += re.findall(r"!\[[^\]]*\]\(([^)\s]+)", markdown_body)
    urls += re.findall(
        r"""<img[^>]*\bsrc\s*=\s*["']([^"']+)["']""",
        markdown_body,
        flags=re.IGNORECASE,
    )
    urls += re.findall(
        r"https?://\S+?\.(?:png|jpe?g|gif|webp)",
        markdown_body,
        flags=re.IGNORECASE,
    )
    urls += re.findall(
        r"https?://github\.com/user-attachments/assets/[A-Za-z0-9-]+",
        markdown_body,
        flags=re.IGNORECASE,
    )
    seen: set[str] = set()
    out: list[IncidentImage] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(IncidentImage(url=u))
    return out
