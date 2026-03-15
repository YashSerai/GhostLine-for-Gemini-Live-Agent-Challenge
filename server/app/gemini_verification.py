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
        "VERIFICATION — 3-GATE CHECK for 'Show Threshold':\n"
        "GATE 1: Is this frame clear enough to analyze? If dark/blurry/shaky: "
        "'I cannot verify — frame is not readable.'\n"
        "GATE 2: Do you see a doorway, door frame, or room boundary edge? "
        "If NOT visible: 'I do not see a threshold. Show me.'\n"
        "GATE 3: Is the threshold CLEARLY defined in frame? Only confirm if "
        "OBVIOUS: 'Confirmed. Threshold is visible.' Otherwise: 'Not confirmed.'"
    ),
    "T2": (
        "VERIFICATION — 3-GATE CHECK for 'Close Boundary':\n"
        "GATE 1 — FRAME QUALITY: Is this frame clear enough to analyze? If "
        "dark, blurry, or shaky: respond ONLY with 'I cannot verify — frame "
        "is not readable.' STOP.\n"
        "GATE 2 — OBJECT PRESENCE: Do you see a door in this frame? Look for "
        "a door, door frame, or doorway. If you cannot see ANY door: respond "
        "'I do not see a door. Point the camera at the door.' STOP.\n"
        "GATE 3 — COMPLETION EVIDENCE: Compare this frame to your BASELINE "
        "memory. In the baseline the door was OPEN — you should have seen a "
        "gap, light from the other side, or an open doorway. NOW, is the door "
        "CLOSED? Look for: the gap is gone, door flush against the frame, no "
        "light leaking through. If the door still shows a gap or open space: "
        "'The door still appears open. Close it fully.' "
        "ONLY say 'CONFIRMED' if the door is OBVIOUSLY, VISIBLY closed and "
        "flush with its frame."
    ),
    "T3": (
        "VERIFICATION — 3-GATE CHECK for 'Increase Illumination':\n"
        "GATE 1: Is this frame clear enough to analyze? If dark/blurry/shaky: "
        "'I cannot verify — frame is not readable.'\n"
        "GATE 2: Do you see a light source or light switch? If NOT visible: "
        "'I do not see a light source. Show me where the light is.'\n"
        "GATE 3: Is the room VISIBLY brighter than baseline? Look for: light on, "
        "increased exposure, fewer shadows. If same darkness: "
        "'Room still looks dim. Turn on a light.' Only confirm if OBVIOUSLY brighter."
    ),
    "T4": (
        "VERIFICATION — 3-GATE CHECK for 'Stabilize Camera':\n"
        "GATE 1: Is the frame sharp and clear? If still blurry/shaky: "
        "'The image is still unstable. Hold the camera steady.'\n"
        "GATE 2: Can you see a clear room scene? If NOT: "
        "'I cannot see the room clearly. Steady the camera.'\n"
        "GATE 3: Is the image NOTICEABLY steadier than baseline? "
        "Only confirm if sharp and stable."
    ),
    "T5": (
        "VERIFICATION — 3-GATE CHECK for 'Place Paper on Surface':\n"
        "GATE 1 — FRAME QUALITY: Is this frame clear enough to analyze? If "
        "dark, blurry, or obstructed: respond ONLY with 'I cannot verify — "
        "frame is not readable.' STOP.\n"
        "GATE 2 — OBJECT PRESENCE: Do you see a flat surface (table, desk, "
        "floor)? If NOT visible: respond 'I do not see a surface. Show me "
        "the surface.' STOP.\n"
        "GATE 3 — COMPLETION EVIDENCE: Compare this frame to your BASELINE "
        "memory. In the baseline the surface was EMPTY. NOW, look for a "
        "white or light-colored rectangular shape (paper/sheet) ON the "
        "surface. It should be flat, roughly A4/letter size. If the surface "
        "still looks empty with no paper: 'I see no paper on that surface. "
        "Place it and show me.' "
        "ONLY say 'CONFIRMED' if you can CLEARLY see paper sitting on the "
        "surface that was not there before."
    ),
    "T6": (
        "VERIFICATION — 3-GATE CHECK for 'Clear Small Surface':\n"
        "GATE 1: Is this frame clear enough? If dark/blurry: "
        "'I cannot verify — frame is not readable.'\n"
        "GATE 2: Do you see the surface area? If NOT: 'Show me the surface.'\n"
        "GATE 3: Is the surface VISIBLY cleared compared to baseline? "
        "If still cluttered: 'Surface still has items. Not cleared.' "
        "Only confirm if OBVIOUSLY clear."
    ),
    "T7": (
        "VERIFICATION CHECK: The caller was asked to SPEAK A CONTAINMENT PHRASE. "
        "This is audio-only — no visual check needed. If you heard them speak a "
        "clear phrase, confirm it. If you heard nothing or it was unclear: "
        "'I did not hear a clear phrase. Say it again.'"
    ),
    "T8": (
        "VERIFICATION — 3-GATE CHECK for 'Draw Simple Mark':\n"
        "GATE 1: Is this frame clear enough? If dark/blurry: "
        "'I cannot verify — frame is not readable.'\n"
        "GATE 2: Do you see paper or card? If NOT: 'Show me the paper.'\n"
        "GATE 3: Does the paper NOW show a drawn mark that was NOT there "
        "in baseline? If still blank: 'I see no mark. Draw one and show me.' "
        "Only confirm if mark is OBVIOUSLY visible."
    ),
    "T9": (
        "VERIFICATION — 3-GATE CHECK for 'Show Reflective Surface':\n"
        "GATE 1: Is this frame clear enough? If dark/blurry: "
        "'I cannot verify — frame is not readable.'\n"
        "GATE 2: Do you see a mirror, glass, or reflective surface? "
        "If NOT: 'I do not see a reflective surface. Show me.'\n"
        "GATE 3: Is a reflective surface CLEARLY held toward the camera? "
        "Only confirm if OBVIOUSLY visible."
    ),
    "T10": (
        "VERIFICATION — 3-GATE CHECK for 'Hold Up Vivid Object':\n"
        "GATE 1: Is this frame clear enough? If dark/blurry: "
        "'I cannot verify — frame is not readable.'\n"
        "GATE 2: Do you see the caller's hands or the area in frame? "
        "If NOT: 'I cannot see the area. Show me.'\n"
        "GATE 3: Is a brightly colored object NOW held in frame where "
        "there was NOT one in baseline? If nothing new: "
        "'I do not see a vivid object. Hold it up.' Only confirm if OBVIOUS."
    ),
    "T11": (
        "VERIFICATION — 3-GATE CHECK for 'Water Sink Release':\n"
        "GATE 1: Is this frame clear enough? If dark/blurry: "
        "'I cannot verify — frame is not readable.'\n"
        "GATE 2: Do you see a sink or water source? "
        "If NOT: 'I do not see a water source. Show me.'\n"
        "GATE 3: Is water VISIBLY running or being poured compared to "
        "baseline? If dry: 'I see no water flow. Show me.' "
        "Only confirm if water motion is OBVIOUS."
    ),
    "T12": (
        "VERIFICATION — 3-GATE CHECK for 'Salt Line':\n"
        "GATE 1: Is this frame clear enough? If dark/blurry: "
        "'I cannot verify — frame is not readable.'\n"
        "GATE 2: Do you see the floor near the boundary? "
        "If NOT: 'Show me the floor near the boundary.'\n"
        "GATE 3: Is salt VISIBLY on the floor that was NOT there in baseline? "
        "If floor looks the same: 'I see no salt. Show me.' "
        "Only confirm if salt is OBVIOUSLY visible."
    ),
}

