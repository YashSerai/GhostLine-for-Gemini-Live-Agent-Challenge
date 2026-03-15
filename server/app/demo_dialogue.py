"""Fixed demo-mode dialogue pack — optimized for Gemini Live Agent Challenge."""

from __future__ import annotations

from typing import Any, Final

# --------------------------------------------------------------------------- #
# Opener & mic test                                                             #
# --------------------------------------------------------------------------- #

DEMO_OPENER_LINE_GRANTED: Final[str] = (
    "Thank you for calling Ghostline. This is the Containment Desk, the Archivist speaking. "
    "I see your microphone is connected to the session, but I need explicit permission to hear you. "
    "Please press the 'Grant Microphone Access' button on your interface now."
)

DEMO_OPENER_LINE_PROMPT: Final[str] = (
    "Thank you for calling Ghostline. This is the Containment Desk, the Archivist speaking. "
    "I need explicit permission to hear you. When you press the 'Grant Microphone Access' button, "
    "a browser popup will come asking to grant access. Please accept it now."
)

DEMO_MIC_CONFIRMED_LINE: Final[str] = (
    "Good, I am receiving your audio. Please state your name so I can verify the vocal baseline."
)

# --------------------------------------------------------------------------- #
# Camera & room scan                                                            #
# --------------------------------------------------------------------------- #

DEMO_CAMERA_REQUEST_LINE: Final[str] = (
    "Your voice is clear. Address the caller as Mr or Mrs followed by the name they "
    "just gave you. Then say: Now I need the room feed. I need deliberate permission. "
    "Please press the Grant Camera Access button so I can see what we're working with."
)

DEMO_ROOM_SCAN_LINE: Final[str] = (
    "Good. Now stand in the center of the room and slowly pan the camera around "
    "in a full circle. Take about five seconds for a 360-degree view. "
    "Make sure the room is well-lit and the camera is steady. "
    "I need a clear feed — if the image is too dark or blurry, I will ask you to try again. "
    "I need to scan the full room before we begin containment."
)

DEMO_ROOM_SCAN_ASSESSMENT_LINE: Final[str] = (
    "Calibration sweep received. Our sensors are now processing the "
    "spatial data. Initial readings show elevated residual activity "
    "in this area. Spectral displacement concentrated near the "
    "threshold zone. This is consistent with a Class-2 residential "
    "haunting. Containment protocol is warranted. Stay with me."
)

# --------------------------------------------------------------------------- #
# Task assignment                                                               #
# --------------------------------------------------------------------------- #

DEMO_DIAGNOSIS_QUESTION_LINE: Final[str] = "What did the sound resemble. Briefly."
DEMO_DIAGNOSIS_INTERPRETATION_LINE: Final[str] = (
    "That matches threshold activity. Classic displacement behavior — the disturbance "
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
    "Anchor is set. Good. That paper is your tripwire now — if it moves "
    "when you're not looking, the displacement field is active in that zone. "
    "We have our reference point. Moving on."
)

DEMO_FLAVOR_POST_T14: Final[str] = (
    "I've logged the sound profile. That pattern is consistent with what "
    "we've catalogued as boundary-phase displacement. It knows it's trapped. "
    "One more step and we seal it."
)

DEMO_FLAVOR_POST_T7: Final[str] = (
    "I felt that. The harmonic just flatlined — the displacement field "
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
    "again — slowly. I need to compare it to what I saw before."
)

DEMO_FINAL_CLOSURE_LINE: Final[str] = (
    "Containment Desk is closing the case now. All boundary checks confirmed. "
    "Spectral readings are within safe parameters. The displacement field has "
    "collapsed. Hold the room quiet tonight — do not disturb the placements. "
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
    "DEMO_MIC_CONFIRMED_LINE",
    "DEMO_OPENER_LINE_GRANTED",
    "DEMO_OPENER_LINE_PROMPT",
    "DEMO_RECOVERY_LINE",
    "DEMO_ROOM_SCAN_ASSESSMENT_LINE",
    "DEMO_ROOM_SCAN_LINE",
    "build_demo_task_assignment_line",
    "get_demo_flavor_for_task",
]
