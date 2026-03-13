"""Transport-level message schemas for the Prompt 6 WebSocket gateway."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

SESSION_MESSAGE_TYPES: Final[tuple[str, ...]] = (
    "client_connect",
    "mic_status",
    "audio_chunk",
    "camera_status",
    "transcript",
    "frame",
    "verify_request",
    "swap_request",
    "pause",
    "stop",
)

_ALLOWED_TOP_LEVEL_KEYS: Final[frozenset[str]] = frozenset(
    {"type", "payload", "requestId", "clientTimestamp"}
)


class InvalidSessionEnvelope(ValueError):
    """Raised when an incoming WebSocket envelope is missing required shape."""


@dataclass(frozen=True)
class SessionEnvelope:
    message_type: str
    payload: dict[str, Any]
    request_id: str | None = None
    client_timestamp: str | None = None


def parse_session_envelope(raw_message: Any) -> SessionEnvelope:
    if not isinstance(raw_message, dict):
        raise InvalidSessionEnvelope("Envelope must be a JSON object.")

    unknown_keys = set(raw_message) - _ALLOWED_TOP_LEVEL_KEYS
    if unknown_keys:
        joined_keys = ", ".join(sorted(unknown_keys))
        raise InvalidSessionEnvelope(f"Unknown envelope key(s): {joined_keys}.")

    message_type = raw_message.get("type")
    if not isinstance(message_type, str) or not message_type.strip():
        raise InvalidSessionEnvelope("Envelope type must be a non-empty string.")
    if message_type not in SESSION_MESSAGE_TYPES:
        raise InvalidSessionEnvelope(f"Unsupported message type: {message_type}.")

    payload = raw_message.get("payload", {})
    if not isinstance(payload, dict):
        raise InvalidSessionEnvelope("Envelope payload must be a JSON object.")

    request_id = raw_message.get("requestId")
    if request_id is not None and not isinstance(request_id, str):
        raise InvalidSessionEnvelope("requestId must be a string when provided.")

    client_timestamp = raw_message.get("clientTimestamp")
    if client_timestamp is not None and not isinstance(client_timestamp, str):
        raise InvalidSessionEnvelope(
            "clientTimestamp must be a string when provided."
        )

    return SessionEnvelope(
        message_type=message_type,
        payload=payload,
        request_id=request_id,
        client_timestamp=client_timestamp,
    )


def build_ack_envelope(envelope: SessionEnvelope, session_id: str) -> dict[str, Any]:
    ack_payload: dict[str, Any] = {
        "status": "accepted",
        "receivedType": envelope.message_type,
    }

    if envelope.message_type == "client_connect":
        ack_payload["supportedTypes"] = list(SESSION_MESSAGE_TYPES)

    return {
        "type": envelope.message_type,
        "sessionId": session_id,
        "requestId": envelope.request_id,
        "payload": ack_payload,
    }


def build_error_envelope(
    *,
    code: str,
    detail: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    envelope: dict[str, Any] = {
        "type": "error",
        "payload": {
            "status": "error",
            "code": code,
            "detail": detail,
        },
    }

    if session_id is not None:
        envelope["sessionId"] = session_id

    return envelope
