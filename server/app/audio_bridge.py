"""Session-scoped Gemini Live bridge for client audio input and operator audio output."""

from __future__ import annotations

import asyncio
import base64
import binascii
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
import logging
from typing import Any

from .demo_barge_in import DEMO_BARGE_IN_SCRIPT, matches_demo_barge_in_trigger
from .gemini_live import GeminiLiveEvent, GeminiLiveSession, GeminiLiveSessionManager
from .logging_utils import log_event
from .verification_flow import VerificationFlowError
from .verification_intent import parse_ready_to_verify_voice_intent
from .voice_intent import build_swap_request_payload, parse_swap_voice_intent

LOGGER = logging.getLogger("ghostline.backend.audio_bridge")

DEFAULT_AUDIO_MIME_TYPE = "audio/pcm;rate=16000"
_AUDIO_MIME_PREFIX = "audio/pcm"
_SYSTEM_INSTRUCTION = (
    "You are The Archivist, Containment Desk — the senior operator at Ghostline, "
    "a live paranormal containment hotline. You speak in short, calm, procedural "
    "lines with brisk pacing. You are professional, slightly clinical, never "
    "dramatic. Think of a veteran field dispatcher who has seen thousands of "
    "cases. You are the caller's lifeline.\n\n"

    "PERSONA RULES:\n"
    "- Speak in 1-3 sentences maximum per turn. Brevity is authority.\n"
    "- You drive the call. You are in control. The caller follows your lead.\n"
    "- Never ask the caller's name, personal details, or location.\n"
    "- Never use campy horror language, threats, profanity, gore, or jump scares.\n"
    "- Be honest about uncertainty. If you cannot see something clearly, say so.\n"
    "- Never bluff visual claims. If the frame is dark or blurry, say it is.\n"
    "- When the caller sounds scared, be calm and reassuring but stay procedural.\n"
    "- Do not break character. You are a containment specialist, not an AI assistant.\n\n"

    "THE CALL FLOW:\n"
    "The backend controls the session flow. Your job is to speak the guidance "
    "naturally and respond to what the caller says and shows you. The flow is:\n"
    "1. Call connects — you greet the caller with a short Containment Desk opener\n"
    "2. Microphone test — ask them to say something so you can verify their voice is coming through\n"
    "3. Camera access — tell them you need the room feed\n"
    "4. Room scan — ask them to slowly pan the camera left to right so you can assess the space\n"
    "5. Tasks begin — you guide them through containment steps one at a time\n"
    "6. Verification — when they say 'Ready to Verify', hold still for inspection\n"
    "7. Case report — you close the case with a final assessment\n\n"

    "ROOM SCAN:\n"
    "When the camera goes live, ask the caller to slowly sweep the room from left "
    "to right. You will receive frames from the camera. Describe what you actually "
    "see — doorways, surfaces, light sources, objects. Then deliver a short, "
    "atmospheric assessment: your sensors have picked up residual spectral activity "
    "in this space. The readings are elevated. Containment protocol is warranted. "
    "Keep it procedural and grounded in what you can actually see in the frame.\n\n"

    "VISION ANALYSIS:\n"
    "You have access to the caller's camera feed. When the backend sends you frames:\n"
    "- ROOM_ANALYSIS: Describe the room features you see and assess readiness.\n"
    "- VERIFICATION_ANALYSIS: Analyze whether a specific containment task was completed. "
    "Be honest about what you see. If the task is done, confirm it. If you cannot "
    "determine completion, say so clearly with a reason.\n\n"

    "INTER-TASK FLAVOR (CONTAINMENT LORE):\n"
    "Between tasks, you should occasionally weave in short pieces of containment "
    "lore and paranormal context. These are brief, procedural observations — NOT "
    "stories or monologues. Examples of the tone:\n"
    "- 'Residual patterns like this usually settle once boundary is established.'\n"
    "- 'The threshold is the most common anchor point. Classic displacement behavior.'\n"
    "- 'Activity of this type tends to concentrate near transitional spaces — doors, hallways, stairwells.'\n"
    "- 'Our containment protocol was designed for exactly this spectral profile.'\n"
    "- 'The room is responding well. Readings are dropping.'\n"
    "Keep these to ONE sentence. They should feel like a veteran operator making "
    "an offhand observation, not narrating a horror story.\n\n"

    "BACKEND DIRECTIVES:\n"
    "The backend sends you instructions in two forms:\n"
    "- OPERATOR_DIRECTIVE: Speak this line exactly as written. Do not add extra words. "
    "Stop after the line.\n"
    "- CONTEXT_DIRECTIVE: This tells you what situation you are in. Generate a natural "
    "Archivist response based on the context. Stay in character and keep it brief.\n"
    "- VERIFICATION_ANALYSIS: A frame from the caller's camera is being sent for "
    "you to analyze for task verification. Describe what you see and assess.\n"
    "- ROOM_ANALYSIS: A frame during room scan. Describe the room and assess.\n\n"

    "IMPORTANT:\n"
    "If the caller asks what to do, restate the latest directive. Do not invent "
    "tasks. The backend assigns tasks — you speak them. When assigning a task, "
    "state the task name, one clear action, and tell them to say 'Ready to Verify' "
    "when the step is complete. You ARE the operator. You drive the call."
)
ForwardEnvelope = Callable[[dict[str, Any]], Awaitable[None]]
StartVerificationCallback = Callable[[dict[str, Any]], Awaitable[None]]
HandleSwapRequestCallback = Callable[[dict[str, Any]], Awaitable[None]]
RecordUserTranscriptCallback = Callable[[str, bool], None]
UpdateDemoBargeInCallback = Callable[[dict[str, Any]], Awaitable[None]]


