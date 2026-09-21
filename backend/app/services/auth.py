import hmac
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    DUMMY_PASSWORD_HASH,
    auth_settings,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    token_fingerprint,
    verify_password,
)
from app.models import RefreshSession, User, UserRole
from app.repositories.refresh_sessions import get_refresh_session_for_update
from app.repositories.users import get_user_by_email, get_user_by_id
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserRegister


class EmailAlreadyRegistered(Exception):
    pass


class InvalidCredentials(Exception):
    pass


class InactiveAccount(Exception):
    pass


class InvalidRefreshToken(Exception):
    pass


def register_user(session: Session, data: UserRegister) -> User:
    if get_user_by_email(session, data.email):
        raise EmailAlreadyRegistered
    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=UserRole.USER,
        is_active=True,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise EmailAlreadyRegistered from exc
    session.refresh(user)
    return user


def _issue_tokens(session: Session, user: User) -> TokenResponse:
    access_token, _ = create_access_token(user.id)
    refresh_token, jti, expires_at = create_refresh_token(user.id)
    session.add(
        RefreshSession(
            user_id=user.id,
            jti=jti,
            token_hash=token_fingerprint(refresh_token),
            expires_at=expires_at,
        )
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=auth_settings().access_minutes * 60,
    )


def login(session: Session, data: LoginRequest) -> TokenResponse:
    user = get_user_by_email(session, data.email)
    password_is_valid = verify_password(
        data.password, user.password_hash if user else DUMMY_PASSWORD_HASH
    )
    if not user or not password_is_valid:
        raise InvalidCredentials
    if not user.is_active:
        raise InactiveAccount
    response = _issue_tokens(session, user)
    session.commit()
    return response


def rotate_refresh_token(session: Session, data: RefreshRequest) -> TokenResponse:
    try:
        claims = decode_token(data.refresh_token, "refresh")
    except ValueError as exc:
        raise InvalidRefreshToken from exc

    refresh_session = get_refresh_session_for_update(session, claims.jti)
    expected_hash = token_fingerprint(data.refresh_token)
    if (
        not refresh_session
        or refresh_session.revoked_at is not None
        or refresh_session.user_id != claims.user_id
        or not hmac.compare_digest(refresh_session.token_hash, expected_hash)
    ):
        raise InvalidRefreshToken

    user = get_user_by_id(session, claims.user_id)
    if not user or not user.is_active:
        raise InvalidRefreshToken

    refresh_session.revoked_at = datetime.now(timezone.utc)
    response = _issue_tokens(session, user)
    session.flush()
    new_claims = decode_token(response.refresh_token, "refresh")
    refresh_session.replaced_by_jti = new_claims.jti
    session.commit()
    return response


def logout(session: Session, data: RefreshRequest) -> None:
    try:
        claims = decode_token(data.refresh_token, "refresh")
    except ValueError as exc:
        raise InvalidRefreshToken from exc
    refresh_session = get_refresh_session_for_update(session, claims.jti)
    if refresh_session and refresh_session.user_id == claims.user_id and hmac.compare_digest(
        refresh_session.token_hash, token_fingerprint(data.refresh_token)
    ):
        if refresh_session.revoked_at is None:
            refresh_session.revoked_at = datetime.now(timezone.utc)
            session.commit()
