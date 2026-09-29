import hashlib
import logging
import math
import os
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.ai.providers.base import EmbeddingProvider
from app.ai.providers.factory import get_embedding_provider
from app.models import BookChunk, ProcessingStatus, RAGStatus
from app.models.rag import EMBEDDING_DIMENSIONS
from app.repositories import rag as repository


logger = logging.getLogger(__name__)


class RAGNotFound(Exception):
    pass


class RAGUnavailable(Exception):
    pass


class RAGConflict(Exception):
    pass


@dataclass(frozen=True)
class ChunkDraft:
    chunk_index: int
    chapter_id: uuid.UUID | None
    content: str
    page_start: int
    page_end: int
    token_count: int
    content_hash: str


@dataclass(frozen=True)
class _Piece:
    text: str
    page: int


@lru_cache
def chunk_limits() -> tuple[int, int]:
    try:
        target = int(os.getenv("RAG_CHUNK_TARGET_TOKENS", "650"))
        overlap = int(os.getenv("RAG_CHUNK_OVERLAP_TOKENS", "100"))
    except ValueError as exc:
        raise RuntimeError("RAG chunk settings must be integers") from exc
    if target < 100 or overlap < 0 or overlap >= target:
        raise RuntimeError("RAG chunk target must be >= 100 and overlap must be smaller")
    return target, overlap


def _hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _pieces(content: str, page: int, max_words: int) -> list[_Piece]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", content) if part.strip()]
    result: list[_Piece] = []
    for paragraph in paragraphs:
        sentences = re.split(r"(?<=[.!?])\s+", " ".join(paragraph.split()))
        current: list[str] = []
        count = 0
        for sentence in sentences:
            words = sentence.split()
            while len(words) > max_words:
                if current:
                    result.append(_Piece(" ".join(current), page))
                    current, count = [], 0
                result.append(_Piece(" ".join(words[:max_words]), page))
                words = words[max_words:]
            if words and current and count + len(words) > max_words:
                result.append(_Piece(" ".join(current), page))
                current, count = [], 0
            current.extend(words)
            count += len(words)
        if current:
            result.append(_Piece(" ".join(current), page))
    return result


def chunk_pages(pages, chapters, *, target: int | None = None, overlap: int | None = None) -> list[ChunkDraft]:
    default_target, default_overlap = chunk_limits()
    target = default_target if target is None else target
    overlap = default_overlap if overlap is None else overlap
    if target < 1 or overlap < 0 or overlap >= target:
        raise ValueError("Invalid chunk target or overlap")

    scopes: list[tuple[uuid.UUID | None, list]] = []
    for page in pages:
        chapter = next((item for item in chapters if item.page_start <= page.page_number <= item.page_end), None)
        key = chapter.id if chapter else None
        if not scopes or scopes[-1][0] != key:
            scopes.append((key, []))
        scopes[-1][1].append(page)

    drafts: list[ChunkDraft] = []
    max_piece_words = max(20, overlap or min(100, target))
    for chapter_id, scope_pages in scopes:
        pieces = [piece for page in scope_pages for piece in _pieces(page.content, page.page_number, max_piece_words)]
        start = 0
        while start < len(pieces):
            end, count = start, 0
            while end < len(pieces) and (count + len(pieces[end].text.split()) <= target or end == start):
                count += len(pieces[end].text.split())
                end += 1
            selected = pieces[start:end]
            content = "\n\n".join(piece.text for piece in selected).strip()
            if content:
                drafts.append(ChunkDraft(
                    len(drafts), chapter_id, content,
                    min(piece.page for piece in selected), max(piece.page for piece in selected),
                    count, _hash(content),
                ))
            if end >= len(pieces):
                break
            next_start, overlap_count = end, 0
            while next_start > start and overlap_count < overlap:
                next_start -= 1
                overlap_count += len(pieces[next_start].text.split())
            start = next_start if next_start > start else end
    return drafts


def _status(session: Session, file) -> dict:
    return {
        "digital_file_id": file.id,
        "edition_id": file.edition_id,
        "status": file.rag_status,
        "chunk_count": repository.chunk_count(session, file.id),
        "embedding_model": file.rag_embedding_model,
        "indexed_at": file.rag_indexed_at,
        "error": file.rag_error,
    }


def get_status(session: Session, file_id: uuid.UUID) -> dict:
    file = repository.file(session, file_id)
    if not file:
        raise RAGNotFound
    return _status(session, file)


def _failed(session: Session, file_id: uuid.UUID, message: str) -> None:
    session.rollback()
    file = repository.file(session, file_id, lock=True)
    if file:
        file.rag_status = RAGStatus.FAILED
        file.rag_error = message[:1000]
        session.commit()


