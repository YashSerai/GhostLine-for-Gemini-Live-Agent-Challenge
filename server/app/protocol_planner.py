"""Deterministic 5-6 task protocol planner for Prompt 18."""

from __future__ import annotations

from dataclasses import dataclass
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
    """Raised when a deterministic 5-6 task protocol plan cannot be built."""


def build_protocol_plan(profile: CapabilityProfile) -> ProtocolPlan:
    """Build a deterministic 5-6 task plan from the capability profile."""

    assignments = (
        _select_assess_boundary_step(profile),
        _select_secure_step(profile),
        _select_visibility_or_stabilization_step(profile),
        _select_anchor_step(profile),
        _select_mark_or_substitute_step(profile),
        _select_seal_closure_step(profile),
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


def _select_assess_boundary_step(profile: CapabilityProfile) -> ProtocolStepAssignment:
    threshold_affordance = profile.resolved_affordances.threshold_available
    if (
        profile.environment.path_mode == "threshold"
        and threshold_affordance.available is not False
    ):
        return ProtocolStepAssignment(
            step="assess_boundary",
            task_id="T1",
            reason="Threshold path is supported, so the plan opens by showing the room boundary.",
            uses_substitute=False,
        )

    return ProtocolStepAssignment(
        step="assess_boundary",
        task_id="T2",
        reason="Threshold path is unavailable or unsafe, so the plan starts with the fallback boundary-control step.",
        uses_substitute=True,
    )


def _select_secure_step(profile: CapabilityProfile) -> ProtocolStepAssignment:
    assess_task_id = _select_assess_boundary_step(profile).task_id
    if assess_task_id == "T2":
        return ProtocolStepAssignment(
            step="secure",
            task_id=None,
            reason="The boundary fallback already performs the secure step, so no extra secure task is added.",
            uses_substitute=False,
        )

    return ProtocolStepAssignment(
        step="secure",
        task_id="T2",
        reason="After boundary assessment, the boundary is actively secured with a hard-gating containment task.",
        uses_substitute=False,
    )


def _select_visibility_or_stabilization_step(
    profile: CapabilityProfile,
) -> ProtocolStepAssignment:
    light_control = profile.resolved_affordances.light_controllable
    if light_control.available is True and (
        profile.quality_metrics.lighting < 0.7
        or profile.environment.path_mode == "low_visibility"
    ):
        return ProtocolStepAssignment(
            step="visibility_or_stabilization",
            task_id="T3",
            reason="Lighting is limited but controllable, so the planner prefers a Tier 1 visibility correction.",
            uses_substitute=False,
        )

    return ProtocolStepAssignment(
        step="visibility_or_stabilization",
        task_id="T4",
        reason="The planner uses camera stabilization as the deterministic visual-quality step when more light is not the primary fix.",
        uses_substitute=False,
    )


def _select_anchor_step(profile: CapabilityProfile) -> ProtocolStepAssignment:
    flat_surface = profile.resolved_affordances.flat_surface_available
    paper = profile.resolved_affordances.paper_available

    if flat_surface.available is not False and paper.available is True:
        return ProtocolStepAssignment(
            step="anchor",
            task_id="T5",
            reason="Paper and a flat surface are available, so the plan uses the strongest anchor task.",
            uses_substitute=False,
        )

    if flat_surface.available is not False:
        return ProtocolStepAssignment(
            step="anchor",
            task_id="T6",
            reason="A flat surface is available but paper is not confirmed, so the planner falls back to the surface-anchor task.",
            uses_substitute=True,
        )

    return ProtocolStepAssignment(
        step="anchor",
        task_id="T13",
        reason="No anchor surface is available, so the planner inserts a non-blocking pacing fallback instead of dead-ending the protocol.",
        uses_substitute=True,
    )


def _select_mark_or_substitute_step(
    profile: CapabilityProfile,
) -> ProtocolStepAssignment:
    flat_surface = profile.resolved_affordances.flat_surface_available
    paper = profile.resolved_affordances.paper_available
    reflective_surface = profile.resolved_affordances.reflective_surface_available

    if flat_surface.available is not False and paper.available is True:
        return ProtocolStepAssignment(
            step="mark_or_substitute",
            task_id="T8",
            reason="Paper and anchor conditions support the primary mark task.",
            uses_substitute=False,
        )

    if profile.environment.path_mode == "low_visibility":
        return ProtocolStepAssignment(
            step="mark_or_substitute",
            task_id="T14",
            reason="Visual confirmation is limited, so the planner substitutes a diagnostic beat instead of bluffing a visual mark.",
            uses_substitute=True,
        )

    if reflective_surface.available is True:
        return ProtocolStepAssignment(
            step="mark_or_substitute",
            task_id="T9",
            reason="A reflective surface is available, so the planner substitutes a controlled visual diagnostic task.",
            uses_substitute=True,
        )

    if profile.environment.visual_quality_limited:
        return ProtocolStepAssignment(
            step="mark_or_substitute",
            task_id="T15",
            reason="The room is not clean enough for a visual mark, so the planner pivots to a deterministic localization question.",
            uses_substitute=True,
        )

    return ProtocolStepAssignment(
        step="mark_or_substitute",
        task_id="T10",
        reason="A vivid-object substitute keeps the protocol visual and deterministic when the primary mark task is not available.",
        uses_substitute=True,
    )


def _select_seal_closure_step(profile: CapabilityProfile) -> ProtocolStepAssignment:
    water_source = profile.resolved_affordances.water_source_nearby
    if water_source.available is True and profile.environment.path_mode == "tabletop":
        return ProtocolStepAssignment(
            step="seal_closure",
            task_id="T11",
            reason="A nearby water source makes the tabletop path suitable for the optional release-style closure.",
            uses_substitute=True,
        )

    return ProtocolStepAssignment(
        step="seal_closure",
        task_id="T7",
        reason="The planner closes with the Tier 1 containment phrase unless a tabletop water release is clearly supported.",
        uses_substitute=False,
    )


__all__ = [
    "ProtocolPlan",
    "ProtocolPlannerError",
    "ProtocolStepAssignment",
    "ProtocolStepName",
    "build_protocol_plan",
]
