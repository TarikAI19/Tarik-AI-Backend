import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ExhibitStatus
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.exhibit_content import ExhibitContent
    from app.models.museum import Museum
    from app.models.visit import Visit


class Exhibit(Base):
    __tablename__ = "exhibits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    museum_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("museums.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    featured_image: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_duration: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ExhibitStatus] = mapped_column(
        Enum(ExhibitStatus, name="exhibit_status", native_enum=False),
        nullable=False,
        default=ExhibitStatus.DRAFT,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    museum: Mapped["Museum"] = relationship(
        "Museum",
        back_populates="exhibits",
    )
    contents: Mapped[list["ExhibitContent"]] = relationship(
        "ExhibitContent",
        back_populates="exhibit",
    )
    visits: Mapped[list["Visit"]] = relationship(
        "Visit",
        back_populates="exhibit",
    )
