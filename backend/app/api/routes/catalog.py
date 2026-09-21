import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import DatabaseSession
from app.models import BookType
from app.schemas.catalog import (
    AuthorResponse,
    BookDetail,
    BookSummary,
    CategoryResponse,
    Page,
)
from app.services.catalog import (
    CatalogNotFound,
    get_author,
    get_authors,
    get_categories,
    get_category,
    get_public_book,
    get_public_books,
)


router = APIRouter(tags=["catalog"])


@router.get("/categories", response_model=Page[CategoryResponse])
def categories(
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return get_categories(session, page, page_size)


@router.get("/categories/{identifier}", response_model=CategoryResponse)
def category(identifier: str, session: DatabaseSession):
    try:
        return get_category(session, identifier)
    except CatalogNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found") from exc


@router.get("/authors", response_model=Page[AuthorResponse])
def authors(
    session: DatabaseSession,
    search: Annotated[str | None, Query(max_length=255)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return get_authors(session, page, page_size, search)


@router.get("/authors/{author_id}", response_model=AuthorResponse)
def author(author_id: uuid.UUID, session: DatabaseSession):
    try:
        return get_author(session, author_id)
    except CatalogNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Author not found") from exc


@router.get("/books", response_model=Page[BookSummary])
def books(
    session: DatabaseSession,
    search: Annotated[str | None, Query(max_length=255)] = None,
    category_filter: Annotated[str | None, Query(alias="category", max_length=255)] = None,
    book_type: BookType | None = None,
    language: Annotated[str | None, Query(max_length=50)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return get_public_books(
        session,
        search=search,
        category=category_filter,
        book_type=book_type,
        language=language,
        page=page,
        page_size=page_size,
    )


@router.get("/books/{identifier}", response_model=BookDetail)
def book(identifier: str, session: DatabaseSession):
    try:
        return get_public_book(session, identifier)
    except CatalogNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Book not found") from exc
