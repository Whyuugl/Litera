import math
import os
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    BookCopy,
    BookCopyStatus,
    Loan,
    LoanStatus,
    Membership,
    MembershipStatus,
    Reservation,
    ReservationStatus,
    User,
)
from app.repositories import circulation as repository
from app.schemas.circulation import CheckoutRequest, LoanPage, ReservationCreate, ReservationPage


class CirculationNotFound(Exception):
    pass


class CirculationConflict(Exception):
    pass


class InvalidCirculationTransition(Exception):
    pass


@lru_cache
def loan_duration_days() -> int:
    return _positive_setting("LOAN_DURATION_DAYS", 14)


@lru_cache
def reservation_hold_days() -> int:
    return _positive_setting("RESERVATION_HOLD_DAYS", 3)


@lru_cache
def max_active_loans() -> int:
    return _positive_setting("MAX_ACTIVE_LOANS_PER_MEMBER", 5)


def _positive_setting(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be positive")
    return value


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _membership_is_active(membership: Membership | None, now: datetime) -> bool:
    return bool(
        membership
        and membership.status == MembershipStatus.ACTIVE
        and membership.expires_at
        and _aware(membership.expires_at) > now
    )


def _commit(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise CirculationConflict("The circulation record changed; please try again") from exc


def _promote_waiting(
    session: Session, edition_id: uuid.UUID, copy: BookCopy, now: datetime
) -> Reservation | None:
    waiting = repository.first_waiting_for_update(session, edition_id)
    if not waiting:
        copy.status = BookCopyStatus.AVAILABLE
        return None
    waiting.status = ReservationStatus.READY
    waiting.book_copy_id = copy.id
    waiting.queue_position = 0
    waiting.expires_at = now + timedelta(days=reservation_hold_days())
    copy.status = BookCopyStatus.RESERVED
    repository.reindex_waiting_queue(session, edition_id)
    return waiting


def _expire_ready(session: Session) -> None:
    now = _now()
    changed = False
    for reservation_id in repository.expired_ready_ids(session, now):
        reservation = repository.get_reservation(session, reservation_id, for_update=True)
        if not reservation or reservation.status != ReservationStatus.READY:
            continue
        copy = repository.get_copy_for_update(session, reservation.book_copy_id) if reservation.book_copy_id else None
        reservation.status = ReservationStatus.EXPIRED
        reservation.book_copy_id = None
        changed = True
        if copy:
            _promote_waiting(session, reservation.edition_id, copy, now)
    if changed:
        _commit(session)


def create_reservation(
    session: Session, data: ReservationCreate, user: User
) -> Reservation:
    edition = repository.get_edition_for_update(session, data.edition_id)
    if not edition:
        raise CirculationNotFound
    if not repository.edition_has_physical_copies(session, edition.id):
        raise CirculationConflict("This edition has no physical copies")
    if repository.get_active_reservation(session, user.id, edition.id):
        raise CirculationConflict("You already have an active reservation for this edition")
    if repository.user_has_active_loan_for_edition(session, user.id, edition.id):
        raise CirculationConflict("You already have this edition on loan")

    reservation = Reservation(
        user_id=user.id,
        edition_id=edition.id,
        status=ReservationStatus.WAITING,
        queue_position=repository.next_queue_position(session, edition.id),
        reserved_at=_now(),
    )
    session.add(reservation)
    _commit(session)
    session.refresh(reservation)
    return reservation


def get_user_reservations(session: Session, user: User) -> list[Reservation]:
    _expire_ready(session)
    return repository.list_user_reservations(session, user.id)


def get_user_reservation(
    session: Session, reservation_id: uuid.UUID, user: User
) -> Reservation:
    _expire_ready(session)
    reservation = repository.get_reservation(session, reservation_id, user_id=user.id)
    if not reservation:
        raise CirculationNotFound
    return reservation


def cancel_user_reservation(
    session: Session, reservation_id: uuid.UUID, user: User
) -> Reservation:
    reservation = repository.get_reservation(
        session, reservation_id, user_id=user.id, for_update=True
    )
    if not reservation:
        raise CirculationNotFound
    return _cancel_reservation(session, reservation)


def _cancel_reservation(session: Session, reservation: Reservation) -> Reservation:
    if reservation.status not in {ReservationStatus.WAITING, ReservationStatus.READY}:
        raise InvalidCirculationTransition
    edition_id = reservation.edition_id
    copy = repository.get_copy_for_update(session, reservation.book_copy_id) if reservation.book_copy_id else None
    reservation.status = ReservationStatus.CANCELLED
    reservation.book_copy_id = None
    reservation.expires_at = None
    if copy:
        _promote_waiting(session, edition_id, copy, _now())
    else:
        repository.reindex_waiting_queue(session, edition_id)
    _commit(session)
    return reservation


def get_admin_reservations(session: Session, **filters) -> ReservationPage:
    _expire_ready(session)
    items, total = repository.list_admin_reservations(session, **filters)
    return ReservationPage(
        items=items,
        total=total,
        page=filters["page"],
        page_size=filters["page_size"],
        total_pages=math.ceil(total / filters["page_size"]) if total else 0,
    )


def get_admin_reservation(session: Session, reservation_id: uuid.UUID) -> Reservation:
    _expire_ready(session)
    reservation = repository.get_reservation(session, reservation_id)
    if not reservation:
        raise CirculationNotFound
    return reservation


def mark_reservation_ready(session: Session, reservation_id: uuid.UUID) -> Reservation:
    reservation = repository.get_reservation(session, reservation_id, for_update=True)
    if not reservation:
        raise CirculationNotFound
    if reservation.status != ReservationStatus.WAITING:
        raise InvalidCirculationTransition
    first = repository.first_waiting_for_update(session, reservation.edition_id)
    if not first or first.id != reservation.id:
        raise CirculationConflict("Earlier reservations must be prepared first")
    copy = repository.get_available_copy_for_update(session, reservation.edition_id)
    if not copy:
        raise CirculationConflict("No physical copy is available for this reservation")
    reservation.status = ReservationStatus.READY
    reservation.book_copy_id = copy.id
    reservation.queue_position = 0
    reservation.expires_at = _now() + timedelta(days=reservation_hold_days())
    copy.status = BookCopyStatus.RESERVED
    repository.reindex_waiting_queue(session, reservation.edition_id)
    _commit(session)
    return reservation


def cancel_admin_reservation(session: Session, reservation_id: uuid.UUID) -> Reservation:
    reservation = repository.get_reservation(session, reservation_id, for_update=True)
    if not reservation:
        raise CirculationNotFound
    return _cancel_reservation(session, reservation)


def checkout(session: Session, data: CheckoutRequest, admin: User) -> Loan:
    now = _now()
    user, membership = repository.get_user_and_membership_for_update(session, data.user_id)
    if not user:
        raise CirculationNotFound
    if not user.is_active or not _membership_is_active(membership, now):
        raise CirculationConflict("Borrower must have an active membership")
    if repository.active_loan_count(session, user.id) >= max_active_loans():
        raise CirculationConflict("Member has reached the active loan limit")

    copy = repository.get_copy_for_update(session, data.book_copy_id)
    if not copy:
        raise CirculationNotFound
    reservation = None
    if data.reservation_id:
        reservation = repository.get_reservation(session, data.reservation_id, for_update=True)
        if (
            not reservation
            or reservation.user_id != user.id
            or reservation.status != ReservationStatus.READY
            or reservation.edition_id != copy.edition_id
            or reservation.book_copy_id != copy.id
            or copy.status != BookCopyStatus.RESERVED
        ):
            raise CirculationConflict("Reservation does not match this member and copy")
    else:
        if copy.status != BookCopyStatus.AVAILABLE:
            raise CirculationConflict("Physical copy is not available")
        if repository.waiting_exists(session, copy.edition_id):
            raise CirculationConflict("This edition has a reservation queue")

    loan = Loan(
        user_id=user.id,
        book_copy_id=copy.id,
        borrowed_at=now,
        due_at=now + timedelta(days=loan_duration_days()),
        status=LoanStatus.BORROWED,
        processed_by=admin.id,
    )
    session.add(loan)
    copy.status = BookCopyStatus.BORROWED
    if reservation:
        reservation.status = ReservationStatus.FULFILLED
        reservation.fulfilled_at = now
        reservation.expires_at = None
    _commit(session)
    session.refresh(loan)
    return loan


def _normalize_overdue(session: Session) -> None:
    repository.normalize_overdue(session, _now())
    _commit(session)


def get_user_loans(session: Session, user: User, view: str | None) -> list[Loan]:
    _normalize_overdue(session)
    return repository.list_user_loans(session, user.id, view)


def get_user_loan(session: Session, loan_id: uuid.UUID, user: User) -> Loan:
    _normalize_overdue(session)
    loan = repository.get_loan(session, loan_id, user_id=user.id)
    if not loan:
        raise CirculationNotFound
    return loan


def get_admin_loans(session: Session, **filters) -> LoanPage:
    _normalize_overdue(session)
    items, total = repository.list_admin_loans(session, **filters)
    return LoanPage(
        items=items,
        total=total,
        page=filters["page"],
        page_size=filters["page_size"],
        total_pages=math.ceil(total / filters["page_size"]) if total else 0,
    )


def get_admin_loan(session: Session, loan_id: uuid.UUID) -> Loan:
    _normalize_overdue(session)
    loan = repository.get_loan(session, loan_id)
    if not loan:
        raise CirculationNotFound
    return loan


def return_loan(session: Session, loan_id: uuid.UUID, admin: User) -> Loan:
    loan = repository.get_loan(session, loan_id, for_update=True)
    if not loan:
        raise CirculationNotFound
    if loan.status not in {LoanStatus.BORROWED, LoanStatus.OVERDUE} or loan.returned_at:
        raise InvalidCirculationTransition
    copy = repository.get_copy_for_update(session, loan.book_copy_id)
    if not copy:
        raise CirculationNotFound
    now = _now()
    loan.status = LoanStatus.RETURNED
    loan.returned_at = now
    loan.processed_by = admin.id
    _promote_waiting(session, copy.edition_id, copy, now)
    _commit(session)
    return loan
