"""phase 9c rag infrastructure

Revision ID: c8f7219a64de
Revises: f4b21cd8e901
Create Date: 2026-09-29 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql


revision: str = "c8f7219a64de"
down_revision: Union[str, None] = "f4b21cd8e901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    rag_status = postgresql.ENUM(
        "NOT_INDEXED", "INDEXING", "READY", "FAILED", "STALE",
        name="rag_status", create_type=False,
    )
    rag_status.create(op.get_bind(), checkfirst=True)
    op.add_column("digital_files", sa.Column("rag_status", rag_status, server_default="NOT_INDEXED", nullable=False))
    op.add_column("digital_files", sa.Column("rag_error", sa.Text(), nullable=True))
    op.add_column("digital_files", sa.Column("rag_indexed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("digital_files", sa.Column("rag_embedding_model", sa.String(), nullable=True))
    op.create_table(
        "book_chunks",
        sa.Column("digital_file_id", sa.Uuid(), nullable=False),
        sa.Column("edition_id", sa.Uuid(), nullable=False),
        sa.Column("chapter_id", sa.Uuid(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=False),
        sa.Column("page_end", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("embedding_model", sa.String(length=255), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["digital_file_id"], ["digital_files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["edition_id"], ["editions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("digital_file_id", "chunk_index"),
    )
    op.create_index("ix_book_chunks_digital_file_id", "book_chunks", ["digital_file_id"])
    op.create_index("ix_book_chunks_edition_id", "book_chunks", ["edition_id"])
    op.create_index("ix_book_chunks_chapter_id", "book_chunks", ["chapter_id"])
    op.create_index("ix_book_chunks_content_hash", "book_chunks", ["content_hash"])
    op.create_index("ix_book_chunks_edition_file", "book_chunks", ["edition_id", "digital_file_id"])


def downgrade() -> None:
    op.drop_table("book_chunks")
    for column in ("rag_embedding_model", "rag_indexed_at", "rag_error", "rag_status"):
        op.drop_column("digital_files", column)
    sa.Enum(name="rag_status").drop(op.get_bind(), checkfirst=True)
