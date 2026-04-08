"""Persistence helpers for the ticket pipeline."""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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
    await session.execute(
        text(
            """
            INSERT INTO prompt_injection_log
                (source, reporter, raw_input, flags, blocked)
            VALUES (:source, :reporter, :raw_input, CAST(:flags AS JSONB), :blocked)
            """
        ),
        {
            "source": source.value,
            "reporter": reporter,
            "raw_input": raw_input,
            "flags": json.dumps([f.value for f in flags]),
            "blocked": blocked,
        },
    )
    await session.commit()
