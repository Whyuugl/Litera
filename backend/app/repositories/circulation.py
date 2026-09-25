import uuid

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Book,
    BookCopy,
    BookCopyStatus,
    Edition,
    Loan,
    LoanStatus,
    Membership,
    Reservation,
    ReservationStatus,
    User,
)


def _reservation_options():
    return (
        joinedload(Reservation.user),
        joinedload(Reservation.edition).joinedload(Edition.book),
        joinedload(Reservation.book_copy)
        .joinedload(BookCopy.edition)
        .joinedload(Edition.book),
    )


def _loan_options():
    return (
        joinedload(Loan.user),
        joinedload(Loan.book_copy).joinedload(BookCopy.edition).joinedload(Edition.book),
    )


def get_edition_for_update(session: Session, edition_id: uuid.UUID) -> Edition | None:
    return session.scalar(
        select(Edition).where(Edition.id == edition_id).with_for_update()
    )


def edition_has_physical_copies(session: Session, edition_id: uuid.UUID) -> bool:
    return session.scalar(
        select(BookCopy.id).where(BookCopy.edition_id == edition_id).limit(1)
    ) is not None


def get_active_reservation(
    session: Session, user_id: uuid.UUID, edition_id: uuid.UUID
) -> Reservation | None:
    return session.scalar(
        select(Reservation).where(
            Reservation.user_id == user_id,
            Reservation.edition_id == edition_id,
            Reservation.status.in_([ReservationStatus.WAITING, ReservationStatus.READY]),
        )
    )


def user_has_active_loan_for_edition(
    session: Session, user_id: uuid.UUID, edition_id: uuid.UUID
) -> bool:
    return session.scalar(
        select(Loan.id)
        .join(Loan.book_copy)
        .where(
            Loan.user_id == user_id,
            BookCopy.edition_id == edition_id,
            Loan.status.in_([LoanStatus.BORROWED, LoanStatus.OVERDUE]),
        )
        .limit(1)
    ) is not None


def next_queue_position(session: Session, edition_id: uuid.UUID) -> int:
    value = session.scalar(
        select(func.max(Reservation.queue_position)).where(
            Reservation.edition_id == edition_id,
            Reservation.status == ReservationStatus.WAITING,
        )
    )
    return (value or 0) + 1


def reindex_waiting_queue(session: Session, edition_id: uuid.UUID) -> None:
    waiting = session.scalars(
        select(Reservation)
        .where(
            Reservation.edition_id == edition_id,
            Reservation.status == ReservationStatus.WAITING,
        )
        .order_by(Reservation.queue_position, Reservation.reserved_at, Reservation.id)
        .with_for_update()
    ).all()
    for position, reservation in enumerate(waiting, 1):
        reservation.queue_position = position


def get_reservation(
    session: Session,
    reservation_id: uuid.UUID,
    *,
    user_id: uuid.UUID | None = None,
    for_update: bool = False,
) -> Reservation | None:
    statement = select(Reservation).where(Reservation.id == reservation_id)
    if user_id:
        statement = statement.where(Reservation.user_id == user_id)
    if for_update:
        statement = statement.with_for_update(of=Reservation)
    return session.scalar(statement.options(*_reservation_options()))


def list_user_reservations(session: Session, user_id: uuid.UUID) -> list[Reservation]:
    return list(
        session.scalars(
            select(Reservation)
            .where(Reservation.user_id == user_id)
            .options(*_reservation_options())
            .order_by(Reservation.reserved_at.desc())
        ).unique().all()
    )


