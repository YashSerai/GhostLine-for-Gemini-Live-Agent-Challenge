"""Fixed demo-mode dialogue pack for Prompt 44."""

from __future__ import annotations

from typing import Any, Final

DEMO_CAMERA_REQUEST_LINE: Final[str] = (
    "Ghostline Containment Desk. I need the room feed now. Grant camera access and show me the doorway, not your face."
)
DEMO_CALIBRATION_LINE: Final[str] = (
    "Calibration is one clean still frame of the room. Keep the doorway centered, hold the phone level, capture it once, then stay still."
)
DEMO_DIAGNOSIS_QUESTION_LINE: Final[str] = "What did the sound resemble. Briefly."
DEMO_DIAGNOSIS_INTERPRETATION_LINE: Final[str] = (
    "That matches threshold activity. Keep the room controlled and continue with the next step."
)
DEMO_RECOVERY_LINE: Final[str] = (
    "I cannot verify that hold yet. Bring the boundary back to center, raise the light slightly, and give me one more still frame."
)
DEMO_FINAL_CLOSURE_LINE: Final[str] = (
    "Containment Desk is closing the case now. Hold the room quiet while I file the final report."
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


__all__ = [
    "DEMO_CALIBRATION_LINE",
    "DEMO_CAMERA_REQUEST_LINE",
    "DEMO_DIAGNOSIS_INTERPRETATION_LINE",
    "DEMO_DIAGNOSIS_QUESTION_LINE",
    "DEMO_FINAL_CLOSURE_LINE",
    "DEMO_RECOVERY_LINE",
    "build_demo_task_assignment_line",
]
