import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import SpoilerMode, SummaryStatus, SummaryType


class SummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    edition_id: uuid.UUID
    chapter_id: uuid.UUID | None
    summary_type: SummaryType
    spoiler_mode: SpoilerMode
    content: str | None
    source_content_hash: str
    provider: str
    model: str
    status: SummaryStatus
    error_message: str | None
    generated_at: datetime | None
    created_at: datetime
    updated_at: datetime
    is_stale: bool = False
