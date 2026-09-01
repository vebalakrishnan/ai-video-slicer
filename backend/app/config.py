"""Application settings loaded from environment variables / .env file.

DATABASE-AGENT's app/database.py imports `settings.DATABASE_URL` from this
module, and DEVOPS-AGENT's docker-compose / env files must supply every
variable listed here. Field names below are the contract - do not rename.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Centralized application configuration.

    All values are sourced from environment variables (or a local .env
    file). Never hardcode secrets - see CLAUDE.md "Forbidden Patterns".
    """

    # App
    APP_NAME: str = "AI Video Slicer"

    # Database (required - no default, DATABASE-AGENT's database.py depends on this)
    DATABASE_URL: str

    # Auth / JWT (SECRET_KEY required - no default)
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI (OpenAI + Whisper)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Background jobs (Celery + Redis)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Stock B-roll
    PEXELS_API_KEY: str = ""

    # yt-dlp cookies file (Netscape format), only needed when a platform's
    # anti-bot check (e.g. YouTube on datacenter IPs) blocks anonymous
    # download - optional, ignored when unset or the path doesn't exist.
    YTDLP_COOKIES_FILE: str = ""

    # Base URL of a running bgutil-ytdlp-pot-provider instance (e.g.
    # http://bgutil-provider:4416), used to mint the PO tokens YouTube now
    # requires even for cookie-authenticated web-client requests. Optional -
    # ignored when unset.
    YTDLP_POT_PROVIDER_URL: str = ""

    # Email (SMTP) - all optional
    SMTP_HOST: str = ""
    SMTP_PORT: str = "587"
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # CORS / Frontend
    # http://localhost (port 80) is the docker-compose `frontend` service's
    # actual origin; :5173 is the Vite dev server; :3000 kept for parity
    # with CLAUDE.md's generic template default.
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    FRONTEND_URL: str = "http://localhost"

    class Config:
        env_file = ".env"


settings = Settings()
