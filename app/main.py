from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import auth, dashboard, exhibits, experience, museums, visitor
from app.core.config import settings
from app.core.exceptions import AppError
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
app.include_router(visitor.router, prefix="/visitor", tags=["visitor"])
app.include_router(experience.router, prefix="/experience", tags=["experience"])

audio_dir = Path(settings.AUDIO_STORAGE_DIR)
audio_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media/audio", StaticFiles(directory=str(audio_dir)), name="audio")


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    content: dict = {
        "success": False,
        "error": exc.error_code,
        "message": exc.message,
    }
    if exc.details is not None:
        content["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=content)


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
