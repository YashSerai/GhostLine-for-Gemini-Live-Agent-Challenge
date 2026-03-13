"""Deterministic capability-failure recovery and task substitution for Prompt 35."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging
from typing import Any, Final, Literal, TypeAlias

from .flavor_text_library import get_flavor_lines
from .logging_utils import log_event
from .task_helpers import InvalidTaskIdError, get_task_by_id
from .task_library import TASK_LIBRARY, TaskDefinition

LOGGER = logging.getLogger("ghostline.backend.capability_recovery")
ForwardEnvelope = Callable[[dict[str, Any]], Awaitable[None]]

CapabilityFailureReason: TypeAlias = Literal[
    "cannot_perform_task",
    "missing_paper",
    "missing_door_or_threshold",
    "missing_required_object",
    "alternative_requested",
    "unknown_constraint",
]
CapabilityRecoveryStatus: TypeAlias = Literal[
    "clarifying_question",
    "substituted",
    "partial_handling",
]

_MAX_SWAPS_PER_STEP: Final[int] = 2
_TASK_CONTEXT_KEYS: Final[tuple[str, ...]] = (
    "capabilitySwapKey",
    "contextLabel",
    "contextStatus",
    "pathMode",
    "protocolStep",
    "taskId",
    "taskName",
    "operatorDescription",
    "taskRoleCategory",
    "taskTier",
    "verificationClass",
)

_REASON_LABELS: Final[dict[str, str]] = {
    "cannot_perform_task": "task cannot be performed",
    "missing_paper": "paper unavailable",
    "missing_door_or_threshold": "no usable door or threshold",
    "missing_required_object": "required object unavailable",
    "alternative_requested": "alternate step requested",
    "unknown_constraint": "constraint reported",
}


class CapabilityRecoveryError(ValueError):
    """Raised when capability-failure recovery receives invalid state."""


@dataclass(frozen=True)
class SubstituteTaskPayload:
    story_function: str
    substitution_group: str
    task_id: str
    task_name: str
    task_role_category: str
    task_tier: int
    verification_class: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "storyFunction": self.story_function,
            "substitutionGroup": self.substitution_group,
            "taskId": self.task_id,
            "taskName": self.task_name,
            "taskRoleCategory": self.task_role_category,
            "taskTier": self.task_tier,
            "verificationClass": self.verification_class,
        }


@dataclass(frozen=True)
class CapabilityRecoveryDirective:
    clarification_question: str | None
    constraint_label: str
    inferred_reason: CapabilityFailureReason
    operator_line: str
    original_task_context: dict[str, Any]
    status: CapabilityRecoveryStatus
    substitute_task: SubstituteTaskPayload | None
    swap_count: int
    swap_limit: int
    task_context: dict[str, Any] | None

    def to_payload(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "constraintLabel": self.constraint_label,
            "inferredReason": self.inferred_reason,
            "operatorLine": self.operator_line,
            "originalTaskContext": self.original_task_context,
            "clarifyingQuestion": self.clarification_question,
            "swapCount": self.swap_count,
            "swapLimit": self.swap_limit,
            "gracefulPartialHandling": self.status == "partial_handling",
            "substituteTask": (
                self.substitute_task.to_payload()
                if self.substitute_task is not None
                else None
            ),
            "taskContext": self.task_context,
        }


class SessionCapabilityRecoveryManager:
    """Owns deterministic Prompt 35 substitution logic for one session."""

    def __init__(
        self,
        *,
        session_id: str,
        forward_envelope: ForwardEnvelope,
    ) -> None:
        self.session_id = session_id
        self._forward_envelope = forward_envelope
        self._swap_counts: dict[str, int] = {}
        self._clarification_asked: set[str] = set()
        self._active_task_context: dict[str, Any] | None = None

    async def handle_swap_request(self, payload: dict[str, Any]) -> None:
        source = _normalize_source(payload.get("source"))
        inferred_reason = _normalize_reason(payload)
        raw_transcript_snippet = _normalize_optional_string(
            payload.get("rawTranscriptSnippet")
        )
        task_context = _build_task_context(payload.get("taskContext"), self._active_task_context)
        log_event(
            LOGGER,
            logging.INFO,
            "swap_requested",
            session_id=self.session_id,
            source=source,
            inferred_reason=inferred_reason,
            current_step=task_context.get("protocolStep"),
            task_id=task_context.get("taskId"),
            task_name=task_context.get("taskName"),
            path_mode=task_context.get("pathMode"),
            raw_transcript_snippet=raw_transcript_snippet,
        )
        swap_key = _build_swap_key(task_context, inferred_reason)
        current_task = _resolve_current_task(task_context, inferred_reason)
        current_swap_count = self._swap_counts.get(swap_key, 0)

        if current_task is None and _needs_clarifying_question(inferred_reason):
            if swap_key not in self._clarification_asked:
                self._clarification_asked.add(swap_key)
                directive = CapabilityRecoveryDirective(
                    clarification_question=(
                        "Name the blocked object or surface once. I can swap the step cleanly after that."
                    ),
                    constraint_label=_REASON_LABELS[inferred_reason],
                    inferred_reason=inferred_reason,
                    operator_line=(
                        "Name the blocked object or surface once. I can swap the step cleanly after that."
                    ),
                    original_task_context=task_context,
                    status="clarifying_question",
                    substitute_task=None,
                    swap_count=current_swap_count,
                    swap_limit=_MAX_SWAPS_PER_STEP,
                    task_context=None,
                )
                await self._emit_directive(
                    directive=directive,
                    source=source,
                    raw_transcript_snippet=raw_transcript_snippet,
                )
                return

            directive = _build_partial_handling_directive(
                inferred_reason=inferred_reason,
                operator_line=(
                    "Understood. I do not have enough clean detail to place a like-for-like substitute. "
                    "I am logging the constraint and keeping the case moving with partial handling."
                ),
                original_task_context=task_context,
                swap_count=current_swap_count,
            )
            await self._emit_directive(
                directive=directive,
                source=source,
                raw_transcript_snippet=raw_transcript_snippet,
            )
            return

        if current_task is None:
            directive = _build_partial_handling_directive(
                inferred_reason=inferred_reason,
                operator_line=(
                    "Understood. This step cannot be swapped cleanly from the current context. "
                    "I am logging the constraint and keeping the case moving with partial handling."
                ),
                original_task_context=task_context,
                swap_count=current_swap_count,
            )
            await self._emit_directive(
                directive=directive,
                source=source,
                raw_transcript_snippet=raw_transcript_snippet,
            )
            return

        if current_swap_count >= _MAX_SWAPS_PER_STEP:
            directive = _build_partial_handling_directive(
                inferred_reason=inferred_reason,
                operator_line=(
                    "Understood. I am not burning another swap on this step. "
                    "I am recording the constraint and moving the case forward with partial handling."
                ),
                original_task_context=task_context,
                swap_count=current_swap_count,
            )
            await self._emit_directive(
                directive=directive,
                source=source,
                raw_transcript_snippet=raw_transcript_snippet,
            )
            return

        substitute_task = _select_substitute(current_task)
        if substitute_task is None:
            directive = _build_partial_handling_directive(
                inferred_reason=inferred_reason,
                operator_line=(
                    "Understood. This room does not support a clean same-function substitute for that step. "
                    "I am logging the constraint and keeping the case moving with partial handling."
                ),
                original_task_context=task_context,
                swap_count=current_swap_count,
            )
            await self._emit_directive(
                directive=directive,
                source=source,
                raw_transcript_snippet=raw_transcript_snippet,
            )
            return

        next_swap_count = current_swap_count + 1
        self._swap_counts[swap_key] = next_swap_count
        self._clarification_asked.discard(swap_key)

        substitute_context = _build_substitute_task_context(
            current_task=current_task,
            original_task_context=task_context,
            substitute_task=substitute_task,
            swap_count=next_swap_count,
            swap_key=swap_key,
        )
        substitute_payload = SubstituteTaskPayload(
            story_function=substitute_task.story_function,
            substitution_group=substitute_task.substitution_group,
            task_id=substitute_task.id,
            task_name=substitute_task.name,
            task_role_category=substitute_task.role_category,
            task_tier=substitute_task.tier,
            verification_class=substitute_task.verification_class,
        )
        operator_line = _build_substitution_operator_line(
            current_task=current_task,
            inferred_reason=inferred_reason,
            substitute_task=substitute_task,
        )
        directive = CapabilityRecoveryDirective(
            clarification_question=None,
            constraint_label=_REASON_LABELS[inferred_reason],
            inferred_reason=inferred_reason,
            operator_line=operator_line,
            original_task_context=task_context,
            status="substituted",
            substitute_task=substitute_payload,
            swap_count=next_swap_count,
            swap_limit=_MAX_SWAPS_PER_STEP,
            task_context=substitute_context,
        )
        self._active_task_context = substitute_context
        await self._emit_directive(
            directive=directive,
            source=source,
            raw_transcript_snippet=raw_transcript_snippet,
        )

    async def _emit_directive(
        self,
        *,
        directive: CapabilityRecoveryDirective,
        source: str,
        raw_transcript_snippet: str | None,
    ) -> None:
        log_event(
            LOGGER,
            logging.INFO,
            "capability_recovery_decision",
            session_id=self.session_id,
            status=directive.status,
            inferred_reason=directive.inferred_reason,
            constraint_label=directive.constraint_label,
            source=source,
            swap_count=directive.swap_count,
            swap_limit=directive.swap_limit,
            original_task_id=directive.original_task_context.get("taskId"),
            substitute_task_id=(
                directive.substitute_task.task_id
                if directive.substitute_task is not None
                else None
            ),
            raw_transcript_snippet=raw_transcript_snippet,
        )
        await self._forward_envelope(
            {
                "type": "swap_request",
                "sessionId": self.session_id,
                "payload": {
                    "source": source,
                    "rawTranscriptSnippet": raw_transcript_snippet,
                    **directive.to_payload(),
                },
            }
        )
        await self._forward_envelope(
            {
                "type": "transcript",
                "sessionId": self.session_id,
                "payload": {
                    "speaker": "operator",
                    "text": directive.operator_line,
                    "isFinal": True,
                    "source": "capability_recovery",
                },
            }
        )


def _build_partial_handling_directive(
    *,
    inferred_reason: CapabilityFailureReason,
    operator_line: str,
    original_task_context: dict[str, Any],
    swap_count: int,
) -> CapabilityRecoveryDirective:
    return CapabilityRecoveryDirective(
        clarification_question=None,
        constraint_label=_REASON_LABELS[inferred_reason],
        inferred_reason=inferred_reason,
        operator_line=operator_line,
        original_task_context=original_task_context,
        status="partial_handling",
        substitute_task=None,
        swap_count=swap_count,
        swap_limit=_MAX_SWAPS_PER_STEP,
        task_context=None,
    )


def _normalize_source(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "control_bar"


def _normalize_optional_string(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _normalize_reason(payload: dict[str, Any]) -> CapabilityFailureReason:
    inferred_reason = payload.get("inferredReason")
    reason = payload.get("reason")

    for candidate in (inferred_reason, reason):
        if not isinstance(candidate, str) or not candidate.strip():
            continue
        normalized = candidate.strip()
        if normalized in _REASON_LABELS:
            return normalized  # type: ignore[return-value]
        if normalized == "cant_do_this":
            return "cannot_perform_task"

    return "unknown_constraint"


def _build_task_context(
    value: Any,
    fallback_context: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        if fallback_context is not None:
            return dict(fallback_context)
        return {
            "contextStatus": "temporary_unassigned",
            "contextLabel": (
                "TEMPORARY PROMPT 35 STUB: active task assignment is not wired yet."
            ),
        }

    task_context: dict[str, Any] = {}
    for key in _TASK_CONTEXT_KEYS:
        raw = value.get(key)
        if raw is not None:
            task_context[key] = raw

    if "contextStatus" not in task_context:
        task_context["contextStatus"] = "temporary_unassigned"
    if "contextLabel" not in task_context:
        task_context["contextLabel"] = (
            "TEMPORARY PROMPT 35 STUB: active task assignment is not wired yet."
        )
    return task_context


def _build_swap_key(
    task_context: dict[str, Any],
    inferred_reason: CapabilityFailureReason,
) -> str:
    capability_swap_key = task_context.get("capabilitySwapKey")
    if isinstance(capability_swap_key, str) and capability_swap_key.strip():
        return capability_swap_key.strip()

    protocol_step = task_context.get("protocolStep")
    path_mode = task_context.get("pathMode")
    task_id = task_context.get("taskId")

    if isinstance(protocol_step, str) and protocol_step.strip():
        return f"step:{protocol_step.strip()}::{path_mode or 'unresolved'}"
    if isinstance(task_id, str) and task_id.strip():
        return f"task:{task_id.strip()}::{path_mode or 'unresolved'}"
    return f"constraint:{inferred_reason}::{path_mode or 'unresolved'}"


def _resolve_current_task(
    task_context: dict[str, Any],
    inferred_reason: CapabilityFailureReason,
) -> TaskDefinition | None:
    task_id = task_context.get("taskId")
    if isinstance(task_id, str) and task_id.strip():
        try:
            return get_task_by_id(task_id.strip())
        except InvalidTaskIdError:
            return None

    if inferred_reason == "missing_door_or_threshold":
        return get_task_by_id("T1")

    return None


def _needs_clarifying_question(inferred_reason: CapabilityFailureReason) -> bool:
    return inferred_reason in {
        "cannot_perform_task",
        "missing_paper",
        "missing_required_object",
        "alternative_requested",
        "unknown_constraint",
    }


def _select_substitute(current_task: TaskDefinition) -> TaskDefinition | None:
    candidates = [
        task
        for task in TASK_LIBRARY
        if task.id != current_task.id and task.story_function == current_task.story_function
    ]
    if not candidates:
        return None

    ordered_candidates = sorted(
        candidates,
        key=lambda task: (
            0 if task.substitution_group == current_task.substitution_group else 1,
            0 if task.tier <= current_task.tier else 1,
            abs(task.tier - current_task.tier),
            task.id,
        ),
    )
    return ordered_candidates[0]


def _build_substitute_task_context(
    *,
    current_task: TaskDefinition,
    original_task_context: dict[str, Any],
    substitute_task: TaskDefinition,
    swap_count: int,
    swap_key: str,
) -> dict[str, Any]:
    substitute_context = dict(original_task_context)
    substitute_context.update(
        {
            "capabilitySwapKey": swap_key,
            "contextStatus": "capability_substituted",
            "contextLabel": (
                f"Capability recovery substituted {current_task.name} with {substitute_task.name}."
            ),
            "swapCount": swap_count,
            "taskId": substitute_task.id,
            "taskName": substitute_task.name,
            "operatorDescription": substitute_task.operator_description,
            "taskRoleCategory": substitute_task.role_category,
            "taskTier": substitute_task.tier,
            "verificationClass": substitute_task.verification_class,
        }
    )
    return substitute_context


def _build_substitution_operator_line(
    *,
    current_task: TaskDefinition,
    inferred_reason: CapabilityFailureReason,
    substitute_task: TaskDefinition,
) -> str:
    occasion = _resolve_swap_occasion(inferred_reason)
    lines = get_flavor_lines("swap_task_response", occasion=occasion)
    if not lines:
        lines = get_flavor_lines("swap_task_response", occasion="general")

    opener = (
        lines[0].text
        if lines
        else "Understood. I am routing to a cleaner substitute."
    )
    return (
        f"{opener} Use {substitute_task.name} instead. "
        f"It preserves the {current_task.story_function} function with a cleaner fit for this room."
    )


def _resolve_swap_occasion(inferred_reason: CapabilityFailureReason) -> str:
    if inferred_reason in {"missing_paper", "missing_required_object"}:
        return "missing_object"
    if inferred_reason in {"missing_door_or_threshold", "cannot_perform_task"}:
        return "capability_mismatch"
    return "general"


__all__ = [
    "CapabilityRecoveryDirective",
    "CapabilityRecoveryError",
    "SessionCapabilityRecoveryManager",
    "SubstituteTaskPayload",
]






