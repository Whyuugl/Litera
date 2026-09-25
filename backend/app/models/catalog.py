import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class MembershipStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    SUSPENDED = "SUSPENDED"


class BookType(str, enum.Enum):
    FICTION = "FICTION"
    NON_FICTION = "NON_FICTION"
    EDUCATIONAL = "EDUCATIONAL"
    REFERENCE = "REFERENCE"


class BookStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class DigitalFileType(str, enum.Enum):
    PDF = "PDF"
    EPUB = "EPUB"


class ProcessingStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class AccessLevel(str, enum.Enum):
    PUBLIC = "PUBLIC"
    REGISTERED = "REGISTERED"
    MEMBER = "MEMBER"


class BookCopyStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    BORROWED = "BORROWED"
    RESERVED = "RESERVED"
    LOST = "LOST"
    DAMAGED = "DAMAGED"
    MAINTENANCE = "MAINTENANCE"


class UUIDTimestampMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(UUIDTimestampMixin, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.USER, server_default=UserRole.USER.value
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    membership: Mapped[Optional["Membership"]] = relationship(
        back_populates="user", foreign_keys="Membership.user_id", uselist=False
    )
    approved_memberships: Mapped[list["Membership"]] = relationship(
        back_populates="approver", foreign_keys="Membership.approved_by"
    )
    created_books: Mapped[list["Book"]] = relationship(back_populates="creator")
    uploaded_files: Mapped[list["DigitalFile"]] = relationship(back_populates="uploader")
    refresh_sessions: Mapped[list["RefreshSession"]] = relationship(back_populates="user")
    loans: Mapped[list["Loan"]] = relationship(
        back_populates="user", foreign_keys="Loan.user_id"
    )
    processed_loans: Mapped[list["Loan"]] = relationship(
        back_populates="processor", foreign_keys="Loan.processed_by"
    )
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="user")
    reading_progress: Mapped[list["ReadingProgress"]] = relationship(back_populates="user")
    bookmarks: Mapped[list["Bookmark"]] = relationship(back_populates="user")
    quiz_attempts: Mapped[list["QuizAttempt"]] = relationship(back_populates="user")


class Membership(UUIDTimestampMixin, Base):
    __tablename__ = "memberships"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    member_number: Mapped[Optional[str]] = mapped_column(String, unique=True)
    status: Mapped[MembershipStatus] = mapped_column(
        Enum(MembershipStatus, name="membership_status"),
        default=MembershipStatus.PENDING,
        server_default=MembershipStatus.PENDING.value,
    )
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)
    suspension_reason: Mapped[Optional[str]] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="membership", foreign_keys=[user_id])
    approver: Mapped[Optional[User]] = relationship(
        back_populates="approved_memberships", foreign_keys=[approved_by]
    )


class Category(UUIDTimestampMixin, Base):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String, unique=True)
    slug: Mapped[str] = mapped_column(String, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)

    books: Mapped[list["Book"]] = relationship(back_populates="category")


class Author(UUIDTimestampMixin, Base):
    __tablename__ = "authors"

    name: Mapped[str] = mapped_column(String)
    bio: Mapped[Optional[str]] = mapped_column(Text)
    photo_url: Mapped[Optional[str]] = mapped_column(String)

    books: Mapped[list["Book"]] = relationship(
        secondary="book_authors", back_populates="authors"
    )


class BookAuthor(Base):
    __tablename__ = "book_authors"

    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id"), primary_key=True)
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("authors.id"), primary_key=True, index=True
    )


class Book(UUIDTimestampMixin, Base):
    __tablename__ = "books"

    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id"), index=True)
    title: Mapped[str] = mapped_column(String)
    slug: Mapped[str] = mapped_column(String, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String)
    cover_url: Mapped[Optional[str]] = mapped_column(String)
    book_type: Mapped[BookType] = mapped_column(Enum(BookType, name="book_type"))
    status: Mapped[BookStatus] = mapped_column(
        Enum(BookStatus, name="book_status"), default=BookStatus.DRAFT, server_default=BookStatus.DRAFT.value
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)

    category: Mapped[Category] = relationship(back_populates="books")
    authors: Mapped[list[Author]] = relationship(
        secondary="book_authors", back_populates="books"
    )
    editions: Mapped[list["Edition"]] = relationship(back_populates="book")
    creator: Mapped[User] = relationship(back_populates="created_books")


class Edition(UUIDTimestampMixin, Base):
    __tablename__ = "editions"

    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id"), index=True)
    isbn: Mapped[Optional[str]] = mapped_column(String, unique=True)
    publisher: Mapped[Optional[str]] = mapped_column(String)
    edition_number: Mapped[Optional[str]] = mapped_column(String)
    publication_year: Mapped[Optional[int]] = mapped_column(Integer)
    page_count: Mapped[Optional[int]] = mapped_column(Integer)
    language: Mapped[Optional[str]] = mapped_column(String)

    book: Mapped[Book] = relationship(back_populates="editions")
    digital_files: Mapped[list["DigitalFile"]] = relationship(back_populates="edition")
    physical_copies: Mapped[list["BookCopy"]] = relationship(back_populates="edition")
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="edition")
    chapters: Mapped[list["Chapter"]] = relationship(back_populates="edition")
    reading_progress: Mapped[list["ReadingProgress"]] = relationship(back_populates="edition")
    bookmarks: Mapped[list["Bookmark"]] = relationship(back_populates="edition")
    ai_summaries: Mapped[list["AISummary"]] = relationship(back_populates="edition")


class DigitalFile(UUIDTimestampMixin, Base):
    __tablename__ = "digital_files"

    edition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("editions.id"), index=True)
    file_url: Mapped[str] = mapped_column(String)
    storage_key: Mapped[Optional[str]] = mapped_column(String, unique=True)
    original_filename: Mapped[Optional[str]] = mapped_column(String)
    mime_type: Mapped[Optional[str]] = mapped_column(String)
    file_type: Mapped[DigitalFileType] = mapped_column(
        Enum(DigitalFileType, name="digital_file_type")
    )
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger)
    access_level: Mapped[AccessLevel] = mapped_column(Enum(AccessLevel, name="access_level"))
    allow_download: Mapped[bool] = mapped_column(default=False, server_default="false")
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, name="processing_status"),
        default=ProcessingStatus.UPLOADED,
        server_default=ProcessingStatus.UPLOADED.value,
    )
    processing_error: Mapped[Optional[str]] = mapped_column(Text)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    edition: Mapped[Edition] = relationship(back_populates="digital_files")
    uploader: Mapped[User] = relationship(back_populates="uploaded_files")
    pages: Mapped[list["DocumentPage"]] = relationship(
        back_populates="digital_file", cascade="all, delete-orphan"
    )


class BookCopy(UUIDTimestampMixin, Base):
    __tablename__ = "book_copies"

    edition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("editions.id"), index=True)
    barcode: Mapped[str] = mapped_column(String, unique=True)
    shelf_location: Mapped[Optional[str]] = mapped_column(String)
    status: Mapped[BookCopyStatus] = mapped_column(
        Enum(BookCopyStatus, name="book_copy_status"),
        default=BookCopyStatus.AVAILABLE,
        server_default=BookCopyStatus.AVAILABLE.value,
    )
    condition: Mapped[Optional[str]] = mapped_column(String)
    acquired_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    edition: Mapped[Edition] = relationship(back_populates="physical_copies")
    loans: Mapped[list["Loan"]] = relationship(back_populates="book_copy")
    reservation_holds: Mapped[list["Reservation"]] = relationship(back_populates="book_copy")
