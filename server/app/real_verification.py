"""Real task-aware verification engine for Prompt 23."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from typing import Final

from .task_helpers import InvalidTaskIdError, get_task_by_id
from .task_library import TaskDefinition
from .verification_engine import (
    ConfidenceBand,
    VerificationContext,
    VerificationDecision,
)

LOGGER = logging.getLogger("ghostline.backend.real_verification")
_NUMBER_WORD_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|\d+)\b"
)
_READY_TO_VERIFY_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(ready to verify|verify now|can you verify|can you check it|check it now|take a look now|ready for you to check)\b"
)
_WORD_RE: Final[re.Pattern[str]] = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class RealVerificationEngine:
    """Deterministic task-aware verifier for Ready-to-Verify windows."""

    async def evaluate(
        self,
        context: VerificationContext,
    ) -> VerificationDecision:
        task = _resolve_task(context)
        if task is None:
            return VerificationDecision(
                block_reason=(
                    "No active task ID was attached to this verification attempt, so the system cannot apply task-aware verification honestly."
                ),
                confidence_band="low",
                is_mock=False,
                last_verified_item=None,
                mock_label=None,
                notes="Real verification requires a concrete task ID from the active session state.",
                reason="The verification attempt did not include an active task ID.",
                status="unconfirmed",
            )

        if task.verification_class == "self_report":
            return _evaluate_transcript_task(task, context)

        if task.story_function in {"boundary", "seal"} and task.id in {"T1", "T2"}:
            return _evaluate_boundary_task(task, context)

        if task.story_function == "visibility" and task.id == "T3":
            return _evaluate_illumination_task(task, context)

        if task.story_function == "stabilization":
            return _evaluate_stabilization_task(task, context)

        if task.story_function == "anchor":
            return _evaluate_anchor_task(task, context)

        if task.verification_class == "soft_visual":
            return _evaluate_soft_visual_task(task, context)

        return VerificationDecision(
            block_reason="The task-aware verifier does not yet have a handler for this task class.",
            confidence_band="low",
            is_mock=False,
            last_verified_item=None,
            mock_label=None,
            notes=f"Unhandled verification path for task {task.id}.",
            reason="No task-specific verification rule matched this task.",
            status="unconfirmed",
        )


def _resolve_task(context: VerificationContext) -> TaskDefinition | None:
    task_id = context.task_context.get("taskId")
    if not isinstance(task_id, str) or not task_id.strip():
        return None

    try:
        return get_task_by_id(task_id.strip())
    except InvalidTaskIdError:
        return None


def _evaluate_boundary_task(
    task: TaskDefinition,
    context: VerificationContext,
) -> VerificationDecision:
    quality = context.quality_metrics
    strong_visual = (
        quality.lighting >= 0.5
        and quality.blur <= 0.45
        and quality.motion_stability >= 0.55
    )
    moderate_visual = (
        quality.lighting >= 0.4
        and quality.blur <= 0.6
        and quality.motion_stability >= 0.45
    )
    path_support = (
        context.current_path_mode == "threshold"
        or context.capability_profile.environment.threshold_ready
    )
    declaration = _has_declaration(
        context,
        keywords=("door", "threshold", "closed", "shut", "boundary"),
    )

    if strong_visual and path_support:
        return _decision(
            status="confirmed",
            confidence_band="high",
            reason="Boundary framing stayed visible and stable across the verification window.",
            last_verified_item=task.name,
            notes="Boundary task used threshold/path evidence plus strong visual quality.",
        )

    if moderate_visual and declaration:
        return _decision(
            status="user_confirmed_only",
            confidence_band="medium",
            reason="Boundary framing was partially usable, but not strong enough for full visual confirmation.",
            last_verified_item=task.name,
            notes="Boundary task fell back to partial visual support plus user declaration.",
        )

    return _decision(
        status="unconfirmed",
        confidence_band="low",
        reason="The boundary task could not be confirmed from the verification window.",
        block_reason=_visual_block_reason(context, prefer_threshold=True),
        notes="Boundary task requires visible threshold framing without bluffing partial visibility.",
    )


def _evaluate_illumination_task(
    task: TaskDefinition,
    context: VerificationContext,
) -> VerificationDecision:
    quality = context.quality_metrics
    declaration = _has_declaration(
        context,
        keywords=("light", "lamp", "brighter", "turned on", "switch"),
    )

    if quality.lighting >= 0.68 and quality.blur <= 0.55:
        return _decision(
            status="confirmed",
            confidence_band="high",
            reason="Scene brightness is measurably strong enough to confirm the illumination step.",
            last_verified_item=task.name,
            notes="Illumination task used measured lighting quality and stable scene context.",
        )

    if quality.lighting >= 0.5 and declaration:
        return _decision(
            status="user_confirmed_only",
            confidence_band="medium",
            reason="Lighting improved, but not enough for full visual confirmation.",
            last_verified_item=task.name,
            notes="Illumination task relied on measurable improvement plus user declaration.",
        )

    return _decision(
        status="unconfirmed",
        confidence_band="low",
        reason="The frame remained too dim for a full illumination confirmation.",
        block_reason="The verification window is still too dark to confirm the illumination step honestly.",
        notes="Illumination tasks require measurable brightness improvement, not a guessed confirmation.",
    )


def _evaluate_stabilization_task(
    task: TaskDefinition,
    context: VerificationContext,
) -> VerificationDecision:
    quality = context.quality_metrics
    declaration = _has_declaration(
        context,
        keywords=("still", "steady", "holding it", "stable"),
    )

    if quality.motion_stability >= 0.75 and quality.blur <= 0.5:
        return _decision(
            status="confirmed",
            confidence_band="high",
            reason="The frame remained stable enough across the window to confirm the stabilization step.",
            last_verified_item=task.name,
            notes="Stabilization task used motion and blur metrics together.",
        )

    if quality.motion_stability >= 0.58 and declaration:
        return _decision(
            status="user_confirmed_only",
            confidence_band="medium",
            reason="The frame improved, but not enough for a full visual stability confirmation.",
            last_verified_item=task.name,
            notes="Stabilization task used moderate motion quality plus user declaration.",
        )

    return _decision(
        status="unconfirmed",
        confidence_band="low",
        reason="The frame was still too unstable to confirm the stabilization step.",
        block_reason="The verification window remained too unstable or blurry to confirm stabilization.",
        notes="Stabilization tasks require measurable steadiness instead of assumed compliance.",
    )


def _evaluate_anchor_task(
    task: TaskDefinition,
    context: VerificationContext,
) -> VerificationDecision:
    quality = context.quality_metrics
    declaration_keywords = (
        ("paper", "placed", "down", "surface")
        if task.id == "T5"
        else ("clear", "surface", "table", "counter")
    )
    declaration = _has_declaration(context, keywords=declaration_keywords)
    flat_surface_blocked = context.capability_profile.user_constraints.no_flat_surface
    paper_blocked = context.capability_profile.user_constraints.no_paper
    tabletop_support = (
        context.current_path_mode == "tabletop"
        or context.capability_profile.environment.tabletop_ready
    )
    strong_visual = (
        quality.lighting >= 0.5
        and quality.blur <= 0.5
        and quality.motion_stability >= 0.6
    )

    if flat_surface_blocked or (task.id == "T5" and paper_blocked):
        return _decision(
            status="unconfirmed",
            confidence_band="low",
            reason="The anchor task conflicts with the declared environment constraints.",
            block_reason="The caller has already declared that the required anchor materials are unavailable.",
            notes="Anchor verification used capability-profile constraints to avoid bluffing object availability.",
        )

    if strong_visual and tabletop_support:
        return _decision(
            status="confirmed",
            confidence_band="high",
            reason="The anchor surface stayed visible and stable enough to confirm the placement step.",
            last_verified_item=task.name,
            notes="Anchor task used tabletop context plus strong visual quality.",
        )

    if declaration and (strong_visual or tabletop_support):
        return _decision(
            status="user_confirmed_only",
            confidence_band="medium",
            reason="The anchor step had some supporting visual evidence, but not enough for full confirmation.",
            last_verified_item=task.name,
            notes="Anchor task relied on partial visual evidence plus a user declaration.",
        )

    return _decision(
        status="unconfirmed",
        confidence_band="low",
        reason="The anchor step could not be verified from the captured window.",
        block_reason=_visual_block_reason(context),
        notes="Anchor tasks require a readable tabletop view; unresolved framing stays unconfirmed.",
    )


def _evaluate_soft_visual_task(
    task: TaskDefinition,
    context: VerificationContext,
) -> VerificationDecision:
    quality = context.quality_metrics
    declaration = _has_declaration(
        context,
        keywords=_soft_visual_keywords(task.id),
    )
    strong_visual = (
        quality.lighting >= 0.55
        and quality.blur <= 0.5
        and quality.motion_stability >= 0.55
    )
    moderate_visual = (
        quality.lighting >= 0.45
        and quality.blur <= 0.62
        and quality.motion_stability >= 0.45
    )

    if strong_visual and declaration:
        return _decision(
            status="confirmed",
            confidence_band="medium",
            reason="The medium-confidence task had both readable visual evidence and a matching declaration.",
            last_verified_item=task.name,
            notes="Soft-visual verification requires both usable frames and corroborating user language.",
        )

    if moderate_visual or declaration:
        return _decision(
            status="user_confirmed_only",
            confidence_band="medium" if declaration else "low",
            reason="The task had partial support, but not enough for a full visual confirmation.",
            last_verified_item=task.name if declaration else None,
            notes="Soft-visual tasks fall back to user-confirmed-only when confidence is limited.",
        )

    return _decision(
        status="unconfirmed",
        confidence_band="low",
        reason="The medium-confidence task could not be verified from the current evidence.",
        block_reason=_visual_block_reason(context),
        notes="Soft-visual tasks stay unconfirmed when neither frames nor declaration are strong enough.",
    )


def _evaluate_transcript_task(
    task: TaskDefinition,
    context: VerificationContext,
) -> VerificationDecision:
    transcripts = _relevant_transcripts(context)
    if task.id == "T7":
        usable_lines = [line for line in transcripts if _word_count(line) >= 3]
        if usable_lines:
            return _decision(
                status="confirmed",
                confidence_band="medium",
                reason="A final user transcript line captured the spoken containment step.",
                last_verified_item=task.name,
                notes="Speech verification used transcript evidence rather than visual guessing.",
            )
        return _decision(
            status="unconfirmed",
            confidence_band="low",
            reason="No usable final speech transcript was available for the containment phrase.",
            block_reason="The system did not capture a clear final user transcript for the speech step.",
            notes="Speech tasks rely on transcript/audio evidence instead of image frames.",
        )

    if task.id == "T13":
        if any(len(_NUMBER_WORD_RE.findall(line)) >= 2 for line in transcripts):
            return _decision(
                status="confirmed",
                confidence_band="medium",
                reason="The transcript contains counting evidence for the fallback pacing task.",
                last_verified_item=task.name,
                notes="Count-backward verification looked for number-word evidence in the transcript.",
            )
        return _decision(
            status="unconfirmed",
            confidence_band="low",
            reason="The transcript did not contain enough counting evidence to confirm the fallback task.",
            block_reason="No clear counting sequence was captured in the final transcript.",
            notes="Count-backward tasks require transcript evidence of multiple number tokens.",
        )

    if any(_word_count(line) >= 3 for line in transcripts):
        return _decision(
            status="confirmed",
            confidence_band="medium",
            reason="The transcript captured a substantive user response for the speech-based task.",
            last_verified_item=task.name,
            notes="Self-report and diagnosis tasks rely on transcript evidence, not visual confirmation.",
        )

    return _decision(
        status="unconfirmed",
        confidence_band="low",
        reason="No usable user transcript was available for the speech-based verification step.",
        block_reason="The final transcript was too short or missing for this speech task.",
        notes="Speech tasks remain unconfirmed without transcript evidence.",
    )


def _soft_visual_keywords(task_id: str) -> tuple[str, ...]:
    mapping = {
        "T8": ("mark", "drew", "drawn", "symbol"),
        "T9": ("mirror", "reflective", "screen", "spoon"),
        "T10": ("bright", "vivid", "object", "red", "blue"),
        "T11": ("water", "sink", "pour", "poured"),
        "T12": ("salt", "line", "pile"),
    }
    return mapping.get(task_id, ("done",))


def _decision(
    *,
    status: str,
    confidence_band: ConfidenceBand,
    reason: str,
    block_reason: str | None = None,
    last_verified_item: str | None = None,
    notes: str | None = None,
) -> VerificationDecision:
    return VerificationDecision(
        block_reason=block_reason,
        confidence_band=confidence_band,
        is_mock=False,
        last_verified_item=last_verified_item,
        mock_label=None,
        notes=notes,
        reason=reason,
        status=status,
    )


def _has_declaration(
    context: VerificationContext,
    *,
    keywords: tuple[str, ...],
) -> bool:
    normalized_lines = [_normalize_text(line) for line in _relevant_transcripts(context)]
    return any(any(keyword in line for keyword in keywords) for line in normalized_lines)


def _relevant_transcripts(context: VerificationContext) -> tuple[str, ...]:
    snippets: list[str] = []
    for line in (*context.recent_user_transcripts, context.raw_transcript_snippet):
        if not isinstance(line, str) or not line.strip():
            continue
        normalized = _normalize_text(line)
        if not normalized or _READY_TO_VERIFY_RE.search(normalized):
            continue
        if normalized not in {_normalize_text(existing) for existing in snippets}:
            snippets.append(line.strip())
    return tuple(snippets)


def _visual_block_reason(
    context: VerificationContext,
    *,
    prefer_threshold: bool = False,
) -> str:
    quality = context.quality_metrics
    if quality.lighting < 0.4:
        return "The verification window was too dark to confirm this task honestly."
    if quality.motion_stability < 0.45:
        return "The verification window was too unstable to confirm this task honestly."
    if quality.blur > 0.6:
        return "The verification window was too blurry to confirm this task honestly."
    if prefer_threshold and context.current_path_mode != "threshold":
        return "The verification window did not show a clear threshold or boundary framing."
    return "The verification window did not provide enough reliable evidence to confirm this task."


def _word_count(text: str) -> int:
    return len(_WORD_RE.findall(text.lower()))


def _normalize_text(text: str) -> str:
    return " ".join(_WORD_RE.findall(text.lower().replace("’", "'")))
