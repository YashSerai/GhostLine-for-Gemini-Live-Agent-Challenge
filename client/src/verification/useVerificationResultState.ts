import { useEffect, useState } from "react";

import type {
  SessionConnectionStatus,
  SessionEnvelopeListener,
} from "../session/sessionTypes";
import type { VerificationTaskContext } from "./useReadyToVerifyFlow";

export type VerificationResultStatus =
  | "confirmed"
  | "unconfirmed"
  | "user_confirmed_only";
export type VerificationConfidenceBand = "low" | "medium" | "high";
export type VerificationProgressionDirective = "advance" | "recover" | "wait";
export type VerificationStatusTone = "success" | "live" | "warning" | "placeholder";
export type VerificationCardTone = "ready" | "pending" | "warning";

export interface VerificationSubstituteTaskSuggestion {
  storyFunction: string;
  substitutionGroup: string;
  taskId: string;
  taskName: string;
  tier: number;
}

export interface VerificationResultState {
  attemptId: string | null;
  awaitingDecision: boolean;
  blockReason: string | null;
  cardBody: string | null;
  cardTitle: string | null;
  cardTone: VerificationCardTone | null;
  confidenceBand: VerificationConfidenceBand | null;
  currentPathMode: string | null;
  hasResolvedResult: boolean;
  isMock: boolean;
  lastVerifiedItem: string | null;
  notes: string | null;
  operatorLine: string | null;
  progressionDirective: VerificationProgressionDirective;
  reason: string | null;
  recoveryAttemptCount: number | null;
  recoveryAttemptLimit: number | null;
  recoveryStep: string | null;
  recoveryStepKey: string | null;
  recoveryStepLabel: string | null;
  retryAllowed: boolean | null;
  status: VerificationResultStatus | null;
  statusLabel: string;
  statusTone: VerificationStatusTone;
  substituteTaskSuggestion: VerificationSubstituteTaskSuggestion | null;
  suggestedPathMode: string | null;
  taskContext: VerificationTaskContext | null;
}

interface UseVerificationResultStateOptions {
  connectionStatus: SessionConnectionStatus;
  subscribeToEnvelopes: (listener: SessionEnvelopeListener) => () => void;
}

interface VerificationStateEnvelopePayload {
  attemptId: string;
  status: "pending" | "captured" | "cancelled";
  taskContext: VerificationTaskContext | null;
}

interface VerificationResultEnvelopePayload {
  attemptId: string;
  blockReason: string | null;
  confidenceBand: VerificationConfidenceBand | null;
  currentPathMode: string | null;
  isMock: boolean;
  lastVerifiedItem: string | null;
  notes: string | null;
  reason: string | null;
  recoveryAttemptCount: number | null;
  recoveryAttemptLimit: number | null;
  recoveryOperatorLine: string | null;
  recoveryStep: string | null;
  recoveryStepKey: string | null;
  recoveryStepLabel: string | null;
  retryAllowed: boolean | null;
  status: VerificationResultStatus;
  substituteTaskSuggestion: VerificationSubstituteTaskSuggestion | null;
  suggestedPathMode: string | null;
  taskContext: VerificationTaskContext | null;
}

const IDLE_RESULT_STATE: VerificationResultState = {
  attemptId: null,
  awaitingDecision: false,
  blockReason: null,
  cardBody: null,
  cardTitle: null,
  cardTone: null,
  confidenceBand: null,
  currentPathMode: null,
  hasResolvedResult: false,
  isMock: false,
  lastVerifiedItem: null,
  notes: null,
  operatorLine: null,
  progressionDirective: "wait",
  reason: null,
  recoveryAttemptCount: null,
  recoveryAttemptLimit: null,
  recoveryStep: null,
  recoveryStepKey: null,
  recoveryStepLabel: null,
  retryAllowed: null,
  status: null,
  statusLabel: "Pending",
  statusTone: "placeholder",
  substituteTaskSuggestion: null,
  suggestedPathMode: null,
  taskContext: null,
};

function getPayloadString(
  payload: Record<string, unknown>,
  key: string,
): string | null {
  const value = payload[key];
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : null;
}

function getPayloadInteger(
  payload: Record<string, unknown>,
  key: string,
): number | null {
  const value = payload[key];
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return null;
  }

  return Math.trunc(value);
}

