"""Session-scoped Ready-to-Verify flow state for Prompt 21."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import logging
from typing import Any
from uuid import uuid4

from .capability_profile import (
    ObservedAffordances,
    QualityMetrics,
    UserDeclaredConstraints,
    build_capability_profile,
)
from .demo_dialogue import DEMO_RECOVERY_LINE
from .demo_recovery import (
    DEMO_NEAR_FAILURE_SCRIPT,
    DemoNearFailureStatus,
    matches_demo_near_failure_task,
)
from .logging_utils import log_event
from .recovery_ladder import RecoveryDirective, VerificationRecoveryLadder
from .verification_engine import (
    VerificationContext,
    VerificationDecision,
    VerificationEngine,
    VerificationEngineError,
    VerificationFrameInput,
)
from .voice_intent import parse_swap_voice_intent

LOGGER = logging.getLogger("ghostline.backend.verification")
ForwardEnvelope = Callable[[dict[str, Any]], Awaitable[None]]
_HOLD_STILL_SECONDS = 1
_CAPTURE_WINDOW_MS = 1000
_EXPECTED_FRAME_COUNT = 4
_MAX_RECENT_USER_TRANSCRIPTS = 6
_VALID_PATH_MODES = {"threshold", "tabletop", "low_visibility"}

# TEMPORARY PROMPT 21 STUB:
# Active task assignment is not wired into the live session yet. Until the
# later planner/state-machine prompts connect real task state to the call, the
# verification flow emits a clearly labeled unresolved task context instead of
# pretending a task is active.
_TEMPORARY_UNRESOLVED_TASK_CONTEXT: dict[str, Any] = {
    "taskId": None,
    "taskName": None,
    "taskRoleCategory": None,
    "taskTier": None,
    "pathMode": None,
    "protocolStep": "ready_to_verify_window",
    "verificationClass": None,
    "contextStatus": "temporary_unassigned",
    "contextLabel": (
        "TEMPORARY PROMPT 21 STUB: active task assignment is not wired yet."
    ),
}


class VerificationFlowError(ValueError):
    """Raised when the Prompt 21 verification flow receives invalid state."""


@dataclass(frozen=True)
class VerificationFrameRecord:
    captured_at: str
    data: str
    height: int
    mime_type: str
    sequence: int
    total_frames: int
    width: int


@dataclass
class VerificationAttempt:
    attempt_id: str
    capture_window_ms: int
    expected_frames: int
    hold_still_seconds: int
    raw_transcript_snippet: str | None
    source: str
    started_at: str
    task_context: dict[str, Any]
    frames: list[VerificationFrameRecord] = field(default_factory=list)
    quality_metrics_input: dict[str, float] | None = None


class SessionVerificationFlow:
    """Owns Prompt 21 verification-window state for one WebSocket session."""

    def __init__(
        self,
        *,
        session_id: str,
        forward_envelope: ForwardEnvelope,
        verification_engine: VerificationEngine | None = None,
        demo_mode_enabled: bool = False,
    ) -> None:
        self.session_id = session_id
        self._forward_envelope = forward_envelope
        self._active_attempt: VerificationAttempt | None = None
        self._camera_ready = False
        self._microphone_streaming = False
        self._verification_engine = verification_engine
        self._demo_mode_enabled = demo_mode_enabled
        self._demo_near_failure_status: DemoNearFailureStatus | None = (
            "idle" if demo_mode_enabled else None
        )
        self._recent_user_transcripts: list[str] = []
        self._recovery_ladder = VerificationRecoveryLadder()

    @property
    def is_pending(self) -> bool:
        return self._active_attempt is not None

    def attach_verification_engine(
        self,
        verification_engine: VerificationEngine | None,
    ) -> None:
        self._verification_engine = verification_engine

    def set_demo_mode_enabled(self, enabled: bool) -> None:
        self._demo_mode_enabled = enabled
        self._demo_near_failure_status = "idle" if enabled else None

    def record_user_transcript(self, text: str, is_final: bool) -> None:
        if not is_final:
            return
        normalized_text = text.strip()
        if not normalized_text:
            return
        self._recent_user_transcripts.append(normalized_text)
        self._recent_user_transcripts = self._recent_user_transcripts[
            -_MAX_RECENT_USER_TRANSCRIPTS:
        ]

    def update_camera_state(self, payload: dict[str, Any]) -> None:
        permission = payload.get("permission")
        preview = payload.get("preview")
        self._camera_ready = permission == "granted" and preview is True

    def update_microphone_state(self, payload: dict[str, Any]) -> None:
        self._microphone_streaming = payload.get("streaming") is True

    async def start_verification(self, payload: dict[str, Any]) -> None:
        if self._active_attempt is not None:
            raise VerificationFlowError(
                "A Ready-to-Verify window is already in progress."
            )
        if not self._camera_ready:
            raise VerificationFlowError(
                "Ready to Verify requires an active room feed before the hold-still window can begin."
            )
        if not self._microphone_streaming:
            raise VerificationFlowError(
                "Ready to Verify requires the live microphone bridge to be active."
            )

        source = payload.get("source")
        if not isinstance(source, str) or not source.strip():
            source = "control_bar"

        raw_transcript_snippet = payload.get("rawTranscriptSnippet")
        if not isinstance(raw_transcript_snippet, str) or not raw_transcript_snippet.strip():
            raw_transcript_snippet = None

        task_context = _build_task_context(payload.get("taskContext"))
        recovery_path_mode = _resolve_recovery_path_mode(task_context)
        if self._recovery_ladder.is_retry_exhausted(
            task_context=task_context,
            current_path_mode=recovery_path_mode,
        ):
            raise VerificationFlowError(
                "This verification path is still blocked. Switch path mode or substitute task before another Ready to Verify attempt."
            )

        attempt = VerificationAttempt(
            attempt_id=f"verify-{uuid4().hex}",
            capture_window_ms=_CAPTURE_WINDOW_MS,
            expected_frames=_EXPECTED_FRAME_COUNT,
            hold_still_seconds=_HOLD_STILL_SECONDS,
            raw_transcript_snippet=raw_transcript_snippet,
            source=source,
            started_at=_utc_now_iso(),
            task_context=task_context,
        )
        self._active_attempt = attempt

        log_event(
            LOGGER,
            logging.INFO,
            "verification_requested",
            session_id=self.session_id,
            verification_attempt_id=attempt.attempt_id,
            source=attempt.source,
            current_step=attempt.task_context.get("protocolStep"),
            task_id=attempt.task_context.get("taskId"),
            task_name=attempt.task_context.get("taskName"),
            path_mode=attempt.task_context.get("pathMode"),
            raw_transcript_snippet=attempt.raw_transcript_snippet,
        )
        log_event(
            LOGGER,
            logging.INFO,
            "verification_window_started",
            session_id=self.session_id,
            verification_attempt_id=attempt.attempt_id,
            source=attempt.source,
            expected_frames=attempt.expected_frames,
            capture_window_ms=attempt.capture_window_ms,
            raw_transcript_snippet=attempt.raw_transcript_snippet,
            task_context_status=attempt.task_context.get("contextStatus"),
        )

        await self._forward_transcript(
            text="Hold still for one second.",
            source="verification_flow",
        )
        await self._forward_state(
            status="pending",
            attempt=attempt,
            received_frames=0,
        )

    async def ingest_frame(self, payload: dict[str, Any]) -> None:
        if self._active_attempt is None:
            raise VerificationFlowError(
                "No Ready-to-Verify window is waiting for frames."
            )

        attempt_id = payload.get("verificationAttemptId")
        if not isinstance(attempt_id, str) or attempt_id != self._active_attempt.attempt_id:
            raise VerificationFlowError(
                "Frame payload does not match the active verification attempt."
            )

        frame = _parse_frame_payload(payload)
        quality_metrics_input = _parse_optional_quality_metrics(payload.get("qualityMetrics"))
        if quality_metrics_input is not None and self._active_attempt.quality_metrics_input is None:
            self._active_attempt.quality_metrics_input = quality_metrics_input

        if any(existing.sequence == frame.sequence for existing in self._active_attempt.frames):
            raise VerificationFlowError(
                "Duplicate verification frame sequence received."
            )

        self._active_attempt.frames.append(frame)
        self._active_attempt.frames.sort(key=lambda item: item.sequence)

        log_event(
            LOGGER,
            logging.INFO,
            "verification_frame_received",
            session_id=self.session_id,
            verification_attempt_id=self._active_attempt.attempt_id,
            sequence=frame.sequence,
            total_frames=frame.total_frames,
            width=frame.width,
            height=frame.height,
            mime_type=frame.mime_type,
        )

        if len(self._active_attempt.frames) < self._active_attempt.expected_frames:
            return

        completed_attempt = self._active_attempt
        self._active_attempt = None

        log_event(
            LOGGER,
            logging.INFO,
            "verification_window_captured",
            session_id=self.session_id,
            verification_attempt_id=completed_attempt.attempt_id,
            received_frames=len(completed_attempt.frames),
            capture_window_ms=completed_attempt.capture_window_ms,
        )

        await self._forward_state(
            status="captured",
            attempt=completed_attempt,
            received_frames=len(completed_attempt.frames),
        )
        await self._forward_transcript(
            text="Verification window captured. Stand by.",
            source="verification_flow",
        )
        if self._verification_engine is not None:
            await self._run_verification_engine(completed_attempt)

    async def cancel_active_attempt(self, reason: str) -> bool:
        if self._active_attempt is None:
            return False

        cancelled_attempt = self._active_attempt
        self._active_attempt = None
        log_event(
            LOGGER,
            logging.INFO,
            "verification_window_cancelled",
            session_id=self.session_id,
            verification_attempt_id=cancelled_attempt.attempt_id,
            reason=reason,
            current_step=cancelled_attempt.task_context.get("protocolStep"),
            task_id=cancelled_attempt.task_context.get("taskId"),
            task_name=cancelled_attempt.task_context.get("taskName"),
        )
        await self._forward_state(
            status="cancelled",
            attempt=cancelled_attempt,
            received_frames=len(cancelled_attempt.frames),
            reason=reason,
        )
        return True

    async def close(self) -> None:
        self._active_attempt = None

    async def _forward_state(
        self,
        *,
        status: str,
        attempt: VerificationAttempt,
        received_frames: int,
        reason: str | None = None,
    ) -> None:
        await self._forward_envelope(
            {
                "type": "verification_state",
                "sessionId": self.session_id,
                "payload": {
                    "status": status,
                    "attemptId": attempt.attempt_id,
                    "captureWindowMs": attempt.capture_window_ms,
                    "expectedFrames": attempt.expected_frames,
                    "holdStillSeconds": attempt.hold_still_seconds,
                    "receivedFrames": received_frames,
                    "source": attempt.source,
                    "rawTranscriptSnippet": attempt.raw_transcript_snippet,
                    "startedAt": attempt.started_at,
                    "taskContext": attempt.task_context,
                    "reason": reason,
                },
            }
        )

    async def _forward_transcript(self, *, text: str, source: str) -> None:
        await self._forward_envelope(
            {
                "type": "transcript",
                "sessionId": self.session_id,
                "payload": {
                    "speaker": "operator",
                    "text": text,
                    "isFinal": True,
                    "source": source,
                },
            }
        )

    async def _run_verification_engine(
        self,
        attempt: VerificationAttempt,
    ) -> None:
        if self._verification_engine is None:
            return

        quality_metrics = _build_quality_metrics_for_attempt(attempt)
        capability_profile = _build_capability_profile_for_attempt(
            attempt=attempt,
            quality_metrics=quality_metrics,
            recent_user_transcripts=tuple(self._recent_user_transcripts),
        )
        current_path_mode = _resolve_current_path_mode(attempt, capability_profile)
        verification_context = VerificationContext(
            attempt_id=attempt.attempt_id,
            capability_profile=capability_profile,
            current_path_mode=current_path_mode,
            frames=tuple(
                VerificationFrameInput(
                    captured_at=frame.captured_at,
                    height=frame.height,
                    mime_type=frame.mime_type,
                    sequence=frame.sequence,
                    total_frames=frame.total_frames,
                    width=frame.width,
                )
                for frame in attempt.frames
            ),
            quality_metrics=quality_metrics,
            raw_transcript_snippet=attempt.raw_transcript_snippet,
            recent_user_transcripts=tuple(self._recent_user_transcripts),
            session_id=self.session_id,
            source=attempt.source,
            started_at=attempt.started_at,
            task_context=attempt.task_context,
        )

        decision = self._build_demo_mode_override(attempt)
        if decision is None:
            try:
                decision = await self._verification_engine.evaluate(verification_context)
            except VerificationEngineError as exc:
                raise VerificationFlowError(str(exc)) from exc

        await self._forward_result(
            attempt=attempt,
            decision=decision,
            quality_metrics=quality_metrics,
            capability_profile=capability_profile,
            current_path_mode=current_path_mode,
        )

    async def _forward_result(
        self,
        *,
        attempt: VerificationAttempt,
        decision: VerificationDecision,
        quality_metrics: QualityMetrics,
        capability_profile: Any,
        current_path_mode: str,
    ) -> None:
        recovery_directive: RecoveryDirective | None = None
        if decision.status == "unconfirmed":
            recovery_directive = self._recovery_ladder.build_directive(
                block_reason=decision.block_reason,
                capability_profile=capability_profile,
                current_path_mode=current_path_mode,
                reason=decision.reason,
                task_context=attempt.task_context,
            )
            if self._demo_mode_enabled:
                recovery_directive = replace(
                    recovery_directive,
                    operator_line=DEMO_RECOVERY_LINE,
                )
            log_event(
                LOGGER,
                logging.INFO,
                "verification_recovery_step_selected",
                session_id=self.session_id,
                verification_attempt_id=attempt.attempt_id,
                recovery_step_key=recovery_directive.step_key,
                recovery_attempt_count=recovery_directive.attempt_count,
                suggested_path_mode=recovery_directive.suggested_path_mode,
                substitute_task_id=(
                    recovery_directive.substitute_task.task_id
                    if recovery_directive.substitute_task is not None
                    else None
                ),
                demo_mode_enabled=self._demo_mode_enabled,
            )
        else:
            self._recovery_ladder.reset(
                task_context=attempt.task_context,
                current_path_mode=current_path_mode,
            )

        log_event(
            LOGGER,
            logging.INFO,
            "verification_result_emitted",
            session_id=self.session_id,
            verification_attempt_id=attempt.attempt_id,
            current_step=attempt.task_context.get("protocolStep"),
            task_id=attempt.task_context.get("taskId"),
            task_name=attempt.task_context.get("taskName"),
            current_path_mode=current_path_mode,
            status=decision.status,
            confidence_band=decision.confidence_band,
            block_reason=decision.block_reason,
            is_mock=decision.is_mock,
        )
        await self._forward_envelope(
            {
                "type": "verification_result",
                "sessionId": self.session_id,
                "payload": {
                    "attemptId": attempt.attempt_id,
                    "status": decision.status,
                    "confidenceBand": decision.confidence_band,
                    "reason": decision.reason,
                    "blockReason": decision.block_reason,
                    "lastVerifiedItem": decision.last_verified_item,
                    "isMock": decision.is_mock,
                    "mockLabel": decision.mock_label,
                    "notes": decision.notes,
                    "currentPathMode": current_path_mode,
                    "qualityMetrics": {
                        "lighting": quality_metrics.lighting,
                        "blur": quality_metrics.blur,
                        "motionStability": quality_metrics.motion_stability,
                    },
                    "capabilityProfile": {
                        "pathMode": capability_profile.environment.path_mode,
                        "visualQualityLimited": capability_profile.environment.visual_quality_limited,
                        "thresholdReady": capability_profile.environment.threshold_ready,
                        "tabletopReady": capability_profile.environment.tabletop_ready,
                        "reasons": capability_profile.environment.reasons,
                    },
                    "taskContext": attempt.task_context,
                    "demoNearFailureStatus": self._demo_near_failure_status,
                    "demoNearFailureFailureType": (
                        DEMO_NEAR_FAILURE_SCRIPT.failure_type
                        if self._demo_mode_enabled
                        else None
                    ),
                    "demoNearFailureTaskId": (
                        DEMO_NEAR_FAILURE_SCRIPT.task_id
                        if self._demo_mode_enabled
                        else None
                    ),
                    **(
                        recovery_directive.to_payload()
                        if recovery_directive is not None
                        else {}
                    ),
                },
            }
        )

        if recovery_directive is not None:
            await self._forward_transcript(
                text=recovery_directive.operator_line,
                source="recovery_ladder",
            )


    def _build_demo_mode_override(
        self,
        attempt: VerificationAttempt,
    ) -> VerificationDecision | None:
        if not self._demo_mode_enabled:
            return None
        if not matches_demo_near_failure_task(attempt.task_context):
            return None
        if self._demo_near_failure_status == "recovered":
            return None

        task_name = attempt.task_context.get("taskName")
        if not isinstance(task_name, str) or not task_name.strip():
            task_name = "Increase Illumination"

        if self._demo_near_failure_status == "idle":
            self._demo_near_failure_status = "failed_once"
            log_event(
                LOGGER,
                logging.INFO,
                "demo_near_failure_triggered",
                session_id=self.session_id,
                verification_task_id=DEMO_NEAR_FAILURE_SCRIPT.task_id,
                failure_type=DEMO_NEAR_FAILURE_SCRIPT.failure_type,
                verification_attempt_id=attempt.attempt_id,
            )
            return VerificationDecision(
                block_reason=DEMO_NEAR_FAILURE_SCRIPT.failure_block_reason,
                confidence_band="low",
                is_mock=False,
                last_verified_item=None,
                mock_label=None,
                notes=(
                    "Demo Mode Prompt 46: controlled first verification failure for the rehearsed recovery beat."
                ),
                reason=DEMO_NEAR_FAILURE_SCRIPT.failure_reason,
                status="unconfirmed",
            )

        if self._demo_near_failure_status == "failed_once":
            self._demo_near_failure_status = "recovered"
            log_event(
                LOGGER,
                logging.INFO,
                "demo_near_failure_recovered",
                session_id=self.session_id,
                verification_task_id=DEMO_NEAR_FAILURE_SCRIPT.task_id,
                failure_type=DEMO_NEAR_FAILURE_SCRIPT.failure_type,
                verification_attempt_id=attempt.attempt_id,
            )
            return VerificationDecision(
                block_reason=None,
                confidence_band="medium",
                is_mock=False,
                last_verified_item=task_name,
                mock_label=None,
                notes=(
                    "Demo Mode Prompt 46: controlled recovery beat resolved on the second scripted verification attempt."
                ),
                reason=DEMO_NEAR_FAILURE_SCRIPT.success_reason,
                status="confirmed",
            )

        return None

def _build_task_context(raw_value: Any) -> dict[str, Any]:
    task_context = dict(_TEMPORARY_UNRESOLVED_TASK_CONTEXT)
    if not isinstance(raw_value, dict):
        return task_context

    for key in (
        "taskId",
        "taskName",
        "taskRoleCategory",
        "taskTier",
        "pathMode",
        "protocolStep",
        "verificationClass",
    ):
        value = raw_value.get(key)
        if value is not None:
            task_context[key] = value

    task_context["contextStatus"] = raw_value.get(
        "contextStatus",
        task_context["contextStatus"],
    )
    task_context["contextLabel"] = raw_value.get(
        "contextLabel",
        task_context["contextLabel"],
    )
    return task_context


def _parse_frame_payload(payload: dict[str, Any]) -> VerificationFrameRecord:
    data = payload.get("data")
    if not isinstance(data, str) or not data.strip():
        raise VerificationFlowError("Verification frames must include base64 image data.")

    sequence = payload.get("sequence")
    total_frames = payload.get("totalFrames")
    width = payload.get("width")
    height = payload.get("height")
    captured_at = payload.get("capturedAt")
    mime_type = payload.get("mimeType")

    for field_name, value in (
        ("sequence", sequence),
        ("totalFrames", total_frames),
        ("width", width),
        ("height", height),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise VerificationFlowError(
                f"Verification frame field {field_name} must be an integer."
            )

    if not isinstance(captured_at, str) or not captured_at.strip():
        raise VerificationFlowError(
            "Verification frames must include a capturedAt timestamp."
        )

    if not isinstance(mime_type, str) or not mime_type.startswith("image/"):
        raise VerificationFlowError(
            "Verification frames must include an image/* MIME type."
        )

    return VerificationFrameRecord(
        captured_at=captured_at,
        data=data.strip(),
        height=height,
        mime_type=mime_type,
        sequence=sequence,
        total_frames=total_frames,
        width=width,
    )


def _parse_optional_quality_metrics(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None

    lighting = value.get("lighting")
    blur = value.get("blur")
    motion_stability = value.get("motionStability")
    parsed: dict[str, float] = {}
    for key, raw in (
        ("lighting", lighting),
        ("blur", blur),
        ("motion_stability", motion_stability),
    ):
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            return None
        normalized = float(raw)
        if normalized < 0 or normalized > 1:
            return None
        parsed[key] = normalized

    return parsed


def _build_quality_metrics_for_attempt(attempt: VerificationAttempt) -> QualityMetrics:
    raw = attempt.quality_metrics_input
    if raw is not None:
        return QualityMetrics(
            lighting=raw["lighting"],
            blur=raw["blur"],
            motion_stability=raw["motion_stability"],
        )

    consistent_dimensions = len(
        {(frame.width, frame.height) for frame in attempt.frames}
    ) == 1
    return QualityMetrics(
        lighting=0.45,
        blur=0.55,
        motion_stability=0.5 if consistent_dimensions else 0.35,
    )


def _build_capability_profile_for_attempt(
    *,
    attempt: VerificationAttempt,
    quality_metrics: QualityMetrics,
    recent_user_transcripts: tuple[str, ...],
):
    task_id = attempt.task_context.get("taskId")
    path_mode = attempt.task_context.get("pathMode")
    transcripts = tuple(
        line
        for line in (*recent_user_transcripts, attempt.raw_transcript_snippet)
        if isinstance(line, str) and line.strip()
    )
    user_constraints = _build_user_constraints(transcripts)
    observed_affordances = ObservedAffordances(
        threshold_available=True if path_mode == "threshold" else None,
        flat_surface_available=True if path_mode == "tabletop" else None,
        paper_available=True if task_id in {"T5", "T8"} and not user_constraints.no_paper else None,
        light_controllable=True if task_id == "T3" and not user_constraints.cannot_adjust_light else None,
        reflective_surface_available=True if task_id == "T9" and not user_constraints.no_reflective_surface else None,
        water_source_nearby=True if task_id == "T11" and not user_constraints.no_water_source else None,
    )
    return build_capability_profile(
        observed_affordances=observed_affordances,
        quality_metrics=quality_metrics,
        user_constraints=user_constraints,
    )


def _build_user_constraints(
    transcripts: tuple[str, ...],
) -> UserDeclaredConstraints:
    lowered = [text.lower() for text in transcripts]
    cannot_use_threshold = False
    no_flat_surface = False
    no_paper = False
    cannot_adjust_light = False
    no_reflective_surface = False
    no_water_source = False
    notes: list[str] = []

    for transcript in lowered:
        swap_request = parse_swap_voice_intent(transcript)
        if swap_request is not None:
            if swap_request.inferred_reason == "missing_paper":
                no_paper = True
                notes.append("user declared paper unavailable")
            elif swap_request.inferred_reason == "missing_door_or_threshold":
                cannot_use_threshold = True
                notes.append("user declared threshold unavailable")

        if "no table" in transcript or "no counter" in transcript or "no flat surface" in transcript:
            no_flat_surface = True
            notes.append("user declared no flat surface")
        if "light wont" in transcript or "light won't" in transcript or "cant adjust light" in transcript or "cannot adjust light" in transcript:
            cannot_adjust_light = True
            notes.append("user declared lighting cannot be adjusted")
        if "no mirror" in transcript or "no reflective" in transcript:
            no_reflective_surface = True
            notes.append("user declared no reflective surface")
        if "no sink" in transcript or "no water" in transcript:
            no_water_source = True
            notes.append("user declared no water source")

    return UserDeclaredConstraints(
        cannot_use_threshold=cannot_use_threshold,
        no_flat_surface=no_flat_surface,
        no_paper=no_paper,
        cannot_adjust_light=cannot_adjust_light,
        no_reflective_surface=no_reflective_surface,
        no_water_source=no_water_source,
        notes=tuple(dict.fromkeys(notes)),
    )


def _resolve_current_path_mode(
    attempt: VerificationAttempt,
    capability_profile: Any,
) -> str:
    path_mode = attempt.task_context.get("pathMode")
    if isinstance(path_mode, str) and path_mode in _VALID_PATH_MODES:
        return path_mode
    return capability_profile.environment.path_mode


def _resolve_recovery_path_mode(task_context: dict[str, Any]) -> str:
    path_mode = task_context.get("pathMode")
    if isinstance(path_mode, str) and path_mode in _VALID_PATH_MODES:
        return path_mode
    return "unresolved"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "SessionVerificationFlow",
    "VerificationFlowError",
]










