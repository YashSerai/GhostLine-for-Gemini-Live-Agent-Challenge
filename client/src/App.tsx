import { useEffect, useRef, useState } from "react";
import { useMicrophoneBridge } from "./audio/useMicrophoneBridge";
import { useOperatorAudioPlayback } from "./audio/useOperatorAudioPlayback";
import { useCameraPreview } from "./media/useCameraPreview";
import { useRoomScan } from "./media/useRoomScan";
import { useTaskVision } from "./media/useTaskVision";
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
  | "request_microphone"
  | "microphone_requesting"
  | "microphone_denied"
  | "request_camera"
  | "camera_requesting"
  | "camera_denied"
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

  if (turnState === "speaking") {
    return "live";
  }

  if (turnState === "listening") {
    return "ready";
  }

  return connectionStatus === "connected" ? "idle" : connectionStatus;
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

  if (microphonePermission === "requesting") {
    return "microphone_requesting";
  }

  if (microphonePermission === "denied") {
    return "microphone_denied";
  }

  if (microphonePermission !== "granted" && !isMicStreaming) {
    return "request_microphone";
  }

  if (cameraPermission === "requesting") {
    return "camera_requesting";
  }

  if (!cameraReady) {
    return cameraPermission === "denied" ? "camera_denied" : "request_camera";
  }

  return "permissions_ready";
}

function formatPermissionStage(stage: PermissionStage): string {
  switch (stage) {
    case "awaiting_call":
      return "Awaiting Call";
    case "request_microphone":
      return "Request Microphone";
    case "microphone_requesting":
      return "Microphone Prompt Open";
    case "microphone_denied":
      return "Microphone Denied";
    case "request_camera":
      return "Request Camera";
    case "camera_requesting":
      return "Camera Prompt Open";
    case "camera_denied":
      return "Camera Denied";
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
    return "Containment Desk is bringing the line up now. Stay with me. I will request microphone first, then camera, then one room sweep and calibration still frame.";
  }

  if (permissionStage === "request_microphone") {
    return "Thank you for calling Ghostline. Stay with me and follow my instructions exactly. To hear you clearly, I need microphone access now.";
  }

  if (permissionStage === "microphone_requesting") {
    return "The microphone request is open now. Approve it and return to the call. Camera comes next.";
  }

  if (permissionStage === "microphone_denied") {
    return "Microphone access was denied. Retry it now. I need to hear you before I place the camera and containment steps.";
  }

  if (permissionStage === "request_camera") {
    return "Good. I have confirmed microphone access. Since you placed this call, I am treating the room as an active containment case. Now grant camera access so I can see the surrounding space.";
  }

  if (permissionStage === "camera_requesting") {
    return "The camera request is open now. Approve it and return to the call. After that, I will ask for one slow room sweep and one calibration still frame.";
  }

  if (permissionStage === "camera_denied") {
    return "Camera access was denied. Retry it now. I need one slow room sweep and one clean calibration frame before I can place the first step.";
  }

  if (connectionStatus === "connected" && cameraReady && captureFrameCount === 0) {
    return "I have confirmed camera access. Pan slowly in a full circle for about five seconds. The scan will complete automatically when I have enough room context.";
  }

  if (
    permissionStage === "permissions_ready" &&
    !isMicStreaming &&
    microphonePermission === "granted"
  ) {
    return "Camera and microphone are both approved in-call. Resume the microphone stream when you are ready to continue the session.";
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
    return "Microphone stream is live. The line is waiting to place or restate the next containment instruction.";
  }

  if (lastError) {
    return `Transport is waiting for a clean reconnect. Last transport error: ${lastError}`;
  }

  return "Primary operator guidance will render here during the live call. Voice is primary, and this panel mirrors the active instruction in case you miss a spoken line.";
}

