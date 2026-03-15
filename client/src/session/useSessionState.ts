import { useEffect, useState } from "react";

import type {
  SessionConnectionStatus,
  SessionEnvelopeListener,
} from "./sessionTypes";
import type { VerificationTaskContext } from "../verification/useReadyToVerifyFlow";

export interface SessionAllowedActions {
  canEnd: boolean;
  canPause: boolean;
  canResume: boolean;
  canSwap: boolean;
  canVerify: boolean;
}

export interface CaseReportTaskEntry {
  origin: "planned" | "substitute";
  outcome: "confirmed" | "user_confirmed_only" | "unverified" | "skipped";
  protocolStep: string | null;
  taskId: string;
  taskName: string;
  taskRoleCategory: string;
  taskTier: number;
}

export interface CaseReportClosingTemplate {
  closingLine: string;
  heading: string;
  tone: "secured" | "partial" | "inconclusive";
}

export interface CaseReportArtifact {
  caseId: string;
  closingTemplate: CaseReportClosingTemplate;
  counts: {
    confirmed: number;
    skipped: number;
    unverified: number;
    user_confirmed_only: number;
  };
  finalVerdict: "secured" | "partial" | "inconclusive";
  generatedAt: string;
  incidentClassificationLabel: string;
  incidentClassificationSummary: string;
  sessionId: string;
  tasks: CaseReportTaskEntry[];
}

export interface SessionPlannedTaskEntry {
  taskId: string;
  taskName: string;
  taskRoleCategory: string;
  taskTier: number;
}

export interface SessionTaskHistoryEntry {
  at: string | null;
  outcome: string;
  protocolStep: string | null;
  reason: string | null;
  taskId: string;
  taskName: string | null;
}

export interface DemoBargeInState {
  matchedTranscript: string | null;
  status: "idle" | "armed" | "triggered" | "restated" | null;
  targetLine: string | null;
  triggerPhrase: string | null;
}

export interface DemoNearFailureState {
  failureType: string | null;
  status: "idle" | "failed_once" | "recovered" | null;
  taskId: string | null;
}

export interface SessionStateSnapshot {
  activeTaskIndex: number | null;
  allowedActions: SessionAllowedActions;
  blockReason: string | null;
  caseReport: CaseReportArtifact | null;
  classificationLabel: string | null;
  currentPathMode: string | null;
  currentStep: string | null;
  currentTaskContext: VerificationTaskContext | null;
  demoModeEnabled: boolean;
  demoBargeIn: DemoBargeInState | null;
  demoNearFailure: DemoNearFailureState | null;
  endedReason: string | null;
  finalVerdict: "secured" | "partial" | "inconclusive" | null;
  hasSnapshot: boolean;
  interruptionCount: number;
  lastVerifiedItem: string | null;
  plannedTasks: SessionPlannedTaskEntry[];
  recoveryAttemptCount: number | null;
  recoveryAttemptLimit: number | null;
  recoveryRerouteRequired: boolean;
  recoveryStep: string | null;
  state: string | null;
  swapCount: number;
  taskHistory: SessionTaskHistoryEntry[];
  turnStatus: string | null;
  verificationStatus: string | null;
  calibrationCapturedAt: string | null;
}

interface UseSessionStateOptions {
  connectionStatus: SessionConnectionStatus;
  subscribeToEnvelopes: (listener: SessionEnvelopeListener) => () => void;
}

const IDLE_ALLOWED_ACTIONS: SessionAllowedActions = {
  canEnd: false,
  canPause: false,
  canResume: false,
  canSwap: false,
  canVerify: false,
};

const IDLE_STATE: SessionStateSnapshot = {
  activeTaskIndex: null,
  allowedActions: IDLE_ALLOWED_ACTIONS,
  blockReason: null,
  caseReport: null,
  classificationLabel: null,
  currentPathMode: null,
  currentStep: null,
  currentTaskContext: null,
  demoModeEnabled: false,
  demoBargeIn: null,
  demoNearFailure: null,
  endedReason: null,
  finalVerdict: null,
  hasSnapshot: false,
  interruptionCount: 0,
  lastVerifiedItem: null,
  plannedTasks: [],
  recoveryAttemptCount: null,
  recoveryAttemptLimit: null,
  recoveryRerouteRequired: false,
  recoveryStep: null,
  state: null,
  swapCount: 0,
  taskHistory: [],
  turnStatus: null,
  verificationStatus: null,
  calibrationCapturedAt: null,
};

