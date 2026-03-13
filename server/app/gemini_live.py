"""Dedicated Gemini Live session manager for backend-only Vertex AI integration."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from .config import GeminiLiveSettings
from .logging_utils import log_event

if TYPE_CHECKING:
    from google import genai as genai_module
    from google.genai import types as genai_types

LOGGER = logging.getLogger("ghostline.backend.gemini_live")


class GeminiLiveError(RuntimeError):
    """Base error for backend Gemini Live lifecycle issues."""


class GeminiLiveDependencyError(GeminiLiveError):
    """Raised when the Google GenAI SDK is unavailable at runtime."""


class GeminiLiveConfigurationError(GeminiLiveError):
    """Raised when environment config is incomplete for Vertex AI usage."""


class GeminiLiveSessionError(GeminiLiveError):
    """Raised when a live session action fails."""


@dataclass(frozen=True)
class GeminiLiveEvent:
    event_type: str
    session_id: str
    payload: dict[str, Any]


SdkLoader = Callable[[], tuple[Any, Any]]
SessionClosedCallback = Callable[[str], None]


class GeminiLiveSession:
    """Wraps a single Gemini Live connection and normalizes server events."""

    def __init__(
        self,
        *,
        session_id: str,
        context_manager: AbstractAsyncContextManager[Any],
        sdk_session: Any,
        sdk_types: Any,
        on_close: SessionClosedCallback | None = None,
    ) -> None:
        self.session_id = session_id
        self._context_manager = context_manager
        self._sdk_session = sdk_session
        self._sdk_types = sdk_types
        self._on_close = on_close
        self._closed = False

    @property
    def is_closed(self) -> bool:
        return self._closed

    def _ensure_open(self) -> None:
        if self._closed:
            raise GeminiLiveSessionError(
                "Cannot use a Gemini Live session after it has been closed."
            )

    async def send_audio_input(
        self,
        audio_bytes: bytes,
        *,
        mime_type: str = "audio/pcm;rate=16000",
    ) -> None:
        self._ensure_open()
        if not audio_bytes:
            raise GeminiLiveSessionError("Audio input cannot be empty.")

        try:
            await self._sdk_session.send_realtime_input(
                audio=self._sdk_types.Blob(data=audio_bytes, mime_type=mime_type)
            )
        except Exception as exc:
            log_event(
                LOGGER,
                logging.ERROR,
                "gemini_live_audio_send_failed",
                session_id=self.session_id,
                mime_type=mime_type,
                detail=str(exc),
            )
            raise GeminiLiveSessionError(
                "Failed to send audio input to Gemini Live."
            ) from exc

    async def finish_audio_input(self) -> None:
        self._ensure_open()

        try:
            await self._sdk_session.send_realtime_input(audio_stream_end=True)
        except Exception as exc:
            log_event(
                LOGGER,
                logging.ERROR,
                "gemini_live_audio_finish_failed",
                session_id=self.session_id,
                detail=str(exc),
            )
            raise GeminiLiveSessionError(
                "Failed to finalize audio input for Gemini Live."
            ) from exc

    async def send_image_frame(
        self,
        image_bytes: bytes,
        *,
        mime_type: str = "image/jpeg",
    ) -> None:
        self._ensure_open()
        if not image_bytes:
            raise GeminiLiveSessionError("Image frame input cannot be empty.")
        if not mime_type.startswith("image/"):
            raise GeminiLiveSessionError(
                "Image frame MIME type must start with 'image/'."
            )

        try:
            await self._sdk_session.send_realtime_input(
                video=self._sdk_types.Blob(data=image_bytes, mime_type=mime_type)
            )
        except Exception as exc:
            log_event(
                LOGGER,
                logging.ERROR,
                "gemini_live_frame_send_failed",
                session_id=self.session_id,
                mime_type=mime_type,
                detail=str(exc),
            )
            raise GeminiLiveSessionError(
                "Failed to send image frame input to Gemini Live."
            ) from exc

    async def receive_events(self) -> AsyncIterator[GeminiLiveEvent]:
        self._ensure_open()

        try:
            while not self._closed:
                async for message in self._sdk_session.receive():
                    for event in _normalize_server_message(self.session_id, message):
                        yield event
        except Exception as exc:
            log_event(
                LOGGER,
                logging.ERROR,
                "gemini_live_receive_failed",
                session_id=self.session_id,
                detail=str(exc),
            )
            raise GeminiLiveSessionError(
                "Failed while receiving Gemini Live server events."
            ) from exc

    async def close(self) -> None:
        if self._closed:
            return

        try:
            await self._context_manager.__aexit__(None, None, None)
            log_event(
                LOGGER,
                logging.INFO,
                "gemini_live_session_closed",
                session_id=self.session_id,
            )
        except Exception as exc:
            log_event(
                LOGGER,
                logging.ERROR,
                "gemini_live_session_close_failed",
                session_id=self.session_id,
                detail=str(exc),
            )
            raise GeminiLiveSessionError(
                "Failed to close the Gemini Live session cleanly."
            ) from exc
        finally:
            self._closed = True
            if self._on_close is not None:
                self._on_close(self.session_id)


def _load_google_genai_sdk() -> tuple[Any, Any]:
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise GeminiLiveDependencyError(
            "google-genai is required for Gemini Live sessions. Install the "
            "backend requirements with a standard CPython 3.11+ interpreter."
        ) from exc

    return genai, types


def _build_speech_config(sdk_types: Any, settings: GeminiLiveSettings) -> Any | None:
    if not settings.voice_name and not settings.voice_language_code:
        return None

    voice_config = None
    if settings.voice_name:
        voice_config = sdk_types.VoiceConfig(
            prebuilt_voice_config=sdk_types.PrebuiltVoiceConfig(
                voice_name=settings.voice_name
            )
        )

    return sdk_types.SpeechConfig(
        voice_config=voice_config,
        language_code=settings.voice_language_code,
    )


def _build_connect_config(
    sdk_types: Any,
    settings: GeminiLiveSettings,
    *,
    system_instruction: str | None,
) -> Any:
    config_kwargs: dict[str, Any] = {
        "response_modalities": ["AUDIO"],
    }

    if settings.input_audio_transcription_enabled:
        config_kwargs["input_audio_transcription"] = (
            sdk_types.AudioTranscriptionConfig()
        )
    if settings.output_audio_transcription_enabled:
        config_kwargs["output_audio_transcription"] = (
            sdk_types.AudioTranscriptionConfig()
        )

    speech_config = _build_speech_config(sdk_types, settings)
    if speech_config is not None:
        config_kwargs["speech_config"] = speech_config

    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction

    return sdk_types.LiveConnectConfig(**config_kwargs)


def _serialize_sdk_model(value: Any) -> Any:
    if value is None:
        return None

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump(exclude_none=True)

    to_json_dict = getattr(value, "to_json_dict", None)
    if callable(to_json_dict):
        return to_json_dict()

    as_dict = getattr(value, "dict", None)
    if callable(as_dict):
        try:
            return as_dict(exclude_none=True)
        except TypeError:
            return as_dict()

    return value


def _normalize_server_message(
    session_id: str,
    message: Any,
) -> list[GeminiLiveEvent]:
    events: list[GeminiLiveEvent] = []

    setup_complete = getattr(message, "setup_complete", None)
    if setup_complete is not None:
        events.append(
            GeminiLiveEvent(
                event_type="setup_complete",
                session_id=session_id,
                payload=_serialize_sdk_model(setup_complete) or {},
            )
        )

    server_content = getattr(message, "server_content", None)
    if server_content is not None:
        model_turn = getattr(server_content, "model_turn", None)
        parts = getattr(model_turn, "parts", None) or ()
        for part in parts:
            inline_data = getattr(part, "inline_data", None)
            if inline_data is None:
                continue

            mime_type = getattr(inline_data, "mime_type", None) or ""
            data = getattr(inline_data, "data", None)
            if data is None or not mime_type.startswith("audio/"):
                continue

            events.append(
                GeminiLiveEvent(
                    event_type="audio_output",
                    session_id=session_id,
                    payload={
                        "mimeType": mime_type,
                        "data": data,
                    },
                )
            )

        input_transcription = getattr(server_content, "input_transcription", None)
        if input_transcription is not None and getattr(
            input_transcription, "text", None
        ):
            events.append(
                GeminiLiveEvent(
                    event_type="input_transcription",
                    session_id=session_id,
                    payload={
                        "text": input_transcription.text,
                        "finished": bool(
                            getattr(input_transcription, "finished", False)
                        ),
                    },
                )
            )

        output_transcription = getattr(server_content, "output_transcription", None)
        if output_transcription is not None and getattr(
            output_transcription, "text", None
        ):
            events.append(
                GeminiLiveEvent(
                    event_type="output_transcription",
                    session_id=session_id,
                    payload={
                        "text": output_transcription.text,
                        "finished": bool(
                            getattr(output_transcription, "finished", False)
                        ),
                    },
                )
            )

        if getattr(server_content, "interrupted", None) is not None:
            events.append(
                GeminiLiveEvent(
                    event_type="interruption",
                    session_id=session_id,
                    payload={
                        "interrupted": bool(server_content.interrupted),
                    },
                )
            )

        if getattr(server_content, "generation_complete", None) is not None:
            events.append(
                GeminiLiveEvent(
                    event_type="generation_complete",
                    session_id=session_id,
                    payload={
                        "generationComplete": bool(
                            server_content.generation_complete
                        ),
                    },
                )
            )

        if getattr(server_content, "turn_complete", None) is not None:
            events.append(
                GeminiLiveEvent(
                    event_type="turn_complete",
                    session_id=session_id,
                    payload={
                        "turnComplete": bool(server_content.turn_complete),
                    },
                )
            )

    vad_signal = getattr(message, "voice_activity_detection_signal", None)
    if vad_signal is not None:
        events.append(
            GeminiLiveEvent(
                event_type="voice_activity_detection",
                session_id=session_id,
                payload=_serialize_sdk_model(vad_signal) or {},
            )
        )

    go_away = getattr(message, "go_away", None)
    if go_away is not None:
        events.append(
            GeminiLiveEvent(
                event_type="go_away",
                session_id=session_id,
                payload=_serialize_sdk_model(go_away) or {},
            )
        )

    if not events:
        events.append(
            GeminiLiveEvent(
                event_type="raw_message",
                session_id=session_id,
                payload={
                    "message": _serialize_sdk_model(message) or {},
                },
            )
        )

    return events


class GeminiLiveSessionManager:
    """Owns Gemini Live session creation and teardown for the backend."""

    def __init__(
        self,
        settings: GeminiLiveSettings,
        *,
        sdk_loader: SdkLoader | None = None,
    ) -> None:
        self._settings = settings
        self._sdk_loader = sdk_loader or _load_google_genai_sdk
        self._client: Any | None = None
        self._sdk_types: Any | None = None
        self._sessions: dict[str, GeminiLiveSession] = {}
        self._lock = asyncio.Lock()

    @property
    def is_configured(self) -> bool:
        return self._settings.is_configured

    @property
    def active_session_count(self) -> int:
        return len(self._sessions)

    def _remove_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def _ensure_configured(self) -> None:
        if self._settings.is_configured:
            return

        raise GeminiLiveConfigurationError(
            "Gemini Live requires GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, "
            "and VERTEX_AI_MODEL to be set."
        )

    def _get_sdk_client(self) -> tuple[Any, Any]:
        genai, sdk_types = self._sdk_loader()
        if self._client is None:
            self._client = genai.Client(
                vertexai=True,
                project=self._settings.project,
                location=self._settings.location,
            )
        if self._sdk_types is None:
            self._sdk_types = sdk_types
        return self._client, self._sdk_types

    async def create_session(
        self,
        *,
        session_id: str | None = None,
        system_instruction: str | None = None,
    ) -> GeminiLiveSession:
        self._ensure_configured()
        resolved_session_id = session_id or uuid4().hex

        async with self._lock:
            if resolved_session_id in self._sessions:
                raise GeminiLiveSessionError(
                    f"Gemini Live session already exists: {resolved_session_id}."
                )

            log_event(
                LOGGER,
                logging.INFO,
                "gemini_live_session_create_started",
                session_id=resolved_session_id,
                project=self._settings.project,
                location=self._settings.location,
                model=self._settings.model,
            )

            try:
                client, sdk_types = self._get_sdk_client()
                connect_config = _build_connect_config(
                    sdk_types,
                    self._settings,
                    system_instruction=system_instruction,
                )
                context_manager = client.aio.live.connect(
                    model=self._settings.model,
                    config=connect_config,
                )
                sdk_session = await context_manager.__aenter__()
            except Exception as exc:
                log_event(
                    LOGGER,
                    logging.ERROR,
                    "gemini_live_session_create_failed",
                    session_id=resolved_session_id,
                    model=self._settings.model,
                    detail=str(exc),
                )
                raise GeminiLiveSessionError(
                    "Failed to create a Gemini Live session."
                ) from exc

            session = GeminiLiveSession(
                session_id=resolved_session_id,
                context_manager=context_manager,
                sdk_session=sdk_session,
                sdk_types=sdk_types,
                on_close=self._remove_session,
            )
            self._sessions[resolved_session_id] = session

            log_event(
                LOGGER,
                logging.INFO,
                "gemini_live_session_created",
                session_id=resolved_session_id,
                model=self._settings.model,
                active_sessions=self.active_session_count,
            )
            return session

    def get_session(self, session_id: str) -> GeminiLiveSession | None:
        return self._sessions.get(session_id)

    async def close_session(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        await session.close()

    async def shutdown(self) -> None:
        sessions = list(self._sessions.values())
        for session in sessions:
            await session.close()
