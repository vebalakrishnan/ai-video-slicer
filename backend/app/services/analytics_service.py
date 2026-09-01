"""Business logic for the per-user analytics overview."""
import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.short_clip import ShortClip
from app.models.video_job import VideoJob, VideoJobStatus

logger = logging.getLogger(__name__)


def get_user_overview(db: Session, user_id: int) -> dict:
    """Aggregate usage metrics for a single user's account.

    Runs three small aggregate queries (job count, shorts count/avg score,
    avg completed-job processing time) rather than loading rows into Python,
    to avoid N+1 queries as a user's job/short history grows.
    """
    videos_processed = (
        db.query(func.count(VideoJob.id)).filter(VideoJob.user_id == user_id).scalar()
    ) or 0

    shorts_count, avg_score = (
        db.query(func.count(ShortClip.id), func.avg(ShortClip.overall_score))
        .join(VideoJob, ShortClip.video_job_id == VideoJob.id)
        .filter(VideoJob.user_id == user_id)
        .one()
    )

    avg_processing_time_seconds = (
        db.query(
            func.avg(func.extract("epoch", VideoJob.updated_at - VideoJob.created_at))
        )
        .filter(
            VideoJob.user_id == user_id,
            VideoJob.status == VideoJobStatus.completed,
        )
        .scalar()
    )

    return {
        "videos_processed": videos_processed,
        "shorts_generated": shorts_count or 0,
        "avg_overall_score": round(float(avg_score), 2) if avg_score is not None else 0.0,
        "avg_processing_time_seconds": (
            round(float(avg_processing_time_seconds), 2)
            if avg_processing_time_seconds is not None
            else None
        ),
    }
