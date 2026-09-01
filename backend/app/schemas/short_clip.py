"""Pydantic schemas for generated short clip responses."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.short_clip import ShortClipCategory, ShortClipStatus


class ShortClipResponse(BaseModel):
    """Full representation of a scored/rendered ShortClip."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    video_job_id: int
    rank: int
    category: ShortClipCategory
    start_time: float
    end_time: float
    duration_seconds: float
    title: str
    transcript_excerpt: str

    # Scoring dimensions (1-10 each) - see moment_analysis_service for how
    # each is computed.
    hook_strength: int
    standalone_value: int
    engagement: int
    retention: int
    payoff: int
    clarity: int
    shareability: int
    viral_potential: int
    b_roll_quality: int

    overall_score: float
    status: ShortClipStatus
    file_path: str | None
    created_at: datetime


class ShortClipListResponse(BaseModel):
    """List wrapper for a VideoJob's ranked ShortClips."""

    shorts: list[ShortClipResponse]
    total: int
