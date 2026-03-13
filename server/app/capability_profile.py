"""Deterministic capability profile and environment classification for Prompt 17."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

PathMode: TypeAlias = Literal["threshold", "tabletop", "low_visibility"]
CapabilityEvidenceSource: TypeAlias = Literal[
    "observed",
    "user_constraint",
    "unresolved",
]
QualityLevel: TypeAlias = Literal["good", "limited", "poor"]


@dataclass(frozen=True)
class ObservedAffordances:
    threshold_available: bool | None = None
    flat_surface_available: bool | None = None
    paper_available: bool | None = None
    light_controllable: bool | None = None
    reflective_surface_available: bool | None = None
    water_source_nearby: bool | None = None


@dataclass(frozen=True)
class UserDeclaredConstraints:
    cannot_use_threshold: bool = False
    no_flat_surface: bool = False
    no_paper: bool = False
    cannot_adjust_light: bool = False
    no_reflective_surface: bool = False
    no_water_source: bool = False
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class QualityMetrics:
    lighting: float
    blur: float
    motion_stability: float

    def __post_init__(self) -> None:
        _validate_normalized_metric("lighting", self.lighting)
        _validate_normalized_metric("blur", self.blur)
        _validate_normalized_metric("motion_stability", self.motion_stability)


@dataclass(frozen=True)
class ResolvedAffordance:
    available: bool | None
    blocked_by_user_constraint: bool
    source: CapabilityEvidenceSource


@dataclass(frozen=True)
class ResolvedAffordances:
    threshold_available: ResolvedAffordance
    flat_surface_available: ResolvedAffordance
    paper_available: ResolvedAffordance
    light_controllable: ResolvedAffordance
    reflective_surface_available: ResolvedAffordance
    water_source_nearby: ResolvedAffordance


@dataclass(frozen=True)
class EnvironmentClassification:
    path_mode: PathMode
    reasons: tuple[str, ...]
    lighting_level: QualityLevel
    blur_level: QualityLevel
    motion_stability_level: QualityLevel
    visual_quality_limited: bool
    threshold_ready: bool
    tabletop_ready: bool


@dataclass(frozen=True)
class CapabilityProfile:
    observed_affordances: ObservedAffordances
    user_constraints: UserDeclaredConstraints
    quality_metrics: QualityMetrics
    resolved_affordances: ResolvedAffordances
    environment: EnvironmentClassification


def build_capability_profile(
    *,
    observed_affordances: ObservedAffordances,
    quality_metrics: QualityMetrics,
    user_constraints: UserDeclaredConstraints | None = None,
) -> CapabilityProfile:
    """Build an inspectable capability profile from observations and constraints."""

    resolved_constraints = user_constraints or UserDeclaredConstraints()
    resolved_affordances = ResolvedAffordances(
        threshold_available=_resolve_affordance(
            observed_value=observed_affordances.threshold_available,
            blocked_by_constraint=resolved_constraints.cannot_use_threshold,
        ),
        flat_surface_available=_resolve_affordance(
            observed_value=observed_affordances.flat_surface_available,
            blocked_by_constraint=resolved_constraints.no_flat_surface,
        ),
        paper_available=_resolve_affordance(
            observed_value=observed_affordances.paper_available,
            blocked_by_constraint=resolved_constraints.no_paper,
        ),
        light_controllable=_resolve_affordance(
            observed_value=observed_affordances.light_controllable,
            blocked_by_constraint=resolved_constraints.cannot_adjust_light,
        ),
        reflective_surface_available=_resolve_affordance(
            observed_value=observed_affordances.reflective_surface_available,
            blocked_by_constraint=resolved_constraints.no_reflective_surface,
        ),
        water_source_nearby=_resolve_affordance(
            observed_value=observed_affordances.water_source_nearby,
            blocked_by_constraint=resolved_constraints.no_water_source,
        ),
    )
    environment = classify_environment(
        resolved_affordances=resolved_affordances,
        quality_metrics=quality_metrics,
    )
    return CapabilityProfile(
        observed_affordances=observed_affordances,
        user_constraints=resolved_constraints,
        quality_metrics=quality_metrics,
        resolved_affordances=resolved_affordances,
        environment=environment,
    )


def classify_environment(
    *,
    resolved_affordances: ResolvedAffordances,
    quality_metrics: QualityMetrics,
) -> EnvironmentClassification:
    """Derive a deterministic path-mode recommendation from profile state."""

    lighting_level = _classify_positive_quality(quality_metrics.lighting)
    blur_level = _classify_inverse_quality(quality_metrics.blur)
    motion_stability_level = _classify_positive_quality(
        quality_metrics.motion_stability
    )

    visual_quality_limited = (
        quality_metrics.lighting < 0.35
        or quality_metrics.blur > 0.65
        or quality_metrics.motion_stability < 0.35
    )
    threshold_ready = (
        resolved_affordances.threshold_available.available is True
        and quality_metrics.lighting >= 0.4
        and quality_metrics.blur <= 0.65
        and quality_metrics.motion_stability >= 0.35
    )
    tabletop_ready = (
        resolved_affordances.flat_surface_available.available is True
        and quality_metrics.blur <= 0.75
        and quality_metrics.motion_stability >= 0.3
    )

    reasons: list[str] = [
        f"lighting={lighting_level}",
        f"blur={blur_level}",
        f"motion_stability={motion_stability_level}",
    ]

    if resolved_affordances.threshold_available.blocked_by_user_constraint:
        reasons.append("threshold blocked by user constraint")
    elif resolved_affordances.threshold_available.available is True:
        reasons.append("threshold is available")

    if resolved_affordances.flat_surface_available.blocked_by_user_constraint:
        reasons.append("flat surface blocked by user constraint")
    elif resolved_affordances.flat_surface_available.available is True:
        reasons.append("flat surface is available")

    if resolved_affordances.light_controllable.blocked_by_user_constraint:
        reasons.append("lighting cannot be adjusted")
    elif resolved_affordances.light_controllable.available is True:
        reasons.append("lighting can be adjusted")

    if visual_quality_limited and (
        resolved_affordances.light_controllable.available is not True
    ):
        reasons.append("visual quality is limited and cannot be recovered safely")
        return EnvironmentClassification(
            path_mode="low_visibility",
            reasons=tuple(reasons),
            lighting_level=lighting_level,
            blur_level=blur_level,
            motion_stability_level=motion_stability_level,
            visual_quality_limited=visual_quality_limited,
            threshold_ready=threshold_ready,
            tabletop_ready=tabletop_ready,
        )

    if threshold_ready:
        reasons.append("threshold path is supported")
        return EnvironmentClassification(
            path_mode="threshold",
            reasons=tuple(reasons),
            lighting_level=lighting_level,
            blur_level=blur_level,
            motion_stability_level=motion_stability_level,
            visual_quality_limited=visual_quality_limited,
            threshold_ready=threshold_ready,
            tabletop_ready=tabletop_ready,
        )

    if tabletop_ready:
        reasons.append("tabletop path is supported")
        return EnvironmentClassification(
            path_mode="tabletop",
            reasons=tuple(reasons),
            lighting_level=lighting_level,
            blur_level=blur_level,
            motion_stability_level=motion_stability_level,
            visual_quality_limited=visual_quality_limited,
            threshold_ready=threshold_ready,
            tabletop_ready=tabletop_ready,
        )

    reasons.append("falling back to low-visibility path")
    return EnvironmentClassification(
        path_mode="low_visibility",
        reasons=tuple(reasons),
        lighting_level=lighting_level,
        blur_level=blur_level,
        motion_stability_level=motion_stability_level,
        visual_quality_limited=visual_quality_limited,
        threshold_ready=threshold_ready,
        tabletop_ready=tabletop_ready,
    )


def _resolve_affordance(
    *,
    observed_value: bool | None,
    blocked_by_constraint: bool,
) -> ResolvedAffordance:
    if blocked_by_constraint:
        return ResolvedAffordance(
            available=False,
            blocked_by_user_constraint=True,
            source="user_constraint",
        )
    if observed_value is None:
        return ResolvedAffordance(
            available=None,
            blocked_by_user_constraint=False,
            source="unresolved",
        )
    return ResolvedAffordance(
        available=observed_value,
        blocked_by_user_constraint=False,
        source="observed",
    )


def _classify_positive_quality(value: float) -> QualityLevel:
    if value >= 0.7:
        return "good"
    if value >= 0.4:
        return "limited"
    return "poor"


def _classify_inverse_quality(value: float) -> QualityLevel:
    if value <= 0.3:
        return "good"
    if value <= 0.6:
        return "limited"
    return "poor"


def _validate_normalized_metric(name: str, value: float) -> None:
    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric.")
    if value < 0 or value > 1:
        raise ValueError(f"{name} must be between 0 and 1 inclusive.")


__all__ = [
    "CapabilityEvidenceSource",
    "CapabilityProfile",
    "EnvironmentClassification",
    "ObservedAffordances",
    "PathMode",
    "QualityLevel",
    "QualityMetrics",
    "ResolvedAffordance",
    "ResolvedAffordances",
    "UserDeclaredConstraints",
    "build_capability_profile",
    "classify_environment",
]
