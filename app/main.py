from fastapi import FastAPI

from app.api.v1 import auth
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


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
