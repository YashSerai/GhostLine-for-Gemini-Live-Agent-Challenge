"""Authoritative full-session state machine for Prompt 36."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
import logging
from typing import Any, Literal, Protocol

from .case_report import build_case_report_artifact
from .capability_profile import (
    ObservedAffordances,
    QualityMetrics,
    UserDeclaredConstraints,
    build_capability_profile,
)
from .incident_classification import (
    IncidentClassificationContext,
    IncidentClassificationStore,
    classify_incident,
)
from .logging_utils import log_event
from .protocol_planner import ProtocolPlan, build_protocol_plan

LOGGER = logging.getLogger("ghostline.backend.session_state")

ForwardEnvelope = Callable[[dict[str, Any]], Awaitable[None]]
SessionStateName = Literal[
    "init",
    "call_connected",
    "consent",
    "camera_request",
    "calibration",
    "task_assigned",
    "waiting_ready",
    "verifying",
    "diagnosis_beat",
    "recovery_active",
    "swap_pending",
    "paused",
    "completed",
    "case_report",
    "ended",
]
TurnStatus = Literal["idle", "speaking", "listening", "interrupted"]


class SessionPersistenceStore(Protocol):
    async def create_session_document(
        self,
        session_id: str,
        snapshot: dict[str, Any],
    ) -> bool: ...

    async def persist_session_snapshot(
        self,
        session_id: str,
        snapshot: dict[str, Any],
    ) -> bool: ...


_ALLOWED_TRANSITIONS: dict[SessionStateName, tuple[SessionStateName, ...]] = {
    "init": ("call_connected", "ended"),
    "call_connected": ("consent", "ended"),
    "consent": ("camera_request", "ended"),
    "camera_request": ("calibration", "paused", "ended"),
    "calibration": ("camera_request", "task_assigned", "paused", "ended"),
    "task_assigned": ("camera_request", "waiting_ready", "swap_pending", "paused", "ended"),
    "waiting_ready": ("camera_request", "verifying", "swap_pending", "paused", "ended"),
    "verifying": ("camera_request", "diagnosis_beat", "recovery_active", "paused", "ended"),
    "diagnosis_beat": ("camera_request", "task_assigned", "completed", "case_report", "paused", "ended"),
    "recovery_active": ("camera_request", "waiting_ready", "swap_pending", "paused", "ended"),
    "swap_pending": ("camera_request", "task_assigned", "waiting_ready", "diagnosis_beat", "completed", "case_report", "paused", "ended"),
    "paused": (
        "camera_request",
        "calibration",
        "task_assigned",
        "waiting_ready",
        "verifying",
        "diagnosis_beat",
        "recovery_active",
        "swap_pending",
        "completed",
        "case_report",
        "ended",
    ),
    "completed": ("case_report", "ended"),
    "case_report": ("ended",),
    "ended": (),
}

_ALLOWED_VERIFY_STATES = frozenset({"waiting_ready", "recovery_active"})
_ALLOWED_SWAP_STATES = frozenset({"task_assigned", "waiting_ready", "recovery_active", "swap_pending"})
_ALLOWED_PAUSE_STATES = frozenset(
    {
        "camera_request",
        "calibration",
        "task_assigned",
        "waiting_ready",
        "verifying",
        "diagnosis_beat",
        "recovery_active",
        "swap_pending",
    }
)
_MAX_HISTORY = 12


class SessionStateMachineError(ValueError):
    """Raised when the session state machine rejects a transition or action."""


class SessionStateMachine:
    """Owns authoritative session state and legal transitions for one call."""

    def __init__(
        self,
        *,
        session_id: str,
        forward_envelope: ForwardEnvelope,
        incident_store: IncidentClassificationStore | None = None,
        session_store: SessionPersistenceStore | None = None,
    ) -> None:
        self.session_id = session_id
        self._forward_envelope = forward_envelope
        self._incident_store = incident_store
        self._session_store = session_store
        self._session_document_created = False
        self.state: SessionStateName = "init"
        self.resume_state: SessionStateName | None = None
        self.plan: ProtocolPlan | None = None
        self.active_task_index = -1
        self.current_task_context: dict[str, Any] | None = None
        self.current_step: str | None = None
        self.current_path_mode: str | None = None
        self.classification_label: str | None = None
        self.classification_reason: str | None = None
        self.case_report_generated_at: str | None = None
        self.case_report_payload: dict[str, Any] | None = None
        self._last_emitted_case_report_id: str | None = None
        self.final_verdict: str | None = None
        self.swap_count = 0
        self.recovery_step: str | None = None
        self.recovery_attempt_count: int | None = None
        self.recovery_attempt_limit: int | None = None
        self.recovery_reroute_required = False
        self.verification_status: str | None = None
        self.block_reason: str | None = None
        self.last_verified_item: str | None = None
        self.turn_status: TurnStatus = "idle"
        self.interruption_count = 0
        self.camera_ready = False
        self.camera_width: int | None = None
        self.camera_height: int | None = None
        self.microphone_streaming = False
        self.transcript_references: list[dict[str, Any]] = []
        self.task_history: list[dict[str, Any]] = []
        self.verification_history: list[dict[str, Any]] = []
        self.transition_history: list[dict[str, Any]] = []
        self.ended_reason: str | None = None

    async def handle_client_connect(self) -> None:
        self._transition("call_connected", "client_connect")
        self._transition("consent", "hotline_connected")
        self._transition("camera_request", "in_call_permission_flow")
        self._log_cloud_proof_event(
            "session_started",
            current_step=self.current_step,
            planned_task_count=(len(self.plan.selected_tasks) if self.plan is not None else 0),
        )
        await self._create_session_document()
        await self.emit_snapshot(persist=False)

    async def handle_camera_status(self, payload: dict[str, Any]) -> None:
        permission = payload.get("permission")
        preview = payload.get("preview")
        self.camera_ready = permission == "granted" and preview is True
        self.camera_width = _int_or_none(payload.get("width")) if self.camera_ready else None
        self.camera_height = _int_or_none(payload.get("height")) if self.camera_ready else None

        if self.state != "paused":
            if self.camera_ready and self.state == "camera_request":
                self._transition("calibration", "camera_ready")
            elif not self.camera_ready and self.state in {
                "calibration",
                "task_assigned",
                "waiting_ready",
                "verifying",
                "diagnosis_beat",
                "recovery_active",
                "swap_pending",
            }:
                self._transition("camera_request", "camera_lost")

        await self.emit_snapshot()

    async def handle_mic_status(self, payload: dict[str, Any]) -> None:
        self.microphone_streaming = payload.get("streaming") is True

        if self.microphone_streaming and self.state == "calibration":
            self._assign_next_task("mic_stream_ready")
            self._transition("waiting_ready", "task_staged")

        await self.emit_snapshot()

    def prepare_verification_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.state not in _ALLOWED_VERIFY_STATES:
            raise SessionStateMachineError(
                f"Ready to Verify is not legal from state {self.state}."
            )
        if self.current_task_context is None:
            raise SessionStateMachineError(
                "Ready to Verify requires an active assigned task."
            )

        next_payload = dict(payload)
        next_payload["taskContext"] = dict(self.current_task_context)
        return next_payload

    def begin_verification_request(self) -> SessionStateName:
        previous_state = self.state
        self._transition("verifying", "verify_request")
        return previous_state

    def prepare_swap_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.state not in _ALLOWED_SWAP_STATES:
            raise SessionStateMachineError(
                f"Swap is not legal from state {self.state}."
            )
        if self.current_task_context is None:
            raise SessionStateMachineError(
                "Swap requires an active assigned task."
            )

        next_payload = dict(payload)
        next_payload["taskContext"] = dict(self.current_task_context)
        return next_payload

    def begin_swap_request(self) -> SessionStateName:
        previous_state = self.state
        self._transition("swap_pending", "swap_request")
        return previous_state

    def rollback(self, previous_state: SessionStateName, expected_state: SessionStateName) -> None:
        if self.state != expected_state or not self.transition_history:
            return
        last_transition = self.transition_history[-1]
        if last_transition.get("to") == expected_state:
            self.transition_history.pop()
        self.state = previous_state

    async def handle_pause_request(self, payload: dict[str, Any]) -> None:
        paused = payload.get("paused")
        if paused is True:
            if self.state == "paused":
                raise SessionStateMachineError("Session is already paused.")
            if self.state not in _ALLOWED_PAUSE_STATES:
                raise SessionStateMachineError(
                    f"Pause is not legal from state {self.state}."
                )
            self.resume_state = self._resolve_pause_resume_state()
            self._transition("paused", "pause_requested")
            self._log_cloud_proof_event(
                "session_paused",
                resume_state=self.resume_state,
            )
        elif paused is False:
            if self.state != "paused":
                raise SessionStateMachineError("Session is not paused.")
            resume_target = self.resume_state or "camera_request"
            self.resume_state = None
            self._transition(resume_target, "pause_cleared")
        else:
            raise SessionStateMachineError(
                "Pause payload must include paused=true or paused=false."
            )

        await self.emit_snapshot()

    async def handle_stop_request(self, reason: str) -> None:
        self.ended_reason = reason
        if self.state != "ended":
            self._transition("ended", reason)
        self._log_cloud_proof_event(
            "session_ended",
            ended_reason=reason,
            final_verdict=self._derive_final_verdict(),
        )
        await self.emit_snapshot()

    def observe_outbound_envelope(self, envelope: dict[str, Any]) -> bool:
        message_type = envelope.get("type")
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            return False

        if message_type == "transcript":
            return self._observe_transcript(payload)
        if message_type == "operator_audio_chunk":
            if self.turn_status != "speaking":
                self.turn_status = "speaking"
                return True
            return False
        if message_type == "operator_interruption":
            self.turn_status = "interrupted"
            self.interruption_count += 1
            return True
        if message_type == "verification_result":
            self._observe_verification_result(payload)
            return True
        if message_type == "swap_request":
            return self._observe_swap_outcome(payload)
        return False

    async def emit_snapshot(self, *, persist: bool = True) -> None:
        snapshot = self.to_payload()
        if persist:
            await self._persist_session_snapshot(snapshot)
        case_report = snapshot.get("caseReport")
        if isinstance(case_report, dict):
            report_id = _string_or_none(case_report.get("caseId"))
            if report_id is not None and report_id != self._last_emitted_case_report_id:
                self._last_emitted_case_report_id = report_id
                await self._forward_envelope(
                    {
                        "type": "case_report",
                        "sessionId": self.session_id,
                        "payload": case_report,
                    }
                )
        await self._forward_envelope(
            {
                "type": "session_state",
                "sessionId": self.session_id,
                "payload": snapshot,
            }
        )

    def to_payload(self) -> dict[str, Any]:
        self._ensure_case_report_generated()
        planned_tasks = []
        protocol_mapping = []
        if self.plan is not None:
            planned_tasks = [
                {
                    "taskId": task.id,
                    "taskName": task.name,
                    "taskTier": task.tier,
                    "taskRoleCategory": task.role_category,
                }
                for task in self.plan.selected_tasks
            ]
            protocol_mapping = [
                {
                    "step": assignment.step,
                    "taskId": assignment.task_id,
                    "reason": assignment.reason,
                    "usesSubstitute": assignment.uses_substitute,
                }
                for assignment in self.plan.protocol_step_mapping
            ]

        return {
            "state": self.state,
            "resumeState": self.resume_state,
            "currentStep": self.current_step,
            "currentTaskContext": self.current_task_context,
            "plannedTasks": planned_tasks,
            "protocolStepMapping": protocol_mapping,
            "activeTaskIndex": self.active_task_index,
            "taskHistory": self.task_history[-_MAX_HISTORY:],
            "verificationHistory": self.verification_history[-_MAX_HISTORY:],
            "classificationLabel": self.classification_label,
            "classificationReason": self.classification_reason,
            "swapCount": self.swap_count,
            "recoveryStep": self.recovery_step,
            "recoveryAttemptCount": self.recovery_attempt_count,
            "recoveryAttemptLimit": self.recovery_attempt_limit,
            "recoveryRerouteRequired": self.recovery_reroute_required,
            "verificationStatus": self.verification_status,
            "blockReason": self.block_reason,
            "lastVerifiedItem": self.last_verified_item,
            "currentPathMode": self.current_path_mode,
            "turnStatus": self.turn_status,
            "interruptionCount": self.interruption_count,
            "cameraReady": self.camera_ready,
            "microphoneStreaming": self.microphone_streaming,
            "transcriptReferences": self.transcript_references[-_MAX_HISTORY:],
            "transitionHistory": self.transition_history[-_MAX_HISTORY:],
            "allowedActions": self._build_allowed_actions(),
            "endedReason": self.ended_reason,
            "caseReport": self.case_report_payload,
            "finalVerdict": self.final_verdict or self._derive_final_verdict(),
        }

    def _observe_transcript(self, payload: dict[str, Any]) -> bool:
        text = payload.get("text")
        if not isinstance(text, str) or not text.strip():
            return False

        is_final = payload.get("isFinal") is True
        if not is_final:
            return False

        speaker = payload.get("speaker")
        if speaker == "user":
            self.turn_status = "listening"
        elif speaker == "operator":
            self.turn_status = "speaking"

        self.transcript_references.append(
            {
                "at": _utc_now_iso(),
                "speaker": speaker,
                "text": text.strip(),
                "source": payload.get("source"),
            }
        )
        self.transcript_references = self.transcript_references[-20:]
        return True

    def _observe_verification_result(self, payload: dict[str, Any]) -> None:
        task_context = payload.get("taskContext")
        if isinstance(task_context, dict):
            self.current_task_context = _normalize_task_context(task_context)

        attempt_id = _string_or_none(payload.get("attemptId"))
        confidence_band = _string_or_none(payload.get("confidenceBand"))
        self.verification_status = _string_or_none(payload.get("status"))
        self.block_reason = _string_or_none(payload.get("blockReason"))
        self.last_verified_item = _string_or_none(payload.get("lastVerifiedItem"))
        self.current_path_mode = (
            _string_or_none(payload.get("currentPathMode")) or self.current_path_mode
        )
        self.recovery_step = _string_or_none(payload.get("recoveryStep"))
        self.recovery_attempt_count = _int_or_none(payload.get("recoveryAttemptCount"))
        self.recovery_attempt_limit = _int_or_none(payload.get("recoveryAttemptLimit"))
        self.recovery_reroute_required = payload.get("recoveryRerouteRequired") is True
        self.verification_history.append(
            {
                "at": _utc_now_iso(),
                "attemptId": attempt_id,
                "status": self.verification_status,
                "taskId": _task_context_value(self.current_task_context, "taskId"),
                "blockReason": self.block_reason,
                "confidenceBand": confidence_band,
                "currentPathMode": self.current_path_mode,
            }
        )
        self._log_cloud_proof_event(
            "verification_result",
            verification_attempt_id=attempt_id,
            confidence_band=confidence_band,
            block_reason=self.block_reason,
            last_verified_item=self.last_verified_item,
        )

        if self.verification_status == "unconfirmed":
            self._record_task_history("unconfirmed", "verification_failed")
            self._transition("recovery_active", "verification_unconfirmed")
            return

        if self.verification_status not in {"confirmed", "user_confirmed_only"}:
            return

        self._record_task_history(self.verification_status, "verification_resolved")
        self._update_incident_classification()
        if self._has_remaining_tasks():
            self._transition("diagnosis_beat", "verification_success")
            self._assign_next_task("planner_progression")
            self._transition("waiting_ready", "task_staged")
            return

        self._transition("completed", "plan_complete")
        self._transition("case_report", "case_report_ready")

    def _observe_swap_outcome(self, payload: dict[str, Any]) -> bool:
        status = payload.get("status")
        if status == "detected":
            return False

        self.swap_count = _int_or_none(payload.get("swapCount")) or self.swap_count

        if status == "clarifying_question":
            self.recovery_step = _string_or_none(payload.get("clarifyingQuestion")) or _string_or_none(payload.get("operatorLine"))
            return True

        if status == "substituted":
            task_context = payload.get("taskContext")
            if isinstance(task_context, dict):
                self.current_task_context = _normalize_task_context(task_context)
            self._record_task_history("substituted", "capability_recovery")
            self._transition("task_assigned", "task_substituted")
            self._transition("waiting_ready", "substitute_ready")
            return True

        if status == "partial_handling":
            self._record_task_history("partial_handling", "capability_recovery")
            if self._has_remaining_tasks():
                self._transition("diagnosis_beat", "partial_handling_progression")
                self._assign_next_task("planner_progression")
                self._transition("waiting_ready", "task_staged")
            else:
                self._transition("completed", "partial_handling_terminal")
                self._transition("case_report", "case_report_ready")
            return True

        return False

    async def _create_session_document(self) -> None:
        if self._session_document_created or self._session_store is None:
            return

        created = await self._session_store.create_session_document(
            self.session_id,
            self.to_payload(),
        )
        if created:
            self._session_document_created = True

    async def _persist_session_snapshot(self, snapshot: dict[str, Any]) -> None:
        if self._session_store is None:
            return

        if not self._session_document_created:
            await self._create_session_document()
            if not self._session_document_created:
                return

        await self._session_store.persist_session_snapshot(self.session_id, snapshot)

    def _ensure_plan(self) -> None:
        if self.plan is not None:
            return

        profile = self._build_live_capability_profile()
        self.plan = build_protocol_plan(profile)
        self.current_path_mode = profile.environment.path_mode

    def _build_live_capability_profile(self):
        transcript_lines = self._recent_user_transcript_lines()
        lowered_lines = tuple(line.lower() for line in transcript_lines)
        observed_affordances = ObservedAffordances(
            threshold_available=_infer_positive_affordance(lowered_lines, ("door", "doorway", "threshold", "hallway", "entry")),
            flat_surface_available=_infer_positive_affordance(lowered_lines, ("table", "desk", "counter", "shelf", "flat surface")),
            paper_available=_infer_positive_affordance(lowered_lines, ("paper", "notebook", "page", "receipt", "index card")),
            light_controllable=_infer_positive_affordance(lowered_lines, ("lamp", "light switch", "overhead light", "flashlight")),
            reflective_surface_available=_infer_positive_affordance(lowered_lines, ("mirror", "glass", "window", "screen")),
            water_source_nearby=_infer_positive_affordance(lowered_lines, ("sink", "faucet", "water", "bowl", "cup")),
        )
        user_constraints = UserDeclaredConstraints(
            cannot_use_threshold=_contains_any(lowered_lines, ("no door", "no threshold", "cannot use the door", "can't use the door")),
            no_flat_surface=_contains_any(lowered_lines, ("no table", "no counter", "no desk", "no flat surface")),
            no_paper=_contains_any(lowered_lines, ("no paper", "dont have paper", "don't have paper")),
            cannot_adjust_light=_contains_any(lowered_lines, ("cannot adjust light", "can't adjust light", "light won't", "lights wont")),
            no_reflective_surface=_contains_any(lowered_lines, ("no mirror", "no reflective", "no glass")),
            no_water_source=_contains_any(lowered_lines, ("no water", "no sink", "no faucet")),
            notes=tuple(self._build_constraint_notes(lowered_lines)),
        )
        quality_metrics = self._build_session_quality_metrics()
        return build_capability_profile(
            observed_affordances=observed_affordances,
            quality_metrics=quality_metrics,
            user_constraints=user_constraints,
        )

    def _build_session_quality_metrics(self) -> QualityMetrics:
        if not self.camera_ready:
            return QualityMetrics(lighting=0.28, blur=0.58, motion_stability=0.35)

        width = self.camera_width or 0
        height = self.camera_height or 0
        if width >= 1280 or height >= 720:
            return QualityMetrics(lighting=0.72, blur=0.24, motion_stability=0.7)
        if width >= 960 or height >= 540:
            return QualityMetrics(lighting=0.62, blur=0.32, motion_stability=0.64)
        return QualityMetrics(lighting=0.52, blur=0.4, motion_stability=0.56)

    def _recent_user_transcript_lines(self) -> tuple[str, ...]:
        return tuple(
            reference["text"]
            for reference in self.transcript_references[-6:]
            if reference.get("speaker") == "user" and isinstance(reference.get("text"), str)
        )

    def _build_constraint_notes(self, lowered_lines: tuple[str, ...]) -> list[str]:
        notes: list[str] = []
        if _contains_any(lowered_lines, ("no door", "no threshold", "cannot use the door", "can't use the door")):
            notes.append("user declared no usable threshold")
        if _contains_any(lowered_lines, ("no table", "no counter", "no desk", "no flat surface")):
            notes.append("user declared no flat surface")
        if _contains_any(lowered_lines, ("no paper", "dont have paper", "don't have paper")):
            notes.append("user declared no paper")
        if _contains_any(lowered_lines, ("cannot adjust light", "can't adjust light", "light won't", "lights wont")):
            notes.append("user declared lighting cannot be adjusted")
        if _contains_any(lowered_lines, ("no mirror", "no reflective", "no glass")):
            notes.append("user declared no reflective surface")
        if _contains_any(lowered_lines, ("no water", "no sink", "no faucet")):
            notes.append("user declared no water source")
        return notes

    def _assign_next_task(self, reason: str) -> None:
        self._ensure_plan()
        if self.plan is None:
            return

        next_index = self.active_task_index + 1
        if next_index >= len(self.plan.selected_tasks):
            self.current_task_context = None
            self.current_step = None
            return

        task = self.plan.selected_tasks[next_index]
        assignment = next(
            (
                item
                for item in self.plan.protocol_step_mapping
                if item.task_id == task.id
            ),
            None,
        )
        self.active_task_index = next_index
        self.current_step = assignment.step if assignment is not None else None
        self.current_task_context = {
            "contextLabel": f"Planner assigned {task.name}.",
            "contextStatus": "planner_assigned",
            "pathMode": self.current_path_mode,
            "protocolStep": self.current_step,
            "taskId": task.id,
            "taskName": task.name,
            "operatorDescription": task.operator_description,
            "taskRoleCategory": task.role_category,
            "taskTier": task.tier,
            "verificationClass": task.verification_class,
            "swapCount": self.swap_count,
        }
        self.recovery_step = None
        self.recovery_attempt_count = None
        self.recovery_attempt_limit = None
        self.recovery_reroute_required = False
        self.verification_status = None
        self.block_reason = None
        self._record_task_history("assigned", reason)
        self._transition("task_assigned", reason)
        self._log_cloud_proof_event(
            "task_assigned",
            assignment_reason=reason,
            active_task_index=self.active_task_index,
            task_tier=task.tier,
            task_role_category=task.role_category,
            verification_class=task.verification_class,
        )

    def _update_incident_classification(self) -> None:
        if self._incident_store is None:
            return

        transcript_lines = tuple(
            reference["text"]
            for reference in self.transcript_references[-6:]
            if reference.get("speaker") == "user"
        )
        decision = classify_incident(
            IncidentClassificationContext(
                path_mode=self.current_path_mode,
                user_descriptions=transcript_lines,
                latest_verification_status=self.verification_status,
            )
        )
        self._incident_store.set_primary_label(self.session_id, decision)
        self.classification_label = decision.display_label
        self.classification_reason = decision.reason

    def _build_allowed_actions(self) -> dict[str, bool]:
        return {
            "canVerify": self.state in _ALLOWED_VERIFY_STATES,
            "canSwap": self.state in _ALLOWED_SWAP_STATES,
            "canPause": self.state in _ALLOWED_PAUSE_STATES,
            "canResume": self.state == "paused",
            "canEnd": self.state != "ended",
        }

    def _resolve_pause_resume_state(self) -> SessionStateName:
        if self.state != "verifying":
            return self.state
        if self.recovery_step is not None or self.recovery_attempt_count is not None:
            return "recovery_active"
        return "waiting_ready"
    def _ensure_case_report_generated(self) -> None:
        if self.state not in {"completed", "case_report", "ended"}:
            return
        if self.case_report_payload is not None:
            return

        artifact = build_case_report_artifact(
            session_id=self.session_id,
            plan=self.plan,
            active_task_index=self.active_task_index,
            current_task_context=self.current_task_context,
            task_history=self.task_history,
            verification_history=self.verification_history,
            classification_label=self.classification_label,
            generated_at=self.case_report_generated_at,
            state=self.state,
        )
        self.case_report_generated_at = artifact.generated_at
        self.case_report_payload = artifact.to_payload()
        self.final_verdict = artifact.final_verdict

    def _log_cloud_proof_event(self, event: str, **fields: Any) -> None:
        payload = {
            "session_id": self.session_id,
            "state": self.state,
            "current_step": self.current_step,
            "task_id": _task_context_value(self.current_task_context, "taskId"),
            "task_name": _task_context_value(self.current_task_context, "taskName"),
            "path_mode": self.current_path_mode,
            "verification_status": self.verification_status,
            "swap_count": self.swap_count,
            "recovery_step": self.recovery_step,
            "classification_label": self.classification_label,
        }
        payload.update(fields)
        log_event(
            LOGGER,
            logging.INFO,
            event,
            **payload,
        )

    def _build_case_report_log_summary(self) -> dict[str, Any]:
        self._ensure_case_report_generated()
        verification_counts = {
            "confirmed": 0,
            "user_confirmed_only": 0,
            "unverified": 0,
            "skipped": 0,
        }
        tasks = self.case_report_payload.get("tasks") if isinstance(self.case_report_payload, dict) else []
        if isinstance(tasks, list):
            for item in tasks:
                if not isinstance(item, dict):
                    continue
                outcome = item.get("outcome")
                if outcome in verification_counts:
                    verification_counts[outcome] += 1

        return {
            "final_verdict": self._derive_final_verdict(),
            "classification_label": self.classification_label,
            "task_history_count": len(self.task_history),
            "verification_history_count": len(self.verification_history),
            "verification_counts": verification_counts,
        }

    def _derive_final_verdict(self) -> str | None:
        if self.final_verdict is not None:
            return self.final_verdict
        if self.case_report_payload is not None:
            return _string_or_none(self.case_report_payload.get("finalVerdict"))
        if self.state in {"completed", "case_report"}:
            return "secured"
        if self.state != "ended":
            return None
        if self.task_history:
            return "partial"
        return "inconclusive"

    def _has_remaining_tasks(self) -> bool:
        return self.plan is not None and (self.active_task_index + 1) < len(self.plan.selected_tasks)

    def _record_task_history(self, outcome: str, reason: str) -> None:
        self.task_history.append(
            {
                "at": _utc_now_iso(),
                "taskId": _task_context_value(self.current_task_context, "taskId"),
                "taskName": _task_context_value(self.current_task_context, "taskName"),
                "outcome": outcome,
                "reason": reason,
                "protocolStep": self.current_step,
            }
        )

    def _transition(self, to_state: SessionStateName, reason: str) -> None:
        if to_state == self.state:
            return
        if to_state not in _ALLOWED_TRANSITIONS[self.state]:
            raise SessionStateMachineError(
                f"Illegal session transition {self.state} -> {to_state}."
            )
        from_state = self.state
        log_event(
            LOGGER,
            logging.INFO,
            "session_state_transition",
            session_id=self.session_id,
            from_state=from_state,
            to_state=to_state,
            reason=reason,
        )
        self.transition_history.append(
            {
                "at": _utc_now_iso(),
                "from": from_state,
                "to": to_state,
                "reason": reason,
            }
        )
        self.state = to_state
        if to_state == "recovery_active":
            self._log_cloud_proof_event(
                "recovery_entered",
                transition_reason=reason,
                block_reason=self.block_reason,
                recovery_attempt_count=self.recovery_attempt_count,
                recovery_attempt_limit=self.recovery_attempt_limit,
                reroute_required=self.recovery_reroute_required,
            )
        elif to_state == "case_report":
            self._log_cloud_proof_event(
                "case_report_generated",
                **self._build_case_report_log_summary(),
            )


def _contains_any(lines: tuple[str, ...], phrases: tuple[str, ...]) -> bool:
    return any(phrase in line for line in lines for phrase in phrases)


def _infer_positive_affordance(
    lines: tuple[str, ...],
    phrases: tuple[str, ...],
) -> bool | None:
    return True if _contains_any(lines, phrases) else None

def _normalize_task_context(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "contextLabel": value.get("contextLabel"),
        "contextStatus": value.get("contextStatus"),
        "pathMode": value.get("pathMode"),
        "protocolStep": value.get("protocolStep"),
        "taskId": value.get("taskId"),
        "taskName": value.get("taskName"),
        "operatorDescription": value.get("operatorDescription"),
        "taskRoleCategory": value.get("taskRoleCategory"),
        "taskTier": value.get("taskTier"),
        "verificationClass": value.get("verificationClass"),
        "swapCount": value.get("swapCount"),
    }


def _task_context_value(context: dict[str, Any] | None, key: str) -> str | None:
    if isinstance(context, dict):
        return _string_or_none(context.get(key))
    return None


def _string_or_none(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = ["SessionStateMachine", "SessionStateMachineError"]























