"""Video download + transcription services (Module 2/3 pipeline entry point).

`download_source_video` fetches a URL-submitted video via yt-dlp - it
supports YouTube and hundreds of other sites, and falls back to a plain
direct-file download (its "generic" extractor) for a bare video URL. The
downloaded file is kept (not a throwaway temp file): `render_service` also
needs local access to the same video later in the pipeline, so the caller
persists the returned path onto `VideoJob.file_path`, exactly like an
uploaded file.

`transcribe_video` is the Whisper step and only ever operates on an
already-local file path - all download/URL handling lives in
`download_source_video`, called once per pipeline run before it.

The `openai_client` is injected by the caller (Celery task) rather than
imported as a module-level global, so this module stays unit-testable with
a mock client.
"""
import ipaddress
import logging
import math
import os
import socket
import tempfile
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import ffmpeg
import yt_dlp

from app.config import settings

logger = logging.getLogger(__name__)

DOWNLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "downloads"

# Hard cap on how large a downloaded source video may be - bounds worker
# disk/bandwidth usage and guards against a malicious/misconfigured host.
# 2GB comfortably covers a 2-3 hour course/tutorial video, matching the
# upload path's MAX_UPLOAD_BYTES (app/routers/videos.py).
MAX_DOWNLOAD_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB

# OpenAI's Whisper endpoint hard-rejects any request body over 25MB (413).
# A full video file (even a short one) routinely exceeds this, so anything
# above the limit gets a compressed, audio-only track extracted first -
# Whisper only needs the audio anyway. The full video itself is untouched
# and still used later for rendering.
WHISPER_MAX_BYTES = 25 * 1024 * 1024  # 25 MB
# 64kbps mono; ~50 minutes of audio fits this within the 25MB cap on its
# own. Longer sources are split into WHISPER_CHUNK_TARGET_BYTES-sized
# pieces (see transcribe_video) rather than being limited by it.
WHISPER_AUDIO_BITRATE = "64k"
WHISPER_AUDIO_BITRATE_BPS = 64_000  # must match WHISPER_AUDIO_BITRATE above

# Per-chunk target when a source is too long for a single Whisper request -
# kept well under WHISPER_MAX_BYTES (not right up against it) since AAC
# encoding/container overhead means actual chunk size can run a bit over
# the pure bitrate*duration estimate used to pick chunk boundaries.
WHISPER_CHUNK_TARGET_BYTES = 20 * 1024 * 1024  # 20 MB

# Generous per-call timeout for the transcription request specifically -
# uploading + transcribing a long video's full audio can genuinely take
# several minutes; this is intentionally much larger than the OpenAI
# client's shared default (see app/tasks/pipeline.py._build_openai_client),
# which stays short so the fast chat-completion calls elsewhere still fail
# fast on a real stall.
WHISPER_TIMEOUT_SECONDS = 600.0


class TranscriptionError(Exception):
    """Base error for any download/transcription failure."""


class VideoUnreachableError(TranscriptionError):
    """Raised when the source video cannot be located/downloaded/opened at all.

    The pipeline maps this to VideoJob.status="failed" with the exact
    message "Unable to access or analyze the provided video URL." per the
    INITIAL.md error-handling contract.
    """


class TranscriptionFailedError(TranscriptionError):
    """Raised when the video was accessible but the Whisper call itself failed."""


