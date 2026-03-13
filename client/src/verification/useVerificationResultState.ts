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
  recoveryStep: string | null;
  status: VerificationResultStatus | null;
  statusLabel: string;
  statusTone: VerificationStatusTone;
  taskContext: VerificationTaskContext | null;
}

interface UseVerificationResultStateOptions {
  connectionStatus: SessionConnectionStatus;
  subscribeToEnvelopes: (listener: SessionEnvelopeListener) => () => void;
}

interface VerificationStateEnvelopePayload {
  attemptId: string;
  status: "pending" | "captured";
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
  status: VerificationResultStatus;
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
  recoveryStep: null,
  status: null,
  statusLabel: "Pending",
  statusTone: "placeholder",
  taskContext: null,
};

function getPayloadString(
  payload: Record<string, unknown>,
  key: string,
): string | null {
  const value = payload[key];
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : null;
}

function parseTaskContext(
  value: unknown,
): VerificationTaskContext | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return null;
  }

  return value as VerificationTaskContext;
}

function parseVerificationStatePayload(
  payload: Record<string, unknown>,
): VerificationStateEnvelopePayload | null {
  const attemptId = getPayloadString(payload, "attemptId");
  const status = payload.status;
  if (
    attemptId === null ||
    (status !== "pending" && status !== "captured")
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
    status,
    taskContext: parseTaskContext(payload.taskContext),
  };
}

function buildRecoveryStep(
  status: VerificationResultStatus,
  blockReason: string | null,
  reason: string | null,
): string | null {
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
    return "Move closer, refocus, and retry the verification window.";
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

  if (reason && recoveryStep) {
    return `I can't confirm that yet. ${reason} ${recoveryStep}`;
  }

  if (reason) {
    return `I can't confirm that yet. ${reason}`;
  }

  return "I can't confirm that yet. Adjust the setup and retry the verification window.";
}

function buildCardTitle(status: VerificationResultStatus): string {
  switch (status) {
    case "confirmed":
      return "Verification Confirmed";
    case "user_confirmed_only":
      return "Verification Logged as User-Confirmed Only";
    case "unconfirmed":
      return "Verification Unconfirmed";
    default:
      return "Verification Pending";
  }
}

function buildCardBody(
  status: VerificationResultStatus,
  reason: string | null,
  recoveryStep: string | null,
): string {
  if (status === "confirmed") {
    return reason ?? "The verification window produced a full visual confirmation.";
  }

  if (status === "user_confirmed_only") {
    return reason
      ? `${reason} This remains visibly distinct from a full visual confirmation.`
      : "The step was logged as caller-confirmed only. This remains visibly distinct from a full visual confirmation.";
  }

  if (reason && recoveryStep) {
    return `${reason} Recovery: ${recoveryStep}`;
  }

  if (reason) {
    return reason;
  }

  return "The verification window did not provide enough evidence to confirm the step.";
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
      if (envelope.type === "verification_state") {
        const payload = parseVerificationStatePayload(envelope.payload);
        if (payload === null) {
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
      );

      setState({
        attemptId: payload.attemptId,
        awaitingDecision: false,
        blockReason: payload.blockReason,
        cardBody: buildCardBody(payload.status, payload.reason, recoveryStep),
        cardTitle: buildCardTitle(payload.status),
        cardTone: buildCardTone(payload.status),
        confidenceBand: payload.confidenceBand,
        currentPathMode: payload.currentPathMode,
        hasResolvedResult: true,
        isMock: payload.isMock,
        lastVerifiedItem: buildLastVerifiedItem(payload),
        notes: payload.notes,
        operatorLine: buildOperatorLine(payload.status, payload.reason, recoveryStep),
        progressionDirective: buildProgressionDirective(payload.status),
        reason: payload.reason,
        recoveryStep,
        status: payload.status,
        statusLabel: buildStatusLabel(payload.status),
        statusTone: buildStatusTone(payload.status),
        taskContext: payload.taskContext,
      });
    });
  }, [subscribeToEnvelopes]);

  return state;
}
