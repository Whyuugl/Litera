import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import ActiveMembership, CurrentUser, DatabaseSession
from app.schemas.learning import (
    AnswerSaved,
    AnswerSelection,
    AttemptResult,
    AttemptStarted,
    AttemptSummary,
    LearningProgress,
    QuizSummary,
    StudentQuiz,
)
from app.services import learning


router = APIRouter(tags=["learning"])


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, learning.LearningNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Quiz or attempt not found")
    return HTTPException(status.HTTP_409_CONFLICT, str(exc) or "Learning action unavailable")


@router.get("/chapters/{chapter_id}/quizzes", response_model=list[QuizSummary])
def quizzes(chapter_id: uuid.UUID, session: DatabaseSession, _: ActiveMembership):
    try:
        return learning.list_member_quizzes(session, chapter_id)
    except learning.LearningNotFound as exc:
        raise _error(exc) from exc


@router.get("/quizzes/{quiz_id}", response_model=StudentQuiz)
def quiz(quiz_id: uuid.UUID, session: DatabaseSession, _: ActiveMembership):
    try:
        return learning.get_member_quiz(session, quiz_id)
    except (learning.LearningNotFound, learning.LearningConflict) as exc:
        raise _error(exc) from exc


@router.post("/quizzes/{quiz_id}/attempts", response_model=AttemptStarted, status_code=201)
def start_attempt(quiz_id: uuid.UUID, session: DatabaseSession, user: CurrentUser, _: ActiveMembership):
    try:
        return learning.start_attempt(session, quiz_id, user)
    except (learning.LearningNotFound, learning.LearningConflict) as exc:
        raise _error(exc) from exc


@router.put("/quiz-attempts/{attempt_id}/answers/{question_id}", response_model=AnswerSaved)
def save_answer(attempt_id: uuid.UUID, question_id: uuid.UUID, data: AnswerSelection, session: DatabaseSession, user: CurrentUser, _: ActiveMembership):
    try:
        return learning.save_answer(session, attempt_id, question_id, data, user)
    except (learning.LearningNotFound, learning.LearningConflict) as exc:
        raise _error(exc) from exc


@router.post("/quiz-attempts/{attempt_id}/submit", response_model=AttemptResult)
def submit(attempt_id: uuid.UUID, session: DatabaseSession, user: CurrentUser, _: ActiveMembership):
    try:
        return learning.submit_attempt(session, attempt_id, user)
    except (learning.LearningNotFound, learning.LearningConflict) as exc:
        raise _error(exc) from exc


@router.get("/quizzes/{quiz_id}/attempts/me", response_model=list[AttemptSummary])
def history(quiz_id: uuid.UUID, session: DatabaseSession, user: CurrentUser, _: ActiveMembership):
    try:
        return learning.attempt_history(session, quiz_id, user)
    except learning.LearningNotFound as exc:
        raise _error(exc) from exc


@router.get("/quiz-attempts/{attempt_id}", response_model=AttemptStarted | AttemptResult)
def attempt(attempt_id: uuid.UUID, session: DatabaseSession, user: CurrentUser, _: ActiveMembership):
    try:
        return learning.attempt_result(session, attempt_id, user)
    except learning.LearningNotFound as exc:
        raise _error(exc) from exc


@router.get("/learning/editions/{edition_id}/progress", response_model=LearningProgress)
def progress(edition_id: uuid.UUID, session: DatabaseSession, user: CurrentUser, _: ActiveMembership):
    try:
        return learning.learning_progress(session, edition_id, user)
    except learning.LearningNotFound as exc:
        raise _error(exc) from exc