function getString(payload: Record<string, unknown>, key: string): string | null {
  const value = payload[key];
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : null;
}

function getInteger(payload: Record<string, unknown>, key: string): number | null {
  const value = payload[key];
  return typeof value === "number" && Number.isFinite(value) ? Math.trunc(value) : null;
}

function parseDemoBargeInState(payload: Record<string, unknown>): DemoBargeInState | null {
  const statusValue = getString(payload, "demoBargeInStatus");
  const status =
    statusValue === "idle" ||
    statusValue === "armed" ||
    statusValue === "triggered" ||
    statusValue === "restated"
      ? statusValue
      : null;
  const targetLine = getString(payload, "demoBargeInTargetLine");
  const triggerPhrase = getString(payload, "demoBargeInTriggerPhrase");
  const matchedTranscript = getString(payload, "demoBargeInMatchedTranscript");

  if (
    status === null &&
    targetLine === null &&
    triggerPhrase === null &&
    matchedTranscript === null
  ) {
    return null;
  }

  return {
    matchedTranscript,
    status,
    targetLine,
    triggerPhrase,
  };
}

function parseDemoNearFailureState(payload: Record<string, unknown>): DemoNearFailureState | null {
  const statusValue = getString(payload, "demoNearFailureStatus");
  const status =
    statusValue === "idle" ||
    statusValue === "failed_once" ||
    statusValue === "recovered"
      ? statusValue
      : null;
  const failureType = getString(payload, "demoNearFailureFailureType");
  const taskId = getString(payload, "demoNearFailureTaskId");

  if (status === null && failureType === null && taskId === null) {
    return null;
  }

  return {
    failureType,
    status,
    taskId,
  };
}

function parseTaskContext(value: unknown): VerificationTaskContext | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return null;
  }

  return value as VerificationTaskContext;
}

function parseAllowedActions(value: unknown): SessionAllowedActions {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return IDLE_ALLOWED_ACTIONS;
  }

  const record = value as Record<string, unknown>;
  return {
    canEnd: record.canEnd === true,
    canPause: record.canPause === true,
    canResume: record.canResume === true,
    canSwap: record.canSwap === true,
    canVerify: record.canVerify === true,
  };
}

function parseCaseReportTaskEntry(value: unknown): CaseReportTaskEntry | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return null;
  }

  const record = value as Record<string, unknown>;
  const taskId = typeof record.taskId === "string" ? record.taskId : null;
  const taskName = typeof record.taskName === "string" ? record.taskName : null;
  const taskRoleCategory =
    typeof record.taskRoleCategory === "string" ? record.taskRoleCategory : null;
  const taskTier =
    typeof record.taskTier === "number" && Number.isFinite(record.taskTier)
      ? Math.trunc(record.taskTier)
      : null;
  const outcome =
    record.outcome === "confirmed" ||
    record.outcome === "user_confirmed_only" ||
    record.outcome === "unverified" ||
    record.outcome === "skipped"
      ? record.outcome
      : null;
  const origin =
    record.origin === "planned" || record.origin === "substitute"
      ? record.origin
      : null;
  const protocolStep =
    typeof record.protocolStep === "string" && record.protocolStep.trim().length > 0
      ? record.protocolStep.trim()
      : null;

  if (
    taskId === null ||
    taskName === null ||
    taskRoleCategory === null ||
    taskTier === null ||
    outcome === null ||
    origin === null
  ) {
    return null;
  }

  return {
    origin,
    outcome,
    protocolStep,
    taskId,
    taskName,
    taskRoleCategory,
    taskTier,
  };
}

