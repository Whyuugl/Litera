from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUser, DatabaseSession
from app.schemas.memberships import CurrentMembershipResponse, MembershipResponse
from app.services.memberships import (
    MembershipConflict,
    MembershipApplicationForbidden,
    apply_for_membership,
    get_current_membership,
)


router = APIRouter(prefix="/memberships", tags=["memberships"])


@router.post("/apply", response_model=MembershipResponse)
def apply(session: DatabaseSession, user: CurrentUser) -> MembershipResponse:
    try:
        return MembershipResponse.model_validate(apply_for_membership(session, user))
    except MembershipConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Current membership cannot be reapplied",
        ) from exc
    except MembershipApplicationForbidden as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users can apply for membership",
        ) from exc


@router.get("/me", response_model=CurrentMembershipResponse)
def current_membership(
    session: DatabaseSession, user: CurrentUser
) -> CurrentMembershipResponse:
    membership = get_current_membership(session, user)
    return CurrentMembershipResponse(
        membership=MembershipResponse.model_validate(membership) if membership else None
    )
