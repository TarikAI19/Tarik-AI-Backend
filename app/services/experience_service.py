import random
import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.enums import ContentStatus, ExhibitStatus, Language, Persona
from app.core.exceptions import AppError
from app.models.exhibit import Exhibit
from app.models.exhibit_content import ExhibitContent
from app.models.museum import Museum
from app.models.visit import Visit
from app.models.visitor_session import VisitorSession
from app.schemas.experience import (
    EndVisitData,
    ExhibitDetail,
    ExhibitListItem,
    RecommendationItem,
    SessionData,
    StartVisitData,
)

SESSION_TTL_HOURS = 24


def _require_language(session: VisitorSession) -> None:
    if session.language is None:
        raise AppError(
            error_code="LANGUAGE_NOT_SELECTED",
            message="Please select a language before accessing exhibits",
            status_code=400,
        )


def create_session(db: Session, museum_id: UUID | None) -> SessionData:
    if museum_id is None:
        raise AppError(
            error_code="MUSEUM_ID_REQUIRED",
            message="museum_id is required to create a visitor session",
            status_code=400,
        )

    museum = db.get(Museum, museum_id)
    if not museum:
        raise AppError(
            error_code="MUSEUM_NOT_FOUND",
            message="Museum not found",
            status_code=404,
        )

    now = datetime.now(UTC)
    session = VisitorSession(
        museum_id=museum_id,
        session_key=str(uuid.uuid4()),
        language=None,
        started_at=now,
        expires_at=now + timedelta(hours=SESSION_TTL_HOURS),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return SessionData(
        session_key=session.session_key,
        museum_id=session.museum_id,
        expires_at=session.expires_at,
        language=session.language,
    )


def get_session(session: VisitorSession) -> SessionData:
    return SessionData(
        session_key=session.session_key,
        museum_id=session.museum_id,
        language=session.language,
        expires_at=session.expires_at,
        started_at=session.started_at,
    )


def update_language(
    db: Session,
    session: VisitorSession,
    language: Language,
) -> SessionData:
    session.language = language
    db.commit()
    db.refresh(session)

    return SessionData(
        session_key=session.session_key,
        museum_id=session.museum_id,
        language=session.language,
        expires_at=session.expires_at,
        started_at=session.started_at,
    )


def _get_historian_content(
    db: Session,
    exhibit_id: UUID,
    language: Language,
) -> ExhibitContent | None:
    return (
        db.query(ExhibitContent)
        .filter(
            ExhibitContent.exhibit_id == exhibit_id,
            ExhibitContent.language == language,
            ExhibitContent.persona == Persona.HISTORIAN,
            ExhibitContent.status == ContentStatus.APPROVED,
        )
        .first()
    )


def _get_published_exhibit(
    db: Session,
    exhibit_id: UUID,
    museum_id: UUID,
) -> Exhibit:
    exhibit = (
        db.query(Exhibit)
        .filter(
            Exhibit.id == exhibit_id,
            Exhibit.museum_id == museum_id,
            Exhibit.status == ExhibitStatus.PUBLISHED,
        )
        .first()
    )
    if not exhibit:
        raise AppError(
            error_code="EXHIBIT_NOT_FOUND",
            message="Exhibit not found",
            status_code=404,
        )
    return exhibit


def list_exhibits(
    db: Session,
    session: VisitorSession,
    *,
    limit: int,
    offset: int,
) -> tuple[list[ExhibitListItem], int]:
    _require_language(session)

    query = (
        db.query(Exhibit)
        .filter(
            Exhibit.museum_id == session.museum_id,
            Exhibit.status == ExhibitStatus.PUBLISHED,
        )
        .order_by(Exhibit.created_at.desc())
    )
    total = query.count()
    exhibits = query.offset(offset).limit(limit).all()

    items: list[ExhibitListItem] = []
    for exhibit in exhibits:
        content = _get_historian_content(db, exhibit.id, session.language)
        items.append(
            ExhibitListItem(
                id=exhibit.id,
                title=exhibit.title,
                featured_image=exhibit.featured_image,
                estimated_duration=exhibit.estimated_duration,
                audio_url=content.audio_url if content else None,
            )
        )

    return items, total


def get_exhibit_detail(
    db: Session,
    session: VisitorSession,
    exhibit_id: UUID,
) -> ExhibitDetail:
    _require_language(session)
    exhibit = _get_published_exhibit(db, exhibit_id, session.museum_id)
    content = _get_historian_content(db, exhibit.id, session.language)

    if not content:
        raise AppError(
            error_code="CONTENT_NOT_FOUND",
            message="Exhibit content not available in the selected language",
            status_code=404,
        )

    return ExhibitDetail(
        id=exhibit.id,
        title=exhibit.title,
        featured_image=exhibit.featured_image,
        estimated_duration=exhibit.estimated_duration,
        audio_url=content.audio_url,
        audio_duration=None,
        generated_text=content.generated_text,
        language=content.language,
        persona=content.persona,
    )


def start_visit(
    db: Session,
    session: VisitorSession,
    exhibit_id: UUID,
) -> StartVisitData:
    _get_published_exhibit(db, exhibit_id, session.museum_id)

    visit = Visit(
        visitor_session_id=session.id,
        exhibit_id=exhibit_id,
        completed=False,
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)

    return StartVisitData(
        visit_id=visit.id,
        exhibit_id=visit.exhibit_id,
        started_at=visit.started_at,
    )


def end_visit(
    db: Session,
    session: VisitorSession,
    visit_id: UUID,
    completed: bool,
) -> EndVisitData:
    visit = db.get(Visit, visit_id)
    if not visit or visit.visitor_session_id != session.id:
        raise AppError(
            error_code="VISIT_NOT_FOUND",
            message="Visit not found",
            status_code=404,
        )

    ended_at = datetime.now(UTC)
    visit.ended_at = ended_at
    visit.completed = completed
    db.commit()
    db.refresh(visit)

    duration_seconds = int((visit.ended_at - visit.started_at).total_seconds())

    return EndVisitData(
        visit_id=visit.id,
        exhibit_id=visit.exhibit_id,
        started_at=visit.started_at,
        ended_at=visit.ended_at,
        completed=visit.completed,
        duration_seconds=duration_seconds,
    )


def get_recommendations(
    db: Session,
    session: VisitorSession,
    current_exhibit_id: UUID,
) -> list[RecommendationItem]:
    _get_published_exhibit(db, current_exhibit_id, session.museum_id)

    visited_ids = {
        exhibit_id
        for (exhibit_id,) in db.query(Visit.exhibit_id)
        .filter(Visit.visitor_session_id == session.id)
        .all()
    }
    visited_ids.add(current_exhibit_id)

    candidates = (
        db.query(Exhibit)
        .filter(
            Exhibit.museum_id == session.museum_id,
            Exhibit.status == ExhibitStatus.PUBLISHED,
            Exhibit.id.notin_(visited_ids),
        )
        .all()
    )

    selected = random.sample(candidates, min(3, len(candidates)))

    return [
        RecommendationItem(
            id=exhibit.id,
            title=exhibit.title,
            featured_image=exhibit.featured_image,
            estimated_duration=exhibit.estimated_duration,
        )
        for exhibit in selected
    ]
