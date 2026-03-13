"""Authored operator flavor text library for Prompt 25."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, TypeAlias

FlavorTextCategory: TypeAlias = Literal[
    "opening_intake",
    "camera_request",
    "task_introduction",
    "while_user_is_performing_task",
    "post_verification_reaction",
    "diagnosis_interpretation",
    "urgency_pacing",
    "reassurance_control",
    "swap_task_response",
    "recovery_response",
    "final_closure",
]

_REQUIRED_CATEGORIES: Final[tuple[FlavorTextCategory, ...]] = (
    "opening_intake",
    "camera_request",
    "task_introduction",
    "while_user_is_performing_task",
    "post_verification_reaction",
    "diagnosis_interpretation",
    "urgency_pacing",
    "reassurance_control",
    "swap_task_response",
    "recovery_response",
    "final_closure",
)
_MAX_LINE_LENGTH: Final[int] = 120


@dataclass(frozen=True)
class FlavorTextLine:
    id: str
    category: FlavorTextCategory
    occasion: str
    text: str


FLAVOR_TEXT_LIBRARY: Final[tuple[FlavorTextLine, ...]] = (
    FlavorTextLine(
        id="opening_intake_01",
        category="opening_intake",
        occasion="default",
        text="Ghostline, Containment Desk. Stay on the line and answer plainly.",
    ),
    FlavorTextLine(
        id="opening_intake_02",
        category="opening_intake",
        occasion="default",
        text="The Archivist speaking. Tell me what changed in the room, not what you fear it means.",
    ),
    FlavorTextLine(
        id="opening_intake_03",
        category="opening_intake",
        occasion="default",
        text="Containment Desk. Keep your voice level and give me the first clean detail.",
    ),
    FlavorTextLine(
        id="camera_request_01",
        category="camera_request",
        occasion="initial",
        text="I need the room, not your face. Show me the nearest threshold or doorway.",
    ),
    FlavorTextLine(
        id="camera_request_02",
        category="camera_request",
        occasion="initial",
        text="Bring the camera up now. Keep it level and let the room stay in frame.",
    ),
    FlavorTextLine(
        id="camera_request_03",
        category="camera_request",
        occasion="initial",
        text="Give me the boundary first. Hold there until I place the next step.",
    ),
    FlavorTextLine(
        id="task_introduction_01",
        category="task_introduction",
        occasion="default",
        text="Good. We move one step at a time. Do this exactly once, then stop.",
    ),
    FlavorTextLine(
        id="task_introduction_02",
        category="task_introduction",
        occasion="default",
        text="Next containment step now. Keep it simple and keep the frame readable.",
    ),
    FlavorTextLine(
        id="task_introduction_03",
        category="task_introduction",
        occasion="default",
        text="Use the nearest stable surface or boundary. Do not improvise beyond the instruction.",
    ),
    FlavorTextLine(
        id="while_user_is_performing_task_01",
        category="while_user_is_performing_task",
        occasion="waiting",
        text="Stay with the step.",
    ),
    FlavorTextLine(
        id="while_user_is_performing_task_02",
        category="while_user_is_performing_task",
        occasion="waiting",
        text="Do that now, then hold.",
    ),
    FlavorTextLine(
        id="while_user_is_performing_task_03",
        category="while_user_is_performing_task",
        occasion="waiting",
        text="Do not rush the frame.",
    ),
    FlavorTextLine(
        id="while_user_is_performing_task_04",
        category="while_user_is_performing_task",
        occasion="waiting",
        text="Good. Once it is placed, stop moving.",
    ),
    FlavorTextLine(
        id="post_verification_reaction_01",
        category="post_verification_reaction",
        occasion="confirmed",
        text="Confirmed. The step holds.",
    ),
    FlavorTextLine(
        id="post_verification_reaction_02",
        category="post_verification_reaction",
        occasion="user_confirmed_only",
        text="I can log that as caller-confirmed only. I am not marking it visually secure.",
    ),
    FlavorTextLine(
        id="post_verification_reaction_03",
        category="post_verification_reaction",
        occasion="unconfirmed",
        text="That did not hold cleanly. We correct it before the next move.",
    ),
    FlavorTextLine(
        id="diagnosis_interpretation_01",
        category="diagnosis_interpretation",
        occasion="sound",
        text="That reads like threshold activity, not a loose room echo.",
    ),
    FlavorTextLine(
        id="diagnosis_interpretation_02",
        category="diagnosis_interpretation",
        occasion="light",
        text="Noted. The room reacts more to framing than to noise.",
    ),
    FlavorTextLine(
        id="diagnosis_interpretation_03",
        category="diagnosis_interpretation",
        occasion="location",
        text="Understood. The disturbance is staying local instead of spreading.",
    ),
    FlavorTextLine(
        id="urgency_pacing_01",
        category="urgency_pacing",
        occasion="default",
        text="Stay with me. Keep the pace clean.",
    ),
    FlavorTextLine(
        id="urgency_pacing_02",
        category="urgency_pacing",
        occasion="default",
        text="Move now, but do not hurry past the frame.",
    ),
    FlavorTextLine(
        id="urgency_pacing_03",
        category="urgency_pacing",
        occasion="default",
        text="Keep it controlled. Fast is useful only if it stays readable.",
    ),
    FlavorTextLine(
        id="reassurance_control_01",
        category="reassurance_control",
        occasion="default",
        text="You are still in control of the room. Keep following the sequence.",
    ),
    FlavorTextLine(
        id="reassurance_control_02",
        category="reassurance_control",
        occasion="default",
        text="Nothing in this step requires force. Precision is enough.",
    ),
    FlavorTextLine(
        id="reassurance_control_03",
        category="reassurance_control",
        occasion="default",
        text="Hold steady. We only need a clear action, not a dramatic one.",
    ),
    FlavorTextLine(
        id="swap_task_response_01",
        category="swap_task_response",
        occasion="missing_object",
        text="Understood. We will not force that material. I am routing to a cleaner substitute.",
    ),
    FlavorTextLine(
        id="swap_task_response_02",
        category="swap_task_response",
        occasion="capability_mismatch",
        text="Noted. That path does not fit the room. I am giving you a safer step.",
    ),
    FlavorTextLine(
        id="swap_task_response_03",
        category="swap_task_response",
        occasion="general",
        text="Say what you cannot do plainly. I will swap the task, not the case.",
    ),
    FlavorTextLine(
        id="recovery_response_01",
        category="recovery_response",
        occasion="framing",
        text="Adjust the frame and hold the boundary cleanly this time.",
    ),
    FlavorTextLine(
        id="recovery_response_02",
        category="recovery_response",
        occasion="lighting",
        text="Increase the light, then give me the same step again without extra motion.",
    ),
    FlavorTextLine(
        id="recovery_response_03",
        category="recovery_response",
        occasion="stability",
        text="Steady the phone first. We retry only when the room stops drifting.",
    ),
    FlavorTextLine(
        id="final_closure_01",
        category="final_closure",
        occasion="contained",
        text="Containment holds. Stand down and leave the room as it is for now.",
    ),
    FlavorTextLine(
        id="final_closure_02",
        category="final_closure",
        occasion="contained",
        text="The case is stable enough to close. Do not disturb the final placement tonight.",
    ),
    FlavorTextLine(
        id="final_closure_03",
        category="final_closure",
        occasion="contained",
        text="We are closing the line. If the pattern returns, resume from the first boundary check.",
    ),
)


def get_flavor_lines(
    category: FlavorTextCategory,
    *,
    occasion: str | None = None,
) -> tuple[FlavorTextLine, ...]:
    if occasion is None:
        return tuple(line for line in FLAVOR_TEXT_LIBRARY if line.category == category)

    normalized_occasion = occasion.strip().lower()
    return tuple(
        line
        for line in FLAVOR_TEXT_LIBRARY
        if line.category == category and line.occasion.lower() == normalized_occasion
    )


def list_flavor_categories() -> tuple[FlavorTextCategory, ...]:
    return _REQUIRED_CATEGORIES


def _validate_library() -> None:
    seen_ids: set[str] = set()
    covered_categories = {category: 0 for category in _REQUIRED_CATEGORIES}

    for line in FLAVOR_TEXT_LIBRARY:
        if line.id in seen_ids:
            raise ValueError(f"Duplicate flavor line id: {line.id}")
        seen_ids.add(line.id)

        if line.category not in covered_categories:
            raise ValueError(f"Unexpected flavor category: {line.category}")
        covered_categories[line.category] += 1

        if not line.text.strip():
            raise ValueError(f"Flavor line {line.id} must not be empty.")
        if len(line.text) > _MAX_LINE_LENGTH:
            raise ValueError(
                f"Flavor line {line.id} exceeds {_MAX_LINE_LENGTH} characters."
            )

    missing_categories = [
        category for category, count in covered_categories.items() if count == 0
    ]
    if missing_categories:
        raise ValueError(
            "Missing authored flavor coverage for categories: "
            + ", ".join(missing_categories)
        )


_validate_library()


__all__ = [
    "FLAVOR_TEXT_LIBRARY",
    "FlavorTextCategory",
    "FlavorTextLine",
    "get_flavor_lines",
    "list_flavor_categories",
]
