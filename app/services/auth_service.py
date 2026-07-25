from uuid import UUID

import jwt
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User


def signup(db: Session, email: str, password: str, full_name: str) -> tuple[User, str]:
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role=UserRole.CURATOR,
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        ) from None

    token = create_access_token(str(user.id), user.email, user.role.value)
    return user, token


def login(db: Session, email: str, password: str) -> tuple[User, str]:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(str(user.id), user.email, user.role.value)
    return user, token


def refresh_access_token(token: str, db: Session) -> str:
    try:
        payload = decode_token(token, verify_exp=False)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user = db.get(User, UUID(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return create_access_token(str(user.id), user.email, user.role.value)
