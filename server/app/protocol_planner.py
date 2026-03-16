"""Session-random 5-6 task protocol planner for regular mode."""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Literal, TypeAlias

from .capability_profile import CapabilityProfile
from .task_helpers import get_task_by_id
from .task_library import TaskDefinition

ProtocolStepName: TypeAlias = Literal[
    "assess_boundary",
    "secure",
    "visibility_or_stabilization",
    "anchor",
    "mark_or_substitute",
    "seal_closure",
]


@dataclass(frozen=True)
class ProtocolStepAssignment:
    step: ProtocolStepName
    task_id: str | None
    reason: str
    uses_substitute: bool


@dataclass(frozen=True)
class ProtocolPlan:
    selected_task_ids: tuple[str, ...]
    selected_tasks: tuple[TaskDefinition, ...]
    protocol_step_mapping: tuple[ProtocolStepAssignment, ...]


class ProtocolPlannerError(RuntimeError):
    """Raised when a regular-mode protocol plan cannot be built."""


def build_protocol_plan(
    profile: CapabilityProfile,
    *,
    seed: str | None = None,
) -> ProtocolPlan:
    """Build a 5-6 task plan with session-level variation for regular mode."""

    rng = random.Random(seed)
    assess_assignment = _select_assess_boundary_step(profile)
    assignments = (
        assess_assignment,
        _select_secure_step(profile, assess_assignment),
        _select_visibility_or_stabilization_step(profile, rng),
        _select_anchor_step(profile, rng),
        _select_mark_or_substitute_step(profile, rng),
        _select_seal_closure_step(profile, rng),
    )

    selected_task_ids = tuple(
        assignment.task_id
        for assignment in assignments
        if assignment.task_id is not None
    )
    selected_tasks = tuple(get_task_by_id(task_id) for task_id in selected_task_ids)

    if len(selected_task_ids) < 5 or len(selected_task_ids) > 6:
        raise ProtocolPlannerError(
            "Protocol plans must resolve to 5-6 selected tasks per session."
        )

    return ProtocolPlan(
        selected_task_ids=selected_task_ids,
        selected_tasks=selected_tasks,
        protocol_step_mapping=assignments,
    )


def _choose_assignment(
    rng: random.Random,
    candidates: tuple[ProtocolStepAssignment, ...],
) -> ProtocolStepAssignment:
    if not candidates:
        raise ProtocolPlannerError("Regular-mode task planner had no valid candidates for a protocol step.")
    return candidates[rng.randrange(len(candidates))]


def _select_assess_boundary_step(profile: CapabilityProfile) -> ProtocolStepAssignment:
    threshold_affordance = profile.resolved_affordances.threshold_available
    if (
        profile.environment.path_mode == "threshold"
        and threshold_affordance.available is not False
    ):
        return ProtocolStepAssignment(
            step="assess_boundary",
            task_id="T1",
            reason="Threshold path is supported, so regular mode opens by showing the room boundary.",
            uses_substitute=False,
        )

    return ProtocolStepAssignment(
        step="assess_boundary",
        task_id="T2",
        reason="Threshold path is unavailable or unsafe, so regular mode starts with the fallback boundary-control step.",
        uses_substitute=True,
    )


def _select_secure_step(
    profile: CapabilityProfile,
    assess_assignment: ProtocolStepAssignment,
) -> ProtocolStepAssignment:
    del profile
    if assess_assignment.task_id == "T2":
        return ProtocolStepAssignment(
            step="secure",
            task_id=None,
            reason="The boundary fallback already performs the secure step, so no extra secure task is added.",
            uses_substitute=False,
        )

    return ProtocolStepAssignment(
        step="secure",
        task_id="T2",
        reason="After boundary assessment, regular mode still secures the boundary with a hard-gating containment task.",
        uses_substitute=False,
    )


