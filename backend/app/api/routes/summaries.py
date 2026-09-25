import uuid

from fastapi import APIRouter, HTTPException, status

from app.ai.services import summary_service
from app.api.dependencies import ActiveMembership, DatabaseSession
from app.schemas.summaries import SummaryResponse


router = APIRouter(tags=["summaries"])


def _get(operation):
    try:
        return operation()
    except summary_service.SummaryNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Book or chapter not found") from exc
    except (
        summary_service.SummaryUnavailable,
        summary_service.SummarySourceUnavailable,
    ) as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.get("/chapters/{chapter_id}/summary", response_model=SummaryResponse)
def chapter_summary(chapter_id: uuid.UUID, session: DatabaseSession, _: ActiveMembership):
    return _get(lambda: summary_service.get_chapter_summary(session, chapter_id))


@router.get("/editions/{edition_id}/summary", response_model=SummaryResponse)
def edition_summary(edition_id: uuid.UUID, session: DatabaseSession, _: ActiveMembership):
    return _get(lambda: summary_service.get_book_summary(session, edition_id))
