from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MuseumCreate(BaseModel):
    name: str
    description: str | None = None
    logo: str | None = None
    cover_image: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None


class MuseumUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    logo: str | None = None
    cover_image: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None


class MuseumResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    logo: str | None
    cover_image: str | None
    address: str | None
    city: str | None
    country: str | None
    created_at: datetime
