"""Admin endpoints: user management + platform-wide stats.

All endpoints require the caller to be an authenticated, active user with
`is_admin=True` (see `require_admin` below), which wraps `get_current_user`
and raises 403 otherwise.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import AppException
from app.models.user import User
from app.schemas.admin import (
    AdminStatsResponse,
    AdminUserResponse,
    AdminUserUpdateRequest,
)
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Resolve the current user and require `is_admin=True`.

    Raises HTTP 403 (via AppException) if the authenticated user is not an
    admin.
    """
    if not user.is_admin:
        raise AppException("Admin privileges required", "FORBIDDEN", 403)
    return user


@router.get("/users", response_model=list[AdminUserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[User]:
    """List all users (paginated)."""
    return admin_service.list_users(db, skip, limit)


@router.put("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: int,
    req: AdminUserUpdateRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> User:
    """Update a user's status (e.g. activate/deactivate)."""
    return admin_service.update_user_status(db, user_id, req.is_active)


@router.get("/stats", response_model=AdminStatsResponse)
async def get_stats(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    """Return platform-wide usage statistics."""
    return admin_service.get_platform_stats(db)
