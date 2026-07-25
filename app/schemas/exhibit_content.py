from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ContentStatus, Language, Persona


class ExhibitContentCreate(BaseModel):
    exhibit_id: UUID
    language: Language
    persona: Persona
    historical_text: str
    audio_path: str | None = None
    status: ContentStatus = ContentStatus.PENDING_REVIEW


class ExhibitContentUpdate(BaseModel):
    language: Language | None = None
    persona: Persona | None = None
    historical_text: str | None = None
    audio_path: str | None = None
    status: ContentStatus | None = None


class ExhibitContentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    exhibit_id: UUID
    language: Language
    persona: Persona
    historical_text: str
    audio_path: str | None
    status: ContentStatus
    created_at: datetime
    updated_at: datetime
