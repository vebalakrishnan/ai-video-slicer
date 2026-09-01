"""FastAPI application entrypoint.

Phase 1 (Foundation): app instance, CORS, health check, and the global
AppException handler only. Phase 2 module agents register their routers
below (see commented placeholders).
"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.exceptions import AppException
from app.rate_limit import limiter
from app.routers import admin, analytics, auth, shorts, videos

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting (slowapi) - protects auth endpoints (/register, /login) per
# CLAUDE.md's security requirement. See app/rate_limit.py for the shared
# Limiter instance and app/routers/auth.py for the per-endpoint decorators.
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Translate a RateLimitExceeded into the app's uniform JSON error body."""
    logger.warning("Rate limit exceeded: %s", request.url.path)
    return JSONResponse(
        status_code=429,
        content={"error": "RATE_LIMITED", "message": "Too many requests, please try again later."},
    )


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Translate any AppException (and its subclasses) into a uniform JSON error body."""
    logger.warning("AppException handled: %s (%s)", exc.message, exc.code)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.code, "message": exc.message},
    )


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness/readiness check used by DEVOPS-AGENT's Docker healthcheck."""
    return {"status": "healthy"}


# --- Phase 2: module routers ---
app.include_router(auth.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(videos.router, prefix="/api/v1")
app.include_router(shorts.router, prefix="/api/v1")
