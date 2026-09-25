import asyncio
import logging
import time
import uuid

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.prompts.quizzes import QUIZ_SYSTEM, quiz_prompt
from app.ai.providers.base import AIProviderError, LLMProvider
from app.ai.providers.factory import get_provider
from app.ai.schemas import GeneratedQuiz
from app.models import QuizGeneratedBy, User
from app.repositories import learning as learning_repository
from app.repositories import summaries as source_repository
from app.schemas.learning import OptionInput, QuestionInput, QuizCreate, QuizDifficulty
from app.services import learning


logger = logging.getLogger(__name__)
MAX_QUIZ_SOURCE_CHARS = 16_000
MIN_QUIZ_SOURCE_CHARS = 200
_generation_locks: dict[uuid.UUID, asyncio.Lock] = {}


class QuizGenerationNotFound(Exception):
    pass


class QuizGenerationUnavailable(Exception):
    pass


class QuizSourceUnavailable(Exception):
    pass


class QuizGenerationConflict(Exception):
    pass


class QuizOutputInvalid(Exception):
    pass


def _representative_source(source: str, limit: int = MAX_QUIZ_SOURCE_CHARS) -> str:
    source = " ".join(source.split())
    if len(source) <= limit:
        return source
    segment_count = 5
    segment_size = limit // segment_count
    last_start = len(source) - segment_size
    segments = []
    for index in range(segment_count):
        start = round(last_start * index / (segment_count - 1))
        if start:
            start = source.find(" ", start) + 1
        end = min(len(source), start + segment_size)
        if end < len(source):
            end = source.rfind(" ", start, end)
        segments.append(source[start:end].strip())
    return "\n\n[SECTION BREAK]\n\n".join(segments)


def _source(session: Session, chapter_id: uuid.UUID):
    chapter = source_repository.chapter(session, chapter_id)
    if not chapter:
        raise QuizGenerationNotFound
    if chapter.edition.book.book_type not in learning.LEARNING_BOOK_TYPES:
        raise QuizSourceUnavailable("Learning Mode is not enabled for this book type")
    file = source_repository.ready_file(session, chapter.edition_id)
    content = chapter.content or (
        source_repository.page_text(session, file.id, chapter.page_start, chapter.page_end)
        if file else ""
    )
    content = " ".join(content.split())
    if len(content) < MIN_QUIZ_SOURCE_CHARS:
        raise QuizSourceUnavailable("This chapter does not contain enough usable extracted content")
    return chapter, _representative_source(content)


def _validated_quiz(content: str, difficulty: QuizDifficulty, question_count: int) -> QuizCreate:
    try:
        generated = GeneratedQuiz.model_validate_json(content)
    except ValidationError as exc:
        raise QuizOutputInvalid("AI returned an invalid quiz structure") from exc
    if len(generated.questions) != question_count:
        raise QuizOutputInvalid(f"AI must return exactly {question_count} questions")
    return QuizCreate(
        title=generated.title,
        difficulty=difficulty,
        is_published=False,
        questions=[
            QuestionInput(
                question=item.question,
                explanation=item.explanation,
                question_type=item.question_type,
                options=[
                    OptionInput(option_text=option.text, is_correct=option.is_correct)
                    for option in item.options
                ],
            )
            for item in generated.questions
        ],
    )


async def _generate(
    session: Session,
    chapter_id: uuid.UUID,
    difficulty: QuizDifficulty,
    question_count: int,
    admin: User,
    *,
    provider: LLMProvider | None,
    replace_quiz_id: uuid.UUID | None = None,
    exclude_draft_id: uuid.UUID | None = None,
) -> dict:
    chapter, source = _source(session, chapter_id)
    existing = learning_repository.ai_draft(session, chapter_id, exclude_id=exclude_draft_id)
    if existing and not replace_quiz_id:
        return learning.get_admin_quiz(session, existing.id)
    try:
        provider = provider or get_provider()
    except RuntimeError as exc:
        raise QuizGenerationUnavailable(str(exc)) from exc
    started = time.monotonic()
    try:
        generated = await provider.generate_structured(
            QUIZ_SYSTEM,
            quiz_prompt(chapter.title, source, difficulty.value, question_count),
        )
        data = _validated_quiz(generated.content, difficulty, question_count)
        target = learning_repository.get_quiz(session, replace_quiz_id) if replace_quiz_id else None
        result = learning.save_ai_quiz(session, chapter, data, admin, provider.model, quiz=target)
        logger.info("ai_quiz_generated", extra={
            "feature": "quiz_generation",
            "chapter_id": str(chapter.id),
            "quiz_id": str(result["id"]),
            "difficulty": difficulty.value,
            "question_count": question_count,
            "provider": provider.name,
            "model": provider.model,
            "input_tokens": generated.input_tokens,
            "output_tokens": generated.output_tokens,
            "latency_ms": round((time.monotonic() - started) * 1000),
            "success": True,
        })
        return result
    except QuizOutputInvalid:
        session.rollback()
        raise
    except (AIProviderError, learning.LearningConflict) as exc:
        session.rollback()
        logger.warning("ai_quiz_generation_failed", extra={
            "feature": "quiz_generation",
            "chapter_id": str(chapter.id),
            "difficulty": difficulty.value,
            "question_count": question_count,
            "provider": provider.name,
            "model": provider.model,
            "latency_ms": round((time.monotonic() - started) * 1000),
            "success": False,
        })
        if isinstance(exc, learning.LearningConflict):
            raise QuizGenerationConflict(str(exc)) from exc
        raise QuizGenerationUnavailable("AI quiz generation is temporarily unavailable") from exc
    except Exception as exc:
        session.rollback()
        logger.exception("ai_quiz_generation_failed", extra={
            "feature": "quiz_generation",
            "chapter_id": str(chapter.id),
            "difficulty": difficulty.value,
            "question_count": question_count,
            "provider": provider.name,
            "model": provider.model,
            "latency_ms": round((time.monotonic() - started) * 1000),
            "success": False,
        })
        raise QuizGenerationUnavailable("AI quiz generation is temporarily unavailable") from exc


async def generate_quiz(
    session: Session,
    chapter_id: uuid.UUID,
    difficulty: QuizDifficulty,
    question_count: int,
    admin: User,
    *,
    provider: LLMProvider | None = None,
) -> dict:
    lock = _generation_locks.setdefault(chapter_id, asyncio.Lock())
    async with lock:
        return await _generate(
            session, chapter_id, difficulty, question_count, admin, provider=provider
        )


async def regenerate_quiz(
    session: Session,
    quiz_id: uuid.UUID,
    admin: User,
    *,
    difficulty: QuizDifficulty | None = None,
    question_count: int | None = None,
    provider: LLMProvider | None = None,
) -> dict:
    quiz = learning_repository.get_quiz(session, quiz_id)
    if not quiz:
        raise QuizGenerationNotFound
    if quiz.generated_by != QuizGeneratedBy.AI or quiz.is_published:
        raise QuizGenerationConflict("Only unpublished AI-generated quizzes can be regenerated")
    difficulty = difficulty or quiz.difficulty
    question_count = question_count or len(quiz.questions)
    has_attempts = bool(learning_repository.attempt_count(session, quiz.id))
    lock = _generation_locks.setdefault(quiz.chapter_id, asyncio.Lock())
    async with lock:
        return await _generate(
            session,
            quiz.chapter_id,
            difficulty,
            question_count,
            admin,
            provider=provider,
            replace_quiz_id=None if has_attempts else quiz.id,
            exclude_draft_id=quiz.id,
        )
