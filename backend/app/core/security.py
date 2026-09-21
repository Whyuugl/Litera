import hashlib
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import jwt
from jwt import PyJWTError
from pwdlib import PasswordHash


@dataclass(frozen=True)
class AuthSettings:
    secret_key: str
    algorithm: str
    access_minutes: int
    refresh_days: int


@dataclass(frozen=True)
class TokenClaims:
    user_id: uuid.UUID
    jti: uuid.UUID
    expires_at: datetime


@lru_cache
def auth_settings() -> AuthSettings:
    secret = os.getenv("JWT_SECRET_KEY", "")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    if len(secret) < 32 or secret.startswith("replace-with"):
        raise RuntimeError("JWT_SECRET_KEY must contain at least 32 non-placeholder characters")
    if algorithm not in {"HS256", "HS384", "HS512"}:
        raise RuntimeError("JWT_ALGORITHM must be HS256, HS384, or HS512")
    try:
        access_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
        refresh_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    except ValueError as exc:
        raise RuntimeError("Token expiration settings must be integers") from exc
    if access_minutes <= 0 or refresh_days <= 0:
        raise RuntimeError("Token expiration settings must be positive")
    return AuthSettings(secret, algorithm, access_minutes, refresh_days)


password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hash.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    return password_hash.verify(password, encoded)


def _create_token(user_id: uuid.UUID, token_type: str, lifetime: timedelta) -> tuple[str, uuid.UUID, datetime]:
    settings = auth_settings()
    now = datetime.now(timezone.utc)
    expires_at = now + lifetime
    jti = uuid.uuid4()
    token = jwt.encode(
        {
            "sub": str(user_id),
            "type": token_type,
            "iat": now,
            "exp": expires_at,
            "jti": str(jti),
        },
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    return token, jti, expires_at


def create_access_token(user_id: uuid.UUID) -> tuple[str, datetime]:
    settings = auth_settings()
    token, _, expires_at = _create_token(
        user_id, "access", timedelta(minutes=settings.access_minutes)
    )
    return token, expires_at


def create_refresh_token(user_id: uuid.UUID) -> tuple[str, uuid.UUID, datetime]:
    settings = auth_settings()
    return _create_token(user_id, "refresh", timedelta(days=settings.refresh_days))


def decode_token(token: str, expected_type: str) -> TokenClaims:
    settings = auth_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"require": ["sub", "type", "iat", "exp", "jti"]},
        )
        if payload["type"] != expected_type:
            raise ValueError
        return TokenClaims(
            user_id=uuid.UUID(payload["sub"]),
            jti=uuid.UUID(payload["jti"]),
            expires_at=datetime.fromtimestamp(payload["exp"], timezone.utc),
        )
    except (PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid or expired token") from exc


def token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
