import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import CurrentUser, DatabaseSession, OptionalUser
from app.schemas.digital import (
    BookmarkCreate,
    BookmarkResponse,
    BookmarkUpdate,
    ProgressListItem,
    ProgressResponse,
    ProgressUpdate,
    ReaderPageResponse,
    ReaderResponse,
)
from app.services import digital


router = APIRouter(tags=["digital reader"])


def _raise(exc: Exception) -> HTTPException:
    if isinstance(exc, digital.DigitalNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Digital edition not found or not ready")
    if isinstance(exc, digital.DigitalAccessDenied):
        return HTTPException(status.HTTP_403_FORBIDDEN, "This digital edition requires additional access")
    return HTTPException(status.HTTP_409_CONFLICT, str(exc) or "Digital reader conflict")


@router.get("/editions/{edition_id}/reader", response_model=ReaderResponse)
def reader(edition_id: uuid.UUID, session: DatabaseSession, user: OptionalUser):
    try:
        return digital.get_reader(session, edition_id, user)
    except (digital.DigitalNotFound, digital.DigitalAccessDenied) as exc:
        raise _raise(exc) from exc


@router.get("/editions/{edition_id}/pages", response_model=list[ReaderPageResponse])
def reader_pages(edition_id: uuid.UUID, session: DatabaseSession, user: OptionalUser):
    try:
        return digital.get_reader_pages(session, edition_id, user)
    except (digital.DigitalNotFound, digital.DigitalAccessDenied) as exc:
        raise _raise(exc) from exc


def _range(value: str | None, size: int) -> tuple[int, int, bool]:
    if not value:
        return 0, size - 1, False
    try:
        unit, requested = value.split("=", 1)
        if unit != "bytes" or "," in requested:
            raise ValueError
        start_text, end_text = requested.split("-", 1)
        if start_text:
            start = int(start_text)
            end = min(int(end_text), size - 1) if end_text else size - 1
        else:
            length = int(end_text)
            start, end = max(0, size - length), size - 1
        if start < 0 or start > end or start >= size:
            raise ValueError
        return start, end, True
    except (ValueError, TypeError):
        raise HTTPException(
            status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            "Invalid byte range",
            headers={"Content-Range": f"bytes */{size}"},
        )


@router.get("/digital-files/{file_id}/content")
def content(
    file_id: uuid.UUID,
    session: DatabaseSession,
    user: OptionalUser,
    range_header: Annotated[str | None, Header(alias="Range")] = None,
    download: bool = Query(False),
):
    try:
        file, path = digital.get_content_file(session, file_id, user)
    except (digital.DigitalNotFound, digital.DigitalAccessDenied) as exc:
        raise _raise(exc) from exc
    if download and not file.allow_download:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Downloads are disabled for this edition")
    size = path.stat().st_size
    start, end, partial = _range(range_header, size)

    def chunks():
        remaining = end - start + 1
        with path.open("rb") as stream:
            stream.seek(start)
            while remaining:
                chunk = stream.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    name = Path(file.original_filename or "document.pdf").name.replace('"', "")
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(end - start + 1),
        "Content-Disposition": f'{"attachment" if download else "inline"}; filename="{name}"',
    }
    if partial:
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    return StreamingResponse(
        chunks(), media_type="application/pdf", headers=headers,
        status_code=status.HTTP_206_PARTIAL_CONTENT if partial else status.HTTP_200_OK,
    )


@router.get("/reading-progress", response_model=list[ProgressListItem])
def progress_list(session: DatabaseSession, user: CurrentUser):
    return digital.list_progress(session, user)


@router.get("/reading-progress/{edition_id}", response_model=ProgressResponse | None)
def progress(edition_id: uuid.UUID, session: DatabaseSession, user: CurrentUser):
    return digital.get_progress(session, edition_id, user)


@router.put("/reading-progress/{edition_id}", response_model=ProgressResponse)
def save_progress(edition_id: uuid.UUID, data: ProgressUpdate, session: DatabaseSession, user: CurrentUser):
    try:
        return digital.save_progress(session, edition_id, data, user)
    except (digital.DigitalNotFound, digital.DigitalAccessDenied, digital.DigitalConflict) as exc:
        raise _raise(exc) from exc


@router.get("/editions/{edition_id}/bookmarks", response_model=list[BookmarkResponse])
def bookmarks(edition_id: uuid.UUID, session: DatabaseSession, user: CurrentUser):
    return digital.list_bookmarks(session, edition_id, user)


@router.get("/bookmarks", response_model=list[BookmarkResponse])
def bookmarks_query(edition_id: uuid.UUID, session: DatabaseSession, user: CurrentUser):
    return digital.list_bookmarks(session, edition_id, user)


@router.post("/bookmarks", response_model=BookmarkResponse, status_code=201)
def create_bookmark(data: BookmarkCreate, session: DatabaseSession, user: CurrentUser):
    try:
        return digital.create_bookmark(session, data, user)
    except (digital.DigitalNotFound, digital.DigitalAccessDenied, digital.DigitalConflict) as exc:
        raise _raise(exc) from exc


@router.patch("/bookmarks/{bookmark_id}", response_model=BookmarkResponse)
def update_bookmark(bookmark_id: uuid.UUID, data: BookmarkUpdate, session: DatabaseSession, user: CurrentUser):
    try:
        return digital.update_bookmark(session, bookmark_id, data, user)
    except digital.DigitalNotFound as exc:
        raise _raise(exc) from exc


@router.delete("/bookmarks/{bookmark_id}", status_code=204)
def delete_bookmark(bookmark_id: uuid.UUID, session: DatabaseSession, user: CurrentUser):
    try:
        digital.delete_bookmark(session, bookmark_id, user)
    except digital.DigitalNotFound as exc:
        raise _raise(exc) from exc
    return Response(status_code=204)
