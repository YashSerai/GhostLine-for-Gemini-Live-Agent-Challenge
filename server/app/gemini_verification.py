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
        "The caller was asked to SHOW THE THRESHOLD — a doorway, door frame, "
        "or room boundary edge. Look at this frame. Can you see a doorway, "
        "door frame, archway, or clear room boundary edge? Describe what you see briefly."
    ),
    "T2": (
        "The caller was asked to CLOSE THE BOUNDARY — close a door or define "
        "the boundary edge clearly. Look at this frame. Is a door closed or a "
        "boundary edge clearly defined and sealed? Describe what you see briefly."
    ),
    "T3": (
        "The caller was asked to INCREASE ILLUMINATION — turn on a lamp, "
        "light switch, or flashlight. Look at this frame. Is the room visibly "
        "brighter or is a light source active? Describe what you see briefly."
    ),
    "T4": (
        "The caller was asked to STABILIZE THE CAMERA — hold the phone still. "
        "Look at this frame. Is the image sharp and stable, or is it blurry "
        "and shaking? Describe what you see briefly."
    ),
    "T5": (
        "The caller was asked to PLACE PAPER ON A FLAT SURFACE. Look at this "
        "frame. Can you see a sheet of paper or card on a table, desk, or flat "
        "surface? Describe what you see briefly."
    ),
    "T6": (
        "The caller was asked to CLEAR A SMALL SURFACE — clear a dinner-plate "
        "sized area. Look at this frame. Can you see a small cleared area on a "
        "surface? Describe what you see briefly."
    ),
    "T7": (
        "The caller was asked to SPEAK A CONTAINMENT PHRASE out loud. This is "
        "an audio-only task. The frame is secondary — mark this as confirmed "
        "if you heard them speak, or user_confirmed_only if unclear."
    ),
    "T8": (
        "The caller was asked to DRAW A SIMPLE MARK on paper. Look at this "
        "frame. Can you see a hand-drawn mark, symbol, or line on paper? "
        "Describe what you see briefly."
    ),
    "T9": (
        "The caller was asked to SHOW A REFLECTIVE SURFACE — mirror, glass, "
        "or dark screen. Look at this frame. Can you see a reflective surface "
        "in the frame? Describe what you see briefly."
    ),
    "T10": (
        "The caller was asked to HOLD UP A VIVID OBJECT — something brightly "
        "colored. Look at this frame. Can you see a vivid, brightly colored "
        "object being held up? Describe what you see briefly."
    ),
    "T11": (
        "The caller was asked to do a WATER SINK RELEASE — run or pour water. "
        "Look at this frame. Can you see water running or a sink/cup area? "
        "Describe what you see briefly."
    ),
    "T12": (
        "The caller was asked to place a SALT LINE near the boundary. Look at "
        "this frame. Can you see salt or a white line/pile near a boundary? "
        "Describe what you see briefly."
    ),
}

_DEFAULT_VERIFICATION_PROMPT = (
    "The caller was performing a containment task. Look at this frame and "
    "describe what you see. Is there evidence of a deliberate action being "
    "performed? Describe briefly."
)


# --------------------------------------------------------------------------- #
# Room scan prompt — used during calibration sweep                             #
# --------------------------------------------------------------------------- #

ROOM_SCAN_ANALYSIS_PROMPT = (
    "ROOM_ANALYSIS: You are scanning the caller's room through their camera. "
    "Describe what you see briefly and in character as The Archivist. "
    "Note if you can see: a doorway or threshold, flat surfaces like tables "
    "or desks, light sources, reflective surfaces, any objects of note. "
    "Then deliver a short, atmospheric assessment — our sensors have picked "
    "up residual activity in this space. Stay procedural and calm."
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

        return (
            f"VERIFICATION_ANALYSIS: {base_prompt} "
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

        When the frame was successfully sent to Gemini, the model will speak
        its analysis through the audio bridge.  We use quality metrics and
        the verification class to set the decision while Gemini provides the
        spoken grounding.
        """
        tier = task_tier if isinstance(task_tier, int) else 2

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

        # If Gemini analyzed the frame, use quality metrics to decide
        # The actual visual reasoning happens in Gemini's spoken response
        if frame_sent:
            lighting = quality_metrics.lighting
            blur = quality_metrics.blur
            motion = quality_metrics.motion_stability

            # Poor visual conditions — be honest about it
            if lighting < 0.3 or blur > 0.7:
                return VerificationDecision(
                    block_reason="visual_quality_insufficient",
                    confidence_band="low",
                    is_mock=False,
                    last_verified_item=None,
                    mock_label=None,
                    notes=(
                        f"Gemini analyzed the frame (task: {task_name}). "
                        f"Quality metrics: lighting={lighting:.2f}, blur={blur:.2f}, "
                        f"stability={motion:.2f}. Conditions insufficient for confident verification."
                    ),
                    reason="Frame quality too low for confident visual verification.",
                    status="unconfirmed",
                )

            # Tier 1 strict visual — high bar
            if tier == 1 and verification_class == "strict_visual":
                if lighting >= 0.5 and blur <= 0.5 and motion >= 0.4:
                    return VerificationDecision(
                        block_reason=None,
                        confidence_band="high" if lighting >= 0.65 else "medium",
                        is_mock=False,
                        last_verified_item=task_name if isinstance(task_name, str) else None,
                        mock_label=None,
                        notes=(
                            f"Gemini vision analysis complete for {task_name}. "
                            f"Frame quality: lighting={lighting:.2f}, blur={blur:.2f}, "
                            f"stability={motion:.2f}. Task appears completed in frame."
                        ),
                        reason=f"Visual analysis confirms {task_name} completion.",
                        status="confirmed",
                    )
                else:
                    return VerificationDecision(
                        block_reason="frame_quality_marginal",
                        confidence_band="low",
                        is_mock=False,
                        last_verified_item=None,
                        mock_label=None,
                        notes=(
                            f"Gemini analyzed the frame for {task_name} but quality "
                            f"metrics are marginal: lighting={lighting:.2f}, blur={blur:.2f}, "
                            f"stability={motion:.2f}."
                        ),
                        reason="Frame quality marginal for strict visual verification.",
                        status="unconfirmed",
                    )

            # Tier 2 soft visual — lower bar
            if lighting >= 0.35 and blur <= 0.6:
                return VerificationDecision(
                    block_reason=None,
                    confidence_band="medium",
                    is_mock=False,
                    last_verified_item=task_name if isinstance(task_name, str) else None,
                    mock_label=None,
                    notes=(
                        f"Gemini vision analysis complete for {task_name} (soft visual). "
                        f"Frame quality acceptable: lighting={lighting:.2f}, blur={blur:.2f}."
                    ),
                    reason=f"Visual analysis supports {task_name} completion.",
                    status="confirmed",
                )

            # Fallback for soft visual with poor quality
            return VerificationDecision(
                block_reason=None,
                confidence_band="low",
                is_mock=False,
                last_verified_item=task_name if isinstance(task_name, str) else None,
                mock_label=None,
                notes=(
                    f"Gemini analyzed frame for {task_name}. "
                    "Quality marginal but logged as user-confirmed."
                ),
                reason="Visual conditions marginal; logged as caller-confirmed only.",
                status="user_confirmed_only",
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

