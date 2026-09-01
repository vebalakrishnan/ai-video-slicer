"""Pydantic schemas for user read/update payloads."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    """Public representation of a User returned by auth/user endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None
    is_active: bool
    is_admin: bool
    created_at: datetime


class UserUpdateRequest(BaseModel):
    """Payload for PUT /auth/me - only self-editable fields."""

    full_name: str | None = None
