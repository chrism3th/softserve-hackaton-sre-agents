"""CRUD operations for the prompt_injection_log table."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud.base import CRUDBase
from app.db.models.prompt_injection_log import PromptInjectionLog
from app.tickets.models import GuardrailFlag, IncidentSource


class CRUDPromptInjectionLog(CRUDBase[PromptInjectionLog]):
    async def log_attempt(
        self,
        session: AsyncSession,
        *,
        source: IncidentSource,
        reporter: str | None,
        raw_input: str,
        flags: list[GuardrailFlag],
        blocked: bool,
    ) -> PromptInjectionLog:
        return await self.create(
            session,
            source=source.value,
            reporter=reporter,
            raw_input=raw_input,
            flags=[f.value for f in flags],
            blocked=blocked,
        )


crud_prompt_injection_log = CRUDPromptInjectionLog(PromptInjectionLog)
