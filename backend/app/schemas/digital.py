import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import AccessLevel, ProcessingStatus


class ReaderBook(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    slug: str
    cover_url: str | None


class ChapterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    edition_id: uuid.UUID
    chapter_number: int
    title: str
    page_start: int
    page_end: int


class ChapterCreate(BaseModel):
    chapter_number: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=500)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)


class ChapterUpdate(BaseModel):
    chapter_number: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=500)
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)


class ReaderResponse(BaseModel):
    edition_id: uuid.UUID
    digital_file_id: uuid.UUID
    access_level: AccessLevel
    processing_status: ProcessingStatus
    page_count: int
    book: ReaderBook
    chapters: list[ChapterResponse]
    learning_available: bool
    summary_chapter_ids: list[uuid.UUID]


class ProgressUpdate(BaseModel):
    current_page: int = Field(ge=1)
    chapter_id: uuid.UUID | None = None
    position_data: dict[str, Any] | None = None


class ProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    edition_id: uuid.UUID
    chapter_id: uuid.UUID | None
    progress_percentage: float
    current_page: int
    position_data: dict[str, Any] | None
    started_at: datetime
    last_read_at: datetime
    completed_at: datetime | None


class ProgressListItem(ProgressResponse):
    book: ReaderBook
    chapter: ChapterResponse | None


class BookmarkCreate(BaseModel):
    edition_id: uuid.UUID
    chapter_id: uuid.UUID | None = None
    page_number: int = Field(ge=1)
    position_data: dict[str, Any] | None = None
    note: str | None = Field(default=None, max_length=1000)


class BookmarkUpdate(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class BookmarkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    edition_id: uuid.UUID
    chapter_id: uuid.UUID | None
    page_number: int
    position_data: dict[str, Any] | None
    note: str | None
    created_at: datetime


class DigitalUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    edition_id: uuid.UUID
    original_filename: str | None
    mime_type: str | None
    file_size: int | None
    access_level: AccessLevel
    allow_download: bool
    processing_status: ProcessingStatus
    processing_error: str | None
    processed_at: datetime | None
    uploaded_at: datetime
