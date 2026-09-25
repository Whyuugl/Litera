import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import AdminUser, DatabaseSession
from app.models import LoanStatus, ReservationStatus
from app.schemas.circulation import (
    AdminLoanResponse,
    AdminReservationResponse,
    CheckoutRequest,
    LoanPage,
    ReservationPage,
)
from app.services import circulation as service
from app.services.circulation import (
    CirculationConflict,
    CirculationNotFound,
    InvalidCirculationTransition,
)


router = APIRouter(prefix="/admin", tags=["admin circulation"])


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, CirculationNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Circulation record not found")
    if isinstance(exc, InvalidCirculationTransition):
        return HTTPException(status.HTTP_409_CONFLICT, "This circulation action is no longer available")
    return HTTPException(status.HTTP_409_CONFLICT, str(exc))


@router.get("/reservations", response_model=ReservationPage)
def reservations(
    session: DatabaseSession,
    _: AdminUser,
    reservation_status: Annotated[ReservationStatus | None, Query(alias="status")] = None,
    search: Annotated[str | None, Query(max_length=255)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return service.get_admin_reservations(
        session, status=reservation_status, search=search, page=page, page_size=page_size
    )


@router.get("/reservations/{reservation_id}", response_model=AdminReservationResponse)
def reservation(reservation_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        return service.get_admin_reservation(session, reservation_id)
    except CirculationNotFound as exc:
        raise _error(exc) from exc


@router.post("/reservations/{reservation_id}/ready", response_model=AdminReservationResponse)
def ready(reservation_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        return service.mark_reservation_ready(session, reservation_id)
    except (CirculationNotFound, CirculationConflict, InvalidCirculationTransition) as exc:
        raise _error(exc) from exc


@router.post("/reservations/{reservation_id}/cancel", response_model=AdminReservationResponse)
def cancel(reservation_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        return service.cancel_admin_reservation(session, reservation_id)
    except (CirculationNotFound, InvalidCirculationTransition) as exc:
        raise _error(exc) from exc


@router.post("/loans/checkout", response_model=AdminLoanResponse, status_code=201)
def checkout(data: CheckoutRequest, session: DatabaseSession, admin: AdminUser):
    try:
        return service.checkout(session, data, admin)
    except (CirculationNotFound, CirculationConflict) as exc:
        raise _error(exc) from exc


@router.get("/loans", response_model=LoanPage)
def loans(
    session: DatabaseSession,
    _: AdminUser,
    loan_status: Annotated[LoanStatus | None, Query(alias="status")] = None,
    search: Annotated[str | None, Query(max_length=255)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return service.get_admin_loans(
        session, status=loan_status, search=search, page=page, page_size=page_size
    )


@router.get("/loans/{loan_id}", response_model=AdminLoanResponse)
def loan(loan_id: uuid.UUID, session: DatabaseSession, _: AdminUser):
    try:
        return service.get_admin_loan(session, loan_id)
    except CirculationNotFound as exc:
        raise _error(exc) from exc


@router.post("/loans/{loan_id}/return", response_model=AdminLoanResponse)
def return_book(loan_id: uuid.UUID, session: DatabaseSession, admin: AdminUser):
    try:
        return service.return_loan(session, loan_id, admin)
    except (CirculationNotFound, InvalidCirculationTransition) as exc:
        raise _error(exc) from exc
