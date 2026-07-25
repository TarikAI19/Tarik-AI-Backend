import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.enums import Language, Persona

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)

LANGUAGE_NAMES = {
    Language.EN: "English",
    Language.AM: "Amharic",
    Language.OM: "Afaan Oromo",
    Language.AR: "Arabic",
}

PERSONA_INSTRUCTIONS = {
    Persona.HISTORIAN: (
        "You are a knowledgeable museum historian. Write clear, accurate, "
        "engaging narration suitable for a museum audio guide. Stay factual "
        "and grounded in the source material."
    ),
    Persona.KID_FRIENDLY: (
        "You are a friendly museum guide for children ages 8-12. Use simple "
        "words, short sentences, and an enthusiastic tone. Make it fun and easy "
        "to understand while keeping the facts accurate."
    ),
    Persona.GHOST_MODE: (
        "You are a mysterious ghost narrator telling stories from the past. "
        "Use an atmospheric, spooky-but-not-terrifying tone. Still keep the "
        "historical facts accurate."
    ),
}


def _build_prompt(
    *,
    historical_text: str,
    language: Language,
    persona: Persona,
) -> str:
    language_name = LANGUAGE_NAMES[language]
    persona_instruction = PERSONA_INSTRUCTIONS[persona]

    return f"""{persona_instruction}

Source material from the museum curator:
{historical_text.strip()}

Write museum exhibit narration in {language_name} ({language.value}).
Use 2-4 paragraphs. Output only the narration text with no titles or labels."""


def generate_persona_text_via_gemini(
    *,
    historical_text: str,
    language: Language,
    persona: Persona,
) -> str:
    if not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GEMINI_API_KEY is not configured",
        )

    base = historical_text.strip()
    if not base:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="historical_text must not be empty",
        )

    prompt = _build_prompt(
        historical_text=base,
        language=language,
        persona=persona,
    )
    url = GEMINI_API_URL.format(model=settings.GEMINI_MODEL)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1024,
        },
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                url,
                params={"key": settings.GEMINI_API_KEY},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini API error: {exc.response.text[:200]}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to reach Gemini API",
        ) from exc

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected response format from Gemini API",
        ) from exc

    result = text.strip()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gemini returned empty text",
        )
    return result
