import hashlib
import logging
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.prompts import BOOK_SYSTEM, CHAPTER_SYSTEM, merge_prompt, source_prompt
from app.ai.providers.base import AIProviderError, LLMProvider
from app.ai.providers.factory import get_provider
from app.models import AISummary, BookType, SpoilerMode, SummaryStatus, SummaryType
from app.repositories import summaries as repository


logger = logging.getLogger(__name__)
MAX_SOURCE_CHARS = 12_000


class SummaryNotFound(Exception):
    pass


class SummaryUnavailable(Exception):
    pass


class SummarySourceUnavailable(Exception):
    pass


class SummaryGenerationInProgress(Exception):
    pass


class SummaryGenerationFailed(Exception):
    pass


def _clean(text: str) -> str:
    return " ".join(text.split())


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _chunks(text: str, limit: int = MAX_SOURCE_CHARS) -> list[str]:
    # Conservative ~4 chars/token budget; every word is retained and oversized text is merged hierarchically.
    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for word in words:
        if len(word) > limit:
            if current:
                chunks.append(" ".join(current))
                current, size = [], 0
            chunks.extend(word[index:index + limit] for index in range(0, len(word), limit))
            continue
        if current and size + len(word) + 1 > limit:
            chunks.append(" ".join(current))
            current, size = [], 0
        current.append(word)
        size += len(word) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


def _spoiler_mode(book_type: BookType) -> SpoilerMode:
    return SpoilerMode.SPOILER_FREE if book_type == BookType.FICTION else SpoilerMode.NONE


def _chapter_source(session: Session, chapter_id: uuid.UUID):
    chapter = repository.chapter(session, chapter_id)
    if not chapter:
        raise SummaryNotFound
    file = repository.ready_file(session, chapter.edition_id)
    source = _clean(
        chapter.content
        or (
            repository.page_text(
                session, file.id, chapter.page_start, chapter.page_end
            )
            if file
            else ""
        )
    )
    if not source:
        raise SummarySourceUnavailable(
            "No usable extracted content is available for this chapter"
        )
    return chapter, source, _hash(source), _spoiler_mode(chapter.edition.book.book_type)


def _book_fingerprint(session: Session, edition_id: uuid.UUID):
    edition = repository.edition(session, edition_id)
    if not edition:
        raise SummaryNotFound
    chapter_sources = []
    for item in repository.chapters(session, edition_id):
        try:
            _, _, source_hash, _ = _chapter_source(session, item.id)
            chapter_sources.append((item, source_hash))
        except SummarySourceUnavailable:
            continue
    if not chapter_sources:
        file = repository.ready_file(session, edition_id)
        source = _clean(repository.page_text(session, file.id) if file else "")
        if not source:
            raise SummarySourceUnavailable(
                "No usable extracted content is available for this edition"
            )
        return edition, [], _hash(source), _spoiler_mode(edition.book.book_type), source
    fingerprint = "\n".join(f"{item.id}:{source_hash}" for item, source_hash in chapter_sources)
    return (
        edition,
        [item for item, _ in chapter_sources],
        _hash(fingerprint),
        _spoiler_mode(edition.book.book_type),
        None,
    )


def _response(summary: AISummary, source_hash: str) -> dict:
    return {
        **{field: getattr(summary, field) for field in (
            "id", "edition_id", "chapter_id", "summary_type", "spoiler_mode",
            "content", "source_content_hash", "provider", "model", "status",
            "error_message", "generated_at", "created_at", "updated_at",
        )},
        "is_stale": summary.source_content_hash != source_hash,
    }


def _cached(
    session: Session,
    *,
    edition_id: uuid.UUID,
    chapter_id: uuid.UUID | None,
    summary_type: SummaryType,
    spoiler_mode: SpoilerMode,
    source_hash: str,
    force: bool,
) -> dict | None:
    summary = repository.get_summary(
        session,
        edition_id=edition_id,
        chapter_id=chapter_id,
        summary_type=summary_type,
        spoiler_mode=spoiler_mode,
    )
    if (
        summary
        and summary.status == SummaryStatus.READY
        and summary.source_content_hash == source_hash
        and not force
    ):
        return _response(summary, source_hash)
    return None


