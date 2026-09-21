import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RefreshSession


def get_refresh_session_for_update(
    session: Session, jti: uuid.UUID
) -> RefreshSession | None:
    return session.scalar(
        select(RefreshSession).where(RefreshSession.jti == jti).with_for_update()
    )
