import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.dependencies import ActiveMembership, CurrentUser, DatabaseSession
from app.schemas.circulation import LoanResponse, ReservationCreate, ReservationResponse
from app.services import circulation as service
from app.services.circulation import (
    CirculationConflict,
    CirculationNotFound,
    InvalidCirculationTransition,
)


router = APIRouter(tags=["circulation"])


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, CirculationNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Circulation record not found")
    if isinstance(exc, InvalidCirculationTransition):
        return HTTPException(status.HTTP_409_CONFLICT, "This circulation action is no longer available")
    return HTTPException(status.HTTP_409_CONFLICT, str(exc))


@router.post("/reservations", response_model=ReservationResponse, status_code=201)
def create_reservation(
    data: ReservationCreate,
    session: DatabaseSession,
    user: CurrentUser,
    _: ActiveMembership,
):
    try:
        return service.create_reservation(session, data, user)
    except (CirculationNotFound, CirculationConflict) as exc:
        raise _error(exc) from exc


@router.get("/reservations/me", response_model=list[ReservationResponse])
def reservations(session: DatabaseSession, user: CurrentUser):
    return service.get_user_reservations(session, user)


@router.get("/reservations/{reservation_id}", response_model=ReservationResponse)
def reservation(reservation_id: uuid.UUID, session: DatabaseSession, user: CurrentUser):
    try:
        return service.get_user_reservation(session, reservation_id, user)
    except CirculationNotFound as exc:
        raise _error(exc) from exc


@router.delete("/reservations/{reservation_id}", status_code=204)
def cancel_reservation(
    reservation_id: uuid.UUID, session: DatabaseSession, user: CurrentUser
):
    try:
        service.cancel_user_reservation(session, reservation_id, user)
    except (CirculationNotFound, InvalidCirculationTransition) as exc:
        raise _error(exc) from exc
    return Response(status_code=204)


@router.get("/loans/me", response_model=list[LoanResponse])
def loans(
    session: DatabaseSession,
    user: CurrentUser,
    view: Annotated[Literal["active", "history", "overdue"] | None, Query()] = None,
):
    return service.get_user_loans(session, user, view)


@router.get("/loans/{loan_id}", response_model=LoanResponse)
def loan(loan_id: uuid.UUID, session: DatabaseSession, user: CurrentUser):
    try:
        return service.get_user_loan(session, loan_id, user)
    except CirculationNotFound as exc:
        raise _error(exc) from exc
