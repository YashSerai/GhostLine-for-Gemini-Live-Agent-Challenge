"""Gemini Vision verification engine — sends captured frames to the Live session for real AI analysis."""

from __future__ import annotations

import base64
import logging
from typing import Any

from .gemini_live import GeminiLiveSession, GeminiLiveSessionError
from .logging_utils import log_event
from .verification_engine import (
    ConfidenceBand,
    VerificationContext,
    VerificationDecision,
    VerificationEngineError,
    VerificationResultStatus,
)

LOGGER = logging.getLogger("ghostline.backend.gemini_verification")

# --------------------------------------------------------------------------- #
# Task-specific verification prompts                                           #
# --------------------------------------------------------------------------- #

_TASK_VERIFICATION_PROMPTS: dict[str, str] = {
    "T1": (
        "VERIFICATION CHECK: The caller says they showed the THRESHOLD — a doorway "
        "or room boundary. Look at this frame carefully. Do you ACTUALLY see a "
        "doorway, door frame, or boundary edge? If YES, confirm it. If NO, "
        "challenge the caller: 'I do not see a threshold in the frame. Show me.'"
    ),
    "T2": (
        "VERIFICATION CHECK: The caller says they CLOSED THE BOUNDARY. Look at "
        "this frame. Do you ACTUALLY see a closed door or sealed boundary? If YES, "
        "confirm it. If NO, challenge: 'I do not see a closed boundary. Show me.'"
    ),
    "T3": (
        "VERIFICATION CHECK: The caller says they INCREASED ILLUMINATION. Look at "
        "this frame. Does the room appear well-lit? Is a light source visibly on? "
        "If YES, confirm. If the room looks dim, challenge: 'The room still looks "
        "dim. Turn on a light and show me.'"
    ),
    "T4": (
        "VERIFICATION CHECK: The caller says they STABILIZED THE CAMERA. Look at "
        "this frame. Is the image sharp and steady? If YES, confirm. If it looks "
        "blurry or shaky, say: 'The image is still unstable. Hold the camera steady.'"
    ),
    "T5": (
        "VERIFICATION CHECK: The caller says they PLACED PAPER ON A SURFACE. Look "
        "at this frame. Can you see a sheet of paper on a flat surface? If YES, "
        "confirm. If NO, challenge: 'I do not see paper on a surface. Show me.'"
    ),
    "T6": (
        "VERIFICATION CHECK: The caller says they CLEARED A SMALL SURFACE. Look "
        "at this frame. Can you see a cleared area? If YES, confirm. If NO, "
        "challenge: 'I do not see a cleared surface. Show me the area.'"
    ),
    "T7": (
        "VERIFICATION CHECK: The caller was asked to SPEAK A CONTAINMENT PHRASE. "
        "This is audio-only. If you heard them speak a clear phrase, confirm it. "
        "If you heard nothing clear, say: 'I did not hear a clear phrase. Say it again.'"
    ),
    "T8": (
        "VERIFICATION CHECK: The caller says they DREW A MARK on paper. Look at "
        "this frame. Can you see a mark, symbol, or line on paper? If YES, confirm. "
        "If NO, challenge: 'I do not see a mark. Show me the paper.'"
    ),
    "T9": (
        "VERIFICATION CHECK: The caller says they showed a REFLECTIVE SURFACE. "
        "Look at this frame. Can you see a mirror, glass, or reflective surface? "
        "If YES, confirm. If NO, challenge: 'I do not see a reflective surface. Show me.'"
    ),
    "T10": (
        "VERIFICATION CHECK: The caller says they held up a VIVID OBJECT. Look at "
        "this frame. Can you see a brightly colored object? If YES, confirm. "
        "If NO, challenge: 'I do not see a vivid object. Hold it up clearly.'"
    ),
    "T11": (
        "VERIFICATION CHECK: The caller says they did a WATER RELEASE. Look at "
        "this frame. Can you see running water or a sink area? If YES, confirm. "
        "If NO, challenge: 'I do not see water. Show me the sink.'"
    ),
    "T12": (
        "VERIFICATION CHECK: The caller says they placed a SALT LINE. Look at "
        "this frame. Can you see salt or a white line near a boundary? If YES, "
        "confirm. If NO, challenge: 'I do not see a salt line. Show me.'"
    ),
}

