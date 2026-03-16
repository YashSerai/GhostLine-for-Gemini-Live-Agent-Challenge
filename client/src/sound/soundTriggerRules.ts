import type { SessionConnectionStatus } from "../session/sessionTypes";
import type { VerificationResultStatus } from "../verification/useVerificationResultState";
import type { SoundSemanticEvent } from "./soundManifest";

export type AutomatedSoundTrigger =
  | "call_connected"
  | "camera_granted"
  | "task_assigned"
  | "verification_success"
  | "recovery"
  | "final_verdict"
  | "paranormal_shriek"
  | "door_creak";

export type FinalContainmentVerdict = "secured" | "partial" | "inconclusive";

export interface SoundTriggerSnapshot {
  cameraReady: boolean;
  connectionStatus: SessionConnectionStatus;
  finalVerdict: FinalContainmentVerdict | null;
  taskAssignmentKey: string | null;
  verificationAttemptId: string | null;
  verificationStatus: VerificationResultStatus | null;
}

export interface SoundTriggerDecision {
  cue: SoundSemanticEvent;
  delayMs: number;
  priority: number;
  trigger: AutomatedSoundTrigger;
}

export interface SoundTriggerOverrides {
  delayMsByTrigger?: Partial<Record<AutomatedSoundTrigger, number>>;
  disabledTriggers?: Partial<Record<AutomatedSoundTrigger, boolean>>;
}

interface TriggerRuleDefinition {
  cue: SoundSemanticEvent;
  defaultDelayMs: number;
  priority: number;
}

const TRIGGER_RULES: Record<AutomatedSoundTrigger, TriggerRuleDefinition> = {
  call_connected: {
    cue: "ambient_bed",
    defaultDelayMs: 0,
    priority: 0,
  },
  camera_granted: {
    cue: "verification_success",
    defaultDelayMs: 140,
    priority: 1,
  },
  task_assigned: {
    cue: "light_tension",
    defaultDelayMs: 180,
    priority: 2,
  },
  verification_success: {
    cue: "verification_success",
    defaultDelayMs: 120,
    priority: 3,
  },
  recovery: {
    cue: "warning_escalation",
    defaultDelayMs: 120,
    priority: 4,
  },
  final_verdict: {
    cue: "containment_result",
    defaultDelayMs: 240,
    priority: 5,
  },
  paranormal_shriek: {
    cue: "spectral_shriek",
    defaultDelayMs: 420,
    priority: 6,
  },
  door_creak: {
    cue: "door_creak",
    defaultDelayMs: 200,
    priority: 7,
  },
} as const;

export function shouldStartAmbientBed(
  previous: SoundTriggerSnapshot | null,
  next: SoundTriggerSnapshot,
): boolean {
  return !isConnected(previous?.connectionStatus ?? null) && isConnected(next.connectionStatus);
}

export function shouldStopAmbientBed(
  previous: SoundTriggerSnapshot | null,
  next: SoundTriggerSnapshot,
): boolean {
  return isConnected(previous?.connectionStatus ?? null) && !isConnected(next.connectionStatus);
}

export function resolveAutomatedSoundTrigger(
  previous: SoundTriggerSnapshot | null,
  next: SoundTriggerSnapshot,
  overrides: SoundTriggerOverrides | undefined,
): SoundTriggerDecision | null {
  const orderedTriggers: AutomatedSoundTrigger[] = [
    "final_verdict",
    "recovery",
    "paranormal_shriek",
    "verification_success",
    "task_assigned",
    "door_creak",
  ];

  for (const trigger of orderedTriggers) {
    if (overrides?.disabledTriggers?.[trigger] === true) {
      continue;
    }

    if (!didTriggerOccur(trigger, previous, next)) {
      continue;
    }

    const rule = TRIGGER_RULES[trigger];
    return {
      cue: rule.cue,
      delayMs: overrides?.delayMsByTrigger?.[trigger] ?? rule.defaultDelayMs,
      priority: rule.priority,
      trigger,
    };
  }

  return null;
}

function didTriggerOccur(
  trigger: AutomatedSoundTrigger,
  previous: SoundTriggerSnapshot | null,
  next: SoundTriggerSnapshot,
): boolean {
  switch (trigger) {
    case "camera_granted":
      return previous?.cameraReady !== true && next.cameraReady;
    case "task_assigned":
      return didTaskAssignmentChange(previous, next);
    case "verification_success":
      return (
        next.verificationStatus === "confirmed" &&
        next.verificationAttemptId !== null &&
        (previous?.verificationAttemptId !== next.verificationAttemptId ||
          previous?.verificationStatus !== "confirmed")
      );
    case "recovery":
      return (
        next.verificationStatus === "unconfirmed" &&
        next.verificationAttemptId !== null &&
        (previous?.verificationAttemptId !== next.verificationAttemptId ||
          previous?.verificationStatus !== "unconfirmed")
      );
    case "final_verdict":
      return next.finalVerdict !== null && next.finalVerdict !== previous?.finalVerdict;
    case "paranormal_shriek":
      return (
        didTaskAssignmentChangeTo(previous, next, "T14") ||
        (
          next.verificationStatus === "unconfirmed" &&
          next.verificationAttemptId !== null &&
          (previous?.verificationAttemptId !== next.verificationAttemptId ||
            previous?.verificationStatus !== "unconfirmed")
        )
      );
    case "door_creak":
      return (
        typeof next.taskAssignmentKey === "string" &&
        next.taskAssignmentKey.length > 0 &&
        (previous == null || previous.taskAssignmentKey == null)
      );
    default:
      return false;
  }
}

function didTaskAssignmentChange(
  previous: SoundTriggerSnapshot | null,
  next: SoundTriggerSnapshot,
): boolean {
  return (
    typeof next.taskAssignmentKey === "string" &&
    next.taskAssignmentKey.length > 0 &&
    next.taskAssignmentKey !== previous?.taskAssignmentKey
  );
}

function didTaskAssignmentChangeTo(
  previous: SoundTriggerSnapshot | null,
  next: SoundTriggerSnapshot,
  taskId: string,
): boolean {
  return next.taskAssignmentKey === taskId && next.taskAssignmentKey !== previous?.taskAssignmentKey;
}

function isConnected(status: SessionConnectionStatus | null): boolean {
  return status === "connected";
}
