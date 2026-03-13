"""Deterministic demo-only barge-in script for Prompt 45."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Final

from .demo_dialogue import DEMO_DIAGNOSIS_INTERPRETATION_LINE


@dataclass(frozen=True)
class DemoBargeInScript:
    target_line: str
    trigger_phrase: str
    restatement_line: str


DEMO_BARGE_IN_SCRIPT: Final[DemoBargeInScript] = DemoBargeInScript(
    target_line=DEMO_DIAGNOSIS_INTERPRETATION_LINE,
    trigger_phrase="Archivist, wait. Say that again.",
    restatement_line="Threshold activity. Keep the room controlled. Continue with the next step.",
)


def matches_demo_barge_in_trigger(text: str) -> bool:
    """Return True when a final user transcript matches the rehearsed demo cue."""

    normalized_text = _normalize_phrase(text)
    normalized_trigger = _normalize_phrase(DEMO_BARGE_IN_SCRIPT.trigger_phrase)
    if not normalized_text or not normalized_trigger:
        return False
    return normalized_trigger in normalized_text


def _normalize_phrase(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return " ".join(cleaned.split())


__all__ = ["DEMO_BARGE_IN_SCRIPT", "DemoBargeInScript", "matches_demo_barge_in_trigger"]
