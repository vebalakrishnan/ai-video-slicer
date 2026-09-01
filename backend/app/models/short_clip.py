"""ShortClip model - a scored, ranked candidate short generated from a VideoJob."""
import enum

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

# All nine scoring columns below are constrained to the 1-10 (inclusive) range.
_SCORE_COLUMN_NAMES = (
    "hook_strength",
    "standalone_value",
    "engagement",
    "retention",
    "payoff",
    "clarity",
    "shareability",
    "viral_potential",
    "b_roll_quality",
)


class ShortClipCategory(str, enum.Enum):
    """Content category assigned to a short clip."""

    viral = "viral"
    educational = "educational"
    emotional = "emotional"
    surprising = "surprising"
    story = "story"
    other = "other"


class ShortClipStatus(str, enum.Enum):
    """Lifecycle status of a short clip's rendering pipeline."""

    scored = "scored"
    rendering = "rendering"
    ready = "ready"
    failed = "failed"


class ShortClip(Base):
    """A ranked, scored candidate short clip extracted from a VideoJob."""

    __tablename__ = "short_clips"

    id = Column(Integer, primary_key=True, index=True)
    # created_at only (no updated_at) - ShortClip rows are immutable once scored,
    # aside from status/file_path transitions handled by the rendering pipeline.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    video_job_id = Column(
        Integer,
        ForeignKey("video_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rank = Column(Integer, nullable=False)
    category = Column(Enum(ShortClipCategory), nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    title = Column(String(255), nullable=False)
    transcript_excerpt = Column(Text, nullable=False)

    # Scoring dimensions - each an integer from 1 to 10 (see CheckConstraints below).
    hook_strength = Column(Integer, nullable=False)
    standalone_value = Column(Integer, nullable=False)
    engagement = Column(Integer, nullable=False)
    retention = Column(Integer, nullable=False)
    payoff = Column(Integer, nullable=False)
    clarity = Column(Integer, nullable=False)
    shareability = Column(Integer, nullable=False)
    viral_potential = Column(Integer, nullable=False)
    b_roll_quality = Column(Integer, nullable=False)

    overall_score = Column(Float, nullable=False)
    status = Column(
        Enum(ShortClipStatus),
        default=ShortClipStatus.scored,
        nullable=False,
    )
    file_path = Column(String(1000), nullable=True)  # rendered MP4 path

    # Relationships
    video_job = relationship("VideoJob", back_populates="short_clips")
    broll_suggestions = relationship(
        "BRollSuggestion",
        back_populates="short_clip",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_short_clips_video_job_rank", "video_job_id", "rank"),
        *(
            CheckConstraint(
                f"{name} >= 1 AND {name} <= 10", name=f"ck_short_clips_{name}_1_to_10"
            )
            for name in _SCORE_COLUMN_NAMES
        ),
    )