_DEFAULT_VERIFICATION_PROMPT = (
    "VERIFICATION CHECK: The caller says they completed a containment task. "
    "Look at this frame carefully. Do you see evidence of any deliberate action? "
    "If YES, describe and confirm it. If NO, challenge the caller: "
    "'I do not see the task completed. Show me what you did.' Do NOT bluff."
)


# --------------------------------------------------------------------------- #
# Room scan prompt — used during calibration sweep                             #
# --------------------------------------------------------------------------- #

ROOM_SCAN_ANALYSIS_PROMPT = (
    "ROOM_ANALYSIS: You are scanning the caller's room through their camera. "
    "Describe ONLY what you ACTUALLY see in the frame — do NOT assume or invent "
    "objects. Keep it brief and in character as The Archivist. "
    "After observing the room, deliver a short atmospheric assessment: our sensors "
    "have picked up residual activity in this space. Stay procedural and calm."
)


class GeminiVisionVerificationEngine:
    """Verification engine that sends captured frames to Gemini for real visual analysis.

    Uses the existing Gemini Live session's ``send_image_frame`` method to send
    JPEG frames and ``send_text_input`` to provide the analysis prompt.
    Gemini responds through the normal audio/text output channel which the
    audio bridge's event drain loop picks up.

    For structured decisions, this engine sends the frame + prompt, then returns
    a decision based on the task tier and verification class.  The actual visual
    reasoning happens in the Gemini model — we send the frame so the model has
    real visual context for its spoken response.
    """

    def __init__(
        self,
        *,
        session_id: str,
        gemini_session: GeminiLiveSession | None = None,
        frame_data_store: dict[str, list[str]] | None = None,
    ) -> None:
        self.session_id = session_id
        self._gemini_session = gemini_session
        self._frame_data_store = frame_data_store or {}
        self._last_observation: str | None = None

    @property
    def last_observation(self) -> str | None:
        """The last observation string Gemini produced (for HUD display)."""
        return self._last_observation

    def attach_session(self, session: GeminiLiveSession | None) -> None:
        self._gemini_session = session

    def store_frame_data(self, attempt_id: str, frames: list[str]) -> None:
        """Store base64 frame data from the verification window."""
        self._frame_data_store[attempt_id] = frames

    async def send_frame_for_analysis(
        self,
        frame_base64: str,
        *,
        task_id: str | None = None,
        task_name: str | None = None,
        mime_type: str = "image/jpeg",
        context_label: str = "verification",
    ) -> bool:
        """Send a single frame to the Gemini Live session with a task-specific analysis prompt.

        Returns True if the frame was sent successfully.
        """
        if self._gemini_session is None or self._gemini_session.is_closed:
            log_event(
                LOGGER,
                logging.WARNING,
                "gemini_vision_no_session",
                session_id=self.session_id,
                context=context_label,
            )
            return False

        try:
            image_bytes = base64.b64decode(frame_base64)
        except Exception:
            log_event(
                LOGGER,
                logging.WARNING,
                "gemini_vision_decode_failed",
                session_id=self.session_id,
            )
            return False

        if not image_bytes:
            return False

        prompt = self._build_prompt(task_id, task_name, context_label)

        try:
            await self._gemini_session.send_image_frame(
                image_bytes,
                mime_type=mime_type,
            )
            await self._gemini_session.send_text_input(prompt)
            log_event(
                LOGGER,
                logging.INFO,
                "gemini_vision_frame_sent",
                session_id=self.session_id,
                task_id=task_id,
                task_name=task_name,
                context=context_label,
                frame_bytes=len(image_bytes),
            )
            return True
        except GeminiLiveSessionError as exc:
            log_event(
                LOGGER,
                logging.ERROR,
                "gemini_vision_send_failed",
                session_id=self.session_id,
                detail=str(exc),
            )
            return False

    async def evaluate(
        self,
        context: VerificationContext,
    ) -> VerificationDecision:
        """Evaluate a verification attempt using Gemini vision.

        Sends the best captured frame to Gemini for visual analysis, then
        returns a decision based on the task's verification class and tier.
        The AI's actual visual reasoning comes through as spoken/transcribed
        output via the audio bridge.
        """
        task_context = context.task_context
        task_id = task_context.get("taskId")
        task_name = task_context.get("taskName")
        task_tier = task_context.get("taskTier")
        verification_class = task_context.get("verificationClass")

        # Try to send the best frame to Gemini for visual analysis
        frame_sent = False
        stored_frames = self._frame_data_store.pop(context.attempt_id, [])
        if stored_frames:
            # Send the middle frame (most likely to be stable)
            best_frame_index = len(stored_frames) // 2
            frame_sent = await self.send_frame_for_analysis(
                stored_frames[best_frame_index],
                task_id=task_id,
                task_name=task_name,
            )

        # Build the decision based on quality metrics + whether we could send the frame
        return self._build_decision(
            task_id=task_id,
            task_name=task_name,
            task_tier=task_tier,
            verification_class=verification_class,
            quality_metrics=context.quality_metrics,
            frame_sent=frame_sent,
            context=context,
        )

    def _build_prompt(
        self,
        task_id: str | None,
        task_name: str | None,
        context_label: str,
    ) -> str:
        if context_label == "room_scan":
            return ROOM_SCAN_ANALYSIS_PROMPT

        if isinstance(task_id, str) and task_id in _TASK_VERIFICATION_PROMPTS:
            base_prompt = _TASK_VERIFICATION_PROMPTS[task_id]
        else:
            base_prompt = _DEFAULT_VERIFICATION_PROMPT

        # Look up per-task completion check for before/after comparison
        from .task_library import TASK_LIBRARY
        completion_check = ""
        if task_id is not None:
            for t in TASK_LIBRARY:
                if t.id == task_id and t.completion_check:
                    completion_check = (
                        f" BEFORE/AFTER CHECK: You saw the room BEFORE this task "
                        f"started. {t.completion_check} Compare what you see NOW "
                        f"to what you saw BEFORE. If the scene has NOT meaningfully "
                        f"changed, this task is NOT done — say so clearly."
                    )
                    break

        return (
            f"VERIFICATION_ANALYSIS: {base_prompt}{completion_check} "
            "Based on what you see, state whether the task appears completed. "
            "Be honest — if the frame is too dark, blurry, or you cannot "
            "confirm the task, say so clearly. Do not bluff."
        )

    def _build_decision(
        self,
        *,
        task_id: str | None,
        task_name: str | None,
        task_tier: Any,
        verification_class: str | None,
        quality_metrics: Any,
        frame_sent: bool,
        context: VerificationContext,
    ) -> VerificationDecision:
        """Build a verification decision.

        The actual verification happens through Gemini's spoken analysis —
        the AI sees the frames and verbally confirms or challenges the user.
        We record the outcome as user_confirmed_only since the AI's verbal
        feedback is the real verification, not a programmatic decision.
        """
        # Self-report tasks (like T7 - Speak Containment Phrase) are audio-only
        if verification_class == "self_report":
            return VerificationDecision(
                block_reason=None,
                confidence_band="medium",
                is_mock=False,
                last_verified_item=task_name if isinstance(task_name, str) else None,
                mock_label=None,
                notes="Self-report task verified by caller audio. Gemini vision not required.",
                reason="Caller completed the spoken task step.",
                status="user_confirmed_only",
            )

        if frame_sent:
            # Gemini has received the frame and will speak its analysis.
            # Return UNCONFIRMED so the state machine sends the task to
            # recovery_active — forcing the user to retry and actually show
            # evidence. The AI will also verbally challenge via the
            # verification prompt.
            return VerificationDecision(
                block_reason="ai_visual_verification_pending",
                confidence_band="low",
                is_mock=False,
                last_verified_item=None,
                mock_label=None,
                notes=(
                    f"Gemini vision analysis sent for {task_name}. "
                    "AI is verifying visually. Task remains unconfirmed until "
                    "the AI can see evidence of completion."
                ),
                reason=f"Visual verification pending for {task_name}. Show the completed task to the camera.",
                status="unconfirmed",
            )

        # Frame could not be sent — fall back to user-confirmed
        return VerificationDecision(
            block_reason=None,
            confidence_band="low",
            is_mock=False,
            last_verified_item=task_name if isinstance(task_name, str) else None,
            mock_label=None,
            notes="Gemini vision unavailable for this attempt. Falling back to caller confirmation.",
            reason="Vision analysis unavailable; logged as caller-confirmed only.",
            status="user_confirmed_only",
        )


