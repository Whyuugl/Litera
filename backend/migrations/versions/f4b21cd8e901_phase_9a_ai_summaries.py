"""phase 9a ai summaries

Revision ID: f4b21cd8e901
Revises: a81e04c73b52
Create Date: 2026-09-25 16:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f4b21cd8e901"
down_revision: Union[str, None] = "a81e04c73b52"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    summary_type = postgresql.ENUM("BOOK", "CHAPTER", name="ai_summary_type", create_type=False)
    spoiler_mode = postgresql.ENUM("NONE", "SPOILER_FREE", name="ai_spoiler_mode", create_type=False)
    summary_status = postgresql.ENUM("PENDING", "READY", "FAILED", name="ai_summary_status", create_type=False)
    for enum in (summary_type, spoiler_mode, summary_status):
        enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "ai_summaries",
        sa.Column("edition_id", sa.Uuid(), nullable=False),
        sa.Column("chapter_id", sa.Uuid(), nullable=True),
        sa.Column("summary_type", summary_type, nullable=False),
        sa.Column("spoiler_mode", spoiler_mode, server_default="NONE", nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("source_content_hash", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("status", summary_status, server_default="PENDING", nullable=False),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["edition_id"], ["editions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_summaries_edition_id", "ai_summaries", ["edition_id"])
    op.create_index("ix_ai_summaries_chapter_id", "ai_summaries", ["chapter_id"])
    op.create_index(
        "uq_ai_summaries_book",
        "ai_summaries",
        ["edition_id", "summary_type", "spoiler_mode"],
        unique=True,
        postgresql_where=sa.text("chapter_id IS NULL"),
    )
    op.create_index(
        "uq_ai_summaries_chapter",
        "ai_summaries",
        ["chapter_id", "summary_type", "spoiler_mode"],
        unique=True,
        postgresql_where=sa.text("chapter_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_table("ai_summaries")
    for name in ("ai_summary_status", "ai_spoiler_mode", "ai_summary_type"):
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
