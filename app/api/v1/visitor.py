from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import success_response
from app.db.database import get_db
from app.schemas.experience import CreateSessionRequest
from app.services import experience_service

router = APIRouter()


@router.post("/session")
def create_session(
    body: CreateSessionRequest | None = None,
    db: Session = Depends(get_db),
):
    museum_id = body.museum_id if body else None
    data = experience_service.create_session(db, museum_id)
    return success_response(data.model_dump(), message="Session created")
