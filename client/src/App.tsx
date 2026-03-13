import { useEffect, useRef, useState } from "react";
import { useMicrophoneBridge } from "./audio/useMicrophoneBridge";
import { useOperatorAudioPlayback } from "./audio/useOperatorAudioPlayback";
import { useCameraPreview } from "./media/useCameraPreview";
import { useTranscriptLayer, type TranscriptEntry } from "./transcript/useTranscriptLayer";
import { useSoundPlayback } from "./sound/useSoundPlayback";
import { useSoundCueTriggers } from "./sound/useSoundCueTriggers";
import { buildGroundingHudSnapshot } from "./hud/groundingHud";
import { useWaitingDialogue } from "./dialogue/useWaitingDialogue";
import {
  buildVerificationControlCopy,
  buildVerificationHudOverrides,
} from "./verification/verificationPresentation";
import { useTaskControls } from "./controls/useTaskControls";
import { useSessionState } from "./session/useSessionState";
import { useSessionWebSocket } from "./session/useSessionWebSocket";
import {
  useReadyToVerifyFlow,
  type ReadyToVerifyPhase,
  type VerificationTaskContext,
} from "./verification/useReadyToVerifyFlow";
import { useVerificationResultState } from "./verification/useVerificationResultState";
import { buildDemoRehearsalHarnessSnapshot } from "./demo/rehearsalHarness";
import type {
  SessionConnectionStatus,
  TransportLogEntry,
} from "./session/sessionTypes";

const TRANSCRIPT_STORAGE_KEY = "ghostline.transcript.entries";
const BACKEND_AUTHORED_OPERATOR_SOURCES = new Set<string>([
  "session_guidance",
  "operator_guidance",
  "demo_mode",
  "verification_flow",
  "recovery_ladder",
  "capability_recovery",
]);

function parseRouteFlag(name: string): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  const rawValue = new URLSearchParams(window.location.search).get(name);
  if (rawValue === null) {
    return false;
  }

  const normalized = rawValue.trim().toLowerCase();
  return normalized === "1" || normalized === "true" || normalized === "yes" || normalized === "on";
}

function getTranscriptPlaceholder(
  connectionStatus: SessionConnectionStatus,
  isMicStreaming: boolean,
  hasEntries: boolean,
): string {
  if (hasEntries) {
    return "";
  }

  if (connectionStatus !== "connected") {
    return "Transcript layer is standing by. Start the hotline and both sides of the call will accumulate here for later context.";
  }

  if (!isMicStreaming) {
    return "Transcript layer is live. User and operator lines will appear here once the in-call audio bridge is active.";
  }

  return "Listening for live user and operator transcript updates now.";
}

type PermissionStage =
  | "awaiting_call"
  | "request_camera"
  | "camera_requesting"
  | "camera_denied"
  | "request_microphone"
  | "microphone_requesting"
  | "microphone_denied"
  | "permissions_ready";

const statusLabels: Record<SessionConnectionStatus, string> = {
  idle: "Idle",
  connecting: "Connecting",
  connected: "Connected",
  reconnecting: "Reconnecting",
  disconnected: "Disconnected",
  error: "Connection Error",
};

function getOperatorTurnLabel(turnState: string): string {
  switch (turnState) {
    case "speaking":
      return "Speaking";
    case "interrupted":
      return "Interrupted";
    case "listening":
      return "Listening";
    default:
      return "Idle";
  }
}

function getOperatorTurnTone(
  turnState: string,
  connectionStatus: SessionConnectionStatus,
): string {
  if (turnState === "interrupted") {
    return "warning";
  }

  if (turnState === "speaking" || turnState === "listening") {
    return "connected";
  }

  return connectionStatus;
}

