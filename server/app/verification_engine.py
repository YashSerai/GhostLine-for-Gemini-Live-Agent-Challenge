"""Shared verification engine contract for Prompt 22 and later real verification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

from .capability_profile import CapabilityProfile, QualityMetrics

VerificationResultStatus = Literal[
    "confirmed",
    "unconfirmed",
    "user_confirmed_only",
]
ConfidenceBand = Literal["low", "medium", "high"]


class VerificationEngineError(RuntimeError):
    """Raised when a verification engine cannot produce a result."""


@dataclass(frozen=True)
class VerificationFrameInput:
    captured_at: str
    height: int
    mime_type: str
    sequence: int
    total_frames: int
    width: int


@dataclass(frozen=True)
class VerificationContext:
    attempt_id: str
    capability_profile: CapabilityProfile
    current_path_mode: str
    frames: tuple[VerificationFrameInput, ...]
    quality_metrics: QualityMetrics
    raw_transcript_snippet: str | None
    recent_user_transcripts: tuple[str, ...]
    session_id: str
    source: str
    started_at: str
    task_context: dict[str, Any]


@dataclass(frozen=True)
class VerificationDecision:
    block_reason: str | None
    confidence_band: ConfidenceBand
    is_mock: bool
    last_verified_item: str | None
    mock_label: str | None
    notes: str | None
    reason: str
    status: VerificationResultStatus


class VerificationEngine(Protocol):
    async def evaluate(
        self,
        context: VerificationContext,
    ) -> VerificationDecision:
        """Return a verification decision for a completed Ready-to-Verify window."""
