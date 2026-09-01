"""Pydantic schemas for the analytics module."""
from pydantic import BaseModel


class AnalyticsOverview(BaseModel):
    """Aggregate usage metrics for the current user's account."""

    videos_processed: int
    shorts_generated: int
    avg_overall_score: float
    avg_processing_time_seconds: float | None
