"""WebSocket gateway for client session traffic and backend session state."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from .audio_bridge import AudioBridgePayloadError, SessionAudioBridge
from .gemini_verification import (
    GeminiVisionVerificationEngine,
    parse_room_scan_affordances,
    AI_RECOVERY_DIRECTIVE_TEMPLATE,
)
from .capability_profile import ObservedAffordances
from .capability_recovery import CapabilityRecoveryError, SessionCapabilityRecoveryManager
from .demo_dialogue import (
    DEMO_CAMERA_REQUEST_LINE,
    DEMO_DIAGNOSIS_INTERPRETATION_LINE,
    DEMO_DIAGNOSIS_QUESTION_LINE,
    DEMO_FINAL_CLOSURE_LINE,
    DEMO_OPENER_LINE_GRANTED,
    DEMO_OPENER_LINE_PROMPT,
    DEMO_ROOM_SCAN_ASSESSMENT_LINE,
    DEMO_ROOM_SCAN_LINE,
    build_demo_task_assignment_line,
    get_demo_flavor_for_task,
)
from .flavor_text_state_model import FlavorTextStateModel
from .gemini_live import GeminiLiveError, GeminiLiveSessionManager
from .incident_classification import IncidentClassificationStore
from .logging_utils import log_event
from .operator_guidance import (
    BACKEND_AUTHORED_TRANSCRIPT_SOURCES,
    NormalModeOperatorGuidanceOrchestrator,
    OperatorGuidanceDirective,
)
from .self_report_flow import (
    CONTAINMENT_PHRASE_TEXT,
    DEMO_SOUND_PROMPT_DELAY_SECONDS,
    build_self_report_verify_reminder,
    is_self_report_task_context,
    resolve_self_report_response,
)
from .session_state_machine import SessionStateMachine, SessionStateMachineError
from .session_transport import (
    InvalidSessionEnvelope,
    build_ack_envelope,
    build_error_envelope,
    parse_session_envelope,
)
from .task_helpers import InvalidTaskIdError, get_task_by_id
from .verification_engine import VerificationEngine
from .verification_flow import SessionVerificationFlow, VerificationFlowError

LOGGER = logging.getLogger("ghostline.backend.websocket")
_NO_ACK_MESSAGE_TYPES = frozenset({"audio_chunk", "room_scan_frame", "task_vision_frame"})
_PLACEHOLDER_ONLY_TYPES = frozenset({"transcript"})
_GUIDANCE_TRANSCRIPT_SOURCES = BACKEND_AUTHORED_TRANSCRIPT_SOURCES
_MIN_ROOM_SCAN_BRIGHTNESS = 8.0
_MIN_ROOM_SCAN_DETAIL = 0.02
_MIN_ROOM_SCAN_LIGHTING_SCORE = _MIN_ROOM_SCAN_BRIGHTNESS / 255.0
_MIN_VALIDATED_ROOM_SCAN_FRAMES = 3
_ROOM_SCAN_REJECTION_LINE = (
    "I am not getting a usable feed. Fix the camera and hold the room still so I can confirm the space."
)

_ROOM_SCAN_REJECTION_LINES: dict[str, str] = {
    "too_dark": "The room is a little too dark to read clearly. Add a bit more light or point the camera toward the lit part of the room.",
    "too_blurry": "Too much blur. Hold the camera still so I can confirm the room.",
    "low_detail": "Too much blur. Hold the camera still so I can confirm the room.",
    "too_close": "The camera is too close. Pull back and show me the room from a corner or doorway.",
    "too_narrow": "I can use a normal room view, but I need a little more of the space in frame. Step back slightly and hold still.",
    "too_unstable": "The feed is unstable. Hold the camera still until the room stays steady.",
    "no_room_visible": "I still do not have the room in view. Turn the camera outward and show me the space.",
    "insufficient_view": "I just need a steadier, readable room view before we continue.",
    "unreadable": _ROOM_SCAN_REJECTION_LINE,
}

class SessionTransportClosedError(RuntimeError):
    """Raised when the client WebSocket can no longer accept messages."""


class SessionConnectionManager:
    """Tracks active client WebSocket sessions for transport-level messaging."""

    def __init__(self) -> None:
        self._connections: dict[str, WebSocket] = {}

    @property
    def active_count(self) -> int:
        return len(self._connections)

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        session_id = uuid4().hex
        self._connections[session_id] = websocket
        return session_id

    def disconnect(self, session_id: str) -> None:
        self._connections.pop(session_id, None)

    async def send_json(self, session_id: str, message: dict[str, Any]) -> None:
        websocket = self._connections.get(session_id)
        if websocket is not None:
            try:
                await websocket.send_json(message)
            except (RuntimeError, WebSocketDisconnect) as exc:
                raise SessionTransportClosedError(str(exc)) from exc


async def _receive_json_message(websocket: WebSocket) -> Any:
    message = await websocket.receive()

    if message["type"] == "websocket.disconnect":
        raise WebSocketDisconnect(code=message.get("code", 1000))

    text = message.get("text")
    if text is None:
        raise InvalidSessionEnvelope("WebSocket messages must be UTF-8 JSON text.")

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidSessionEnvelope("Invalid JSON payload.") from exc



def _extract_guidance_transcript(message: dict[str, Any]) -> tuple[str, str] | None:
    if message.get("type") != "transcript":
        return None

    payload = message.get("payload")
    if not isinstance(payload, dict):
        return None

    if payload.get("speaker") != "operator":
        return None

    source = payload.get("source")
    text = payload.get("text")
    if not isinstance(source, str) or source not in _GUIDANCE_TRANSCRIPT_SOURCES:
        return None
    if not isinstance(text, str) or not text.strip():
        return None

    return text.strip(), source


def _build_task_assignment_guidance(
    flavor_model: FlavorTextStateModel,
    session_id: str,
    task_context: dict[str, Any] | None,
    *,
    demo_mode_enabled: bool,
) -> str | None:
    if not isinstance(task_context, dict):
        return None

    if demo_mode_enabled:
        return build_demo_task_assignment_line(task_context)

    task_name = task_context.get("taskName")
    if not isinstance(task_name, str) or not task_name.strip():
        return None

    opener_selection = flavor_model.select_flavor_line(
        session_id,
        "task_assignment",
        preferred_category="task_introduction",
    )
    opener = (
        opener_selection.text
        if opener_selection is not None
        else "Good. We move one step at a time. Do this exactly once, then stop."
    )

    operator_description = task_context.get("operatorDescription")
    if not isinstance(operator_description, str) or not operator_description.strip():
        task_id = task_context.get("taskId")
        if isinstance(task_id, str) and task_id.strip():
            try:
                operator_description = get_task_by_id(task_id.strip()).operator_description
            except InvalidTaskIdError:
                operator_description = None

    detail = (
        operator_description.strip()
        if isinstance(operator_description, str) and operator_description.strip()
        else "Perform the current containment step once, keep the frame readable, then stop."
    )
    return (
        f"{opener} Current task: {task_name.strip()}. {detail} "
        "When the step is in place, stop and say Ready to Verify."
    )


def _resolve_demo_mode_request(
    payload: dict[str, Any],
    *,
    default_enabled: bool,
) -> bool:
    requested = payload.get("demoMode")
    if isinstance(requested, bool):
        return requested
    return default_enabled

def _task_id_from_context(task_context: dict[str, Any] | None) -> str | None:
    if isinstance(task_context, dict):
        value = task_context.get("taskId")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None

def _coerce_float(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _is_room_scan_frame_usable(payload: dict[str, Any]) -> bool:
    quality = payload.get("quality")
    brightness = _coerce_float(payload.get("brightness"))
    detail = _coerce_float(payload.get("detail"))
    lighting_score = _coerce_float(payload.get("lightingScore"))
    detail_score = _coerce_float(payload.get("detailScore"))

    if quality == "unusable":
        return False
    if brightness is not None and brightness < _MIN_ROOM_SCAN_BRIGHTNESS:
        return False
    if lighting_score is not None and lighting_score < _MIN_ROOM_SCAN_LIGHTING_SCORE:
        return False
    if detail is not None and detail < _MIN_ROOM_SCAN_DETAIL:
        return False
    if detail_score is not None and detail_score < _MIN_ROOM_SCAN_DETAIL:
        return False
    if quality == "usable":
        return True
    return any(value is not None for value in (brightness, detail, lighting_score, detail_score))


def _room_scan_quality_reason(payload: dict[str, Any]) -> str:
    explicit_reason = payload.get("qualityReason")
    if isinstance(explicit_reason, str) and explicit_reason.strip():
        return explicit_reason.strip()
    brightness = _coerce_float(payload.get("brightness"))
    lighting_score = _coerce_float(payload.get("lightingScore"))
    detail = _coerce_float(payload.get("detail"))
    detail_score = _coerce_float(payload.get("detailScore"))
    if brightness is not None and brightness < _MIN_ROOM_SCAN_BRIGHTNESS:
        return "too_dark"
    if lighting_score is not None and lighting_score < _MIN_ROOM_SCAN_LIGHTING_SCORE:
        return "too_dark"
    if detail is not None and detail < _MIN_ROOM_SCAN_DETAIL:
        return "low_detail"
    if detail_score is not None and detail_score < _MIN_ROOM_SCAN_DETAIL:
        return "low_detail"
    return "unreadable"


def _room_scan_rejection_line(reason: str | None) -> str:
    if isinstance(reason, str):
        return _ROOM_SCAN_REJECTION_LINES.get(reason, _ROOM_SCAN_REJECTION_LINE)
    return _ROOM_SCAN_REJECTION_LINE

def register_websocket_gateway(app: FastAPI) -> None:
    manager = SessionConnectionManager()
    app.state.session_connection_manager = manager

    @app.websocket("/ws/session")
    async def session_gateway(websocket: WebSocket) -> None:
        session_id = await manager.connect(websocket)
        disconnect_reason = "client_disconnect"
        disconnect_code = 1000

        gemini_live_session_manager: GeminiLiveSessionManager = (
            app.state.gemini_live_session_manager
        )
        verification_engine: VerificationEngine | None = getattr(
            app.state,
            "verification_engine",
            None,
        )
        incident_store: IncidentClassificationStore | None = getattr(
            app.state,
            "incident_classification_store",
            None,
        )
        firestore_session_store = getattr(
            app.state,
            "firestore_session_store",
            None,
        )
        cloud_proof_registry = getattr(
            app.state,
            "cloud_proof_registry",
            None,
        )
        flavor_text_state_model: FlavorTextStateModel = app.state.flavor_text_state_model
        bridge: SessionAudioBridge | None = None
        default_demo_mode = app.state.settings.demo_mode.enabled_by_default
        demo_last_announced_task_id: str | None = None
        demo_last_announced_state: str | None = None
        demo_opener_sent = False
        demo_camera_request_sent = False
        demo_room_scan_sent = False
        demo_calibration_sent = False
        demo_diagnosis_question_sent = False
        demo_diagnosis_interpretation_sent = False
        demo_final_closure_sent = False
        demo_case_report_auto_end_triggered = False
        demo_self_report_attempt_state: dict[str, dict[str, int]] = {}
        room_scan_context_primed = False
        task_vision_last_primed_id: str | None = None
        room_scan_usable_frame_count = 0
        room_scan_warning_sent = False
        last_room_scan_quality_reason: str | None = None
        room_scan_last_eval_frame_count = 0
        state_machine = SessionStateMachine(
            session_id=session_id,
            forward_envelope=lambda message: manager.send_json(session_id, message),
            incident_store=incident_store,
            session_store=firestore_session_store,
            demo_mode_enabled=default_demo_mode,
        )

        normal_mode_guidance = NormalModeOperatorGuidanceOrchestrator(
            session_id=session_id,
            flavor_model=flavor_text_state_model,
        )

        async def emit_operator_guidance(
            directive: OperatorGuidanceDirective,
        ) -> None:
            await forward_component_envelope(
                {
                    "type": "transcript",
                    "sessionId": session_id,
                    "payload": {
                        "speaker": "operator",
                        "text": directive.text,
                        "isFinal": True,
                        "source": directive.source,
                        "beat": directive.beat,
                    },
                }
            )

        def reset_room_scan_tracking() -> None:
            nonlocal room_scan_usable_frame_count
            nonlocal room_scan_warning_sent
            nonlocal last_room_scan_quality_reason
            nonlocal room_scan_last_eval_frame_count

            room_scan_usable_frame_count = 0
            room_scan_warning_sent = False
            last_room_scan_quality_reason = None
            room_scan_last_eval_frame_count = 0

        async def maybe_emit_room_scan_rejection(reason: str) -> None:
            nonlocal room_scan_warning_sent

            if bridge is None or state_machine.state != "room_sweep":
                return
            if bridge.is_operator_turn_active() or room_scan_warning_sent:
                return

            room_scan_warning_sent = True
            await bridge.send_operator_guidance(
                _room_scan_rejection_line(reason),
                source="session_guidance",
            )
            log_event(
                LOGGER,
                logging.INFO,
                "room_scan_rejection_guidance_sent",
                session_id=session_id,
                reason=reason,
            )

        async def perform_room_scan_verification(payload: dict[str, Any]) -> None:
            nonlocal room_scan_context_primed
            nonlocal room_scan_warning_sent

            if bridge is None:
                raise VerificationFlowError(
                    "Room scan confirmation is not available right now."
                )
            if state_machine.state not in {"room_sweep", "calibration"}:
                raise VerificationFlowError(
                    f"Ready to Verify is not legal from state {state_machine.state}."
                )
            if bridge.is_operator_turn_active():
                await bridge.interrupt_operator_turn(reason="room_verify_request")

            frame_data = payload.get("data")
            frame_mime_type = payload.get("mimeType")
            if not isinstance(frame_data, str):
                await bridge.send_operator_guidance(
                    "One second. Capturing the room view.",
                    source="verification_flow",
                )
                await manager.send_json(
                    session_id,
                    {
                        "type": "room_verification_request",
                        "sessionId": session_id,
                        "payload": {
                            "source": payload.get("source") if isinstance(payload.get("source"), str) else "verification_flow",
                        },
                    },
                )
                log_event(
                    LOGGER,
                    logging.INFO,
                    "room_verification_capture_requested",
                    session_id=session_id,
                    source=payload.get("source") if isinstance(payload.get("source"), str) else "verification_flow",
                )
                return

            await bridge.send_room_scan_frame(
                frame_data,
                mime_type=frame_mime_type if isinstance(frame_mime_type, str) and frame_mime_type.strip() else "image/jpeg",
                enforce_brightness_gate=False,
            )

            await bridge.send_operator_guidance(
                "One second. Verifying the room view.",
                source="verification_flow",
            )
            if not await bridge.wait_for_operator_turn_idle(timeout=12.0):
                raise VerificationFlowError(
                    "The room verification prompt did not finish cleanly. Hold the frame and try again."
                )


            await bridge.request_room_scan_readiness_check()
            readiness_status, readiness_reason = await bridge.wait_for_room_scan_readiness(
                timeout=10.0,
            )
            if readiness_status != "ready":
                rejection_reason = (
                    readiness_reason
                    or last_room_scan_quality_reason
                    or "insufficient_view"
                )
                room_scan_warning_sent = False
                await maybe_emit_room_scan_rejection(rejection_reason)
                raise VerificationFlowError(
                    "The operator still does not have a usable room view. Fix the frame and try again."
                )

            captured_payload = {
                "status": "captured",
            }
            captured_at = payload.get("capturedAt")
            if isinstance(captured_at, str) and captured_at.strip():
                captured_payload["capturedAt"] = captured_at.strip()

            await state_machine.handle_calibration_status(captured_payload)
            room_scan_context_primed = False
            reset_room_scan_tracking()
            await bridge.reset_for_setup_transition(reason="calibration_captured")
            calibration_snapshot = state_machine.to_payload()
            await forward_component_envelope(
                {
                    "type": "session_state",
                    "sessionId": session_id,
                    "payload": calibration_snapshot,
                }
            )
            log_event(
                LOGGER,
                logging.INFO,
                "websocket_room_scan_verification_completed",
                session_id=session_id,
            )

        async def forward_component_envelope(message: dict[str, Any]) -> None:
            changed = state_machine.observe_outbound_envelope(message)
            guidance_transcript = _extract_guidance_transcript(message)
            payload = message.get("payload")
            if (
                cloud_proof_registry is not None
                and message.get("type") == "session_state"
                and isinstance(payload, dict)
            ):
                cloud_proof_registry.observe_snapshot(session_id, payload)
            await manager.send_json(session_id, message)
            if (
                bridge is not None
                and message.get("type") == "session_state"
                and isinstance(payload, dict)
            ):
                bridge.update_session_context(
                    state_name=payload.get("state") if isinstance(payload.get("state"), str) else None,
                    camera_ready=payload.get("cameraReady") is True,
                )
                if (
                    payload.get("cameraReady") is not True
                    or payload.get("state") != "room_sweep"
                    or payload.get("calibrationCapturedAt") is not None
                ):
                    reset_room_scan_tracking()
            if guidance_transcript is not None and bridge is not None:
                guidance_text, guidance_source = guidance_transcript
                await bridge.send_operator_guidance(
                    guidance_text,
                    source=guidance_source,
                )

            if (
                message.get("type") == "transcript"
                and isinstance(payload, dict)
                and payload.get("speaker") == "operator"
            ):
                gemini_vision_engine.observe_operator_transcript(
                    str(payload.get("text", "")),
                    source=payload.get("source") if isinstance(payload.get("source"), str) else None,
                    is_final=payload.get("isFinal") is True,
                )

            # Watch for ROOM_FEATURES markers in operator transcripts from
            # Gemini's room scan - parse them and feed into the state machine
            # so the protocol planner uses AI-observed room features.
            msg_payload_for_scan = message.get("payload")
            if (
                message.get("type") == "transcript"
                and isinstance(msg_payload_for_scan, dict)
                and msg_payload_for_scan.get("speaker") == "operator"
                and not state_machine.demo_mode_enabled
                and state_machine.ai_observed_affordances is None
            ):
                operator_text = msg_payload_for_scan.get("text", "")
                if isinstance(operator_text, str) and "ROOM_FEATURES" in operator_text:
                    parsed = parse_room_scan_affordances(operator_text)
                    if parsed is not None:
                        ai_affordances = ObservedAffordances(
                            threshold_available=parsed.get("threshold", False),
                            flat_surface_available=parsed.get("flat_surface", False),
                            paper_available=parsed.get("paper", False),
                            light_controllable=parsed.get("light_controllable", False),
                            reflective_surface_available=parsed.get("reflective_surface", False),
                            water_source_nearby=parsed.get("water_source", False),
                        )
                        state_machine.set_ai_observed_affordances(ai_affordances)
                        log_event(
                            LOGGER,
                            logging.INFO,
                            "room_scan_affordances_parsed",
                            session_id=session_id,
                            affordances=parsed,
                        )

            await handle_demo_dialogue_hooks(message)
            await handle_normal_guidance_hooks(message)
            await handle_self_report_hooks(message)
            if changed:
                await state_machine.emit_snapshot()

        async def maybe_prime_room_scan_context() -> None:
            nonlocal room_scan_context_primed
            if state_machine.demo_mode_enabled:
                return
            if bridge is None or room_scan_context_primed or state_machine.state != "room_sweep":
                return
            room_scan_context_primed = True
            await bridge.prime_room_scan_context()

        async def maybe_prime_task_vision_context() -> None:
            nonlocal task_vision_last_primed_id
            if state_machine.demo_mode_enabled:
                return
            if bridge is None or state_machine.state not in {"task_assigned", "waiting_ready", "recovery_active"}:
                return
            task_ctx = state_machine.current_task_context
            if not isinstance(task_ctx, dict):
                return
            ctx_task_id = task_ctx.get("taskId")
            if not isinstance(ctx_task_id, str) or ctx_task_id == task_vision_last_primed_id:
                return
            task_vision_last_primed_id = ctx_task_id
            task_name = task_ctx.get("taskName", "containment step")
            task_desc = task_ctx.get("operatorDescription", "perform the assigned step")
            await bridge.prime_task_vision_context(
                str(task_name),
                str(task_desc),
                task_id=ctx_task_id,
            )


        async def emit_demo_guidance(text: str) -> None:
            await forward_component_envelope(
                {
                    "type": "transcript",
                    "sessionId": session_id,
                    "payload": {
                        "speaker": "operator",
                        "text": text,
                        "isFinal": True,
                        "source": "demo_mode",
                    },
                }
            )
        async def emit_demo_guidance_for_task(
            task_id: str,
            text: str,
            *,
            delay_seconds: float = 0.0,
        ) -> None:
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
            current_task_id = _task_id_from_context(state_machine.current_task_context)
            if current_task_id != task_id:
                return
            if state_machine.state not in {"task_assigned", "waiting_ready", "recovery_active", "diagnosis_beat"}:
                return
            await emit_demo_guidance(text)

        def schedule_demo_guidance_for_task(
            task_id: str,
            text: str,
            *,
            delay_seconds: float = 0.0,
        ) -> None:
            async def runner() -> None:
                try:
                    await emit_demo_guidance_for_task(
                        task_id,
                        text,
                        delay_seconds=delay_seconds,
                    )
                except SessionTransportClosedError as exc:
                    log_event(
                        LOGGER,
                        logging.WARNING,
                        "demo_guidance_send_failed",
                        session_id=session_id,
                        task_id=task_id,
                        detail=str(exc),
                    )
                except Exception as exc:
                    log_event(
                        LOGGER,
                        logging.ERROR,
                        "demo_guidance_task_failed",
                        session_id=session_id,
                        task_id=task_id,
                        detail=str(exc),
                        error_type=type(exc).__name__,
                    )
                    LOGGER.exception(
                        "Unhandled exception in delayed demo guidance task for session %s",
                        session_id,
                    )

            asyncio.create_task(runner())

        async def emit_self_report_confirmation(
            *,
            confidence_band: str,
            last_verified_item: str | None,
            notes: str | None,
            reason: str,
            transcript_text: str,
        ) -> None:
            task_context = state_machine.current_task_context
            if not isinstance(task_context, dict):
                return
            previous_state = state_machine.begin_verification_request()
            try:
                await forward_component_envelope(
                    {
                        "type": "verification_result",
                        "sessionId": session_id,
                        "payload": {
                            "attemptId": f"self-report-{uuid4().hex}",
                            "status": "confirmed",
                            "confidenceBand": confidence_band,
                            "reason": reason,
                            "blockReason": None,
                            "lastVerifiedItem": last_verified_item,
                            "isMock": False,
                            "mockLabel": None,
                            "notes": notes,
                            "currentPathMode": state_machine.current_path_mode,
                            "taskContext": dict(task_context),
                            "rawTranscriptSnippet": transcript_text,
                        },
                    }
                )
            except Exception:
                state_machine.rollback(previous_state, "verifying")
                raise

        def recent_user_transcripts_for_current_task(
            task_context: dict[str, Any] | None,
        ) -> tuple[str, ...]:
            task_id = _task_id_from_context(task_context)
            if task_id is None:
                return ()

            assigned_at: str | None = None
            for entry in reversed(state_machine.task_history):
                if entry.get("taskId") != task_id or entry.get("outcome") != "assigned":
                    continue
                raw_at = entry.get("at")
                if isinstance(raw_at, str) and raw_at.strip():
                    assigned_at = raw_at.strip()
                break

            transcripts: list[str] = []
            for reference in state_machine.transcript_references:
                if reference.get("speaker") != "user":
                    continue
                transcript_text = reference.get("text")
                if not isinstance(transcript_text, str) or not transcript_text.strip():
                    continue
                reference_at = reference.get("at")
                if (
                    assigned_at is not None
                    and isinstance(reference_at, str)
                    and reference_at.strip()
                    and reference_at.strip() < assigned_at
                ):
                    continue
                transcripts.append(transcript_text.strip())
            return tuple(transcripts)

        def transcript_window_token_count(
            transcript_lines: tuple[str, ...],
            *,
            baseline_index: int = 0,
        ) -> int:
            if baseline_index >= len(transcript_lines):
                return 0
            return len(" ".join(transcript_lines[baseline_index:]).split())

        async def handle_self_report_hooks(message: dict[str, Any]) -> None:
            if message.get("type") != "transcript":
                return
            payload = message.get("payload")
            if not isinstance(payload, dict):
                return
            if payload.get("speaker") != "user" or payload.get("isFinal") is not True:
                return
            task_context = state_machine.current_task_context
            if not is_self_report_task_context(task_context):
                return
            if state_machine.state not in {"waiting_ready", "recovery_active"}:
                return
            text = payload.get("text")
            if not isinstance(text, str) or not text.strip():
                return

            task_id = _task_id_from_context(task_context)
            recent_user_transcripts = recent_user_transcripts_for_current_task(task_context)
            if state_machine.demo_mode_enabled and task_id == "T7":
                attempt_state = demo_self_report_attempt_state.get(
                    task_id,
                    {"attempt_count": 0, "baseline_index": 0},
                )
                attempt_count = attempt_state.get("attempt_count", 0)
                baseline_index = attempt_state.get("baseline_index", 0)
                token_count = transcript_window_token_count(
                    recent_user_transcripts,
                    baseline_index=baseline_index,
                )

                if attempt_count == 0:
                    if token_count >= 8 and bridge is not None:
                        demo_self_report_attempt_state[task_id] = {
                            "attempt_count": 1,
                            "baseline_index": len(recent_user_transcripts),
                        }
                        await bridge.interrupt_operator_turn(reason="demo_containment_phrase_retry")
                        await bridge.send_operator_guidance(
                            "Again. Stronger this time. More power. Repeat exactly after me: "
                            f"'{CONTAINMENT_PHRASE_TEXT}'",
                            source="operator_guidance",
                        )
                    return

                if token_count < 3:
                    return

                demo_self_report_attempt_state[task_id] = {
                    "attempt_count": 2,
                    "baseline_index": len(recent_user_transcripts),
                }
                await emit_self_report_confirmation(
                    confidence_band="medium",
                    last_verified_item=(
                        task_context.get("taskName")
                        if isinstance(task_context, dict)
                        else None
                    ),
                    notes="Demo mode resolved the containment phrase on the second live attempt.",
                    reason="The caller repeated the containment phrase with stronger delivery on the second demo attempt.",
                    transcript_text=text.strip(),
                )
                return

            resolution = resolve_self_report_response(task_context, text)
            if resolution.action == "confirm" and resolution.reason is not None:
                await emit_self_report_confirmation(
                    confidence_band=resolution.confidence_band or "medium",
                    last_verified_item=resolution.last_verified_item,
                    notes=resolution.notes,
                    reason=resolution.reason,
                    transcript_text=text.strip(),
                )
                return
            if resolution.action == "reprompt" and resolution.operator_line is not None and bridge is not None:
                await bridge.interrupt_operator_turn(reason="self_report_reprompt")
                await bridge.send_operator_guidance(
                    resolution.operator_line,
                    source="operator_guidance",
                )


        async def update_demo_barge_in(payload: dict[str, Any]) -> None:
            changed = state_machine.update_demo_barge_in(payload)
            if changed:
                await state_machine.emit_snapshot()

        # Create per-session Gemini Vision verification engine.
        # This replaces the global RealVerificationEngine so that
        # Gemini actually analyses captured frames during verification.
        gemini_vision_engine = GeminiVisionVerificationEngine(
            session_id=session_id,
            fallback_engine=(
                verification_engine
                if verification_engine is not None and not getattr(verification_engine, "is_mock", False)
                else None
            ),
        )
        # Use the vision engine as primary; fall back to the global
        # engine only when mock-verification mode is active.
        active_verification_engine: VerificationEngine | None = (
            verification_engine
            if verification_engine is not None
            and getattr(verification_engine, "is_mock", False)
            else gemini_vision_engine
        )

        verification_flow = SessionVerificationFlow(
            session_id=session_id,
            forward_envelope=forward_component_envelope,
            verification_engine=active_verification_engine,
            demo_mode_enabled=default_demo_mode,
        )
        capability_recovery = SessionCapabilityRecoveryManager(
            session_id=session_id,
            forward_envelope=forward_component_envelope,
        )

        async def handle_demo_dialogue_hooks(message: dict[str, Any]) -> None:
            nonlocal demo_last_announced_task_id
            nonlocal demo_last_announced_state
            nonlocal demo_opener_sent
            nonlocal demo_camera_request_sent
            nonlocal demo_room_scan_sent
            nonlocal demo_calibration_sent
            nonlocal demo_diagnosis_question_sent
            nonlocal demo_diagnosis_interpretation_sent

            nonlocal demo_final_closure_sent
            nonlocal demo_case_report_auto_end_triggered

            if not state_machine.demo_mode_enabled:
                return

            message_type = message.get("type")
            payload = message.get("payload")
            if not isinstance(payload, dict):
                return

            if message_type == "transcript":
                return

            if message_type == "verification_result":
                v_status = payload.get("status")
                v_task_ctx = payload.get("taskContext")
                if (
                    v_status == "confirmed"
                    and isinstance(v_task_ctx, dict)
                    and isinstance(v_task_ctx.get("taskId"), str)
                ):
                    if bridge is not None:
                        bridge.update_session_context(
                            state_name=state_machine.state,
                            camera_ready=state_machine.camera_ready,
                        )
                    completed_task_id = v_task_ctx["taskId"]
                    flavor = get_demo_flavor_for_task(completed_task_id)
                    if flavor is not None:
                        await emit_demo_guidance(flavor)

                    next_task_ctx = (
                        state_machine.current_task_context
                        if isinstance(state_machine.current_task_context, dict)
                        else None
                    )
                    next_task_id = (
                        next_task_ctx.get("taskId")
                        if isinstance(next_task_ctx, dict)
                        else None
                    )
                    if (
                        isinstance(next_task_id, str)
                        and next_task_id.strip()
                        and next_task_id != completed_task_id
                        and state_machine.state in {"task_assigned", "waiting_ready"}
                    ):
                        next_task_guidance = _build_task_assignment_guidance(
                            flavor_text_state_model,
                            session_id,
                            next_task_ctx,
                            demo_mode_enabled=True,
                        )
                        if next_task_guidance is not None:
                            demo_last_announced_task_id = next_task_id
                            if next_task_id == "T14":
                                schedule_demo_guidance_for_task(
                                    next_task_id,
                                    next_task_guidance,
                                    delay_seconds=DEMO_SOUND_PROMPT_DELAY_SECONDS,
                                )
                            else:
                                await emit_demo_guidance(next_task_guidance)
                return

            if message_type != "session_state":
                return

            state_name = payload.get("state")
            active_task_index = payload.get("activeTaskIndex")
            task_context = payload.get("currentTaskContext")
            task_id = task_context.get("taskId") if isinstance(task_context, dict) else None
            calibration_captured_at = payload.get("calibrationCapturedAt")

            demo_last_announced_state = state_name

            browser_mic_permission = payload.get("browserMicPermission")
            if state_name == "microphone_request" and not demo_opener_sent:
                demo_opener_sent = True
                opener_line = (
                    DEMO_OPENER_LINE_GRANTED
                    if browser_mic_permission == "granted"
                    else DEMO_OPENER_LINE_PROMPT
                )
                await emit_demo_guidance(opener_line)

            if state_name == "camera_request" and not demo_camera_request_sent:
                demo_camera_request_sent = True
                await emit_demo_guidance(DEMO_CAMERA_REQUEST_LINE)

            if state_name == "room_sweep" and not demo_room_scan_sent:
                demo_room_scan_sent = True
                await emit_demo_guidance(DEMO_ROOM_SCAN_LINE)

            task_guidance: str | None = None
            should_announce_new_task = (
                isinstance(task_id, str)
                and task_id.strip()
                and task_id != demo_last_announced_task_id
                and state_name in {"task_assigned", "waiting_ready"}
            )
            if should_announce_new_task:
                task_guidance = _build_task_assignment_guidance(
                    flavor_text_state_model,
                    session_id,
                    task_context,
                    demo_mode_enabled=True,
                )

            if calibration_captured_at and not demo_calibration_sent:
                demo_calibration_sent = True
                if task_guidance is not None and active_task_index == 0:
                    demo_last_announced_task_id = task_id
                    await emit_demo_guidance(
                        f"{DEMO_ROOM_SCAN_ASSESSMENT_LINE} {task_guidance}"
                    )
                    task_guidance = None
                else:
                    await emit_demo_guidance(DEMO_ROOM_SCAN_ASSESSMENT_LINE)

            if should_announce_new_task:
                demo_last_announced_task_id = task_id
                if task_guidance is not None:
                    if task_id == "T14":
                        schedule_demo_guidance_for_task(
                            task_id,
                            task_guidance,
                            delay_seconds=DEMO_SOUND_PROMPT_DELAY_SECONDS,
                        )
                    else:
                        await emit_demo_guidance(task_guidance)

            if (
                state_name in {"case_report", "ended"}
                and not demo_final_closure_sent
            ):
                demo_final_closure_sent = True
                await emit_demo_guidance(DEMO_FINAL_CLOSURE_LINE)
                if (
                    state_name == "case_report"
                    and not demo_case_report_auto_end_triggered
                ):
                    demo_case_report_auto_end_triggered = True
                    if bridge is not None:
                        await bridge.wait_for_operator_turn_idle(timeout=20.0)
                    await state_machine.handle_stop_request("demo_case_report_complete")

        async def handle_normal_guidance_hooks(message: dict[str, Any]) -> None:
            if state_machine.demo_mode_enabled:
                return

            # In normal mode, use CONTEXT_DIRECTIVE to let Gemini generate
            # contextual operator dialogue instead of authored templates.
            msg_type = message.get("type")
            msg_payload = message.get("payload")
            if msg_type == "verification_result" and isinstance(msg_payload, dict):
                v_status = msg_payload.get("status", "unknown")
                v_task_ctx = msg_payload.get("taskContext")
                task_name = (
                    v_task_ctx.get("taskName", "the current task")
                    if isinstance(v_task_ctx, dict)
                    else "the current task"
                )
                context_text = (
                    f"The caller just finished attempting '{task_name}'. "
                    f"Verification result: {v_status}. "
                )
                if v_status == "confirmed":
                    context_text += (
                        "Acknowledge this success briefly, weave in a short "
                        "containment lore observation, then transition to "
                        "what the caller needs to do next."
                    )
                elif v_status == "unconfirmed":
                    task_id = (
                        v_task_ctx.get("taskId", "unknown")
                        if isinstance(v_task_ctx, dict)
                        else "unknown"
                    )
                    block_reason = msg_payload.get("blockReason", "unclear")
                    context_text += (
                        AI_RECOVERY_DIRECTIVE_TEMPLATE.format(
                            task_name=task_name,
                            task_id=task_id,
                            status=v_status,
                            block_reason=block_reason,
                        )
                    )
                else:
                    context_text += (
                        "The step was self-reported. Acknowledge it and "
                        "move on to the next containment instruction."
                    )

        async def start_verification_from_bridge(payload: dict[str, Any]) -> None:
            if state_machine.state in {"room_sweep", "calibration"}:
                await perform_room_scan_verification(payload)
                return

            current_task_context = state_machine.current_task_context
            if is_self_report_task_context(current_task_context):
                if bridge is not None:
                    await bridge.interrupt_operator_turn(reason="self_report_verify_redirect")
                    await bridge.send_operator_guidance(
                        build_self_report_verify_reminder(current_task_context),
                        source="operator_guidance",
                    )
                return

            try:
                prepared_payload = state_machine.prepare_verification_request(payload)

                if bridge is not None:
                    # Clear any active or queued operator speech so the
                    # verification acknowledgment is heard before results.
                    await bridge.interrupt_operator_turn(reason="task_verify_request")
                    await bridge.send_operator_guidance(
                        "Hold still. One second. Verifying.",
                        source="verification_flow",
                    )

                previous_state = state_machine.begin_verification_request()
                try:
                    if bridge is not None:
                        bridge.update_session_context(
                            state_name="verifying",
                            camera_ready=state_machine.camera_ready,
                        )
                    await verification_flow.start_verification(prepared_payload)
                except Exception:
                    state_machine.rollback(previous_state, "verifying")
                    raise
                await state_machine.emit_snapshot()
            except SessionStateMachineError as exc:
                raise VerificationFlowError(str(exc)) from exc


        async def handle_swap_request_from_bridge(payload: dict[str, Any]) -> None:
            try:
                prepared_payload = state_machine.prepare_swap_request(payload)
                previous_state = state_machine.begin_swap_request()
                try:
                    await capability_recovery.handle_swap_request(prepared_payload)
                except Exception:
                    state_machine.rollback(previous_state, "swap_pending")
                    raise
                await state_machine.emit_snapshot()
            except (SessionStateMachineError, CapabilityRecoveryError) as exc:
                await manager.send_json(
                    session_id,
                    build_error_envelope(
                        code="capability_recovery_error",
                        detail=str(exc),
                        session_id=session_id,
                    ),
                )
                log_event(
                    LOGGER,
                    logging.WARNING,
                    "websocket_capability_recovery_rejected",
                    session_id=session_id,
                    message_type="swap_request",
                    detail=str(exc),
                )

        bridge = SessionAudioBridge(
            session_id=session_id,
            gemini_session_manager=gemini_live_session_manager,
            forward_envelope=forward_component_envelope,
            start_verification=start_verification_from_bridge,
            handle_swap_request=handle_swap_request_from_bridge,
            record_user_transcript=verification_flow.record_user_transcript,
            update_demo_barge_in=update_demo_barge_in,
            record_hidden_operator_transcript=gemini_vision_engine.observe_operator_transcript,
        )

        # Attach the Gemini Live session to the vision engine so it can
        # send frames for analysis during verification.  The session is
        # lazy - it is created when the bridge opens its first stream -
        # so we attach via property reference on the bridge.
        gemini_vision_engine.attach_session(bridge.gemini_session)

        log_event(
            LOGGER,
            logging.INFO,
            "websocket_connected",
            session_id=session_id,
            active_connections=manager.active_count,
        )

        try:
            while True:
                try:
                    raw_message = await _receive_json_message(websocket)
                    envelope = parse_session_envelope(raw_message)
                except InvalidSessionEnvelope as exc:
                    await manager.send_json(
                        session_id,
                        build_error_envelope(
                            code="invalid_message",
                            detail=str(exc),
                            session_id=session_id,
                        ),
                    )
                    log_event(
                        LOGGER,
                        logging.WARNING,
                        "websocket_invalid_message",
                        session_id=session_id,
                        detail=str(exc),
                    )
                    continue

                log_event(
                    LOGGER,
                    logging.INFO,
                    "websocket_message_received",
                    session_id=session_id,
                    message_type=envelope.message_type,
                )

                try:
                    if envelope.message_type == "client_connect":
                        state_machine.configure_demo_mode(
                            _resolve_demo_mode_request(
                                envelope.payload,
                                default_enabled=default_demo_mode,
                            )
                        )
                        verification_flow.set_demo_mode_enabled(state_machine.demo_mode_enabled)
                        await bridge.configure_demo_mode(enabled=state_machine.demo_mode_enabled)
                        await state_machine.handle_client_connect(envelope.payload)
                        # Replay the session state through the full guidance
                        # pipeline.  handle_client_connect() already sent the
                        # snapshot to the client via emit_snapshot(), but that
                        # goes through manager.send_json directly - it never
                        # passes through forward_component_envelope, so the
                        # guidance hooks (demo and normal) never fire and the
                        # opener text never reaches Gemini for speech.
                        # By forwarding the snapshot here, the hooks process
                        # the "microphone_request" state and emit the operator
                        # guidance directive, which in turn calls
                        # bridge.send_operator_guidance() to make Gemini speak.
                        connect_snapshot = state_machine.to_payload()
                        await forward_component_envelope(
                            {
                                "type": "session_state",
                                "sessionId": session_id,
                                "payload": connect_snapshot,
                            }
                        )
                        log_event(
                            LOGGER,
                            logging.INFO,
                            "cloud_proof_session_locator",
                            session_id=session_id,
                            log_query_hint=f'jsonPayload.session_id="{session_id}"',
                        )
                    elif envelope.message_type == "mic_status":
                        verification_flow.update_microphone_state(envelope.payload)
                        await state_machine.handle_mic_status(envelope.payload)
                        if envelope.payload.get("streaming") is True:
                            await bridge.start_stream(envelope.payload)
                        elif envelope.payload.get("streaming") is False:
                            reason = envelope.payload.get("reason")
                            await bridge.stop_stream(
                                reason=reason if isinstance(reason, str) and reason else "client_requested"
                            )
                        # Replay so guidance hooks emit mic-confirmed /
                        # camera-request lines to Gemini.
                        mic_snapshot = state_machine.to_payload()
                        await forward_component_envelope(
                            {
                                "type": "session_state",
                                "sessionId": session_id,
                                "payload": mic_snapshot,
                            }
                        )
                    elif envelope.message_type == "audio_chunk":
                        await bridge.forward_audio_chunk(envelope.payload)
                    elif envelope.message_type == "camera_status":
                        verification_flow.update_camera_state(envelope.payload)
                        await state_machine.handle_camera_status(envelope.payload)
                        # Replay so guidance hooks emit room-sweep /
                        # camera-request lines to Gemini.
                        cam_snapshot = state_machine.to_payload()
                        await forward_component_envelope(
                            {
                                "type": "session_state",
                                "sessionId": session_id,
                                "payload": cam_snapshot,
                            }
                        )
                        if not state_machine.camera_ready:
                            room_scan_context_primed = False
                    elif envelope.message_type == "verify_request":
                        await start_verification_from_bridge(envelope.payload)
                    elif envelope.message_type == "swap_request":
                        prepared_payload = state_machine.prepare_swap_request(envelope.payload)
                        previous_state = state_machine.begin_swap_request()
                        try:
                            await capability_recovery.handle_swap_request(prepared_payload)
                        except Exception:
                            state_machine.rollback(previous_state, "swap_pending")
                            raise
                        await state_machine.emit_snapshot()
                    elif envelope.message_type == "frame":
                        await verification_flow.ingest_frame(envelope.payload)
                        # Store frame data in the vision engine so it
                        # can send the best frame to Gemini when evaluate() is called.
                        frame_data = envelope.payload.get("data")
                        attempt_id = envelope.payload.get("attemptId")
                        if isinstance(frame_data, str):
                            if isinstance(attempt_id, str):
                                existing = gemini_vision_engine._frame_data_store.get(attempt_id, [])
                                existing.append(frame_data)
                                gemini_vision_engine.store_frame_data(attempt_id, existing)
                            # Also re-attach the session in case it was
                            # lazily created after bridge init.
                            if bridge is not None and gemini_vision_engine._gemini_session is None:
                                gemini_vision_engine.attach_session(bridge.gemini_session)
                    elif envelope.message_type == "room_scan_frame":
                        # Passive room scan frames for Gemini context during setup.
                        frame_data = envelope.payload.get("data")
                        frame_usable = _is_room_scan_frame_usable(envelope.payload)
                        if frame_usable:
                            room_scan_usable_frame_count += 1
                            room_scan_warning_sent = False
                            last_room_scan_quality_reason = None
                        else:
                            room_scan_usable_frame_count = 0
                            last_room_scan_quality_reason = _room_scan_quality_reason(envelope.payload)
                        if isinstance(frame_data, str) and bridge is not None:
                            await maybe_prime_room_scan_context()
                            frame_sent = await bridge.send_room_scan_frame(
                                frame_data,
                                enforce_brightness_gate=False,
                            )
                            log_event(
                                LOGGER,
                                logging.INFO,
                                "websocket_room_scan_frame_forwarded",
                                session_id=session_id,
                                frame_sent=frame_sent,
                                frame_usable=frame_usable,
                                usable_frame_count=room_scan_usable_frame_count,
                                quality_reason=last_room_scan_quality_reason,
                            )
                    elif envelope.message_type == "calibration_status":
                        # Backwards-compatible fallback: treat manual calibration as an explicit room verification request.
                        await perform_room_scan_verification(envelope.payload)
                    elif envelope.message_type == "client_event":
                        await state_machine.handle_client_event(envelope.payload)
                        log_event(
                            LOGGER,
                            logging.INFO,
                            "websocket_client_event_handled",
                            session_id=session_id,
                        )
                    elif envelope.message_type == "task_vision_frame":
                        # Continuous camera frames during task execution
                        frame_data = envelope.payload.get("data")
                        if isinstance(frame_data, str):
                            verification_flow.observe_task_vision_frame(
                                envelope.payload,
                                state_machine.current_task_context,
                            )
                        if isinstance(frame_data, str) and bridge is not None:
                            await maybe_prime_task_vision_context()
                            frame_sent = await bridge.send_room_scan_frame(frame_data)
                            log_event(
                                LOGGER,
                                logging.INFO,
                                "websocket_task_vision_frame_forwarded",
                                session_id=session_id,
                                task_id=_task_id_from_context(state_machine.current_task_context),
                                frame_sent=frame_sent,
                            )
                    elif envelope.message_type == "pause":
                        await state_machine.handle_pause_request(envelope.payload)
                        if envelope.payload.get("paused") is True:
                            await verification_flow.cancel_active_attempt("session_paused")
                    elif envelope.message_type == "stop":
                        disconnect_reason = "stop_requested"
                        reason = envelope.payload.get("reason")
                        await verification_flow.cancel_active_attempt("session_ended")
                        await state_machine.handle_stop_request(
                            reason if isinstance(reason, str) and reason else disconnect_reason
                        )
                    elif envelope.message_type in _PLACEHOLDER_ONLY_TYPES:
                        log_event(
                            LOGGER,
                            logging.INFO,
                            "websocket_placeholder_message_accepted",
                            session_id=session_id,
                            message_type=envelope.message_type,
                        )

                except AudioBridgePayloadError as exc:
                    await manager.send_json(
                        session_id,
                        build_error_envelope(
                            code="invalid_audio_payload",
                            detail=str(exc),
                            session_id=session_id,
                        ),
                    )
                    log_event(
                        LOGGER,
                        logging.WARNING,
                        "websocket_audio_payload_rejected",
                        session_id=session_id,
                        message_type=envelope.message_type,
                        detail=str(exc),
                    )
                    continue
                except GeminiLiveError as exc:
                    await manager.send_json(
                        session_id,
                        build_error_envelope(
                            code="gemini_live_error",
                            detail=str(exc),
                            session_id=session_id,
                        ),
                    )
                    log_event(
                        LOGGER,
                        logging.ERROR,
                        "websocket_gemini_bridge_failed",
                        session_id=session_id,
                        message_type=envelope.message_type,
                        detail=str(exc),
                    )
                    continue
                except VerificationFlowError as exc:
                    await manager.send_json(
                        session_id,
                        build_error_envelope(
                            code="verification_flow_error",
                            detail=str(exc),
                            session_id=session_id,
                        ),
                    )
                    log_event(
                        LOGGER,
                        logging.WARNING,
                        "websocket_verification_flow_rejected",
                        session_id=session_id,
                        message_type=envelope.message_type,
                        detail=str(exc),
                    )
                    continue
                except CapabilityRecoveryError as exc:
                    await manager.send_json(
                        session_id,
                        build_error_envelope(
                            code="capability_recovery_error",
                            detail=str(exc),
                            session_id=session_id,
                        ),
                    )
                    log_event(
                        LOGGER,
                        logging.WARNING,
                        "websocket_capability_recovery_rejected",
                        session_id=session_id,
                        message_type=envelope.message_type,
                        detail=str(exc),
                    )
                    continue
                except SessionStateMachineError as exc:
                    await manager.send_json(
                        session_id,
                        build_error_envelope(
                            code="session_state_error",
                            detail=str(exc),
                            session_id=session_id,
                        ),
                    )
                    log_event(
                        LOGGER,
                        logging.WARNING,
                        "websocket_state_machine_rejected",
                        session_id=session_id,
                        message_type=envelope.message_type,
                        detail=str(exc),
                    )
                    continue
                if envelope.message_type not in _NO_ACK_MESSAGE_TYPES:
                    await manager.send_json(
                        session_id,
                        build_ack_envelope(envelope, session_id),
                    )

                if envelope.message_type == "stop":
                    await bridge.close(reason=disconnect_reason)
                    await websocket.close(code=1000, reason="stop requested")
                    break

        except WebSocketDisconnect as exc:
            disconnect_reason = "client_disconnect"
            disconnect_code = exc.code
        except SessionTransportClosedError as exc:
            disconnect_reason = "transport_send_failed"
            disconnect_code = 1006
            current_task_context = state_machine.current_task_context
            log_event(
                LOGGER,
                logging.WARNING,
                "websocket_transport_send_failed",
                session_id=session_id,
                detail=str(exc),
                state=state_machine.state,
                task_id=_task_id_from_context(current_task_context),
                task_name=(
                    current_task_context.get("taskName")
                    if isinstance(current_task_context, dict)
                    else None
                ),
            )
        except Exception as exc:
            disconnect_reason = "server_error"
            disconnect_code = 1011
            current_task_context = state_machine.current_task_context
            log_event(
                LOGGER,
                logging.ERROR,
                "websocket_gateway_unhandled_exception",
                session_id=session_id,
                detail=str(exc),
                error_type=type(exc).__name__,
                state=state_machine.state,
                task_id=_task_id_from_context(current_task_context),
                task_name=(
                    current_task_context.get("taskName")
                    if isinstance(current_task_context, dict)
                    else None
                ),
            )
            LOGGER.exception(
                "Unhandled exception in WebSocket gateway for session %s",
                session_id,
            )
            try:
                await websocket.close(code=1011, reason="internal server error")
            except Exception:
                pass
        finally:
            if state_machine.state != "ended":
                with_state_reason = disconnect_reason
                try:
                    await state_machine.handle_stop_request(with_state_reason)
                except SessionStateMachineError:
                    pass
            await bridge.close(reason=disconnect_reason)
            await verification_flow.close()
            manager.disconnect(session_id)
            if cloud_proof_registry is not None:
                cloud_proof_registry.end_session(session_id, reason=disconnect_reason)
            log_event(
                LOGGER,
                logging.INFO,
                "websocket_disconnected",
                session_id=session_id,
                code=disconnect_code,
                reason=disconnect_reason,
                active_connections=manager.active_count,
            )

























