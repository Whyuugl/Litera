import os
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from fastapi import UploadFile
from pypdf import PdfReader
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    AccessLevel,
    Bookmark,
    Chapter,
    DigitalFile,
    DigitalFileType,
    DocumentPage,
    Edition,
    ProcessingStatus,
    ReadingProgress,
    Quiz,
    AISummary,
    SummaryStatus,
    SummaryType,
    User,
)
from app.repositories import digital as repository
from app.schemas.digital import BookmarkCreate, BookmarkUpdate, ChapterCreate, ChapterUpdate, ProgressUpdate
from app.services.memberships import ActiveMembershipRequired, require_active_membership
from app.services.storage import FileTooLarge, StorageError, storage


class DigitalNotFound(Exception):
    pass


class DigitalConflict(Exception):
    pass


class DigitalAccessDenied(Exception):
    pass


class InvalidPdf(Exception):
    pass


@lru_cache
def max_book_file_size() -> int:
    try:
        value = int(os.getenv("MAX_BOOK_FILE_SIZE_MB", "50"))
    except ValueError as exc:
        raise RuntimeError("MAX_BOOK_FILE_SIZE_MB must be an integer") from exc
    if value <= 0:
        raise RuntimeError("MAX_BOOK_FILE_SIZE_MB must be positive")
    return value * 1024 * 1024


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _validate_upload(upload: UploadFile) -> None:
    if not upload.filename or Path(upload.filename).suffix.lower() != ".pdf":
        raise InvalidPdf("Only PDF files are supported")
    if upload.content_type not in {"application/pdf", "application/octet-stream"}:
        raise InvalidPdf("The uploaded file is not a PDF")


def _extract(path: Path) -> tuple[list[str], list[tuple[int, str, int, int]]]:
    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise InvalidPdf("Encrypted PDFs are not supported")
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
        if not pages:
            raise InvalidPdf("The PDF has no pages")
        starts: list[tuple[int, str]] = []

        def visit(items) -> None:
            for item in items:
                if isinstance(item, list):
                    visit(item)
                    continue
                try:
                    page = reader.get_destination_page_number(item) + 1
                    title = str(item.title).strip()
                except Exception:
                    continue
                if title and page >= 1:
                    starts.append((page, title[:500]))

        try:
            visit(reader.outline)
        except Exception:
            starts = []
        unique = sorted({page: title for page, title in starts}.items())
        if not unique:
            return pages, [(1, "Full Document", 1, len(pages))]
        chapters = []
        for index, (page, title) in enumerate(unique, 1):
            end = unique[index][0] - 1 if index < len(unique) else len(pages)
            if page <= len(pages):
                chapters.append((len(chapters) + 1, title, page, max(page, end)))
        return pages, chapters or [(1, "Full Document", 1, len(pages))]
    except InvalidPdf:
        raise
    except Exception as exc:
        raise InvalidPdf("PDF text extraction failed") from exc


def _replace_extracted(
    session: Session,
    file: DigitalFile,
    pages: list[str],
    chapters: list[tuple[int, str, int, int]],
) -> None:
    session.execute(delete(DocumentPage).where(DocumentPage.digital_file_id == file.id))
    session.execute(delete(Chapter).where(Chapter.edition_id == file.edition_id))
    session.add_all([
        DocumentPage(digital_file_id=file.id, page_number=index, content=content)
        for index, content in enumerate(pages, 1)
    ])
    session.add_all([
        Chapter(
            edition_id=file.edition_id,
            chapter_number=number,
            title=title,
            page_start=start,
            page_end=end,
        )
        for number, title, start, end in chapters
    ])


def process_document(session: Session, file: DigitalFile) -> DigitalFile:
    if not file.storage_key:
        raise DigitalConflict("This record has no stored PDF")
    file.processing_status = ProcessingStatus.PROCESSING
    file.processing_error = None
    session.commit()
    try:
        pages, chapters = _extract(storage.path(file.storage_key))
        _replace_extracted(session, file, pages, chapters)
        file.processing_status = ProcessingStatus.READY
        file.processed_at = _now()
        session.commit()
    except Exception as exc:
        session.rollback()
        file = session.get(DigitalFile, file.id)
        file.processing_status = ProcessingStatus.FAILED
        file.processing_error = str(exc)[:1000] or "Document processing failed"
        file.processed_at = None
        session.commit()
    return file


