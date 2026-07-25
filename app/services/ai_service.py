import logging
import re

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.enums import Language, Persona

logger = logging.getLogger(__name__)

LANGUAGE_NAMES: dict[Language, str] = {
    Language.EN: "English",
    Language.AM: "Amharic",
    Language.OM: "Afaan Oromo",
    Language.AR: "Arabic",
}

ADDIS_LANGUAGE_CODES: dict[Language, str] = {
    Language.AM: "am",
    Language.OM: "om",
}

PERSONA_INSTRUCTIONS: dict[Persona, str] = {
    Persona.HISTORIAN: """Persona: HISTORIAN
Write clear, accurate, engaging adult museum narration in the third person.
Give brief historical context and help a visitor understand why this exhibit matters.
Tone: professional, warm, and informative — not academic or dry.""",
    Persona.KID_FRIENDLY: """Persona: KID_FRIENDLY
Write for children about ages 6–12.
Use short sentences, simple words, warmth, and curiosity or wonder.
Avoid scary imagery, dense jargon, and long lists of dates.
You may ask one gentle rhetorical question to keep kids engaged.
Tone: playful and friendly, still truthful.""",
    Persona.GHOST_MODE: """Persona: GHOST_MODE
Write in the FIRST PERSON as the exhibit subject speaking (the object, figure, place, or remnant itself).
Use “I…” / equivalent first-person forms in the target language.
Tone: atmospheric and mysterious, like a quiet voice from the past — still faithful to the source facts.
Do not invent biography or events not supported by the source notes.""",
}


def _strip_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    return cleaned.strip()


def _build_user_prompt(
    *,
    source_text: str,
    language: Language,
    persona: Persona,
    title: str | None,
) -> str:
    language_name = LANGUAGE_NAMES[language]
    persona_block = PERSONA_INSTRUCTIONS.get(
        persona, PERSONA_INSTRUCTIONS[Persona.HISTORIAN]
    )
    exhibit_title = title.strip() if title else "Untitled exhibit"

    return f"""You are a museum content writer for Tarik AI.
Rewrite the curator source notes into a spoken exhibit narration for audio.

Language: {language_name} ({language.value})
Exhibit title: {exhibit_title}

{persona_block}

Shared rules:
- Write entirely in the target language ({language_name})
- Stay faithful to the source; do not invent facts
- Use 2–4 short paragraphs suitable for audio narration
- Return only the narration text (no titles, labels, or markdown)

Source notes:
{source_text.strip()}
"""


def _generate_with_groq(prompt: str) -> str:
    if not settings.GROQ_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GROQ_API_KEY is not configured",
        )

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a museum content writer for Tarik AI. "
                    "Stay faithful to the source. Return only narration text."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 1024,
    }

    try:
        with httpx.Client(timeout=90.0) as client:
            response = client.post(url, headers=headers, json=payload)
            if response.is_error:
                try:
                    err_body = response.json()
                    err_msg = (
                        err_body.get("error", {}).get("message")
                        or response.text
                    )
                except Exception:
                    err_msg = response.text
                logger.error("Groq API error %s: %s", response.status_code, err_msg)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Groq API error: {response.status_code} — {err_msg}",
                )
            data = response.json()
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        logger.exception("Groq API request failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to reach Groq API",
        ) from exc

    choices = data.get("choices") or []
    if not choices:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Groq API returned empty content",
        )

    message = choices[0].get("message") or {}
    text = _strip_fences(str(message.get("content") or ""))
    if not text:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Groq API returned empty content",
        )
    return text


def _generate_with_addis(prompt: str, language: Language) -> str:
    if not settings.ADDIS_AI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADDIS_AI_API_KEY is not configured",
        )

    target = ADDIS_LANGUAGE_CODES.get(language)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Addis AI does not support language {language.value}",
        )

    url = f"{settings.ADDIS_AI_BASE_URL.rstrip('/')}/chat_generate"
    headers = {
        "x-api-key": settings.ADDIS_AI_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "target_language": target,
        "persona": "You are a museum content writer for Tarik AI.",
        "system": (
            "Stay faithful to the source notes. Do not invent facts. "
            "Return only the narration text suitable for audio."
        ),
        "generation_config": {
            "temperature": 0.4,
            "maxOutputTokens": 1024,
        },
    }

    try:
        with httpx.Client(timeout=90.0) as client:
            response = client.post(url, headers=headers, json=payload)
            if response.is_error:
                try:
                    err_body = response.json()
                    err_msg = (
                        err_body.get("error", {}).get("message")
                        or err_body.get("message")
                        or response.text
                    )
                except Exception:
                    err_msg = response.text
                logger.error("Addis AI error %s: %s", response.status_code, err_msg)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Addis AI error: {response.status_code} — {err_msg}",
                )
            data = response.json()
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        logger.exception("Addis AI request failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to reach Addis AI",
        ) from exc

    if isinstance(data, dict) and data.get("status") == "error":
        err_msg = data.get("message") or data.get("error") or data
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Addis AI error: {err_msg}",
        )

    text = _extract_addis_text(data)
    if not text:
        logger.error(
            "Addis AI empty payload keys=%s",
            list(data.keys()) if isinstance(data, dict) else type(data),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Addis AI returned empty content",
        )
    return text


def _extract_addis_text(data: object) -> str:
    """Parse Addis chat_generate JSON (flat or {status, data} envelope)."""
    if not isinstance(data, dict):
        return ""

    candidates: list[object] = [data]
    nested = data.get("data")
    if isinstance(nested, dict):
        candidates.append(nested)

    for body in candidates:
        if not isinstance(body, dict):
            continue

        direct = body.get("response_text") or body.get("text") or body.get("content")
        if isinstance(direct, str) and direct.strip():
            return _strip_fences(direct)

        choices = body.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message") if isinstance(choices[0], dict) else None
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return _strip_fences(content)

    return ""


def generate_content_text(
    *,
    source_text: str,
    language: Language,
    persona: Persona,
    title: str | None = None,
) -> str:
    """
    Generate exhibit narration.

    Provider routing:
    - EN (and AR): Groq
    - AM / OM: Addis AI
    """
    base = source_text.strip()
    if not base:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source_text must not be empty",
        )

    prompt = _build_user_prompt(
        source_text=base,
        language=language,
        persona=persona,
        title=title,
    )

    if language in (Language.AM, Language.OM):
        return _generate_with_addis(prompt, language)

    return _generate_with_groq(prompt)
