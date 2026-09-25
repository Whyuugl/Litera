import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import Bookmark, Chapter, DigitalFile, DocumentPage, Edition, ProcessingStatus, ReadingProgress


def get_file(session: Session, file_id: uuid.UUID, *, for_update: bool = False) -> DigitalFile | None:
    statement = select(DigitalFile).where(DigitalFile.id == file_id)
    if for_update:
        statement = statement.with_for_update(of=DigitalFile)
    return session.scalar(statement)


def get_edition_file(session: Session, edition_id: uuid.UUID, *, ready_only: bool = False) -> DigitalFile | None:
    statement = select(DigitalFile).where(
        DigitalFile.edition_id == edition_id,
        DigitalFile.storage_key.is_not(None),
    )
    if ready_only:
        statement = statement.where(DigitalFile.processing_status == ProcessingStatus.READY)
    return session.scalar(statement.order_by(DigitalFile.uploaded_at.desc()))


def page_count(session: Session, file_id: uuid.UUID) -> int:
    return session.scalar(
        select(func.count()).select_from(DocumentPage).where(DocumentPage.digital_file_id == file_id)
    ) or 0


def list_chapters(session: Session, edition_id: uuid.UUID) -> list[Chapter]:
    return list(session.scalars(
        select(Chapter).where(Chapter.edition_id == edition_id).order_by(Chapter.chapter_number)
    ).all())


def get_progress(session: Session, user_id: uuid.UUID, edition_id: uuid.UUID) -> ReadingProgress | None:
    return session.scalar(select(ReadingProgress).where(
        ReadingProgress.user_id == user_id, ReadingProgress.edition_id == edition_id
    ))


def list_progress(session: Session, user_id: uuid.UUID) -> list[ReadingProgress]:
    return list(session.scalars(
        select(ReadingProgress)
        .where(ReadingProgress.user_id == user_id)
        .options(
            joinedload(ReadingProgress.edition).joinedload(Edition.book),
            joinedload(ReadingProgress.chapter),
        )
        .order_by(ReadingProgress.last_read_at.desc())
    ).unique().all())


def has_reader_data(session: Session, edition_id: uuid.UUID) -> bool:
    progress = session.scalar(select(ReadingProgress.id).where(ReadingProgress.edition_id == edition_id).limit(1))
    bookmark = session.scalar(select(Bookmark.id).where(Bookmark.edition_id == edition_id).limit(1))
    return progress is not None or bookmark is not None


def get_bookmark(session: Session, bookmark_id: uuid.UUID, user_id: uuid.UUID) -> Bookmark | None:
    return session.scalar(select(Bookmark).where(Bookmark.id == bookmark_id, Bookmark.user_id == user_id))


def list_bookmarks(session: Session, user_id: uuid.UUID, edition_id: uuid.UUID) -> list[Bookmark]:
    return list(session.scalars(select(Bookmark).where(
        Bookmark.user_id == user_id, Bookmark.edition_id == edition_id
    ).order_by(Bookmark.page_number, Bookmark.created_at)).all())
