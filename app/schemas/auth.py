from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.core.enums import UserRole


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    id: UUID
    email: EmailStr
    token: str
    role: UserRole


class TokenResponse(BaseModel):
    token: str


class MeResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    museum_id: UUID | None


class LogoutResponse(BaseModel):
    message: str
