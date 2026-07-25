from app.core.enums import Language, Persona


def generate_content_text(
    *,
    source_text: str,
    language: Language,
    persona: Persona,
) -> str:
    """
    MVP stub for AI content generation.

    Uses exhibit.source_text plus language/persona markers.
    Replace with a real Anthropic Claude call later.
    """
    base = source_text.strip()
    if not base:
        raise ValueError("source_text must not be empty")

    return (
        f"[{language.value} | {persona.value}]\n\n"
        f"{base}\n\n"
        f"(Stub-generated narration for {persona.value.replace('_', ' ').title()} "
        f"in {language.value}.)"
    )
