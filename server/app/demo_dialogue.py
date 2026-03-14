"""Fixed demo-mode dialogue pack — optimized for Gemini Live Agent Challenge."""

from __future__ import annotations

from typing import Any, Final

# --------------------------------------------------------------------------- #
# Opener & mic test                                                             #
# --------------------------------------------------------------------------- #

DEMO_OPENER_LINE: Final[str] = (
    "Ghostline, Containment Desk. The Archivist speaking. "
    "I need to hear you clearly before we begin. "
    "Grant microphone access now so the line can pick up your voice."
)

DEMO_MIC_CONFIRMED_LINE: Final[str] = (
    "Good, your microphone is connected. "
    "Say something for me now so I can verify your audio is coming through."
)

# --------------------------------------------------------------------------- #
# Camera & room scan                                                            #
# --------------------------------------------------------------------------- #

DEMO_CAMERA_REQUEST_LINE: Final[str] = (
    "I need the room feed now. Grant camera access — I need to see what we're working with."
)

DEMO_ROOM_SCAN_LINE: Final[str] = (
    "Good. Now slowly pan the camera from left to right. "
    "I need to scan the full room before we begin containment."
)

DEMO_ROOM_SCAN_ASSESSMENT_LINE: Final[str] = (
    "I can see the space. Our sensors are reading elevated residual activity "
    "in this room. Spectral displacement concentrated near the threshold area. "
    "This is consistent with a Class-2 residential haunting. "
    "Containment protocol is warranted. Stay with me."
)

DEMO_CALIBRATION_LINE: Final[str] = (
    "Calibration is one clean still frame of the room. Keep the doorway centered, "
    "hold the phone level, capture it once, then stay still."
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
# Inter-task flavor text beats (Archivist lore)                                 #
# --------------------------------------------------------------------------- #

DEMO_FLAVOR_POST_T1: Final[str] = (
    "Good. The threshold is established. Residual patterns like this usually "
    "settle once boundary is defined. Moving to the next step."
)

DEMO_FLAVOR_POST_T2: Final[str] = (
    "Boundary is sealed. Activity of this type tends to concentrate near "
    "transitional spaces — doors, hallways, stairwells. We're containing it."
)

DEMO_FLAVOR_POST_T3: Final[str] = (
    "Illumination is up. The room reads cleaner now. Our containment protocol "
    "was designed for exactly this spectral profile."
)

DEMO_FLAVOR_POST_T4: Final[str] = (
    "Camera is stable. Readings are leveling. The room is responding well."
)

DEMO_FLAVOR_POST_T6: Final[str] = (
    "Surface is clear. That gives us a clean staging area for the final seal. "
    "Almost there."
)

DEMO_FLAVOR_BY_TASK: Final[dict[str, str]] = {
    "T1": DEMO_FLAVOR_POST_T1,
    "T2": DEMO_FLAVOR_POST_T2,
    "T3": DEMO_FLAVOR_POST_T3,
    "T4": DEMO_FLAVOR_POST_T4,
    "T6": DEMO_FLAVOR_POST_T6,
}

# --------------------------------------------------------------------------- #
# Verification & recovery                                                       #
# --------------------------------------------------------------------------- #

DEMO_RECOVERY_LINE: Final[str] = (
    "I cannot verify that hold yet. Bring the boundary back to center, "
    "raise the light slightly, and give me one more still frame."
)

DEMO_FINAL_CLOSURE_LINE: Final[str] = (
    "Containment Desk is closing the case now. All boundary checks confirmed. "
    "Spectral readings are within safe parameters. Hold the room quiet while "
    "I file the final report. Do not disturb the placements tonight."
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
    "DEMO_CALIBRATION_LINE",
    "DEMO_CAMERA_REQUEST_LINE",
    "DEMO_DIAGNOSIS_INTERPRETATION_LINE",
    "DEMO_DIAGNOSIS_QUESTION_LINE",
    "DEMO_FINAL_CLOSURE_LINE",
    "DEMO_FLAVOR_BY_TASK",
    "DEMO_MIC_CONFIRMED_LINE",
    "DEMO_OPENER_LINE",
    "DEMO_RECOVERY_LINE",
    "DEMO_ROOM_SCAN_ASSESSMENT_LINE",
    "DEMO_ROOM_SCAN_LINE",
    "build_demo_task_assignment_line",
    "get_demo_flavor_for_task",
]
