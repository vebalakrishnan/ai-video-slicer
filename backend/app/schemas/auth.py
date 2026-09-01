"""Pydantic schemas for authentication requests/responses.

Credentials-only auth (email + password) - see CLAUDE.md "Authentication".
No Google OAuth / social login schemas are defined here or anywhere else.
"""
from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """Access + refresh token pair returned by /auth/login and /auth/refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    """Payload for POST /auth/register."""

    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None


class RefreshRequest(BaseModel):
    """Payload for POST /auth/refresh."""

    refresh_token: str
