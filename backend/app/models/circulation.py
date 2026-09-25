import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.catalog import BookCopy, Edition, UUIDTimestampMixin, User


class LoanStatus(str, enum.Enum):
    BORROWED = "BORROWED"
    RETURNED = "RETURNED"
    OVERDUE = "OVERDUE"
    LOST = "LOST"


class ReservationStatus(str, enum.Enum):
    WAITING = "WAITING"
    READY = "READY"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class Loan(UUIDTimestampMixin, Base):
    __tablename__ = "loans"
    __table_args__ = (
        Index("ix_loans_user_status", "user_id", "status"),
        Index("ix_loans_due_at", "due_at"),
        Index(
            "uq_loans_active_copy",
            "book_copy_id",
            unique=True,
            postgresql_where=text("status IN ('BORROWED', 'OVERDUE')"),
            sqlite_where=text("status IN ('BORROWED', 'OVERDUE')"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    book_copy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("book_copies.id"), index=True)
    borrowed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    returned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[LoanStatus] = mapped_column(
        Enum(LoanStatus, name="loan_status"),
        default=LoanStatus.BORROWED,
        server_default=LoanStatus.BORROWED.value,
    )
    renewal_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    processed_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"), index=True)

    user: Mapped[User] = relationship(foreign_keys=[user_id], back_populates="loans")
    processor: Mapped[Optional[User]] = relationship(
        foreign_keys=[processed_by], back_populates="processed_loans"
    )
    book_copy: Mapped[BookCopy] = relationship(back_populates="loans")


class Reservation(UUIDTimestampMixin, Base):
    __tablename__ = "reservations"
    __table_args__ = (
        Index("ix_reservations_edition_status", "edition_id", "status"),
        Index("ix_reservations_user_status", "user_id", "status"),
        Index("ix_reservations_queue", "edition_id", "status", "queue_position"),
        Index(
            "uq_reservations_active_user_edition",
            "user_id",
            "edition_id",
            unique=True,
            postgresql_where=text("status IN ('WAITING', 'READY')"),
            sqlite_where=text("status IN ('WAITING', 'READY')"),
        ),
        Index(
            "uq_reservations_ready_copy",
            "book_copy_id",
            unique=True,
            postgresql_where=text("status = 'READY'"),
            sqlite_where=text("status = 'READY'"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    edition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("editions.id"), index=True)
    book_copy_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("book_copies.id"), index=True
    )
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus, name="reservation_status"),
        default=ReservationStatus.WAITING,
        server_default=ReservationStatus.WAITING.value,
    )
    queue_position: Mapped[int] = mapped_column(Integer)
    reserved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    fulfilled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="reservations")
    edition: Mapped[Edition] = relationship(back_populates="reservations")
    book_copy: Mapped[Optional[BookCopy]] = relationship(back_populates="reservation_holds")
