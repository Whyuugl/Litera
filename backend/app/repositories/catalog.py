import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    Author,
    Book,
    BookCopy,
    BookStatus,
    BookType,
    Category,
    DigitalFile,
    Edition,
)


def paginate(session: Session, statement, page: int, page_size: int):
    total = session.scalar(
        select(func.count()).select_from(statement.order_by(None).subquery())
    ) or 0
    items = session.scalars(
        statement.offset((page - 1) * page_size).limit(page_size)
    ).unique().all()
    return list(items), total


def list_categories(session: Session, page: int, page_size: int):
    return paginate(session, select(Category).order_by(Category.name), page, page_size)


def get_category(session: Session, identifier: str) -> Category | None:
    try:
        category_id = uuid.UUID(identifier)
    except ValueError:
        return session.scalar(select(Category).where(Category.slug == identifier))
    return session.get(Category, category_id)


def list_authors(
    session: Session, page: int, page_size: int, search: str | None
):
    statement = select(Author)
    if search:
        statement = statement.where(Author.name.ilike(f"%{search.strip()}%"))
    return paginate(session, statement.order_by(Author.name), page, page_size)


def get_author(session: Session, author_id: uuid.UUID) -> Author | None:
    return session.get(Author, author_id)


def get_authors(session: Session, author_ids: list[uuid.UUID]) -> list[Author]:
    return list(session.scalars(select(Author).where(Author.id.in_(author_ids))).all())


def list_public_books(
    session: Session,
    *,
    page: int,
    page_size: int,
    search: str | None,
    category: str | None,
    book_type: BookType | None,
    language: str | None,
):
    statement = select(Book).where(Book.status == BookStatus.PUBLISHED)
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.outerjoin(Book.authors).where(
            or_(Book.title.ilike(pattern), Author.name.ilike(pattern))
        )
    if category:
        statement = statement.join(Book.category).where(Category.slug == category)
    if book_type:
        statement = statement.where(Book.book_type == book_type)
    if language:
        statement = statement.where(func.lower(Book.language) == language.lower())
    statement = statement.distinct().options(
        joinedload(Book.category), selectinload(Book.authors)
    )
    return paginate(session, statement.order_by(Book.title), page, page_size)


def get_public_book(session: Session, identifier: str) -> Book | None:
    try:
        condition = Book.id == uuid.UUID(identifier)
    except ValueError:
        condition = Book.slug == identifier
    return session.scalar(
        select(Book)
        .where(condition, Book.status == BookStatus.PUBLISHED)
        .options(
            joinedload(Book.category),
            selectinload(Book.authors),
            selectinload(Book.editions).selectinload(Edition.digital_files),
            selectinload(Book.editions).selectinload(Edition.physical_copies),
        )
    )


def get_book(session: Session, book_id: uuid.UUID) -> Book | None:
    return session.scalar(
        select(Book)
        .where(Book.id == book_id)
        .options(joinedload(Book.category), selectinload(Book.authors))
    )


def slug_exists(
    session: Session, model: type[Book] | type[Category], slug: str, exclude_id=None
) -> bool:
    statement = select(model.id).where(model.slug == slug)
    if exclude_id:
        statement = statement.where(model.id != exclude_id)
    return session.scalar(statement) is not None


def category_has_books(session: Session, category_id: uuid.UUID) -> bool:
    return session.scalar(select(Book.id).where(Book.category_id == category_id).limit(1)) is not None


def author_has_books(session: Session, author_id: uuid.UUID) -> bool:
    return session.scalar(
        select(Book.id).join(Book.authors).where(Author.id == author_id).limit(1)
    ) is not None


def get_edition(session: Session, edition_id: uuid.UUID) -> Edition | None:
    return session.get(Edition, edition_id)


def book_has_editions(session: Session, book_id: uuid.UUID) -> bool:
    return session.scalar(select(Edition.id).where(Edition.book_id == book_id).limit(1)) is not None


def edition_has_resources(session: Session, edition_id: uuid.UUID) -> bool:
    digital = session.scalar(
        select(DigitalFile.id).where(DigitalFile.edition_id == edition_id).limit(1)
    )
    physical = session.scalar(
        select(BookCopy.id).where(BookCopy.edition_id == edition_id).limit(1)
    )
    return digital is not None or physical is not None


def get_digital_file(session: Session, file_id: uuid.UUID) -> DigitalFile | None:
    return session.get(DigitalFile, file_id)


def get_book_copy(session: Session, copy_id: uuid.UUID) -> BookCopy | None:
    return session.get(BookCopy, copy_id)


def list_book_copies(session: Session, edition_id: uuid.UUID) -> list[BookCopy]:
    return list(
        session.scalars(
            select(BookCopy)
            .where(BookCopy.edition_id == edition_id)
            .order_by(BookCopy.barcode)
        ).all()
    )