function parseCaseReportClosingTemplate(value: unknown): CaseReportClosingTemplate | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return null;
  }

  const record = value as Record<string, unknown>;
  const closingLine = typeof record.closingLine === "string" ? record.closingLine : null;
  const heading = typeof record.heading === "string" ? record.heading : null;
  const tone =
    record.tone === "secured" ||
    record.tone === "partial" ||
    record.tone === "inconclusive"
      ? record.tone
      : null;

  if (closingLine === null || heading === null || tone === null) {
    return null;
  }

  return { closingLine, heading, tone };
}

function parsePlannedTaskEntry(value: unknown): SessionPlannedTaskEntry | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return null;
  }

  const record = value as Record<string, unknown>;
  const taskId = typeof record.taskId === "string" ? record.taskId : null;
  const taskName = typeof record.taskName === "string" ? record.taskName : null;
  const taskRoleCategory =
    typeof record.taskRoleCategory === "string" ? record.taskRoleCategory : null;
  const taskTier =
    typeof record.taskTier === "number" && Number.isFinite(record.taskTier)
      ? Math.trunc(record.taskTier)
      : null;

  if (
    taskId === null ||
    taskName === null ||
    taskRoleCategory === null ||
    taskTier === null
  ) {
    return null;
  }

  return {
    taskId,
    taskName,
    taskRoleCategory,
    taskTier,
  };
}

function parseTaskHistoryEntry(value: unknown): SessionTaskHistoryEntry | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return null;
  }

  const record = value as Record<string, unknown>;
  const taskId = typeof record.taskId === "string" ? record.taskId : null;
  const outcome = typeof record.outcome === "string" ? record.outcome : null;

  if (taskId === null || outcome === null) {
    return null;
  }

  return {
    at: typeof record.at === "string" ? record.at : null,
    outcome,
    protocolStep:
      typeof record.protocolStep === "string" && record.protocolStep.trim().length > 0
        ? record.protocolStep.trim()
        : null,
    reason:
      typeof record.reason === "string" && record.reason.trim().length > 0
        ? record.reason.trim()
        : null,
    taskId,
    taskName:
      typeof record.taskName === "string" && record.taskName.trim().length > 0
        ? record.taskName.trim()
        : null,
  };
}

function shouldPreserveDisconnectedSnapshot(
  snapshot: SessionStateSnapshot,
): boolean {
  return (
    snapshot.caseReport !== null ||
    snapshot.state === "completed" ||
    snapshot.state === "case_report" ||
    snapshot.state === "ended"
  );
}

function parseCaseReport(value: unknown): CaseReportArtifact | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return null;
  }

  const record = value as Record<string, unknown>;
  const caseId = typeof record.caseId === "string" ? record.caseId : null;
  const sessionId = typeof record.sessionId === "string" ? record.sessionId : null;
  const generatedAt = typeof record.generatedAt === "string" ? record.generatedAt : null;
  const incidentClassificationLabel =
    typeof record.incidentClassificationLabel === "string"
      ? record.incidentClassificationLabel
      : null;
  const incidentClassificationSummary =
    typeof record.incidentClassificationSummary === "string"
      ? record.incidentClassificationSummary
      : null;
  const finalVerdict =
    record.finalVerdict === "secured" ||
    record.finalVerdict === "partial" ||
    record.finalVerdict === "inconclusive"
      ? record.finalVerdict
      : null;
  const closingTemplate = parseCaseReportClosingTemplate(record.closingTemplate);
  const rawTasks = Array.isArray(record.tasks) ? record.tasks : null;
  const rawCounts =
    typeof record.counts === "object" && record.counts !== null && !Array.isArray(record.counts)
      ? (record.counts as Record<string, unknown>)
      : null;

  if (
    caseId === null ||
    sessionId === null ||
    generatedAt === null ||
    incidentClassificationLabel === null ||
    incidentClassificationSummary === null ||
    finalVerdict === null ||
    closingTemplate === null ||
    rawTasks === null ||
    rawCounts === null
  ) {
    return null;
  }

  const tasks = rawTasks
    .map((item) => parseCaseReportTaskEntry(item))
    .filter((item): item is CaseReportTaskEntry => item !== null);

  return {
    caseId,
    closingTemplate,
    counts: {
      confirmed:
        typeof rawCounts.confirmed === "number" && Number.isFinite(rawCounts.confirmed)
          ? Math.trunc(rawCounts.confirmed)
          : 0,
      skipped:
        typeof rawCounts.skipped === "number" && Number.isFinite(rawCounts.skipped)
          ? Math.trunc(rawCounts.skipped)
          : 0,
      unverified:
        typeof rawCounts.unverified === "number" && Number.isFinite(rawCounts.unverified)
          ? Math.trunc(rawCounts.unverified)
          : 0,
      user_confirmed_only:
        typeof rawCounts.user_confirmed_only === "number" && Number.isFinite(rawCounts.user_confirmed_only)
          ? Math.trunc(rawCounts.user_confirmed_only)
          : 0,
    },
    finalVerdict,
    generatedAt,
    incidentClassificationLabel,
    incidentClassificationSummary,
    sessionId,
    tasks,
  };
}

