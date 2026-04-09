"""CRUD operations for the agent_invocations table."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud.base import CRUDBase
from app.db.models.agent_invocation import AgentInvocation


class CRUDAgentInvocation(CRUDBase[AgentInvocation]):
    async def log_invocation(
        self,
        session: AsyncSession,
        *,
        agent_name: str,
        input: str,
        output: str | None = None,
        tokens_used: int = 0,
    ) -> AgentInvocation:
        return await self.create(
            session,
            agent_name=agent_name,
            input=input,
            output=output,
            tokens_used=tokens_used,
        )


crud_agent_invocation = CRUDAgentInvocation(AgentInvocation)
