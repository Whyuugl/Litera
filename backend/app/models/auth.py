import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.catalog import UUIDTimestampMixin, User


class RefreshSession(UUIDTimestampMixin, Base):
    __tablename__ = "refresh_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    jti: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    replaced_by_jti: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("refresh_sessions.jti")
    )

    user: Mapped[User] = relationship(back_populates="refresh_sessions")
