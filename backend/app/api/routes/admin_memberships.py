import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import AdminUser, DatabaseSession
from app.models import MembershipStatus
from app.schemas.memberships import (
    AdminMembershipResponse,
    MembershipPage,
    MembershipReasonRequest,
)
from app.services.memberships import (
    InvalidMembershipTransition,
    MembershipNotFound,
    approve_membership,
    get_admin_membership,
    get_admin_memberships,
    reject_membership,
    suspend_membership,
)


router = APIRouter(prefix="/admin/memberships", tags=["admin memberships"])


def _response(membership) -> AdminMembershipResponse:
    return AdminMembershipResponse.model_validate(membership)


def _not_found_or_conflict(exc: Exception) -> HTTPException:
    if isinstance(exc, MembershipNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Membership not found")
    return HTTPException(status.HTTP_409_CONFLICT, "Invalid membership transition")


@router.get("", response_model=MembershipPage)
def list_all(
    session: DatabaseSession,
    _: AdminUser,
    membership_status: Annotated[MembershipStatus | None, Query(alias="status")] = None,
    search: Annotated[str | None, Query(max_length=255)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> MembershipPage:
    items, total = get_admin_memberships(
        session,
        status=membership_status,
        search=search,
        page=page,
        page_size=page_size,
    )
    return MembershipPage(
        items=[_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{membership_id}", response_model=AdminMembershipResponse)
def detail(
    membership_id: uuid.UUID, session: DatabaseSession, _: AdminUser
) -> AdminMembershipResponse:
    try:
        return _response(get_admin_membership(session, membership_id))
    except MembershipNotFound as exc:
        raise _not_found_or_conflict(exc) from exc


@router.post("/{membership_id}/approve", response_model=AdminMembershipResponse)
def approve(
    membership_id: uuid.UUID, session: DatabaseSession, admin: AdminUser
) -> AdminMembershipResponse:
    try:
        return _response(approve_membership(session, membership_id, admin))
    except (MembershipNotFound, InvalidMembershipTransition) as exc:
        raise _not_found_or_conflict(exc) from exc


@router.post("/{membership_id}/reject", response_model=AdminMembershipResponse)
def reject(
    membership_id: uuid.UUID,
    data: MembershipReasonRequest,
    session: DatabaseSession,
    _: AdminUser,
) -> AdminMembershipResponse:
    try:
        return _response(reject_membership(session, membership_id, data.reason))
    except (MembershipNotFound, InvalidMembershipTransition) as exc:
        raise _not_found_or_conflict(exc) from exc


@router.post("/{membership_id}/suspend", response_model=AdminMembershipResponse)
def suspend(
    membership_id: uuid.UUID,
    data: MembershipReasonRequest,
    session: DatabaseSession,
    _: AdminUser,
) -> AdminMembershipResponse:
    try:
        return _response(suspend_membership(session, membership_id, data.reason))
    except (MembershipNotFound, InvalidMembershipTransition) as exc:
        raise _not_found_or_conflict(exc) from exc
