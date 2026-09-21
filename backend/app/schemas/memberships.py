import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import MembershipStatus


class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: MembershipStatus
    member_number: str | None
    applied_at: datetime
    approved_at: datetime | None
    expires_at: datetime | None
    rejection_reason: str | None
    suspension_reason: str | None


class CurrentMembershipResponse(BaseModel):
    membership: MembershipResponse | None


class MembershipUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: EmailStr


class AdminMembershipResponse(MembershipResponse):
    user: MembershipUserResponse


class MembershipPage(BaseModel):
    items: list[AdminMembershipResponse]
    total: int
    page: int
    page_size: int


class MembershipReasonRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        if not (value := value.strip()):
            raise ValueError("Reason cannot be blank")
        return value
