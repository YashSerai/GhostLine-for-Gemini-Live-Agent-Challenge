from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Literal

CONTAINMENT_PHRASE_TEXT = (
    "This space is held. This line is sealed. Nothing crosses that was not invited."
)
DEMO_SOUND_PROMPT_DELAY_SECONDS = 7.1
DEMO_SOUND_PROMPT_LINE = (
    "Next step: Describe the Sound. What was that sound? Describe it for me exactly. "
    "Do not guess at the cause - tell me how it sounded."
)
DEMO_CONTAINMENT_PROMPT_LINE = (
    "Next step: Speak Containment Phrase. That sound profile confirms it is trapped and fighting the seal. "
    f"One step left. Repeat exactly after me: '{CONTAINMENT_PHRASE_TEXT}' "
    "I will listen for the cadence live."
)

_READY_TO_VERIFY_RE = re.compile(
    r"\b(ready to verify|verify now|can you verify|can you check it|check it now|take a look now|ready for you to check)\b",
    re.IGNORECASE,
)
_WORD_RE = re.compile(r"[a-z0-9']+")
_NUMBER_WORD_RE = re.compile(
    r"\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|\d+)\b",
    re.IGNORECASE,
)
_SOUND_DESCRIPTOR_KEYWORDS = frozenset(
    {
        "shriek",
        "shrieking",
        "scream",
        "screaming",
        "screech",
        "screeching",
        "wail",
        "wailing",
        "piercing",
        "high",
        "pitched",
        "highpitched",
        "sharp",
        "cry",
        "crying",
        "loud",
    }
)
_CONTAINMENT_REQUIRED_WORDS = frozenset(
    {
        "space",
        "held",
        "line",
        "sealed",
        "nothing",
        "crosses",
        "invited",
    }
)


@dataclass(frozen=True)
class SelfReportResolution:
    action: Literal["confirm", "reprompt", "ignore"]
    confidence_band: str | None = None
    last_verified_item: str | None = None
    notes: str | None = None
    operator_line: str | None = None
    reason: str | None = None


def is_self_report_task_context(task_context: dict[str, Any] | None) -> bool:
    if not isinstance(task_context, dict):
        return False
    return task_context.get("verificationClass") == "self_report"


def build_self_report_completion_signal(task_context: dict[str, Any] | None) -> str:
    task_id = _task_id(task_context)
    if task_id == "T14":
        return "After the sound cue ends, describe it out loud. I will judge that answer live - no Ready to Verify needed."
    if task_id == "T7":
        return (
            f"Repeat this phrase out loud when ready: '{CONTAINMENT_PHRASE_TEXT}' "
            "I will listen for it live - no Ready to Verify needed."
        )
    if task_id == "T13":
        return "Count backward out loud. I will listen for it live - no Ready to Verify needed."
    if task_id == "T15":
        return "Answer out loud with where it felt strongest. I will listen for it live - no Ready to Verify needed."
    return "Answer out loud when ready. I will listen for it live - no Ready to Verify needed."


def build_self_report_verify_reminder(task_context: dict[str, Any] | None) -> str:
    task_id = _task_id(task_context)
    if task_id == "T14":
        return "Not this step. Just tell me what the sound was like once the cue finishes."
    if task_id == "T7":
        return (
            "Not this step. I need the phrase itself, out loud. "
            f"Repeat exactly after me: '{CONTAINMENT_PHRASE_TEXT}'"
        )
    if task_id == "T13":
        return "Not this step. Count backward out loud for me so I can hear it happen live."
    return "Not this step. Answer out loud and I will handle the confirmation live."


