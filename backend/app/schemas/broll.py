"""Pydantic schemas for B-roll suggestion responses."""
from pydantic import BaseModel, ConfigDict

from app.models.broll_suggestion import BRollVisualType


class BRollSuggestionResponse(BaseModel):
    """Full representation of a BRollSuggestion for a ShortClip."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    short_clip_id: int
    start_time: float
    end_time: float
    visual_type: BRollVisualType
    search_keywords: str
    description: str
    stock_asset_url: str | None
