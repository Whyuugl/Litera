import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import BookCopyStatus, LoanStatus, ReservationStatus


class ReservationCreate(BaseModel):
    edition_id: uuid.UUID


class CheckoutRequest(BaseModel):
    user_id: uuid.UUID
    book_copy_id: uuid.UUID
    reservation_id: uuid.UUID | None = None


class CirculationUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str


class CirculationBook(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    slug: str
    cover_url: str | None


class CirculationEdition(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    isbn: str | None
    publisher: str | None
    book: CirculationBook


class CirculationCopy(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    barcode: str
    shelf_location: str | None
    status: BookCopyStatus
    edition: CirculationEdition


class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    edition_id: uuid.UUID
    book_copy_id: uuid.UUID | None
    status: ReservationStatus
    queue_position: int
    reserved_at: datetime
    expires_at: datetime | None
    fulfilled_at: datetime | None
    edition: CirculationEdition
    book_copy: CirculationCopy | None


class AdminReservationResponse(ReservationResponse):
    user: CirculationUser


class ReservationPage(BaseModel):
    items: list[AdminReservationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class LoanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    book_copy_id: uuid.UUID
    borrowed_at: datetime
    due_at: datetime
    returned_at: datetime | None
    status: LoanStatus
    renewal_count: int
    processed_by: uuid.UUID | None
    book_copy: CirculationCopy


class AdminLoanResponse(LoanResponse):
    user: CirculationUser


class LoanPage(BaseModel):
    items: list[AdminLoanResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
