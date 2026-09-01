"""AI moment analysis & clip scoring service.

Implements PRP Module 3 STEP 2-6:
  STEP 2: scan the FULL transcript and identify candidate 30-60s moments
          with clean sentence boundaries (identify_candidate_moments).
  STEP 3-5: score every candidate across 9 engagement dimensions
          (score_candidate).
  STEP 6: select 5-10 distinct, standalone shorts, preferring different
          time-ranges/topics (select_top_shorts).

All functions take an injected `openai_client` (never a module-level
global) so they are unit-testable with a mock client. `gpt-4o-mini` is
instructed, in every prompt, to never invent content that is not present
in the supplied transcript - see CLAUDE.md / INITIAL.md "Special
Requirements -> AI Model".
"""
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

MIN_CLIP_SECONDS = 30
MAX_CLIP_SECONDS = 60
MIN_SHORTS = 1
MAX_SHORTS = 10

# Weighted average is NOT used - overall_score is the simple arithmetic mean
# of all nine 1-10 dimensions (documented per TASKS.md item 3).
_SCORE_FIELDS = (
    "hook_strength",
    "standalone_value",
    "engagement",
    "retention",
    "payoff",
    "clarity",
    "shareability",
    "viral_potential",
    "b_roll_quality",
)

_VALID_CATEGORIES = {"viral", "educational", "emotional", "surprising", "story", "other"}


class MomentAnalysisError(Exception):
    """Raised when candidate identification or scoring fails unrecoverably."""


def _transcript_to_text(transcript: list[dict]) -> str:
    """Render timestamped transcript segments as a compact numbered listing.

    Keeping start/end timestamps inline lets the model return time ranges
    that map directly back onto the source transcript, instead of
    hallucinating its own timing.
    """
    lines = [
        f"[{seg.get('start', 0):.2f}-{seg.get('end', 0):.2f}] {seg.get('text', '').strip()}"
        for seg in transcript
    ]
    return "\n".join(lines)


def _expand_short_candidate(candidate: dict, transcript: list[dict]) -> dict:
    """Widen a too-short candidate using adjacent transcript segments.

    Defensive backstop for when the model doesn't respect the 30-60s
    requirement despite being explicitly instructed (observed in practice:
    gpt-4o-mini sometimes returns a 2-5s window around one striking
    sentence instead of a full clip-length span). Extends the window
    forward first (include what follows the highlighted moment), then
    backward if still short, using only real transcript segment
    boundaries - never fabricates timing or text. Capped so the result
    never exceeds MAX_CLIP_SECONDS.

    A no-op if the candidate is already >= MIN_CLIP_SECONDS.
    """
    start_time = candidate["start_time"]
    end_time = candidate["end_time"]
    if end_time - start_time >= MIN_CLIP_SECONDS or not transcript:
        return candidate

    ordered = sorted(transcript, key=lambda s: s.get("start", 0))

    for seg in ordered:
        if end_time - start_time >= MIN_CLIP_SECONDS:
            break
        seg_start, seg_end = seg.get("start", 0), seg.get("end", 0)
        if seg_start >= end_time and seg_end > end_time:
            end_time = min(seg_end, start_time + MAX_CLIP_SECONDS)

    for seg in reversed(ordered):
        if end_time - start_time >= MIN_CLIP_SECONDS:
            break
        seg_start, seg_end = seg.get("start", 0), seg.get("end", 0)
        if seg_end <= start_time and seg_start < start_time:
            start_time = max(seg_start, end_time - MAX_CLIP_SECONDS)

    if start_time == candidate["start_time"] and end_time == candidate["end_time"]:
        return candidate  # no eligible neighboring segments found - leave as-is

    excerpt = " ".join(
        seg.get("text", "").strip()
        for seg in ordered
        if seg.get("start", 0) < end_time and seg.get("end", 0) > start_time and seg.get("text")
    ).strip()

    return {
        **candidate,
        "start_time": start_time,
        "end_time": end_time,
        "duration_seconds": end_time - start_time,
        "transcript_excerpt": excerpt or candidate["transcript_excerpt"],
    }


def _extract_json_object(raw_content: str) -> dict:
    try:
        return json.loads(raw_content)
    except (TypeError, ValueError) as exc:
        raise MomentAnalysisError(f"Model did not return valid JSON: {exc}") from exc


