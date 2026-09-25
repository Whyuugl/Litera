"""phase 7 digital reader

Revision ID: d42af61c908e
Revises: b7619aaf3c24
Create Date: 2026-09-25 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d42af61c908e"
down_revision: Union[str, None] = "b7619aaf3c24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    processing_status = sa.Enum("UPLOADED", "PROCESSING", "READY", "FAILED", name="processing_status")
    processing_status.create(op.get_bind(), checkfirst=True)
    op.add_column("digital_files", sa.Column("storage_key", sa.String(), nullable=True))
    op.add_column("digital_files", sa.Column("original_filename", sa.String(), nullable=True))
    op.add_column("digital_files", sa.Column("mime_type", sa.String(), nullable=True))
    op.add_column("digital_files", sa.Column("allow_download", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("digital_files", sa.Column("processing_status", processing_status, server_default="UPLOADED", nullable=False))
    op.add_column("digital_files", sa.Column("processing_error", sa.Text(), nullable=True))
    op.add_column("digital_files", sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_digital_files_storage_key", "digital_files", ["storage_key"])

    op.create_table(
        "document_pages",
        sa.Column("digital_file_id", sa.Uuid(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), server_default="", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["digital_file_id"], ["digital_files.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("digital_file_id", "page_number"),
    )
    op.create_index("ix_document_pages_digital_file_id", "document_pages", ["digital_file_id"])
    op.create_table(
        "chapters",
        sa.Column("edition_id", sa.Uuid(), nullable=False),
        sa.Column("chapter_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("page_start", sa.Integer(), nullable=False),
        sa.Column("page_end", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["edition_id"], ["editions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("edition_id", "chapter_number"),
    )
    op.create_index("ix_chapters_edition_id", "chapters", ["edition_id"])
    op.create_table(
        "reading_progress",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("edition_id", sa.Uuid(), nullable=False),
        sa.Column("chapter_id", sa.Uuid(), nullable=True),
        sa.Column("progress_percentage", sa.Float(), server_default="0", nullable=False),
        sa.Column("current_page", sa.Integer(), server_default="1", nullable=False),
        sa.Column("position_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"]),
        sa.ForeignKeyConstraint(["edition_id"], ["editions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "edition_id"),
    )
    op.create_index("ix_reading_progress_user_id", "reading_progress", ["user_id"])
    op.create_index("ix_reading_progress_edition_id", "reading_progress", ["edition_id"])
    op.create_index("ix_reading_progress_user_last_read", "reading_progress", ["user_id", "last_read_at"])
    op.create_table(
        "bookmarks",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("edition_id", sa.Uuid(), nullable=False),
        sa.Column("chapter_id", sa.Uuid(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("position_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"]),
        sa.ForeignKeyConstraint(["edition_id"], ["editions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bookmarks_user_id", "bookmarks", ["user_id"])
    op.create_index("ix_bookmarks_edition_id", "bookmarks", ["edition_id"])
    op.create_index("ix_bookmarks_user_edition", "bookmarks", ["user_id", "edition_id"])


def downgrade() -> None:
    op.drop_table("bookmarks")
    op.drop_table("reading_progress")
    op.drop_table("chapters")
    op.drop_table("document_pages")
    op.drop_constraint("uq_digital_files_storage_key", "digital_files", type_="unique")
    for column in ("processed_at", "processing_error", "processing_status", "allow_download", "mime_type", "original_filename", "storage_key"):
        op.drop_column("digital_files", column)
    sa.Enum(name="processing_status").drop(op.get_bind(), checkfirst=True)