export function useSessionState(
  options: UseSessionStateOptions,
): SessionStateSnapshot {
  const { connectionStatus, subscribeToEnvelopes } = options;
  const [state, setState] = useState<SessionStateSnapshot>(IDLE_STATE);

  useEffect(() => {
    if (connectionStatus === "disconnected" || connectionStatus === "error") {
      setState((currentState) =>
        shouldPreserveDisconnectedSnapshot(currentState) ? currentState : IDLE_STATE,
      );
    }
  }, [connectionStatus]);

  useEffect(() => {
    return subscribeToEnvelopes((envelope) => {
      if (envelope.type !== "session_state" && envelope.type !== "case_report") {
        return;
      }

      if (envelope.type === "case_report") {
        const caseReport = parseCaseReport(envelope.payload);
        if (caseReport === null) {
          return;
        }

        setState((currentState) => ({
          ...currentState,
          caseReport,
          finalVerdict: caseReport.finalVerdict,
        }));
        return;
      }

      const payload = envelope.payload;
      const caseReport = parseCaseReport(payload.caseReport);
      const finalVerdict =
        payload.finalVerdict === "secured" ||
        payload.finalVerdict === "partial" ||
        payload.finalVerdict === "inconclusive"
          ? payload.finalVerdict
          : caseReport?.finalVerdict ?? null;

      setState({
        activeTaskIndex: getInteger(payload, "activeTaskIndex"),
        allowedActions: parseAllowedActions(payload.allowedActions),
        blockReason: getString(payload, "blockReason"),
        caseReport,
        classificationLabel: getString(payload, "classificationLabel"),
        currentPathMode: getString(payload, "currentPathMode"),
        currentStep: getString(payload, "currentStep"),
        currentTaskContext: parseTaskContext(payload.currentTaskContext),
        demoModeEnabled: payload.demoModeEnabled === true,
        demoBargeIn: parseDemoBargeInState(payload),
        demoNearFailure: parseDemoNearFailureState(payload),
        endedReason: getString(payload, "endedReason"),
        finalVerdict,
        hasSnapshot: true,
        interruptionCount: getInteger(payload, "interruptionCount") ?? 0,
        lastVerifiedItem: getString(payload, "lastVerifiedItem"),
        plannedTasks: Array.isArray(payload.plannedTasks)
          ? payload.plannedTasks
              .map((item) => parsePlannedTaskEntry(item))
              .filter((item): item is SessionPlannedTaskEntry => item !== null)
          : [],
        recoveryAttemptCount: getInteger(payload, "recoveryAttemptCount"),
        recoveryAttemptLimit: getInteger(payload, "recoveryAttemptLimit"),
        recoveryRerouteRequired: payload.recoveryRerouteRequired === true,
        recoveryStep: getString(payload, "recoveryStep"),
        state: getString(payload, "state"),
        swapCount: getInteger(payload, "swapCount") ?? 0,
        taskHistory: Array.isArray(payload.taskHistory)
          ? payload.taskHistory
              .map((item) => parseTaskHistoryEntry(item))
              .filter((item): item is SessionTaskHistoryEntry => item !== null)
          : [],
        turnStatus: getString(payload, "turnStatus"),
        verificationStatus: getString(payload, "verificationStatus"),
        calibrationCapturedAt: getString(payload, "calibrationCapturedAt"),
      });
    });
  }, [subscribeToEnvelopes]);

  return state;
}