def upload_pdf(
    session: Session,
    edition_id: uuid.UUID,
    upload: UploadFile,
    access_level: AccessLevel,
    allow_download: bool,
    admin: User,
) -> DigitalFile:
    _validate_upload(upload)
    if not session.get(Edition, edition_id):
        raise DigitalNotFound
    if repository.get_edition_file(session, edition_id):
        raise DigitalConflict("This edition already has a PDF; use Replace")
    try:
        key, size = storage.save(upload.file, edition_id, max_book_file_size())
    except FileTooLarge as exc:
        raise InvalidPdf("PDF exceeds the configured file-size limit") from exc
    with storage.open(key) as saved:
        valid_signature = saved.read(5) == b"%PDF-"
    if not valid_signature:
        storage.delete(key)
        raise InvalidPdf("File signature is not a valid PDF")
    file = DigitalFile(
        id=uuid.uuid4(),
        edition_id=edition_id,
        file_url="",
        storage_key=key,
        original_filename=Path(upload.filename).name,
        mime_type="application/pdf",
        file_type=DigitalFileType.PDF,
        file_size=size,
        access_level=access_level,
        allow_download=allow_download,
        processing_status=ProcessingStatus.UPLOADED,
        uploaded_by=admin.id,
    )
    file.file_url = f"/api/v1/digital-files/{file.id}/content"
    session.add(file)
    try:
        session.commit()
    except Exception:
        session.rollback()
        storage.delete(key)
        raise
    return process_document(session, file)


def replace_pdf(session: Session, file_id: uuid.UUID, upload: UploadFile, admin: User) -> DigitalFile:
    _validate_upload(upload)
    file = repository.get_file(session, file_id, for_update=True)
    if not file:
        raise DigitalNotFound
    if repository.has_reader_data(session, file.edition_id):
        raise DigitalConflict("Replacement is blocked while reading progress or bookmarks exist")
    try:
        key, size = storage.save(upload.file, file.edition_id, max_book_file_size())
        with storage.open(key) as saved:
            if saved.read(5) != b"%PDF-":
                raise InvalidPdf("File signature is not a valid PDF")
        pages, chapters = _extract(storage.path(key))
    except Exception:
        if "key" in locals():
            storage.delete(key)
        raise
    old_key = file.storage_key
    try:
        _replace_extracted(session, file, pages, chapters)
        file.storage_key = key
        file.original_filename = Path(upload.filename).name
        file.mime_type = "application/pdf"
        file.file_size = size
        file.uploaded_by = admin.id
        file.uploaded_at = _now()
        file.processing_status = ProcessingStatus.READY
        file.processing_error = None
        file.processed_at = _now()
        session.commit()
    except Exception:
        session.rollback()
        storage.delete(key)
        raise
    if old_key:
        storage.delete(old_key)
    return file


def retry_processing(session: Session, file_id: uuid.UUID) -> DigitalFile:
    file = repository.get_file(session, file_id, for_update=True)
    if not file:
        raise DigitalNotFound
    return process_document(session, file)


def authorize_file(session: Session, file: DigitalFile, user: User | None) -> None:
    if file.processing_status != ProcessingStatus.READY or not file.storage_key:
        raise DigitalNotFound
    if file.access_level == AccessLevel.PUBLIC:
        return
    if not user:
        raise DigitalAccessDenied
    if file.access_level == AccessLevel.MEMBER:
        try:
            require_active_membership(session, user)
        except ActiveMembershipRequired as exc:
            raise DigitalAccessDenied from exc


def get_reader(session: Session, edition_id: uuid.UUID, user: User | None):
    file = repository.get_edition_file(session, edition_id, ready_only=True)
    if not file:
        raise DigitalNotFound
    authorize_file(session, file, user)
    edition = session.get(Edition, edition_id)
    return {
        "edition_id": edition_id,
        "digital_file_id": file.id,
        "access_level": file.access_level,
        "processing_status": file.processing_status,
        "page_count": repository.page_count(session, file.id),
        "book": edition.book,
        "chapters": repository.list_chapters(session, edition_id),
        "learning_available": bool(session.scalar(
            select(Quiz.id)
            .join(Chapter, Chapter.id == Quiz.chapter_id)
            .where(Chapter.edition_id == edition_id, Quiz.is_published.is_(True))
            .limit(1)
        )),
        "summary_chapter_ids": list(session.scalars(
            select(AISummary.chapter_id).where(
                AISummary.edition_id == edition_id,
                AISummary.summary_type == SummaryType.CHAPTER,
                AISummary.status == SummaryStatus.READY,
                AISummary.chapter_id.is_not(None),
            )
        ).all()),
    }


def get_content_file(session: Session, file_id: uuid.UUID, user: User | None) -> tuple[DigitalFile, Path]:
    file = repository.get_file(session, file_id)
    if not file:
        raise DigitalNotFound
    authorize_file(session, file, user)
    return file, storage.path(file.storage_key)


def delete_file(session: Session, file_id: uuid.UUID) -> None:
    file = repository.get_file(session, file_id, for_update=True)
    if not file:
        raise DigitalNotFound
    if repository.has_reader_data(session, file.edition_id):
        raise DigitalConflict("Delete bookmarks and reading progress before deleting this PDF")
    key = file.storage_key
    session.execute(delete(Chapter).where(Chapter.edition_id == file.edition_id))
    session.delete(file)
    session.commit()
    if key:
        storage.delete(key)


def get_progress(session: Session, edition_id: uuid.UUID, user: User):
    return repository.get_progress(session, user.id, edition_id)


