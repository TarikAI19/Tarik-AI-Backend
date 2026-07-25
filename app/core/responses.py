from typing import Any


def success_response(
    data: Any,
    message: str | None = None,
) -> dict[str, Any]:
    response: dict[str, Any] = {"success": True, "data": data}
    if message is not None:
        response["message"] = message
    return response


def paginated_response(
    data: list[Any],
    *,
    limit: int,
    offset: int,
    total: int,
    message: str | None = None,
) -> dict[str, Any]:
    response: dict[str, Any] = {
        "success": True,
        "data": data,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_next": offset + limit < total,
        },
    }
    if message is not None:
        response["message"] = message
    return response
