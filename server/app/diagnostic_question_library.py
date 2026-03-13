"""Authored diagnostic question library for Prompt 27."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, TypeAlias

DiagnosticCategory: TypeAlias = Literal[
    "sound",
    "location",
    "light_reactivity",
    "stillness_motion",
    "escalation",
]

DiagnosticAppropriateWhen: TypeAlias = Literal[
    "between_tasks",
    "after_user_reports_noise",
    "after_location_report",
    "after_light_change",
    "after_motion_report",
    "after_escalation_report",
]

_REQUIRED_CATEGORIES: Final[tuple[DiagnosticCategory, ...]] = (
    "sound",
    "location",
    "light_reactivity",
    "stillness_motion",
    "escalation",
)
_MIN_QUESTIONS_PER_CATEGORY: Final[int] = 3
_MAX_QUESTION_LENGTH: Final[int] = 96


@dataclass(frozen=True)
class DiagnosticQuestion:
    id: str
    category: DiagnosticCategory
    appropriate_when: tuple[DiagnosticAppropriateWhen, ...]
    text: str


DIAGNOSTIC_QUESTION_LIBRARY: Final[tuple[DiagnosticQuestion, ...]] = (
    DiagnosticQuestion(
        id="diagnostic_sound_01",
        category="sound",
        appropriate_when=("between_tasks", "after_user_reports_noise"),
        text="What did the sound resemble?",
    ),
    DiagnosticQuestion(
        id="diagnostic_sound_02",
        category="sound",
        appropriate_when=("between_tasks", "after_user_reports_noise"),
        text="Was it a knock, a scrape, or a voice?",
    ),
    DiagnosticQuestion(
        id="diagnostic_sound_03",
        category="sound",
        appropriate_when=("between_tasks", "after_user_reports_noise"),
        text="Did it repeat in a pattern or only once?",
    ),
    DiagnosticQuestion(
        id="diagnostic_location_01",
        category="location",
        appropriate_when=("between_tasks", "after_location_report"),
        text="Where was it strongest?",
    ),
    DiagnosticQuestion(
        id="diagnostic_location_02",
        category="location",
        appropriate_when=("between_tasks", "after_location_report"),
        text="Was it holding near the doorway or deeper in the room?",
    ),
    DiagnosticQuestion(
        id="diagnostic_location_03",
        category="location",
        appropriate_when=("between_tasks", "after_location_report"),
        text="Did it stay local or drift as you moved?",
    ),
    DiagnosticQuestion(
        id="diagnostic_light_01",
        category="light_reactivity",
        appropriate_when=("between_tasks", "after_light_change"),
        text="Did it change with the light?",
    ),
    DiagnosticQuestion(
        id="diagnostic_light_02",
        category="light_reactivity",
        appropriate_when=("between_tasks", "after_light_change"),
        text="Did the room react when the screen brightened?",
    ),
    DiagnosticQuestion(
        id="diagnostic_light_03",
        category="light_reactivity",
        appropriate_when=("between_tasks", "after_light_change"),
        text="Did the flicker stop when the light held steady?",
    ),
    DiagnosticQuestion(
        id="diagnostic_motion_01",
        category="stillness_motion",
        appropriate_when=("between_tasks", "after_motion_report"),
        text="Did it stop when you stood still?",
    ),
    DiagnosticQuestion(
        id="diagnostic_motion_02",
        category="stillness_motion",
        appropriate_when=("between_tasks", "after_motion_report"),
        text="Did the room change when the phone moved?",
    ),
    DiagnosticQuestion(
        id="diagnostic_motion_03",
        category="stillness_motion",
        appropriate_when=("between_tasks", "after_motion_report"),
        text="Did it react more to motion or to silence?",
    ),
    DiagnosticQuestion(
        id="diagnostic_escalation_01",
        category="escalation",
        appropriate_when=("between_tasks", "after_escalation_report"),
        text="Is it stronger, weaker, or unchanged now?",
    ),
    DiagnosticQuestion(
        id="diagnostic_escalation_02",
        category="escalation",
        appropriate_when=("between_tasks", "after_escalation_report"),
        text="Did the pressure shift after the last step?",
    ),
    DiagnosticQuestion(
        id="diagnostic_escalation_03",
        category="escalation",
        appropriate_when=("between_tasks", "after_escalation_report"),
        text="Did it calm when you followed the instruction exactly?",
    ),
)


def get_diagnostic_questions(
    category: DiagnosticCategory | None = None,
    *,
    appropriate_when: DiagnosticAppropriateWhen | None = None,
) -> tuple[DiagnosticQuestion, ...]:
    questions = DIAGNOSTIC_QUESTION_LIBRARY

    if category is not None:
        questions = tuple(
            question for question in questions if question.category == category
        )

    if appropriate_when is not None:
        questions = tuple(
            question
            for question in questions
            if appropriate_when in question.appropriate_when
        )

    return questions


def list_diagnostic_categories() -> tuple[DiagnosticCategory, ...]:
    return _REQUIRED_CATEGORIES


def _validate_library() -> None:
    seen_ids: set[str] = set()
    category_counts = {category: 0 for category in _REQUIRED_CATEGORIES}

    for question in DIAGNOSTIC_QUESTION_LIBRARY:
        if question.id in seen_ids:
            raise ValueError(f"Duplicate diagnostic question id: {question.id}")
        seen_ids.add(question.id)

        if question.category not in category_counts:
            raise ValueError(f"Unexpected diagnostic category: {question.category}")
        category_counts[question.category] += 1

        if not question.text.strip():
            raise ValueError(f"Diagnostic question {question.id} must not be empty.")
        if len(question.text) > _MAX_QUESTION_LENGTH:
            raise ValueError(
                f"Diagnostic question {question.id} exceeds {_MAX_QUESTION_LENGTH} characters."
            )
        if not question.appropriate_when:
            raise ValueError(
                f"Diagnostic question {question.id} must declare at least one appropriateness tag."
            )

    undercovered_categories = [
        category
        for category, count in category_counts.items()
        if count < _MIN_QUESTIONS_PER_CATEGORY
    ]
    if undercovered_categories:
        raise ValueError(
            "Diagnostic categories below minimum authored coverage: "
            + ", ".join(undercovered_categories)
        )


_validate_library()


__all__ = [
    "DIAGNOSTIC_QUESTION_LIBRARY",
    "DiagnosticAppropriateWhen",
    "DiagnosticCategory",
    "DiagnosticQuestion",
    "get_diagnostic_questions",
    "list_diagnostic_categories",
]
