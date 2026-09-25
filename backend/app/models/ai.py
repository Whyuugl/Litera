import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.catalog import Edition, UUIDTimestampMixin
from app.models.digital import Chapter


class SummaryType(str, enum.Enum):
    BOOK = "BOOK"
    CHAPTER = "CHAPTER"


class SummaryStatus(str, enum.Enum):
    PENDING = "PENDING"
    READY = "READY"
    FAILED = "FAILED"


class SpoilerMode(str, enum.Enum):
    NONE = "NONE"
    SPOILER_FREE = "SPOILER_FREE"


class AISummary(UUIDTimestampMixin, Base):
    __tablename__ = "ai_summaries"
    __table_args__ = (
        Index(
            "uq_ai_summaries_book",
            "edition_id",
            "summary_type",
            "spoiler_mode",
            unique=True,
            postgresql_where=text("chapter_id IS NULL"),
            sqlite_where=text("chapter_id IS NULL"),
        ),
        Index(
            "uq_ai_summaries_chapter",
            "chapter_id",
            "summary_type",
            "spoiler_mode",
            unique=True,
            postgresql_where=text("chapter_id IS NOT NULL"),
            sqlite_where=text("chapter_id IS NOT NULL"),
        ),
    )

    edition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("editions.id", ondelete="CASCADE"), index=True
    )
    chapter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), index=True
    )
    summary_type: Mapped[SummaryType] = mapped_column(
        Enum(SummaryType, name="ai_summary_type")
    )
    spoiler_mode: Mapped[SpoilerMode] = mapped_column(
        Enum(SpoilerMode, name="ai_spoiler_mode"), default=SpoilerMode.NONE
    )
    content: Mapped[Optional[str]] = mapped_column(Text)
    source_content_hash: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(255))
    status: Mapped[SummaryStatus] = mapped_column(
        Enum(SummaryStatus, name="ai_summary_status"), default=SummaryStatus.PENDING
    )
    error_message: Mapped[Optional[str]] = mapped_column(String(1000))
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    edition: Mapped[Edition] = relationship(back_populates="ai_summaries")
    chapter: Mapped[Optional[Chapter]] = relationship(back_populates="ai_summaries")
