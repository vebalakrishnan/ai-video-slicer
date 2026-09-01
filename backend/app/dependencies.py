"""Shared FastAPI dependencies.

Re-exports `get_db` for convenient importing (`from app.dependencies import
get_db, get_current_user`) and provides the `get_current_user` auth
dependency used by every protected router.

NOTE: `app.auth.jwt` and `app.models` are created by other Phase 1/2 agents
(DATABASE-AGENT owns app/models, and Phase 2's AUTH backend work adds
app/auth/jwt.py). This module is written against that contract now so it
is ready to run as soon as those files land.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.jwt import decode_token
from app.database import (
    get_db,
)
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the current authenticated user from a bearer JWT access token.

    Raises HTTP 401 if the token is missing/invalid/expired, is not an
    "access" token, or does not resolve to an active User.
    """
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user
