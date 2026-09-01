"""Business logic for registration, login, token refresh, and profile updates."""
import logging

from sqlalchemy.orm import Session

from app.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.exceptions import ConflictError, UnauthorizedError
from app.models.user import User
from app.schemas.auth import RegisterRequest, Token
from app.schemas.user import UserUpdateRequest

logger = logging.getLogger(__name__)


def register_user(db: Session, req: RegisterRequest) -> User:
    """Create a new user account.

    Raises ConflictError if the email is already registered.
    """
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise ConflictError("Email already registered")

    user = User(
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Registered new user id=%s", user.id)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    """Validate credentials and return the matching active User.

    Raises UnauthorizedError if the email/password combination is invalid.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")
    if not user.is_active:
        raise UnauthorizedError("User account is inactive")
    return user


def refresh_tokens(db: Session, refresh_token: str) -> Token:
    """Validate a refresh token and issue a new access + refresh token pair.

    Raises UnauthorizedError if the token is missing/invalid/expired, is not
    a "refresh"-type token, or does not resolve to an active user.
    """
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise UnauthorizedError("Invalid refresh token")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first() if user_id else None
    if not user or not user.is_active:
        raise UnauthorizedError("Invalid refresh token")

    return Token(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
    )


def update_user(db: Session, user: User, req: UserUpdateRequest) -> User:
    """Apply a self-service profile update to an existing User."""
    if req.full_name is not None:
        user.full_name = req.full_name
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
