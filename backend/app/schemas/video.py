"""Pydantic schemas for video ingestion requests/responses."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.video_job import VideoJobStatus, VideoSourceType


class VideoSubmitRequest(BaseModel):
    """JSON payload for POST /videos when submitting a video by URL.

    File uploads use multipart/form-data instead (see routers/videos.py),
    so this schema only covers the URL-submission body shape.
    """

    source_url: str | None = None


class VideoJobResponse(BaseModel):
    """Public representation of a VideoJob returned by video ingestion endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    source_type: VideoSourceType
    source_url: str | None
    file_path: str | None
    title: str | None
    duration_seconds: float | None
    status: VideoJobStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime | None


class VideoJobListResponse(BaseModel):
    """Paginated list wrapper for VideoJob rows."""

    videos: list[VideoJobResponse]
    total: int
