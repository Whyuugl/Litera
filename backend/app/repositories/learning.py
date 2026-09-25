import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Chapter, Edition, Quiz, QuizAnswer, QuizAttempt, QuizQuestion


def get_quiz(session: Session, quiz_id: uuid.UUID, *, published_only: bool = False) -> Quiz | None:
    statement = select(Quiz).where(Quiz.id == quiz_id)
    if published_only:
        statement = statement.where(Quiz.is_published.is_(True))
    return session.scalar(statement.options(
        joinedload(Quiz.chapter).joinedload(Chapter.edition).joinedload(Edition.book),
        selectinload(Quiz.questions).selectinload(QuizQuestion.options),
    ))


def chapter_quizzes(session: Session, chapter_id: uuid.UUID, *, published_only: bool = False) -> list[Quiz]:
    statement = select(Quiz).where(Quiz.chapter_id == chapter_id)
    if published_only:
        statement = statement.where(Quiz.is_published.is_(True))
    return list(session.scalars(
        statement.options(selectinload(Quiz.questions).selectinload(QuizQuestion.options))
        .order_by(Quiz.created_at)
    ).unique().all())


def attempt_count(session: Session, quiz_id: uuid.UUID) -> int:
    return session.scalar(select(func.count()).select_from(QuizAttempt).where(QuizAttempt.quiz_id == quiz_id)) or 0


def get_attempt(session: Session, attempt_id: uuid.UUID, user_id: uuid.UUID | None = None, *, lock: bool = False) -> QuizAttempt | None:
    statement = select(QuizAttempt).where(QuizAttempt.id == attempt_id)
    if user_id:
        statement = statement.where(QuizAttempt.user_id == user_id)
    if lock:
        statement = statement.with_for_update(of=QuizAttempt)
    return session.scalar(statement)


def load_attempt(session: Session, attempt_id: uuid.UUID, user_id: uuid.UUID) -> QuizAttempt | None:
    return session.scalar(
        select(QuizAttempt)
        .where(QuizAttempt.id == attempt_id, QuizAttempt.user_id == user_id)
        .options(
            selectinload(QuizAttempt.quiz).selectinload(Quiz.questions).selectinload(QuizQuestion.options),
            selectinload(QuizAttempt.answers).joinedload(QuizAnswer.selected_option),
        )
    )


def attempt_history(session: Session, quiz_id: uuid.UUID, user_id: uuid.UUID) -> list[QuizAttempt]:
    return list(session.scalars(
        select(QuizAttempt)
        .where(QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user_id)
        .order_by(QuizAttempt.started_at.desc())
    ).all())
