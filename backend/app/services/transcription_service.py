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
MAX_DOWNLOAD_BYTES = 500 * 1024 * 1024  # 500 MB

# OpenAI's Whisper endpoint hard-rejects any request body over 25MB (413).
# A full video file (even a short one) routinely exceeds this, so anything
# above the limit gets a compressed, audio-only track extracted first -
# Whisper only needs the audio anyway. The full video itself is untouched
# and still used later for rendering.
WHISPER_MAX_BYTES = 25 * 1024 * 1024  # 25 MB
# 64kbps mono covers roughly 50+ minutes of audio within that 25MB cap;
# very long source videos beyond that aren't chunked (a known limitation).
WHISPER_AUDIO_BITRATE = "64k"

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
        # YouTube's "confirm you're not a bot" check targets the web
        # client and disproportionately triggers on datacenter/VPS IPs;
        # the android/tv clients use a different (non-web) API path that
        # isn't subject to it, so trying those first avoids requiring
        # user-supplied cookies for the common case.
        "extractor_args": {"youtube": {"player_client": ["android", "tv"]}},
    }
    if settings.YTDLP_COOKIES_FILE and os.path.exists(settings.YTDLP_COOKIES_FILE):
        ydl_opts["cookiefile"] = settings.YTDLP_COOKIES_FILE

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


def _extract_audio_for_whisper(source_path: str) -> str:
    """Extract a small, compressed mono audio track from `source_path`.

    Used when the source file itself exceeds Whisper's 25MB request-size
    limit - Whisper only needs the audio, so this avoids ever having to
    send the (much larger) full video. Returns a temp file path the caller
    is responsible for deleting.
    """
    fd, audio_path = tempfile.mkstemp(suffix=".m4a")
    os.close(fd)
    try:
        (
            ffmpeg.input(source_path)
            .output(audio_path, vn=None, acodec="aac", audio_bitrate=WHISPER_AUDIO_BITRATE, ac=1)
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

    whisper_input_path = file_path
    extracted_audio_path: str | None = None
    if os.path.getsize(file_path) > WHISPER_MAX_BYTES:
        extracted_audio_path = _extract_audio_for_whisper(file_path)
        whisper_input_path = extracted_audio_path

    try:
        try:
            with open(whisper_input_path, "rb") as media_file:
                response = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=media_file,
                    response_format="verbose_json",
                    # Override the client's shared 120s default for this
                    # call specifically: receiving + transcribing a long
                    # video's full audio track can legitimately take well
                    # over 120s (e.g. ~7 min for a 34-min source), whereas
                    # the client's other callers (fast chat-completion
                    # calls for scoring/B-roll) should still fail fast.
                    timeout=WHISPER_TIMEOUT_SECONDS,
                )
        except OSError as exc:
            raise VideoUnreachableError(f"Unable to open video file at {file_path}") from exc
        except Exception as exc:
            logger.exception("Whisper transcription call failed for %s", file_path)
            raise TranscriptionFailedError(str(exc)) from exc
    finally:
        if extracted_audio_path:
            try:
                os.remove(extracted_audio_path)
            except OSError:
                logger.warning("Failed to clean up extracted audio %s", extracted_audio_path)

    def _field(segment: Any, name: str, default: Any = None) -> Any:
        """Read a field from either a dict segment or an SDK object segment."""
        if isinstance(segment, dict):
            return segment.get(name, default)
        return getattr(segment, name, default)

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
