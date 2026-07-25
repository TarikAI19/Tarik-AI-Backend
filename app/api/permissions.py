from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.api.deps import get_current_user
from app.core.enums import UserRole
from app.models.user import User


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    allowed = set(roles)

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return dependency


def assert_museum_access(user: User, museum_id: UUID) -> None:
    """SUPER_ADMIN can access any museum; others only their assigned museum."""
    if user.role == UserRole.SUPER_ADMIN:
        return
    if user.museum_id is None or user.museum_id != museum_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this museum",
        )


def assert_can_manage_museum(user: User, museum_id: UUID) -> None:
    """SUPER_ADMIN or MUSEUM_ADMIN of that museum may mutate museum metadata."""
    if user.role == UserRole.SUPER_ADMIN:
        return
    if user.role == UserRole.MUSEUM_ADMIN and user.museum_id == museum_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not allowed to manage this museum",
    )
