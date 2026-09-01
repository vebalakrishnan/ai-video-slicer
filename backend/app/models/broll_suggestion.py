"""BRollSuggestion model - a suggested B-roll insert for a ShortClip."""
import enum

from sqlalchemy import Column, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class BRollVisualType(str, enum.Enum):
    """Kind of visual suggested for a B-roll insert."""

    stock_footage = "stock_footage"
    image = "image"
    screenshot = "screenshot"
    screen_recording = "screen_recording"
    chart = "chart"
    animation = "animation"


class BRollSuggestion(Base):
    """A suggested B-roll visual to overlay within a short clip's timeline."""

    __tablename__ = "broll_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    short_clip_id = Column(
        Integer,
        ForeignKey("short_clips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    visual_type = Column(Enum(BRollVisualType), nullable=False)
    search_keywords = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    stock_asset_url = Column(String(1000), nullable=True)

    # Relationships
    short_clip = relationship("ShortClip", back_populates="broll_suggestions")
