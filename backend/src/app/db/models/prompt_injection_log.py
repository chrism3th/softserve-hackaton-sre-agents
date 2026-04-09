"""SQLAlchemy model for the prompt injection audit log.

Records every guardrail trigger so security events can be reviewed
and anomaly patterns detected offline.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PromptInjectionLog(Base):
    """One row per guardrail trigger in the ticket pipeline."""

    __tablename__ = "prompt_injection_log"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    reporter: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_input: Mapped[str] = mapped_column(Text, nullable=False)
    flags: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    blocked: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_pil_reporter", "reporter"),
        Index("idx_pil_created_at", "created_at"),
    )
