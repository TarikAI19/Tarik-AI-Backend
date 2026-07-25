from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    LogoutResponse,
    MeResponse,
    SignupRequest,
    TokenResponse,
)
from app.services import auth_service

router = APIRouter()
bearer_scheme = HTTPBearer()


@router.post("/signup", response_model=AuthResponse)
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    user, token = auth_service.signup(
        db,
        email=body.email,
        password=body.password,
        full_name=body.full_name,
    )
    return AuthResponse(
        id=user.id,
        email=user.email,
        token=token,
        role=user.role,
    )


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user, token = auth_service.login(
        db,
        email=body.email,
        password=body.password,
    )
    return AuthResponse(
        id=user.id,
        email=user.email,
        token=token,
        role=user.role,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    token = auth_service.refresh_access_token(credentials.credentials, db)
    return TokenResponse(token=token)


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)):
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        museum_id=current_user.museum_id,
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(_current_user: User = Depends(get_current_user)):
    return LogoutResponse(message="logged out")
