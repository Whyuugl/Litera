import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    BookType,
    Chapter,
    Edition,
    Quiz,
    QuizAnswer,
    QuizAttempt,
    QuizGeneratedBy,
    QuizOption,
    QuizQuestion,
    ReadingProgress,
    User,
    AISummary,
    SummaryStatus,
    SummaryType,
)
from app.repositories import learning as repository
from app.schemas.learning import AnswerSelection, QuestionInput, QuizCreate, QuizUpdate


LEARNING_BOOK_TYPES = {BookType.EDUCATIONAL, BookType.NON_FICTION, BookType.REFERENCE}


class LearningNotFound(Exception):
    pass


class LearningConflict(Exception):
    pass


def _validate_questions(questions: list[QuestionInput]) -> None:
    if not questions:
        raise LearningConflict("A quiz needs at least one question")
    for question in questions:
        if len(question.options) < 2:
            raise LearningConflict("Every question needs at least two options")
        if sum(option.is_correct for option in question.options) != 1:
            raise LearningConflict("Every question must have exactly one correct option")


def _add_questions(quiz: Quiz, questions: list[QuestionInput]) -> None:
    for question_number, data in enumerate(questions, 1):
        question = QuizQuestion(
            question=data.question.strip(),
            explanation=data.explanation.strip() or None if data.explanation is not None else None,
            question_type=data.question_type,
            order_number=question_number,
        )
        question.options = [
            QuizOption(option_text=option.option_text.strip(), is_correct=option.is_correct, order_number=index)
            for index, option in enumerate(data.options, 1)
        ]
        quiz.questions.append(question)


def _ensure_eligible(quiz: Quiz) -> None:
    if quiz.chapter.edition.book.book_type not in LEARNING_BOOK_TYPES:
        raise LearningConflict("Learning Mode is not enabled for this book type")


def _admin_quiz(session: Session, quiz: Quiz) -> dict:
    return {
        "id": quiz.id,
        "chapter_id": quiz.chapter_id,
        "title": quiz.title,
        "difficulty": quiz.difficulty,
        "generated_by": quiz.generated_by,
        "ai_model": quiz.ai_model,
        "is_published": quiz.is_published,
        "created_by": quiz.created_by,
        "created_at": quiz.created_at,
        "updated_at": quiz.updated_at,
        "questions": quiz.questions,
        "attempt_count": repository.attempt_count(session, quiz.id),
    }


def list_admin_quizzes(session: Session, chapter_id: uuid.UUID) -> list[dict]:
    if not session.get(Chapter, chapter_id):
        raise LearningNotFound
    return [_admin_quiz(session, quiz) for quiz in repository.chapter_quizzes(session, chapter_id)]


def get_admin_quiz(session: Session, quiz_id: uuid.UUID) -> dict:
    quiz = repository.get_quiz(session, quiz_id)
    if not quiz:
        raise LearningNotFound
    return _admin_quiz(session, quiz)


def create_quiz(session: Session, chapter_id: uuid.UUID, data: QuizCreate, admin: User) -> dict:
    _validate_questions(data.questions)
    chapter = session.scalar(
        select(Chapter).where(Chapter.id == chapter_id).options(joinedload(Chapter.edition).joinedload(Edition.book))
    )
    if not chapter:
        raise LearningNotFound
    if chapter.edition.book.book_type not in LEARNING_BOOK_TYPES:
        raise LearningConflict("Learning Mode is not enabled for this book type")
    quiz = Quiz(
        chapter=chapter,
        title=data.title.strip(),
        difficulty=data.difficulty,
        generated_by=QuizGeneratedBy.ADMIN,
        is_published=data.is_published,
        created_by=admin.id,
    )
    _add_questions(quiz, data.questions)
    session.add(quiz)
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    return get_admin_quiz(session, quiz.id)


def update_quiz(session: Session, quiz_id: uuid.UUID, data: QuizUpdate) -> dict:
    quiz = repository.get_quiz(session, quiz_id)
    if not quiz:
        raise LearningNotFound
    values = data.model_dump(exclude_unset=True)
    questions = values.pop("questions", None)
    if questions is not None:
        _validate_questions(data.questions)
        if repository.attempt_count(session, quiz.id):
            raise LearningConflict("Quiz structure is locked because attempts already exist")
        quiz.questions.clear()
        session.flush()
        _add_questions(quiz, data.questions)
    for field, value in values.items():
        setattr(quiz, field, value.strip() if field == "title" else value)
    session.commit()
    return get_admin_quiz(session, quiz.id)