def resolve_self_report_response(
    task_context: dict[str, Any] | None,
    transcript_text: str,
) -> SelfReportResolution:
    task_id = _task_id(task_context)
    task_name = _task_name(task_context)
    normalized_text = transcript_text.strip()
    if not normalized_text:
        return SelfReportResolution(action="ignore")

    if _READY_TO_VERIFY_RE.search(normalized_text):
        return SelfReportResolution(action="ignore")

    tokens = _normalized_words(normalized_text)
    if not tokens:
        return SelfReportResolution(action="ignore")

    if task_id == "T14":
        descriptor_hits = len(_SOUND_DESCRIPTOR_KEYWORDS.intersection(tokens))
        if descriptor_hits >= 1 or (len(tokens) >= 4 and _mentions_sound_shape(tokens)):
            return SelfReportResolution(
                action="confirm",
                confidence_band="medium",
                last_verified_item=task_name,
                notes="The sound-description task was resolved from the live user transcript.",
                reason="The caller described the sound profile live without requiring a camera verification beat.",
            )
        if len(tokens) >= 3:
            return SelfReportResolution(
                action="reprompt",
                operator_line=(
                    "Again. I need the sound itself, not the room. "
                    "Tell me whether it sounded like a scream, a shriek, or some other piercing cry."
                ),
            )
        return SelfReportResolution(action="ignore")

    if task_id == "T7":
        required_hits = len(_CONTAINMENT_REQUIRED_WORDS.intersection(tokens))
        if required_hits >= 6 and len(tokens) >= 8:
            return SelfReportResolution(
                action="confirm",
                confidence_band="medium",
                last_verified_item=task_name,
                notes="The containment phrase was matched from the live user transcript.",
                reason="The caller repeated the containment phrase clearly enough to resolve the seal step live.",
            )
        if len(tokens) >= 3:
            return SelfReportResolution(
                action="reprompt",
                operator_line=(
                    "Not quite. Again, exactly after me: "
                    f"'{CONTAINMENT_PHRASE_TEXT}'"
                ),
            )
        return SelfReportResolution(action="ignore")

    if task_id == "T13":
        if len(_NUMBER_WORD_RE.findall(normalized_text)) >= 3:
            return SelfReportResolution(
                action="confirm",
                confidence_band="medium",
                last_verified_item=task_name,
                notes="The count-backward task was resolved from transcript evidence.",
                reason="The caller counted backward out loud clearly enough to resolve the pacing step.",
            )
        if len(tokens) >= 2:
            return SelfReportResolution(
                action="reprompt",
                operator_line="Count backward out loud for me. I need at least three clear numbers in sequence.",
            )
        return SelfReportResolution(action="ignore")

    if len(tokens) >= 3:
        return SelfReportResolution(
            action="confirm",
            confidence_band="medium",
            last_verified_item=task_name,
            notes="The self-report task was resolved from the live user transcript.",
            reason="The caller gave a substantive live answer for the current self-report step.",
        )

    return SelfReportResolution(action="reprompt", operator_line=build_self_report_verify_reminder(task_context))


def _mentions_sound_shape(tokens: set[str]) -> bool:
    return bool(tokens.intersection({"sound", "noise", "heard", "like", "was", "cry", "piercing"}))


def _normalized_words(text: str) -> set[str]:
    collapsed = text.lower().replace("high-pitched", "highpitched")
    return set(_WORD_RE.findall(collapsed))


def _task_id(task_context: dict[str, Any] | None) -> str | None:
    if not isinstance(task_context, dict):
        return None
    task_id = task_context.get("taskId")
    if isinstance(task_id, str) and task_id.strip():
        return task_id.strip()
    return None


def _task_name(task_context: dict[str, Any] | None) -> str | None:
    if not isinstance(task_context, dict):
        return None
    task_name = task_context.get("taskName")
    if isinstance(task_name, str) and task_name.strip():
        return task_name.strip()
    return None


__all__ = [
    "CONTAINMENT_PHRASE_TEXT",
    "DEMO_CONTAINMENT_PROMPT_LINE",
    "DEMO_SOUND_PROMPT_DELAY_SECONDS",
    "DEMO_SOUND_PROMPT_LINE",
    "SelfReportResolution",
    "build_self_report_completion_signal",
    "build_self_report_verify_reminder",
    "is_self_report_task_context",
    "resolve_self_report_response",
]