async def ingest(
    session: Session,
    file_id: uuid.UUID,
    *,
    force: bool = False,
    provider: EmbeddingProvider | None = None,
) -> dict:
    file = repository.file(session, file_id, lock=True)
    if not file:
        raise RAGNotFound
    if file.rag_status == RAGStatus.INDEXING:
        raise RAGConflict("RAG indexing is already in progress")
    if file.processing_status != ProcessingStatus.READY:
        raise RAGConflict("Document extraction must be READY before RAG indexing")
    pages = repository.pages(session, file.id)
    drafts = chunk_pages(pages, repository.chapters(session, file.edition_id))
    if not drafts:
        _failed(session, file.id, "No usable extracted text is available")
        raise RAGUnavailable("No usable extracted text is available")
    try:
        provider = provider or get_embedding_provider()
    except RuntimeError as exc:
        _failed(session, file.id, str(exc))
        raise RAGUnavailable(str(exc)) from exc
    if provider.dimensions != EMBEDDING_DIMENSIONS:
        message = f"Embedding dimension {provider.dimensions} does not match schema dimension {EMBEDDING_DIMENSIONS}"
        _failed(session, file.id, message)
        raise RAGUnavailable(message)

    old = repository.chunks(session, file.id)
    if not force and old and file.rag_status == RAGStatus.READY and file.rag_embedding_model == provider.model:
        if [item.content_hash for item in old] == [item.content_hash for item in drafts]:
            return _status(session, file)
    file.rag_status = RAGStatus.INDEXING
    file.rag_error = None
    session.commit()

    started = time.monotonic()
    try:
        reusable = {(item.content_hash, item.embedding_model): list(item.embedding) for item in old}
        vectors: list[list[float] | None] = [None] * len(drafts)
        missing = [index for index, item in enumerate(drafts) if force or (item.content_hash, provider.model) not in reusable]
        missing_set = set(missing)
        for index, item in enumerate(drafts):
            if index not in missing_set:
                vectors[index] = reusable[(item.content_hash, provider.model)]
        batch_size = getattr(getattr(provider, "settings", None), "batch_size", 32)
        for offset in range(0, len(missing), batch_size):
            indexes = missing[offset:offset + batch_size]
            embedded = await provider.embed_batch([drafts[index].content for index in indexes])
            if len(embedded) != len(indexes) or any(len(vector) != EMBEDDING_DIMENSIONS for vector in embedded):
                raise ValueError("Embedding provider returned invalid dimensions")
            for index, vector in zip(indexes, embedded):
                vectors[index] = vector

        session.execute(delete(BookChunk).where(BookChunk.digital_file_id == file.id))
        session.add_all([
            BookChunk(
                digital_file_id=file.id, edition_id=file.edition_id, chapter_id=item.chapter_id,
                chunk_index=item.chunk_index, content=item.content, page_start=item.page_start,
                page_end=item.page_end, token_count=item.token_count, content_hash=item.content_hash,
                embedding=vectors[index], embedding_model=provider.model,
            )
            for index, item in enumerate(drafts)
        ])
        file.rag_status = RAGStatus.READY
        file.rag_error = None
        file.rag_embedding_model = provider.model
        file.rag_indexed_at = datetime.now(timezone.utc)
        session.commit()
        logger.info("rag_ingestion_complete", extra={
            "feature": "rag_ingestion", "digital_file_id": str(file.id),
            "edition_id": str(file.edition_id), "chunk_count": len(drafts),
            "embedding_model": provider.model,
            "duration_ms": round((time.monotonic() - started) * 1000), "success": True,
        })
        return _status(session, file)
    except Exception as exc:
        _failed(session, file.id, "RAG indexing failed; the previous chunks were preserved")
        logger.warning("rag_ingestion_failed", extra={
            "feature": "rag_ingestion", "digital_file_id": str(file.id),
            "edition_id": str(file.edition_id), "embedding_model": provider.model,
            "duration_ms": round((time.monotonic() - started) * 1000), "success": False,
        })
        raise RAGUnavailable("RAG indexing failed") from exc


def _cosine(left, right) -> float:
    dot = sum(float(a) * float(b) for a, b in zip(left, right))
    denominator = math.sqrt(sum(float(a) ** 2 for a in left)) * math.sqrt(sum(float(b) ** 2 for b in right))
    return dot / denominator if denominator else 0.0


async def search(
    session: Session,
    edition_id: uuid.UUID,
    query: str,
    *,
    top_k: int = 5,
    provider: EmbeddingProvider | None = None,
) -> list[dict]:
    file = repository.edition_file(session, edition_id)
    if not file:
        raise RAGNotFound
    if file.rag_status != RAGStatus.READY:
        raise RAGConflict("This edition does not have a current READY RAG index")
    provider = provider or get_embedding_provider()
    if provider.dimensions != EMBEDDING_DIMENSIONS or provider.model != file.rag_embedding_model:
        raise RAGUnavailable("Configured embedding model does not match this index")
    started = time.monotonic()
    query_vector = await provider.embed_text(" ".join(query.split()))
    if len(query_vector) != EMBEDDING_DIMENSIONS:
        raise RAGUnavailable("Query embedding dimension does not match the index")

    if session.bind and session.bind.dialect.name == "postgresql":
        distance = BookChunk.embedding.cosine_distance(query_vector).label("distance")
        rows = session.execute(
            select(BookChunk, distance)
            .where(BookChunk.edition_id == edition_id, BookChunk.digital_file_id == file.id)
            .options(joinedload(BookChunk.chapter))
            .order_by(distance)
            .limit(top_k)
        ).all()
        ranked = [(chunk, 1.0 - float(value)) for chunk, value in rows]
    else:
        ranked = sorted(
            ((chunk, _cosine(chunk.embedding, query_vector)) for chunk in repository.edition_chunks(session, edition_id) if chunk.digital_file_id == file.id),
            key=lambda item: item[1], reverse=True,
        )[:top_k]
    logger.info("rag_retrieval_complete", extra={
        "feature": "rag_retrieval", "digital_file_id": str(file.id),
        "edition_id": str(edition_id), "top_k": top_k,
        "duration_ms": round((time.monotonic() - started) * 1000), "success": True,
    })
    return [{
        "chunk_id": chunk.id,
        "content": chunk.content,
        "chapter": {"id": chunk.chapter.id, "title": chunk.chapter.title} if chunk.chapter else None,
        "page_start": chunk.page_start,
        "page_end": chunk.page_end,
        "score": round(max(-1.0, min(1.0, score)), 6),
    } for chunk, score in ranked]
