import uuid

from fastapi import APIRouter, HTTPException, Response, status

from app.api.dependencies import AdminUser, DatabaseSession
from app.schemas.learning import AdminQuizResponse, QuizCreate, QuizUpdate
from app.services import learning


router = APIRouter(prefix="/admin", tags=["admin learning"])


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, learning.LearningNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Learning resource not found")
    return HTTPException(status.HTTP_409_CONFLICT, str(exc) or "Learning resource conflict")


@router.get("/chapters/{chapter_id}/quizzes", response_model=list[AdminQuizResponse])
def quizzes(chapter_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        return learning.list_admin_quizzes(session, chapter_id)
    except learning.LearningNotFound as exc:
        raise _error(exc) from exc


@router.post("/chapters/{chapter_id}/quizzes", response_model=AdminQuizResponse, status_code=201)
def create_quiz(chapter_id: uuid.UUID, data: QuizCreate, session: DatabaseSession, admin: AdminUser):
    try:
        return learning.create_quiz(session, chapter_id, data, admin)
    except (learning.LearningNotFound, learning.LearningConflict) as exc:
        raise _error(exc) from exc


@router.get("/quizzes/{quiz_id}", response_model=AdminQuizResponse)
def quiz(quiz_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        return learning.get_admin_quiz(session, quiz_id)
    except learning.LearningNotFound as exc:
        raise _error(exc) from exc


@router.patch("/quizzes/{quiz_id}", response_model=AdminQuizResponse)
def update_quiz(quiz_id: uuid.UUID, data: QuizUpdate, session: DatabaseSession, _: AdminUser):
    try:
        return learning.update_quiz(session, quiz_id, data)
    except (learning.LearningNotFound, learning.LearningConflict) as exc:
        raise _error(exc) from exc


@router.delete("/quizzes/{quiz_id}", status_code=204)
def delete_quiz(quiz_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        learning.delete_quiz(session, quiz_id)
    except (learning.LearningNotFound, learning.LearningConflict) as exc:
        raise _error(exc) from exc
    return Response(status_code=204)
