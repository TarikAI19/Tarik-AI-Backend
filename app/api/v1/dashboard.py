from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.permissions import require_roles
from app.api.responses import ok, ok_list
from app.core.enums import UserRole
from app.db.database import get_db
from app.models.user import User
from app.services import dashboard_service

router = APIRouter()


@router.get("/museums")
def dashboard_museums(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
):
    items, total = dashboard_service.list_dashboard_museums(
        db, limit=limit, offset=offset
    )
    data = [item.model_dump() for item in items]
    return ok_list(
        data,
        limit=limit,
        offset=offset,
        total=total,
        message="Dashboard museums retrieved",
    )


@router.get("/exhibits")
def dashboard_exhibits(
    museum_id: UUID | None = None,
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.MUSEUM_ADMIN,
            UserRole.CURATOR,
        )
    ),
):
    items, total = dashboard_service.list_dashboard_exhibits(
        db,
        current_user,
        museum_id=museum_id,
        limit=limit,
        offset=offset,
    )
    data = [item.model_dump() for item in items]
    return ok_list(
        data,
        limit=limit,
        offset=offset,
        total=total,
        message="Dashboard exhibits retrieved",
    )


@router.get("/content-review")
def dashboard_content_review(
    museum_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.MUSEUM_ADMIN,
            UserRole.CURATOR,
        )
    ),
):
    items = dashboard_service.list_content_review(
        db, current_user, museum_id=museum_id
    )
    return ok(
        [item.model_dump() for item in items],
        message="Content review queue retrieved",
    )


@router.get("/analytics")
def dashboard_analytics(
    museum_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.MUSEUM_ADMIN,
        )
    ),
):
    analytics = dashboard_service.get_analytics(
        db,
        current_user,
        museum_id=museum_id,
        date_from=date_from,
        date_to=date_to,
    )
    return ok(analytics.model_dump(), message="Analytics retrieved")
