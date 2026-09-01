"""Celery task chain for the video-to-shorts pipeline (Modules 2-6).

Registered on the shared `celery_app` from app.tasks. Celery tasks run
outside the FastAPI request/response cycle, so they open their own DB
session via `SessionLocal()` directly (never `Depends(get_db)`) and always
close it in a `finally` block.

Orchestration (`process_video_job`):
    pending -> transcribing -> analyzing -> [rendering per clip] -> completed
                                          \\-> partial (< 5 valid shorts)
    (any stage that cannot access/analyze the video at all) -> failed

One bad ShortClip (B-roll or render failure) is caught and marked
status="failed" on that clip only - it never aborts the rest of the job.
"""
import json
import logging
import uuid
from pathlib import Path

from openai import OpenAI

from app.config import settings
from app.database import SessionLocal
from app.models.broll_suggestion import BRollSuggestion
from app.models.short_clip import ShortClip, ShortClipStatus
from app.models.video_job import VideoJob, VideoJobStatus
from app.services import (
    broll_service,
    email_service,
    moment_analysis_service,
    render_service,
    transcription_service,
)
from app.services.transcription_service import TranscriptionError, transcribe_video
from app.tasks import celery_app

logger = logging.getLogger(__name__)

# VideoJob.error_message text mandated by INITIAL.md "Error Handling" contract
# for a video that cannot be accessed/analyzed at all - must match exactly.
VIDEO_UNREACHABLE_MESSAGE = "Unable to access or analyze the provided video URL."

# Base text mandated for the <5-valid-shorts "partial" contract.
PARTIAL_SHORTS_MESSAGE = (
    "The video does not contain five sufficiently strong standalone "
    "segments between 30 and 60 seconds."
)

RENDER_DIR = Path(__file__).resolve().parent.parent.parent / "renders"


def _build_openai_client() -> OpenAI:
    # The SDK's default timeout is 600s (10 min) with no retries visible in
    # logs while it waits - a slow/stalled connection reads as the whole
    # pipeline silently hanging with zero error output for up to 10
    # minutes. 120s is generous for both a Whisper upload and a chat
    # completion; fail fast and let Celery's own error path report it
    # cleanly instead.
    return OpenAI(api_key=settings.OPENAI_API_KEY, timeout=120.0, max_retries=2)


def _persist_short_clip(db, video_job_id: int, short: dict) -> ShortClip:
    clip = ShortClip(
        video_job_id=video_job_id,
        rank=short["rank"],
        category=short["category"],
        start_time=short["start_time"],
        end_time=short["end_time"],
        duration_seconds=short["duration_seconds"],
        title=short["title"],
        transcript_excerpt=short["transcript_excerpt"],
        hook_strength=short["hook_strength"],
        standalone_value=short["standalone_value"],
        engagement=short["engagement"],
        retention=short["retention"],
        payoff=short["payoff"],
        clarity=short["clarity"],
        shareability=short["shareability"],
        viral_potential=short["viral_potential"],
        b_roll_quality=short["b_roll_quality"],
        overall_score=short["overall_score"],
        status=ShortClipStatus.scored,
    )
    db.add(clip)
    db.commit()
    db.refresh(clip)
    return clip


