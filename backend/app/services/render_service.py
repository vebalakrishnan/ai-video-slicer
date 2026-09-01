"""Rendering & export service - builds the ffmpeg pipeline for a final short.

Produces a 9:16 (1080x1920) H.264/AAC MP4: trim to [start_time, end_time],
then composite the FULL source frame (scaled to fit, never cropped) over a
blurred, edge-to-edge copy of itself as the background. Uses `ffmpeg-python`
to build the filter graph and shells out to the system `ffmpeg` binary.

Two things intentionally NOT done here, both per product decisions:
- Subtitles are not burned in.
- B-roll clips are not composited into the video (still generated and
  shown in the UI's B-Roll Suggestions section, just not rendered in).

Framing note: a naive "scale to cover + center-crop" (the original
approach) only keeps the center ~30% of a 16:9 screen-recording's width
when reformatting to 9:16 - for desktop/browser recordings, that crops
away exactly the sidebar/tab-bar/table content that makes the recording
readable, while leaving a mostly-empty center strip. Scaling the full
frame to FIT (never cropping) and padding the rest with a blurred,
scaled-to-cover copy of the same frame keeps every pixel of the original
content visible and readable, while still filling the vertical canvas
edge-to-edge instead of leaving hard black bars.
"""
import logging
import os
from typing import TYPE_CHECKING

import ffmpeg

if TYPE_CHECKING:
    from app.models.short_clip import ShortClip
    from app.models.video_job import VideoJob

logger = logging.getLogger(__name__)

OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080


class RenderError(Exception):
    """Raised when rendering a short clip fails."""


def render_short(
    video_job: "VideoJob",
    short: "ShortClip",
    output_path: str,
) -> str:
    """Render a single short clip to a 9:16 H.264/AAC MP4.

    Pipeline: trim source to [short.start_time, short.end_time] -> build a
    blurred, full-bleed background (scale-to-cover 1080x1920) -> overlay the
    same frame scaled to FIT (no cropping, so nothing is ever cut off) on
    top, centered -> encode H.264/AAC MP4.

    Returns the output_path on success. Raises RenderError on failure.
    """
    source = video_job.file_path or video_job.source_url
    if not source:
        raise RenderError(f"VideoJob {video_job.id} has no source file_path/source_url")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    try:
        # 1. Trim to the clip's [start_time, end_time] window.
        video_stream = ffmpeg.input(
            source, ss=short.start_time, to=short.end_time
        )
        trimmed = video_stream.video.filter_multi_output("split")
        bg_in, fg_in = trimmed.stream(0), trimmed.stream(1)

        # 2. Background: scale to COVER the full 1080x1920 canvas (crops,
        # but that's fine here - it's blurred and never meant to be read)
        # then heavily blur it so it reads as ambient motion, not content.
        background = (
            bg_in.filter(
                "scale", OUTPUT_WIDTH, OUTPUT_HEIGHT, force_original_aspect_ratio="increase"
            )
            .filter("crop", OUTPUT_WIDTH, OUTPUT_HEIGHT)
            .filter("gblur", sigma=30)
        )

        # 3. Foreground: scale to FIT within 1080x1920 - the full original
        # frame, never cropped, so no content is ever cut off.
        foreground = fg_in.filter(
            "scale", OUTPUT_WIDTH, OUTPUT_HEIGHT, force_original_aspect_ratio="decrease"
        )

        # 4. Composite the full foreground centered over the blurred background.
        v = ffmpeg.overlay(background, foreground, x="(W-w)/2", y="(H-h)/2")

        # 5. Encode H.264/AAC MP4.
        output = ffmpeg.output(
            v,
            video_stream.audio,
            output_path,
            vcodec="libx264",
            acodec="aac",
            video_bitrate="4M",
            audio_bitrate="128k",
            format="mp4",
        ).overwrite_output()

        output.run(capture_stdout=True, capture_stderr=True, quiet=True)
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else str(exc)
        logger.exception("ffmpeg render failed for short %s: %s", short.id, stderr)
        raise RenderError(f"ffmpeg render failed for short {short.id}: {stderr}") from exc
    except Exception as exc:
        logger.exception("Render pipeline failed for short %s", short.id)
        raise RenderError(f"Render pipeline failed for short {short.id}: {exc}") from exc

    return output_path
