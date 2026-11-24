"""Projects, documents and feedback.

Revision ID: 0001
Revises:
Create Date: 2026-11-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("step", sa.Text(), nullable=True),
        sa.Column("percent", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("analysis", postgresql.JSONB(), nullable=True),
        sa.Column("questions", postgresql.JSONB(), nullable=False),
    )
    op.create_index("ix_project_created_at", "project", ["created_at"])
    op.create_table(
        "document",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("ocr_page_count", sa.Integer(), nullable=False),
        sa.Column("pages", postgresql.JSONB(), nullable=False),
        sa.Column("doc_type", sa.Text(), nullable=True),
        sa.Column("doc_type_source", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("revision", sa.Text(), nullable=True),
        sa.Column("document_date", sa.Text(), nullable=True),
        sa.Column("meta_source", sa.Text(), nullable=True),
        sa.Column("classification_confidence", sa.Float(), nullable=True),
        sa.Column("plans", postgresql.JSONB(), nullable=False),
    )
    op.create_index("ix_document_project_id", "document", ["project_id"])
    op.create_table(
        "feedback",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("project.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("user_name", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("screenshot_key", sa.Text(), nullable=True),
        sa.Column("triage", postgresql.JSONB(), nullable=True),
        sa.Column("forwarded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_feedback_created_at", "feedback", ["created_at"])


def downgrade() -> None:
    op.drop_table("feedback")
    op.drop_table("document")
    op.drop_table("project")
