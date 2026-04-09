"""Persistence helpers for the ticket pipeline."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud.prompt_injection_log import crud_prompt_injection_log
from app.tickets.models import GuardrailFlag, IncidentSource


async def log_injection_attempt(
    session: AsyncSession,
    *,
    source: IncidentSource,
    reporter: str | None,
    raw_input: str,
    flags: list[GuardrailFlag],
    blocked: bool,
) -> None:
    await crud_prompt_injection_log.log_attempt(
        session,
        source=source,
        reporter=reporter,
        raw_input=raw_input,
        flags=flags,
        blocked=blocked,
    )
