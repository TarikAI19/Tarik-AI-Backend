from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1 import auth, dashboard, exhibits, museums
from app.core.config import settings
from app.db.base import Base
from app.db.database import engine
from app.models import (  # noqa: F401
    exhibit,
    exhibit_content,
    museum,
    user,
    visit,
    visitor_session,
)

app = FastAPI(title="Tarik AI Backend")

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(museums.router, prefix="/museums", tags=["museums"])
app.include_router(exhibits.router, prefix="/exhibits", tags=["exhibits"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])

audio_dir = Path(settings.AUDIO_STORAGE_DIR)
audio_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media/audio", StaticFiles(directory=str(audio_dir)), name="audio")


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