function getPayloadBoolean(
  payload: Record<string, unknown>,
  key: string,
): boolean | null {
  const value = payload[key];
  return typeof value === "boolean" ? value : null;
}

function parseTaskContext(
  value: unknown,
): VerificationTaskContext | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return null;
  }

  return value as VerificationTaskContext;
}

function getTaskContextId(
  taskContext: VerificationTaskContext | null,
): string | null {
  const taskId = taskContext?.taskId;
  return typeof taskId === "string" && taskId.trim().length > 0
    ? taskId.trim()
    : null;
}

function parseSubstituteTaskSuggestion(
  value: unknown,
): VerificationSubstituteTaskSuggestion | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return null;
  }

  const record = value as Record<string, unknown>;
  const taskId =
    typeof record.task_id === "string" && record.task_id.trim().length > 0
      ? record.task_id.trim()
      : null;
  const taskName =
    typeof record.task_name === "string" && record.task_name.trim().length > 0
      ? record.task_name.trim()
      : null;
  const substitutionGroup =
    typeof record.substitution_group === "string" &&
    record.substitution_group.trim().length > 0
      ? record.substitution_group.trim()
      : null;
  const storyFunction =
    typeof record.story_function === "string" &&
    record.story_function.trim().length > 0
      ? record.story_function.trim()
      : null;
  const tier =
    typeof record.tier === "number" && Number.isFinite(record.tier)
      ? Math.trunc(record.tier)
      : null;

  if (
    taskId === null ||
    taskName === null ||
    substitutionGroup === null ||
    storyFunction === null ||
    tier === null
  ) {
    return null;
  }

  return {
    storyFunction,
    substitutionGroup,
    taskId,
    taskName,
    tier,
  };
}

function parseVerificationStatePayload(
  payload: Record<string, unknown>,
): VerificationStateEnvelopePayload | null {
  const attemptId = getPayloadString(payload, "attemptId");
  const status = payload.status;
  if (
    attemptId === null ||
    (status !== "pending" && status !== "captured" && status !== "cancelled")
  ) {
    return null;
  }

  return {
    attemptId,
    status,
    taskContext: parseTaskContext(payload.taskContext),
  };
}

function parseVerificationResultPayload(
  payload: Record<string, unknown>,
): VerificationResultEnvelopePayload | null {
  const attemptId = getPayloadString(payload, "attemptId");
  const status = payload.status;
  if (
    attemptId === null ||
    (status !== "confirmed" &&
      status !== "unconfirmed" &&
      status !== "user_confirmed_only")
  ) {
    return null;
  }

  const confidenceBand = payload.confidenceBand;
  const normalizedConfidenceBand =
    confidenceBand === "low" || confidenceBand === "medium" || confidenceBand === "high"
      ? confidenceBand
      : null;

  return {
    attemptId,
    blockReason: getPayloadString(payload, "blockReason"),
    confidenceBand: normalizedConfidenceBand,
    currentPathMode: getPayloadString(payload, "currentPathMode"),
    isMock: payload.isMock === true,
    lastVerifiedItem: getPayloadString(payload, "lastVerifiedItem"),
    notes: getPayloadString(payload, "notes"),
    reason: getPayloadString(payload, "reason"),
    recoveryAttemptCount: getPayloadInteger(payload, "recoveryAttemptCount"),
    recoveryAttemptLimit: getPayloadInteger(payload, "recoveryAttemptLimit"),
    recoveryOperatorLine: getPayloadString(payload, "recoveryOperatorLine"),
    recoveryStep: getPayloadString(payload, "recoveryStep"),
    recoveryStepKey: getPayloadString(payload, "recoveryStepKey"),
    recoveryStepLabel: getPayloadString(payload, "recoveryStepLabel"),
    retryAllowed: getPayloadBoolean(payload, "retryAllowed"),
    status,
    substituteTaskSuggestion: parseSubstituteTaskSuggestion(payload.substituteTaskSuggestion),
    suggestedPathMode: getPayloadString(payload, "suggestedPathMode"),
    taskContext: parseTaskContext(payload.taskContext),
  };
}

