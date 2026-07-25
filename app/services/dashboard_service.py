from datetime import datetime
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
from app.models.visit import Visit
from app.models.visitor_session import VisitorSession
from app.schemas.dashboard import (
    AnalyticsResponse,
    ApprovalStatusMap,
    AudioStatusMap,
    ContentReviewItem,
    DashboardExhibitItem,
    DashboardMuseumItem,
    DashboardOverview,
    TopExhibitItem,
)


def list_dashboard_museums(
    db: Session,
    *,
    limit: int = 10,
    offset: int = 0,
) -> tuple[list[DashboardMuseumItem], int]:
    total = db.scalar(select(func.count()).select_from(Museum)) or 0
    museums = list(
        db.scalars(
            select(Museum).order_by(Museum.created_at.desc()).limit(limit).offset(offset)
        ).all()
    )

    items: list[DashboardMuseumItem] = []
    for museum in museums:
        exhibits_count = (
            db.scalar(
                select(func.count())
                .select_from(Exhibit)
                .where(Exhibit.museum_id == museum.id)
            )
            or 0
        )
        total_visits = (
            db.scalar(
                select(func.count())
                .select_from(Visit)
                .join(Exhibit, Visit.exhibit_id == Exhibit.id)
                .where(Exhibit.museum_id == museum.id)
            )
            or 0
        )
        items.append(
            DashboardMuseumItem(
                id=museum.id,
                name=museum.name,
                exhibits_count=exhibits_count,
                total_visits=total_visits,
            )
        )
    return items, total


def list_dashboard_exhibits(
    db: Session,
    user: User,
    *,
    museum_id: UUID | None = None,
    limit: int = 10,
    offset: int = 0,
) -> tuple[list[DashboardExhibitItem], int]:
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

    total = (
        db.scalar(select(func.count()).select_from(Exhibit).where(*filters))
        if filters
        else db.scalar(select(func.count()).select_from(Exhibit))
    ) or 0

    query = select(Exhibit).options(selectinload(Exhibit.contents))
    if filters:
        query = query.where(*filters)

    exhibits = list(
        db.scalars(
            query.order_by(Exhibit.created_at.desc()).limit(limit).offset(offset)
        ).all()
    )

    items: list[DashboardExhibitItem] = []
    for exhibit in exhibits:
        approval: dict[str, ContentStatus | None] = {
            lang.value: None for lang in Language
        }
        audio: dict[str, str | None] = {lang.value: None for lang in Language}

        for content in exhibit.contents:
            if content.persona != Persona.HISTORIAN:
                continue
            lang_key = content.language.value
            approval[lang_key] = content.status
            audio[lang_key] = "READY" if content.audio_url else "PENDING"

        items.append(
            DashboardExhibitItem(
                id=exhibit.id,
                title=exhibit.title,
                status=exhibit.status,
                museum_id=exhibit.museum_id,
                approval_status=ApprovalStatusMap(**approval),
                audio_status=AudioStatusMap(**audio),
            )
        )
    return items, total


def list_content_review(
    db: Session,
    user: User,
    *,
    museum_id: UUID | None = None,
) -> list[ContentReviewItem]:
    query = (
        select(ExhibitContent, Exhibit.title)
        .join(Exhibit, ExhibitContent.exhibit_id == Exhibit.id)
        .where(ExhibitContent.status == ContentStatus.PENDING_REVIEW)
    )

    target_museum = museum_id
    if user.role != UserRole.SUPER_ADMIN:
        if user.museum_id is None:
            return []
        if museum_id is not None and museum_id != user.museum_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not allowed to access this museum",
            )
        target_museum = user.museum_id

    if target_museum is not None:
        query = query.where(Exhibit.museum_id == target_museum)

    rows = db.execute(query.order_by(ExhibitContent.created_at.asc())).all()
    return [
        ContentReviewItem(
            content_id=content.id,
            exhibit_id=content.exhibit_id,
            exhibit_title=title,
            language=content.language,
            persona=content.persona,
            status=content.status,
            created_at=content.created_at,
        )
        for content, title in rows
    ]


def _resolve_museum_target(
    user: User,
    museum_id: UUID | None,
) -> UUID:
    if user.role == UserRole.SUPER_ADMIN:
        if museum_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="museum_id is required",
            )
        return museum_id

    if user.museum_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not assigned to a museum",
        )
    if museum_id is not None:
        assert_museum_access(user, museum_id)
        return museum_id
    return user.museum_id


