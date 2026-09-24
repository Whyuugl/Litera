import math
import re
import unicodedata
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Author, Book, BookCopy, BookCopyStatus, Category, DigitalFile, Edition, User
from app.repositories import catalog as repository
from app.schemas.catalog import (
    AuthorCreate,
    AuthorUpdate,
    BookAdminDetail,
    BookAdminResponse,
    BookCopyCreate,
    BookCopyUpdate,
    BookCreate,
    BookDetail,
    BookUpdate,
    CategoryCreate,
    CategoryUpdate,
    DigitalAvailability,
    DigitalFileCreate,
    DigitalFileUpdate,
    EditionAdminDetail,
    EditionCreate,
    EditionPublicResponse,
    EditionUpdate,
    Page,
    PhysicalAvailability,
)


class CatalogNotFound(Exception):
    pass


class CatalogConflict(Exception):
    pass


class InvalidCatalogReference(Exception):
    pass


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise CatalogConflict("A valid slug could not be generated")
    return slug


def _commit(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise CatalogConflict("A unique catalog value already exists") from exc


def _page(items, total: int, page: int, page_size: int) -> Page:
    return Page(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=math.ceil(total / page_size) if total else 0,
    )


def get_categories(session: Session, page: int, page_size: int) -> Page:
    items, total = repository.list_categories(session, page, page_size)
    return _page(items, total, page, page_size)


def get_category(session: Session, identifier: str) -> Category:
    category = repository.get_category(session, identifier)
    if not category:
        raise CatalogNotFound
    return category


def create_category(session: Session, data: CategoryCreate) -> Category:
    category = Category(
        name=data.name.strip(),
        slug=slugify(data.slug or data.name),
        description=data.description,
    )
    session.add(category)
    _commit(session)
    session.refresh(category)
    return category


def update_category(
    session: Session, category_id: uuid.UUID, data: CategoryUpdate
) -> Category:
    category = session.get(Category, category_id)
    if not category:
        raise CatalogNotFound
    fields = data.model_dump(exclude_unset=True)
    if fields.get("name") is not None:
        category.name = fields["name"].strip()
    if fields.get("slug") is not None:
        category.slug = slugify(fields["slug"])
    if "description" in fields:
        category.description = fields["description"]
    _commit(session)
    return category


def delete_category(session: Session, category_id: uuid.UUID) -> None:
    category = session.get(Category, category_id)
    if not category:
        raise CatalogNotFound
    if repository.category_has_books(session, category_id):
        raise CatalogConflict("Category still contains books")
    session.delete(category)
    _commit(session)


def get_authors(session: Session, page: int, page_size: int, search: str | None) -> Page:
    items, total = repository.list_authors(session, page, page_size, search)
    return _page(items, total, page, page_size)


def get_author(session: Session, author_id: uuid.UUID) -> Author:
    author = repository.get_author(session, author_id)
    if not author:
        raise CatalogNotFound
    return author


def create_author(session: Session, data: AuthorCreate) -> Author:
    author = Author(name=data.name.strip(), bio=data.bio, photo_url=data.photo_url)
    session.add(author)
    _commit(session)
    session.refresh(author)
    return author


def update_author(session: Session, author_id: uuid.UUID, data: AuthorUpdate) -> Author:
    author = repository.get_author(session, author_id)
    if not author:
        raise CatalogNotFound
    fields = data.model_dump(exclude_unset=True)
    if fields.get("name") is not None:
        author.name = fields["name"].strip()
    for field in ("bio", "photo_url"):
        if field in fields:
            setattr(author, field, fields[field])
    _commit(session)
    return author


def delete_author(session: Session, author_id: uuid.UUID) -> None:
    author = repository.get_author(session, author_id)
    if not author:
        raise CatalogNotFound
    if repository.author_has_books(session, author_id):
        raise CatalogConflict("Author is assigned to books")
    session.delete(author)
    _commit(session)


def get_public_books(session: Session, **filters) -> Page:
    items, total = repository.list_public_books(session, **filters)
    return _page(items, total, filters["page"], filters["page_size"])


def get_admin_books(session: Session, **filters) -> Page:
    items, total = repository.list_admin_books(session, **filters)
    return _page(items, total, filters["page"], filters["page_size"])


def get_admin_book(session: Session, book_id: uuid.UUID) -> BookAdminDetail:
    book = repository.get_admin_book_detail(session, book_id)
    if not book:
        raise CatalogNotFound
    return BookAdminDetail(
        **BookAdminResponse.model_validate(book).model_dump(),
        editions=[
            EditionAdminDetail(
                id=edition.id,
                book_id=edition.book_id,
                isbn=edition.isbn,
                publisher=edition.publisher,
                edition_number=edition.edition_number,
                publication_year=edition.publication_year,
                page_count=edition.page_count,
                language=edition.language,
                digital_files=edition.digital_files,
                physical_copies=edition.physical_copies,
            )
            for edition in book.editions
        ],
    )


def _book_detail(book: Book) -> BookDetail:
    editions = []
    for edition in book.editions:
        editions.append(
            EditionPublicResponse(
                id=edition.id,
                isbn=edition.isbn,
                publisher=edition.publisher,
                edition_number=edition.edition_number,
                publication_year=edition.publication_year,
                page_count=edition.page_count,
                language=edition.language,
                digital=[
                    DigitalAvailability(
                        file_type=file.file_type, access_level=file.access_level
                    )
                    for file in edition.digital_files
                ],
                physical=PhysicalAvailability(
                    total_copies=len(edition.physical_copies),
                    available_copies=sum(
                        copy.status == BookCopyStatus.AVAILABLE
                        for copy in edition.physical_copies
                    ),
                ),
            )
        )
    return BookDetail(
        **BookAdminResponse.model_validate(book).model_dump(exclude={"status"}),
        editions=editions,
    )


def get_public_book(session: Session, identifier: str) -> BookDetail:
    book = repository.get_public_book(session, identifier)
    if not book:
        raise CatalogNotFound
    return _book_detail(book)


def _unique_book_slug(session: Session, value: str, exclude_id=None) -> str:
    base = slugify(value)
    candidate = base
    suffix = 2
    while repository.slug_exists(session, Book, candidate, exclude_id):
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _resolve_book_relations(
    session: Session, category_id: uuid.UUID, author_ids: list[uuid.UUID]
) -> tuple[Category, list[Author]]:
    category = session.get(Category, category_id)
    authors = repository.get_authors(session, author_ids)
    if not category or len(authors) != len(author_ids):
        raise InvalidCatalogReference
    return category, authors


def create_book(session: Session, data: BookCreate, admin: User) -> Book:
    category, authors = _resolve_book_relations(session, data.category_id, data.author_ids)
    book = Book(
        category=category,
        authors=authors,
        title=data.title.strip(),
        slug=_unique_book_slug(session, data.slug or data.title),
        description=data.description,
        language=data.language.strip(),
        cover_url=data.cover_url,
        book_type=data.book_type,
        status=data.status,
        created_by=admin.id,
    )
    session.add(book)
    _commit(session)
    session.refresh(book)
    return book


def update_book(session: Session, book_id: uuid.UUID, data: BookUpdate) -> Book:
    book = repository.get_book(session, book_id)
    if not book:
        raise CatalogNotFound
    fields = data.model_dump(exclude_unset=True)
    if fields.get("category_id") is not None:
        category = session.get(Category, fields.pop("category_id"))
        if not category:
            raise InvalidCatalogReference
        book.category = category
    if fields.get("author_ids") is not None:
        author_ids = fields.pop("author_ids")
        authors = repository.get_authors(session, author_ids)
        if len(authors) != len(author_ids):
            raise InvalidCatalogReference
        book.authors = authors
    if fields.get("slug") is not None:
        book.slug = _unique_book_slug(session, fields.pop("slug"), book.id)
    for field in ("title", "language"):
        if fields.get(field) is not None:
            setattr(book, field, fields.pop(field).strip())
    for field, value in fields.items():
        if value is not None or field in {"description", "cover_url"}:
            setattr(book, field, value)
    _commit(session)
    return book


def delete_book(session: Session, book_id: uuid.UUID) -> None:
    book = repository.get_book(session, book_id)
    if not book:
        raise CatalogNotFound
    if repository.book_has_editions(session, book_id):
        raise CatalogConflict("Book still contains editions")
    session.delete(book)
    _commit(session)


def create_edition(session: Session, book_id: uuid.UUID, data: EditionCreate) -> Edition:
    if not session.get(Book, book_id):
        raise InvalidCatalogReference
    edition = Edition(book_id=book_id, **data.model_dump())
    session.add(edition)
    _commit(session)
    session.refresh(edition)
    return edition


def update_edition(session: Session, edition_id: uuid.UUID, data: EditionUpdate) -> Edition:
    edition = repository.get_edition(session, edition_id)
    if not edition:
        raise CatalogNotFound
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(edition, field, value)
    _commit(session)
    return edition


def delete_edition(session: Session, edition_id: uuid.UUID) -> None:
    edition = repository.get_edition(session, edition_id)
    if not edition:
        raise CatalogNotFound
    if repository.edition_has_resources(session, edition_id):
        raise CatalogConflict("Edition still contains digital files or physical copies")
    session.delete(edition)
    _commit(session)


def create_digital_file(
    session: Session, edition_id: uuid.UUID, data: DigitalFileCreate, admin: User
) -> DigitalFile:
    if not repository.get_edition(session, edition_id):
        raise InvalidCatalogReference
    digital_file = DigitalFile(
        edition_id=edition_id, uploaded_by=admin.id, **data.model_dump()
    )
    session.add(digital_file)
    _commit(session)
    session.refresh(digital_file)
    return digital_file


def update_digital_file(
    session: Session, file_id: uuid.UUID, data: DigitalFileUpdate
) -> DigitalFile:
    digital_file = repository.get_digital_file(session, file_id)
    if not digital_file:
        raise CatalogNotFound
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None or field == "file_size":
            setattr(digital_file, field, value)
    _commit(session)
    return digital_file


def delete_digital_file(session: Session, file_id: uuid.UUID) -> None:
    digital_file = repository.get_digital_file(session, file_id)
    if not digital_file:
        raise CatalogNotFound
    session.delete(digital_file)
    _commit(session)


def get_book_copies(session: Session, edition_id: uuid.UUID) -> list[BookCopy]:
    if not repository.get_edition(session, edition_id):
        raise CatalogNotFound
    return repository.list_book_copies(session, edition_id)


def create_book_copy(
    session: Session, edition_id: uuid.UUID, data: BookCopyCreate
) -> BookCopy:
    if not repository.get_edition(session, edition_id):
        raise InvalidCatalogReference
    copy = BookCopy(edition_id=edition_id, **data.model_dump())
    session.add(copy)
    _commit(session)
    session.refresh(copy)
    return copy


def update_book_copy(
    session: Session, copy_id: uuid.UUID, data: BookCopyUpdate
) -> BookCopy:
    copy = repository.get_book_copy(session, copy_id)
    if not copy:
        raise CatalogNotFound
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None or field in {"shelf_location", "condition", "acquired_at"}:
            setattr(copy, field, value)
    _commit(session)
    return copy


def delete_book_copy(session: Session, copy_id: uuid.UUID) -> None:
    copy = repository.get_book_copy(session, copy_id)
    if not copy:
        raise CatalogNotFound
    session.delete(copy)
    _commit(session)
