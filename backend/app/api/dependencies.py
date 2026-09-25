from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.security import decode_token
from app.models import Membership, User, UserRole
from app.repositories.users import get_user_by_id
from app.services.memberships import ActiveMembershipRequired, require_active_membership


bearer = HTTPBearer(auto_error=False)
DatabaseSession = Annotated[Session, Depends(get_session)]


def get_current_user(
    session: DatabaseSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials or credentials.scheme.lower() != "bearer":
        raise unauthorized
    try:
        claims = decode_token(credentials.credentials, "access")
    except ValueError as exc:
        raise unauthorized from exc
    user = get_user_by_id(session, claims.user_id)
    if not user or not user.is_active:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_optional_user(
    session: DatabaseSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User | None:
    if not credentials:
        return None
    return get_current_user(session, credentials)


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def require_admin(current_user: CurrentUser) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]


def require_active_member(
    session: DatabaseSession, current_user: CurrentUser
) -> Membership:
    try:
        return require_active_membership(session, current_user)
    except ActiveMembershipRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active membership required",
        ) from exc


ActiveMembership = Annotated[Membership, Depends(require_active_member)]
