"""Deterministic helper functions for the canonical task library."""

from __future__ import annotations

from typing import Final

from .task_library import (
    TASK_LIBRARY,
    TaskDefinition,
    TaskRoleCategory,
    TaskTier,
)


class InvalidTaskIdError(KeyError):
    """Raised when planner code references an unknown canonical task ID."""


class InvalidSubstitutionGroupError(KeyError):
    """Raised when planner code references an unknown substitution group."""


_TASKS_BY_ID: Final[dict[str, TaskDefinition]] = {
    task.id: task for task in TASK_LIBRARY
}
_TASKS_BY_SUBSTITUTION_GROUP: Final[dict[str, tuple[TaskDefinition, ...]]] = {
    substitution_group: tuple(
        task
        for task in TASK_LIBRARY
        if task.substitution_group == substitution_group
    )
    for substitution_group in {task.substitution_group for task in TASK_LIBRARY}
}


def get_task_by_id(task_id: str) -> TaskDefinition:
    """Return the canonical task definition for a task ID."""

    task = _TASKS_BY_ID.get(task_id)
    if task is None:
        raise InvalidTaskIdError(f"Unknown task ID: {task_id}")
    return task


def get_task_tier(task_id: str) -> TaskTier:
    """Return the reliability tier for a task ID."""

    return get_task_by_id(task_id).tier


def get_task_role_category(task_id: str) -> TaskRoleCategory:
    """Return the role category for a task ID."""

    return get_task_by_id(task_id).role_category


def can_task_hard_gate_progression(task_id: str) -> bool:
    """Return whether the task can block protocol progression."""

    return get_task_by_id(task_id).can_block_progression


def get_tasks_by_substitution_group(
    substitution_group: str,
) -> tuple[TaskDefinition, ...]:
    """Return the canonical tasks that share a substitution group."""

    tasks = _TASKS_BY_SUBSTITUTION_GROUP.get(substitution_group)
    if tasks is None:
        raise InvalidSubstitutionGroupError(
            f"Unknown substitution group: {substitution_group}"
        )
    return tasks


__all__ = [
    "InvalidSubstitutionGroupError",
    "InvalidTaskIdError",
    "can_task_hard_gate_progression",
    "get_task_by_id",
    "get_task_role_category",
    "get_task_tier",
    "get_tasks_by_substitution_group",
]
