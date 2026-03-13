"""WebSocket gateway for client session traffic and backend session state."""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from .audio_bridge import AudioBridgePayloadError, SessionAudioBridge
from .capability_recovery import CapabilityRecoveryError, SessionCapabilityRecoveryManager
from .gemini_live import GeminiLiveError, GeminiLiveSessionManager
from .incident_classification import IncidentClassificationStore
from .logging_utils import log_event
from .session_state_machine import SessionStateMachine, SessionStateMachineError
from .session_transport import (
    InvalidSessionEnvelope,
    build_ack_envelope,
    build_error_envelope,
    parse_session_envelope,
)
from .verification_engine import VerificationEngine
from .verification_flow import SessionVerificationFlow, VerificationFlowError

LOGGER = logging.getLogger("ghostline.backend.websocket")
_NO_ACK_MESSAGE_TYPES = frozenset({"audio_chunk"})
_PLACEHOLDER_ONLY_TYPES = frozenset({"transcript"})


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
        state_machine = SessionStateMachine(
            session_id=session_id,
            forward_envelope=lambda message: manager.send_json(session_id, message),
            incident_store=incident_store,
            session_store=firestore_session_store,
        )

        async def forward_component_envelope(message: dict[str, Any]) -> None:
            changed = state_machine.observe_outbound_envelope(message)
            await manager.send_json(session_id, message)
            if changed:
                await state_machine.emit_snapshot()

        verification_flow = SessionVerificationFlow(
            session_id=session_id,
            forward_envelope=forward_component_envelope,
            verification_engine=verification_engine,
        )
        capability_recovery = SessionCapabilityRecoveryManager(
            session_id=session_id,
            forward_envelope=forward_component_envelope,
        )

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
        )

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
                        await state_machine.handle_client_connect()
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
                    elif envelope.message_type == "audio_chunk":
                        await bridge.forward_audio_chunk(envelope.payload)
                    elif envelope.message_type == "camera_status":
                        verification_flow.update_camera_state(envelope.payload)
                        await state_machine.handle_camera_status(envelope.payload)
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
            log_event(
                LOGGER,
                logging.INFO,
                "websocket_disconnected",
                session_id=session_id,
                code=disconnect_code,
                reason=disconnect_reason,
                active_connections=manager.active_count,
            )

