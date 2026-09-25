import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    AISummary,
    Chapter,
    DigitalFile,
    DocumentPage,
    Edition,
    ProcessingStatus,
    SpoilerMode,
    SummaryType,
)


def chapter(session: Session, chapter_id: uuid.UUID) -> Chapter | None:
    return session.scalar(
        select(Chapter)
        .where(Chapter.id == chapter_id)
        .options(joinedload(Chapter.edition).joinedload(Edition.book))
    )


def edition(session: Session, edition_id: uuid.UUID) -> Edition | None:
    return session.scalar(
        select(Edition)
        .where(Edition.id == edition_id)
        .options(joinedload(Edition.book))
    )


def chapters(session: Session, edition_id: uuid.UUID) -> list[Chapter]:
    return list(
        session.scalars(
            select(Chapter)
            .where(Chapter.edition_id == edition_id)
            .order_by(Chapter.chapter_number)
        ).all()
    )


def ready_file(session: Session, edition_id: uuid.UUID) -> DigitalFile | None:
    return session.scalar(
        select(DigitalFile)
        .where(
            DigitalFile.edition_id == edition_id,
            DigitalFile.processing_status == ProcessingStatus.READY,
        )
        .order_by(DigitalFile.uploaded_at.desc())
    )


def page_text(
    session: Session,
    file_id: uuid.UUID,
    start: int | None = None,
    end: int | None = None,
) -> str:
    statement = select(DocumentPage.content).where(DocumentPage.digital_file_id == file_id)
    if start is not None:
        statement = statement.where(DocumentPage.page_number >= start)
    if end is not None:
        statement = statement.where(DocumentPage.page_number <= end)
    return "\n\n".join(session.scalars(statement.order_by(DocumentPage.page_number)).all())


def get_summary(
    session: Session,
    *,
    edition_id: uuid.UUID,
    chapter_id: uuid.UUID | None,
    summary_type: SummaryType,
    spoiler_mode: SpoilerMode,
    lock: bool = False,
) -> AISummary | None:
    statement = select(AISummary).where(
        AISummary.edition_id == edition_id,
        AISummary.summary_type == summary_type,
        AISummary.spoiler_mode == spoiler_mode,
    )
    statement = (
        statement.where(AISummary.chapter_id == chapter_id)
        if chapter_id
        else statement.where(AISummary.chapter_id.is_(None))
    )
    if lock:
        statement = statement.with_for_update(of=AISummary)
    return session.scalar(statement)
