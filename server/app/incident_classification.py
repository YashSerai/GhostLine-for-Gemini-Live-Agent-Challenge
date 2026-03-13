"""Lightweight incident classification for Prompt 28."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Literal, TypeAlias

from .diagnostic_question_library import DiagnosticCategory

IncidentClassificationLabel: TypeAlias = Literal[
    "threshold_disturbance",
    "reflective_anomaly",
    "low_visibility_anchor",
    "passive_echo",
    "reactive_presence",
]

_LABEL_DISPLAY_NAMES: Final[dict[IncidentClassificationLabel, str]] = {
    "threshold_disturbance": "threshold disturbance",
    "reflective_anomaly": "reflective anomaly",
    "low_visibility_anchor": "low-visibility anchor",
    "passive_echo": "passive echo",
    "reactive_presence": "reactive presence",
}

_PERSONAL_PROFILE_FIELDS: Final[tuple[str, ...]] = (
    "age",
    "gender",
    "race",
    "ethnicity",
    "religion",
    "nationality",
    "orientation",
    "health",
    "diagnosis",
)

_THRESHOLD_KEYWORDS: Final[tuple[str, ...]] = (
    "threshold",
    "door",
    "doorway",
    "hall",
    "hallway",
    "entry",
    "boundary",
    "frame",
)
_REFLECTIVE_KEYWORDS: Final[tuple[str, ...]] = (
    "mirror",
    "glass",
    "window",
    "reflection",
    "reflect",
    "screen",
    "shiny",
)
_LOW_VISIBILITY_KEYWORDS: Final[tuple[str, ...]] = (
    "dark",
    "dim",
    "shadow",
    "low light",
    "hard to see",
    "unclear",
    "blackout",
)
_PASSIVE_ECHO_KEYWORDS: Final[tuple[str, ...]] = (
    "echo",
    "knock",
    "tap",
    "scrape",
    "hum",
    "static",
    "murmur",
)
_REACTIVE_KEYWORDS: Final[tuple[str, ...]] = (
    "react",
    "changed",
    "followed",
    "stronger",
    "weaker",
    "shifted",
    "moved",
    "answered",
)


@dataclass(frozen=True)
class IncidentClassificationContext:
    path_mode: str | None
    user_descriptions: tuple[str, ...] = ()
    diagnostic_categories: tuple[DiagnosticCategory, ...] = ()
    latest_verification_status: str | None = None
    light_reactivity_reported: bool = False
    motion_reactivity_reported: bool = False
    escalation_reported: bool = False


@dataclass(frozen=True)
class IncidentClassificationDecision:
    display_label: str
    label: IncidentClassificationLabel
    matched_signals: tuple[str, ...]
    reason: str


@dataclass
class IncidentClassificationStore:
    _labels_by_session: dict[str, IncidentClassificationDecision] = field(
        default_factory=dict
    )

    def set_primary_label(
        self,
        session_id: str,
        decision: IncidentClassificationDecision,
    ) -> IncidentClassificationDecision:
        self._labels_by_session[session_id] = decision
        return decision

    def get_primary_label(
        self,
        session_id: str,
    ) -> IncidentClassificationDecision | None:
        return self._labels_by_session.get(session_id)

    def clear_session(self, session_id: str) -> None:
        self._labels_by_session.pop(session_id, None)


def classify_incident(
    context: IncidentClassificationContext,
) -> IncidentClassificationDecision:
    _validate_context(context)
    normalized_descriptions = " ".join(
        description.strip().lower()
        for description in context.user_descriptions
        if description.strip()
    )
    matched_signals: list[str] = []

    def has_any(keyword_group: tuple[str, ...]) -> bool:
        return any(keyword in normalized_descriptions for keyword in keyword_group)

    if context.path_mode == "threshold" or has_any(_THRESHOLD_KEYWORDS):
        matched_signals.extend(_collect_matches(normalized_descriptions, _THRESHOLD_KEYWORDS))
        return _build_decision(
            "threshold_disturbance",
            matched_signals or ["path_mode:threshold"],
            "Boundary language or threshold routing points to a threshold-linked incident.",
        )

    if (
        has_any(_REFLECTIVE_KEYWORDS)
        or (
            "light_reactivity" in context.diagnostic_categories
            and context.light_reactivity_reported
        )
    ):
        matched_signals.extend(
            _collect_matches(normalized_descriptions, _REFLECTIVE_KEYWORDS)
        )
        if context.light_reactivity_reported:
            matched_signals.append("reported:light_reactivity")
        return _build_decision(
            "reflective_anomaly",
            matched_signals or ["diagnostic:light_reactivity"],
            "Reflective or light-reactive cues dominate the current incident description.",
        )

    if context.path_mode == "low_visibility" or has_any(_LOW_VISIBILITY_KEYWORDS):
        matched_signals.extend(
            _collect_matches(normalized_descriptions, _LOW_VISIBILITY_KEYWORDS)
        )
        return _build_decision(
            "low_visibility_anchor",
            matched_signals or ["path_mode:low_visibility"],
            "Low-visibility constraints are the strongest usable signal in this session.",
        )

    if (
        has_any(_REACTIVE_KEYWORDS)
        or context.motion_reactivity_reported
        or context.escalation_reported
        or "stillness_motion" in context.diagnostic_categories
        or "escalation" in context.diagnostic_categories
    ):
        matched_signals.extend(_collect_matches(normalized_descriptions, _REACTIVE_KEYWORDS))
        if context.motion_reactivity_reported:
            matched_signals.append("reported:motion_reactivity")
        if context.escalation_reported:
            matched_signals.append("reported:escalation")
        return _build_decision(
            "reactive_presence",
            matched_signals or ["diagnostic:reactive"],
            "The incident appears to change in response to motion, pacing, or escalation.",
        )

    matched_signals.extend(_collect_matches(normalized_descriptions, _PASSIVE_ECHO_KEYWORDS))
    if context.latest_verification_status:
        matched_signals.append(f"verification:{context.latest_verification_status}")
    return _build_decision(
        "passive_echo",
        matched_signals or ["fallback:ambient_audio_pattern"],
        "No stronger boundary, reflective, or reactive signal dominated, so the incident remains a passive echo.",
    )


def format_incident_label_for_dialogue(
    decision: IncidentClassificationDecision,
) -> str:
    return f"This reads as a {decision.display_label}."


def format_incident_label_for_report(
    decision: IncidentClassificationDecision,
) -> str:
    return f"Primary incident label: {decision.display_label}."


def _build_decision(
    label: IncidentClassificationLabel,
    matched_signals: list[str],
    reason: str,
) -> IncidentClassificationDecision:
    return IncidentClassificationDecision(
        display_label=_LABEL_DISPLAY_NAMES[label],
        label=label,
        matched_signals=tuple(dict.fromkeys(matched_signals)),
        reason=reason,
    )


def _collect_matches(
    normalized_descriptions: str,
    keywords: tuple[str, ...],
) -> list[str]:
    return [
        f"keyword:{keyword}"
        for keyword in keywords
        if keyword in normalized_descriptions
    ]


def _validate_context(context: IncidentClassificationContext) -> None:
    lowered_descriptions = " ".join(
        description.lower() for description in context.user_descriptions
    )
    for banned_field in _PERSONAL_PROFILE_FIELDS:
        if banned_field in lowered_descriptions:
            raise ValueError(
                "Incident classification must not derive labels from personal profile traits."
            )


__all__ = [
    "IncidentClassificationContext",
    "IncidentClassificationDecision",
    "IncidentClassificationLabel",
    "IncidentClassificationStore",
    "classify_incident",
    "format_incident_label_for_dialogue",
    "format_incident_label_for_report",
]
