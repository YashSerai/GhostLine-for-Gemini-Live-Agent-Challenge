"""State-aware flavor text selector for Prompt 29."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Final, Literal, TypeAlias

from .diagnostic_question_library import (
    DiagnosticAppropriateWhen,
    DiagnosticCategory,
    DiagnosticQuestion,
    get_diagnostic_questions,
    list_diagnostic_categories,
)
from .flavor_text_library import (
    FlavorTextCategory,
    FlavorTextLine,
    get_flavor_lines,
    list_flavor_categories,
)

FlavorState: TypeAlias = Literal[
    "opening_intake",
    "camera_request",
    "task_assignment",
    "task_in_progress",
    "verification_pending",
    "verification_success",
    "verification_failure",
    "substitution",
    "escalation",
    "final_closure",
]
FlavorSelectionKind: TypeAlias = Literal["flavor_line", "diagnostic_question"]

_REQUIRED_STATES: Final[tuple[FlavorState, ...]] = (
    "opening_intake",
    "camera_request",
    "task_assignment",
    "task_in_progress",
    "verification_pending",
    "verification_success",
    "verification_failure",
    "substitution",
    "escalation",
    "final_closure",
)
_CATEGORY_COOLDOWN: Final[int] = 2
_ITEM_COOLDOWN: Final[int] = 3


@dataclass(frozen=True)
class FlavorStateEligibility:
    flavor_categories: tuple[FlavorTextCategory, ...]
    diagnostic_appropriate_when: DiagnosticAppropriateWhen | None = None
    diagnostic_categories: tuple[DiagnosticCategory, ...] = ()


@dataclass(frozen=True)
class FlavorSelection:
    category: str
    id: str
    kind: FlavorSelectionKind
    occasion: str | None
    state: FlavorState
    text: str


_STATE_MODEL: Final[dict[FlavorState, FlavorStateEligibility]] = {
    "opening_intake": FlavorStateEligibility(
        flavor_categories=("opening_intake",),
    ),
    "camera_request": FlavorStateEligibility(
        flavor_categories=("camera_request",),
    ),
    "task_assignment": FlavorStateEligibility(
        flavor_categories=("task_introduction", "reassurance_control"),
    ),
    "task_in_progress": FlavorStateEligibility(
        flavor_categories=(
            "while_user_is_performing_task",
            "urgency_pacing",
            "reassurance_control",
        ),
    ),
    "verification_pending": FlavorStateEligibility(
        flavor_categories=("urgency_pacing", "reassurance_control"),
    ),
    "verification_success": FlavorStateEligibility(
        flavor_categories=("post_verification_reaction", "diagnosis_interpretation"),
        diagnostic_appropriate_when="between_tasks",
        diagnostic_categories=(
            "sound",
            "location",
            "light_reactivity",
            "stillness_motion",
        ),
    ),
    "verification_failure": FlavorStateEligibility(
        flavor_categories=("post_verification_reaction", "recovery_response"),
        diagnostic_appropriate_when="between_tasks",
        diagnostic_categories=("location", "light_reactivity", "stillness_motion"),
    ),
    "substitution": FlavorStateEligibility(
        flavor_categories=("swap_task_response", "reassurance_control"),
    ),
    "escalation": FlavorStateEligibility(
        flavor_categories=(
            "urgency_pacing",
            "reassurance_control",
            "diagnosis_interpretation",
        ),
        diagnostic_appropriate_when="after_escalation_report",
        diagnostic_categories=("sound", "stillness_motion", "escalation"),
    ),
    "final_closure": FlavorStateEligibility(
        flavor_categories=("final_closure",),
    ),
}

_DEFAULT_OCCASIONS: Final[dict[tuple[FlavorState, FlavorTextCategory], str]] = {
    ("camera_request", "camera_request"): "initial",
    ("verification_success", "post_verification_reaction"): "confirmed",
    ("verification_failure", "post_verification_reaction"): "unconfirmed",
    ("final_closure", "final_closure"): "contained",
}


class FlavorTextStateModel:
    def __init__(self) -> None:
        self._rotation_counters: dict[tuple[str, str, str], int] = {}
        self._recent_flavor_categories: dict[str, deque[str]] = {}
        self._recent_flavor_ids: dict[str, deque[str]] = {}
        self._recent_diagnostic_categories: dict[str, deque[str]] = {}
        self._recent_diagnostic_ids: dict[str, deque[str]] = {}

    def get_eligibility(self, state: FlavorState) -> FlavorStateEligibility:
        return _STATE_MODEL[state]

    def select_flavor_line(
        self,
        session_id: str,
        state: FlavorState,
        *,
        occasion: str | None = None,
        preferred_category: FlavorTextCategory | None = None,
    ) -> FlavorSelection | None:
        eligibility = self.get_eligibility(state)
        categories = self._resolve_flavor_categories(
            eligibility.flavor_categories,
            preferred_category,
        )
        selected_category = self._select_rotating_value(
            session_id,
            state,
            "flavor_category",
            self._apply_recent_filter(
                categories,
                self._get_recent_history(self._recent_flavor_categories, session_id, _CATEGORY_COOLDOWN),
            ),
        )
        if selected_category is None:
            return None

        selected_occasion = occasion or _DEFAULT_OCCASIONS.get(
            (state, selected_category)
        )
        lines = get_flavor_lines(selected_category, occasion=selected_occasion)
        if not lines:
            lines = get_flavor_lines(selected_category)
            selected_occasion = None
        selected_line = self._select_rotating_value(
            session_id,
            state,
            f"flavor_item:{selected_category}",
            self._apply_recent_filter(
                lines,
                self._get_recent_history(self._recent_flavor_ids, session_id, _ITEM_COOLDOWN),
                key=lambda line: line.id,
            ),
        )
        if selected_line is None:
            return None

        self._record_history(self._recent_flavor_categories, session_id, selected_category, _CATEGORY_COOLDOWN)
        self._record_history(self._recent_flavor_ids, session_id, selected_line.id, _ITEM_COOLDOWN)
        return FlavorSelection(
            category=selected_category,
            id=selected_line.id,
            kind="flavor_line",
            occasion=selected_occasion,
            state=state,
            text=selected_line.text,
        )

    def select_diagnostic_question(
        self,
        session_id: str,
        state: FlavorState,
        *,
        appropriate_when: DiagnosticAppropriateWhen | None = None,
        preferred_category: DiagnosticCategory | None = None,
    ) -> FlavorSelection | None:
        eligibility = self.get_eligibility(state)
        if not eligibility.diagnostic_categories:
            return None

        categories = self._resolve_diagnostic_categories(
            eligibility.diagnostic_categories,
            preferred_category,
        )
        selected_category = self._select_rotating_value(
            session_id,
            state,
            "diagnostic_category",
            self._apply_recent_filter(
                categories,
                self._get_recent_history(
                    self._recent_diagnostic_categories,
                    session_id,
                    _CATEGORY_COOLDOWN,
                ),
            ),
        )
        if selected_category is None:
            return None

        selected_appropriate_when = (
            appropriate_when or eligibility.diagnostic_appropriate_when or "between_tasks"
        )
        questions = get_diagnostic_questions(
            selected_category,
            appropriate_when=selected_appropriate_when,
        )
        if not questions:
            questions = get_diagnostic_questions(selected_category)
            selected_appropriate_when = None
        selected_question = self._select_rotating_value(
            session_id,
            state,
            f"diagnostic_item:{selected_category}",
            self._apply_recent_filter(
                questions,
                self._get_recent_history(
                    self._recent_diagnostic_ids,
                    session_id,
                    _ITEM_COOLDOWN,
                ),
                key=lambda question: question.id,
            ),
        )
        if selected_question is None:
            return None

        self._record_history(
            self._recent_diagnostic_categories,
            session_id,
            selected_category,
            _CATEGORY_COOLDOWN,
        )
        self._record_history(
            self._recent_diagnostic_ids,
            session_id,
            selected_question.id,
            _ITEM_COOLDOWN,
        )
        return FlavorSelection(
            category=selected_category,
            id=selected_question.id,
            kind="diagnostic_question",
            occasion=selected_appropriate_when,
            state=state,
            text=selected_question.text,
        )

    def reset_session(self, session_id: str) -> None:
        self._recent_flavor_categories.pop(session_id, None)
        self._recent_flavor_ids.pop(session_id, None)
        self._recent_diagnostic_categories.pop(session_id, None)
        self._recent_diagnostic_ids.pop(session_id, None)
        for key in tuple(self._rotation_counters):
            if key[0] == session_id:
                self._rotation_counters.pop(key, None)

    def _resolve_flavor_categories(
        self,
        eligible_categories: tuple[FlavorTextCategory, ...],
        preferred_category: FlavorTextCategory | None,
    ) -> tuple[FlavorTextCategory, ...]:
        if preferred_category is None:
            return eligible_categories
        if preferred_category not in eligible_categories:
            raise ValueError(
                f"Flavor category {preferred_category!r} is not eligible for the current state."
            )
        return (preferred_category,)

    def _resolve_diagnostic_categories(
        self,
        eligible_categories: tuple[DiagnosticCategory, ...],
        preferred_category: DiagnosticCategory | None,
    ) -> tuple[DiagnosticCategory, ...]:
        if preferred_category is None:
            return eligible_categories
        if preferred_category not in eligible_categories:
            raise ValueError(
                f"Diagnostic category {preferred_category!r} is not eligible for the current state."
            )
        return (preferred_category,)

    def _get_recent_history(
        self,
        store: dict[str, deque[str]],
        session_id: str,
        max_length: int,
    ) -> tuple[str, ...]:
        history = store.get(session_id)
        if history is None:
            return ()
        return tuple(history)[-max_length:]

    def _record_history(
        self,
        store: dict[str, deque[str]],
        session_id: str,
        value: str,
        max_length: int,
    ) -> None:
        history = store.setdefault(session_id, deque(maxlen=max_length))
        history.append(value)

    def _select_rotating_value(self, session_id: str, state: FlavorState, bucket: str, values):
        if not values:
            return None
        counter_key = (session_id, state, bucket)
        current_index = self._rotation_counters.get(counter_key, 0)
        selected_value = values[current_index % len(values)]
        self._rotation_counters[counter_key] = current_index + 1
        return selected_value

    def _apply_recent_filter(self, values, recent_values: tuple[str, ...], *, key=lambda value: value):
        if len(values) <= 1:
            return tuple(values)
        filtered_values = tuple(
            value for value in values if key(value) not in recent_values
        )
        return filtered_values or tuple(values)


def list_flavor_states() -> tuple[FlavorState, ...]:
    return _REQUIRED_STATES


def _validate_state_model() -> None:
    if set(_STATE_MODEL) != set(_REQUIRED_STATES):
        missing_states = [state for state in _REQUIRED_STATES if state not in _STATE_MODEL]
        extra_states = [state for state in _STATE_MODEL if state not in _REQUIRED_STATES]
        raise ValueError(
            "Flavor state model mismatch. Missing states: "
            + ", ".join(missing_states or ["none"])
            + "; extra states: "
            + ", ".join(extra_states or ["none"])
        )

    valid_flavor_categories = set(list_flavor_categories())
    valid_diagnostic_categories = set(list_diagnostic_categories())

    for state, eligibility in _STATE_MODEL.items():
        if not eligibility.flavor_categories:
            raise ValueError(f"Flavor state {state} must expose at least one flavor category.")
        invalid_flavor_categories = [
            category
            for category in eligibility.flavor_categories
            if category not in valid_flavor_categories
        ]
        if invalid_flavor_categories:
            raise ValueError(
                f"Flavor state {state} references unknown flavor categories: {invalid_flavor_categories}"
            )
        invalid_diagnostic_categories = [
            category
            for category in eligibility.diagnostic_categories
            if category not in valid_diagnostic_categories
        ]
        if invalid_diagnostic_categories:
            raise ValueError(
                f"Flavor state {state} references unknown diagnostic categories: {invalid_diagnostic_categories}"
            )


_validate_state_model()


__all__ = [
    "FlavorSelection",
    "FlavorSelectionKind",
    "FlavorState",
    "FlavorStateEligibility",
    "FlavorTextStateModel",
    "list_flavor_states",
]