def _render_clip_with_broll(
    db, video_job: VideoJob, clip: ShortClip, openai_client: OpenAI
) -> None:
    """Generate + persist B-roll suggestions, then render the clip.

    Marks the clip status="failed" (and keeps going) if either stage
    raises - a single bad clip must never abort the rest of the job.
    """
    try:
        clip.status = ShortClipStatus.rendering
        db.commit()

        short_dict = {
            "title": clip.title,
            "transcript_excerpt": clip.transcript_excerpt,
            "duration_seconds": clip.duration_seconds,
        }

        broll_rows: list[BRollSuggestion] = []
        try:
            suggestions = broll_service.generate_broll_suggestions(
                short_dict, openai_client, settings.OPENAI_MODEL
            )
        except Exception as exc:
            logger.warning("B-roll generation failed for short %s: %s", clip.id, exc)
            suggestions = []

        for suggestion in suggestions:
            asset_url = broll_service.fetch_stock_asset(
                suggestion["search_keywords"], settings.PEXELS_API_KEY
            )
            row = BRollSuggestion(
                short_clip_id=clip.id,
                start_time=suggestion["start_time"],
                end_time=suggestion["end_time"],
                visual_type=suggestion["visual_type"],
                search_keywords=suggestion["search_keywords"],
                description=suggestion["description"],
                stock_asset_url=asset_url,
            )
            db.add(row)
            broll_rows.append(row)
        db.commit()

        RENDER_DIR.mkdir(parents=True, exist_ok=True)
        output_path = str(RENDER_DIR / f"short_{clip.id}_{uuid.uuid4().hex}.mp4")
        # B-roll suggestions are still generated/persisted above (shown in
        # the UI's B-Roll Suggestions section) but no longer composited
        # into the rendered video - see render_service for why.
        rendered_path = render_service.render_short(video_job, clip, output_path)

        clip.file_path = rendered_path
        clip.status = ShortClipStatus.ready
        db.commit()
    except Exception:
        logger.exception("Rendering pipeline failed for short %s", clip.id)
        db.rollback()
        clip.status = ShortClipStatus.failed
        db.commit()


@celery_app.task
def process_video_job(video_job_id: int) -> None:
    """Full pipeline: transcribe -> identify+score+select shorts -> B-roll+render -> notify."""
    db = SessionLocal()
    try:
        video_job = db.query(VideoJob).filter(VideoJob.id == video_job_id).first()
        if not video_job:
            logger.warning("process_video_job: VideoJob %s not found", video_job_id)
            return

        openai_client = _build_openai_client()

        # --- Transcription ---
        video_job.status = VideoJobStatus.transcribing
        db.commit()

        # URL submissions have no local file yet - download it once via
        # yt-dlp (YouTube + hundreds of other sites, or a plain direct file
        # URL) and persist the path onto VideoJob.file_path, exactly like an
        # upload, so the render stage further down can reuse the same local
        # file instead of trying to feed a platform URL straight to ffmpeg.
        if not video_job.file_path:
            try:
                local_path, metadata = transcription_service.download_source_video(
                    video_job.source_url
                )
            except TranscriptionError as exc:
                logger.warning(
                    "Source video download failed for VideoJob %s: %s", video_job_id, exc
                )
                video_job.status = VideoJobStatus.failed
                video_job.error_message = VIDEO_UNREACHABLE_MESSAGE
                db.commit()
                _notify_failure(db, video_job)
                return

            video_job.file_path = local_path
            if metadata.get("title") and video_job.title == video_job.source_url:
                video_job.title = metadata["title"]
            if metadata.get("duration"):
                video_job.duration_seconds = metadata["duration"]
            db.commit()

        # A retry after a later-stage failure (analysis/render) already has
        # a transcript from a prior successful transcription - re-running
        # Whisper on the same file would just waste minutes for no benefit.
        if video_job.transcript:
            transcript = json.loads(video_job.transcript)
        else:
            try:
                transcript = transcribe_video(video_job.file_path, openai_client)
            except TranscriptionError as exc:
                logger.warning("Transcription failed for VideoJob %s: %s", video_job_id, exc)
                video_job.status = VideoJobStatus.failed
                video_job.error_message = VIDEO_UNREACHABLE_MESSAGE
                db.commit()
                _notify_failure(db, video_job)
                return

            video_job.transcript = json.dumps(transcript)
            if transcript.get("duration"):
                video_job.duration_seconds = transcript["duration"]
            db.commit()

        # --- Moment analysis: identify -> score -> select ---
        video_job.status = VideoJobStatus.analyzing
        db.commit()

        try:
            candidates = moment_analysis_service.identify_candidate_moments(
                transcript["segments"], openai_client, settings.OPENAI_MODEL
            )
        except moment_analysis_service.MomentAnalysisError as exc:
            logger.warning("Candidate identification failed for VideoJob %s: %s", video_job_id, exc)
            video_job.status = VideoJobStatus.failed
            video_job.error_message = VIDEO_UNREACHABLE_MESSAGE
            db.commit()
            _notify_failure(db, video_job)
            return

        scored_candidates = []
        for candidate in candidates:
            try:
                scored_candidates.append(
                    moment_analysis_service.score_candidate(
                        candidate, openai_client, settings.OPENAI_MODEL
                    )
                )
            except moment_analysis_service.MomentAnalysisError as exc:
                logger.warning(
                    "Skipping candidate that failed scoring in VideoJob %s: %s",
                    video_job_id,
                    exc,
                )
                continue

        selected_shorts = moment_analysis_service.select_top_shorts(scored_candidates)

        if len(selected_shorts) < moment_analysis_service.MIN_SHORTS:
            video_job.status = VideoJobStatus.partial
            video_job.error_message = (
                f"{PARTIAL_SHORTS_MESSAGE} Found {len(selected_shorts)} usable segment(s)."
            )
            db.commit()
            _notify_failure(db, video_job)  # partial gets its own message inside email_service
            return

        # --- Persist ShortClip rows ---
        clips: list[ShortClip] = [
            _persist_short_clip(db, video_job_id, short) for short in selected_shorts
        ]

        # --- Per-clip B-roll + render (isolated failures) ---
        for clip in clips:
            _render_clip_with_broll(db, video_job, clip, openai_client)

        video_job.status = VideoJobStatus.completed
        db.commit()
        _notify_completion(db, video_job)

    except Exception:
        logger.exception("process_video_job failed unexpectedly for VideoJob %s", video_job_id)
        db.rollback()
        video_job = db.query(VideoJob).filter(VideoJob.id == video_job_id).first()
        if video_job:
            video_job.status = VideoJobStatus.failed
            # Log the real exception server-side only; never surface raw
            # internals (paths, library errors) to the end user.
            video_job.error_message = (
                "Video processing failed unexpectedly. Please try again."
            )
            db.commit()
            _notify_failure(db, video_job)
    finally:
        db.close()


