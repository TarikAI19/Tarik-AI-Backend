from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.permissions import assert_museum_access
from app.core.enums import ContentStatus, ExhibitStatus, Language, Persona, UserRole
from app.models.exhibit import Exhibit
from app.models.exhibit_content import ExhibitContent
from app.models.museum import Museum
from app.models.user import User
from app.schemas.exhibit import ExhibitCreate, ExhibitUpdate
from app.services import ai_service


def _ensure_museum_exists(db: Session, museum_id: UUID) -> None:
    if not db.get(Museum, museum_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Museum not found",
        )


def create_exhibit(db: Session, payload: ExhibitCreate, user: User) -> Exhibit:
    assert_museum_access(user, payload.museum_id)
    _ensure_museum_exists(db, payload.museum_id)

    exhibit = Exhibit(
        museum_id=payload.museum_id,
        title=payload.title,
        slug=payload.slug,
        featured_image=payload.featured_image,
        source_text=payload.source_text,
        estimated_duration=payload.estimated_duration,
        status=ExhibitStatus.DRAFT,
    )
    db.add(exhibit)
    db.flush()

    generated_text = ai_service.generate_content_text(
        source_text=payload.source_text,
        language=Language.EN,
        persona=Persona.HISTORIAN,
    )
    seed = ExhibitContent(
        exhibit_id=exhibit.id,
        language=Language.EN,
        persona=Persona.HISTORIAN,
        generated_text=generated_text,
        audio_url=None,
        status=ContentStatus.PENDING_REVIEW,
    )
    db.add(seed)
    db.commit()

    return get_exhibit(db, exhibit.id, user)


def list_exhibits(
    db: Session,
    user: User,
    *,
    museum_id: UUID | None = None,
    status_filter: ExhibitStatus | None = None,
    limit: int = 10,
    offset: int = 0,
) -> tuple[list[Exhibit], int]:
    filters = []

    if user.role != UserRole.SUPER_ADMIN:
        if user.museum_id is None:
            return [], 0
        if museum_id is not None and museum_id != user.museum_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not allowed to access this museum",
            )
        filters.append(Exhibit.museum_id == user.museum_id)
    elif museum_id is not None:
        filters.append(Exhibit.museum_id == museum_id)

    if status_filter is not None:
        filters.append(Exhibit.status == status_filter)

    total = (
        db.scalar(select(func.count()).select_from(Exhibit).where(*filters))
        if filters
        else db.scalar(select(func.count()).select_from(Exhibit))
    ) or 0

    query = select(Exhibit)
    if filters:
        query = query.where(*filters)

    exhibits = list(
        db.scalars(
            query.order_by(Exhibit.created_at.desc()).limit(limit).offset(offset)
        ).all()
    )
    return exhibits, total


def get_exhibit(db: Session, exhibit_id: UUID, user: User) -> Exhibit:
    exhibit = db.scalar(
        select(Exhibit)
        .options(selectinload(Exhibit.contents))
        .where(Exhibit.id == exhibit_id)
    )
    if not exhibit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exhibit not found",
        )
    assert_museum_access(user, exhibit.museum_id)
    return exhibit


def update_exhibit(
    db: Session,
    exhibit_id: UUID,
    payload: ExhibitUpdate,
    user: User,
) -> Exhibit:
    exhibit = get_exhibit(db, exhibit_id, user)
    updates = payload.model_dump(exclude_unset=True)
    # Publish only via approval workflow — ignore client status changes.
    updates.pop("status", None)
    for field, value in updates.items():
        setattr(exhibit, field, value)
    db.commit()
    return get_exhibit(db, exhibit_id, user)


def delete_exhibit(db: Session, exhibit_id: UUID, user: User) -> None:
    exhibit = get_exhibit(db, exhibit_id, user)
    # Contents are already loaded; without cascade SQLAlchemy would SET NULL
    # on exhibit_id (NOT NULL) and fail. Delete children explicitly first.
    for content in list(exhibit.contents):
        db.delete(content)
    for visit in list(exhibit.visits):
        db.delete(visit)
    db.delete(exhibit)
    db.commit()


def list_exhibit_contents(
    db: Session,
    exhibit_id: UUID,
    user: User,
) -> list[ExhibitContent]:
    exhibit = get_exhibit(db, exhibit_id, user)
    return list(exhibit.contents)
