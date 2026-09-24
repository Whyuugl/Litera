import uuid
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import AccessLevel, BookCopyStatus, BookStatus, BookType, DigitalFileType


T = TypeVar("T")


def _required_text(value: str | None) -> str | None:
    if value is not None and not (value := value.strip()):
        raise ValueError("Value cannot be blank")
    return value


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int
    total_pages: int


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    description: str | None = None

    _normalize_name = field_validator("name")(_required_text)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None

    _normalize_name = field_validator("name")(_required_text)


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str | None


class CategorySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str


class AuthorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    bio: str | None = None
    photo_url: str | None = Field(default=None, max_length=2048)

    _normalize_name = field_validator("name")(_required_text)


class AuthorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    bio: str | None = None
    photo_url: str | None = Field(default=None, max_length=2048)

    _normalize_name = field_validator("name")(_required_text)


class AuthorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    bio: str | None
    photo_url: str | None


class AuthorSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class BookCreate(BaseModel):
    category_id: uuid.UUID
    author_ids: list[uuid.UUID] = Field(min_length=1)
    title: str = Field(min_length=1, max_length=500)
    slug: str | None = Field(default=None, max_length=255)
    description: str | None = None
    language: str = Field(min_length=1, max_length=50)
    cover_url: str | None = Field(default=None, max_length=2048)
    book_type: BookType
    status: BookStatus = BookStatus.DRAFT

    _normalize_text = field_validator("title", "language")(_required_text)

    @field_validator("author_ids")
    @classmethod
    def unique_authors(cls, value: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Author IDs must be unique")
        return value


class BookUpdate(BaseModel):
    category_id: uuid.UUID | None = None
    author_ids: list[uuid.UUID] | None = Field(default=None, min_length=1)
    title: str | None = Field(default=None, min_length=1, max_length=500)
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    language: str | None = Field(default=None, min_length=1, max_length=50)
    cover_url: str | None = Field(default=None, max_length=2048)
    book_type: BookType | None = None
    status: BookStatus | None = None

    _normalize_text = field_validator("title", "language")(_required_text)

    @field_validator("author_ids")
    @classmethod
    def unique_authors(cls, value: list[uuid.UUID] | None) -> list[uuid.UUID] | None:
        if value is not None and len(value) != len(set(value)):
            raise ValueError("Author IDs must be unique")
        return value


class BookSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    slug: str
    description: str | None
    cover_url: str | None
    language: str
    book_type: BookType
    category: CategorySummary
    authors: list[AuthorSummary]


class DigitalAvailability(BaseModel):
    file_type: DigitalFileType
    access_level: AccessLevel
    available: bool = True


class PhysicalAvailability(BaseModel):
    total_copies: int
    available_copies: int


class EditionPublicResponse(BaseModel):
    id: uuid.UUID
    isbn: str | None
    publisher: str | None
    edition_number: str | None
    publication_year: int | None
    page_count: int | None
    language: str | None
    digital: list[DigitalAvailability]
    physical: PhysicalAvailability


class BookDetail(BookSummary):
    editions: list[EditionPublicResponse]


class BookAdminResponse(BookSummary):
    status: BookStatus


class EditionCreate(BaseModel):
    isbn: str | None = Field(default=None, max_length=32)
    publisher: str | None = Field(default=None, max_length=255)
    edition_number: str | None = Field(default=None, max_length=50)
    publication_year: int | None = Field(default=None, ge=1)
    page_count: int | None = Field(default=None, ge=1)
    language: str | None = Field(default=None, max_length=50)

    @field_validator("isbn")
    @classmethod
    def normalize_isbn(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("publication_year")
    @classmethod
    def sensible_year(cls, value: int | None) -> int | None:
        if value is not None and value > datetime.now().year + 1:
            raise ValueError("Publication year cannot be in the distant future")
        return value


class EditionUpdate(EditionCreate):
    pass


class EditionAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    book_id: uuid.UUID
    isbn: str | None
    publisher: str | None
    edition_number: str | None
    publication_year: int | None
    page_count: int | None
    language: str | None


class DigitalFileCreate(BaseModel):
    file_url: str = Field(min_length=1, max_length=2048)
    file_type: DigitalFileType
    file_size: int | None = Field(default=None, ge=0)
    access_level: AccessLevel

    _normalize_url = field_validator("file_url")(_required_text)


class DigitalFileUpdate(BaseModel):
    file_url: str | None = Field(default=None, min_length=1, max_length=2048)
    file_type: DigitalFileType | None = None
    file_size: int | None = Field(default=None, ge=0)
    access_level: AccessLevel | None = None

    _normalize_url = field_validator("file_url")(_required_text)


class DigitalFileAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    edition_id: uuid.UUID
    file_url: str
    file_type: DigitalFileType
    file_size: int | None
    access_level: AccessLevel
    uploaded_at: datetime


class BookCopyCreate(BaseModel):
    barcode: str = Field(min_length=1, max_length=255)
    shelf_location: str | None = Field(default=None, max_length=255)
    status: BookCopyStatus = BookCopyStatus.AVAILABLE
    condition: str | None = Field(default=None, max_length=255)
    acquired_at: datetime | None = None

    _normalize_barcode = field_validator("barcode")(_required_text)


class BookCopyUpdate(BaseModel):
    barcode: str | None = Field(default=None, min_length=1, max_length=255)
    shelf_location: str | None = Field(default=None, max_length=255)
    status: BookCopyStatus | None = None
    condition: str | None = Field(default=None, max_length=255)
    acquired_at: datetime | None = None

    _normalize_barcode = field_validator("barcode")(_required_text)


class BookCopyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    edition_id: uuid.UUID
    barcode: str
    shelf_location: str | None
    status: BookCopyStatus
    condition: str | None
    acquired_at: datetime | None


class EditionAdminDetail(EditionAdminResponse):
    digital_files: list[DigitalFileAdminResponse]
    physical_copies: list[BookCopyResponse]


class BookAdminDetail(BookAdminResponse):
    editions: list[EditionAdminDetail]