def identify_candidate_moments(
    transcript: list[dict],
    openai_client: Any,
    model: str,
) -> list[dict]:
    """Scan the full transcript and propose candidate 30-60s short-form moments.

    Args:
        transcript: list of {"start": float, "end": float, "text": str} segments,
            covering the ENTIRE source video (not just the opening).
        openai_client: injected OpenAI client exposing
            `.chat.completions.create(...)`.
        model: model name to use (e.g. settings.OPENAI_MODEL == "gpt-4o-mini").

    Returns:
        A list of candidate dicts:
            {
                "start_time": float, "end_time": float,
                "duration_seconds": float,
                "title": str, "transcript_excerpt": str,
                "category": str,  # one of ShortClipCategory values
            }

    Raises:
        MomentAnalysisError: on an unusable/malformed model response.
    """
    if not transcript:
        return []

    transcript_text = _transcript_to_text(transcript)

    system_prompt = (
        "You are a short-form video producer. You are given a FULL timestamped "
        "transcript of a long-form video, formatted as one line per segment: "
        "[start-end] text. Scan the ENTIRE transcript - beginning, middle, and "
        "end - and identify candidate moments that could become standalone "
        "short-form clips for YouTube Shorts/Reels.\n\n"
        "HARD REQUIREMENT ON LENGTH: end_time minus start_time MUST be between "
        "30 and 60 seconds. This is not optional and not a suggestion - a 3-5 "
        "second soundbite around one striking sentence is NOT a valid "
        "candidate on its own. If the single most compelling sentence/quote "
        "is short, you MUST widen the window to include the setup before it "
        "and/or the follow-through after it (using the surrounding transcript "
        "segments) so the total span reaches at least 30 seconds, while "
        "keeping it one complete, coherent, standalone idea - not just "
        "padding with unrelated content.\n"
        "Example of correct sizing: if the striking line is at [120.5-124.0] "
        "(only 3.5s), a valid candidate widens that to roughly [98.0-140.0] "
        "(42s) by including the buildup before and the payoff after, NOT "
        "just [120.5-124.0] on its own.\n\n"
        "Each candidate MUST: (1) start and end on clean sentence boundaries "
        "present in the transcript, never mid-sentence; (2) contain a complete "
        "idea with a clear beginning, middle, and payoff; (3) have "
        "end_time - start_time between 30 and 60 seconds (see HARD "
        "REQUIREMENT above); (4) use start_time/end_time values taken "
        "directly from the transcript timestamps. "
        "CRITICAL: never invent, paraphrase beyond minor cleanup, or "
        "fabricate any text, fact, or quote that is not present in the "
        "transcript. transcript_excerpt must be composed of the actual "
        "transcript text for that time range, and must include the full "
        "widened span, not just the single striking sentence. "
        "Return JSON of the form: "
        '{"candidates": [{"start_time": number, "end_time": number, '
        '"title": string, "transcript_excerpt": string, '
        '"category": "viral"|"educational"|"emotional"|"surprising"|"story"|"other"}]}'
    )
    user_prompt = f"TRANSCRIPT:\n{transcript_text}"

    try:
        response = openai_client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=4000,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        raw_content = response.choices[0].message.content
    except Exception as exc:
        logger.exception("identify_candidate_moments: OpenAI call failed")
        raise MomentAnalysisError(str(exc)) from exc

    parsed = _extract_json_object(raw_content)
    raw_candidates = parsed.get("candidates", [])
    if not isinstance(raw_candidates, list):
        raise MomentAnalysisError("Model response 'candidates' field is not a list")
    if not raw_candidates:
        logger.warning("identify_candidate_moments: model returned zero candidates")

    candidates: list[dict] = []
    for item in raw_candidates:
        try:
            start_time = float(item["start_time"])
            end_time = float(item["end_time"])
            duration = end_time - start_time
            if duration <= 0:
                continue
            category = item.get("category", "other")
            if category not in _VALID_CATEGORIES:
                category = "other"
            candidates.append(
                {
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration_seconds": duration,
                    "title": str(item.get("title", "")).strip() or "Untitled moment",
                    "transcript_excerpt": str(item.get("transcript_excerpt", "")).strip(),
                    "category": category,
                }
            )
        except (KeyError, TypeError, ValueError):
            logger.warning("Skipping malformed candidate from model response: %r", item)
            continue

    # Widen any too-short candidate using real neighboring transcript
    # segments before the final range check - see _expand_short_candidate.
    candidates = [_expand_short_candidate(c, transcript) for c in candidates]

    # Enforce the 30-60s clean-boundary requirement defensively - even
    # though the prompt asks for it, never trust the model blindly.
    in_range = [
        c for c in candidates if MIN_CLIP_SECONDS <= c["duration_seconds"] <= MAX_CLIP_SECONDS
    ]
    if candidates and not in_range:
        # Every parsed candidate existed but none landed in [30, 60]s - log
        # the actual durations returned so an all-zero result is
        # diagnosable (e.g. the model returning broader topic segments)
        # rather than a silent "found 0 usable segments".
        logger.warning(
            "identify_candidate_moments: model returned %d candidate(s) but none had a "
            "duration in [%d, %d]s - durations were: %s",
            len(candidates),
            MIN_CLIP_SECONDS,
            MAX_CLIP_SECONDS,
            [round(c["duration_seconds"], 1) for c in candidates],
        )
    return in_range


