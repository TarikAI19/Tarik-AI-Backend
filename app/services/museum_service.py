from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.museum import Museum
from app.schemas.museum import MuseumCreate, MuseumUpdate


def create_museum(db: Session, payload: MuseumCreate) -> Museum:
    museum = Museum(**payload.model_dump())
    db.add(museum)
    db.commit()
    db.refresh(museum)
    return museum


def list_museums(
    db: Session,
    *,
    limit: int = 10,
    offset: int = 0,
) -> tuple[list[Museum], int]:
    total = db.scalar(select(func.count()).select_from(Museum)) or 0
    museums = list(
        db.scalars(
            select(Museum).order_by(Museum.created_at.desc()).limit(limit).offset(offset)
        ).all()
    )
    return museums, total


def get_museum(db: Session, museum_id: UUID) -> Museum:
    museum = db.get(Museum, museum_id)
    if not museum:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Museum not found",
        )
    return museum


def update_museum(db: Session, museum_id: UUID, payload: MuseumUpdate) -> Museum:
    museum = get_museum(db, museum_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(museum, field, value)
    db.commit()
    db.refresh(museum)
    return museum


def delete_museum(db: Session, museum_id: UUID) -> None:
    museum = get_museum(db, museum_id)
    db.delete(museum)
    db.commit()
