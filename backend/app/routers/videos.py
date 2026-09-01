"""Video ingestion endpoints (Module 2).

POST /videos accepts EITHER:
  - JSON body `{"source_url": "..."}`               (Content-Type: application/json)
  - multipart/form-data with a `file` field           (Content-Type: multipart/form-data)
on a single endpoint, dispatched by inspecting the request's Content-Type
header - this avoids forcing two separate routes for what is conceptually
one "submit a video" action, while keeping each body shape's own
validation (VideoSubmitRequest for the URL case).

All endpoints are scoped to `current_user.id` - a job's existence is
defined as "exists AND is owned by the caller"; anything else 404s via
NotFoundError, never leaking whether a job exists for another user.
"""
import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.short_clip import ShortClip
from app.models.user import User
from app.models.video_job import VideoJob, VideoJobStatus, VideoSourceType
from app.schemas.short_clip import ShortClipListResponse
from app.schemas.video import VideoJobListResponse, VideoJobResponse, VideoSubmitRequest
from app.tasks.pipeline import process_video_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["videos"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"

# Hard cap on an uploaded file's size, to bound memory/disk usage per request.
MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB

# Only accept extensions we can actually feed into the transcription/render
# pipeline - never trust an arbitrary client-supplied extension verbatim.
ALLOWED_UPLOAD_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}

# Statuses that mean "the pipeline is actively running" - generate-shorts
# must not be re-dispatched while one of these is in effect.
_PROCESSING_STATUSES = {
    VideoJobStatus.transcribing,
    VideoJobStatus.analyzing,
    VideoJobStatus.rendering,
}


def _get_owned_job(db: Session, video_job_id: int, user_id: int) -> VideoJob:
    job = (
        db.query(VideoJob)
        .filter(VideoJob.id == video_job_id, VideoJob.user_id == user_id)
        .first()
    )
    if not job:
        raise NotFoundError("Video job")
    return job


@router.post("/", response_model=VideoJobResponse, status_code=status.HTTP_201_CREATED)
async def submit_video(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VideoJob:
    """Submit a video by URL (JSON) or by file upload (multipart/form-data)."""
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("file")
        if upload is None or not isinstance(upload, UploadFile):
            raise ValidationError("Multipart upload must include a 'file' field")

        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        original_name = upload.filename or "upload"
        extension = os.path.splitext(original_name)[1].lower()
        if extension not in ALLOWED_UPLOAD_EXTENSIONS:
            raise ValidationError(
                f"Unsupported file extension '{extension}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}"
            )
        stored_filename = f"{uuid.uuid4().hex}{extension}"
        dest_path = UPLOAD_DIR / stored_filename

        contents = await upload.read(MAX_UPLOAD_BYTES + 1)
        if not contents:
            raise ValidationError("Uploaded file is empty")
        if len(contents) > MAX_UPLOAD_BYTES:
            raise ValidationError(f"Uploaded file exceeds the {MAX_UPLOAD_BYTES} byte limit")

        def _write_upload(path: Path, data: bytes) -> None:
            with open(path, "wb") as f:
                f.write(data)

        await run_in_threadpool(_write_upload, dest_path, contents)

        title_field = form.get("title")
        title = str(title_field) if title_field else os.path.splitext(original_name)[0]

        video_job = VideoJob(
            user_id=current_user.id,
            source_type=VideoSourceType.upload,
            file_path=str(dest_path),
            title=title,
            status=VideoJobStatus.pending,
        )
    else:
        payload = await request.json()
        req = VideoSubmitRequest(**payload)
        if not req.source_url:
            raise ValidationError("source_url is required when submitting a video by URL")

        video_job = VideoJob(
            user_id=current_user.id,
            source_type=VideoSourceType.url,
            source_url=req.source_url,
            title=req.source_url,
            status=VideoJobStatus.pending,
        )

    db.add(video_job)
    db.commit()
    db.refresh(video_job)
    logger.info("Created VideoJob %s for user %s", video_job.id, current_user.id)
    return video_job


@router.get("/", response_model=VideoJobListResponse)
async def list_videos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VideoJobListResponse:
    """List the current user's video jobs, most recent first."""
    query = (
        db.query(VideoJob)
        .filter(VideoJob.user_id == current_user.id)
        .order_by(VideoJob.created_at.desc())
    )
    total = query.count()
    jobs = query.offset(skip).limit(limit).all()
    return VideoJobListResponse(videos=jobs, total=total)


@router.get("/{video_job_id}", response_model=VideoJobResponse)
async def get_video(
    video_job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VideoJob:
    """Get a single video job's status/metadata."""
    return _get_owned_job(db, video_job_id, current_user.id)


@router.delete("/{video_job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a video job (cascades to its shorts/B-roll rows) and best-effort
    delete the underlying source file and any rendered clip files from disk."""
    job = _get_owned_job(db, video_job_id, current_user.id)

    file_paths = [job.file_path]
    file_paths.extend(clip.file_path for clip in job.short_clips)

    db.delete(job)
    db.commit()

    for path in file_paths:
        if not path:
            continue
        try:
            os.remove(path)
        except OSError as exc:
            logger.warning("Best-effort delete failed for %s: %s", path, exc)


@router.post("/{video_job_id}/generate-shorts", response_model=VideoJobResponse)
async def generate_shorts(
    video_job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VideoJob:
    """Dispatch the async pipeline (transcription -> analysis -> render -> notify)."""
    job = _get_owned_job(db, video_job_id, current_user.id)

    if job.status in _PROCESSING_STATUSES:
        raise ConflictError(
            f"Video job {video_job_id} is already processing (status={job.status.value})"
        )

    # Re-running an already-completed/partial/failed job must not pile up a
    # second set of ShortClip/BRollSuggestion rows and orphaned rendered
    # files alongside the old ones - clear the prior results first.
    existing_clips = db.query(ShortClip).filter(ShortClip.video_job_id == job.id).all()
    for clip in existing_clips:
        if clip.file_path:
            try:
                os.remove(clip.file_path)
            except OSError as exc:
                logger.warning("Best-effort delete failed for %s: %s", clip.file_path, exc)
        db.delete(clip)

    job.status = VideoJobStatus.pending
    job.error_message = None
    db.commit()
    db.refresh(job)

    process_video_job.delay(job.id)
    logger.info("Dispatched process_video_job for VideoJob %s", job.id)
    return job


@router.get("/{video_job_id}/shorts", response_model=ShortClipListResponse)
async def list_shorts_for_video(
    video_job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShortClipListResponse:
    """List this video job's generated shorts, ordered by rank."""
    job = _get_owned_job(db, video_job_id, current_user.id)
    clips = (
        db.query(ShortClip)
        .filter(ShortClip.video_job_id == job.id)
        .order_by(ShortClip.rank)
        .all()
    )
    return ShortClipListResponse(shorts=clips, total=len(clips))
