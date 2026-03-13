"""Deterministic demo-mode planning for Prompt 43."""

from __future__ import annotations

from typing import Final

from .protocol_planner import ProtocolPlan, ProtocolStepAssignment
from .task_helpers import get_task_by_id

DEMO_MODE_TASK_SEQUENCE: Final[tuple[str, ...]] = (
    "T1",
    "T2",
    "T3",
    "T4",
    "T6",
    "T7",
)

DEMO_MODE_PATH_MODE: Final[str] = "threshold"

_DEMO_MODE_ASSIGNMENTS: Final[tuple[ProtocolStepAssignment, ...]] = (
    ProtocolStepAssignment(
        step="assess_boundary",
        task_id="T1",
        reason=(
            "Demo mode always opens by showing the threshold so the judged path "
            "starts with a clear, readable room boundary."
        ),
        uses_substitute=False,
    ),
    ProtocolStepAssignment(
        step="secure",
        task_id="T2",
        reason=(
            "Demo mode always follows with an explicit boundary close so the "
            "containment sequence feels procedural on every run."
        ),
        uses_substitute=False,
    ),
    ProtocolStepAssignment(
        step="visibility_or_stabilization",
        task_id="T3",
        reason=(
            "Demo mode uses the fixed illumination step because it is safe, "
            "reliable, and easy to read on camera."
        ),
        uses_substitute=False,
    ),
    ProtocolStepAssignment(
        step="visibility_or_stabilization",
        task_id="T4",
        reason=(
            "Demo mode immediately follows with camera stabilization so the "
            "recorded verification path stays filmable and repeatable."
        ),
        uses_substitute=False,
    ),
    ProtocolStepAssignment(
        step="anchor",
        task_id="T6",
        reason=(
            "Demo mode uses the clear-surface anchor instead of paper placement "
            "to avoid fragile optional-object dependencies."
        ),
        uses_substitute=True,
    ),
    ProtocolStepAssignment(
        step="seal_closure",
        task_id="T7",
        reason=(
            "Demo mode always closes with the spoken containment phrase so the "
            "final seal remains voice-first and easy to subtitle."
        ),
        uses_substitute=False,
    ),
)


def build_demo_protocol_plan() -> ProtocolPlan:
    """Return the fixed demo-safe protocol plan."""

    selected_tasks = tuple(get_task_by_id(task_id) for task_id in DEMO_MODE_TASK_SEQUENCE)
    return ProtocolPlan(
        selected_task_ids=DEMO_MODE_TASK_SEQUENCE,
        selected_tasks=selected_tasks,
        protocol_step_mapping=_DEMO_MODE_ASSIGNMENTS,
    )


__all__ = [
    "DEMO_MODE_PATH_MODE",
    "DEMO_MODE_TASK_SEQUENCE",
    "build_demo_protocol_plan",
]
