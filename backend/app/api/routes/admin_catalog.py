import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.dependencies import AdminUser, DatabaseSession
from app.models import BookStatus, BookType
from app.schemas.catalog import (
    AuthorCreate,
    AuthorResponse,
    AuthorUpdate,
    BookAdminDetail,
    BookAdminResponse,
    BookCopyCreate,
    BookCopyResponse,
    BookCopyUpdate,
    BookCreate,
    BookUpdate,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    DigitalFileAdminResponse,
    DigitalFileCreate,
    DigitalFileUpdate,
    EditionAdminResponse,
    EditionCreate,
    EditionUpdate,
    Page,
)
from app.services import catalog as service
from app.services.catalog import CatalogConflict, CatalogNotFound, InvalidCatalogReference


router = APIRouter(prefix="/admin", tags=["admin catalog"])


def _raise_catalog_error(exc: Exception) -> HTTPException:
    if isinstance(exc, CatalogNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Catalog resource not found")
    if isinstance(exc, InvalidCatalogReference):
        return HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid catalog reference")
    return HTTPException(status.HTTP_409_CONFLICT, str(exc) or "Catalog conflict")


@router.get("/books", response_model=Page[BookAdminResponse])
def books(
    session: DatabaseSession,
    _: AdminUser,
    search: Annotated[str | None, Query(max_length=255)] = None,
    category: Annotated[str | None, Query(max_length=255)] = None,
    book_type: BookType | None = None,
    book_status: Annotated[BookStatus | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return service.get_admin_books(
        session,
        search=search,
        category=category,
        book_type=book_type,
        status=book_status,
        page=page,
        page_size=page_size,
    )


@router.get("/books/{book_id}", response_model=BookAdminDetail)
def book(book_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        return service.get_admin_book(session, book_id)
    except CatalogNotFound as exc:
        raise _raise_catalog_error(exc) from exc


@router.post("/categories", response_model=CategoryResponse, status_code=201)
def create_category(data: CategoryCreate, session: DatabaseSession, _: AdminUser):
    try:
        return service.create_category(session, data)
    except CatalogConflict as exc:
        raise _raise_catalog_error(exc) from exc


@router.patch("/categories/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: uuid.UUID, data: CategoryUpdate, session: DatabaseSession, _: AdminUser
):
    try:
        return service.update_category(session, category_id, data)
    except (CatalogNotFound, CatalogConflict) as exc:
        raise _raise_catalog_error(exc) from exc


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        service.delete_category(session, category_id)
    except (CatalogNotFound, CatalogConflict) as exc:
        raise _raise_catalog_error(exc) from exc
    return Response(status_code=204)


@router.post("/authors", response_model=AuthorResponse, status_code=201)
def create_author(data: AuthorCreate, session: DatabaseSession, _: AdminUser):
    return service.create_author(session, data)


@router.patch("/authors/{author_id}", response_model=AuthorResponse)
def update_author(
    author_id: uuid.UUID, data: AuthorUpdate, session: DatabaseSession, _: AdminUser
):
    try:
        return service.update_author(session, author_id, data)
    except CatalogNotFound as exc:
        raise _raise_catalog_error(exc) from exc


@router.delete("/authors/{author_id}", status_code=204)
def delete_author(author_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        service.delete_author(session, author_id)
    except (CatalogNotFound, CatalogConflict) as exc:
        raise _raise_catalog_error(exc) from exc
    return Response(status_code=204)


@router.post("/books", response_model=BookAdminResponse, status_code=201)
def create_book(data: BookCreate, session: DatabaseSession, admin: AdminUser):
    try:
        return service.create_book(session, data, admin)
    except (CatalogConflict, InvalidCatalogReference) as exc:
        raise _raise_catalog_error(exc) from exc


@router.patch("/books/{book_id}", response_model=BookAdminResponse)
def update_book(
    book_id: uuid.UUID, data: BookUpdate, session: DatabaseSession, _: AdminUser
):
    try:
        return service.update_book(session, book_id, data)
    except (CatalogNotFound, CatalogConflict, InvalidCatalogReference) as exc:
        raise _raise_catalog_error(exc) from exc


@router.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        service.delete_book(session, book_id)
    except (CatalogNotFound, CatalogConflict) as exc:
        raise _raise_catalog_error(exc) from exc
    return Response(status_code=204)


@router.post("/books/{book_id}/editions", response_model=EditionAdminResponse, status_code=201)
def create_edition(
    book_id: uuid.UUID, data: EditionCreate, session: DatabaseSession, _: AdminUser
):
    try:
        return service.create_edition(session, book_id, data)
    except (CatalogConflict, InvalidCatalogReference) as exc:
        raise _raise_catalog_error(exc) from exc


@router.patch("/editions/{edition_id}", response_model=EditionAdminResponse)
def update_edition(
    edition_id: uuid.UUID, data: EditionUpdate, session: DatabaseSession, _: AdminUser
):
    try:
        return service.update_edition(session, edition_id, data)
    except (CatalogNotFound, CatalogConflict) as exc:
        raise _raise_catalog_error(exc) from exc


@router.delete("/editions/{edition_id}", status_code=204)
def delete_edition(edition_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        service.delete_edition(session, edition_id)
    except (CatalogNotFound, CatalogConflict) as exc:
        raise _raise_catalog_error(exc) from exc
    return Response(status_code=204)


@router.post(
    "/editions/{edition_id}/digital-files",
    response_model=DigitalFileAdminResponse,
    status_code=201,
)
def create_digital_file(
    edition_id: uuid.UUID,
    data: DigitalFileCreate,
    session: DatabaseSession,
    admin: AdminUser,
):
    try:
        return service.create_digital_file(session, edition_id, data, admin)
    except InvalidCatalogReference as exc:
        raise _raise_catalog_error(exc) from exc


@router.patch("/digital-files/{file_id}", response_model=DigitalFileAdminResponse)
def update_digital_file(
    file_id: uuid.UUID, data: DigitalFileUpdate, session: DatabaseSession, _: AdminUser
):
    try:
        return service.update_digital_file(session, file_id, data)
    except CatalogNotFound as exc:
        raise _raise_catalog_error(exc) from exc


@router.delete("/digital-files/{file_id}", status_code=204)
def delete_digital_file(file_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        service.delete_digital_file(session, file_id)
    except CatalogNotFound as exc:
        raise _raise_catalog_error(exc) from exc
    return Response(status_code=204)


@router.get("/editions/{edition_id}/copies", response_model=list[BookCopyResponse])
def copies(edition_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        return service.get_book_copies(session, edition_id)
    except CatalogNotFound as exc:
        raise _raise_catalog_error(exc) from exc


@router.post(
    "/editions/{edition_id}/copies", response_model=BookCopyResponse, status_code=201
)
def create_copy(
    edition_id: uuid.UUID, data: BookCopyCreate, session: DatabaseSession, _: AdminUser
):
    try:
        return service.create_book_copy(session, edition_id, data)
    except (CatalogConflict, InvalidCatalogReference) as exc:
        raise _raise_catalog_error(exc) from exc


@router.patch("/book-copies/{copy_id}", response_model=BookCopyResponse)
def update_copy(
    copy_id: uuid.UUID, data: BookCopyUpdate, session: DatabaseSession, _: AdminUser
):
    try:
        return service.update_book_copy(session, copy_id, data)
    except (CatalogNotFound, CatalogConflict) as exc:
        raise _raise_catalog_error(exc) from exc


@router.delete("/book-copies/{copy_id}", status_code=204)
def delete_copy(copy_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        service.delete_book_copy(session, copy_id)
    except CatalogNotFound as exc:
        raise _raise_catalog_error(exc) from exc
    return Response(status_code=204)
