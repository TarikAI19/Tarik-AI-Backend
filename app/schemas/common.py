from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    limit: int
    offset: int
    total: int
    has_next: bool


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    message: str = "Operation successful"


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: list[T]
    pagination: PaginationMeta
    message: str = "Operation successful"


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
