"""Deterministic voice-intent parsing for swap-related transcript snippets."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Literal, TypeAlias

DetectedIntent: TypeAlias = Literal["task_inability", "swap_request"]
InferredReason: TypeAlias = Literal[
    "cannot_perform_task",
    "missing_paper",
    "missing_door_or_threshold",
    "missing_required_object",
    "alternative_requested",
]

_MAX_SNIPPET_LENGTH: Final[int] = 160
_WHITESPACE_RE: Final[re.Pattern[str]] = re.compile(r"\s+")
_NON_WORD_RE: Final[re.Pattern[str]] = re.compile(r"[^a-z0-9\s]")


@dataclass(frozen=True)
class VoiceSwapRequest:
    """Structured backend output for swap-related voice intent."""

    detected_intent: DetectedIntent
    inferred_reason: InferredReason
    matched_phrase: str
    raw_transcript_snippet: str


@dataclass(frozen=True)
class _VoiceIntentRule:
    detected_intent: DetectedIntent
    inferred_reason: InferredReason
    matched_phrase: str
    aliases: tuple[str, ...]


_VOICE_INTENT_RULES: Final[tuple[_VoiceIntentRule, ...]] = (
    _VoiceIntentRule(
        detected_intent="task_inability",
        inferred_reason="missing_paper",
        matched_phrase="no paper",
        aliases=(
            "no paper",
            "dont have paper",
            "do not have paper",
            "no paper here",
        ),
    ),
    _VoiceIntentRule(
        detected_intent="task_inability",
        inferred_reason="missing_door_or_threshold",
        matched_phrase="no door here",
        aliases=(
            "no door here",
            "there is no door here",
            "theres no door here",
            "no threshold here",
        ),
    ),
    _VoiceIntentRule(
        detected_intent="task_inability",
        inferred_reason="missing_required_object",
        matched_phrase="i dont have that",
        aliases=(
            "i dont have that",
            "i do not have that",
            "dont have that",
            "do not have that",
        ),
    ),
    _VoiceIntentRule(
        detected_intent="task_inability",
        inferred_reason="cannot_perform_task",
        matched_phrase="i cant do that",
        aliases=(
            "i cant do that",
            "i cannot do that",
            "cant do that",
            "cannot do that",
            "i cant do this",
            "i cannot do this",
        ),
    ),
    _VoiceIntentRule(
        detected_intent="swap_request",
        inferred_reason="alternative_requested",
        matched_phrase="another option",
        aliases=(
            "another option",
            "give me something else",
            "give me another option",
        ),
    ),
)


def parse_swap_voice_intent(transcript_text: str) -> VoiceSwapRequest | None:
    """Parse a user transcript snippet into a structured swap request."""

    snippet = _build_snippet(transcript_text)
    if snippet is None:
        return None

    normalized_text = _normalize_transcript_text(snippet)
    for rule in _VOICE_INTENT_RULES:
        for alias in rule.aliases:
            if alias in normalized_text:
                return VoiceSwapRequest(
                    detected_intent=rule.detected_intent,
                    inferred_reason=rule.inferred_reason,
                    matched_phrase=rule.matched_phrase,
                    raw_transcript_snippet=snippet,
                )

    return None


def build_swap_request_payload(swap_request: VoiceSwapRequest) -> dict[str, str]:
    """Return a serializable payload for downstream swap handling."""

    return {
        "detectedIntent": swap_request.detected_intent,
        "inferredReason": swap_request.inferred_reason,
        "rawTranscriptSnippet": swap_request.raw_transcript_snippet,
    }


def _build_snippet(transcript_text: str) -> str | None:
    stripped_text = transcript_text.strip()
    if not stripped_text:
        return None

    if len(stripped_text) <= _MAX_SNIPPET_LENGTH:
        return stripped_text

    return f"{stripped_text[:_MAX_SNIPPET_LENGTH].rstrip()}..."


def _normalize_transcript_text(transcript_text: str) -> str:
    normalized_text = transcript_text.lower().replace("’", "'").replace("'", "")
    normalized_text = _NON_WORD_RE.sub(" ", normalized_text)
    return _WHITESPACE_RE.sub(" ", normalized_text).strip()


__all__ = [
    "DetectedIntent",
    "InferredReason",
    "VoiceSwapRequest",
    "build_swap_request_payload",
    "parse_swap_voice_intent",
]
