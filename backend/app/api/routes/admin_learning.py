import uuid

from fastapi import APIRouter, HTTPException, Response, status

from app.api.dependencies import AdminUser, DatabaseSession
from app.ai.services import quiz_generation_service
from app.schemas.learning import AdminQuizResponse, QuizCreate, QuizGenerateRequest, QuizRegenerateRequest, QuizUpdate
from app.services import learning


router = APIRouter(prefix="/admin", tags=["admin learning"])


def _generation_error(exc: Exception) -> HTTPException:
    if isinstance(exc, quiz_generation_service.QuizGenerationNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Chapter or quiz not found")
    if isinstance(exc, quiz_generation_service.QuizSourceUnavailable):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    if isinstance(exc, quiz_generation_service.QuizGenerationConflict):
        return HTTPException(status.HTTP_409_CONFLICT, str(exc))
    if isinstance(exc, quiz_generation_service.QuizOutputInvalid):
        return HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc) or "AI quiz generation unavailable")


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


@router.post("/chapters/{chapter_id}/quiz/generate", response_model=AdminQuizResponse)
async def generate_quiz(
    chapter_id: uuid.UUID,
    session: DatabaseSession,
    admin: AdminUser,
    data: QuizGenerateRequest | None = None,
):
    data = data or QuizGenerateRequest()
    try:
        return await quiz_generation_service.generate_quiz(
            session, chapter_id, data.difficulty, data.question_count, admin
        )
    except (
        quiz_generation_service.QuizGenerationNotFound,
        quiz_generation_service.QuizSourceUnavailable,
        quiz_generation_service.QuizGenerationConflict,
        quiz_generation_service.QuizOutputInvalid,
        quiz_generation_service.QuizGenerationUnavailable,
    ) as exc:
        raise _generation_error(exc) from exc


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


@router.post("/quizzes/{quiz_id}/regenerate", response_model=AdminQuizResponse)
async def regenerate_quiz(
    quiz_id: uuid.UUID,
    session: DatabaseSession,
    admin: AdminUser,
    data: QuizRegenerateRequest | None = None,
):
    data = data or QuizRegenerateRequest()
    try:
        return await quiz_generation_service.regenerate_quiz(
            session,
            quiz_id,
            admin,
            difficulty=data.difficulty,
            question_count=data.question_count,
        )
    except (
        quiz_generation_service.QuizGenerationNotFound,
        quiz_generation_service.QuizSourceUnavailable,
        quiz_generation_service.QuizGenerationConflict,
        quiz_generation_service.QuizOutputInvalid,
        quiz_generation_service.QuizGenerationUnavailable,
    ) as exc:
        raise _generation_error(exc) from exc


@router.delete("/quizzes/{quiz_id}", status_code=204)
def delete_quiz(quiz_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        learning.delete_quiz(session, quiz_id)
    except (learning.LearningNotFound, learning.LearningConflict) as exc:
        raise _error(exc) from exc
    return Response(status_code=204)