function buildRecoveryStep(
  status: VerificationResultStatus,
  blockReason: string | null,
  reason: string | null,
  backendRecoveryStep: string | null,
): string | null {
  if (backendRecoveryStep !== null) {
    return backendRecoveryStep;
  }

  if (status === "confirmed") {
    return "Ready for the next operator step once the session state advances.";
  }

  if (status === "user_confirmed_only") {
    return "Hold for operator review or a follow-up verification before treating this as fully confirmed.";
  }

  const basis = `${blockReason ?? ""} ${reason ?? ""}`.toLowerCase();

  if (basis.includes("dark") || basis.includes("dim") || basis.includes("light")) {
    return "Increase illumination, then run Ready to Verify again.";
  }

  if (basis.includes("unstable") || basis.includes("steady") || basis.includes("motion")) {
    return "Stabilize the phone and hold the frame steady before retrying.";
  }

  if (basis.includes("blurry") || basis.includes("blur")) {
    return "Move closer, refocus, and retry the verification capture.";
  }

  if (basis.includes("threshold") || basis.includes("boundary") || basis.includes("door")) {
    return "Reframe the threshold or room boundary clearly, then retry.";
  }

  if (basis.includes("transcript") || basis.includes("speech") || basis.includes("phrase")) {
    return "Repeat the spoken step clearly so the live transcript can capture it.";
  }

  return "Adjust the task setup or framing, then retry Ready to Verify.";
}

function buildProgressionDirective(
  status: VerificationResultStatus,
): VerificationProgressionDirective {
  if (status === "confirmed") {
    return "advance";
  }

  if (status === "unconfirmed") {
    return "recover";
  }

  return "wait";
}

function buildStatusLabel(
  status: VerificationResultStatus,
): string {
  switch (status) {
    case "confirmed":
      return "Visually Confirmed";
    case "user_confirmed_only":
      return "User-Confirmed Only";
    case "unconfirmed":
      return "Unconfirmed";
    default:
      return "Pending";
  }
}

function buildStatusTone(
  status: VerificationResultStatus,
): VerificationStatusTone {
  switch (status) {
    case "confirmed":
      return "success";
    case "user_confirmed_only":
      return "live";
    case "unconfirmed":
      return "warning";
    default:
      return "placeholder";
  }
}

function buildCardTone(
  status: VerificationResultStatus,
): VerificationCardTone {
  switch (status) {
    case "confirmed":
      return "ready";
    case "user_confirmed_only":
      return "pending";
    case "unconfirmed":
      return "warning";
    default:
      return "pending";
  }
}

function buildLastVerifiedItem(
  payload: VerificationResultEnvelopePayload,
): string | null {
  if (payload.lastVerifiedItem) {
    return payload.lastVerifiedItem;
  }

  if (
    payload.status !== "unconfirmed" &&
    payload.taskContext?.taskName &&
    payload.taskContext.taskName.trim().length > 0
  ) {
    return payload.taskContext.taskName.trim();
  }

  return null;
}

function buildOperatorLine(
  status: VerificationResultStatus,
  reason: string | null,
  recoveryStep: string | null,
  recoveryOperatorLine: string | null,
): string {
  if (status === "confirmed") {
    return reason
      ? `Verification confirmed. ${reason}`
      : "Verification confirmed. Hold for the next containment instruction.";
  }

  if (status === "user_confirmed_only") {
    return reason
      ? `I can log that as caller-confirmed only, not visually confirmed. ${reason}`
      : "I can log that as caller-confirmed only, not visually confirmed.";
  }

  if (recoveryOperatorLine) {
    return recoveryOperatorLine;
  }

  if (reason && recoveryStep) {
    return `I can't confirm that yet. ${reason} ${recoveryStep}`;
  }

  if (reason) {
    return `I can't confirm that yet. ${reason}`;
  }

  return "I can't confirm that yet. Adjust the setup and retry the verification capture.";
}

function buildCardTitle(
  status: VerificationResultStatus,
  recoveryStepLabel: string | null,
): string {
  switch (status) {
    case "confirmed":
      return "Verification Confirmed";
    case "user_confirmed_only":
      return "Verification Logged as User-Confirmed Only";
    case "unconfirmed":
      return recoveryStepLabel ?? "Verification Unconfirmed";
    default:
      return "Verification Pending";
  }
}