def list_admin_reservations(
    session: Session,
    *,
    status: ReservationStatus | None,
    search: str | None,
    page: int,
    page_size: int,
):
    filters = []
    if status:
        filters.append(Reservation.status == status)
    statement = (
        select(Reservation)
        .join(Reservation.user)
        .join(Reservation.edition)
        .join(Edition.book)
    )
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(or_(User.name.ilike(pattern), User.email.ilike(pattern), Book.title.ilike(pattern)))
    statement = statement.where(*filters)
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    items = session.scalars(
        statement.options(*_reservation_options())
        .order_by(Reservation.reserved_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).unique().all()
    return list(items), total


def get_available_copy_for_update(
    session: Session, edition_id: uuid.UUID, copy_id: uuid.UUID | None = None
) -> BookCopy | None:
    statement = select(BookCopy).where(
        BookCopy.edition_id == edition_id,
        BookCopy.status == BookCopyStatus.AVAILABLE,
    )
    if copy_id:
        statement = statement.where(BookCopy.id == copy_id)
    return session.scalar(statement.order_by(BookCopy.barcode).with_for_update())


def get_copy_for_update(session: Session, copy_id: uuid.UUID) -> BookCopy | None:
    return session.scalar(
        select(BookCopy)
        .where(BookCopy.id == copy_id)
        .options(joinedload(BookCopy.edition).joinedload(Edition.book))
        .with_for_update(of=BookCopy)
    )


def first_waiting_for_update(
    session: Session, edition_id: uuid.UUID
) -> Reservation | None:
    return session.scalar(
        select(Reservation)
        .where(
            Reservation.edition_id == edition_id,
            Reservation.status == ReservationStatus.WAITING,
        )
        .order_by(Reservation.queue_position, Reservation.reserved_at, Reservation.id)
        .with_for_update()
    )


def waiting_exists(session: Session, edition_id: uuid.UUID) -> bool:
    return session.scalar(
        select(Reservation.id).where(
            Reservation.edition_id == edition_id,
            Reservation.status == ReservationStatus.WAITING,
        ).limit(1)
    ) is not None


def expired_ready_ids(session: Session, now) -> list[uuid.UUID]:
    return list(
        session.scalars(
            select(Reservation.id).where(
                Reservation.status == ReservationStatus.READY,
                Reservation.expires_at.is_not(None),
                Reservation.expires_at <= now,
            )
        ).all()
    )


def get_user_and_membership_for_update(
    session: Session, user_id: uuid.UUID
) -> tuple[User | None, Membership | None]:
    user = session.scalar(select(User).where(User.id == user_id).with_for_update())
    membership = session.scalar(
        select(Membership).where(Membership.user_id == user_id).with_for_update()
    )
    return user, membership


def active_loan_count(session: Session, user_id: uuid.UUID) -> int:
    return session.scalar(
        select(func.count()).select_from(Loan).where(
            Loan.user_id == user_id,
            Loan.status.in_([LoanStatus.BORROWED, LoanStatus.OVERDUE]),
        )
    ) or 0


def get_loan(
    session: Session,
    loan_id: uuid.UUID,
    *,
    user_id: uuid.UUID | None = None,
    for_update: bool = False,
) -> Loan | None:
    statement = select(Loan).where(Loan.id == loan_id)
    if user_id:
        statement = statement.where(Loan.user_id == user_id)
    if for_update:
        statement = statement.with_for_update(of=Loan)
    return session.scalar(statement.options(*_loan_options()))


def list_user_loans(session: Session, user_id: uuid.UUID, view: str | None) -> list[Loan]:
    statement = select(Loan).where(Loan.user_id == user_id)
    if view == "active":
        statement = statement.where(Loan.status.in_([LoanStatus.BORROWED, LoanStatus.OVERDUE]))
    elif view == "history":
        statement = statement.where(Loan.status.in_([LoanStatus.RETURNED, LoanStatus.LOST]))
    elif view == "overdue":
        statement = statement.where(Loan.status == LoanStatus.OVERDUE)
    return list(
        session.scalars(
            statement.options(*_loan_options()).order_by(Loan.borrowed_at.desc())
        ).unique().all()
    )


def list_admin_loans(
    session: Session,
    *,
    status: LoanStatus | None,
    search: str | None,
    page: int,
    page_size: int,
):
    filters = []
    if status:
        filters.append(Loan.status == status)
    statement = (
        select(Loan)
        .join(Loan.user)
        .join(Loan.book_copy)
        .join(BookCopy.edition)
        .join(Edition.book)
    )
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(User.name.ilike(pattern), User.email.ilike(pattern), Book.title.ilike(pattern), BookCopy.barcode.ilike(pattern))
        )
    statement = statement.where(*filters)
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    items = session.scalars(
        statement.options(*_loan_options())
        .order_by(Loan.borrowed_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).unique().all()
    return list(items), total


def normalize_overdue(session: Session, now) -> None:
    session.execute(
        update(Loan)
        .where(
            Loan.status == LoanStatus.BORROWED,
            Loan.returned_at.is_(None),
            Loan.due_at < now,
        )
        .values(status=LoanStatus.OVERDUE)
    )