def _assert_public_http_url(url: str) -> None:
    """Reject any URL that isn't a plain http(s) request to a public host.

    Blocks SSRF: internal services, loopback, link-local (incl. cloud
    metadata endpoints like 169.254.169.254), and other reserved/private
    IP ranges are all rejected, whether given directly as a hostname or
    reached after DNS resolution. yt-dlp follows redirects and makes its
    own further requests (e.g. to a platform's CDN) internally, but this
    guard still stops the user-supplied entry URL itself from targeting an
    internal address before yt-dlp ever touches it.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise VideoUnreachableError(f"Unsupported URL scheme for source video: {url}")
    if not parsed.hostname:
        raise VideoUnreachableError(f"Source video URL has no host: {url}")

    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except OSError as exc:
        raise VideoUnreachableError(f"Unable to resolve host for source video: {url}") from exc

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise VideoUnreachableError(
                f"Source video URL resolves to a disallowed address: {url}"
            )


def download_source_video(source_url: str) -> tuple[str, dict]:
    """Download a URL-submitted source video via yt-dlp to a persistent local file.

    Supports YouTube and hundreds of other platforms yt-dlp recognizes, and
    falls back to a plain direct-file download for a bare video URL via
    yt-dlp's own generic extractor - callers no longer need a separate
    "is this a known platform?" branch.

    The file is written under DOWNLOAD_DIR and is NOT deleted afterward:
    unlike a transcription-only temp file, the render stage later in the
    same pipeline run needs local access to the same video, so the caller
    is expected to persist the returned path onto VideoJob.file_path (it
    is then cleaned up exactly like an uploaded file, on VideoJob delete).

    Returns (local_file_path, metadata) where metadata has "title" and
    "duration" (seconds) whenever yt-dlp could determine them (None
    otherwise) - the caller may use these to enrich VideoJob fields that
    would otherwise just default to the raw source_url.

    Raises VideoUnreachableError on any validation/network/extraction failure.
    """
    _assert_public_http_url(source_url)

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    outtmpl = str(DOWNLOAD_DIR / f"{uuid.uuid4().hex}.%(ext)s")

    ydl_opts = {
        # yt-dlp's own recommended default: best video-only + best audio-only
        # streams merged via ffmpeg, falling back to a single progressive
        # stream. Most modern YouTube videos have no combined "best" format
        # at all (only separate DASH video/audio), so constraining to a
        # single-stream `best[filesize<X]` (as an earlier version of this
        # did) fails outright with "Requested format is not available" for
        # those - `max_filesize` below is the correct way to bound size
        # without breaking format selection.
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 30,
        "retries": 2,
        "max_filesize": MAX_DOWNLOAD_BYTES,
    }
    youtube_extractor_args: dict[str, Any] = {}
    if settings.YTDLP_COOKIES_FILE and os.path.exists(settings.YTDLP_COOKIES_FILE):
        # A logged-in session already gets past YouTube's bot check on its
        # own - the android/tv override below is for the no-cookies case
        # only, since those clients don't carry an authenticated session
        # and yt-dlp errors ("The page needs to be reloaded") when both
        # are set together.
        ydl_opts["cookiefile"] = settings.YTDLP_COOKIES_FILE
    else:
        # YouTube's "confirm you're not a bot" check targets the web
        # client and disproportionately triggers on datacenter/VPS IPs;
        # the android/tv clients use a different (non-web) API path that
        # isn't subject to it, so trying those first avoids requiring
        # user-supplied cookies for the common case.
        youtube_extractor_args["player_client"] = ["android", "tv"]

    extractor_args: dict[str, Any] = {}
    if youtube_extractor_args:
        extractor_args["youtube"] = youtube_extractor_args
    if settings.YTDLP_POT_PROVIDER_URL:
        # Even cookie-authenticated web-client requests now need a PO
        # (Proof of Origin) token from a running bgutil-ytdlp-pot-provider
        # instance - without it, extraction fails with a generic
        # "The page needs to be reloaded" error regardless of cookies.
        extractor_args["youtubepot-bgutilhttp"] = {"base_url": [settings.YTDLP_POT_PROVIDER_URL]}
    if extractor_args:
        ydl_opts["extractor_args"] = extractor_args

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(source_url, download=True)
            # After a bv*+ba merge, the final container's actual path/ext
            # (e.g. forced to .mp4 via merge_output_format) is only
            # reliably reflected in `requested_downloads` - prepare_filename
            # alone can still report the pre-merge extension.
            requested = info.get("requested_downloads") or []
            if requested and requested[0].get("filepath"):
                local_path = requested[0]["filepath"]
            else:
                local_path = ydl.prepare_filename(info)
    except yt_dlp.utils.DownloadError as exc:
        raise VideoUnreachableError(
            f"Unable to download source video from URL: {source_url}"
        ) from exc

    if not local_path or not os.path.exists(local_path):
        raise VideoUnreachableError(
            f"Download reported success but no file was produced for: {source_url}"
        )

    metadata = {"title": info.get("title"), "duration": info.get("duration")}
    return local_path, metadata


def _extract_audio_segment(
    source_path: str, start: float | None = None, duration: float | None = None
) -> str:
    """Extract a small, compressed mono audio track from `source_path`.

    With no `start`/`duration`, extracts the whole track. With both given,
    extracts just that window (used to split a long source into
    Whisper-sized chunks). Returns a temp file path the caller must delete.
    """
    fd, audio_path = tempfile.mkstemp(suffix=".m4a")
    os.close(fd)
    input_kwargs: dict[str, Any] = {}
    if start is not None:
        input_kwargs["ss"] = start
    output_kwargs: dict[str, Any] = {
        "vn": None,
        "acodec": "aac",
        "audio_bitrate": WHISPER_AUDIO_BITRATE,
        "ac": 1,
    }
    if duration is not None:
        output_kwargs["t"] = duration
    try:
        (
            ffmpeg.input(source_path, **input_kwargs)
            .output(audio_path, **output_kwargs)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True, quiet=True)
        )
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else str(exc)
        try:
            os.remove(audio_path)
        except OSError:
            pass
        raise TranscriptionFailedError(
            f"Failed to extract audio for transcription: {stderr}"
        ) from exc
    return audio_path


def _probe_duration_seconds(path: str) -> float:
    """Return a media file's duration via ffprobe."""
    try:
        probe = ffmpeg.probe(path)
        return float(probe["format"]["duration"])
    except (ffmpeg.Error, KeyError, ValueError, TypeError) as exc:
        raise TranscriptionFailedError(f"Failed to determine video duration: {exc}") from exc


