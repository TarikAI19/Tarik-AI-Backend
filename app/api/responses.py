from typing import Any

from app.schemas.common import PaginatedResponse, PaginationMeta, SuccessResponse


def ok(data: Any, message: str = "Operation successful") -> dict[str, Any]:
    return SuccessResponse(data=data, message=message).model_dump()


def ok_list(
    data: list[Any],
    *,
    limit: int,
    offset: int,
    total: int,
    message: str = "Operation successful",
) -> dict[str, Any]:
    pagination = PaginationMeta(
        limit=limit,
        offset=offset,
        total=total,
        has_next=offset + limit < total,
    )
    return PaginatedResponse(
        data=data,
        pagination=pagination,
        message=message,
    ).model_dump()
