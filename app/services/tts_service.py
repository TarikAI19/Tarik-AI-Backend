import logging
from pathlib import Path
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.exhibit_content import ExhibitContent

logger = logging.getLogger(__name__)

ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


def _storage_root() -> Path:
    root = Path(settings.AUDIO_STORAGE_DIR)
    root.mkdir(parents=True, exist_ok=True)
    return root


def generate_audio_bytes(text: str) -> bytes:
    if not settings.ELEVENLABS_API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY is not configured")

    url = ELEVENLABS_TTS_URL.format(voice_id=settings.ELEVENLABS_VOICE_ID)
    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
    }

    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.content


def store_audio_file(
    exhibit_id: UUID,
    language: str,
    persona: str,
    audio_bytes: bytes,
) -> str:
    exhibit_dir = _storage_root() / str(exhibit_id)
    exhibit_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{language}_{persona}.mp3"
    file_path = exhibit_dir / filename
    file_path.write_bytes(audio_bytes)
    # Relative path under storage root (served at /media/audio/...)
    return f"{exhibit_id}/{filename}"


def generate_and_store(content_id: UUID) -> None:
    """Background job: synthesize TTS and persist audio_url. Never raises to caller."""
    db: Session = SessionLocal()
    try:
        content = db.get(ExhibitContent, content_id)
        if not content:
            logger.error("TTS skipped: content %s not found", content_id)
            return
        if not content.generated_text.strip():
            logger.warning("TTS skipped: empty text for content %s", content_id)
            return

        audio_bytes = generate_audio_bytes(content.generated_text)
        relative_path = store_audio_file(
            content.exhibit_id,
            content.language.value,
            content.persona.value,
            audio_bytes,
        )
        content.audio_url = f"/media/audio/{relative_path}"
        db.commit()
        logger.info("TTS stored for content %s at %s", content_id, content.audio_url)
    except Exception:
        db.rollback()
        logger.exception("TTS failed for content %s", content_id)
    finally:
        db.close()
