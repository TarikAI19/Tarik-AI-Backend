import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import Language

if TYPE_CHECKING:
    from app.models.museum import Museum
    from app.models.visit import Visit


class VisitorSession(Base):
    __tablename__ = "visitor_sessions"

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
    session_key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    language: Mapped[Language] = mapped_column(
        Enum(Language, name="language", native_enum=False, create_constraint=False),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    museum: Mapped["Museum"] = relationship(
        "Museum",
        back_populates="visitor_sessions",
    )
    visits: Mapped[list["Visit"]] = relationship(
        "Visit",
        back_populates="visitor_session",
    )
