"""phase 6 physical circulation

Revision ID: b7619aaf3c24
Revises: 369074c6389d
Create Date: 2026-09-25 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7619aaf3c24"
down_revision: Union[str, None] = "369074c6389d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    loan_status = sa.Enum("BORROWED", "RETURNED", "OVERDUE", "LOST", name="loan_status")
    reservation_status = sa.Enum(
        "WAITING", "READY", "FULFILLED", "CANCELLED", "EXPIRED",
        name="reservation_status",
    )
    op.create_table(
        "loans",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("book_copy_id", sa.Uuid(), nullable=False),
        sa.Column("borrowed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", loan_status, server_default="BORROWED", nullable=False),
        sa.Column("renewal_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("processed_by", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["book_copy_id"], ["book_copies.id"]),
        sa.ForeignKeyConstraint(["processed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_loans_user_id", "loans", ["user_id"])
    op.create_index("ix_loans_book_copy_id", "loans", ["book_copy_id"])
    op.create_index("ix_loans_processed_by", "loans", ["processed_by"])
    op.create_index("ix_loans_user_status", "loans", ["user_id", "status"])
    op.create_index("ix_loans_due_at", "loans", ["due_at"])
    op.create_index(
        "uq_loans_active_copy", "loans", ["book_copy_id"], unique=True,
        postgresql_where=sa.text("status IN ('BORROWED', 'OVERDUE')"),
    )

    op.create_table(
        "reservations",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("edition_id", sa.Uuid(), nullable=False),
        sa.Column("book_copy_id", sa.Uuid(), nullable=True),
        sa.Column("status", reservation_status, server_default="WAITING", nullable=False),
        sa.Column("queue_position", sa.Integer(), nullable=False),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["book_copy_id"], ["book_copies.id"]),
        sa.ForeignKeyConstraint(["edition_id"], ["editions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reservations_user_id", "reservations", ["user_id"])
    op.create_index("ix_reservations_edition_id", "reservations", ["edition_id"])
    op.create_index("ix_reservations_book_copy_id", "reservations", ["book_copy_id"])
    op.create_index("ix_reservations_edition_status", "reservations", ["edition_id", "status"])
    op.create_index("ix_reservations_user_status", "reservations", ["user_id", "status"])
    op.create_index("ix_reservations_queue", "reservations", ["edition_id", "status", "queue_position"])
    op.create_index(
        "uq_reservations_active_user_edition", "reservations", ["user_id", "edition_id"],
        unique=True, postgresql_where=sa.text("status IN ('WAITING', 'READY')"),
    )
    op.create_index(
        "uq_reservations_ready_copy", "reservations", ["book_copy_id"],
        unique=True, postgresql_where=sa.text("status = 'READY'"),
    )


def downgrade() -> None:
    op.drop_table("reservations")
    op.drop_table("loans")
    sa.Enum(name="reservation_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="loan_status").drop(op.get_bind(), checkfirst=True)
