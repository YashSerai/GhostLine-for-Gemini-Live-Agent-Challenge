/**
 * Prompt 3 shared contract skeleton.
 *
 * These machine-readable labels are the TypeScript mirror of the locked
 * product constants defined in the source docs. Keep them aligned with the
 * Python mirror in ../python/product_constants.py.
 */

export const TASK_IDS = [
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
] as const;
export type TaskId = (typeof TASK_IDS)[number];

export const TASK_TIERS = [1, 2, 3] as const;
export type TaskTier = (typeof TASK_TIERS)[number];

export const TASK_ROLE_CATEGORIES = [
  "containment",
  "diagnostic",
  "flavor",
] as const;
export type TaskRoleCategory = (typeof TASK_ROLE_CATEGORIES)[number];

export const PATH_MODES = [
  "threshold",
  "tabletop",
  "low_visibility",
] as const;
export type PathMode = (typeof PATH_MODES)[number];

export const VERIFICATION_RESULT_STATUSES = [
  "confirmed",
  "unconfirmed",
  "user_confirmed_only",
] as const;
export type VerificationResultStatus =
  (typeof VERIFICATION_RESULT_STATUSES)[number];

// The product doc lists these states in prose with spaces.
// Snake_case is the shared machine format for frontend/backend code.
export const SESSION_STATES = [`r`n  "init",`r`n  "call_connected",`r`n  "consent",`r`n  "microphone_request",`r`n  "name_request",`r`n  "name_confirmation",`r`n  "camera_request",`r`n  "room_sweep",`r`n  "calibration",`r`n  "task_assigned",`r`n  "waiting_ready",`r`n  "verifying",`r`n  "diagnosis_beat",`r`n  "recovery_active",`r`n  "swap_pending",`r`n  "paused",`r`n  "completed",`r`n  "case_report",`r`n  "ended",`r`n] as const;
export type SessionState = (typeof SESSION_STATES)[number];

export const CASE_REPORT_VERDICTS = [
  "secured",
  "partial",
  "inconclusive",
] as const;
export type CaseReportVerdict = (typeof CASE_REPORT_VERDICTS)[number];

export const UI_STATUS_LABELS = [
  "speaking",
  "listening",
  "interrupted",
] as const;
export type UiStatusLabel = (typeof UI_STATUS_LABELS)[number];

export const PRODUCT_CONSTANTS = {
  taskIds: TASK_IDS,
  taskTiers: TASK_TIERS,
  taskRoleCategories: TASK_ROLE_CATEGORIES,
  pathModes: PATH_MODES,
  verificationResultStatuses: VERIFICATION_RESULT_STATUSES,
  sessionStates: SESSION_STATES,
  caseReportVerdicts: CASE_REPORT_VERDICTS,
  uiStatusLabels: UI_STATUS_LABELS,
} as const;

