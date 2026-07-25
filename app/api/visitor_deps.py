from datetime import UTC, datetime

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.database import get_db
from app.models.visitor_session import VisitorSession


def get_visitor_session(
    session_key: str,
    db: Session = Depends(get_db),
) -> VisitorSession:
    session = (
        db.query(VisitorSession)
        .filter(VisitorSession.session_key == session_key)
        .first()
    )
    if not session:
        raise AppError(
            error_code="SESSION_NOT_FOUND",
            message="Session not found",
            status_code=401,
        )

    if session.expires_at <= datetime.now(UTC):
        raise AppError(
            error_code="SESSION_EXPIRED",
            message="Session expired",
            status_code=401,
        )

    return session