_DEFAULT_VERIFICATION_PROMPT = (
    "VERIFICATION — DEFAULT 3-GATE CHECK:\n"
    "GATE 1: Is this frame clear enough to analyze? If dark, blurry, shaky, "
    "or obstructed: 'I cannot verify — the frame is not readable.'\n"
    "GATE 2: Can you see the area relevant to the task? If NOT: "
    "'I cannot see what I need. Show me.'\n"
    "GATE 3: Do you see evidence that a deliberate action was completed? "
    "DEFAULT TO NOT CONFIRMED. Only confirm if the evidence is OBVIOUS and "
    "UNMISTAKABLE. If unsure: 'I do not see the task completed. Show me.' "
    "NEVER bluff. NEVER assume."
)


# --------------------------------------------------------------------------- #
# Room scan prompt — used during calibration sweep                             #
# --------------------------------------------------------------------------- #

ROOM_SCAN_ANALYSIS_PROMPT = (
    "ROOM_ANALYSIS: You are scanning the caller's room through their camera. "
    "FIRST assess frame quality — if the frame is dark, blurry, shaky, or "
    "unclear for ANY reason, say so immediately: 'The feed is not usable. "
    "Check your camera.' Do NOT describe a room you cannot see.\n"
    "If the frame IS clear: describe ONLY what you ACTUALLY see — do NOT "
    "assume or invent objects. Keep it brief and in character as The Archivist. "
    "After observing the room, deliver a short atmospheric assessment. "
    "Stay procedural and calm."
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

        # Server-side brightness check — reject black/very dark frames
        _MIN_SIZE = 800
        _MIN_BRIGHTNESS = 20
        if len(image_bytes) < _MIN_SIZE:
            log_event(LOGGER, logging.INFO, "frame_for_analysis_rejected_small",
                      session_id=self.session_id, frame_bytes=len(image_bytes))
            return False
        start = len(image_bytes) // 4
        end = start + min(200, len(image_bytes) // 2)
        sample = image_bytes[start:end]
        if sample and sum(sample) / len(sample) < _MIN_BRIGHTNESS:
            log_event(LOGGER, logging.INFO, "frame_for_analysis_rejected_dark",
                      session_id=self.session_id)
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

    # Server-side brightness check — reject black/very dark frames
    _MIN_SIZE = 800
    _MIN_BRIGHTNESS = 20
    if len(image_bytes) < _MIN_SIZE:
        log_event(LOGGER, logging.INFO, "room_scan_frame_rejected_small",
                  session_id=session_id, frame_bytes=len(image_bytes))
        return False
    start = len(image_bytes) // 4
    end = start + min(200, len(image_bytes) // 2)
    sample = image_bytes[start:end]
    if sample and sum(sample) / len(sample) < _MIN_BRIGHTNESS:
        log_event(LOGGER, logging.INFO, "room_scan_frame_rejected_dark",
                  session_id=session_id)
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