def _field(segment: Any, name: str, default: Any = None) -> Any:
    """Read a field from either a dict segment or an SDK object segment."""
    if isinstance(segment, dict):
        return segment.get(name, default)
    return getattr(segment, name, default)


def _call_whisper(path: str, openai_client: Any) -> dict:
    """Send one local audio/video file to Whisper and normalize the response.

    Returns {"segments": [...], "text": str, "duration": float | None} with
    segment timestamps relative to the start of `path` itself - the caller
    is responsible for offsetting them when `path` is one chunk of a longer
    source.
    """
    try:
        with open(path, "rb") as media_file:
            response = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=media_file,
                response_format="verbose_json",
                # Override the client's shared 120s default for this call
                # specifically: transcribing even one chunk of a long
                # video can legitimately take well over 120s, whereas the
                # client's other callers (fast chat-completion calls for
                # scoring/B-roll) should still fail fast.
                timeout=WHISPER_TIMEOUT_SECONDS,
            )
    except OSError as exc:
        raise VideoUnreachableError(f"Unable to open video file at {path}") from exc
    except Exception as exc:
        logger.exception("Whisper transcription call failed for %s", path)
        raise TranscriptionFailedError(str(exc)) from exc

    segments = [
        {
            "start": float(_field(segment, "start", 0.0)),
            "end": float(_field(segment, "end", 0.0)),
            "text": str(_field(segment, "text", "")).strip(),
        }
        for segment in getattr(response, "segments", None) or []
    ]
    full_text = getattr(response, "text", "") or " ".join(s["text"] for s in segments)
    duration = getattr(response, "duration", None)
    return {"segments": segments, "text": full_text, "duration": duration}


def transcribe_video(file_path: str, openai_client: Any) -> dict:
    """Transcribe a local video/audio file into a timestamped transcript.

    Args:
        file_path: A local filesystem path - either an uploaded file, or
            the path returned by `download_source_video` for a URL submission.
        openai_client: An injected OpenAI client exposing
            `.audio.transcriptions.create(...)` (e.g. `openai.OpenAI()`),
            so tests can pass a mock/stub instead.

    Returns:
        {
            "segments": [{"start": float, "end": float, "text": str}, ...],
            "text": str,        # full transcript text
            "duration": float | None,
        }

    Raises:
        VideoUnreachableError: the file could not be opened.
        TranscriptionFailedError: the file was accessible but Whisper failed.
    """
    if not file_path or not os.path.exists(file_path):
        raise VideoUnreachableError(f"Video file not found at path: {file_path}")

    # Fast path: small enough to send as-is (covers most short/medium
    # videos - no audio extraction or probing needed at all).
    if os.path.getsize(file_path) <= WHISPER_MAX_BYTES:
        return _call_whisper(file_path, openai_client)

    total_duration = _probe_duration_seconds(file_path)
    estimated_audio_bytes = (total_duration * WHISPER_AUDIO_BITRATE_BPS) / 8

    if estimated_audio_bytes <= WHISPER_MAX_BYTES:
        # A single compressed-audio track comfortably fits Whisper's cap.
        extracted_path = _extract_audio_segment(file_path)
        try:
            return _call_whisper(extracted_path, openai_client)
        finally:
            try:
                os.remove(extracted_path)
            except OSError:
                logger.warning("Failed to clean up extracted audio %s", extracted_path)

    # Long source (e.g. a 2-3 hour course video): even compressed audio
    # would exceed Whisper's 25MB cap on its own, so split it into
    # sequential chunks short enough to each fit, transcribe each
    # separately, and merge the results with timestamps offset by every
    # chunk's start time so they stay correct against the original video.
    chunk_seconds = (WHISPER_CHUNK_TARGET_BYTES * 8) / WHISPER_AUDIO_BITRATE_BPS
    num_chunks = max(1, math.ceil(total_duration / chunk_seconds))
    logger.info(
        "Transcribing %s in %d chunk(s) (~%.0fs each) - %.0fs total",
        file_path,
        num_chunks,
        chunk_seconds,
        total_duration,
    )

    all_segments: list[dict] = []
    text_parts: list[str] = []
    chunk_paths: list[str] = []
    try:
        for i in range(num_chunks):
            start = i * chunk_seconds
            this_duration = min(chunk_seconds, total_duration - start)
            if this_duration <= 0:
                break
            chunk_path = _extract_audio_segment(file_path, start=start, duration=this_duration)
            chunk_paths.append(chunk_path)
            result = _call_whisper(chunk_path, openai_client)
            for segment in result["segments"]:
                all_segments.append(
                    {
                        "start": segment["start"] + start,
                        "end": segment["end"] + start,
                        "text": segment["text"],
                    }
                )
            if result["text"]:
                text_parts.append(result["text"])
    finally:
        for chunk_path in chunk_paths:
            try:
                os.remove(chunk_path)
            except OSError:
                logger.warning("Failed to clean up audio chunk %s", chunk_path)

    return {"segments": all_segments, "text": " ".join(text_parts), "duration": total_duration}
