from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import ContentStatus, ExhibitStatus, Language, Persona
from app.models.exhibit import Exhibit
from app.models.exhibit_content import ExhibitContent
from app.models.user import User
from app.services import ai_service, exhibit_service

ALL_LANGUAGES = {Language.EN, Language.AM, Language.OM, Language.AR}


def _get_content(
    db: Session,
    exhibit_id: UUID,
    language: Language,
    persona: Persona,
) -> ExhibitContent:
    content = db.scalar(
        select(ExhibitContent).where(
            ExhibitContent.exhibit_id == exhibit_id,
            ExhibitContent.language == language,
            ExhibitContent.persona == persona,
        )
    )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exhibit content not found",
        )
    return content


def _resolve_historical_text(
    db: Session,
    exhibit: Exhibit,
    content: ExhibitContent,
) -> str:
    if content.persona == Persona.HISTORIAN:
        if not exhibit.source_text or not exhibit.source_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exhibit source_text is required for historian content",
            )
        return exhibit.source_text.strip()

    historian = db.scalar(
        select(ExhibitContent).where(
            ExhibitContent.exhibit_id == exhibit.id,
            ExhibitContent.language == content.language,
            ExhibitContent.persona == Persona.HISTORIAN,
        )
    )
    if not historian or not historian.generated_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Historian content for this language must exist before "
                "approving other personas"
            ),
        )
    return historian.generated_text.strip()


def create_content(
    db: Session,
    exhibit_id: UUID,
    user: User,
    *,
    language: Language,
    persona: Persona,
) -> ExhibitContent:
    exhibit = exhibit_service.get_exhibit(db, exhibit_id, user)

    if persona == Persona.HISTORIAN:
        if not exhibit.source_text or not exhibit.source_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exhibit source_text is required before generating content",
            )
        draft_text = exhibit.source_text.strip()
    else:
        historian = db.scalar(
            select(ExhibitContent).where(
                ExhibitContent.exhibit_id == exhibit.id,
                ExhibitContent.language == language,
                ExhibitContent.persona == Persona.HISTORIAN,
            )
        )
        if not historian or not historian.generated_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Create historian content for this language before "
                    "other personas"
                ),
            )
        draft_text = historian.generated_text.strip()

    content = ExhibitContent(
        exhibit_id=exhibit.id,
        language=language,
        persona=persona,
        generated_text=draft_text,
        audio_url=None,
        status=ContentStatus.PENDING_REVIEW,
    )
    db.add(content)
    try:
        db.commit()
        db.refresh(content)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Content for this language and persona already exists",
        ) from None
    return content


def get_content(
    db: Session,
    exhibit_id: UUID,
    language: Language,
    persona: Persona,
    user: User,
) -> ExhibitContent:
    exhibit_service.get_exhibit(db, exhibit_id, user)
    return _get_content(db, exhibit_id, language, persona)


def update_content(
    db: Session,
    exhibit_id: UUID,
    language: Language,
    persona: Persona,
    user: User,
    *,
    generated_text: str | None = None,
) -> ExhibitContent:
    exhibit_service.get_exhibit(db, exhibit_id, user)
    content = _get_content(db, exhibit_id, language, persona)

    if generated_text is not None:
        content.generated_text = generated_text
        # Editing approved text requires re-review before publish/TTS.
        if content.status == ContentStatus.APPROVED:
            content.status = ContentStatus.PENDING_REVIEW
            content.audio_url = None

    db.commit()
    db.refresh(content)
    return content


def maybe_auto_publish(db: Session, exhibit: Exhibit) -> bool:
    historian_rows = [
        c for c in exhibit.contents if c.persona == Persona.HISTORIAN
    ]
    approved_languages = {
        c.language for c in historian_rows if c.status == ContentStatus.APPROVED
    }
    if approved_languages >= ALL_LANGUAGES:
        exhibit.status = ExhibitStatus.PUBLISHED
        db.commit()
        return True
    return False


def approve_content(
    db: Session,
    exhibit_id: UUID,
    language: Language,
    persona: Persona,
    user: User,
) -> ExhibitContent:
    exhibit = exhibit_service.get_exhibit(db, exhibit_id, user)
    content = _get_content(db, exhibit_id, language, persona)

    historical_text = _resolve_historical_text(db, exhibit, content)
    content.generated_text = ai_service.generate_persona_text_via_gemini(
        historical_text=historical_text,
        language=language,
        persona=persona,
    )
    content.status = ContentStatus.APPROVED
    db.commit()
    db.refresh(content)

    exhibit = exhibit_service.get_exhibit(db, exhibit_id, user)
    maybe_auto_publish(db, exhibit)
    db.refresh(content)
    return content


def get_content_by_id(db: Session, content_id: UUID) -> ExhibitContent | None:
    return db.get(ExhibitContent, content_id)
