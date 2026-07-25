from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(user_id: str, email: str, role: str) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.JWT_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, *, verify_exp: bool = True) -> dict:
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
        options={"verify_exp": verify_exp},
    )
