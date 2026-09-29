import uuid
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.catalog import DigitalFile, Edition, UUIDTimestampMixin
from app.models.digital import Chapter


EMBEDDING_DIMENSIONS = 1536


class BookChunk(UUIDTimestampMixin, Base):
    __tablename__ = "book_chunks"
    __table_args__ = (
        UniqueConstraint("digital_file_id", "chunk_index"),
        Index("ix_book_chunks_edition_file", "edition_id", "digital_file_id"),
    )

    digital_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("digital_files.id", ondelete="CASCADE"), index=True
    )
    edition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("editions.id", ondelete="CASCADE"), index=True
    )
    chapter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("chapters.id", ondelete="SET NULL"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    page_start: Mapped[int] = mapped_column(Integer)
    page_end: Mapped[int] = mapped_column(Integer)
    token_count: Mapped[Optional[int]] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    embedding_model: Mapped[str] = mapped_column(String(255))

    digital_file: Mapped[DigitalFile] = relationship(back_populates="chunks")
    edition: Mapped[Edition] = relationship()
    chapter: Mapped[Optional[Chapter]] = relationship(back_populates="chunks")
