import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.catalog import DigitalFile, Edition, UUIDTimestampMixin, User


json_type = JSON().with_variant(JSONB(), "postgresql")


class DocumentPage(UUIDTimestampMixin, Base):
    __tablename__ = "document_pages"
    __table_args__ = (UniqueConstraint("digital_file_id", "page_number"),)

    digital_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("digital_files.id", ondelete="CASCADE"), index=True
    )
    page_number: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text, default="", server_default="")

    digital_file: Mapped[DigitalFile] = relationship(back_populates="pages")


class Chapter(UUIDTimestampMixin, Base):
    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("edition_id", "chapter_number"),)

    edition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("editions.id"), index=True)
    chapter_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String)
    content: Mapped[Optional[str]] = mapped_column(Text)
    page_start: Mapped[int] = mapped_column(Integer)
    page_end: Mapped[int] = mapped_column(Integer)

    edition: Mapped[Edition] = relationship(back_populates="chapters")
    quizzes: Mapped[list["Quiz"]] = relationship(back_populates="chapter")
    ai_summaries: Mapped[list["AISummary"]] = relationship(back_populates="chapter")


class ReadingProgress(UUIDTimestampMixin, Base):
    __tablename__ = "reading_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "edition_id"),
        Index("ix_reading_progress_user_last_read", "user_id", "last_read_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    edition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("editions.id"), index=True)
    chapter_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("chapters.id"))
    progress_percentage: Mapped[float] = mapped_column(Float, default=0, server_default="0")
    current_page: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    position_data: Mapped[Optional[dict[str, Any]]] = mapped_column(json_type)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="reading_progress")
    edition: Mapped[Edition] = relationship(back_populates="reading_progress")
    chapter: Mapped[Optional[Chapter]] = relationship()


class Bookmark(UUIDTimestampMixin, Base):
    __tablename__ = "bookmarks"
    __table_args__ = (Index("ix_bookmarks_user_edition", "user_id", "edition_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    edition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("editions.id"), index=True)
    chapter_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("chapters.id"))
    page_number: Mapped[int] = mapped_column(Integer)
    position_data: Mapped[Optional[dict[str, Any]]] = mapped_column(json_type)
    note: Mapped[Optional[str]] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="bookmarks")
    edition: Mapped[Edition] = relationship(back_populates="bookmarks")
    chapter: Mapped[Optional[Chapter]] = relationship()