function getPermissionRequestCopy(
  permissionStage: PermissionStage,
  isMicStreaming: boolean,
): { title: string; body: string; tone: "pending" | "warning" | "ready" } {
  switch (permissionStage) {
    case "awaiting_call":
      return {
        title: "Call Not Started",
        body: "Start the hotline first. Microphone comes first, then camera, then one room sweep and one calibration still frame.",
        tone: "pending",
      };
    case "request_microphone":
      return {
        title: "Microphone Request",
        body: "The Archivist is taking control of the call now. Grant microphone access first so the line can hear you clearly before the room sweep begins.",
        tone: "pending",
      };
    case "microphone_requesting":
      return {
        title: "Awaiting Microphone Permission",
        body: "Your browser microphone prompt should be open. Approve it, then return to the call. Camera comes next.",
        tone: "pending",
      };
    case "microphone_denied":
      return {
        title: "Microphone Access Denied",
        body: "Retry microphone access now. The hotline should hear you before it asks for the room feed.",
        tone: "warning",
      };
    case "request_camera":
      return {
        title: "Camera Request",
        body: "Microphone access is confirmed. Grant camera access now so the Archivist can direct a room sweep, lock calibration, and place the first containment step.",
        tone: "pending",
      };
    case "camera_requesting":
      return {
        title: "Awaiting Camera Permission",
        body: "Your browser camera prompt should be open. Approve it, then return to the hotline. The next beat is one slow room sweep plus one calibration still frame.",
        tone: "pending",
      };
    case "camera_denied":
      return {
        title: "Camera Access Denied",
        body: "Retry camera access now. The hotline cannot place the first step until the room sweep and calibration frame are complete.",
        tone: "warning",
      };
    case "permissions_ready":
      return {
        title: "Permissions Complete",
        body: isMicStreaming
          ? "Microphone and camera were both granted in-call. Pan the camera slowly for a 360-degree sweep. The scan completes automatically, then follow the assigned task exactly."
          : "Microphone and camera are both approved in-call. Resume the microphone stream when you are ready to continue.",
        tone: "ready",
      };
    default:
      return {
        title: "Call Not Started",
        body: "Start the hotline first. Microphone comes first, then camera, then one room sweep and one calibration still frame.",
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
    return "Task controls stay locked until microphone and camera are granted in-call. End Session remains available so the user keeps a clean exit.";
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

function playStartCallRing(): void {
  if (typeof window === "undefined") {
    return;
  }

  const AudioContextConstructor = window.AudioContext ?? (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!AudioContextConstructor) {
    return;
  }

  const context = new AudioContextConstructor();
  const master = context.createGain();
  master.gain.value = 0.04;
  master.connect(context.destination);

  const startAt = context.currentTime + 0.02;
  const bursts = [0, 0.34, 0.68];
  for (const offset of bursts) {
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.type = "triangle";
    oscillator.frequency.setValueAtTime(920, startAt + offset);
    gain.gain.setValueAtTime(0.0001, startAt + offset);
    gain.gain.exponentialRampToValueAtTime(0.24, startAt + offset + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, startAt + offset + 0.17);
    oscillator.connect(gain);
    gain.connect(master);
    oscillator.start(startAt + offset);
    oscillator.stop(startAt + offset + 0.18);
  }

  window.setTimeout(() => {
    void context.close();
  }, 1300);
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

  const [browserMicPermission, setBrowserMicPermission] = useState<string>("prompt");

  useEffect(() => {
    if (typeof navigator?.permissions?.query !== "function") return;
    navigator.permissions.query({ name: "microphone" as PermissionName })
      .then((status) => {
        setBrowserMicPermission(status.state);
        status.onchange = () => {
          setBrowserMicPermission(status.state);
        };
      })
      .catch((err) => console.warn("Could not query microphone permission", err));
  }, []);

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

  // Room scan: stream camera frames at ~1fps to Gemini during room_sweep
  const roomScan = useRoomScan({
    isScanning: sessionState.state === "room_sweep",
    connectionStatus: session.status,
    videoRef: camera.videoRef,
    canvasRef: camera.canvasRef,
    sendMessage: session.sendMessage,
  });

  // Task vision: stream camera frames at ~1fps to Gemini during task execution
  useTaskVision({
    isActive:
      camera.cameraReady &&
      (sessionState.state === "task_assigned" || sessionState.state === "waiting_ready"),
    connectionStatus: session.status,
    videoRef: camera.videoRef,
    canvasRef: camera.canvasRef,
    sendMessage: session.sendMessage,
  });

  const endTeardownHandledRef = useRef(false);
  const [isDemoResetting, setIsDemoResetting] = useState(false);
  const [pendingStartCallIntro, setPendingStartCallIntro] = useState(false);

  // --- Onboarding splash ---
  const [showSplash, setShowSplash] = useState(true);

  // --- Session timer ---
  const [callStartTime, setCallStartTime] = useState<number | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    if (session.status === "connected" && callStartTime === null) {
      setCallStartTime(Date.now());
    }
    if (session.status === "disconnected" || session.status === "idle") {
      setCallStartTime(null);
      setElapsedSeconds(0);
    }
  }, [session.status, callStartTime]);

  useEffect(() => {
    if (callStartTime === null) return;
    const id = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - callStartTime) / 1000));
    }, 1000);
    return () => clearInterval(id);
  }, [callStartTime]);

  const formatTimer = (secs: number): string => {
    const m = Math.floor(secs / 60).toString().padStart(2, "0");
    const s = (secs % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

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
  const showRehearsalHarness = isDemoMode && rehearsalModeRequested;
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
    !microphone.isStreaming &&
    microphone.permission !== "requesting";

  useEffect(() => {
    if (!pendingStartCallIntro || session.status !== "connected") {
      return;
    }
    setPendingStartCallIntro(false);
    void operatorAudio.preparePlayback();
  }, [pendingStartCallIntro, session.status, microphone, operatorAudio]);
  useEffect(() => {
    if (session.status !== "connected" && session.status !== "connecting") {
      setPendingStartCallIntro(false);
    }
  }, [session.status]);

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
    playStartCallRing();
    transcriptLayer.resetTranscript();
    setPendingStartCallIntro(true);
    session.updateClientConnectPayload({ browserMicPermission });
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

  // --- Containment score ---
  const containmentScore = (() => {
    const cr = sessionState.caseReport;
    if (!cr) return null;
    const total = cr.counts.confirmed + cr.counts.user_confirmed_only + cr.counts.unverified + cr.counts.skipped;
    if (total === 0) return null;
    const points = cr.counts.confirmed * 100 + cr.counts.user_confirmed_only * 60;
    return Math.round(points / (total * 100) * 100);
  })();

  // --- Share report ---
  async function handleShareReport() {
    const cr = sessionState.caseReport;
    if (!cr) return;
    const text = [
      `🔮 GHOSTLINE CONTAINMENT REPORT`,
      `Case: ${cr.caseId}`,
      `Verdict: ${cr.closingTemplate.heading}`,
      `Classification: ${cr.incidentClassificationLabel}`,
      containmentScore !== null ? `Containment Score: ${containmentScore}%` : "",
      `Tasks: ${cr.counts.confirmed} confirmed, ${cr.counts.user_confirmed_only} user-confirmed, ${cr.counts.unverified} unverified, ${cr.counts.skipped} skipped`,
      callStartTime ? `Duration: ${formatTimer(elapsedSeconds)}` : "",
      ``,
      `${cr.closingTemplate.closingLine}`,
      ``,
      `Investigated via Ghostline — Live Paranormal Containment Hotline`,
    ].filter(Boolean).join("\n");

    if (navigator.share) {
      try {
        await navigator.share({ title: "Ghostline Case Report", text });
        return;
      } catch { /* user cancelled or unsupported */ }
    }
    try {
      await navigator.clipboard.writeText(text);
      alert("Report copied to clipboard!");
    } catch {
      alert("Could not share report.");
    }
  }

  // --- Splash screen ---
  if (showSplash) {
    return (
      <div className="ghostline-splash" onClick={() => setShowSplash(false)}>
        <div className="splash-content">
          <p className="splash-eyebrow">Ghostline</p>
          <h1 className="splash-title">Live Paranormal<br />Containment Hotline</h1>
          <p className="splash-body">
            A real-time voice &amp; camera experience powered by Gemini Live.
            The Archivist guides you through a containment protocol — step by step.
          </p>
          <button
            type="button"
            className="splash-cta"
            onClick={(e) => { e.stopPropagation(); setShowSplash(false); }}
          >
            Start the Hotline
          </button>
          <p className="splash-hint">Tap anywhere to continue</p>
        </div>
      </div>
    );
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
          {callStartTime !== null ? (
            <span className="status-pill status-pill-connected">
              ⏱ {formatTimer(elapsedSeconds)}
            </span>
          ) : null}
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
                <span>Preview activates once the operator requests it</span>
                <small>Grant camera access in-call to begin the live feed.</small>
              </div>
            ) : null}
          </div>
          <canvas ref={camera.canvasRef} className="capture-canvas" aria-hidden="true" />

          <div className="camera-capture-panel">

            {camera.cameraReady &&
            sessionState.state !== "task_assigned" &&
            sessionState.state !== "waiting_ready" &&
            sessionState.state !== "verifying" &&
            sessionState.state !== "paused" &&
            sessionState.state !== "ended" &&
            sessionState.calibrationCapturedAt === null ? (
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
                    ? "Force Complete Scan (Fallback)"
                    : "Force Complete Scan"}
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

              </article>
            ) : null}

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

          {areTaskControlsArmed && activeTaskContext?.taskName ? (
            <div className="active-task-card" style={{
              background: "linear-gradient(135deg, rgba(139,92,246,0.15), rgba(59,130,246,0.1))",
              border: "1px solid rgba(139,92,246,0.3)",
              borderRadius: "12px",
              padding: "16px",
              marginBottom: "12px",
              position: "relative" as const,
              overflow: "hidden",
            }}>
              <div style={{
                position: "absolute" as const,
                top: 0, left: 0, right: 0, height: "3px",
                background: sessionState.state === "verifying"
                  ? "linear-gradient(90deg, #f59e0b, #ef4444)"
                  : sessionState.state === "recovery_active"
                  ? "linear-gradient(90deg, #ef4444, #dc2626)"
                  : "linear-gradient(90deg, #8b5cf6, #3b82f6)",
                animation: sessionState.state === "verifying" ? "pulse 1.5s ease-in-out infinite" : undefined,
              }} />
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
                <span style={{ fontSize: "16px" }}>
                  {sessionState.state === "verifying" ? "🟠" :
                   sessionState.state === "recovery_active" ? "🔴" :
                   verificationResult.status === "confirmed" ? "✅" : "🔵"}
                </span>
                <strong style={{ fontSize: "14px", color: "#e2e8f0", letterSpacing: "0.02em" }}>
                  {activeTaskContext.taskName}
                </strong>
              </div>
              {activeTaskContext.operatorDescription ? (
                <p style={{
                  fontSize: "12px", color: "#94a3b8", margin: "0 0 12px 0",
                  lineHeight: "1.5",
                }}>
                  {String(activeTaskContext.operatorDescription)}
                </p>
              ) : null}
              <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                <span style={{
                  fontSize: "11px", color: "#64748b",
                  textTransform: "uppercase" as const,
                  letterSpacing: "0.05em",
                  fontWeight: 600,
                }}>
                  {sessionState.state === "verifying" ? "Verifying..." :
                   sessionState.state === "recovery_active" ? "Retry Required" :
                   verificationResult.status === "confirmed" ? "Complete" : "In Progress"}
                </span>
                <div style={{ flex: 1 }} />
                <button
                  type="button"
                  className="secondary-button"
                  style={{ fontSize: "11px", padding: "4px 12px" }}
                  disabled={!canReadyToVerify}
                  onClick={() => {
                    taskControls.requestReadyToVerify({
                      taskContext: activeTaskContext,
                    });
                  }}
                >
                  {taskControls.readyToVerifyPending ? "Verifying..." : "✓ Mark Complete"}
                </button>
              </div>
            </div>
          ) : null}

          {areTaskControlsArmed && !activeTaskContext?.taskName ? (
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
            {(() => {
              const GUIDANCE_SOURCES = new Set([
                "demo_mode",
                "operator_guidance",
                "session_guidance",
                "verification_flow",
                "recovery_ladder",
              ]);
              const spokenEntries = transcriptLayer.entries.filter(
                (entry) => !GUIDANCE_SOURCES.has(entry.source),
              );
              return spokenEntries.length > 0 ? (
                spokenEntries.map((entry) => (
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
            );
            })()}
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

          <details className="rehearsal-details">
            <summary>Open detailed rehearsal checks</summary>
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
          </details>
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
          {containmentScore !== null ? (
            <article className="case-report-summary containment-score-section">
              <p className="case-report-summary-label">Containment Effectiveness</p>
              <div className="containment-score-row">
                <div className="containment-score-bar-track">
                  <div
                    className={`containment-score-bar-fill containment-score-bar-fill-${containmentScore >= 80 ? "high" : containmentScore >= 50 ? "mid" : "low"}`}
                    style={{ width: `${containmentScore}%` }}
                  />
                </div>
                <span className="containment-score-value">{containmentScore}%</span>
              </div>
              {callStartTime !== null ? (
                <p className="containment-score-timer">Duration: {formatTimer(elapsedSeconds)}</p>
              ) : null}
            </article>
          ) : null}

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

          <button
            type="button"
            className="secondary-button share-report-button"
            onClick={() => { void handleShareReport(); }}
          >
            📋 Share Containment Report
          </button>

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





































































































