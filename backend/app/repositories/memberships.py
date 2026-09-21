import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, contains_eager

from app.models import Membership, MembershipStatus, User


def get_membership_by_user(
    session: Session, user_id: uuid.UUID, *, for_update: bool = False
) -> Membership | None:
    statement = select(Membership).where(Membership.user_id == user_id)
    if for_update:
        statement = statement.with_for_update()
    return session.scalar(statement)


def get_membership_by_id(
    session: Session, membership_id: uuid.UUID, *, for_update: bool = False
) -> Membership | None:
    statement = (
        select(Membership)
        .join(Membership.user)
        .options(contains_eager(Membership.user))
        .where(Membership.id == membership_id)
    )
    if for_update:
        statement = statement.with_for_update(of=Membership)
    return session.scalar(statement)


def list_memberships(
    session: Session,
    *,
    status: MembershipStatus | None,
    search: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Membership], int]:
    filters = []
    if status:
        filters.append(Membership.status == status)
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                User.name.ilike(pattern),
                User.email.ilike(pattern),
                Membership.member_number.ilike(pattern),
            )
        )

    base = select(Membership).join(Membership.user).where(*filters)
    total = session.scalar(
        select(func.count()).select_from(Membership).join(Membership.user).where(*filters)
    ) or 0
    items = session.scalars(
        base.options(contains_eager(Membership.user))
        .order_by(Membership.applied_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(items), total
