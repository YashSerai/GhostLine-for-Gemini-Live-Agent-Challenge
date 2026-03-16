"""Prompt 3 shared contract skeleton for backend-side mirrors."""

from __future__ import annotations

from typing import Final, Literal, TypeAlias

TASK_IDS: Final = (
    "T1",
    "T2",
    "T3",
    "T4",
    "T5",
    "T6",
    "T7",
    "T8",
    "T9",
    "T10",
    "T11",
    "T12",
    "T13",
    "T14",
    "T15",
)
TaskId: TypeAlias = Literal[
    "T1",
    "T2",
    "T3",
    "T4",
    "T5",
    "T6",
    "T7",
    "T8",
    "T9",
    "T10",
    "T11",
    "T12",
    "T13",
    "T14",
    "T15",
]

TASK_TIERS: Final = (1, 2, 3)
TaskTier: TypeAlias = Literal[1, 2, 3]

TASK_ROLE_CATEGORIES: Final = (
    "containment",
    "diagnostic",
    "flavor",
)
TaskRoleCategory: TypeAlias = Literal[
    "containment",
    "diagnostic",
    "flavor",
]

PATH_MODES: Final = (
    "threshold",
    "tabletop",
    "low_visibility",
)
PathMode: TypeAlias = Literal[
    "threshold",
    "tabletop",
    "low_visibility",
]

VERIFICATION_RESULT_STATUSES: Final = (
    "confirmed",
    "unconfirmed",
    "user_confirmed_only",
)
VerificationResultStatus: TypeAlias = Literal[
    "confirmed",
    "unconfirmed",
    "user_confirmed_only",
]

# The product doc lists these states in prose with spaces.
# Snake_case is the shared machine format for frontend/backend code.
SESSION_STATES: Final = (`r`n    "init",`r`n    "call_connected",`r`n    "consent",`r`n    "microphone_request",`r`n    "name_request",`r`n    "name_confirmation",`r`n    "camera_request",`r`n    "room_sweep",`r`n    "calibration",`r`n    "task_assigned",`r`n    "waiting_ready",`r`n    "verifying",`r`n    "diagnosis_beat",`r`n    "recovery_active",`r`n    "swap_pending",`r`n    "paused",`r`n    "completed",`r`n    "case_report",`r`n    "ended",`r`n)`r`nSessionState: TypeAlias = Literal[`r`n    "init",`r`n    "call_connected",`r`n    "consent",`r`n    "microphone_request",`r`n    "name_request",`r`n    "name_confirmation",`r`n    "camera_request",`r`n    "room_sweep",`r`n    "calibration",`r`n    "task_assigned",`r`n    "waiting_ready",`r`n    "verifying",`r`n    "diagnosis_beat",`r`n    "recovery_active",`r`n    "swap_pending",`r`n    "paused",`r`n    "completed",`r`n    "case_report",`r`n    "ended",`r`n]

CASE_REPORT_VERDICTS: Final = (
    "secured",
    "partial",
    "inconclusive",
)
CaseReportVerdict: TypeAlias = Literal[
    "secured",
    "partial",
    "inconclusive",
]

UI_STATUS_LABELS: Final = (
    "speaking",
    "listening",
    "interrupted",
)
UiStatusLabel: TypeAlias = Literal[
    "speaking",
    "listening",
    "interrupted",
]

PRODUCT_CONSTANTS: Final = {
    "taskIds": TASK_IDS,
    "taskTiers": TASK_TIERS,
    "taskRoleCategories": TASK_ROLE_CATEGORIES,
    "pathModes": PATH_MODES,
    "verificationResultStatuses": VERIFICATION_RESULT_STATUSES,
    "sessionStates": SESSION_STATES,
    "caseReportVerdicts": CASE_REPORT_VERDICTS,
    "uiStatusLabels": UI_STATUS_LABELS,
}

__all__ = [
    "CASE_REPORT_VERDICTS",
    "PATH_MODES",
    "PRODUCT_CONSTANTS",
    "SESSION_STATES",
    "TASK_IDS",
    "TASK_ROLE_CATEGORIES",
    "TASK_TIERS",
    "UI_STATUS_LABELS",
    "VERIFICATION_RESULT_STATUSES",
    "CaseReportVerdict",
    "PathMode",
    "SessionState",
    "TaskId",
    "TaskRoleCategory",
    "TaskTier",
    "UiStatusLabel",
    "VerificationResultStatus",
]