async def send_room_scan_frame(
    gemini_session: GeminiLiveSession,
    frame_base64: str,
    *,
    session_id: str,
    mime_type: str = "image/jpeg",
) -> bool:
    """Send a room scan frame to Gemini during calibration.

    Returns True if the frame was sent successfully.
    """
    try:
        image_bytes = base64.b64decode(frame_base64)
    except Exception:
        return False

    if not image_bytes:
        return False

    try:
        await gemini_session.send_image_frame(image_bytes, mime_type=mime_type)
        await gemini_session.send_text_input(ROOM_SCAN_ANALYSIS_PROMPT)
        log_event(
            LOGGER,
            logging.INFO,
            "room_scan_frame_sent",
            session_id=session_id,
            frame_bytes=len(image_bytes),
        )
        return True
    except GeminiLiveSessionError as exc:
        log_event(
            LOGGER,
            logging.ERROR,
            "room_scan_frame_failed",
            session_id=session_id,
            detail=str(exc),
        )
        return False


# --------------------------------------------------------------------------- #
# Structured room scan: ask Gemini to include parseable room feature markers   #
# --------------------------------------------------------------------------- #

ROOM_SCAN_STRUCTURED_PROMPT = (
    "ROOM_ASSESSMENT: Based on everything you have seen during the room scan, "
    "now deliver your assessment. In character as The Archivist, describe the "
    "room and its spectral readings. "
    "IMPORTANT — at the end of your spoken assessment, silently include this "
    "exact block (the caller won't hear it, it's for our containment records):\n"
    "ROOM_FEATURES: "
    "threshold=YES_OR_NO, "
    "flat_surface=YES_OR_NO, "
    "paper=YES_OR_NO, "
    "light_controllable=YES_OR_NO, "
    "reflective_surface=YES_OR_NO, "
    "water_source=YES_OR_NO\n"
    "Replace YES_OR_NO with YES if you observed that feature in the room or "
    "NO if you did not. Base this only on what you actually saw."
)


