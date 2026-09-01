"""Business logic for the admin module: user management + platform stats."""
import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.exceptions import NotFoundError
from app.models.user import User
from app.models.video_job import VideoJob, VideoJobStatus

logger = logging.getLogger(__name__)


def list_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
    """Return a page of all users, ordered by id."""
    return db.query(User).order_by(User.id).offset(skip).limit(limit).all()


def update_user_status(db: Session, user_id: int, is_active: bool | None) -> User:
    """Update a user's active status.

    Raises NotFoundError if no user with `user_id` exists. `is_active=None`
    is a no-op update (the user is still fetched/returned as-is).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User")

    if is_active is not None:
        user.is_active = is_active
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Admin updated user id=%s is_active=%s", user_id, is_active)

    return user


def get_platform_stats(db: Session) -> dict:
    """Aggregate platform-wide usage statistics.

    Uses a single GROUP BY query for the per-status job breakdown and a
    separate aggregate for average processing time, avoiding row-by-row
    iteration over the jobs table.
    """
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_video_jobs = db.query(func.count(VideoJob.id)).scalar() or 0

    status_rows = db.query(VideoJob.status, func.count(VideoJob.id)).group_by(VideoJob.status).all()
    jobs_by_status: dict[str, int] = {status.value: count for status, count in status_rows}

    completed = jobs_by_status.get(VideoJobStatus.completed.value, 0)
    partial = jobs_by_status.get(VideoJobStatus.partial.value, 0)
    failed = jobs_by_status.get(VideoJobStatus.failed.value, 0)
    denominator = completed + partial + failed
    success_rate = (completed / denominator) if denominator else 0.0

    avg_processing_time_seconds = (
        db.query(func.avg(func.extract("epoch", VideoJob.updated_at - VideoJob.created_at)))
        .filter(VideoJob.status == VideoJobStatus.completed)
        .scalar()
    )

    return {
        "total_users": total_users,
        "total_video_jobs": total_video_jobs,
        "jobs_by_status": jobs_by_status,
        "success_rate": round(success_rate, 4),
        "avg_processing_time_seconds": (
            round(float(avg_processing_time_seconds), 2)
            if avg_processing_time_seconds is not None
            else None
        ),
    }