def list_progress(session: Session, user: User) -> list[dict]:
    return [
        {
            **{column: getattr(item, column) for column in (
                "id", "user_id", "edition_id", "chapter_id", "progress_percentage",
                "current_page", "position_data", "started_at", "last_read_at", "completed_at",
            )},
            "book": item.edition.book,
            "chapter": item.chapter,
        }
        for item in repository.list_progress(session, user.id)
    ]


def save_progress(session: Session, edition_id: uuid.UUID, data: ProgressUpdate, user: User):
    file = repository.get_edition_file(session, edition_id, ready_only=True)
    if not file:
        raise DigitalNotFound
    authorize_file(session, file, user)
    total = repository.page_count(session, file.id)
    if not total or data.current_page > total:
        raise DigitalConflict("Page is outside this document")
    if data.chapter_id:
        chapter = session.scalar(select(Chapter).where(Chapter.id == data.chapter_id, Chapter.edition_id == edition_id))
        if not chapter:
            raise DigitalConflict("Chapter does not belong to this edition")
    now = _now()
    progress = repository.get_progress(session, user.id, edition_id)
    if not progress:
        progress = ReadingProgress(user_id=user.id, edition_id=edition_id, started_at=now, last_read_at=now)
        session.add(progress)
    progress.current_page = data.current_page
    progress.chapter_id = data.chapter_id
    progress.position_data = data.position_data
    progress.progress_percentage = round(data.current_page / total * 100, 2)
    progress.last_read_at = now
    progress.completed_at = now if data.current_page == total else None
    session.commit()
    session.refresh(progress)
    return progress


def list_bookmarks(session: Session, edition_id: uuid.UUID, user: User):
    return repository.list_bookmarks(session, user.id, edition_id)


def create_bookmark(session: Session, data: BookmarkCreate, user: User):
    file = repository.get_edition_file(session, data.edition_id, ready_only=True)
    if not file:
        raise DigitalNotFound
    authorize_file(session, file, user)
    total = repository.page_count(session, file.id)
    if data.page_number > total:
        raise DigitalConflict("Page is outside this document")
    if data.chapter_id and not session.scalar(select(Chapter.id).where(Chapter.id == data.chapter_id, Chapter.edition_id == data.edition_id)):
        raise DigitalConflict("Chapter does not belong to this edition")
    bookmark = Bookmark(user_id=user.id, **data.model_dump())
    session.add(bookmark)
    session.commit()
    session.refresh(bookmark)
    return bookmark


def update_bookmark(session: Session, bookmark_id: uuid.UUID, data: BookmarkUpdate, user: User):
    bookmark = repository.get_bookmark(session, bookmark_id, user.id)
    if not bookmark:
        raise DigitalNotFound
    bookmark.note = data.note.strip() or None if data.note is not None else None
    session.commit()
    return bookmark


def delete_bookmark(session: Session, bookmark_id: uuid.UUID, user: User) -> None:
    bookmark = repository.get_bookmark(session, bookmark_id, user.id)
    if not bookmark:
        raise DigitalNotFound
    session.delete(bookmark)
    session.commit()


def list_chapters(session: Session, edition_id: uuid.UUID):
    if not session.get(Edition, edition_id):
        raise DigitalNotFound
    return repository.list_chapters(session, edition_id)


def create_chapter(session: Session, edition_id: uuid.UUID, data: ChapterCreate):
    _validate_chapter(session, edition_id, data.page_start, data.page_end)
    chapter = Chapter(edition_id=edition_id, **data.model_dump())
    session.add(chapter)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise DigitalConflict("Chapter number already exists") from exc
    return chapter


def update_chapter(session: Session, chapter_id: uuid.UUID, data: ChapterUpdate):
    chapter = session.get(Chapter, chapter_id)
    if not chapter:
        raise DigitalNotFound
    values = data.model_dump(exclude_unset=True)
    start = values.get("page_start", chapter.page_start)
    end = values.get("page_end", chapter.page_end)
    _validate_chapter(session, chapter.edition_id, start, end)
    for field, value in values.items():
        setattr(chapter, field, value.strip() if field == "title" else value)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise DigitalConflict("Chapter number already exists") from exc
    return chapter


def delete_chapter(session: Session, chapter_id: uuid.UUID) -> None:
    chapter = session.get(Chapter, chapter_id)
    if not chapter:
        raise DigitalNotFound
    referenced = session.scalar(select(ReadingProgress.id).where(ReadingProgress.chapter_id == chapter_id).limit(1))
    referenced = referenced or session.scalar(select(Bookmark.id).where(Bookmark.chapter_id == chapter_id).limit(1))
    if referenced:
        raise DigitalConflict("Chapter is referenced by reader data")
    session.delete(chapter)
    session.commit()


def _validate_chapter(session: Session, edition_id: uuid.UUID, start: int, end: int) -> None:
    if start > end:
        raise DigitalConflict("Chapter end must be after its start")
    file = repository.get_edition_file(session, edition_id, ready_only=True)
    if not file or end > repository.page_count(session, file.id):
        raise DigitalConflict("Chapter pages are outside this document")