def delete_quiz(session: Session, quiz_id: uuid.UUID) -> None:
    quiz = repository.get_quiz(session, quiz_id)
    if not quiz:
        raise LearningNotFound
    if repository.attempt_count(session, quiz.id):
        raise LearningConflict("Quiz has attempt history; unpublish it instead")
    session.delete(quiz)
    session.commit()


def _student_quiz(quiz: Quiz) -> dict:
    return {
        "id": quiz.id,
        "chapter_id": quiz.chapter_id,
        "edition_id": quiz.chapter.edition_id,
        "title": quiz.title,
        "difficulty": quiz.difficulty,
        "questions": [
            {
                "id": question.id,
                "question": question.question,
                "question_type": question.question_type,
                "order_number": question.order_number,
                "options": [
                    {"id": option.id, "option_text": option.option_text, "order_number": option.order_number}
                    for option in question.options
                ],
            }
            for question in quiz.questions
        ],
    }


def list_member_quizzes(session: Session, chapter_id: uuid.UUID) -> list[dict]:
    if not session.get(Chapter, chapter_id):
        raise LearningNotFound
    return [
        {
            "id": quiz.id,
            "chapter_id": quiz.chapter_id,
            "title": quiz.title,
            "difficulty": quiz.difficulty,
            "question_count": len(quiz.questions),
        }
        for quiz in repository.chapter_quizzes(session, chapter_id, published_only=True)
    ]


def get_member_quiz(session: Session, quiz_id: uuid.UUID) -> dict:
    quiz = repository.get_quiz(session, quiz_id, published_only=True)
    if not quiz:
        raise LearningNotFound
    _ensure_eligible(quiz)
    return _student_quiz(quiz)


def start_attempt(session: Session, quiz_id: uuid.UUID, user: User) -> dict:
    quiz = repository.get_quiz(session, quiz_id, published_only=True)
    if not quiz:
        raise LearningNotFound
    _ensure_eligible(quiz)
    if not quiz.questions:
        raise LearningConflict("This quiz has no questions")
    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=user.id,
        total_questions=len(quiz.questions),
    )
    session.add(attempt)
    session.commit()
    session.refresh(attempt)
    return {"id": attempt.id, "quiz": _student_quiz(quiz), "started_at": attempt.started_at, "answers": {}}


def save_answer(
    session: Session,
    attempt_id: uuid.UUID,
    question_id: uuid.UUID,
    data: AnswerSelection,
    user: User,
) -> dict:
    attempt = repository.get_attempt(session, attempt_id, user.id, lock=True)
    if not attempt:
        raise LearningNotFound
    if attempt.completed_at:
        raise LearningConflict("Completed attempts cannot be changed")
    question = session.scalar(select(QuizQuestion).where(QuizQuestion.id == question_id, QuizQuestion.quiz_id == attempt.quiz_id))
    option = session.scalar(select(QuizOption).where(QuizOption.id == data.selected_option_id, QuizOption.question_id == question_id))
    if not question or not option:
        raise LearningConflict("Question or option does not belong to this quiz")
    answer = session.scalar(select(QuizAnswer).where(QuizAnswer.attempt_id == attempt.id, QuizAnswer.question_id == question_id))
    if answer:
        answer.selected_option_id = option.id
        answer.is_correct = None
    else:
        session.add(QuizAnswer(attempt_id=attempt.id, question_id=question.id, selected_option_id=option.id))
    session.commit()
    return {"question_id": question.id, "selected_option_id": option.id}


def submit_attempt(session: Session, attempt_id: uuid.UUID, user: User) -> dict:
    attempt = repository.get_attempt(session, attempt_id, user.id, lock=True)
    if not attempt:
        raise LearningNotFound
    if attempt.completed_at:
        raise LearningConflict("This attempt is already completed")
    quiz = repository.get_quiz(session, attempt.quiz_id)
    answers = list(session.scalars(select(QuizAnswer).where(QuizAnswer.attempt_id == attempt.id)).all())
    if len(answers) != len(quiz.questions):
        raise LearningConflict(f"Answer all {len(quiz.questions)} questions before submitting")
    options = {option.id: option for question in quiz.questions for option in question.options}
    correct = 0
    for answer in answers:
        answer.is_correct = options[answer.selected_option_id].is_correct
        correct += int(answer.is_correct)
    attempt.correct_answers = correct
    attempt.total_questions = len(quiz.questions)
    attempt.score = round(correct / attempt.total_questions * 100, 2)
    attempt.completed_at = datetime.now(timezone.utc)
    session.commit()
    return attempt_result(session, attempt.id, user)


