from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ContentStatus, Language, Persona


class ExhibitContentCreate(BaseModel):
    language: Language
    persona: Persona


class ExhibitContentUpdate(BaseModel):
    generated_text: str | None = Field(default=None, min_length=1)


class ExhibitContentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    exhibit_id: UUID
    language: Language
    persona: Persona
    generated_text: str
    audio_url: str | None
    status: ContentStatus
    created_at: datetime
    updated_at: datetime