def _pending(
    session: Session,
    *,
    edition_id: uuid.UUID,
    chapter_id: uuid.UUID | None,
    summary_type: SummaryType,
    spoiler_mode: SpoilerMode,
    source_hash: str,
    provider: LLMProvider,
    force: bool,
) -> tuple[AISummary, bool]:
    summary = repository.get_summary(
        session,
        edition_id=edition_id,
        chapter_id=chapter_id,
        summary_type=summary_type,
        spoiler_mode=spoiler_mode,
        lock=True,
    )
    if (
        summary
        and summary.status == SummaryStatus.READY
        and summary.source_content_hash == source_hash
        and not force
    ):
        return summary, True
    if (
        summary
        and summary.status == SummaryStatus.PENDING
        and summary.source_content_hash == source_hash
    ):
        raise SummaryGenerationInProgress("Summary generation is already in progress")
    if not summary:
        summary = AISummary(
            edition_id=edition_id,
            chapter_id=chapter_id,
            summary_type=summary_type,
            spoiler_mode=spoiler_mode,
            source_content_hash=source_hash,
            provider=provider.name,
            model=provider.model,
        )
        session.add(summary)
    summary.source_content_hash = source_hash
    summary.provider = provider.name
    summary.model = provider.model
    summary.status = SummaryStatus.PENDING
    summary.content = None
    summary.error_message = None
    summary.generated_at = None
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise SummaryGenerationInProgress("Summary generation is already in progress") from exc
    session.refresh(summary)
    return summary, False


async def _summarize(
    provider: LLMProvider,
    title: str,
    source: str,
    *,
    spoiler_free: bool,
) -> str:
    partials = [
        (
            await provider.generate(
                CHAPTER_SYSTEM,
                source_prompt(title, chunk, spoiler_free=spoiler_free),
            )
        ).content
        for chunk in _chunks(source)
    ]
    while len(partials) > 1:
        groups = _chunks("\n\n".join(partials))
        partials = [
            (
                await provider.generate(
                    BOOK_SYSTEM,
                    merge_prompt(title, group, spoiler_free=spoiler_free),
                )
            ).content
            for group in groups
        ]
    return partials[0]


async def _complete(
    session: Session,
    summary: AISummary,
    operation,
    *,
    feature: str,
) -> dict:
    started = time.monotonic()
    try:
        summary.content = await operation()
        summary.status = SummaryStatus.READY
        summary.generated_at = datetime.now(timezone.utc)
        summary.error_message = None
        session.commit()
        logger.info(
            "ai_summary_generated",
            extra={
                "feature": feature,
                "summary_type": summary.summary_type.value,
                "edition_id": str(summary.edition_id),
                "chapter_id": str(summary.chapter_id) if summary.chapter_id else None,
                "provider": summary.provider,
                "model": summary.model,
                "latency_ms": round((time.monotonic() - started) * 1000),
                "success": True,
            },
        )
        return _response(summary, summary.source_content_hash)
    except Exception as exc:
        session.rollback()
        summary = session.get(AISummary, summary.id)
        summary.status = SummaryStatus.FAILED
        summary.content = None
        summary.error_message = "AI service temporarily unavailable. Try again later."
        session.commit()
        logger.warning(
            "ai_summary_failed",
            extra={
                "feature": feature,
                "summary_type": summary.summary_type.value,
                "edition_id": str(summary.edition_id),
                "chapter_id": str(summary.chapter_id) if summary.chapter_id else None,
                "provider": summary.provider,
                "model": summary.model,
                "latency_ms": round((time.monotonic() - started) * 1000),
                "success": False,
            },
        )
        raise SummaryGenerationFailed(summary.error_message) from exc


