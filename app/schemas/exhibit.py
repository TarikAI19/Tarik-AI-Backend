from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ExhibitStatus
from app.schemas.exhibit_content import ExhibitContentResponse


class ExhibitCreate(BaseModel):
    museum_id: UUID
    title: str
    slug: str
    featured_image: str | None = None
    estimated_duration: int = Field(gt=0)
    status: ExhibitStatus = ExhibitStatus.DRAFT


class ExhibitUpdate(BaseModel):
    title: str | None = None
    slug: str | None = None
    featured_image: str | None = None
    estimated_duration: int | None = Field(default=None, gt=0)
    status: ExhibitStatus | None = None


class ExhibitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    museum_id: UUID
    title: str
    slug: str
    featured_image: str | None
    estimated_duration: int
    status: ExhibitStatus
    created_at: datetime
    updated_at: datetime
    contents: list[ExhibitContentResponse] = Field(default_factory=list)
