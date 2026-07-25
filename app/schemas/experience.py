from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import Language, Persona


class CreateSessionRequest(BaseModel):
    museum_id: UUID | None = None


class SessionData(BaseModel):
    session_key: str
    museum_id: UUID
    expires_at: datetime
    language: Language | None = None
    started_at: datetime | None = None


class UpdateLanguageRequest(BaseModel):
    language: Language


class ExhibitListItem(BaseModel):
    id: UUID
    title: str
    featured_image: str | None
    estimated_duration: int
    audio_url: str | None = None


class ExhibitDetail(BaseModel):
    id: UUID
    title: str
    featured_image: str | None
    estimated_duration: int
    audio_url: str | None = None
    audio_duration: int | None = None
    historical_text: str
    language: Language
    persona: Persona


class StartVisitRequest(BaseModel):
    exhibit_id: UUID


class StartVisitData(BaseModel):
    visit_id: UUID
    exhibit_id: UUID
    started_at: datetime


class EndVisitRequest(BaseModel):
    completed: bool = True


class EndVisitData(BaseModel):
    visit_id: UUID
    exhibit_id: UUID
    started_at: datetime
    ended_at: datetime
    completed: bool
    duration_seconds: int


class QuestionRequest(BaseModel):
    question: str = Field(max_length=500)


class QuestionSources(BaseModel):
    exhibit_id: UUID
    language: Language
    persona: Persona


class QuestionData(BaseModel):
    answer: str
    sources: QuestionSources


class RecommendationItem(BaseModel):
    id: UUID
    title: str
    featured_image: str | None
    estimated_duration: int
