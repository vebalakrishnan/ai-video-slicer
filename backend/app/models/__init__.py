"""Model package - imports every model so Alembic autogenerate can discover them.

`Base` is re-exported here for convenience, but the canonical definition lives
in app.database (per skills/DATABASE.md).
"""
from app.database import Base
from app.models.broll_suggestion import BRollSuggestion, BRollVisualType
from app.models.short_clip import ShortClip, ShortClipCategory, ShortClipStatus
from app.models.user import User
from app.models.video_job import VideoJob, VideoJobStatus, VideoSourceType

__all__ = [
    "BRollSuggestion",
    "BRollVisualType",
    "Base",
    "ShortClip",
    "ShortClipCategory",
    "ShortClipStatus",
    "User",
    "VideoJob",
    "VideoJobStatus",
    "VideoSourceType",
]
