import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ContentStatus, Language, Persona
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.exhibit import Exhibit


class ExhibitContent(Base):
    __tablename__ = "exhibit_contents"
    __table_args__ = (
        UniqueConstraint(
            "exhibit_id",
            "language",
            "persona",
            name="uq_exhibit_content_language_persona",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    exhibit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exhibits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    language: Mapped[Language] = mapped_column(
        Enum(Language, name="language", native_enum=False, create_constraint=False),
        nullable=False,
    )
    persona: Mapped[Persona] = mapped_column(
        Enum(Persona, name="persona", native_enum=False),
        nullable=False,
    )
    historical_text: Mapped[str] = mapped_column(Text, nullable=False)
    audio_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, name="content_status", native_enum=False),
        nullable=False,
        default=ContentStatus.PENDING_REVIEW,
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

    exhibit: Mapped["Exhibit"] = relationship(
        "Exhibit",
        back_populates="contents",
    )
