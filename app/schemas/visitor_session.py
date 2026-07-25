from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import Language


class VisitorSessionCreate(BaseModel):
    museum_id: UUID
    session_key: str
    language: Language
    expires_at: datetime


class VisitorSessionUpdate(BaseModel):
    language: Language | None = None
    expires_at: datetime | None = None


class VisitorSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    museum_id: UUID
    session_key: str
    language: Language
    started_at: datetime
    expires_at: datetime
    created_at: datetime
