"""Fixed demo-mode dialogue pack - optimized for Gemini Live Agent Challenge."""

from __future__ import annotations

from typing import Any, Final

from .room_scan_copy import ROOM_SCAN_PROMPT

# --------------------------------------------------------------------------- #
# Opener & mic test                                                             #
# --------------------------------------------------------------------------- #

DEMO_OPENER_LINE_GRANTED: Final[str] = (
    "Ghostline, Containment Desk. The Archivist speaking. "
    "Press Grant Microphone Access now."
)

DEMO_OPENER_LINE_PROMPT: Final[str] = (
    "Ghostline, Containment Desk. The Archivist speaking. "
    "Press Grant Microphone Access and accept the popup now."
)

# --------------------------------------------------------------------------- #
# Camera & room scan                                                            #
# --------------------------------------------------------------------------- #

DEMO_CAMERA_REQUEST_LINE: Final[str] = (
    "Good. Press Grant Camera Access and accept the popup now so I can see the room."
)

DEMO_ROOM_SCAN_LINE: Final[str] = ROOM_SCAN_PROMPT

DEMO_ROOM_SCAN_ASSESSMENT_LINE: Final[str] = (
    "Room view received. I have enough to begin. "
    "Readings are elevated. Containment starts now."
)

# --------------------------------------------------------------------------- #
# Task assignment                                                               #
# --------------------------------------------------------------------------- #

DEMO_DIAGNOSIS_QUESTION_LINE: Final[str] = "What did the sound resemble. Briefly."
DEMO_DIAGNOSIS_INTERPRETATION_LINE: Final[str] = (
    "That matches threshold activity. Classic displacement behavior - the disturbance "
    "anchors near transitional spaces. Keep the room controlled and continue."
)

# --------------------------------------------------------------------------- #
# Inter-task flavor text (Archivist lore)                                       #
# --------------------------------------------------------------------------- #

DEMO_FLAVOR_POST_T2: Final[str] = (
    "Boundary is sealed. Good. You felt that? That pressure shift? "
    "The displacement field just compressed. It's contained to this room now. "
    "Nothing in, nothing out. That's what we want."
)

DEMO_FLAVOR_POST_T5: Final[str] = (
    "Anchor is set. Good. That paper is your tripwire now - if it moves "
    "when you're not looking, the displacement field is active in that zone. "
    "We have our reference point. Moving on."
)

DEMO_FLAVOR_POST_T14: Final[str] = (
    "I've logged the sound profile. That pattern is consistent with what "
    "we've catalogued as boundary-phase displacement. It knows it's trapped. "
    "One more step and we seal it."
)

DEMO_FLAVOR_POST_T7: Final[str] = (
    "I felt that. The harmonic just flatlined - the displacement field "
    "collapsed. Your containment phrase held. The seal is active."
)

DEMO_FLAVOR_BY_TASK: Final[dict[str, str]] = {
    "T2": DEMO_FLAVOR_POST_T2,
    "T5": DEMO_FLAVOR_POST_T5,
    "T14": DEMO_FLAVOR_POST_T14,
    "T7": DEMO_FLAVOR_POST_T7,
}

# --------------------------------------------------------------------------- #
# Verification & recovery                                                       #
# --------------------------------------------------------------------------- #

DEMO_RECOVERY_LINE: Final[str] = (
    "I cannot verify that yet. Something is off. Show me the full frame "
    "again - slowly. I need to compare it to what I saw before."
)

DEMO_FINAL_CLOSURE_LINE: Final[str] = (
    "Containment Desk is closing the case now. All boundary checks confirmed. "
    "Spectral readings are within safe parameters. The displacement field has "
    "collapsed. Hold the room quiet tonight - do not disturb the placements. "
    "If anything resurfaces, call this number again. The Archivist is always on duty. "
    "Stay safe."
)


def build_demo_task_assignment_line(task_context: dict[str, Any] | None) -> str | None:
    if not isinstance(task_context, dict):
        return None

    task_name = task_context.get("taskName")
    if not isinstance(task_name, str) or not task_name.strip():
        return None

    operator_description = task_context.get("operatorDescription")
    if not isinstance(operator_description, str) or not operator_description.strip():
        operator_description = "Perform the current containment step once, keep the frame readable, then stop."

    return (
        f"Next step: {task_name.strip()}. {operator_description.strip()} "
        "When the step is complete, stop and say Ready to Verify."
    )


def get_demo_flavor_for_task(task_id: str) -> str | None:
    """Get inter-task flavor text for a completed demo task."""
    return DEMO_FLAVOR_BY_TASK.get(task_id)


__all__ = [
    "DEMO_CAMERA_REQUEST_LINE",
    "DEMO_DIAGNOSIS_INTERPRETATION_LINE",
    "DEMO_DIAGNOSIS_QUESTION_LINE",
    "DEMO_FINAL_CLOSURE_LINE",
    "DEMO_FLAVOR_BY_TASK",
    "DEMO_OPENER_LINE_GRANTED",
    "DEMO_OPENER_LINE_PROMPT",
    "DEMO_RECOVERY_LINE",
    "DEMO_ROOM_SCAN_ASSESSMENT_LINE",
    "DEMO_ROOM_SCAN_LINE",
    "build_demo_task_assignment_line",
    "get_demo_flavor_for_task",
]
