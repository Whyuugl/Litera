from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserRegister, UserResponse
from app.services.auth import (
    EmailAlreadyRegistered,
    InactiveAccount,
    InvalidCredentials,
    InvalidRefreshToken,
    login,
    logout,
    register_user,
    rotate_refresh_token,
)


router = APIRouter(prefix="/auth", tags=["authentication"])
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: UserRegister, session: DatabaseSession) -> UserResponse:
    try:
        return UserResponse.model_validate(register_user(session, data))
    except EmailAlreadyRegistered as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from exc


@router.post("/login", response_model=TokenResponse)
def log_in(data: LoginRequest, session: DatabaseSession) -> TokenResponse:
    try:
        return login(session, data)
    except InvalidCredentials as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password") from exc
    except InactiveAccount as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is inactive") from exc


@router.post("/refresh", response_model=TokenResponse)
def refresh(data: RefreshRequest, session: DatabaseSession) -> TokenResponse:
    try:
        return rotate_refresh_token(session, data)
    except InvalidRefreshToken as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token") from exc


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def log_out(data: RefreshRequest, session: DatabaseSession) -> Response:
    try:
        logout(session, data)
    except InvalidRefreshToken as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