def get_overview(
    db: Session,
    user: User,
    *,
    museum_id: UUID | None = None,
) -> DashboardOverview:
    target = _resolve_museum_target(user, museum_id)
    museum = db.get(Museum, target)
    if not museum:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Museum not found",
        )

    total_exhibits = (
        db.scalar(
            select(func.count())
            .select_from(Exhibit)
            .where(Exhibit.museum_id == target)
        )
        or 0
    )
    published_exhibits = (
        db.scalar(
            select(func.count())
            .select_from(Exhibit)
            .where(
                Exhibit.museum_id == target,
                Exhibit.status == ExhibitStatus.PUBLISHED,
            )
        )
        or 0
    )
    pending_review_count = (
        db.scalar(
            select(func.count())
            .select_from(ExhibitContent)
            .join(Exhibit, ExhibitContent.exhibit_id == Exhibit.id)
            .where(
                Exhibit.museum_id == target,
                ExhibitContent.status == ContentStatus.PENDING_REVIEW,
            )
        )
        or 0
    )

    analytics = get_analytics(db, user, museum_id=target)

    return DashboardOverview(
        museum_id=target,
        museum_name=museum.name,
        total_exhibits=total_exhibits,
        published_exhibits=published_exhibits,
        draft_exhibits=total_exhibits - published_exhibits,
        pending_review_count=pending_review_count,
        total_visitors=analytics.total_visitors,
        total_visits=analytics.total_visits,
        exhibits_viewed=analytics.exhibits_viewed,
        avg_session_duration_seconds=analytics.avg_session_duration_seconds,
    )


def get_analytics(
    db: Session,
    user: User,
    *,
    museum_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> AnalyticsResponse:
    target = _resolve_museum_target(user, museum_id)

    session_filters = [VisitorSession.museum_id == target]
    visit_filters = [Exhibit.museum_id == target]

    if date_from is not None:
        session_filters.append(VisitorSession.started_at >= date_from)
        visit_filters.append(Visit.started_at >= date_from)
    if date_to is not None:
        session_filters.append(VisitorSession.started_at <= date_to)
        visit_filters.append(Visit.started_at <= date_to)

    total_visitors = (
        db.scalar(
            select(func.count()).select_from(VisitorSession).where(*session_filters)
        )
        or 0
    )

    total_visits = (
        db.scalar(
            select(func.count())
            .select_from(Visit)
            .join(Exhibit, Visit.exhibit_id == Exhibit.id)
            .where(*visit_filters)
        )
        or 0
    )

    exhibits_viewed = (
        db.scalar(
            select(func.count(func.distinct(Visit.exhibit_id)))
            .select_from(Visit)
            .join(Exhibit, Visit.exhibit_id == Exhibit.id)
            .where(*visit_filters)
        )
        or 0
    )

    # Average completed visit duration when ended_at is present
    duration_expr = func.avg(
        func.extract("epoch", Visit.ended_at - Visit.started_at)
    )
    avg_duration = db.scalar(
        select(duration_expr)
        .select_from(Visit)
        .join(Exhibit, Visit.exhibit_id == Exhibit.id)
        .where(*visit_filters, Visit.ended_at.is_not(None))
    )

    top_rows = db.execute(
        select(Exhibit.id, Exhibit.title, func.count(Visit.id).label("visit_count"))
        .join(Visit, Visit.exhibit_id == Exhibit.id)
        .where(*visit_filters)
        .group_by(Exhibit.id, Exhibit.title)
        .order_by(func.count(Visit.id).desc())
        .limit(5)
    ).all()

    top_exhibits = [
        TopExhibitItem(
            exhibit_id=row.id,
            title=row.title,
            visit_count=row.visit_count,
        )
        for row in top_rows
    ]

    return AnalyticsResponse(
        total_visitors=total_visitors,
        total_visits=total_visits,
        exhibits_viewed=exhibits_viewed,
        avg_session_duration_seconds=float(avg_duration) if avg_duration is not None else None,
        top_exhibits=top_exhibits,
        museum_id=target,
        date_from=date_from,
        date_to=date_to,
    )
