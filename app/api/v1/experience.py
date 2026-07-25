from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.visitor_deps import get_visitor_session
from app.core.responses import paginated_response, success_response
from app.db.database import get_db
from app.models.visitor_session import VisitorSession
from app.schemas.experience import (
    EndVisitRequest,
    StartVisitRequest,
    UpdateLanguageRequest,
)
from app.services import experience_service

router = APIRouter()


@router.get("/{session_key}")
def get_session(
    session: VisitorSession = Depends(get_visitor_session),
):
    data = experience_service.get_session(session)
    return success_response(data.model_dump())


@router.patch("/{session_key}")
def update_language(
    body: UpdateLanguageRequest,
    session: VisitorSession = Depends(get_visitor_session),
    db: Session = Depends(get_db),
):
    data = experience_service.update_language(db, session, body.language)
    return success_response(
        {
            "session_key": data.session_key,
            "language": data.language,
        },
        message="Language updated",
    )


@router.get("/{session_key}/exhibits")
def list_exhibits(
    session: VisitorSession = Depends(get_visitor_session),
    db: Session = Depends(get_db),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    items, total = experience_service.list_exhibits(
        db,
        session,
        limit=limit,
        offset=offset,
    )
    return paginated_response(
        [item.model_dump() for item in items],
        limit=limit,
        offset=offset,
        total=total,
    )


@router.get("/{session_key}/exhibit/{exhibit_id}")
def get_exhibit(
    exhibit_id: UUID,
    session: VisitorSession = Depends(get_visitor_session),
    db: Session = Depends(get_db),
):
    data = experience_service.get_exhibit_detail(db, session, exhibit_id)
    return success_response(data.model_dump())


@router.post("/{session_key}/visit")
def start_visit(
    body: StartVisitRequest,
    session: VisitorSession = Depends(get_visitor_session),
    db: Session = Depends(get_db),
):
    data = experience_service.start_visit(db, session, body.exhibit_id)
    return success_response(data.model_dump(), message="Visit started")


@router.patch("/{session_key}/visit/{visit_id}")
def end_visit(
    visit_id: UUID,
    body: EndVisitRequest,
    session: VisitorSession = Depends(get_visitor_session),
    db: Session = Depends(get_db),
):
    data = experience_service.end_visit(db, session, visit_id, body.completed)
    return success_response(data.model_dump())


@router.get("/{session_key}/recommend")
def get_recommendations(
    current_exhibit_id: UUID = Query(...),
    session: VisitorSession = Depends(get_visitor_session),
    db: Session = Depends(get_db),
):
    items = experience_service.get_recommendations(
        db,
        session,
        current_exhibit_id,
    )
    return success_response([item.model_dump() for item in items])
