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
    task_id="T3",
    failure_type="temporary_low_light",
    failure_block_reason=(
        "The verification window stayed slightly too dim to confirm this demo step honestly."
    ),
    failure_reason=(
        "The first demo verification intentionally catches a brief low-light miss so the recovery ladder is visible."
    ),
    success_reason=(
        "The corrected hold restored enough light and framing to confirm the illumination step cleanly."
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
