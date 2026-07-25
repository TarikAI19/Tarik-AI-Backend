from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.permissions import require_roles
from app.api.responses import ok, ok_list
from app.core.enums import ExhibitStatus, Language, Persona, UserRole
from app.db.database import get_db
from app.models.user import User
from app.schemas.exhibit import ExhibitCreate, ExhibitResponse, ExhibitUpdate
from app.schemas.exhibit_content import ExhibitContentResponse
from app.services import content_service, exhibit_service, tts_service

router = APIRouter()

STAFF_ROLES = require_roles(
    UserRole.SUPER_ADMIN,
    UserRole.MUSEUM_ADMIN,
    UserRole.CURATOR,
)


class ContentCreateBody(BaseModel):
    language: Language
    persona: Persona


class ContentUpdateBody(BaseModel):
    generated_text: str | None = Field(default=None, min_length=1)


@router.post("")
def create_exhibit(
    body: ExhibitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(STAFF_ROLES),
):
    exhibit = exhibit_service.create_exhibit(db, body, current_user)
    return ok(
        ExhibitResponse.model_validate(exhibit).model_dump(),
        message="Exhibit created",
    )


@router.get("")
def list_exhibits(
    museum_id: UUID | None = None,
    status: ExhibitStatus | None = None,
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(STAFF_ROLES),
):
    exhibits, total = exhibit_service.list_exhibits(
        db,
        current_user,
        museum_id=museum_id,
        status_filter=status,
        limit=limit,
        offset=offset,
    )
    data = [
        ExhibitResponse.model_validate(e).model_dump(exclude={"contents"})
        for e in exhibits
    ]
    return ok_list(
        data,
        limit=limit,
        offset=offset,
        total=total,
        message="Exhibits retrieved",
    )


@router.get("/{exhibit_id}")
def get_exhibit(
    exhibit_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(STAFF_ROLES),
):
    exhibit = exhibit_service.get_exhibit(db, exhibit_id, current_user)
    return ok(
        ExhibitResponse.model_validate(exhibit).model_dump(),
        message="Exhibit retrieved",
    )


@router.patch("/{exhibit_id}")
def update_exhibit(
    exhibit_id: UUID,
    body: ExhibitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(STAFF_ROLES),
):
    exhibit = exhibit_service.update_exhibit(db, exhibit_id, body, current_user)
    return ok(
        ExhibitResponse.model_validate(exhibit).model_dump(),
        message="Exhibit updated",
    )


@router.delete("/{exhibit_id}")
def delete_exhibit(
    exhibit_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(STAFF_ROLES),
):
    exhibit_service.delete_exhibit(db, exhibit_id, current_user)
    return ok({"id": str(exhibit_id)}, message="Exhibit deleted")


@router.get("/{exhibit_id}/content")
def list_content(
    exhibit_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(STAFF_ROLES),
):
    contents = exhibit_service.list_exhibit_contents(db, exhibit_id, current_user)
    data = [ExhibitContentResponse.model_validate(c).model_dump() for c in contents]
    return ok(data, message="Exhibit content retrieved")


@router.post("/{exhibit_id}/content")
def create_content(
    exhibit_id: UUID,
    body: ContentCreateBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(STAFF_ROLES),
):
    content = content_service.create_content(
        db,
        exhibit_id,
        current_user,
        language=body.language,
        persona=body.persona,
    )
    return ok(
        ExhibitContentResponse.model_validate(content).model_dump(),
        message="Exhibit content created",
    )


@router.get("/{exhibit_id}/content/{language}/{persona}")
def get_content(
    exhibit_id: UUID,
    language: Language,
    persona: Persona,
    db: Session = Depends(get_db),
    current_user: User = Depends(STAFF_ROLES),
):
    content = content_service.get_content(
        db, exhibit_id, language, persona, current_user
    )
    return ok(
        ExhibitContentResponse.model_validate(content).model_dump(),
        message="Exhibit content retrieved",
    )


@router.patch("/{exhibit_id}/content/{language}/{persona}")
def update_content(
    exhibit_id: UUID,
    language: Language,
    persona: Persona,
    body: ContentUpdateBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(STAFF_ROLES),
):
    content = content_service.update_content(
        db,
        exhibit_id,
        language,
        persona,
        current_user,
        generated_text=body.generated_text,
    )
    return ok(
        ExhibitContentResponse.model_validate(content).model_dump(),
        message="Exhibit content updated",
    )


@router.patch("/{exhibit_id}/content/{language}/{persona}/approve")
def approve_content(
    exhibit_id: UUID,
    language: Language,
    persona: Persona,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(STAFF_ROLES),
):
    content = content_service.approve_content(
        db, exhibit_id, language, persona, current_user
    )
    background_tasks.add_task(tts_service.generate_and_store, content.id)
    return ok(
        ExhibitContentResponse.model_validate(content).model_dump(),
        message="Exhibit content approved; TTS queued",
    )
