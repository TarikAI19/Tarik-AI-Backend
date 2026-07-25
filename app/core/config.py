import os

from dotenv import load_dotenv

load_dotenv()

# Built-in ElevenLabs voice — only the API key is required from the user.
DEFAULT_ELEVENLABS_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_DAYS: int = int(os.getenv("JWT_EXPIRE_DAYS", "7"))
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "").strip()
    # Optional; empty env falls back to the default public voice.
    ELEVENLABS_VOICE_ID: str = (
        os.getenv("ELEVENLABS_VOICE_ID", "").strip() or DEFAULT_ELEVENLABS_VOICE_ID
    )
    TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "elevenlabs")
    AUDIO_STORAGE_DIR: str = os.getenv("AUDIO_STORAGE_DIR", "storage/audio")
    # Kept for visitor Q&A / other features
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    # Exhibit content generation
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
    ADDIS_AI_API_KEY: str = os.getenv("ADDIS_AI_API_KEY", "").strip()
    ADDIS_AI_BASE_URL: str = os.getenv(
        "ADDIS_AI_BASE_URL",
        "https://api.addisassistant.com/api/v1",
    ).rstrip("/")
    # Addis Voices 2 (AM / OM TTS)
    ADDIS_TTS_VOICE_AM: str = (
        os.getenv("ADDIS_TTS_VOICE_AM", "").strip() or "am-hamen"
    )
    ADDIS_TTS_VOICE_OM: str = (
        os.getenv("ADDIS_TTS_VOICE_OM", "").strip() or "om-bikila"
    )


settings = Settings()

if not settings.JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable is not set")
