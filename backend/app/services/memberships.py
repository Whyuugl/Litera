import os
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Membership, MembershipStatus, User, UserRole
from app.repositories.memberships import (
    get_membership_by_id,
    get_membership_by_user,
    list_memberships,
)


class MembershipNotFound(Exception):
    pass


class MembershipConflict(Exception):
    pass


class MembershipApplicationForbidden(Exception):
    pass


class InvalidMembershipTransition(Exception):
    pass


class ActiveMembershipRequired(Exception):
    pass


@lru_cache
def membership_duration_days() -> int:
    try:
        duration = int(os.getenv("MEMBERSHIP_DURATION_DAYS", "365"))
    except ValueError as exc:
        raise RuntimeError("MEMBERSHIP_DURATION_DAYS must be an integer") from exc
    if duration <= 0:
        raise RuntimeError("MEMBERSHIP_DURATION_DAYS must be positive")
    return duration


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _expired(membership: Membership, now: datetime | None = None) -> bool:
    if membership.expires_at is None:
        return False
    expires_at = membership.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= (now or _now())


def normalize_expiration(session: Session, membership: Membership) -> Membership:
    if membership.status == MembershipStatus.ACTIVE and _expired(membership):
        membership.status = MembershipStatus.EXPIRED
        session.commit()
    return membership


def apply_for_membership(session: Session, user: User) -> Membership:
    if user.role != UserRole.USER:
        raise MembershipApplicationForbidden
    membership = get_membership_by_user(session, user.id, for_update=True)
    if membership and membership.status == MembershipStatus.ACTIVE and _expired(membership):
        membership.status = MembershipStatus.EXPIRED
    if membership and membership.status not in {
        MembershipStatus.REJECTED,
        MembershipStatus.EXPIRED,
    }:
        raise MembershipConflict

    now = _now()
    if membership is None:
        membership = Membership(user_id=user.id, status=MembershipStatus.PENDING)
        session.add(membership)
    else:
        membership.status = MembershipStatus.PENDING
        membership.applied_at = now
        membership.member_number = None
        membership.approved_at = None
        membership.approved_by = None
        membership.expires_at = None
        membership.rejection_reason = None
        membership.suspension_reason = None

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise MembershipConflict from exc
    session.refresh(membership)
    return membership


def get_current_membership(session: Session, user: User) -> Membership | None:
    membership = get_membership_by_user(session, user.id)
    return normalize_expiration(session, membership) if membership else None


def get_admin_memberships(
    session: Session,
    *,
    status: MembershipStatus | None,
    search: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Membership], int]:
    session.execute(
        update(Membership)
        .where(
            Membership.status == MembershipStatus.ACTIVE,
            Membership.expires_at.is_not(None),
            Membership.expires_at <= _now(),
        )
        .values(status=MembershipStatus.EXPIRED)
    )
    session.commit()
    return list_memberships(
        session, status=status, search=search, page=page, page_size=page_size
    )


def get_admin_membership(session: Session, membership_id: uuid.UUID) -> Membership:
    membership = get_membership_by_id(session, membership_id)
    if not membership:
        raise MembershipNotFound
    return normalize_expiration(session, membership)


def approve_membership(
    session: Session, membership_id: uuid.UUID, admin: User
) -> Membership:
    membership = get_membership_by_id(session, membership_id, for_update=True)
    if not membership:
        raise MembershipNotFound
    if membership.status != MembershipStatus.PENDING:
        raise InvalidMembershipTransition

    now = _now()
    membership.status = MembershipStatus.ACTIVE
    membership.approved_by = admin.id
    membership.approved_at = now
    membership.expires_at = now + timedelta(days=membership_duration_days())
    membership.member_number = f"LIT-{now.year}-{membership.id.hex.upper()}"
    membership.rejection_reason = None
    membership.suspension_reason = None
    session.commit()
    return membership


def reject_membership(
    session: Session, membership_id: uuid.UUID, reason: str
) -> Membership:
    membership = get_membership_by_id(session, membership_id, for_update=True)
    if not membership:
        raise MembershipNotFound
    if membership.status != MembershipStatus.PENDING:
        raise InvalidMembershipTransition

    membership.status = MembershipStatus.REJECTED
    membership.rejection_reason = reason
    membership.member_number = None
    membership.approved_by = None
    membership.approved_at = None
    membership.expires_at = None
    membership.suspension_reason = None
    session.commit()
    return membership


def suspend_membership(
    session: Session, membership_id: uuid.UUID, reason: str
) -> Membership:
    membership = get_membership_by_id(session, membership_id, for_update=True)
    if not membership:
        raise MembershipNotFound
    normalize_expiration(session, membership)
    if membership.status != MembershipStatus.ACTIVE:
        raise InvalidMembershipTransition

    membership.status = MembershipStatus.SUSPENDED
    membership.suspension_reason = reason
    session.commit()
    return membership


def require_active_membership(session: Session, user: User) -> Membership:
    membership = get_membership_by_user(session, user.id)
    if not membership:
        raise ActiveMembershipRequired
    normalize_expiration(session, membership)
    if (
        membership.status != MembershipStatus.ACTIVE
        or membership.expires_at is None
        or _expired(membership)
    ):
        raise ActiveMembershipRequired
    return membership