def score_candidate(candidate: dict, openai_client: Any, model: str) -> dict:
    """Score a single candidate moment across 9 engagement dimensions (1-10 each).

    overall_score is the simple arithmetic mean of the 9 dimensions
    (documented choice - not a weighted average).

    Returns the candidate dict merged with the 9 score fields and
    "overall_score" (float).

    Raises:
        MomentAnalysisError: on an unusable/malformed model response.
    """
    system_prompt = (
        "You are a short-form video content strategist. Score the given clip "
        "candidate (with its transcript excerpt) on each of the following "
        "dimensions, as an integer from 1 (weak) to 10 (excellent): "
        "hook_strength (does it grab attention in the first 1-2 seconds), "
        "standalone_value (does it make sense without the rest of the video), "
        "engagement, retention (would viewers watch to the end), "
        "payoff (satisfying conclusion), clarity, shareability, "
        "viral_potential, and b_roll_quality (how well the content lends "
        "itself to illustrative supporting visuals). "
        "Base every score ONLY on the transcript excerpt provided - do not "
        "assume or invent content beyond it. "
        'Return JSON of the form: {"hook_strength": int, "standalone_value": int, '
        '"engagement": int, "retention": int, "payoff": int, "clarity": int, '
        '"shareability": int, "viral_potential": int, "b_roll_quality": int}'
    )
    user_prompt = (
        f"TITLE: {candidate.get('title', '')}\n"
        f"CATEGORY: {candidate.get('category', 'other')}\n"
        f"DURATION_SECONDS: {candidate.get('duration_seconds', 0):.1f}\n"
        f"TRANSCRIPT EXCERPT:\n{candidate.get('transcript_excerpt', '')}"
    )

    try:
        response = openai_client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=500,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        raw_content = response.choices[0].message.content
    except Exception as exc:
        logger.exception("score_candidate: OpenAI call failed")
        raise MomentAnalysisError(str(exc)) from exc

    parsed = _extract_json_object(raw_content)

    scores: dict[str, int] = {}
    for field in _SCORE_FIELDS:
        try:
            value = int(parsed[field])
        except (KeyError, TypeError, ValueError) as exc:
            raise MomentAnalysisError(f"Missing/invalid score field '{field}'") from exc
        scores[field] = max(1, min(10, value))

    overall_score = round(sum(scores.values()) / len(_SCORE_FIELDS), 2)

    return {**candidate, **scores, "overall_score": overall_score}


def _overlaps(a: dict, b: dict, max_overlap_fraction: float = 0.2) -> bool:
    """True if candidates a/b overlap in time by more than `max_overlap_fraction`
    of the shorter clip's duration - used to prefer distinct time-ranges/topics."""
    overlap_start = max(a["start_time"], b["start_time"])
    overlap_end = min(a["end_time"], b["end_time"])
    overlap = max(0.0, overlap_end - overlap_start)
    shortest = min(a["duration_seconds"], b["duration_seconds"])
    if shortest <= 0:
        return False
    return (overlap / shortest) > max_overlap_fraction


def select_top_shorts(scored_candidates: list[dict]) -> list[dict]:
    """Select 5-10 distinct, standalone shorts from scored candidates.

    Sorts by overall_score (descending) and greedily selects candidates
    that don't significantly time-overlap with an already-selected one, so
    the result prefers different time-ranges/topics across the source
    video. Caps the result at MAX_SHORTS (10).

    If fewer than MIN_SHORTS (5) genuinely distinct, valid candidates
    exist, returns whatever was found (which may be 0-4 items) - the
    caller (pipeline) is responsible for deciding this drives a "partial"
    VideoJob status rather than forcing weak/duplicate clips.
    """
    valid = [
        c
        for c in scored_candidates
        if MIN_CLIP_SECONDS <= c.get("duration_seconds", 0) <= MAX_CLIP_SECONDS
    ]
    ranked = sorted(valid, key=lambda c: c.get("overall_score", 0), reverse=True)

    selected: list[dict] = []
    for candidate in ranked:
        if len(selected) >= MAX_SHORTS:
            break
        if any(_overlaps(candidate, chosen) for chosen in selected):
            continue
        selected.append(candidate)

    for rank, short in enumerate(selected, start=1):
        short["rank"] = rank

    return selected