def _notify_completion(db, video_job: VideoJob) -> None:
    try:
        user = video_job.user
        if user and user.email:
            email_service.send_completion_email(user.email, video_job, settings)
    except Exception:
        logger.exception("Failed to send completion email for VideoJob %s", video_job.id)


def _notify_failure(db, video_job: VideoJob) -> None:
    try:
        user = video_job.user
        if user and user.email:
            if video_job.status == VideoJobStatus.partial:
                email_service.send_completion_email(user.email, video_job, settings)
            else:
                email_service.send_failure_email(user.email, video_job, settings)
    except Exception:
        logger.exception("Failed to send failure/partial email for VideoJob %s", video_job.id)


@celery_app.task
def render_single_short(short_clip_id: int) -> None:
    """Render (or re-render) a single ShortClip on demand (used by POST /shorts/{id}/render).

    Regenerates B-roll suggestions and re-renders, isolated from the rest
    of the parent VideoJob's clips - failures here only affect this clip.
    """
    db = SessionLocal()
    try:
        clip = db.query(ShortClip).filter(ShortClip.id == short_clip_id).first()
        if not clip:
            logger.warning("render_single_short: ShortClip %s not found", short_clip_id)
            return

        video_job = db.query(VideoJob).filter(VideoJob.id == clip.video_job_id).first()
        if not video_job:
            logger.warning(
                "render_single_short: parent VideoJob for ShortClip %s not found", short_clip_id
            )
            clip.status = ShortClipStatus.failed
            db.commit()
            return

        openai_client = _build_openai_client()
        _render_clip_with_broll(db, video_job, clip, openai_client)
    finally:
        db.close()
