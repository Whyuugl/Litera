import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models import RAGStatus


class RAGIndexResponse(BaseModel):
    digital_file_id: uuid.UUID
    edition_id: uuid.UUID
    status: RAGStatus
    chunk_count: int
    embedding_model: str | None
    indexed_at: datetime | None
    error: str | None


class RetrievalSearch(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=10)


class RetrievalChapter(BaseModel):
    id: uuid.UUID
    title: str


class RetrievalResult(BaseModel):
    chunk_id: uuid.UUID
    content: str
    chapter: RetrievalChapter | None
    page_start: int
    page_end: int
    score: float
