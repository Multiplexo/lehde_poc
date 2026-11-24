"""LV positions, check results, project chat and subcontractors.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "project",
        sa.Column("checks", postgresql.JSONB(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "project", sa.Column("checks_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_table(
        "lv_position",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.Column("sort_index", sa.Integer(), nullable=False),
        sa.Column("oz", sa.Text(), nullable=True),
        sa.Column("short_text", sa.Text(), nullable=False),
        sa.Column("long_text", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("quantity_formula", sa.Text(), nullable=True),
        sa.Column("trade_code", sa.Text(), nullable=True),
        sa.Column("trade_source", sa.Text(), nullable=True),
        sa.Column("trade_confidence", sa.Float(), nullable=True),
        sa.Column("source", postgresql.JSONB(), nullable=True),
        sa.Column("assumption", sa.Text(), nullable=True),
        sa.Column("included", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_lv_position_project_id", "lv_position", ["project_id"])
    op.create_table(
        "chat_message",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sources", postgresql.JSONB(), nullable=False),
        sa.Column("unsupported", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_chat_message_project_id", "chat_message", ["project_id"])
    op.create_index("ix_chat_message_created_at", "chat_message", ["created_at"])
    op.create_table(
        "subcontractor",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("trade_codes", postgresql.JSONB(), nullable=False),
        sa.Column("postal_code", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("contact", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("subcontractor")
    op.drop_table("chat_message")
    op.drop_table("lv_position")
    op.drop_column("project", "checks_at")
    op.drop_column("project", "checks")
