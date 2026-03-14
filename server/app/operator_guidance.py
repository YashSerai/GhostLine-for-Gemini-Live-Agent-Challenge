"""Deterministic live operator guidance orchestration for normal mode."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Literal, TypeAlias

from .flavor_text_state_model import FlavorTextStateModel
from .task_helpers import InvalidTaskIdError, get_task_by_id

OperatorGuidanceBeat: TypeAlias = Literal[
    "microphone_request",
    "camera_request",
    "room_sweep",
    "calibration_acknowledged",
    "task_assignment",
    "verification_reaction",
    "final_closure",
]

BACKEND_AUTHORED_TRANSCRIPT_SOURCES: Final[frozenset[str]] = frozenset(
    {
        "session_guidance",
        "operator_guidance",
        "demo_mode",
        "verification_flow",
        "recovery_ladder",
        "capability_recovery",
    }
)
REACTIVE_FILLER_ALLOWED_STATES: Final[frozenset[str]] = frozenset(
    {
        "waiting_ready",
        "diagnosis_beat",
        "recovery_active",
    }
)
_LOW_CONTEXT_PATH_MODES: Final[frozenset[str]] = frozenset({"low_visibility"})


@dataclass(frozen=True)
class OperatorGuidanceDirective:
    beat: OperatorGuidanceBeat
    text: str
    source: str = "operator_guidance"


class NormalModeOperatorGuidanceOrchestrator:
    """Owns deterministic, authored normal-mode spoken guidance beats."""

    def __init__(
        self,
        *,
        session_id: str,
        flavor_model: FlavorTextStateModel,
    ) -> None:
        self.session_id = session_id
        self._flavor_model = flavor_model
        self._last_state: str | None = None
        self._last_task_id_announced: str | None = None
        self._last_verification_attempt_id: str | None = None
        self._last_case_report_id: str | None = None
        self._last_calibration_captured_at: str | None = None

    def consume_envelope(
        self,
        envelope: dict[str, Any],
    ) -> tuple[OperatorGuidanceDirective, ...]:
        message_type = envelope.get("type")
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            return ()

        if message_type == "session_state":
            return self._build_state_guidance(payload)
        if message_type == "verification_result":
            directive = self._build_verification_reaction(payload)
            return (directive,) if directive is not None else ()
        return ()

    def build_microphone_request_guidance(self) -> OperatorGuidanceDirective:
        return OperatorGuidanceDirective(
            beat="microphone_request",
            text=(
                "Thank you for calling Ghostline. Stay with me and follow my instructions exactly. "
                "To hear you clearly, I need microphone access now."
            ),
        )

    def build_camera_request_guidance(self) -> OperatorGuidanceDirective:
        return OperatorGuidanceDirective(
            beat="camera_request",
            text=(
                "Good. Since you placed this call, I am treating the room as an active containment case. "
                "You sound unsettled, so I am going to drive this. Grant camera access now so I can see the surrounding space."
            ),
        )

    def build_room_sweep_guidance(self) -> OperatorGuidanceDirective:
        return OperatorGuidanceDirective(
            beat="room_sweep",
            text=(
                "Good. Pan slowly across the room once. Show me the doorway, the nearest boundary, and any clear surface you can use. "
                "Then keep the phone level and tap Finish Sweep plus Calibrate once so I can lock the first containment step."
            ),
        )

    def build_calibration_acknowledgement(self) -> OperatorGuidanceDirective:
        return OperatorGuidanceDirective(
            beat="calibration_acknowledged",
            text=(
                "That is enough room context. Calibration is locked. I am placing the first containment step now."
            ),
        )

    def build_task_assignment_guidance(
        self,
        task_context: dict[str, Any] | None,
        *,
        active_task_index: int | None = None,
    ) -> OperatorGuidanceDirective | None:
        if not isinstance(task_context, dict):
            return None

        task_name = _string_or_none(task_context.get("taskName"))
        if task_name is None:
            return None

        operator_description = _string_or_none(task_context.get("operatorDescription"))
        if operator_description is None:
            task_id = _string_or_none(task_context.get("taskId"))
            if task_id is not None:
                try:
                    operator_description = get_task_by_id(task_id).operator_description
                except InvalidTaskIdError:
                    operator_description = None

        detail = (
            operator_description
            if operator_description is not None
            else "Perform the current containment step once, keep the frame readable, then stop."
        )
        instruction_lead = "First task" if active_task_index == 0 else "Next task"
        completion_signal = (
            "When this step is complete, stop moving, say Ready to Verify, or press the Ready to Verify button."
        )
        low_context_follow_up = _build_low_context_follow_up(task_context)
        if low_context_follow_up is not None:
            completion_signal = f"{completion_signal} {low_context_follow_up}"

        return OperatorGuidanceDirective(
            beat="task_assignment",
            text=(
                f"{instruction_lead}: {task_name}. Exact action: {detail} "
                f"{completion_signal}"
            ),
        )

    def _build_state_guidance(
        self,
        payload: dict[str, Any],
    ) -> tuple[OperatorGuidanceDirective, ...]:
        directives: list[OperatorGuidanceDirective] = []
        state_name = _string_or_none(payload.get("state"))
        task_context = payload.get("currentTaskContext")
        case_report = payload.get("caseReport")
        active_task_index = _int_or_none(payload.get("activeTaskIndex"))
        calibration_captured_at = _string_or_none(payload.get("calibrationCapturedAt"))

        if state_name == "microphone_request" and self._last_state != "microphone_request":
            directives.append(self.build_microphone_request_guidance())

        if state_name == "camera_request" and self._last_state != "camera_request":
            directives.append(self.build_camera_request_guidance())

        if state_name == "room_sweep" and self._last_state != "room_sweep":
            directives.append(self.build_room_sweep_guidance())

        if (
            calibration_captured_at is not None
            and calibration_captured_at != self._last_calibration_captured_at
        ):
            directives.append(self.build_calibration_acknowledgement())
            self._last_calibration_captured_at = calibration_captured_at

        task_id = (
            _string_or_none(task_context.get("taskId"))
            if isinstance(task_context, dict)
            else None
        )
        if (
            state_name in {"task_assigned", "waiting_ready"}
            and task_id is not None
            and task_id != self._last_task_id_announced
        ):
            task_guidance = self.build_task_assignment_guidance(
                task_context,
                active_task_index=active_task_index,
            )
            if task_guidance is not None:
                directives.append(task_guidance)
                self._last_task_id_announced = task_id

        if state_name in {"case_report", "ended"}:
            closure_directive = self._build_final_closure(case_report)
            if closure_directive is not None:
                directives.append(closure_directive)

        self._last_state = state_name
        return tuple(directives)

    def _build_verification_reaction(
        self,
        payload: dict[str, Any],
    ) -> OperatorGuidanceDirective | None:
        attempt_id = _string_or_none(payload.get("attemptId"))
        if attempt_id is not None and attempt_id == self._last_verification_attempt_id:
            return None
        if attempt_id is not None:
            self._last_verification_attempt_id = attempt_id

        status = _string_or_none(payload.get("status"))
        if status == "confirmed":
            selection = self._flavor_model.select_flavor_line(
                self.session_id,
                "verification_success",
                preferred_category="post_verification_reaction",
                occasion="confirmed",
            )
        elif status == "user_confirmed_only":
            selection = self._flavor_model.select_flavor_line(
                self.session_id,
                "verification_success",
                preferred_category="post_verification_reaction",
                occasion="user_confirmed_only",
            )
        elif status == "unconfirmed":
            selection = self._flavor_model.select_flavor_line(
                self.session_id,
                "verification_failure",
                preferred_category="post_verification_reaction",
                occasion="unconfirmed",
            )
        else:
            return None

        if selection is None:
            return None

        current_path_mode = _string_or_none(payload.get("currentPathMode"))
        confidence_band = _string_or_none(payload.get("confidenceBand"))
        task_context = payload.get("taskContext")
        low_context_follow_up = _build_weak_confidence_follow_up(
            status=status,
            confidence_band=confidence_band,
            current_path_mode=current_path_mode,
            task_context=task_context if isinstance(task_context, dict) else None,
        )
        text = selection.text
        if low_context_follow_up is not None:
            text = f"{text} {low_context_follow_up}"

        return OperatorGuidanceDirective(
            beat="verification_reaction",
            text=text,
        )

    def _build_final_closure(
        self,
        case_report: Any,
    ) -> OperatorGuidanceDirective | None:
        if not isinstance(case_report, dict):
            return None

        case_id = _string_or_none(case_report.get("caseId"))
        if case_id is None or case_id == self._last_case_report_id:
            return None
        self._last_case_report_id = case_id

        closing_template = case_report.get("closingTemplate")
        if isinstance(closing_template, dict):
            closing_line = _string_or_none(closing_template.get("closingLine"))
            if closing_line is not None:
                return OperatorGuidanceDirective(
                    beat="final_closure",
                    text=closing_line,
                )

        selection = self._flavor_model.select_flavor_line(
            self.session_id,
            "final_closure",
            preferred_category="final_closure",
            occasion="contained",
        )
        if selection is None:
            return None
        return OperatorGuidanceDirective(
            beat="final_closure",
            text=selection.text,
        )


def _build_low_context_follow_up(task_context: dict[str, Any]) -> str | None:
    path_mode = _string_or_none(task_context.get("pathMode"))
    if path_mode not in _LOW_CONTEXT_PATH_MODES:
        return None

    return (
        "Before you move, answer one thing plainly: "
        f"{_select_grounding_question(task_context)}"
    )


def _build_weak_confidence_follow_up(
    *,
    status: str,
    confidence_band: str | None,
    current_path_mode: str | None,
    task_context: dict[str, Any] | None,
) -> str | None:
    weak_confidence = confidence_band in {"low", "medium"}
    low_visibility = current_path_mode in _LOW_CONTEXT_PATH_MODES
    if not weak_confidence and not low_visibility:
        return None

    if status == "user_confirmed_only":
        if isinstance(task_context, dict):
            return f"Answer one thing plainly before I route the next step: {_select_grounding_question(task_context)}"
        return "Answer one thing plainly before I route the next step: Where is it strongest?"

    return None


def _select_grounding_question(task_context: dict[str, Any]) -> str:
    protocol_step = _string_or_none(task_context.get("protocolStep")) or ""
    task_name = _string_or_none(task_context.get("taskName")) or ""
    operator_description = _string_or_none(task_context.get("operatorDescription")) or ""
    task_basis = f"{protocol_step} {task_name} {operator_description}".lower()

    if any(token in task_basis for token in ("boundary", "threshold", "door", "doorway", "assess_boundary")):
        return "Is there a doorway in front of you?"
    if any(token in task_basis for token in ("surface", "table", "desk", "counter", "anchor", "mark_or_substitute")):
        return "What flat surface is available?"
    if any(token in task_basis for token in ("light", "illumination", "bright")):
        return "Did the sound change when the light changed?"
    return "Where is it strongest?"


def _string_or_none(value: Any) -> str | None:
    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            return normalized
    return None


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None