async def generate_chapter_summary(
    session: Session,
    chapter_id: uuid.UUID,
    *,
    force: bool = False,
    provider: LLMProvider | None = None,
) -> dict:
    chapter, source, source_hash, spoiler_mode = _chapter_source(session, chapter_id)
    cached = _cached(
        session,
        edition_id=chapter.edition_id,
        chapter_id=chapter.id,
        summary_type=SummaryType.CHAPTER,
        spoiler_mode=spoiler_mode,
        source_hash=source_hash,
        force=force,
    )
    if cached:
        return cached
    try:
        provider = provider or get_provider()
    except RuntimeError as exc:
        raise SummaryGenerationFailed(str(exc)) from exc
    summary, cached = _pending(
        session,
        edition_id=chapter.edition_id,
        chapter_id=chapter.id,
        summary_type=SummaryType.CHAPTER,
        spoiler_mode=spoiler_mode,
        source_hash=source_hash,
        provider=provider,
        force=force,
    )
    if cached:
        return _response(summary, source_hash)
    return await _complete(
        session,
        summary,
        lambda: _summarize(
            provider,
            chapter.title,
            source,
            spoiler_free=spoiler_mode == SpoilerMode.SPOILER_FREE,
        ),
        feature="chapter_summary",
    )


async def generate_book_summary(
    session: Session,
    edition_id: uuid.UUID,
    *,
    force: bool = False,
    provider: LLMProvider | None = None,
) -> dict:
    edition, chapters, source_hash, spoiler_mode, fallback = _book_fingerprint(
        session, edition_id
    )
    cached = _cached(
        session,
        edition_id=edition.id,
        chapter_id=None,
        summary_type=SummaryType.BOOK,
        spoiler_mode=spoiler_mode,
        source_hash=source_hash,
        force=force,
    )
    if cached:
        return cached
    try:
        provider = provider or get_provider()
    except RuntimeError as exc:
        raise SummaryGenerationFailed(str(exc)) from exc
    summary, cached = _pending(
        session,
        edition_id=edition.id,
        chapter_id=None,
        summary_type=SummaryType.BOOK,
        spoiler_mode=spoiler_mode,
        source_hash=source_hash,
        provider=provider,
        force=force,
    )
    if cached:
        return _response(summary, source_hash)

    async def operation() -> str:
        if fallback:
            return await _summarize(
                provider,
                edition.book.title,
                fallback,
                spoiler_free=spoiler_mode == SpoilerMode.SPOILER_FREE,
            )
        chapter_summaries = [
            (
                await generate_chapter_summary(
                    session, item.id, provider=provider
                )
            )["content"]
            for item in chapters
        ]
        return await _summarize(
            provider,
            edition.book.title,
            "\n\n".join(chapter_summaries),
            spoiler_free=spoiler_mode == SpoilerMode.SPOILER_FREE,
        )

    return await _complete(
        session, summary, operation, feature="book_summary"
    )


def get_chapter_summary(session: Session, chapter_id: uuid.UUID, *, admin: bool = False) -> dict:
    chapter, _, source_hash, spoiler_mode = _chapter_source(session, chapter_id)
    summary = repository.get_summary(
        session,
        edition_id=chapter.edition_id,
        chapter_id=chapter.id,
        summary_type=SummaryType.CHAPTER,
        spoiler_mode=spoiler_mode,
    )
    if not summary:
        raise SummaryUnavailable("Summary has not been generated")
    response = _response(summary, source_hash)
    if not admin and (summary.status != SummaryStatus.READY or response["is_stale"]):
        raise SummaryUnavailable("A current summary is not available")
    return response


def get_book_summary(session: Session, edition_id: uuid.UUID, *, admin: bool = False) -> dict:
    edition, _, source_hash, spoiler_mode, _ = _book_fingerprint(session, edition_id)
    summary = repository.get_summary(
        session,
        edition_id=edition.id,
        chapter_id=None,
        summary_type=SummaryType.BOOK,
        spoiler_mode=spoiler_mode,
    )
    if not summary:
        raise SummaryUnavailable("Summary has not been generated")
    response = _response(summary, source_hash)
    if not admin and (summary.status != SummaryStatus.READY or response["is_stale"]):
        raise SummaryUnavailable("A current summary is not available")
    return response
