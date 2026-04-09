"""initial schema: agent_invocations + prompt_injection_log

Revision ID: 0001
Revises:
Create Date: 2026-04-08

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_invocations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("agent_name", sa.Text(), nullable=False),
        sa.Column("input", sa.Text(), nullable=False),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column(
            "tokens_used",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_invocations_created_at",
        "agent_invocations",
        ["created_at"],
    )

    op.create_table(
        "prompt_injection_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("reporter", sa.String(length=255), nullable=True),
        sa.Column("raw_input", sa.Text(), nullable=False),
        sa.Column(
            "flags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("blocked", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_pil_reporter", "prompt_injection_log", ["reporter"])
    op.create_index("idx_pil_created_at", "prompt_injection_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_pil_created_at", table_name="prompt_injection_log")
    op.drop_index("idx_pil_reporter", table_name="prompt_injection_log")
    op.drop_table("prompt_injection_log")

    op.drop_index("idx_invocations_created_at", table_name="agent_invocations")
    op.drop_table("agent_invocations")
