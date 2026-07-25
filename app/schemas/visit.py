from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class VisitCreate(BaseModel):
    visitor_session_id: UUID
    exhibit_id: UUID
    started_at: datetime | None = None
    ended_at: datetime | None = None
    completed: bool = False


class VisitUpdate(BaseModel):
    ended_at: datetime | None = None
    completed: bool | None = None


class VisitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    visitor_session_id: UUID
    exhibit_id: UUID
    started_at: datetime
    ended_at: datetime | None
    completed: bool
    created_at: datetime
