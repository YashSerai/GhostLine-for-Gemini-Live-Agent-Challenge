import type { CapturedFrame } from "../media/frameCapture";
import type { SessionConnectionStatus } from "../session/sessionTypes";

export type GroundingHudTone =
  | "default"
  | "live"
  | "warning"
  | "success"
  | "placeholder";

export interface GroundingHudValueOverride {
  tone?: GroundingHudTone;
  value: string;
}

export interface GroundingHudField {
  label: string;
  tone: GroundingHudTone;
  value: string;
}

export interface GroundingHudSection {
  fields: readonly GroundingHudField[];
  title: string;
}

export interface GroundingHudSummaryChip {
  label: string;
  tone: GroundingHudTone;
  value: string;
}

export interface GroundingHudSnapshot {
  sections: readonly GroundingHudSection[];
  summary: readonly GroundingHudSummaryChip[];
}

type GroundingHudOverrideValue =
  | string
  | number
  | null
  | undefined
  | GroundingHudValueOverride;

export interface GroundingHudOverrides {
  activeTaskId?: string | null;
  activeTaskName?: string | null;
  blockReason?: GroundingHudOverrideValue;
  classificationLabel?: GroundingHudOverrideValue;
  lastVerifiedItem?: GroundingHudOverrideValue;
  pathMode?: GroundingHudOverrideValue;
  protocolStep?: GroundingHudOverrideValue;
  recoveryStep?: GroundingHudOverrideValue;
  swapCount?: number | null;
  taskRoleCategory?: GroundingHudOverrideValue;
  taskTier?: number | string | GroundingHudValueOverride | null;
  turnStatus?: GroundingHudOverrideValue;
  verificationStatus?: GroundingHudOverrideValue;
}

export interface BuildGroundingHudSnapshotOptions {
  activeIssue: string | null;
  cameraPermission: string;
  cameraReady: boolean;
  captureFrameCount: number;
  connectionStatus: SessionConnectionStatus;
  isMicStreaming: boolean;
  isOperatorSpeaking: boolean;
  lastCapturedFrame: Pick<CapturedFrame, "captureType"> | null;
  microphonePermission: string;
  overrides?: GroundingHudOverrides;
  permissionStage: string;
  permissionStageLabel: string;
}

interface GroundingHudValue {
  tone: GroundingHudTone;
  value: string;
}

function createValue(value: string, tone: GroundingHudTone): GroundingHudValue {
  return { tone, value };
}

function createField(label: string, presentation: GroundingHudValue): GroundingHudField {
  return {
    label,
    tone: presentation.tone,
    value: presentation.value,
  };
}

function isValueOverride(
  value: GroundingHudOverrideValue,
): value is GroundingHudValueOverride {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    typeof value.value === "string"
  );
}

function getOverrideValue(
  value: GroundingHudOverrideValue,
  fallbackTone: GroundingHudTone,
): GroundingHudValue | null {
  if (typeof value === "number") {
    return createValue(String(value), fallbackTone);
  }

  if (typeof value === "string" && value.trim().length > 0) {
    return createValue(value, fallbackTone);
  }

  if (isValueOverride(value) && value.value.trim().length > 0) {
    return createValue(value.value, value.tone ?? fallbackTone);
  }

  return null;
}

function getPlaceholderValue(
  value: GroundingHudOverrideValue,
  fallback: string,
): GroundingHudValue {
  return getOverrideValue(value, "default") ?? createValue(fallback, "placeholder");
}

function getProtocolStep(
  options: BuildGroundingHudSnapshotOptions,
): GroundingHudValue {
  const override = getOverrideValue(options.overrides?.protocolStep, "default");
  if (override !== null) {
    return override;
  }

  if (options.connectionStatus === "reconnecting") {
    return createValue("Line recovery", "warning");
  }

  if (options.connectionStatus === "error") {
    return createValue("Transport interrupted", "warning");
  }

  if (options.connectionStatus !== "connected") {
    return createValue("Call standby", "placeholder");
  }

  switch (options.permissionStage) {
    case "request_camera":
      return createValue("Room feed authorization", "warning");
    case "camera_requesting":
      return createValue("Awaiting camera approval", "warning");
    case "camera_denied":
      return createValue("Camera authorization blocked", "warning");
    case "request_microphone":
      return createValue("Audio bridge authorization", "warning");
    case "microphone_requesting":
      return createValue("Awaiting microphone approval", "warning");
    case "microphone_denied":
      return createValue("Microphone authorization blocked", "warning");
    case "permissions_ready":
      if (options.lastCapturedFrame?.captureType === "ready_to_verify") {
        return createValue("Ready to Verify hold", "success");
      }

      if (options.lastCapturedFrame?.captureType === "calibration") {
        return createValue("Calibration sample staged", "live");
      }

      if (options.lastCapturedFrame?.captureType === "manual_test") {
        return createValue("Manual room sample staged", "live");
      }

      if (!options.isMicStreaming) {
        return createValue("Audio bridge armed", "success");
      }

      if (options.captureFrameCount > 0) {
        return createValue("Live monitoring with staged room sample", "live");
      }

      return createValue("Live monitoring", "live");
    default:
      return createValue(options.permissionStageLabel, "default");
  }
}

