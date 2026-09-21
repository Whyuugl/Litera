from fastapi import APIRouter

from app.api.dependencies import CurrentUser
from app.schemas.auth import UserResponse


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def current_user(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)
