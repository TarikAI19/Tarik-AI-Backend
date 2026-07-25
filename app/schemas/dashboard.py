from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import ContentStatus, ExhibitStatus, Language, Persona


class DashboardMuseumItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    exhibits_count: int
    total_visits: int


class ApprovalStatusMap(BaseModel):
    EN: ContentStatus | None = None
    AM: ContentStatus | None = None
    OM: ContentStatus | None = None
    AR: ContentStatus | None = None


class AudioStatusMap(BaseModel):
    EN: str | None = None
    AM: str | None = None
    OM: str | None = None
    AR: str | None = None


class DashboardExhibitItem(BaseModel):
    id: UUID
    title: str
    status: ExhibitStatus
    museum_id: UUID
    approval_status: ApprovalStatusMap
    audio_status: AudioStatusMap


class ContentReviewItem(BaseModel):
    exhibit_id: UUID
    exhibit_title: str
    language: Language
    persona: Persona
    status: ContentStatus
    created_at: datetime


class AnalyticsResponse(BaseModel):
    total_visitors: int
    total_visits: int
    exhibits_viewed: int
    avg_session_duration_seconds: float | None = None
    museum_id: UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