function formatTransportTime(timestamp: string): string {
  const parsedDate = new Date(timestamp);
  if (Number.isNaN(parsedDate.valueOf())) {
    return timestamp;
  }

  return parsedDate.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatEnvelopeSummary(entry: TransportLogEntry): string {
  if (entry.direction === "sent") {
    return `Sent ${entry.envelope.type}`;
  }

  return `Received ${entry.envelope.type}`;
}

function formatDemoBargeInStatus(status: string | null): string {
  switch (status) {
    case "armed":
      return "Armed";
    case "triggered":
      return "Triggered";
    case "restated":
      return "Restated";
    default:
      return "Standby";
  }
}

function formatDemoNearFailureStatus(status: string | null): string {
  switch (status) {
    case "failed_once":
      return "Failed Once";
    case "recovered":
      return "Recovered";
    default:
      return "Standby";
  }
}

function formatCaptureSummary(timestamp: string): string {
  const parsedDate = new Date(timestamp);
  if (Number.isNaN(parsedDate.valueOf())) {
    return timestamp;
  }

  return parsedDate.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function getPermissionStage(
  connectionStatus: SessionConnectionStatus,
  cameraPermission: string,
  cameraReady: boolean,
  microphonePermission: string,
  isMicStreaming: boolean,
): PermissionStage {
  if (connectionStatus !== "connected") {
    return "awaiting_call";
  }

  if (cameraPermission === "requesting") {
    return "camera_requesting";
  }

  if (!cameraReady) {
    return cameraPermission === "denied" ? "camera_denied" : "request_camera";
  }

  if (microphonePermission === "requesting") {
    return "microphone_requesting";
  }

  if (microphonePermission === "denied") {
    return "microphone_denied";
  }

  if (microphonePermission !== "granted" && !isMicStreaming) {
    return "request_microphone";
  }

  return "permissions_ready";
}

function formatPermissionStage(stage: PermissionStage): string {
  switch (stage) {
    case "awaiting_call":
      return "Awaiting Call";
    case "request_camera":
      return "Request Camera";
    case "camera_requesting":
      return "Camera Prompt Open";
    case "camera_denied":
      return "Camera Denied";
    case "request_microphone":
      return "Request Microphone";
    case "microphone_requesting":
      return "Microphone Prompt Open";
    case "microphone_denied":
      return "Microphone Denied";
    case "permissions_ready":
      return "Permissions Ready";
    default:
      return "Awaiting Call";
  }
}

function buildActiveTaskInstruction(
  activeTaskContext: VerificationTaskContext | null,
): string | null {
  if (activeTaskContext === null) {
    return null;
  }

  const taskName =
    typeof activeTaskContext.taskName === "string" &&
    activeTaskContext.taskName.trim().length > 0
      ? activeTaskContext.taskName.trim()
      : null;
  if (taskName === null) {
    return null;
  }

  const operatorDescription =
    typeof activeTaskContext.operatorDescription === "string" &&
    activeTaskContext.operatorDescription.trim().length > 0
      ? activeTaskContext.operatorDescription.trim()
      : "Perform the current containment step once, keep the frame readable, then stop.";

  return `First task: ${taskName}. Exact action: ${operatorDescription} When you are finished, say Ready to Verify or press the Ready to Verify button.`;
}
function getLatestBackendAuthoredOperatorLine(
  entries: readonly TranscriptEntry[],
): string | null {
  for (let index = entries.length - 1; index >= 0; index -= 1) {
    const entry = entries[index];
    if (
      entry.speaker === "operator" &&
      entry.status === "final" &&
      BACKEND_AUTHORED_OPERATOR_SOURCES.has(entry.source) &&
      entry.text.trim().length > 0
    ) {
      return entry.text.trim();
    }
  }

  return null;
}

function getOperatorPlaceholder(
  connectionStatus: SessionConnectionStatus,
  permissionStage: PermissionStage,
  cameraReady: boolean,
  captureFrameCount: number,
  activeTaskContext: VerificationTaskContext | null,
  microphonePermission: string,
  isMicStreaming: boolean,
  isOperatorSpeaking: boolean,
  operatorTurnState: string,
  operatorAudioChunkCount: number,
  lastError: string | null,
  cameraError: string | null,
  micError: string | null,
  playbackError: string | null,
): string {
  if (playbackError) {
    return playbackError;
  }

  if (cameraError) {
    return cameraError;
  }

  if (micError) {
    return micError;
  }

  if (isOperatorSpeaking) {
    return "Operator audio is streaming live from Gemini Live now. The room feed remains staged locally so calibration and verification windows can capture still frames on demand.";
  }

  if (operatorTurnState === "interrupted") {
    return "User interruption detected. Operator audio was flushed immediately. Speak now. The line is listening for a clean restatement.";
  }

  if (
    connectionStatus === "connecting" ||
    connectionStatus === "reconnecting"
  ) {
    return "Containment Desk is bringing the line up now. Stay with me. I will request camera and microphone in-call once the session is stable.";
  }

  if (permissionStage === "request_camera") {
    return "I need your camera. Grant access now. Calibration means one clean still frame of the room. Center the doorway or nearest boundary, keep the phone level, and capture one still image. After calibration, I will place the first task for you.";
  }

  if (permissionStage === "camera_requesting") {
    return "The camera request is open now. Approve it and return to the call. I will not advance until the room feed is visible.";
  }

  if (permissionStage === "camera_denied") {
    return "Camera access was denied. Retry it now. I need the room visible before I can stage calibration or a Ready to Verify hold.";
  }

  if (permissionStage === "request_microphone") {
    return "Good. I have the room feed. Now grant microphone access so I can hear you directly and keep the containment call live.";
  }

  if (permissionStage === "microphone_requesting") {
    return "The microphone request is open now. Approve it and speak when the capture bridge is live. We keep this inside the call, not in a setup screen.";
  }

  if (permissionStage === "microphone_denied") {
    return "Microphone access was denied. Retry it now. The line stays active while you reopen the audio bridge.";
  }

  if (connectionStatus === "connected" && cameraReady && captureFrameCount === 0) {
    return "Room feed linked. Calibration means one clean still frame of the room so I can place the first task. Center the doorway or nearest boundary, keep the phone level, capture one still frame, then hold. Once that frame is logged, I will give you the first containment step.";
  }

  if (
    permissionStage === "permissions_ready" &&
    !isMicStreaming &&
    microphonePermission === "granted"
  ) {
    return "Both permissions were granted in-call. Resume the microphone stream when you are ready to continue the session.";
  }

  const activeTaskInstruction = buildActiveTaskInstruction(activeTaskContext);
  if (
    connectionStatus === "connected" &&
    permissionStage === "permissions_ready" &&
    activeTaskInstruction !== null
  ) {
    return activeTaskInstruction;
  }

  if (
    connectionStatus === "connected" &&
    isMicStreaming &&
    operatorTurnState === "listening" &&
    operatorAudioChunkCount > 0
  ) {
    return "Interruption cleared. The line is listening now. Speak and the operator will restate cleanly without replaying stale speech.";
  }

  if (connectionStatus === "connected" && isMicStreaming && operatorAudioChunkCount > 0) {
    return "Live call active. Use the controls beside the room feed to verify a finished step, request a swap, pause, or end the session cleanly.";
  }

  if (connectionStatus === "connected" && isMicStreaming) {
    return "Microphone stream is live. Waiting for the first operator audio response from Gemini Live while the room-feed controls stay armed for verify, swap, pause, and end.";
  }

  if (lastError) {
    return `Transport is waiting for a clean reconnect. Last transport error: ${lastError}`;
  }

  return "Operator text will render here during the live call. Camera and microphone permissions remain part of the hotline exchange instead of a pre-call setup screen.";
}

function getPermissionRequestCopy(
  permissionStage: PermissionStage,
  isMicStreaming: boolean,
): { title: string; body: string; tone: "pending" | "warning" | "ready" } {
  switch (permissionStage) {
    case "awaiting_call":
      return {
        title: "Call Not Started",
        body: "Start the hotline first. Camera and microphone access are requested only after the operator asks for them in context.",
        tone: "pending",
      };
    case "request_camera":
      return {
        title: "Camera Request",
        body: "The Archivist is asking for the room feed now. Grant camera access from this panel so the call stays in character.",
        tone: "pending",
      };
    case "camera_requesting":
      return {
        title: "Awaiting Camera Permission",
        body: "Your browser camera prompt should be open. Approve it, then return to the hotline. The operator will wait for the room feed.",
        tone: "pending",
      };
    case "camera_denied":
      return {
        title: "Camera Access Denied",
        body: "Retry camera access when ready. The room view is required before calibration sampling and later verification holds.",
        tone: "warning",
      };
    case "request_microphone":
      return {
        title: "Microphone Request",
        body: "The room feed is linked. Grant microphone access now so the live audio bridge can open inside the call.",
        tone: "pending",
      };
    case "microphone_requesting":
      return {
        title: "Awaiting Microphone Permission",
        body: "Your browser microphone prompt should be open. Approve it, then speak. The transport remains live while the prompt is open.",
        tone: "pending",
      };
    case "microphone_denied":
      return {
        title: "Microphone Access Denied",
        body: "Retry microphone access when ready. The operator will keep the session open and wait for the audio bridge.",
        tone: "warning",
      };
    case "permissions_ready":
      return {
        title: "Permissions Complete",
        body: isMicStreaming
          ? "Camera and microphone were both requested and granted in-call. The session can proceed without any pre-call setup step."
          : "Camera and microphone were both requested in-call. The microphone stream is currently idle, but permission is already secured.",
        tone: "ready",
      };
    default:
      return {
        title: "Call Not Started",
        body: "Start the hotline first. Camera and microphone access are requested only after the operator asks for them in context.",
        tone: "pending",
      };
  }
}

function getControlBarCopy(
  isTransportActive: boolean,
  permissionStage: PermissionStage,
  verificationPhase: ReadyToVerifyPhase,
): string {
  if (!isTransportActive) {
    return "Start Call arms the live hotline. Ready to Verify, swap, pause, and end controls stay hidden until the line is active.";
  }

  if (permissionStage !== "permissions_ready") {
    return "Task controls stay locked until camera and microphone are granted in-call. End Session remains available so the user keeps a clean exit.";
  }

  if (verificationPhase === "pending" || verificationPhase === "capturing_window") {
    return "Ready to Verify is active now. Hold still for one second while the bounded verification window is captured.";
  }

  if (verificationPhase === "uploading_frames") {
    return "The bounded verification window was captured. Frame data is being sent to the backend now.";
  }

  if (verificationPhase === "captured") {
    return "The verification window is staged on the backend. This is a real Ready to Verify capture, not a continuous upload loop.";
  }

  return "Ready to Verify, swap, pause, and end now send structured WebSocket envelopes to the backend. Verification requests trigger a bounded hold-still capture window instead of a background stream.";
}

function getVerificationPhaseLabel(phase: ReadyToVerifyPhase): string {
  switch (phase) {
    case "pending":
      return "Pending";
    case "capturing_window":
      return "Capturing";
    case "uploading_frames":
      return "Uploading";
    case "captured":
      return "Captured";
    default:
      return "Idle";
  }
}

function getVerificationWindowCopy(
  phase: ReadyToVerifyPhase,
  expectedFrames: number,
  localCapturedFrames: number,
): string {
  switch (phase) {
    case "pending":
      return "The backend opened a Ready to Verify window. The operator has asked the caller to hold still for one second.";
    case "capturing_window":
      return `Capturing a bounded one-second verification window now. ${localCapturedFrames} of ${expectedFrames} frames staged locally.`;
    case "uploading_frames":
      return `The verification window is complete. Sending ${expectedFrames} staged frames plus task context to the backend.`;
    case "captured":
      return `The backend received the bounded verification window. ${expectedFrames} staged frames were delivered for the next verification phase.`;
    default:
      return "Ready to Verify stays idle until the user requests it by button or voice.";
  }
}

function getVerificationHudOverrides(verificationPhase: ReadyToVerifyPhase): {
  blockReason?: string;
  lastVerifiedItem?: string;
  protocolStep?: string;
  recoveryStep?: string;
  verificationStatus?: string;
} {
  switch (verificationPhase) {
    case "pending":
    case "capturing_window":
      return {
        protocolStep: "Ready to Verify window",
        verificationStatus: "Hold still - verification pending",
        blockReason: "Verification window in progress",
        recoveryStep: "Keep the frame steady for one second",
      };
    case "uploading_frames":
      return {
        protocolStep: "Ready to Verify upload",
        verificationStatus: "Uploading staged verification window",
        blockReason: "Waiting for backend frame intake",
        recoveryStep: "Hold the line while staged frames upload",
      };
    case "captured":
      return {
        protocolStep: "Verification window staged",
        verificationStatus: "Bounded capture complete",
        blockReason: "None active",
        recoveryStep: "Awaiting verification engine handoff",
        lastVerifiedItem: "Verification window captured",
      };
    default:
      return {};
  }
}

function formatCaseReportTimestamp(timestamp: string): string {
  const parsedDate = new Date(timestamp);
  if (Number.isNaN(parsedDate.valueOf())) {
    return timestamp;
  }

  return parsedDate.toLocaleString([], {
    hour: "2-digit",
    minute: "2-digit",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatCaseReportOutcome(outcome: string): string {
  switch (outcome) {
    case "user_confirmed_only":
      return "User Confirmed Only";
    case "unverified":
      return "Unverified";
    case "skipped":
      return "Skipped";
    default:
      return "Confirmed";
  }
}

function formatVerdictLabel(verdict: string | null): string {
  if (verdict === "inconclusive") {
    return "Inconclusive / Contained For Now";
  }
  if (verdict === "partial") {
    return "Partial Containment";
  }
  if (verdict === "secured") {
    return "Secured";
  }
  return "Pending";
}

function buildArchiveReferences(caseId: string): string[] {
  const normalized = caseId.replace(/[^A-Za-z0-9]/g, "").toUpperCase();
  const seed = normalized.length > 0 ? normalized : "CASE0000";
  const prefix = seed.slice(0, 4).padEnd(4, "X");
  const suffixSource = seed.slice(-4).padStart(4, "0");
  const baseValue = Number.parseInt(suffixSource, 36) || 0;

  return [1, 2, 3].map((offset) => {
    const nextValue = Math.max(baseValue - offset, 0)
      .toString(36)
      .toUpperCase()
      .padStart(4, "0");
    return `${prefix}-${nextValue}`;
  });
}

function App() {
  const session = useSessionWebSocket();
  const sessionState = useSessionState({
    connectionStatus: session.status,
    subscribeToEnvelopes: session.subscribeToEnvelopes,
  });
  const camera = useCameraPreview({
    connectionStatus: session.status,
    sendMessage: session.sendMessage,
  });
  const microphone = useMicrophoneBridge({
    connectionStatus: session.status,
    sendMessage: session.sendMessage,
  });
  const operatorAudio = useOperatorAudioPlayback({
    connectionStatus: session.status,
    isMicStreaming: microphone.isStreaming,
    subscribeToEnvelopes: session.subscribeToEnvelopes,
  });
  const soundPlayback = useSoundPlayback({
    isOperatorSpeaking: operatorAudio.isSpeaking,
  });
  const transcriptLayer = useTranscriptLayer({
    connectionStatus: session.status,
    subscribeToEnvelopes: session.subscribeToEnvelopes,
  });
  const taskControls = useTaskControls({
    connectionStatus: session.status,
    sendEnvelope: session.sendEnvelope,
    subscribeToEnvelopes: session.subscribeToEnvelopes,
  });
  const verificationFlow = useReadyToVerifyFlow({
    cameraReady: camera.cameraReady,
    captureFrame: camera.captureFrame,
    connectionStatus: session.status,
    sendMessage: session.sendMessage,
    subscribeToEnvelopes: session.subscribeToEnvelopes,
  });
  const verificationResult = useVerificationResultState({
    connectionStatus: session.status,
    subscribeToEnvelopes: session.subscribeToEnvelopes,
  });
  const activeTaskContext =
    sessionState.currentTaskContext ??
    taskControls.activeTaskContext ??
    verificationResult.taskContext ??
    verificationFlow.taskContext;
  const soundTriggerState = useSoundCueTriggers({
    cameraReady: camera.cameraReady,
    connectionStatus: session.status,
    finalVerdict: sessionState.finalVerdict,
    playCue: soundPlayback.playCue,
    startAmbientBed: soundPlayback.startAmbientBed,
    stopAmbientBed: soundPlayback.stopAmbientBed,
    taskAssignmentKey: activeTaskContext?.taskId ?? null,
    verificationAttemptId: verificationResult.attemptId,
    verificationStatus: verificationResult.status,
  });
  const endTeardownHandledRef = useRef(false);
  const [isDemoResetting, setIsDemoResetting] = useState(false);

  useEffect(() => {
    if (sessionState.state === "paused") {
      operatorAudio.interruptPlayback();
    }
  }, [sessionState.state]);

  useEffect(() => {
    if (sessionState.state === "ended") {
      if (endTeardownHandledRef.current) {
        return;
      }

      endTeardownHandledRef.current = true;
      operatorAudio.interruptPlayback();
      soundPlayback.stopAmbientBed();
      void microphone.stopMicrophone("session_ended");
      void camera.stopCamera();
      return;
    }

    endTeardownHandledRef.current = false;
  }, [sessionState.state]);

  const isTransportActive =
    session.status === "connected" ||
    session.status === "connecting" ||
    session.status === "reconnecting";
  const connectionLabel = statusLabels[session.status];
  const operatorTurnLabel = getOperatorTurnLabel(operatorAudio.turnState);
  const operatorTurnTone = getOperatorTurnTone(operatorAudio.turnState, session.status);
  const permissionStage = getPermissionStage(
    session.status,
    camera.permission,
    camera.cameraReady,
    microphone.permission,
    microphone.isStreaming,
  );
  const permissionStageLabel = formatPermissionStage(permissionStage);
  const rehearsalModeRequested = parseRouteFlag("rehearsal");
  const isDemoMode = sessionState.demoModeEnabled || session.demoModeRequested;
  const callModeLabel =
    isDemoMode
      ? "Ghostline demo mode / fixed safe path"
      : "Ghostline control surface";
  const demoBargeInStatusLabel = formatDemoBargeInStatus(
    sessionState.demoBargeIn?.status ?? null,
  );
  const demoNearFailureStatusLabel = formatDemoNearFailureStatus(
    sessionState.demoNearFailure?.status ?? null,
  );
  const showRehearsalHarness = isDemoMode && rehearsalModeRequested;
  const showDemoOperatorMeta = (sessionState.demoModeEnabled || session.demoModeRequested) && !showRehearsalHarness;
  const rehearsalHarness = showRehearsalHarness
    ? buildDemoRehearsalHarnessSnapshot(sessionState)
    : null;
  const permissionRequestCopy = getPermissionRequestCopy(
    permissionStage,
    microphone.isStreaming,
  );
  const activeIssue =
    verificationFlow.error ??
    camera.error ??
    operatorAudio.error ??
    soundPlayback.error ??
    microphone.error ??
    session.lastError;
  const fallbackOperatorPlaceholder = getOperatorPlaceholder(
    session.status,
    permissionStage,
    camera.cameraReady,
    camera.captureFrameCount,
    activeTaskContext,
    microphone.permission,
    microphone.isStreaming,
    operatorAudio.isSpeaking,
    operatorAudio.turnState,
    operatorAudio.operatorAudioChunkCount,
    session.lastError,
    camera.error,
    microphone.error,
    operatorAudio.error,
  );
  const waitingDialogue = useWaitingDialogue({
    active:
      session.status === "connected" &&
      permissionStage === "permissions_ready" &&
      sessionState.state !== "paused" &&
      microphone.isStreaming &&
      verificationFlow.phase === "idle" &&
      !verificationResult.awaitingDecision &&
      !verificationResult.hasResolvedResult &&
      !taskControls.readyToVerifyPending &&
      !taskControls.swapPending &&
      !taskControls.pausePending &&
      !taskControls.endSessionPending &&
      !operatorAudio.isInterrupted &&
      activeIssue === null,
    allowDiagnosticPrompt: camera.cameraReady && camera.captureFrameCount > 0,
    context:
      camera.cameraReady && camera.captureFrameCount > 0
        ? "task_execution"
        : "frame_guidance",
    demoModeEnabled: sessionState.demoModeEnabled || session.demoModeRequested,
    isOperatorSpeaking: operatorAudio.isSpeaking,
  });
  const verificationOperatorPlaceholder = verificationResult.awaitingDecision
    ? verificationFlow.operatorLine
    : verificationResult.operatorLine ??
      (verificationFlow.phase !== "captured" ? verificationFlow.operatorLine : null);
  const latestBackendAuthoredOperatorLine =
    sessionState.state === "ended" ||
    sessionState.caseReport !== null ||
    sessionState.state === "paused"
      ? null
      : getLatestBackendAuthoredOperatorLine(transcriptLayer.entries);
  const endedOperatorPlaceholder =
    sessionState.state === "ended" || sessionState.caseReport !== null
      ? "Session ended. Media activity has been stopped. Review the case report and archive reference below."
      : null;
  const pausedOperatorPlaceholder =
    sessionState.state === "paused"
      ? "Session paused. Resume when ready. The current task, transcript context, and recovery state remain staged."
      : null;
  const operatorPlaceholder =
    endedOperatorPlaceholder ??
    pausedOperatorPlaceholder ??
    latestBackendAuthoredOperatorLine ??
    verificationOperatorPlaceholder ??
    taskControls.swapOperatorLine ??
    waitingDialogue.currentLine ??
    fallbackOperatorPlaceholder;

  const sessionStateHudOverrides = sessionState.hasSnapshot
    ? {
        activeTaskId: activeTaskContext?.taskId ?? undefined,
        activeTaskName: activeTaskContext?.taskName ?? undefined,
        taskRoleCategory: activeTaskContext?.taskRoleCategory ?? undefined,
        taskTier: activeTaskContext?.taskTier ?? undefined,
        pathMode: activeTaskContext?.pathMode ?? sessionState.currentPathMode ?? undefined,
        protocolStep:
          sessionState.currentStep?.replace(/_/g, " ") ??
          sessionState.state?.replace(/_/g, " ") ??
          undefined,
        classificationLabel: sessionState.classificationLabel ?? undefined,
        swapCount: sessionState.swapCount,
        recoveryStep: sessionState.recoveryStep ?? undefined,
        verificationStatus:
          sessionState.verificationStatus?.replace(/_/g, " ") ?? undefined,
        blockReason: sessionState.blockReason ?? undefined,
        lastVerifiedItem: sessionState.lastVerifiedItem ?? undefined,
        ...(sessionState.turnStatus
          ? { turnStatus: sessionState.turnStatus.replace(/_/g, " ") }
          : {}),
      }
    : {};

  const groundingHud = buildGroundingHudSnapshot({
    activeIssue,
    cameraPermission: camera.permission,
    cameraReady: camera.cameraReady,
    captureFrameCount: camera.captureFrameCount,
    connectionStatus: session.status,
    isMicStreaming: microphone.isStreaming,
    isOperatorSpeaking: operatorAudio.isSpeaking,
    lastCapturedFrame: camera.lastCapturedFrame,
    microphonePermission: microphone.permission,
    overrides: {
      ...sessionStateHudOverrides,
      ...buildVerificationHudOverrides(
        verificationFlow.phase,
        verificationResult,
      ),
      ...(operatorAudio.turnState === "interrupted"
        ? { turnStatus: { value: "Interrupted", tone: "warning" as const } }
        : operatorAudio.turnState === "listening"
          ? { turnStatus: { value: "Listening", tone: "live" as const } }
          : {}),
    },
    permissionStage,
    permissionStageLabel,
  });

  const transportRows = session.recentMessages.slice(0, 2);
  const areTaskControlsVisible = session.status === "connected";
  const areTaskControlsArmed =
    areTaskControlsVisible && permissionStage === "permissions_ready";
  const pauseActionIsResume = sessionState.allowedActions.canResume;
  const pauseButtonLabel = pauseActionIsResume ? "Resume Session" : "Pause Session";
  const hasEndedReportView =
    sessionState.state === "ended" ||
    sessionState.state === "case_report" ||
    sessionState.caseReport !== null;
  const controlBarCopy = isDemoResetting
    ? "Demo reset is tearing down media, transport, and staged session state now. The shell will reload into a fresh demo-ready take."
    : hasEndedReportView
      ? "Session ended. Media activity was stopped cleanly and the report view is now staged below."
      : sessionState.state === "paused"
        ? "Session paused. Resume the hotline to continue task flow. Verification, swap, and recovery stay blocked until the line is resumed."
        : buildVerificationControlCopy(
            isTransportActive,
            permissionStage,
            verificationFlow.phase,
            verificationResult,
          );
  const canDemoReset = isDemoMode && !isDemoResetting;
  const isRecoveryRerouteRequired =
    verificationResult.status === "unconfirmed" &&
    verificationResult.retryAllowed === false;
  const canReadyToVerify =
    areTaskControlsArmed &&
    sessionState.allowedActions.canVerify &&
    camera.cameraReady &&
    microphone.isStreaming &&
    !verificationFlow.isBusy &&
    !verificationResult.awaitingDecision &&
    !isRecoveryRerouteRequired &&
    !taskControls.readyToVerifyPending &&
    !taskControls.pausePending &&
    !taskControls.endSessionPending &&
    !isDemoResetting;
  const canSwapTask =
    areTaskControlsArmed &&
    sessionState.allowedActions.canSwap &&
    !verificationFlow.isBusy &&
    !verificationResult.awaitingDecision &&
    !taskControls.swapPending &&
    !taskControls.pausePending &&
    !taskControls.endSessionPending &&
    !isDemoResetting;
  const canPauseSession =
    areTaskControlsArmed &&
    (sessionState.allowedActions.canPause || sessionState.allowedActions.canResume) &&
    !verificationFlow.isBusy &&
    !verificationResult.awaitingDecision &&
    !taskControls.pausePending &&
    !taskControls.endSessionPending &&
    !isDemoResetting;
  const canEndSession =
    areTaskControlsVisible &&
    (sessionState.allowedActions.canEnd || !sessionState.hasSnapshot) &&
    !taskControls.endSessionPending &&
    !isDemoResetting;
  const subtitlePlaceholder = getTranscriptPlaceholder(
    session.status,
    microphone.isStreaming,
    transcriptLayer.hasEntries,
  );
  const verificationWindowActive =
    verificationFlow.phase !== "idle" && !verificationResult.hasResolvedResult;
  const canRequestCamera =
    session.status === "connected" &&
    !camera.cameraReady &&
    camera.permission !== "requesting";
  const canRequestMicrophone =
    session.status === "connected" &&
    camera.cameraReady &&
    !microphone.isStreaming &&
    microphone.permission !== "requesting";

  let permissionActionLabel: string | null = null;
  let permissionAction: (() => void) | null = null;
  let permissionActionDisabled = false;

  if (permissionStage === "request_camera" || permissionStage === "camera_denied") {
    permissionActionLabel =
      permissionStage === "camera_denied"
        ? "Retry Camera Access"
        : "Grant Camera Access";
    permissionAction = () => {
      void camera.requestCameraAccess();
    };
    permissionActionDisabled = !canRequestCamera;
  } else if (
    permissionStage === "request_microphone" ||
    permissionStage === "microphone_denied"
  ) {
    permissionActionLabel =
      permissionStage === "microphone_denied"
        ? "Retry Microphone Access"
        : "Grant Microphone Access";
    permissionAction = () => {
      void operatorAudio.preparePlayback();
      void microphone.startMicrophone();
    };
    permissionActionDisabled = !canRequestMicrophone;
  } else if (
    permissionStage === "permissions_ready" &&
    microphone.permission === "granted" &&
    !microphone.isStreaming
  ) {
    permissionActionLabel = "Resume Microphone Stream";
    permissionAction = () => {
      void operatorAudio.preparePlayback();
      void microphone.startMicrophone();
    };
    permissionActionDisabled = !canRequestMicrophone;
  }

  async function handleStartCall(): Promise<void> {
    if (isTransportActive || isDemoResetting) {
      return;
    }

    void operatorAudio.preparePlayback();
    void soundPlayback.prepare();
    transcriptLayer.resetTranscript();
    session.connect();
  }

  async function handleDemoReset(): Promise<void> {
    if (!isDemoMode || isDemoResetting) {
      return;
    }

    setIsDemoResetting(true);

    try {
      if (isTransportActive) {
        session.sendMessage("stop", {
          reason: "demo_reset",
        });
      }

      operatorAudio.interruptPlayback();
      soundPlayback.stopAmbientBed();
      transcriptLayer.resetTranscript();

      try {
        window.sessionStorage.removeItem(TRANSCRIPT_STORAGE_KEY);
      } catch {
        // Demo reset clears persisted transcript state on a best-effort basis.
      }

      await microphone.stopMicrophone("demo_reset");
      await camera.stopCamera();

      window.setTimeout(() => {
        session.disconnect();
        window.location.assign(window.location.href);
      }, 180);
    } catch {
      window.location.assign(window.location.href);
    }
  }

  return (
    <div className={`hotline-shell${isDemoMode ? " hotline-shell-demo-readable" : ""}${isDemoResetting ? " hotline-shell-demo-resetting" : ""}`}>
      <header className="hero-panel panel">
        <div>
          <p className="eyebrow">Ghostline // Live Agent Shell</p>
          <h1>Ghostline Containment Hotline</h1>
          <p className="hero-copy">
            The Archivist, Containment Desk leads the room step by step. Camera, calibration, verification, recovery, and report flow now stay visible beside the live call.
          </p>
        </div>

        <div className="hero-status">
          <span className={`status-pill status-pill-${session.status}`}>
            Transport {connectionLabel}
          </span>
          <span className={`status-pill ${camera.cameraReady ? "status-pill-connected" : ""}`}>
            Camera {camera.cameraReady ? "Live" : camera.permission}
          </span>
          <span className={`status-pill ${microphone.isStreaming ? "status-pill-connected" : ""}`}>
            Mic {microphone.isStreaming ? "Streaming" : microphone.permission}
          </span>
          <span className={`status-pill status-pill-${operatorTurnTone}`}>
            Operator {operatorTurnLabel}
          </span>
          <span className={`status-pill ${soundPlayback.status === "ready" ? "status-pill-connected" : ""}`}>
            Sound {soundPlayback.statusLabel}
          </span>
          {activeIssue ? (
            <span className="status-pill status-pill-error">Issue recorded</span>
          ) : null}
          {verificationResult.hasResolvedResult ? (
            <span className={`status-pill status-pill-${verificationResult.statusTone}`}>
              {verificationResult.statusLabel}
            </span>
          ) : null}
        </div>
      </header>

      <main className="stage-grid">
        <section className="panel operator-panel" aria-label="Operator panel">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Operator Panel</p>
              <h2>The Archivist, Containment Desk</h2>
            </div>
            <span className={`panel-tag panel-tag-${operatorTurnTone}`}>
              {operatorTurnLabel}
            </span>
          </div>

          <div className="operator-script">
            <p className="operator-label">Primary Operator Guidance</p>
            <blockquote>{operatorPlaceholder}</blockquote>
          </div>

          <div
            className={`permission-request-card permission-request-card-${permissionRequestCopy.tone}`}
          >
            <div className="permission-request-header">
              <div>
                <p className="operator-label">In-Call Permission Flow</p>
                <h3>{permissionRequestCopy.title}</h3>
              </div>
              <span className="control-chip">{permissionStageLabel}</span>
            </div>
            <p className="permission-request-copy">{permissionRequestCopy.body}</p>
            <div className="permission-request-status">
              <span className="control-chip">Camera {camera.permission}</span>
              <span className="control-chip">Mic {microphone.permission}</span>
            </div>
            {permissionActionLabel && permissionAction ? (
              <div className="permission-request-actions">
                <button
                  type="button"
                  className="secondary-button"
                  disabled={permissionActionDisabled}
                  onClick={permissionAction}
                >
                  {permissionActionLabel}
                </button>
              </div>
            ) : null}
          </div>

          <div className="operator-meta">
            <div>
              <span className="meta-label">Call Mode</span>
              <strong>{callModeLabel}</strong>
            </div>
            <div>
              <span className="meta-label">Transport</span>
              <strong>{session.sessionUrl}</strong>
            </div>
            <div>
              <span className="meta-label">Permission Stage</span>
              <strong>{permissionStageLabel}</strong>
            </div>
            <div>
              <span className="meta-label">Sampler</span>
              <strong>
                {camera.captureFrameCount} staged frame
                {camera.captureFrameCount === 1 ? "" : "s"}
              </strong>
            </div>
            <div>
              <span className="meta-label">Sound Surface</span>
              <strong>
                {soundPlayback.statusLabel}
                {soundPlayback.isAmbientActive
                  ? soundPlayback.isAmbientDucked
                    ? " / ambient ducked under operator"
                    : " / ambient live"
                  : " / static cue manifest armed"}
              </strong>
            </div>
            <div>
              <span className="meta-label">Last Cue</span>
              <strong>{soundTriggerState.lastTriggeredCue ?? "None yet"}</strong>
            </div>
            {showDemoOperatorMeta ? (
              <div>
                <span className="meta-label">Demo Barge-In</span>
                <strong>{demoBargeInStatusLabel}</strong>
              </div>
            ) : null}
            {showDemoOperatorMeta ? (
              <div>
                <span className="meta-label">Cue Phrase</span>
                <strong>{sessionState.demoBargeIn?.triggerPhrase ?? "Archivist, wait. Say that again."}</strong>
              </div>
            ) : null}
            {showDemoOperatorMeta ? (
              <div>
                <span className="meta-label">Interrupt On</span>
                <strong>{sessionState.demoBargeIn?.targetLine ?? "That matches threshold activity. Keep the room controlled and continue with the next step."}</strong>
              </div>
            ) : null}
            {showDemoOperatorMeta ? (
              <div>
                <span className="meta-label">Demo Recovery Beat</span>
                <strong>{demoNearFailureStatusLabel}</strong>
              </div>
            ) : null}
            {showDemoOperatorMeta ? (
              <div>
                <span className="meta-label">Failure Type</span>
                <strong>{sessionState.demoNearFailure?.failureType?.replace(/_/g, " ") ?? "temporary low light"}</strong>
              </div>
            ) : null}
            {showDemoOperatorMeta ? (
              <div>
                <span className="meta-label">Recovery Task</span>
                <strong>{sessionState.demoNearFailure?.taskId ?? "T3"}</strong>
              </div>
            ) : null}
          </div>

          {activeIssue ? (
            <div className="issue-banner" role="status">
              <p>{activeIssue}</p>
            </div>
          ) : null}

          {verificationResult.hasResolvedResult ? (
            <article
              className={`control-status-card control-status-card-${verificationResult.cardTone} verification-result-card`}
              role="status"
            >
              <span className="control-status-title">{verificationResult.cardTitle}</span>
              <p className="control-status-body">{verificationResult.cardBody}</p>
              <div className="verification-result-meta">
                <span className="control-chip">{verificationResult.statusLabel}</span>
                {verificationResult.confidenceBand ? (
                  <span className="control-chip">
                    Confidence {verificationResult.confidenceBand}
                  </span>
                ) : null}
                {verificationResult.currentPathMode ? (
                  <span className="control-chip">
                    Path {verificationResult.currentPathMode}
                  </span>
                ) : null}
                {verificationResult.recoveryAttemptCount !== null &&
                verificationResult.recoveryAttemptLimit !== null ? (
                  <span className="control-chip">
                    Recovery {verificationResult.recoveryAttemptCount}/
                    {verificationResult.recoveryAttemptLimit}
                  </span>
                ) : null}
                {isRecoveryRerouteRequired ? (
                  <span className="control-chip">Reroute Required</span>
                ) : null}
                {verificationResult.isMock ? (
                  <span className="control-chip">Mock Result</span>
                ) : null}
              </div>
              {verificationResult.lastVerifiedItem ? (
                <p className="verification-result-detail">
                  <strong>Last Verified Item:</strong> {verificationResult.lastVerifiedItem}
                </p>
              ) : null}
              {verificationResult.blockReason ? (
                <p className="verification-result-detail">
                  <strong>Block Reason:</strong> {verificationResult.blockReason}
                </p>
              ) : null}
              {verificationResult.recoveryStep &&
              verificationResult.status === "unconfirmed" ? (
                <p className="verification-result-detail">
                  <strong>
                    {verificationResult.recoveryStepLabel ?? "Recovery"}:
                  </strong>{" "}
                  {verificationResult.recoveryStep}
                </p>
              ) : null}
              {verificationResult.suggestedPathMode ? (
                <p className="verification-result-detail">
                  <strong>Suggested Path:</strong>{" "}
                  {verificationResult.suggestedPathMode.replace(/_/g, " ")}
                </p>
              ) : null}
              {verificationResult.substituteTaskSuggestion ? (
                <p className="verification-result-detail">
                  <strong>Suggested Substitute:</strong>{" "}
                  {verificationResult.substituteTaskSuggestion.taskName} (
                  {verificationResult.substituteTaskSuggestion.taskId})
                </p>
              ) : null}
            </article>
          ) : null}

          <div className="transport-monitor">
            <p className="operator-label">Session Bridge</p>
            <div className="transport-list">
              {transportRows.length > 0 ? (
                transportRows.map((entry) => (
                  <article
                    className="transport-row"
                    key={`${entry.timestamp}-${entry.envelope.type}`}
                  >
                    <div>
                      <span
                        className={`transport-direction transport-direction-${entry.direction}`}
                      >
                        {entry.direction}
                      </span>
                      <strong>{formatEnvelopeSummary(entry)}</strong>
                    </div>
                    <span className="transport-time">
                      {formatTransportTime(entry.timestamp)}
                    </span>
                  </article>
                ))
              ) : (
                <article className="transport-row transport-row-empty">
                  Start Call opens the session. The operator then requests camera and
                  microphone in context, inside the call, instead of forcing a setup
                  screen before the hotline begins.
                </article>
              )}
            </div>
          </div>
        </section>

        <section className="panel camera-panel" aria-label="Camera preview area">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Camera Preview</p>
              <h2>Room Feed</h2>
            </div>
            <span className={`panel-tag ${camera.cameraReady ? "panel-tag-connected" : ""}`}>
              {camera.cameraReady ? "Live" : camera.permission}
            </span>
          </div>

          <div className={`camera-frame ${camera.cameraReady ? "camera-frame-live" : ""}`}>
            <video
              ref={camera.videoRef}
              className="camera-preview-video"
              autoPlay
              playsInline
              muted
            />
            {!camera.cameraReady ? (
              <div className="frame-overlay">
                <span>Preview activates only after the operator requests it</span>
                <small>Grant camera access in-call, then stage frames on demand.</small>
              </div>
            ) : null}
          </div>
          <canvas ref={camera.canvasRef} className="capture-canvas" aria-hidden="true" />

          <div className="camera-capture-panel">
            <div className="camera-meta">
              <span className="control-chip">Camera {camera.permission}</span>
              <span className="control-chip">Frames {camera.captureFrameCount}</span>
              <span className="control-chip">
                {camera.lastCapturedFrame
                  ? `${camera.lastCapturedFrame.width}x${camera.lastCapturedFrame.height}`
                  : "No staged frame yet"}
              </span>
            </div>

            {camera.cameraReady ? (
              <div className="camera-action-row">
                <button
                  type="button"
                  className="secondary-button"
                  disabled={taskControls.endSessionPending || verificationFlow.isBusy}
                  onClick={() => {
                    void camera.captureFrame("calibration");
                  }}
                >
                  {camera.captureFrameCount > 0
                    ? "Retake Calibration"
                    : "Capture Calibration"}
                </button>
              </div>
            ) : null}

            {verificationWindowActive ? (
              <article
                className={`capture-preview-card verification-window-card verification-window-card-${verificationFlow.phase}`}
              >
                <div className="capture-preview-header">
                  <strong>Ready to Verify Window</strong>
                  <span>{getVerificationPhaseLabel(verificationFlow.phase)}</span>
                </div>
                <p className="verification-window-body">
                  {getVerificationWindowCopy(
                    verificationFlow.phase,
                    verificationFlow.expectedFrames,
                    verificationFlow.localCapturedFrames,
                  )}
                </p>
                <div className="camera-meta">
                  <span className="control-chip">
                    Attempt {verificationFlow.attemptId ?? "idle"}
                  </span>
                  <span className="control-chip">
                    Local {verificationFlow.localCapturedFrames}/{verificationFlow.expectedFrames}
                  </span>
                  <span className="control-chip">
                    Backend {verificationFlow.receivedFrames}/{verificationFlow.expectedFrames}
                  </span>
                </div>
              </article>
            ) : null}

            {camera.lastCapturedFrame ? (
              <article className="capture-preview-card">
                <div className="capture-preview-header">
                  <strong>{camera.lastCapturedFrame.captureType.replace(/_/g, " ")}</strong>
                  <span>{formatCaptureSummary(camera.lastCapturedFrame.capturedAt)}</span>
                </div>
                <img
                  src={camera.lastCapturedFrame.dataUrl}
                  alt={`Last ${camera.lastCapturedFrame.captureType} frame`}
                />
              </article>
            ) : (
              <article className="capture-preview-card capture-preview-card-empty">
                Still frames remain staged locally for calibration now and for the later Ready to Verify flow.
              </article>
            )}
          </div>
          <section className="panel control-bar camera-control-deck" aria-label="Session controls">
        <div className="control-bar-copy">
          <div>
            <p className="panel-kicker">Session Controls</p>
            <h2>Session Controls</h2>
            <p className="control-copy">{controlBarCopy}</p>
          </div>

          {taskControls.lastNotice ? (
            <article
              className={`control-status-card control-status-card-${taskControls.lastNotice.tone}`}
            >
              <span className="control-status-title">{taskControls.lastNotice.title}</span>
              <p className="control-status-body">{taskControls.lastNotice.body}</p>
            </article>
          ) : null}

          {isDemoMode ? (
            <article className="control-status-card control-status-card-demo-support">
              <span className="control-status-title">Demo Support</span>
              <p className="control-status-body">
                Readability mode is active for recording. Demo Reset clears transcript, media,
                staged report state, and the current session take in one step.
              </p>
            </article>
          ) : null}
        </div>

        <div className="control-actions">
          {!isTransportActive ? (
            <button
              type="button"
              className={`start-call-button start-call-button-${session.status}`}
              disabled={isDemoResetting}
              onClick={() => {
                void handleStartCall();
              }}
            >
              {session.status === "error" ? "Reconnect Call" : "Start Call"}
            </button>
          ) : (
            <button
              type="button"
              className={`start-call-button start-call-button-${session.status}`}
              disabled
            >
              {session.status === "connected" ? "Call Live" : connectionLabel}
            </button>
          )}

          {areTaskControlsVisible && !areTaskControlsArmed ? (
            <span className="control-chip">
              Controls arm after in-call camera and mic approval
            </span>
          ) : null}

          {areTaskControlsArmed ? (
            <button
              type="button"
              className="secondary-button"
              disabled={!canReadyToVerify}
              onClick={() => {
                taskControls.requestReadyToVerify({
                  taskContext: activeTaskContext,
                });
              }}
            >
              {taskControls.readyToVerifyPending ? "Sending Verify Request" : "Ready to Verify"}
            </button>
          ) : null}

          {areTaskControlsArmed ? (
            <button
              type="button"
              className="secondary-button"
              disabled={!canSwapTask}
              onClick={() => {
                taskControls.requestSwapTask({
                  taskContext: activeTaskContext,
                });
              }}
            >
              {taskControls.swapPending ? "Sending Swap Request" : "Can't Do This / Swap Task"}
            </button>
          ) : null}

          {areTaskControlsArmed ? (
            <button
              type="button"
              className="secondary-button"
              disabled={!canPauseSession}
              onClick={() => {
                taskControls.requestPauseSession(!pauseActionIsResume);
              }}
            >
              {taskControls.pausePending ? `Sending ${pauseButtonLabel}` : pauseButtonLabel}
            </button>
          ) : null}

          {areTaskControlsVisible ? (
            <button
              type="button"
              className="danger-button"
              disabled={!canEndSession}
              onClick={() => {
                taskControls.requestEndSession();
              }}
            >
              {taskControls.endSessionPending ? "Ending Session" : "End Session"}
            </button>
          ) : null}

          {isDemoMode ? (
            <button
              type="button"
              className="secondary-button demo-reset-button"
              disabled={!canDemoReset}
              onClick={() => {
                void handleDemoReset();
              }}
            >
              {isDemoResetting ? "Resetting Demo" : "Demo Reset"}
            </button>
          ) : null}
        </div>
          </section>
        </section>

        <section className="panel subtitles-panel" aria-label="Subtitles area">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Subtitles</p>
              <h2>Conversation Transcript</h2>
            </div>
            <span className="panel-tag">
              {transcriptLayer.hasEntries
                ? `${transcriptLayer.entries.length} line${transcriptLayer.entries.length === 1 ? "" : "s"}`
                : "Always On"}
            </span>
          </div>

          <div className="subtitle-list">
            {transcriptLayer.hasEntries ? (
              transcriptLayer.entries.map((entry) => (
                <article
                  className={`subtitle-row subtitle-row-${entry.speaker}`}
                  key={entry.id}
                >
                  <div className="subtitle-meta">
                    <div className="subtitle-meta-group">
                      <span className="subtitle-speaker">
                        {entry.speaker === "operator" ? "Operator" : "User"}
                      </span>
                      <span className={`subtitle-status subtitle-status-${entry.status}`}>
                        {entry.status === "final" ? "Final" : "Live"}
                      </span>
                    </div>
                    <span className="subtitle-time">
                      {formatCaptureSummary(entry.updatedAt)}
                    </span>
                  </div>
                  <p className="subtitle-body">{entry.text}</p>
                </article>
              ))
            ) : (
              <article className="subtitle-row subtitle-row-empty">
                {subtitlePlaceholder}
              </article>
            )}
          </div>
        </section>

        <aside className="panel hud-panel" aria-label="Grounding HUD area">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Grounding HUD</p>
              <h2>Containment Surface</h2>
            </div>
            <span className={`panel-tag panel-tag-${session.status}`}>{connectionLabel}</span>
          </div>

          <div className="hud-summary" aria-label="Grounding HUD summary">
            {groundingHud.summary.map((item) => (
              <article
                className={`hud-summary-chip hud-summary-chip-${item.tone}`}
                key={item.label}
              >
                <span className="hud-summary-label">{item.label}</span>
                <strong className={`hud-summary-value hud-value-${item.tone}`}>
                  {item.value}
                </strong>
              </article>
            ))}
          </div>

          <div className="hud-sections">
            {groundingHud.sections.map((section) => (
              <section className="hud-section" key={section.title}>
                <h3>{section.title}</h3>
                <dl className="hud-grid">
                  {section.fields.map((field) => (
                    <div className="hud-row" key={field.label}>
                      <dt>{field.label}</dt>
                      <dd className={`hud-value hud-value-${field.tone}`}>
                        {field.value}
                      </dd>
                    </div>
                  ))}
                </dl>
              </section>
            ))}
          </div>
        </aside>
      </main>
      {showRehearsalHarness && rehearsalHarness ? (
        <section className="panel rehearsal-panel" aria-label="Demo rehearsal harness">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Demo Rehearsal Harness</p>
              <h2>Fixed Path Checklist</h2>
            </div>
            <span className="panel-tag panel-tag-warning">Developer View</span>
          </div>

          <div className="rehearsal-summary-row">
            <p className="control-copy">{rehearsalHarness.summary}</p>
            <span className="control-chip">Use Demo Reset between takes</span>
          </div>

          <div className="rehearsal-grid">
            <section className="rehearsal-card">
              <p className="meta-label">Key Checks</p>
              <div className="rehearsal-check-list">
                {rehearsalHarness.checks.map((check) => (
                  <article
                    className={`rehearsal-check rehearsal-check-${check.status}`}
                    key={check.label}
                  >
                    <div className="rehearsal-check-header">
                      <strong>{check.label}</strong>
                      <span className="control-chip">{check.status}</span>
                    </div>
                    <p className="control-status-body">{check.detail}</p>
                  </article>
                ))}
              </div>
            </section>

            <section className="rehearsal-card">
              <p className="meta-label">Fixed Task Path</p>
              <div className="rehearsal-task-list">
                {rehearsalHarness.taskProgress.map((task) => (
                  <article
                    className={`rehearsal-task rehearsal-task-${task.status}`}
                    key={task.taskId}
                  >
                    <div className="rehearsal-task-header">
                      <strong>
                        {task.taskName} <span>({task.taskId})</span>
                      </strong>
                      <span className="control-chip">{task.status}</span>
                    </div>
                    <p className="control-status-body">{task.detail}</p>
                  </article>
                ))}
              </div>
            </section>
          </div>
        </section>
      ) : null}
      {sessionState.caseReport ? (
        <section className={`panel case-report-panel case-report-panel-${sessionState.caseReport.closingTemplate.tone}`} aria-label="Case report">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Case Report</p>
              <h2>{sessionState.caseReport.closingTemplate.heading}</h2>
            </div>
            <span className={`panel-tag panel-tag-${sessionState.finalVerdict ?? "idle"}`}>
              {formatVerdictLabel(sessionState.caseReport.finalVerdict)}
            </span>
          </div>
          <div className="case-report-meta">
            <article>
              <span className="meta-label">Case ID</span>
              <strong>{sessionState.caseReport.caseId}</strong>
            </article>
            <article>
              <span className="meta-label">Generated</span>
              <strong>{formatCaseReportTimestamp(sessionState.caseReport.generatedAt)}</strong>
            </article>
            <article>
              <span className="meta-label">Classification</span>
              <strong>{sessionState.caseReport.incidentClassificationLabel}</strong>
            </article>
            <article>
              <span className="meta-label">Verdict</span>
              <strong>{formatVerdictLabel(sessionState.caseReport.finalVerdict)}</strong>
            </article>
          </div>
          <article className="case-report-summary">
            <p className="case-report-summary-label">Incident Summary</p>
            <p className="case-report-summary-copy">
              {sessionState.caseReport.incidentClassificationSummary}
            </p>
            <div className="case-report-counts">
              <span className="control-chip case-report-chip-confirmed">
                Confirmed {sessionState.caseReport.counts.confirmed}
              </span>
              <span className="control-chip case-report-chip-user-confirmed">
                User Confirmed {sessionState.caseReport.counts.user_confirmed_only}
              </span>
              <span className="control-chip case-report-chip-unverified">
                Unverified {sessionState.caseReport.counts.unverified}
              </span>
              <span className="control-chip case-report-chip-skipped">
                Skipped {sessionState.caseReport.counts.skipped}
              </span>
            </div>
          </article>
          <article className={`case-report-closing case-report-closing-${sessionState.caseReport.closingTemplate.tone}`}>
            <p className="case-report-summary-label">Closing Line</p>
            <p className="case-report-summary-copy">
              {sessionState.caseReport.closingTemplate.closingLine}
            </p>
          </article>

          <article className="case-report-archive" aria-label="Containment Desk archive reference">
            <div className="case-report-archive-header">
              <p className="case-report-summary-label">Containment Desk Archive Reference</p>
              <span className="control-chip">Current {sessionState.caseReport.caseId}</span>
            </div>
            <div className="case-report-archive-list" role="list">
              {buildArchiveReferences(sessionState.caseReport.caseId).map((reference) => (
                <span className="case-report-archive-chip" key={reference} role="listitem">
                  {reference}
                </span>
              ))}
            </div>
          </article>

          <div className="case-report-task-list" role="list">
            {sessionState.caseReport.tasks.map((task) => (
              <article className="case-report-task-row" key={`${task.taskId}-${task.origin}`} role="listitem">
                <div className="case-report-task-header">
                  <div>
                    <p className="case-report-task-step">{task.protocolStep ?? "Unmapped step"}</p>
                    <h3>
                      {task.taskName} <span>({task.taskId})</span>
                    </h3>
                  </div>
                  <span
                    className={`case-report-outcome case-report-outcome-${task.outcome.replace(/_/g, "-")}`}
                  >
                    {formatCaseReportOutcome(task.outcome)}
                  </span>
                </div>
                <div className="case-report-task-meta">
                  <span className="control-chip">Tier {task.taskTier}</span>
                  <span className="control-chip">{task.taskRoleCategory}</span>
                  <span className="control-chip">
                    {task.origin === "substitute" ? "Substitute Task" : "Planned Task"}
                  </span>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}

export default App;



































































































