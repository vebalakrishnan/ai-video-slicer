"""Pydantic schemas for the admin module."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class AdminUserResponse(BaseModel):
    """Admin-facing representation of a User row."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None
    is_active: bool
    is_admin: bool
    created_at: datetime


class AdminUserUpdateRequest(BaseModel):
    """Payload for PUT /admin/users/{id} - only status is admin-editable."""

    is_active: bool | None = None


class AdminStatsResponse(BaseModel):
    """Platform-wide usage statistics."""

    total_users: int
    total_video_jobs: int
    jobs_by_status: dict[str, int]
    success_rate: float
    avg_processing_time_seconds: float | None
