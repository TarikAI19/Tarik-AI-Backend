from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.permissions import (
    assert_can_manage_museum,
    require_roles,
)
from app.api.responses import ok, ok_list
from app.core.enums import UserRole
from app.db.database import get_db
from app.models.user import User
from app.schemas.museum import MuseumCreate, MuseumResponse, MuseumUpdate
from app.services import museum_service

router = APIRouter()


@router.post("")
def create_museum(
    body: MuseumCreate,
    db: Session = Depends(get_db),
    _: User = Depends(
        require_roles(UserRole.SUPER_ADMIN, UserRole.MUSEUM_ADMIN)
    ),
):
    museum = museum_service.create_museum(db, body)
    return ok(
        MuseumResponse.model_validate(museum).model_dump(),
        message="Museum created",
    )


@router.get("")
def list_museums(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    museums, total = museum_service.list_museums(db, limit=limit, offset=offset)
    data = [MuseumResponse.model_validate(m).model_dump() for m in museums]
    return ok_list(data, limit=limit, offset=offset, total=total, message="Museums retrieved")


@router.get("/{museum_id}")
def get_museum(
    museum_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    museum = museum_service.get_museum(db, museum_id)
    return ok(
        MuseumResponse.model_validate(museum).model_dump(),
        message="Museum retrieved",
    )


@router.patch("/{museum_id}")
def update_museum(
    museum_id: UUID,
    body: MuseumUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.SUPER_ADMIN, UserRole.MUSEUM_ADMIN)
    ),
):
    assert_can_manage_museum(current_user, museum_id)
    museum = museum_service.update_museum(db, museum_id, body)
    return ok(
        MuseumResponse.model_validate(museum).model_dump(),
        message="Museum updated",
    )


@router.delete("/{museum_id}")
def delete_museum(
    museum_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
):
    museum_service.delete_museum(db, museum_id)
    return ok({"id": str(museum_id)}, message="Museum deleted")
