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
            await websocket.send_json(message)


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
        demo_pending_task_guidance: str | None = None
        demo_final_closure_sent = False
        room_scan_context_primed = False
        task_vision_last_primed_id: str | None = None
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
            if changed:
                await state_machine.emit_snapshot()

        async def maybe_prime_room_scan_context() -> None:
            nonlocal room_scan_context_primed
            if bridge is None or room_scan_context_primed or state_machine.state != "room_sweep":
                return
            room_scan_context_primed = True
            await bridge.prime_room_scan_context()

        async def maybe_prime_task_vision_context() -> None:
            nonlocal task_vision_last_primed_id
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
            nonlocal demo_pending_task_guidance
            nonlocal demo_final_closure_sent

            if not state_machine.demo_mode_enabled:
                return

            message_type = message.get("type")
            payload = message.get("payload")
            if not isinstance(payload, dict):
                return

            if message_type == "transcript":
                if (
                    demo_diagnosis_question_sent
                    and not demo_diagnosis_interpretation_sent
                    and payload.get("speaker") == "user"
                    and payload.get("isFinal") is True
                    and isinstance(payload.get("text"), str)
                    and payload.get("text").strip()
                ):
                    demo_diagnosis_interpretation_sent = True
                    await emit_demo_guidance(DEMO_DIAGNOSIS_INTERPRETATION_LINE)
                    if demo_pending_task_guidance is not None:
                        pending_guidance = demo_pending_task_guidance
                        demo_pending_task_guidance = None
                        await emit_demo_guidance(pending_guidance)
                return

            if message_type == "verification_result":
                v_status = payload.get("status")
                v_task_ctx = payload.get("taskContext")
                if (
                    v_status == "confirmed"
                    and isinstance(v_task_ctx, dict)
                    and isinstance(v_task_ctx.get("taskId"), str)
                ):
                    flavor = get_demo_flavor_for_task(v_task_ctx["taskId"])
                    if flavor is not None:
                        await emit_demo_guidance(flavor)
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

            if calibration_captured_at and not demo_calibration_sent:
                demo_calibration_sent = True
                await emit_demo_guidance(DEMO_ROOM_SCAN_ASSESSMENT_LINE)

            if (
                isinstance(task_id, str)
                and task_id.strip()
                and task_id != demo_last_announced_task_id
                and state_name in {"task_assigned", "waiting_ready"}
            ):
                task_guidance = _build_task_assignment_guidance(
                    flavor_text_state_model,
                    session_id,
                    task_context,
                    demo_mode_enabled=True,
                )
                demo_last_announced_task_id = task_id
                if task_guidance is not None:
                    if active_task_index == 1 and not demo_diagnosis_question_sent:
                        demo_pending_task_guidance = task_guidance
                        demo_diagnosis_question_sent = True
                        await emit_demo_guidance(DEMO_DIAGNOSIS_QUESTION_LINE)
                    else:
                        await emit_demo_guidance(task_guidance)

            if (
                state_name in {"case_report", "ended"}
                and not demo_final_closure_sent
            ):
                demo_final_closure_sent = True
                await emit_demo_guidance(DEMO_FINAL_CLOSURE_LINE)

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
                if bridge is not None:
                    await bridge.send_context_directive(context_text)
                return

            # Fall back to authored templates for non-verification envelopes.
            for directive in normal_mode_guidance.consume_envelope(message):
                await emit_operator_guidance(directive)

        async def start_verification_from_bridge(payload: dict[str, Any]) -> None:
            try:
                prepared_payload = state_machine.prepare_verification_request(payload)
                previous_state = state_machine.begin_verification_request()
                try:
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
                            firestore_document_path=(
                                firestore_session_store.document_path(session_id)
                                if firestore_session_store is not None and getattr(firestore_session_store, "is_configured", False)
                                else None
                            ),
                            firestore_collection=(
                                getattr(firestore_session_store, "collection", None)
                                if firestore_session_store is not None
                                else None
                            ),
                            log_query_hint=f'jsonPayload.session_id="{session_id}"',
                            proof_endpoint="/ops/proof/active-session",
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
                        prepared_payload = state_machine.prepare_verification_request(envelope.payload)
                        previous_state = state_machine.begin_verification_request()
                        try:
                            await verification_flow.start_verification(prepared_payload)
                        except Exception:
                            state_machine.rollback(previous_state, "verifying")
                            raise
                        await state_machine.emit_snapshot()
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
                        # Room scan frame for Gemini vision during room setup.
                        frame_data = envelope.payload.get("data")
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
                            )
                    elif envelope.message_type == "calibration_status":
                        # Room setup auto-complete: useRoomScan sends this after a few usable frames
                        await state_machine.handle_calibration_status(envelope.payload)
                        room_scan_context_primed = False
                        if bridge is not None:
                            await bridge.reset_for_setup_transition(
                                reason="calibration_captured"
                            )
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
                            "websocket_calibration_status_handled",
                            session_id=session_id,
                        )
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











