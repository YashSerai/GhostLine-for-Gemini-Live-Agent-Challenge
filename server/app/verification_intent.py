"""Deterministic voice intent parsing for Ready-to-Verify requests."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

_MAX_SNIPPET_LENGTH: Final[int] = 160
_WHITESPACE_RE: Final[re.Pattern[str]] = re.compile(r"\s+")
_NON_WORD_RE: Final[re.Pattern[str]] = re.compile(r"[^a-z0-9\s]")
_READY_TO_VERIFY_ALIASES: Final[tuple[str, ...]] = (
    "ready to verify",
    "verify now",
    "can you verify",
    "can you check it",
    "check it now",
    "take a look now",
    "ready for you to check",
)


@dataclass(frozen=True)
class ReadyToVerifyVoiceIntent:
    matched_phrase: str
    raw_transcript_snippet: str


def parse_ready_to_verify_voice_intent(
    transcript_text: str,
) -> ReadyToVerifyVoiceIntent | None:
    snippet = _build_snippet(transcript_text)
    if snippet is None:
        return None

    normalized_text = _normalize_transcript_text(snippet)
    for alias in _READY_TO_VERIFY_ALIASES:
        if alias in normalized_text:
            return ReadyToVerifyVoiceIntent(
                matched_phrase=alias,
                raw_transcript_snippet=snippet,
            )

    return None


def _build_snippet(transcript_text: str) -> str | None:
    stripped_text = transcript_text.strip()
    if not stripped_text:
        return None

    if len(stripped_text) <= _MAX_SNIPPET_LENGTH:
        return stripped_text

    return f"{stripped_text[:_MAX_SNIPPET_LENGTH].rstrip()}..."


def _normalize_transcript_text(transcript_text: str) -> str:
    normalized_text = transcript_text.lower().replace("\u2019", "'").replace("'", "")
    normalized_text = _NON_WORD_RE.sub(" ", normalized_text)
    return _WHITESPACE_RE.sub(" ", normalized_text).strip()


__all__ = [
    "ReadyToVerifyVoiceIntent",
    "parse_ready_to_verify_voice_intent",
]
