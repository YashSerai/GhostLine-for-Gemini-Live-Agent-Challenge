"""Temporary Prompt 22 mock verifier.

TODO(Prompt 23): Replace this module with the real task-aware verification
engine. This file must stay isolated so mock verification cannot become
accidental shipping logic.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from .config import MockVerificationSettings
from .logging_utils import log_event
from .verification_engine import (
    ConfidenceBand,
    VerificationContext,
    VerificationDecision,
    VerificationEngineError,
    VerificationResultStatus,
)

LOGGER = logging.getLogger("ghostline.backend.mock_verification")
_MOCK_LABEL = "MOCK VERIFIER"


@dataclass(frozen=True)
class MockVerificationEngine:
    """Development-only verification engine for early UI/system testing.

    TODO(Prompt 23): Remove this engine from runtime wiring once the real
    verifier is available behind the same VerificationEngine interface.
    """

    settings: MockVerificationSettings

    async def evaluate(
        self,
        context: VerificationContext,
    ) -> VerificationDecision:
        if not self.settings.enabled:
            raise VerificationEngineError(
                "Mock verification cannot evaluate when the config flag is disabled."
            )

        task_tier = _parse_task_tier(context.task_context.get("taskTier"))
        task_name = _parse_task_name(context.task_context.get("taskName"))
        status = self._resolve_status(task_tier)
        decision = VerificationDecision(
            block_reason=_build_block_reason(status),
            confidence_band=_build_confidence_band(status),
            is_mock=True,
            last_verified_item=task_name if status != "unconfirmed" else None,
            mock_label=_MOCK_LABEL,
            notes=_build_notes(task_tier, status),
            reason=_build_reason(task_tier, status),
            status=status,
        )

        log_event(
            LOGGER,
            logging.WARNING,
            "mock_verification_result_generated",
            session_id=context.session_id,
            verification_attempt_id=context.attempt_id,
            mock=True,
            mock_label=_MOCK_LABEL,
            status=decision.status,
            confidence_band=decision.confidence_band,
            task_tier=task_tier,
            task_name=task_name,
            captured_frame_count=len(context.frames),
            source=context.source,
            forced_failure=self.settings.force_failure,
            raw_transcript_snippet=context.raw_transcript_snippet,
        )
        return decision

    def _resolve_status(
        self,
        task_tier: int | None,
    ) -> VerificationResultStatus:
        if self.settings.force_failure:
            return "unconfirmed"
        if task_tier == 1:
            return self.settings.tier1_result
        if task_tier == 2:
            return self.settings.tier2_result
        if task_tier == 3:
            return self.settings.tier3_result
        return self.settings.unknown_tier_result


def _parse_task_tier(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value in {1, 2, 3}:
        return value
    if isinstance(value, str) and value.strip() in {"1", "2", "3"}:
        return int(value.strip())
    return None


def _parse_task_name(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "Ready-to-Verify capture"


def _build_block_reason(
    status: VerificationResultStatus,
) -> str | None:
    if status == "unconfirmed":
        return (
            "MOCK VERIFIER: forced failure or mock unconfirmed outcome for recovery testing."
        )
    return None


def _build_confidence_band(
    status: VerificationResultStatus,
) -> ConfidenceBand:
    if status == "confirmed":
        return "high"
    if status == "user_confirmed_only":
        return "medium"
    return "low"


def _build_reason(
    task_tier: int | None,
    status: VerificationResultStatus,
) -> str:
    if task_tier is None:
        return (
            "MOCK VERIFIER: no task tier was provided, so the configured fallback "
            "result was used."
        )
    return (
        f"MOCK VERIFIER: Tier {task_tier} returned {status} under the development-only "
        "mock verification rules."
    )


def _build_notes(
    task_tier: int | None,
    status: VerificationResultStatus,
) -> str:
    if task_tier is None:
        return (
            "MOCK VERIFIER: task tier was unresolved, so the configured fallback "
            "mock result was used."
        )
    return (
        f"MOCK VERIFIER: Tier {task_tier} produced a {status} result using "
        "development-only mock verification rules."
    )

