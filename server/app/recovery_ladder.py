"""Deterministic recovery ladder for verification failures."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Final, Literal

from .capability_profile import CapabilityProfile
from .flavor_text_library import get_flavor_lines
from .task_helpers import InvalidTaskIdError, InvalidSubstitutionGroupError, get_task_by_id, get_tasks_by_substitution_group
from .task_library import TaskDefinition

RecoveryStepKey = Literal[
    "move_closer",
    "adjust_angle_or_lighting",
    "hold_still_again",
    "retry_verification",
    "switch_path_or_substitute",
]

_MAX_RECOVERY_ATTEMPTS: Final[int] = 5
_RECOVERY_STEP_SEQUENCE: Final[tuple[RecoveryStepKey, ...]] = (
    "move_closer",
    "adjust_angle_or_lighting",
    "hold_still_again",
    "retry_verification",
    "switch_path_or_substitute",
)


@dataclass(frozen=True)
class SubstituteTaskSuggestion:
    task_id: str
    task_name: str
    substitution_group: str
    story_function: str
    tier: int


@dataclass(frozen=True)
class RecoveryDirective:
    attempt_count: int
    attempt_limit: int
    operator_line: str
    retry_allowed: bool
    step_instruction: str
    step_key: RecoveryStepKey
    step_label: str
    substitute_task: SubstituteTaskSuggestion | None = None
    suggested_path_mode: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "recoveryAttemptCount": self.attempt_count,
            "recoveryAttemptLimit": self.attempt_limit,
            "recoveryOperatorLine": self.operator_line,
            "recoveryStep": self.step_instruction,
            "recoveryStepKey": self.step_key,
            "recoveryStepLabel": self.step_label,
            "retryAllowed": self.retry_allowed,
            "suggestedPathMode": self.suggested_path_mode,
            "substituteTaskSuggestion": (
                asdict(self.substitute_task) if self.substitute_task is not None else None
            ),
        }


class VerificationRecoveryLadder:
    """Track deterministic recovery attempts per task context."""

    def __init__(self) -> None:
        self._attempt_counts: dict[str, int] = {}

    def is_retry_exhausted(
        self,
        *,
        task_context: dict[str, Any],
        current_path_mode: str,
    ) -> bool:
        return (
            self._attempt_counts.get(
                _build_recovery_key(
                    task_context=task_context,
                    current_path_mode=current_path_mode,
                ),
                0,
            )
            >= _MAX_RECOVERY_ATTEMPTS
        )

    def reset(
        self,
        *,
        task_context: dict[str, Any],
        current_path_mode: str,
    ) -> None:
        self._attempt_counts.pop(
            _build_recovery_key(task_context=task_context, current_path_mode=current_path_mode),
            None,
        )

    def build_directive(
        self,
        *,
        block_reason: str | None,
        capability_profile: CapabilityProfile,
        current_path_mode: str,
        reason: str | None,
        task_context: dict[str, Any],
    ) -> RecoveryDirective:
        key = _build_recovery_key(
            task_context=task_context,
            current_path_mode=current_path_mode,
        )
        attempt_count = min(self._attempt_counts.get(key, 0) + 1, _MAX_RECOVERY_ATTEMPTS)
        self._attempt_counts[key] = attempt_count

        step_key = _RECOVERY_STEP_SEQUENCE[attempt_count - 1]
        step_label = f"Recovery step {attempt_count} of {_MAX_RECOVERY_ATTEMPTS}"
        occasion = _resolve_recovery_occasion(block_reason=block_reason, reason=reason)
        current_task = _resolve_current_task(task_context)

        if step_key == "move_closer":
            instruction = "Move closer and keep the active item centered before retrying Ready to Verify."
            operator_line = "Move closer. Keep the same step centered and give me another clean hold."
            return RecoveryDirective(
                attempt_count=attempt_count,
                attempt_limit=_MAX_RECOVERY_ATTEMPTS,
                operator_line=operator_line,
                retry_allowed=True,
                step_instruction=instruction,
                step_key=step_key,
                step_label=step_label,
            )

        if step_key == "adjust_angle_or_lighting":
            instruction = _build_adjust_instruction(occasion)
            operator_line = _build_adjust_operator_line(occasion)
            return RecoveryDirective(
                attempt_count=attempt_count,
                attempt_limit=_MAX_RECOVERY_ATTEMPTS,
                operator_line=operator_line,
                retry_allowed=True,
                step_instruction=instruction,
                step_key=step_key,
                step_label=step_label,
            )

        if step_key == "hold_still_again":
            return RecoveryDirective(
                attempt_count=attempt_count,
                attempt_limit=_MAX_RECOVERY_ATTEMPTS,
                operator_line=_build_stability_operator_line(),
                retry_allowed=True,
                step_instruction="Hold still again for one full second once the frame is corrected.",
                step_key=step_key,
                step_label=step_label,
            )

        if step_key == "retry_verification":
            return RecoveryDirective(
                attempt_count=attempt_count,
                attempt_limit=_MAX_RECOVERY_ATTEMPTS,
                operator_line=(
                    "Good. Run the same step again now. Hold the correction exactly as it is and wait for my check."
                ),
                retry_allowed=True,
                step_instruction="Retry Ready to Verify with the corrected setup and no extra movement.",
                step_key=step_key,
                step_label=step_label,
            )

        suggested_path_mode = _suggest_path_mode(
            capability_profile=capability_profile,
            current_path_mode=current_path_mode,
        )
        substitute_task = _suggest_substitute_task(current_task)
        operator_line = _build_reroute_operator_line(
            suggested_path_mode=suggested_path_mode,
            substitute_task=substitute_task,
        )
        instruction = _build_reroute_instruction(
            suggested_path_mode=suggested_path_mode,
            substitute_task=substitute_task,
        )
        return RecoveryDirective(
            attempt_count=attempt_count,
            attempt_limit=_MAX_RECOVERY_ATTEMPTS,
            operator_line=operator_line,
            retry_allowed=False,
            step_instruction=instruction,
            step_key=step_key,
            step_label=step_label,
            substitute_task=substitute_task,
            suggested_path_mode=suggested_path_mode,
        )


def _build_recovery_key(*, task_context: dict[str, Any], current_path_mode: str) -> str:
    task_id = task_context.get("taskId")
    if isinstance(task_id, str) and task_id.strip():
        return f"task:{task_id.strip()}"

    protocol_step = task_context.get("protocolStep")
    if isinstance(protocol_step, str) and protocol_step.strip():
        return f"context:{protocol_step.strip()}::{current_path_mode}"

    return f"context:unresolved::{current_path_mode}"


def _resolve_recovery_occasion(
    *,
    block_reason: str | None,
    reason: str | None,
) -> str:
    basis = f"{block_reason or ''} {reason or ''}".lower()
    if any(token in basis for token in ("light", "dark", "dim", "bright")):
        return "lighting"
    if any(token in basis for token in ("stable", "stability", "motion", "steady", "blur", "blurry")):
        return "stability"
    return "framing"


def _build_adjust_instruction(occasion: str) -> str:
    if occasion == "lighting":
        return (
            "Increase the light or move toward the brightest area, keep the doorway or active item centered, "
            "then retry the same verification step."
        )
    if occasion == "stability":
        return (
            "Brace the phone against a solid surface or use both hands, keep the active item centered, "
            "and stop moving before the next hold."
        )
    return "Adjust the angle so the doorway or active item is centered cleanly before retrying the same step."


def _build_adjust_operator_line(occasion: str) -> str:
    if occasion == "lighting":
        lines = get_flavor_lines("recovery_response", occasion="lighting")
    elif occasion == "stability":
        lines = get_flavor_lines("recovery_response", occasion="stability")
    else:
        lines = get_flavor_lines("recovery_response", occasion="framing")

    if lines:
        authored_line = lines[0].text
        if occasion == "lighting":
            return (
                f"{authored_line} Move toward the brightest area and keep the doorway or active item centered."
            )
        if occasion == "stability":
            return (
                f"{authored_line} Brace the phone against something solid or use both hands before the next hold."
            )
        return f"{authored_line} Keep only the doorway or active item centered before the next hold."

    if occasion == "lighting":
        return "Increase the light or move toward the brightest area. Keep the doorway or active item centered, then give me the same step again without extra motion."
    if occasion == "stability":
        return "Brace the phone against something solid or use both hands. Keep the active item centered and wait until the room stops drifting."
    return "Adjust the frame so only the doorway or active item sits in the center, then hold it there cleanly."


def _build_stability_operator_line() -> str:
    lines = get_flavor_lines("recovery_response", occasion="stability")
    if lines:
        return f"{lines[0].text} Brace the phone against something solid or use both hands before the next hold."
    return "Brace the phone against something solid or use both hands. We retry only when the room stops drifting."


def _suggest_path_mode(
    *,
    capability_profile: CapabilityProfile,
    current_path_mode: str,
) -> str | None:
    if current_path_mode == "threshold":
        if capability_profile.environment.tabletop_ready:
            return "tabletop"
        if capability_profile.environment.visual_quality_limited:
            return "low_visibility"
        return None

    if current_path_mode == "tabletop":
        if capability_profile.environment.threshold_ready:
            return "threshold"
        if capability_profile.environment.visual_quality_limited:
            return "low_visibility"
        return None

    if capability_profile.environment.threshold_ready:
        return "threshold"
    if capability_profile.environment.tabletop_ready:
        return "tabletop"
    return None


def _resolve_current_task(task_context: dict[str, Any]) -> TaskDefinition | None:
    task_id = task_context.get("taskId")
    if not isinstance(task_id, str) or not task_id.strip():
        return None

    try:
        return get_task_by_id(task_id.strip())
    except InvalidTaskIdError:
        return None


def _suggest_substitute_task(
    current_task: TaskDefinition | None,
) -> SubstituteTaskSuggestion | None:
    if current_task is None:
        return None

    try:
        candidates = tuple(
            task
            for task in get_tasks_by_substitution_group(current_task.substitution_group)
            if task.id != current_task.id
        )
    except InvalidSubstitutionGroupError:
        return None

    if not candidates:
        return None

    ordered = sorted(
        candidates,
        key=lambda task: (
            0 if task.story_function == current_task.story_function else 1,
            task.tier,
            task.id,
        ),
    )
    selected = ordered[0]
    return SubstituteTaskSuggestion(
        task_id=selected.id,
        task_name=selected.name,
        substitution_group=selected.substitution_group,
        story_function=selected.story_function,
        tier=selected.tier,
    )


def _build_reroute_operator_line(
    *,
    suggested_path_mode: str | None,
    substitute_task: SubstituteTaskSuggestion | None,
) -> str:
    if suggested_path_mode is not None:
        return (
            f"This path is still blocked. I am routing you to the {suggested_path_mode.replace('_', ' ')} path instead of forcing another blind retry."
        )
    if substitute_task is not None:
        return (
            f"This path is still blocked. I am routing to {substitute_task.task_name} as the safer substitute step."
        )
    return "This path is still blocked. Hold there while I reroute the case to a safer option."


def _build_reroute_instruction(
    *,
    suggested_path_mode: str | None,
    substitute_task: SubstituteTaskSuggestion | None,
) -> str:
    if suggested_path_mode is not None:
        return f"Switch path mode to {suggested_path_mode.replace('_', ' ')} before the next verification attempt."
    if substitute_task is not None:
        return f"Switch to substitute task {substitute_task.task_name} before the next verification attempt."
    return "Do not keep retrying this verification path. Reroute to a safer path or substitute task."


__all__ = [
    "RecoveryDirective",
    "SubstituteTaskSuggestion",
    "VerificationRecoveryLadder",
]