class AudioBridgePayloadError(ValueError):
    """Raised when client audio bridge payloads are malformed."""


@dataclass(frozen=True)
class AudioChunk:
    sequence: int
    mime_type: str
    audio_bytes: bytes
    sample_count: int | None = None


class SessionAudioBridge:
    """Owns the Prompt 9-10 audio bridge for one client WebSocket session."""

    def __init__(
        self,
        *,
        session_id: str,
        gemini_session_manager: GeminiLiveSessionManager,
        forward_envelope: ForwardEnvelope,
        start_verification: StartVerificationCallback | None = None,
        handle_swap_request: HandleSwapRequestCallback | None = None,
        record_user_transcript: RecordUserTranscriptCallback | None = None,
        update_demo_barge_in: UpdateDemoBargeInCallback | None = None,
    ) -> None:
        self.session_id = session_id
        self._gemini_session_manager = gemini_session_manager
        self._forward_envelope = forward_envelope
        self._start_verification = start_verification
        self._handle_swap_request = handle_swap_request
        self._record_user_transcript = record_user_transcript
        self._update_demo_barge_in = update_demo_barge_in
        self._gemini_session: GeminiLiveSession | None = None
        self._receive_task: asyncio.Task[None] | None = None
        self._mic_active = False
        self._chunk_count = 0
        self._drained_event_count = 0
        self._last_sequence = -1
        self._active_mime_type = DEFAULT_AUDIO_MIME_TYPE
        self._operator_audio_sequence = 0
        self._operator_playback_epoch = 0
        self._discard_operator_audio = False
        self._pending_epoch_advance = False
        self._demo_mode_enabled = False
        self._demo_barge_in_armed = False
        self._demo_barge_in_triggered = False
        self._demo_barge_in_restatement_pending = False
        self._demo_barge_in_completed = False
        self._suppress_operator_output_transcripts = False

    @property
    def gemini_session(self) -> GeminiLiveSession | None:
        """Expose the live Gemini session for vision verification."""
        return self._gemini_session

    async def send_context_directive(self, context: str) -> None:
        """Send a CONTEXT_DIRECTIVE to Gemini for adaptive dialogue.

        Unlike OPERATOR_DIRECTIVE (which Gemini reads verbatim), a context
        directive gives Gemini the situation and lets it generate a natural
        Archivist response.
        """
        session = await self._ensure_session()
        await session.send_text_input(f"CONTEXT_DIRECTIVE: {context}")
        log_event(
            LOGGER,
            logging.INFO,
            "context_directive_sent",
            session_id=self.session_id,
            context_preview=context[:80],
        )

    async def send_room_scan_frame(
        self,
        frame_base64: str,
        *,
        mime_type: str = "image/jpeg",
    ) -> bool:
        """Send a room scan frame to the Gemini session during calibration.

        Only the image frame is sent here — the room-analysis context
        directive is sent once via ``prime_room_scan_context`` before
        scanning begins, so Gemini knows how to interpret these frames
        without creating a new conversational turn for each one.

        Returns True if the frame was sent successfully.
        """
        session = await self._ensure_session()
        try:
            image_bytes = base64.b64decode(frame_base64)
        except Exception:
            return False

        if not image_bytes:
            return False

        try:
            await session.send_image_frame(image_bytes, mime_type=mime_type)
            log_event(
                LOGGER,
                logging.INFO,
                "room_scan_frame_sent",
                session_id=self.session_id,
                frame_bytes=len(image_bytes),
            )
            return True
        except Exception as exc:
            log_event(
                LOGGER,
                logging.WARNING,
                "room_scan_frame_failed",
                session_id=self.session_id,
                detail=str(exc),
            )
            return False

    async def prime_room_scan_context(self) -> None:
        """Send the room-analysis context directive once before scanning.

        This tells Gemini how to interpret incoming room scan frames
        without creating a new conversational turn per frame.
        """
        await self.send_context_directive(
            "ROOM_ANALYSIS: You are about to receive a series of camera "
            "frames from the caller's room. As The Archivist, observe "
            "what you see — note doorways, flat surfaces, light sources, "
            "reflective surfaces, any objects of note. When you have "
            "enough visual context, deliver a short atmospheric assessment: "
            "our sensors have picked up residual activity in this space. "
            "Stay procedural and calm. Do NOT interrupt yourself or "
            "restart your analysis with each new frame — treat them as "
            "a continuous feed."
        )

    async def send_verification_frame(
        self,
        frame_base64: str,
        *,
        task_id: str | None = None,
        task_name: str | None = None,
        mime_type: str = "image/jpeg",
    ) -> bool:
        """Send a verification frame to the Gemini session for vision analysis.

        Returns True if the frame was sent successfully.
        """
        session = await self._ensure_session()
        try:
            image_bytes = base64.b64decode(frame_base64)
        except Exception:
            return False

        if not image_bytes:
            return False

        prompt = (
            f"VERIFICATION_ANALYSIS: The caller was performing task '{task_name or 'unknown'}' "
            f"(ID: {task_id or 'unknown'}). Analyze this frame. Can you see evidence "
            "that the task was completed? Describe what you see briefly and honestly. "
            "If the frame is dark, blurry, or you cannot confirm, say so clearly."
        )

        try:
            await session.send_image_frame(image_bytes, mime_type=mime_type)
            await session.send_text_input(prompt)
            log_event(
                LOGGER,
                logging.INFO,
                "verification_frame_sent",
                session_id=self.session_id,
                task_id=task_id,
                frame_bytes=len(image_bytes),
            )
            return True
        except Exception as exc:
            log_event(
                LOGGER,
                logging.WARNING,
                "verification_frame_failed",
                session_id=self.session_id,
                detail=str(exc),
            )
            return False

    async def start_stream(self, payload: dict[str, Any]) -> None:

        streaming = payload.get("streaming")
        if streaming is not True:
            raise AudioBridgePayloadError(
                "Mic start payload must include streaming=true."
            )

        mime_type = _parse_audio_mime_type(payload.get("mimeType"))
        chunk_duration_ms = _parse_optional_int(payload.get("chunkDurationMs"))
        device_sample_rate = _parse_optional_int(payload.get("deviceSampleRate"))
        sample_rate = _parse_optional_int(payload.get("sampleRate"))

        if self._mic_active:
            log_event(
                LOGGER,
                logging.INFO,
                "audio_bridge_start_ignored",
                session_id=self.session_id,
                reason="already_active",
            )
            return

        await self._ensure_session()

        self._mic_active = True
        self._chunk_count = 0
        self._last_sequence = -1
        self._active_mime_type = mime_type

        log_event(
            LOGGER,
            logging.INFO,
            "audio_bridge_started",
            session_id=self.session_id,
            mime_type=mime_type,
            sample_rate=sample_rate,
            device_sample_rate=device_sample_rate,
            chunk_duration_ms=chunk_duration_ms,
        )

    async def stop_stream(self, *, reason: str) -> None:
        if not self._mic_active:
            log_event(
                LOGGER,
                logging.INFO,
                "audio_bridge_stop_ignored",
                session_id=self.session_id,
                reason=reason,
                detail="mic_not_active",
            )
            return

        self._mic_active = False

        if self._gemini_session is not None and not self._gemini_session.is_closed:
            await self._gemini_session.finish_audio_input()

        log_event(
            LOGGER,
            logging.INFO,
            "audio_bridge_stopped",
            session_id=self.session_id,
            reason=reason,
            chunk_count=self._chunk_count,
        )

    async def forward_audio_chunk(self, payload: dict[str, Any]) -> None:
        if not self._mic_active:
            raise AudioBridgePayloadError(
                "Audio chunks require an active mic stream."
            )

        session = await self._ensure_session()
        chunk = _parse_audio_chunk(
            payload=payload,
            default_mime_type=self._active_mime_type,
        )
        if chunk.sequence <= self._last_sequence:
            raise AudioBridgePayloadError(
                "Audio chunk sequence must increase monotonically."
            )

        await session.send_audio_input(chunk.audio_bytes, mime_type=chunk.mime_type)
        self._chunk_count += 1
        self._last_sequence = chunk.sequence
        self._active_mime_type = chunk.mime_type

        if self._chunk_count == 1 or self._chunk_count % 10 == 0:
            log_event(
                LOGGER,
                logging.INFO,
                "audio_chunk_forwarded",
                session_id=self.session_id,
                chunk_count=self._chunk_count,
                sequence=chunk.sequence,
                byte_count=len(chunk.audio_bytes),
                mime_type=chunk.mime_type,
                sample_count=chunk.sample_count,
            )

    async def close(self, *, reason: str) -> None:
        if self._mic_active:
            await self.stop_stream(reason=reason)

        if self._receive_task is not None:
            self._receive_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._receive_task
            self._receive_task = None

        if self._gemini_session is not None and not self._gemini_session.is_closed:
            await self._gemini_session_manager.close_session(self.session_id)
        self._gemini_session = None

    async def configure_demo_mode(self, *, enabled: bool) -> None:
        self._demo_mode_enabled = enabled
        self._demo_barge_in_armed = False
        self._demo_barge_in_triggered = False
        self._demo_barge_in_restatement_pending = False
        self._demo_barge_in_completed = False
        self._suppress_operator_output_transcripts = False

    async def send_operator_guidance(self, text: str, *, source: str, emit_transcript: bool = False) -> None:
        normalized_text = text.strip()
        if not normalized_text:
            return

        session = await self._ensure_session()
        self._suppress_operator_output_transcripts = True
        if emit_transcript:
            await self._forward_envelope(
                {
                    "type": "transcript",
                    "sessionId": self.session_id,
                    "payload": {
                        "speaker": "operator",
                        "text": normalized_text,
                        "isFinal": True,
                        "source": source,
                    },
                }
            )
        await session.send_text_input(f"OPERATOR_DIRECTIVE: {normalized_text}")
        log_event(
            LOGGER,
            logging.INFO,
            "operator_guidance_sent",
            session_id=self.session_id,
            source=source,
            text_preview=normalized_text[:120],
        )
        await self._maybe_arm_demo_barge_in(normalized_text, source=source)

    async def _ensure_session(self) -> GeminiLiveSession:
        if self._gemini_session is None or self._gemini_session.is_closed:
            self._gemini_session = await self._gemini_session_manager.create_session(
                session_id=self.session_id,
                system_instruction=_SYSTEM_INSTRUCTION,
            )
            self._drained_event_count = 0
            self._operator_audio_sequence = 0
            self._operator_playback_epoch = 0
            self._discard_operator_audio = False
            self._pending_epoch_advance = False

        if self._receive_task is None or self._receive_task.done():
            self._receive_task = asyncio.create_task(self._drain_gemini_events())

        return self._gemini_session

    async def _drain_gemini_events(self) -> None:
        if self._gemini_session is None:
            return

        try:
            async for event in self._gemini_session.receive_events():
                self._drained_event_count += 1
                await self._handle_gemini_event(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log_event(
                LOGGER,
                logging.ERROR,
                "gemini_live_event_drain_failed",
                session_id=self.session_id,
                detail=str(exc),
            )
            await self._forward_envelope(
                {
                    "type": "error",
                    "sessionId": self.session_id,
                    "payload": {
                        "status": "error",
                        "code": "gemini_receive_failed",
                        "detail": "Gemini Live audio output stopped unexpectedly.",
                    },
                }
            )

    async def _handle_gemini_event(self, event: GeminiLiveEvent) -> None:
        if event.event_type == "audio_output":
            raw_audio = event.payload.get("data")
            if not isinstance(raw_audio, (bytes, bytearray)):
                return

            if self._discard_operator_audio:
                log_event(
                    LOGGER,
                    logging.INFO,
                    "operator_audio_chunk_discarded",
                    session_id=self.session_id,
                    playback_epoch=self._operator_playback_epoch,
                    byte_count=len(raw_audio),
                    reason="interruption_flush_active",
                )
                return

            self._operator_audio_sequence += 1
            mime_type = event.payload.get("mimeType", DEFAULT_AUDIO_MIME_TYPE)
            await self._forward_envelope(
                {
                    "type": "operator_audio_chunk",
                    "sessionId": self.session_id,
                    "payload": {
                        "sequence": self._operator_audio_sequence,
                        "playbackEpoch": self._operator_playback_epoch,
                        "mimeType": mime_type,
                        "data": base64.b64encode(bytes(raw_audio)).decode("ascii"),
                        "byteCount": len(raw_audio),
                    },
                }
            )
            log_event(
                LOGGER,
                logging.INFO,
                "operator_audio_chunk_forwarded",
                session_id=self.session_id,
                playback_epoch=self._operator_playback_epoch,
                sequence=self._operator_audio_sequence,
                byte_count=len(raw_audio),
                mime_type=mime_type,
            )
            return

        if event.event_type == "interruption":
            interrupted = bool(event.payload.get("interrupted", False))
            if interrupted:
                self._discard_operator_audio = True
                self._pending_epoch_advance = True

            await self._forward_envelope(
                {
                    "type": "operator_interruption",
                    "sessionId": self.session_id,
                    "payload": {
                        **event.payload,
                        "playbackEpoch": self._operator_playback_epoch,
                    },
                }
            )
            log_event(
                LOGGER,
                logging.INFO,
                "operator_audio_interruption_forwarded",
                session_id=self.session_id,
                interrupted=interrupted,
                playback_epoch=self._operator_playback_epoch,
            )
            log_event(
                LOGGER,
                logging.INFO,
                "interruption_handled",
                session_id=self.session_id,
                interrupted=interrupted,
                playback_epoch=self._operator_playback_epoch,
                operator_audio_sequence=self._operator_audio_sequence,
                flush_active=self._discard_operator_audio,
            )
            return

        if event.event_type in {"generation_complete", "turn_complete"}:
            completed = bool(
                event.payload.get("generationComplete", False)
                or event.payload.get("turnComplete", False)
            )
            if (
                completed
                and self._demo_mode_enabled
                and self._demo_barge_in_armed
                and not self._demo_barge_in_triggered
            ):
                self._demo_barge_in_armed = False
                await self._publish_demo_barge_in_status("idle")
                log_event(
                    LOGGER,
                    logging.INFO,
                    "demo_barge_in_disarmed",
                    session_id=self.session_id,
                    reason="target_line_completed_without_interrupt",
                )
            if completed:
                self._suppress_operator_output_transcripts = False
            if self._pending_epoch_advance and completed:
                await self._release_operator_audio_flush(released_by=event.event_type)
            return

        if event.event_type in {"input_transcription", "output_transcription"}:
            text = event.payload.get("text")
            if isinstance(text, str) and text.strip():
                direction = (
                    "input"
                    if event.event_type == "input_transcription"
                    else "output"
                )
                is_final = bool(event.payload.get("finished", False))
                if direction == "output" and self._suppress_operator_output_transcripts:
                    log_event(
                        LOGGER,
                        logging.INFO,
                        "gemini_live_output_transcript_suppressed",
                        session_id=self.session_id,
                        finished=is_final,
                        text_preview=text[:80],
                    )
                    if is_final:
                        self._suppress_operator_output_transcripts = False
                else:
                    await self._forward_envelope(
                        {
                            "type": "transcript",
                            "sessionId": self.session_id,
                            "payload": {
                                "speaker": "user" if direction == "input" else "operator",
                                "text": text.strip(),
                                "isFinal": is_final,
                                "source": "gemini_live",
                            },
                        }
                    )
                    log_event(
                        LOGGER,
                        logging.INFO,
                        "gemini_live_transcript_received",
                        session_id=self.session_id,
                        direction=direction,
                        finished=is_final,
                        text_preview=text[:80],
                    )
                if direction == "input" and is_final:
                    if self._pending_epoch_advance:
                        await self._release_operator_audio_flush(released_by="input_transcription")
                    if self._record_user_transcript is not None:
                        self._record_user_transcript(text.strip(), is_final)
                    await self._maybe_trigger_demo_barge_in(text.strip())
                    ready_to_verify_intent = parse_ready_to_verify_voice_intent(text)
                    if (
                        ready_to_verify_intent is not None
                        and self._start_verification is not None
                    ):
                        try:
                            await self._start_verification(
                                {
                                    "source": "voice_intent",
                                    "trigger": "transcript",
                                    "matchedPhrase": ready_to_verify_intent.matched_phrase,
                                    "rawTranscriptSnippet": ready_to_verify_intent.raw_transcript_snippet,
                                }
                            )
                            log_event(
                                LOGGER,
                                logging.INFO,
                                "voice_ready_to_verify_detected",
                                session_id=self.session_id,
                                matchedPhrase=ready_to_verify_intent.matched_phrase,
                                rawTranscriptSnippet=ready_to_verify_intent.raw_transcript_snippet,
                            )
                        except VerificationFlowError as exc:
                            log_event(
                                LOGGER,
                                logging.INFO,
                                "voice_ready_to_verify_ignored",
                                session_id=self.session_id,
                                detail=str(exc),
                            )

                    swap_request = parse_swap_voice_intent(text)
                    if swap_request is not None:
                        swap_payload = {
                            "source": "voice_intent",
                            "matchedPhrase": swap_request.matched_phrase,
                            **build_swap_request_payload(swap_request),
                        }
                        await self._forward_envelope(
                            {
                                "type": "swap_request",
                                "sessionId": self.session_id,
                                "payload": {
                                    "status": "detected",
                                    **swap_payload,
                                },
                            }
                        )
                        log_event(
                            LOGGER,
                            logging.INFO,
                            "voice_swap_intent_detected",
                            session_id=self.session_id,
                            matchedPhrase=swap_request.matched_phrase,
                            **build_swap_request_payload(swap_request),
                        )
                        if self._handle_swap_request is not None:
                            await self._handle_swap_request(swap_payload)
            return

        if event.event_type != "raw_message":
            log_event(
                LOGGER,
                logging.INFO,
                "gemini_live_event_drained",
                session_id=self.session_id,
                event_type=event.event_type,
            )

    async def _publish_demo_barge_in_status(
        self,
        status: str | None,
        *,
        matched_transcript_snippet: str | None = None,
    ) -> None:
        if self._update_demo_barge_in is None:
            return

        await self._update_demo_barge_in(
            {
                "status": status,
                "targetLine": (
                    DEMO_BARGE_IN_SCRIPT.target_line if self._demo_mode_enabled else None
                ),
                "triggerPhrase": (
                    DEMO_BARGE_IN_SCRIPT.trigger_phrase if self._demo_mode_enabled else None
                ),
                "matchedTranscriptSnippet": matched_transcript_snippet,
            }
        )

    async def _maybe_arm_demo_barge_in(self, text: str, *, source: str) -> None:
        if not self._demo_mode_enabled or source != "demo_mode":
            return
        if self._demo_barge_in_completed or self._demo_barge_in_triggered:
            return
        if text != DEMO_BARGE_IN_SCRIPT.target_line:
            return

        self._demo_barge_in_armed = True
        await self._publish_demo_barge_in_status("armed")
        log_event(
            LOGGER,
            logging.INFO,
            "demo_barge_in_armed",
            session_id=self.session_id,
            target_line=DEMO_BARGE_IN_SCRIPT.target_line,
            trigger_phrase=DEMO_BARGE_IN_SCRIPT.trigger_phrase,
        )

    async def _maybe_trigger_demo_barge_in(self, transcript_text: str) -> None:
        if not self._demo_mode_enabled or not self._demo_barge_in_armed:
            return
        if self._demo_barge_in_triggered or self._demo_barge_in_completed:
            return
        if not matches_demo_barge_in_trigger(transcript_text):
            return

        self._demo_barge_in_armed = False
        self._demo_barge_in_triggered = True
        self._demo_barge_in_restatement_pending = True
        await self._publish_demo_barge_in_status(
            "triggered",
            matched_transcript_snippet=transcript_text,
        )
        log_event(
            LOGGER,
            logging.INFO,
            "demo_barge_in_triggered",
            session_id=self.session_id,
            trigger_phrase=DEMO_BARGE_IN_SCRIPT.trigger_phrase,
            matched_transcript_snippet=transcript_text[:120],
        )

    async def _release_operator_audio_flush(self, *, released_by: str) -> None:
        self._discard_operator_audio = False
        self._pending_epoch_advance = False
        self._operator_playback_epoch += 1
        log_event(
            LOGGER,
            logging.INFO,
            "operator_audio_flush_released",
            session_id=self.session_id,
            released_by=released_by,
            playback_epoch=self._operator_playback_epoch,
        )

        if not self._demo_barge_in_restatement_pending or self._demo_barge_in_completed:
            return

        self._demo_barge_in_restatement_pending = False
        self._demo_barge_in_completed = True
        await self.send_operator_guidance(
            DEMO_BARGE_IN_SCRIPT.restatement_line,
            source="demo_mode",
            emit_transcript=True,
        )
        await self._publish_demo_barge_in_status("restated")
        log_event(
            LOGGER,
            logging.INFO,
            "demo_barge_in_restated",
            session_id=self.session_id,
            released_by=released_by,
            restatement_line=DEMO_BARGE_IN_SCRIPT.restatement_line,
        )


def _parse_audio_mime_type(value: Any) -> str:
    if value is None:
        return DEFAULT_AUDIO_MIME_TYPE
    if not isinstance(value, str) or not value.strip():
        raise AudioBridgePayloadError("Audio MIME type must be a non-empty string.")
    if not value.startswith(_AUDIO_MIME_PREFIX):
        raise AudioBridgePayloadError("Audio chunks must use an audio/pcm MIME type.")
    return value.strip()


def _parse_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise AudioBridgePayloadError("Audio metadata integers must be numeric.")
    return value


def _parse_audio_chunk(*, payload: dict[str, Any], default_mime_type: str) -> AudioChunk:
    data = payload.get("data")
    if not isinstance(data, str) or not data.strip():
        raise AudioBridgePayloadError("Audio chunk payloads must include base64 data.")

    sequence = payload.get("sequence")
    if isinstance(sequence, bool) or not isinstance(sequence, int):
        raise AudioBridgePayloadError("Audio chunk sequence must be an integer.")

    sample_count = _parse_optional_int(payload.get("sampleCount"))
    mime_type = _parse_audio_mime_type(payload.get("mimeType") or default_mime_type)

    try:
        audio_bytes = base64.b64decode(data, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise AudioBridgePayloadError("Audio chunk data must be valid base64.") from exc

    if not audio_bytes:
        raise AudioBridgePayloadError("Audio chunks cannot be empty.")

    return AudioChunk(
        sequence=sequence,
        mime_type=mime_type,
        audio_bytes=audio_bytes,
        sample_count=sample_count,
    )
















