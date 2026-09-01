"""Password hashing and JWT access/refresh token creation & decoding.

Exact pattern from skills/BACKEND.md "JWT Auth" section, using the
SECRET_KEY / ALGORITHM / ACCESS_TOKEN_EXPIRE_MINUTES / REFRESH_TOKEN_EXPIRE_DAYS
fields from app.config.settings.
"""
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plaintext password against a bcrypt hash."""
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    """Create a short-lived JWT access token (type=access)."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {**data, "exp": expire, "type": "access"}, settings.SECRET_KEY, settings.ALGORITHM
    )


def create_refresh_token(data: dict) -> str:
    """Create a long-lived JWT refresh token (type=refresh)."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {**data, "exp": expire, "type": "refresh"}, settings.SECRET_KEY, settings.ALGORITHM
    )


def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT, returning its payload or None if invalid/expired."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
