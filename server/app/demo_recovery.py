"""Fixed demo near-failure and recovery beat for Prompt 46."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Literal

DemoNearFailureStatus = Literal["idle", "failed_once", "recovered"]


@dataclass(frozen=True)
class DemoNearFailureScript:
    task_id: str
    failure_type: str
    failure_block_reason: str
    failure_reason: str
    success_reason: str


DEMO_NEAR_FAILURE_SCRIPT: Final[DemoNearFailureScript] = DemoNearFailureScript(
    task_id="T2",
    failure_type="boundary_not_sealed",
    failure_block_reason=(
        "The verification window shows the boundary still appears open — "
        "the door has not been fully closed."
    ),
    failure_reason=(
        "The first demo verification intentionally catches the boundary "
        "still unsealed so the recovery ladder is visible to judges."
    ),
    success_reason=(
        "The corrected hold confirmed the door is now closed and the "
        "boundary is sealed. Containment perimeter established."
    ),
)


def matches_demo_near_failure_task(task_context: dict[str, Any]) -> bool:
    task_id = task_context.get("taskId")
    return isinstance(task_id, str) and task_id.strip() == DEMO_NEAR_FAILURE_SCRIPT.task_id


__all__ = [
    "DEMO_NEAR_FAILURE_SCRIPT",
    "DemoNearFailureStatus",
    "matches_demo_near_failure_task",
]
