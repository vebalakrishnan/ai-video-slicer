"""VideoJob model - represents a submitted source video and its processing state."""
import enum

from sqlalchemy import (
    Column,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import TimestampMixin


class VideoSourceType(str, enum.Enum):
    """How the source video was provided."""

    url = "url"
    upload = "upload"


class VideoJobStatus(str, enum.Enum):
    """Lifecycle status of the video processing pipeline."""

    pending = "pending"
    transcribing = "transcribing"
    analyzing = "analyzing"
    rendering = "rendering"
    completed = "completed"
    partial = "partial"
    failed = "failed"


class VideoJob(Base, TimestampMixin):
    """A user-submitted video and its short-generation pipeline state."""

    __tablename__ = "video_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type = Column(Enum(VideoSourceType), nullable=False)
    source_url = Column(String(1000), nullable=True)
    file_path = Column(String(1000), nullable=True)
    title = Column(String(255), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    status = Column(
        Enum(VideoJobStatus),
        default=VideoJobStatus.pending,
        nullable=False,
    )
    transcript = Column(Text, nullable=True)  # timestamped transcript, stored as JSON text
    error_message = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="video_jobs")
    short_clips = relationship(
        "ShortClip",
        back_populates="video_job",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_video_jobs_user_status", "user_id", "status"),
    )