def parse_room_scan_affordances(
    transcript_text: str,
) -> dict[str, bool] | None:
    """Parse ROOM_FEATURES markers from Gemini's transcript output.

    Returns a dict of affordance booleans, or None if no marker was found.
    """
    import re

    match = re.search(r"ROOM_FEATURES:\s*(.+)", transcript_text, re.IGNORECASE)
    if match is None:
        return None

    features_str = match.group(1).strip()
    result: dict[str, bool] = {}
    for pair in features_str.split(","):
        pair = pair.strip()
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        key = key.strip().lower()
        value = value.strip().upper()
        result[key] = value == "YES"

    expected_keys = {
        "threshold",
        "flat_surface",
        "paper",
        "light_controllable",
        "reflective_surface",
        "water_source",
    }
    if not expected_keys.intersection(result.keys()):
        return None

    return result


# --------------------------------------------------------------------------- #
# AI-reasoned recovery directive template                                      #
# --------------------------------------------------------------------------- #

AI_RECOVERY_DIRECTIVE_TEMPLATE = (
    "RECOVERY_GUIDANCE: The caller attempted the task '{task_name}' "
    "({task_id}). Verification came back as {status}. "
    "The block reason was: {block_reason}. "
    "Look at the most recent frame you received. Based on what you see and "
    "know about the task, give the caller ONE specific, actionable instruction "
    "to fix the issue. Be concise and procedural. Do not repeat the task "
    "description — tell them exactly what to adjust."
)

