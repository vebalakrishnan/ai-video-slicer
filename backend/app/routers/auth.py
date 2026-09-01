"""Authentication endpoints: register, login, refresh, logout, profile.

Credentials-only (email + password) - see CLAUDE.md "Authentication".
/register and /login are rate-limited (5/minute per client IP) per the
CLAUDE.md security requirement, using the shared slowapi limiter in
app.rate_limit.
"""
from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token, create_refresh_token
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.rate_limit import limiter
from app.schemas.auth import RefreshRequest, RegisterRequest, Token
from app.schemas.user import UserResponse, UserUpdateRequest
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request,
    req: RegisterRequest,
    db: Session = Depends(get_db),
) -> User:
    """Create a new credentials-based user account."""
    return auth_service.register_user(db, req)


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """Authenticate with email (as `username`) + password and issue a token pair."""
    user = auth_service.authenticate_user(db, form.username, form.password)
    return Token(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
    )


@router.post("/refresh", response_model=Token)
async def refresh(req: RefreshRequest, db: Session = Depends(get_db)) -> Token:
    """Exchange a valid refresh token for a new access + refresh token pair."""
    return auth_service.refresh_tokens(db, req.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(_user: User = Depends(get_current_user)) -> None:
    """Log out the current user.

    MVP LIMITATION: JWTs are stateless and there is no refresh-token
    blocklist table yet, so this endpoint cannot actually invalidate
    outstanding tokens server-side - it only confirms the caller is
    authenticated. The client is responsible for discarding its tokens.
    A future iteration should add a token-blocklist/session table to make
    logout (and forced revocation) effective server-side.
    """
    return


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)) -> User:
    """Return the current authenticated user's profile."""
    return user


@router.put("/me", response_model=UserResponse)
async def update_me(
    req: UserUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Update the current authenticated user's own profile."""
    return auth_service.update_user(db, user, req)
