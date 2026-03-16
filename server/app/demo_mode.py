"""Deterministic demo-mode planning - optimized for a judged hackathon demo."""

from __future__ import annotations

from typing import Final

from .protocol_planner import ProtocolPlan, ProtocolStepAssignment
from .task_helpers import get_task_by_id

# ---------------------------------------------------------------------------
# Optimized 4-task demo flow (~4 minutes total):
#   T2  Close Boundary             - dramatic door close, visual before/after
#   T5  Place Paper on Surface     - high-contrast anchor, easy AI verification
#   T14 Describe the Sound         - voice diagnostic, zero camera issues
#   T7  Speak Containment Phrase   - cinematic ritual chant finale
# ---------------------------------------------------------------------------

DEMO_MODE_TASK_SEQUENCE: Final[tuple[str, ...]] = (
    "T2",
    "T5",
    "T14",
    "T7",
)

DEMO_MODE_PATH_MODE: Final[str] = "threshold"

_DEMO_MODE_ASSIGNMENTS: Final[tuple[ProtocolStepAssignment, ...]] = (
    ProtocolStepAssignment(
        step="secure",
        task_id="T2",
        reason=(
            "Opens with boundary close - the door going from open to closed is "
            "immediately visible to judges, and the 'do NOT look through the crack' "
            "lore sets the tone. The step can still fail naturally if the caller "
            "leaves the boundary open, but demo mode does not force that outcome."
        ),
        uses_substitute=False,
    ),
    ProtocolStepAssignment(
        step="anchor",
        task_id="T5",
        reason=(
            "Paper placement on a cleared surface is the highest-contrast visual "
            "change - empty surface to white paper is unmistakable for AI "
            "verification. Demonstrates the before/after baseline comparison."
        ),
        uses_substitute=False,
    ),
    ProtocolStepAssignment(
        step="mark_or_substitute",
        task_id="T14",
        reason=(
            "Voice diagnostic showcases AI conversational intelligence and entity "
            "classification. Zero camera dependency - caller describes the shriek "
            "and the operator classifies it in real time."
        ),
        uses_substitute=False,
    ),
    ProtocolStepAssignment(
        step="seal_closure",
        task_id="T7",
        reason=(
            "Containment phrase is the cinematic finale - the caller repeats a "
            "ritual chant, the operator confirms the seal, and the case closes. "
            "Maximum dramatic impact for the ending."
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
