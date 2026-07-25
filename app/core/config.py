import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_DAYS: int = int(os.getenv("JWT_EXPIRE_DAYS", "7"))
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
    TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "elevenlabs")
    AUDIO_STORAGE_DIR: str = os.getenv("AUDIO_STORAGE_DIR", "storage/audio")


settings = Settings()

if not settings.JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable is not set")
