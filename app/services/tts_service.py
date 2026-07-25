import logging
import os
import uuid
from pathlib import Path
from uuid import UUID

import httpx
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.core.config import DEFAULT_ELEVENLABS_VOICE_ID, settings
from app.core.enums import Language
from app.db.database import SessionLocal
from app.models.exhibit_content import ExhibitContent

logger = logging.getLogger(__name__)

ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

ADDIS_TTS_LANG_CODES: dict[Language, str] = {
    Language.AM: "am",
    Language.OM: "om",
}


def _storage_root() -> Path:
    root = Path(settings.AUDIO_STORAGE_DIR)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _elevenlabs_api_key() -> str:
    """Re-read .env so keys added after process start are picked up."""
    load_dotenv(override=True)
    return os.getenv("ELEVENLABS_API_KEY", "").strip() or settings.ELEVENLABS_API_KEY


def _elevenlabs_voice_id() -> str:
    load_dotenv(override=True)
    return (
        os.getenv("ELEVENLABS_VOICE_ID", "").strip()
        or settings.ELEVENLABS_VOICE_ID
        or DEFAULT_ELEVENLABS_VOICE_ID
    )


def generate_audio_bytes_elevenlabs(text: str) -> bytes:
    api_key = _elevenlabs_api_key()
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not configured")

    url = ELEVENLABS_TTS_URL.format(voice_id=_elevenlabs_voice_id())
    headers = {
        "xi-api-key": api_key,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
    }

    with httpx.Client(timeout=90.0) as client:
        response = client.post(url, headers=headers, json=payload)
        if response.is_error:
            detail = response.text[:500]
            logger.error("ElevenLabs TTS error %s: %s", response.status_code, detail)
            raise RuntimeError(
                f"ElevenLabs TTS error: {response.status_code} — {detail}"
            )
        return response.content


def _addis_voice_id(language: Language) -> str:
    if language == Language.AM:
        return settings.ADDIS_TTS_VOICE_AM
    if language == Language.OM:
        return settings.ADDIS_TTS_VOICE_OM
    raise RuntimeError(f"No Addis TTS voice for language {language.value}")


def _extract_addis_audio_url(data: object) -> str | None:
    """Parse Addis voice/generations JSON (flat or {status, data} envelope)."""
    if not isinstance(data, dict):
        return None

    candidates: list[object] = [data]
    nested = data.get("data")
    if isinstance(nested, dict):
        candidates.append(nested)

    for body in candidates:
        if not isinstance(body, dict):
            continue
        for key in ("audio_url", "audioUrl"):
            value = body.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def generate_audio_bytes_addis(text: str, language: Language) -> bytes:
    if not settings.ADDIS_AI_API_KEY:
        raise RuntimeError("ADDIS_AI_API_KEY is not configured")

    lang_code = ADDIS_TTS_LANG_CODES.get(language)
    if not lang_code:
        raise RuntimeError(f"Addis TTS does not support language {language.value}")

    url = f"{settings.ADDIS_AI_BASE_URL.rstrip('/')}/voice/generations"
    headers = {
        "x-api-key": settings.ADDIS_AI_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "voice_id": _addis_voice_id(language),
        "language": lang_code,
        "output_format": "mp3_44100",
        "client_request_id": str(uuid.uuid4()),
    }

    with httpx.Client(timeout=120.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict) and data.get("status") == "error":
            raise RuntimeError(f"Addis TTS error: {data.get('message') or data}")

        audio_url = _extract_addis_audio_url(data)
        if not audio_url:
            raise RuntimeError("Addis TTS returned no audio_url")

        # Signed URL may expire; download bytes and store locally.
        audio_response = client.get(audio_url)
        audio_response.raise_for_status()
        return audio_response.content


def generate_audio_bytes(text: str, language: Language) -> bytes:
    """Route TTS by language: Addis for AM/OM, ElevenLabs for EN/AR."""
    if language in (Language.AM, Language.OM):
        return generate_audio_bytes_addis(text, language)
    return generate_audio_bytes_elevenlabs(text)


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


def generate_and_store(content_id: UUID, *, raise_on_error: bool = False) -> str | None:
    """Synthesize TTS and persist audio_url. Returns the stored path or None."""
    db: Session = SessionLocal()
    try:
        content = db.get(ExhibitContent, content_id)
        if not content:
            msg = f"TTS skipped: content {content_id} not found"
            logger.error(msg)
            if raise_on_error:
                raise RuntimeError(msg)
            return None
        if not content.generated_text.strip():
            msg = f"TTS skipped: empty text for content {content_id}"
            logger.warning(msg)
            if raise_on_error:
                raise RuntimeError(msg)
            return None

        audio_bytes = generate_audio_bytes(
            content.generated_text,
            content.language,
        )
        relative_path = store_audio_file(
            content.exhibit_id,
            content.language.value,
            content.persona.value,
            audio_bytes,
        )
        content.audio_url = f"/media/audio/{relative_path}"
        db.commit()
        logger.info(
            "TTS stored for content %s lang=%s at %s",
            content_id,
            content.language.value,
            content.audio_url,
        )
        return content.audio_url
    except Exception:
        db.rollback()
        logger.exception("TTS failed for content %s", content_id)
        if raise_on_error:
            raise
        return None
    finally:
        db.close()
