"""B-roll suggestion & stock footage sourcing service.

`generate_broll_suggestions` uses gpt-4o-mini to identify statements within
a short clip that can be visually illustrated (preferring mid-clip
placement) and produces search keywords. `fetch_stock_asset` then queries
Pexels for a matching asset - this is always best-effort: a Pexels miss or
API failure must never raise, since B-roll is a nice-to-have overlay, not
a pipeline-critical step.
"""
import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_VALID_VISUAL_TYPES = {
    "stock_footage",
    "image",
    "screenshot",
    "screen_recording",
    "chart",
    "animation",
}

PEXELS_VIDEO_SEARCH_URL = "https://api.pexels.com/videos/search"
PEXELS_PHOTO_SEARCH_URL = "https://api.pexels.com/v1/search"


class BRollGenerationError(Exception):
    """Raised when keyword generation fails unrecoverably (rare - caller may
    choose to swallow this too, since B-roll is best-effort overall)."""


def generate_broll_suggestions(short: dict, openai_client: Any, model: str) -> list[dict]:
    """Generate B-roll placement suggestions for a single short clip.

    Args:
        short: dict with at least "title", "transcript_excerpt",
            "duration_seconds" (all timestamps returned are relative to the
            SHORT's own 0..duration_seconds timeline, not the source video).
        openai_client: injected OpenAI client.
        model: model name (settings.OPENAI_MODEL).

    Returns:
        A list of dicts: {"start_time", "end_time", "visual_type",
        "search_keywords", "description"}. Prefers placements clustered
        around the middle of the clip.

    Raises:
        BRollGenerationError: on an unusable/malformed model response.
    """
    duration = short.get("duration_seconds", 30)

    system_prompt = (
        "You are a B-roll director for short-form video. Given a short "
        "clip's transcript excerpt and duration, identify 1-3 moments that "
        "can be visually illustrated with supporting B-roll (stock footage, "
        "an image, a screenshot, a screen recording, a chart, or a simple "
        "animation). Prefer placements near the MIDDLE of the clip rather "
        "than the very start or end, so the hook and payoff stay "
        "unobstructed. For each, provide a short search_keywords string "
        "suitable for a stock footage search API, and a one-sentence "
        "description of what should appear and why it supports the "
        "narration. Base suggestions only on what is actually said in the "
        "excerpt - never invent unrelated visuals. "
        'Return JSON of the form: {"suggestions": [{"start_time": number, '
        '"end_time": number, "visual_type": "stock_footage"|"image"|'
        '"screenshot"|"screen_recording"|"chart"|"animation", '
        '"search_keywords": string, "description": string}]}. All '
        f"start_time/end_time values must fall within 0 and {duration:.1f} "
        "(the clip's own duration in seconds)."
    )
    user_prompt = (
        f"TITLE: {short.get('title', '')}\n"
        f"DURATION_SECONDS: {duration:.1f}\n"
        f"TRANSCRIPT EXCERPT:\n{short.get('transcript_excerpt', '')}"
    )

    try:
        response = openai_client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=1000,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        raw_content = response.choices[0].message.content
        parsed = json.loads(raw_content)
    except Exception as exc:
        logger.exception("generate_broll_suggestions: OpenAI call failed")
        raise BRollGenerationError(str(exc)) from exc

    raw_suggestions = parsed.get("suggestions", [])
    if not isinstance(raw_suggestions, list):
        raise BRollGenerationError("Model response 'suggestions' field is not a list")

    suggestions: list[dict] = []
    mid_point = duration / 2

    for item in raw_suggestions:
        try:
            start_time = max(0.0, min(float(item["start_time"]), duration))
            end_time = max(start_time, min(float(item["end_time"]), duration))
            visual_type = item.get("visual_type", "stock_footage")
            if visual_type not in _VALID_VISUAL_TYPES:
                visual_type = "stock_footage"
            suggestions.append(
                {
                    "start_time": start_time,
                    "end_time": end_time,
                    "visual_type": visual_type,
                    "search_keywords": str(item.get("search_keywords", "")).strip(),
                    "description": str(item.get("description", "")).strip(),
                }
            )
        except (KeyError, TypeError, ValueError):
            logger.warning("Skipping malformed B-roll suggestion: %r", item)
            continue

    # Prefer mid-clip placements when sorting/returning.
    suggestions.sort(key=lambda s: abs(((s["start_time"] + s["end_time"]) / 2) - mid_point))
    return suggestions


def fetch_stock_asset(keywords: str, pexels_api_key: str) -> str | None:
    """Fetch the first matching stock video/photo URL from Pexels.

    Best-effort only: returns None (never raises) if the API key is
    missing, the request fails, or nothing matches, since B-roll asset
    fetching should never fail the overall rendering pipeline.
    """
    if not keywords or not pexels_api_key:
        return None

    headers = {"Authorization": pexels_api_key}

    try:
        with httpx.Client(timeout=10.0) as client:
            video_response = client.get(
                PEXELS_VIDEO_SEARCH_URL,
                headers=headers,
                params={"query": keywords, "per_page": 1, "orientation": "portrait"},
            )
            video_response.raise_for_status()
            video_data = video_response.json()
            videos = video_data.get("videos") or []
            if videos:
                video_files = videos[0].get("video_files") or []
                if video_files:
                    return video_files[0].get("link")

            # Fall back to a photo if no video matched.
            photo_response = client.get(
                PEXELS_PHOTO_SEARCH_URL,
                headers=headers,
                params={"query": keywords, "per_page": 1},
            )
            photo_response.raise_for_status()
            photo_data = photo_response.json()
            photos = photo_data.get("photos") or []
            if photos:
                return photos[0].get("src", {}).get("original")

    except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
        logger.warning("Pexels lookup failed for keywords=%r: %s", keywords, exc)
        return None

    return None