function buildCardBody(
  payload: VerificationResultEnvelopePayload,
  recoveryStep: string | null,
): string {
  if (payload.status === "confirmed") {
    return payload.reason ?? "The verification capture produced a full visual confirmation.";
  }

  if (payload.status === "user_confirmed_only") {
    return payload.reason
      ? `${payload.reason} This remains visibly distinct from a full visual confirmation.`
      : "The step was logged as caller-confirmed only. This remains visibly distinct from a full visual confirmation.";
  }

  const baseReason =
    payload.reason ??
    "The verification capture did not provide enough evidence to confirm the step.";

  if (payload.retryAllowed === false) {
    if (payload.suggestedPathMode) {
      return `${baseReason} This verification path is exhausted. Reroute to the ${payload.suggestedPathMode.replace(/_/g, " ")} path instead of retrying the same hold.`;
    }

    if (payload.substituteTaskSuggestion) {
      return `${baseReason} This verification path is exhausted. Switch to ${payload.substituteTaskSuggestion.taskName} as the safer substitute step.`;
    }

    return `${baseReason} This verification path is exhausted. Do not keep retrying the same blocked setup.`;
  }

  if (recoveryStep) {
    return `${baseReason} Recovery: ${recoveryStep}`;
  }

  return baseReason;
}

export function useVerificationResultState(
  options: UseVerificationResultStateOptions,
): VerificationResultState {
  const { connectionStatus, subscribeToEnvelopes } = options;
  const [state, setState] = useState<VerificationResultState>(IDLE_RESULT_STATE);

  useEffect(() => {
    if (connectionStatus === "disconnected" || connectionStatus === "error") {
      setState(IDLE_RESULT_STATE);
    }
  }, [connectionStatus]);

  useEffect(() => {
    return subscribeToEnvelopes((envelope) => {
      if (envelope.type === "session_state") {
        const nextTaskContext = parseTaskContext(envelope.payload.currentTaskContext);
        const nextTaskId = getTaskContextId(nextTaskContext);

        setState((currentState) => {
          const currentTaskId = getTaskContextId(currentState.taskContext);
          if (nextTaskId === null || nextTaskId === currentTaskId) {
            return currentState;
          }

          return IDLE_RESULT_STATE;
        });
        return;
      }

      if (envelope.type === "verification_state") {
        const payload = parseVerificationStatePayload(envelope.payload);
        if (payload === null) {
          return;
        }

        if (payload.status === "cancelled") {
          setState(IDLE_RESULT_STATE);
          return;
        }

        setState({
          ...IDLE_RESULT_STATE,
          attemptId: payload.attemptId,
          awaitingDecision: payload.status === "captured",
          taskContext: payload.taskContext,
        });
        return;
      }

      if (envelope.type !== "verification_result") {
        return;
      }

      const payload = parseVerificationResultPayload(envelope.payload);
      if (payload === null) {
        return;
      }

      const recoveryStep = buildRecoveryStep(
        payload.status,
        payload.blockReason,
        payload.reason,
        payload.recoveryStep,
      );

      setState({
        attemptId: payload.attemptId,
        awaitingDecision: false,
        blockReason: payload.blockReason,
        cardBody: buildCardBody(payload, recoveryStep),
        cardTitle: buildCardTitle(payload.status, payload.recoveryStepLabel),
        cardTone: buildCardTone(payload.status),
        confidenceBand: payload.confidenceBand,
        currentPathMode: payload.currentPathMode,
        hasResolvedResult: true,
        isMock: payload.isMock,
        lastVerifiedItem: buildLastVerifiedItem(payload),
        notes: payload.notes,
        operatorLine: buildOperatorLine(
          payload.status,
          payload.reason,
          recoveryStep,
          payload.recoveryOperatorLine,
        ),
        progressionDirective: buildProgressionDirective(payload.status),
        reason: payload.reason,
        recoveryAttemptCount: payload.recoveryAttemptCount,
        recoveryAttemptLimit: payload.recoveryAttemptLimit,
        recoveryStep,
        recoveryStepKey: payload.recoveryStepKey,
        recoveryStepLabel: payload.recoveryStepLabel,
        retryAllowed: payload.retryAllowed,
        status: payload.status,
        statusLabel: buildStatusLabel(payload.status),
        statusTone: buildStatusTone(payload.status),
        substituteTaskSuggestion: payload.substituteTaskSuggestion,
        suggestedPathMode: payload.suggestedPathMode,
        taskContext: payload.taskContext,
      });
    });
  }, [subscribeToEnvelopes]);

  return state;
}