def _summary(attempt: QuizAttempt) -> dict:
    return {
        "id": attempt.id,
        "quiz_id": attempt.quiz_id,
        "score": attempt.score,
        "correct_answers": attempt.correct_answers,
        "total_questions": attempt.total_questions,
        "started_at": attempt.started_at,
        "completed_at": attempt.completed_at,
    }


def attempt_result(session: Session, attempt_id: uuid.UUID, user: User) -> dict:
    attempt = repository.load_attempt(session, attempt_id, user.id)
    if not attempt:
        raise LearningNotFound
    if not attempt.completed_at:
        return {
            "id": attempt.id,
            "quiz": _student_quiz(attempt.quiz),
            "started_at": attempt.started_at,
            "answers": {answer.question_id: answer.selected_option_id for answer in attempt.answers},
        }
    answers = {answer.question_id: answer for answer in attempt.answers}
    review = []
    for question in attempt.quiz.questions:
        answer = answers[question.id]
        correct_option = next(option for option in question.options if option.is_correct)
        review.append({
            "question_id": question.id,
            "question": question.question,
            "selected_option_id": answer.selected_option_id,
            "selected_answer": answer.selected_option.option_text,
            "correct_option_id": correct_option.id,
            "correct_answer": correct_option.option_text,
            "is_correct": bool(answer.is_correct),
            "explanation": question.explanation,
        })
    return {**_summary(attempt), "quiz": _student_quiz(attempt.quiz), "review": review}


def attempt_history(session: Session, quiz_id: uuid.UUID, user: User) -> list[dict]:
    if not repository.get_quiz(session, quiz_id, published_only=True):
        raise LearningNotFound
    return [_summary(attempt) for attempt in repository.attempt_history(session, quiz_id, user.id)]


def learning_progress(session: Session, edition_id: uuid.UUID, user: User) -> dict:
    edition = session.scalar(
        select(Edition).where(Edition.id == edition_id).options(
            joinedload(Edition.book),
            selectinload(Edition.chapters).selectinload(Chapter.quizzes).selectinload(Quiz.questions),
        )
    )
    if not edition or edition.book.book_type not in LEARNING_BOOK_TYPES:
        raise LearningNotFound
    progress = session.scalar(select(ReadingProgress).where(ReadingProgress.user_id == user.id, ReadingProgress.edition_id == edition_id))
    quizzes = [quiz for chapter in edition.chapters for quiz in chapter.quizzes if quiz.is_published]
    attempts = list(session.scalars(
        select(QuizAttempt).where(
            QuizAttempt.user_id == user.id,
            QuizAttempt.quiz_id.in_([quiz.id for quiz in quizzes]),
            QuizAttempt.completed_at.is_not(None),
        )
    ).all()) if quizzes else []
    best_scores: dict[uuid.UUID, float] = {}
    for attempt in attempts:
        best_scores[attempt.quiz_id] = max(best_scores.get(attempt.quiz_id, 0), attempt.score or 0)
    chapters = sorted(edition.chapters, key=lambda item: item.chapter_number)
    ready_summaries = list(session.scalars(
        select(AISummary).where(
            AISummary.edition_id == edition_id,
            AISummary.status == SummaryStatus.READY,
        )
    ).all())
    summary_chapters = {
        summary.chapter_id
        for summary in ready_summaries
        if summary.summary_type == SummaryType.CHAPTER
    }
    return {
        "edition_id": edition.id,
        "book": {"id": edition.book.id, "title": edition.book.title, "slug": edition.book.slug, "cover_url": edition.book.cover_url},
        "chapters_total": len(chapters),
        "chapters_read": sum(bool(progress and chapter.page_end <= progress.current_page) for chapter in chapters),
        "quizzes_available": len(quizzes),
        "quizzes_completed": len(best_scores),
        "average_score": round(sum(best_scores.values()) / len(best_scores), 2) if best_scores else None,
        "book_summary_available": any(
            summary.summary_type == SummaryType.BOOK for summary in ready_summaries
        ),
        "chapters": [
            {
                "id": chapter.id,
                "chapter_number": chapter.chapter_number,
                "title": chapter.title,
                "page_start": chapter.page_start,
                "page_end": chapter.page_end,
                "is_read": bool(progress and chapter.page_end <= progress.current_page),
                "quizzes": [
                    {"id": quiz.id, "chapter_id": chapter.id, "title": quiz.title, "difficulty": quiz.difficulty, "question_count": len(quiz.questions)}
                    for quiz in chapter.quizzes if quiz.is_published
                ],
                "best_score": (lambda scores: max(scores) if scores else None)([
                    best_scores[quiz.id] for quiz in chapter.quizzes if quiz.id in best_scores
                ]),
                "summary_available": chapter.id in summary_chapters,
            }
            for chapter in chapters
        ],
    }