def _select_visibility_or_stabilization_step(
    profile: CapabilityProfile,
    rng: random.Random,
) -> ProtocolStepAssignment:
    candidates: list[ProtocolStepAssignment] = [
        ProtocolStepAssignment(
            step="visibility_or_stabilization",
            task_id="T4",
            reason="Regular mode selected camera stabilization for the visual-quality step.",
            uses_substitute=False,
        )
    ]

    light_control = profile.resolved_affordances.light_controllable
    if light_control.available is True:
        candidates.append(
            ProtocolStepAssignment(
                step="visibility_or_stabilization",
                task_id="T3",
                reason="Regular mode selected illumination correction because a controllable light source appears available.",
                uses_substitute=False,
            )
        )

    return _choose_assignment(rng, tuple(candidates))


def _select_anchor_step(
    profile: CapabilityProfile,
    rng: random.Random,
) -> ProtocolStepAssignment:
    flat_surface = profile.resolved_affordances.flat_surface_available
    paper = profile.resolved_affordances.paper_available

    if flat_surface.available is False:
        return ProtocolStepAssignment(
            step="anchor",
            task_id="T13",
            reason="No anchor surface is available, so regular mode inserts the pacing fallback instead of dead-ending the protocol.",
            uses_substitute=True,
        )

    candidates: list[ProtocolStepAssignment] = [
        ProtocolStepAssignment(
            step="anchor",
            task_id="T6",
            reason="Regular mode selected a clear-surface anchor step for this session.",
            uses_substitute=True,
        )
    ]
    if paper.available is True:
        candidates.append(
            ProtocolStepAssignment(
                step="anchor",
                task_id="T5",
                reason="Regular mode selected paper placement on a flat surface for this session.",
                uses_substitute=False,
            )
        )

    return _choose_assignment(rng, tuple(candidates))


def _select_mark_or_substitute_step(
    profile: CapabilityProfile,
    rng: random.Random,
) -> ProtocolStepAssignment:
    flat_surface = profile.resolved_affordances.flat_surface_available
    paper = profile.resolved_affordances.paper_available
    reflective_surface = profile.resolved_affordances.reflective_surface_available

    candidates: list[ProtocolStepAssignment] = []
    if flat_surface.available is not False and paper.available is True:
        candidates.append(
            ProtocolStepAssignment(
                step="mark_or_substitute",
                task_id="T8",
                reason="Regular mode selected the paper-mark task for this session.",
                uses_substitute=False,
            )
        )

    if reflective_surface.available is True:
        candidates.append(
            ProtocolStepAssignment(
                step="mark_or_substitute",
                task_id="T9",
                reason="Regular mode selected the reflective-surface diagnostic for this session.",
                uses_substitute=True,
            )
        )

    if profile.environment.visual_quality_limited:
        candidates.append(
            ProtocolStepAssignment(
                step="mark_or_substitute",
                task_id="T15",
                reason="Regular mode selected the low-visibility localization question because the room feed is limited.",
                uses_substitute=True,
            )
        )
    elif profile.environment.path_mode == "low_visibility":
        candidates.append(
            ProtocolStepAssignment(
                step="mark_or_substitute",
                task_id="T14",
                reason="Regular mode selected the audio diagnosis beat because the session path is low-visibility.",
                uses_substitute=True,
            )
        )
    else:
        candidates.append(
            ProtocolStepAssignment(
                step="mark_or_substitute",
                task_id="T10",
                reason="Regular mode selected a vivid-object visibility check for this session.",
                uses_substitute=True,
            )
        )

    return _choose_assignment(rng, tuple(candidates))


def _select_seal_closure_step(
    profile: CapabilityProfile,
    rng: random.Random,
) -> ProtocolStepAssignment:
    candidates: list[ProtocolStepAssignment] = [
        ProtocolStepAssignment(
            step="seal_closure",
            task_id="T7",
            reason="Regular mode selected the containment phrase as the closure step for this session.",
            uses_substitute=False,
        )
    ]

    water_source = profile.resolved_affordances.water_source_nearby
    if water_source.available is True and profile.environment.path_mode == "tabletop":
        candidates.append(
            ProtocolStepAssignment(
                step="seal_closure",
                task_id="T11",
                reason="Regular mode selected the nearby water-release closure for this session.",
                uses_substitute=True,
            )
        )

    return _choose_assignment(rng, tuple(candidates))


__all__ = [
    "ProtocolPlan",
    "ProtocolPlannerError",
    "ProtocolStepAssignment",
    "ProtocolStepName",
    "build_protocol_plan",
]
