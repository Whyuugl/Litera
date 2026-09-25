import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.ai.services import summary_service
from app.api.dependencies import AdminUser, DatabaseSession
from app.schemas.summaries import SummaryResponse


router = APIRouter(prefix="/admin", tags=["admin summaries"])


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, summary_service.SummaryNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Book or chapter not found")
    if isinstance(exc, summary_service.SummaryUnavailable):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, summary_service.SummarySourceUnavailable):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    if isinstance(exc, summary_service.SummaryGenerationInProgress):
        return HTTPException(status.HTTP_409_CONFLICT, str(exc))
    return HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        str(exc) or "AI service temporarily unavailable",
    )


@router.get("/chapters/{chapter_id}/summary", response_model=SummaryResponse)
def chapter_summary(chapter_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        return summary_service.get_chapter_summary(session, chapter_id, admin=True)
    except (
        summary_service.SummaryNotFound,
        summary_service.SummaryUnavailable,
        summary_service.SummarySourceUnavailable,
    ) as exc:
        raise _error(exc) from exc


@router.post("/chapters/{chapter_id}/summary/generate", response_model=SummaryResponse)
async def generate_chapter_summary(
    chapter_id: uuid.UUID,
    session: DatabaseSession,
    _: AdminUser,
    regenerate: bool = Query(False),
):
    try:
        return await summary_service.generate_chapter_summary(
            session, chapter_id, force=regenerate
        )
    except (
        summary_service.SummaryNotFound,
        summary_service.SummarySourceUnavailable,
        summary_service.SummaryGenerationInProgress,
        summary_service.SummaryGenerationFailed,
    ) as exc:
        raise _error(exc) from exc


@router.get("/editions/{edition_id}/summary", response_model=SummaryResponse)
def edition_summary(edition_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        return summary_service.get_book_summary(session, edition_id, admin=True)
    except (
        summary_service.SummaryNotFound,
        summary_service.SummaryUnavailable,
        summary_service.SummarySourceUnavailable,
    ) as exc:
        raise _error(exc) from exc


@router.post("/editions/{edition_id}/summary/generate", response_model=SummaryResponse)
async def generate_edition_summary(
    edition_id: uuid.UUID,
    session: DatabaseSession,
    _: AdminUser,
    regenerate: bool = Query(False),
):
    try:
        return await summary_service.generate_book_summary(
            session, edition_id, force=regenerate
        )
    except (
        summary_service.SummaryNotFound,
        summary_service.SummarySourceUnavailable,
        summary_service.SummaryGenerationInProgress,
        summary_service.SummaryGenerationFailed,
    ) as exc:
        raise _error(exc) from exc