function getTurnStatus(
  options: BuildGroundingHudSnapshotOptions,
): GroundingHudValue {
  const override = getOverrideValue(options.overrides?.turnStatus, "default");
  if (override !== null) {
    return override;
  }

  if (
    options.connectionStatus === "reconnecting" ||
    options.connectionStatus === "error"
  ) {
    return createValue("Interrupted", "warning");
  }

  if (options.isOperatorSpeaking) {
    return createValue("Speaking", "live");
  }

  if (options.isMicStreaming) {
    return createValue("Listening", "live");
  }

  if (options.connectionStatus === "connected") {
    return createValue("Awaiting live audio", "placeholder");
  }

  return createValue("Standing by", "placeholder");
}

function getVerificationStatus(
  options: BuildGroundingHudSnapshotOptions,
): GroundingHudValue {
  const override = getOverrideValue(options.overrides?.verificationStatus, "default");
  if (override !== null) {
    return override;
  }

  if (options.lastCapturedFrame?.captureType === "ready_to_verify") {
    return createValue("Pending ready check", "success");
  }

  if (options.captureFrameCount > 0) {
    return createValue("Sampling staged", "live");
  }

  if (!options.cameraReady) {
    return createValue("Awaiting room feed", "placeholder");
  }

  if (!options.isMicStreaming) {
    return createValue("Awaiting audio bridge", "placeholder");
  }

  return createValue("Pending", "placeholder");
}

function getBlockReason(
  options: BuildGroundingHudSnapshotOptions,
): GroundingHudValue {
  const override = getOverrideValue(options.overrides?.blockReason, "warning");
  if (override !== null) {
    return override;
  }

  if (options.connectionStatus === "reconnecting") {
    return createValue("Transport reconnect in progress", "warning");
  }

  if (options.connectionStatus === "error") {
    return createValue("Transport error recorded", "warning");
  }

  if (options.cameraPermission === "denied") {
    return createValue("Camera access denied", "warning");
  }

  if (options.microphonePermission === "denied") {
    return createValue("Microphone access denied", "warning");
  }

  if (options.activeIssue) {
    return createValue(options.activeIssue, "warning");
  }

  return createValue("None active", "success");
}

function getRecoveryStep(
  options: BuildGroundingHudSnapshotOptions,
): GroundingHudValue {
  const override = getOverrideValue(options.overrides?.recoveryStep, "default");
  if (override !== null) {
    return override;
  }

  if (options.connectionStatus === "reconnecting") {
    return createValue("Hold line and re-establish transport", "warning");
  }

  if (options.connectionStatus === "error") {
    return createValue("Reconnect the hotline session", "warning");
  }

  if (options.cameraPermission === "denied") {
    return createValue("Retry camera access", "warning");
  }

  if (options.microphonePermission === "denied") {
    return createValue("Retry microphone access", "warning");
  }

  if (options.activeIssue) {
    return createValue("Stabilize the live media bridge", "warning");
  }

  return createValue("None active", "success");
}

export function buildGroundingHudSnapshot(
  options: BuildGroundingHudSnapshotOptions,
): GroundingHudSnapshot {
  const protocolStep = getProtocolStep(options);
  const turnStatus = getTurnStatus(options);
  const verificationStatus = getVerificationStatus(options);
  const blockReason = getBlockReason(options);
  const recoveryStep = getRecoveryStep(options);
  const activeTaskId = getPlaceholderValue(
    options.overrides?.activeTaskId,
    "Pending assignment",
  );
  const activeTaskName = getPlaceholderValue(
    options.overrides?.activeTaskName,
    "No active containment task yet",
  );
  const taskRoleCategory = getPlaceholderValue(
    options.overrides?.taskRoleCategory,
    "Pending task routing",
  );
  const taskTier = getPlaceholderValue(
    options.overrides?.taskTier,
    "Pending",
  );
  const pathMode = getPlaceholderValue(
    options.overrides?.pathMode,
    "Pending route",
  );
  const swapCount =
    typeof options.overrides?.swapCount === "number"
      ? createValue(String(options.overrides.swapCount), "default")
      : createValue("0", "default");
  const lastVerifiedItem = getPlaceholderValue(
    options.overrides?.lastVerifiedItem,
    "None recorded",
  );
  const classificationLabel = getPlaceholderValue(
    options.overrides?.classificationLabel,
    "Not assigned",
  );

  const protocolFields = [
    createField("Protocol Step", protocolStep),
    createField("Verification Status", verificationStatus),
  ];

  if (blockReason.value !== "None active") {
    protocolFields.push(createField("Block Reason", blockReason));
  }

  if (recoveryStep.value !== "None active") {
    protocolFields.push(createField("Recovery Step", recoveryStep));
  }

  return {
    summary: [
      {
        label: "Protocol Step",
        tone: protocolStep.tone,
        value: protocolStep.value,
      },
      {
        label: "Turn Status",
        tone: turnStatus.tone,
        value: turnStatus.value,
      },
      {
        label: "Verification",
        tone: verificationStatus.tone,
        value: verificationStatus.value,
      },
      {
        label: "System Integrity",
        tone: options.connectionStatus === "connected" ? "success" : "warning",
        value: options.connectionStatus === "connected" ? "Nominal" : "Degraded",
      },
    ],
    sections: [
      {
        title: "Protocol",
        fields: protocolFields,
      },
      {
        title: "Active Task",
        fields: [
          createField("Active Task ID", activeTaskId),
          createField("Active Task Name", activeTaskName),
          createField("Path Mode", pathMode),
          createField("Classification Label", classificationLabel),
        ],
      },
      {
        title: "Verification Surface",
        fields: [
          createField("Swap Count", swapCount),
          createField("Last Verified Item", lastVerifiedItem),
        ],
      },
    ],
  };
}
