"""Short clip endpoints (Modules 3-5: scoring detail, B-roll, render, download).

ShortClip has no direct user_id column, so ownership is always checked by
joining through the parent VideoJob's user_id - a short that exists but
belongs to another user's video job 404s exactly like one that doesn't
exist at all.
"""
import logging
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.exceptions import ConflictError, NotFoundError
from app.models.broll_suggestion import BRollSuggestion
from app.models.short_clip import ShortClip, ShortClipStatus
from app.models.user import User
from app.models.video_job import VideoJob
from app.schemas.broll import BRollSuggestionResponse
from app.schemas.short_clip import ShortClipResponse
from app.tasks.pipeline import render_single_short

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shorts", tags=["shorts"])


def _get_owned_short(db: Session, short_id: int, user_id: int) -> ShortClip:
    clip = (
        db.query(ShortClip)
        .join(VideoJob, ShortClip.video_job_id == VideoJob.id)
        .filter(ShortClip.id == short_id, VideoJob.user_id == user_id)
        .first()
    )
    if not clip:
        raise NotFoundError("Short clip")
    return clip


@router.get("/{short_id}", response_model=ShortClipResponse)
async def get_short(
    short_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShortClip:
    """Full detail for a short clip, including all 9 scores + transcript excerpt."""
    return _get_owned_short(db, short_id, current_user.id)


@router.get("/{short_id}/broll", response_model=list[BRollSuggestionResponse])
async def list_broll(
    short_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BRollSuggestion]:
    """List B-roll suggestions (with fetched stock asset URLs) for a short."""
    clip = _get_owned_short(db, short_id, current_user.id)
    return (
        db.query(BRollSuggestion)
        .filter(BRollSuggestion.short_clip_id == clip.id)
        .order_by(BRollSuggestion.start_time)
        .all()
    )


@router.post("/{short_id}/render", response_model=ShortClipResponse)
async def render_short_endpoint(
    short_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShortClip:
    """Trigger (or re-trigger) an async render for this short clip."""
    clip = _get_owned_short(db, short_id, current_user.id)

    if clip.status == ShortClipStatus.rendering:
        raise ConflictError(f"Short clip {short_id} is already rendering")

    clip.status = ShortClipStatus.rendering
    db.commit()
    db.refresh(clip)

    render_single_short.delay(clip.id)
    logger.info("Dispatched render_single_short for ShortClip %s", clip.id)
    return clip


@router.get("/{short_id}/download")
async def download_short(
    short_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Download the rendered MP4 for a short clip. Requires status == 'ready'."""
    clip = _get_owned_short(db, short_id, current_user.id)

    if clip.status != ShortClipStatus.ready or not clip.file_path:
        raise ConflictError(
            f"Short clip {short_id} is not ready for download (status={clip.status.value})"
        )
    if not await run_in_threadpool(Path(clip.file_path).exists):
        raise NotFoundError("Rendered file")

    return FileResponse(
        clip.file_path,
        media_type="video/mp4",
        filename=Path(clip.file_path).name,
    )
