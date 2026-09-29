import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import BookChunk, DigitalFile, DocumentPage, Chapter


def file(session: Session, file_id: uuid.UUID, *, lock: bool = False) -> DigitalFile | None:
    statement = select(DigitalFile).where(DigitalFile.id == file_id)
    if lock:
        statement = statement.with_for_update(of=DigitalFile)
    return session.scalar(statement)


def edition_file(session: Session, edition_id: uuid.UUID) -> DigitalFile | None:
    return session.scalar(
        select(DigitalFile)
        .where(DigitalFile.edition_id == edition_id)
        .order_by(DigitalFile.uploaded_at.desc())
    )


def pages(session: Session, file_id: uuid.UUID) -> list[DocumentPage]:
    return list(session.scalars(
        select(DocumentPage)
        .where(DocumentPage.digital_file_id == file_id)
        .order_by(DocumentPage.page_number)
    ))


def chapters(session: Session, edition_id: uuid.UUID) -> list[Chapter]:
    return list(session.scalars(
        select(Chapter)
        .where(Chapter.edition_id == edition_id)
        .order_by(Chapter.page_start, Chapter.chapter_number)
    ))


def chunks(session: Session, file_id: uuid.UUID) -> list[BookChunk]:
    return list(session.scalars(
        select(BookChunk)
        .where(BookChunk.digital_file_id == file_id)
        .options(joinedload(BookChunk.chapter))
        .order_by(BookChunk.chunk_index)
    ))


def edition_chunks(session: Session, edition_id: uuid.UUID) -> list[BookChunk]:
    return list(session.scalars(
        select(BookChunk)
        .where(BookChunk.edition_id == edition_id)
        .options(joinedload(BookChunk.chapter))
    ))


def chunk_count(session: Session, file_id: uuid.UUID) -> int:
    return session.scalar(
        select(func.count()).select_from(BookChunk).where(BookChunk.digital_file_id == file_id)
    ) or 0
