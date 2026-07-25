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
LANGUAGE_ORDER = (
    Language.EN,
    Language.AM,
    Language.OM,
    Language.AR,
)


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


def generate_persona_contents(
    db: Session,
    exhibit_id: UUID,
    user: User,
    *,
    persona: Persona = Persona.HISTORIAN,
) -> list[ExhibitContent]:
    """Generate EN/AM/OM/AR content for one persona from exhibit.source_text."""
    exhibit = exhibit_service.get_exhibit(db, exhibit_id, user)

    if not exhibit.source_text or not exhibit.source_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exhibit source_text is required before generating content",
        )

    existing = db.scalar(
        select(ExhibitContent.id).where(
            ExhibitContent.exhibit_id == exhibit.id,
            ExhibitContent.persona == persona,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{persona.value} content already exists for this exhibit",
        )

    generated_by_language: dict[Language, str] = {}
    for language in LANGUAGE_ORDER:
        generated_by_language[language] = ai_service.generate_content_text(
            source_text=exhibit.source_text,
            language=language,
            persona=persona,
            title=exhibit.title,
        )

    contents: list[ExhibitContent] = []
    for language, generated_text in generated_by_language.items():
        content = ExhibitContent(
            exhibit_id=exhibit.id,
            language=language,
            persona=persona,
            generated_text=generated_text,
            audio_url=None,
            status=ContentStatus.PENDING_REVIEW,
        )
        db.add(content)
        contents.append(content)

    db.commit()
    for content in contents:
        db.refresh(content)
    return contents


# Backwards-compatible alias
def generate_historian_contents(
    db: Session,
    exhibit_id: UUID,
    user: User,
) -> list[ExhibitContent]:
    return generate_persona_contents(
        db, exhibit_id, user, persona=Persona.HISTORIAN
    )


def create_content(
    db: Session,
    exhibit_id: UUID,
    user: User,
    *,
    language: Language,
    persona: Persona,
) -> ExhibitContent:
    exhibit = exhibit_service.get_exhibit(db, exhibit_id, user)

    if not exhibit.source_text or not exhibit.source_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exhibit source_text is required before generating content",
        )

    generated_text = ai_service.generate_content_text(
        source_text=exhibit.source_text,
        language=language,
        persona=persona,
        title=exhibit.title,
    )

    content = ExhibitContent(
        exhibit_id=exhibit.id,
        language=language,
        persona=persona,
        generated_text=generated_text,
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
    exhibit_service.get_exhibit(db, exhibit_id, user)
    content = _get_content(db, exhibit_id, language, persona)

    if not content.generated_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot approve content with empty generated_text",
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
