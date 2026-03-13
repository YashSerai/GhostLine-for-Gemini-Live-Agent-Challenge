import { useEffect, useRef, useState } from "react";

import type { CapturedFrame } from "../media/frameCapture";
import type { CameraCaptureType } from "../media/useCameraPreview";
import type {
  ClientSessionMessageType,
  SessionConnectionStatus,
  SessionEnvelopeListener,
} from "../session/sessionTypes";
import { captureVerificationWindow } from "./captureVerificationWindow";

export type ReadyToVerifyPhase =
  | "idle"
  | "pending"
  | "capturing_window"
  | "uploading_frames"
  | "captured";

export interface VerificationTaskContext {
  contextLabel?: string;
  contextStatus?: string;
  pathMode?: string | null;
  protocolStep?: string | null;
  taskId?: string | null;
  taskName?: string | null;
  taskRoleCategory?: string | null;
  taskTier?: number | string | null;
  verificationClass?: string | null;
}

export interface ReadyToVerifyState {
  attemptId: string | null;
  error: string | null;
  expectedFrames: number;
  holdStillSeconds: number;
  isBusy: boolean;
  localCapturedFrames: number;
  operatorLine: string | null;
  phase: ReadyToVerifyPhase;
  receivedFrames: number;
  source: string | null;
  taskContext: VerificationTaskContext | null;
}

interface UseReadyToVerifyFlowOptions {
  cameraReady: boolean;
  captureFrame: (captureType: CameraCaptureType) => Promise<CapturedFrame | null>;
  connectionStatus: SessionConnectionStatus;
  sendMessage: <T extends ClientSessionMessageType>(
    type: T,
    payload?: Record<string, unknown>,
  ) => boolean;
  subscribeToEnvelopes: (listener: SessionEnvelopeListener) => () => void;
}

interface VerificationStateEnvelopePayload {
  attemptId: string;
  captureWindowMs: number;
  expectedFrames: number;
  holdStillSeconds: number;
  rawTranscriptSnippet: string | null;
  receivedFrames: number;
  source: string | null;
  startedAt: string | null;
  status: "pending" | "captured" | "cancelled";
  taskContext: VerificationTaskContext | null;
}

const IDLE_STATE: ReadyToVerifyState = {
  attemptId: null,
  error: null,
  expectedFrames: 0,
  holdStillSeconds: 1,
  isBusy: false,
  localCapturedFrames: 0,
  operatorLine: null,
  phase: "idle",
  receivedFrames: 0,
  source: null,
  taskContext: null,
};

function parseVerificationStatePayload(
  payload: Record<string, unknown>,
): VerificationStateEnvelopePayload | null {
  const attemptId = payload.attemptId;
  const captureWindowMs = payload.captureWindowMs;
  const expectedFrames = payload.expectedFrames;
  const holdStillSeconds = payload.holdStillSeconds;
  const receivedFrames = payload.receivedFrames;
  const status = payload.status;

  if (
    typeof attemptId !== "string" ||
    typeof captureWindowMs !== "number" ||
    typeof expectedFrames !== "number" ||
    typeof holdStillSeconds !== "number" ||
    typeof receivedFrames !== "number" ||
    (status !== "pending" && status !== "captured" && status !== "cancelled")
  ) {
    return null;
  }

  return {
    attemptId,
    captureWindowMs,
    expectedFrames,
    holdStillSeconds,
    rawTranscriptSnippet:
      typeof payload.rawTranscriptSnippet === "string"
        ? payload.rawTranscriptSnippet
        : null,
    receivedFrames,
    source: typeof payload.source === "string" ? payload.source : null,
    startedAt: typeof payload.startedAt === "string" ? payload.startedAt : null,
    status,
    taskContext:
      typeof payload.taskContext === "object" &&
      payload.taskContext !== null &&
      !Array.isArray(payload.taskContext)
        ? (payload.taskContext as VerificationTaskContext)
        : null,
  };
}

function buildOperatorLine(
  phase: ReadyToVerifyPhase,
  holdStillSeconds: number,
): string | null {
  switch (phase) {
    case "pending":
    case "capturing_window":
      return holdStillSeconds === 1
        ? "Hold still for one second."
        : `Hold still for ${holdStillSeconds} seconds.`;
    case "uploading_frames":
      return "Verification window captured. Sending the staged frame window now.";
    case "captured":
      return "Verification window captured. Stand by.";
    default:
      return null;
  }
}

export function useReadyToVerifyFlow(
  options: UseReadyToVerifyFlowOptions,
): ReadyToVerifyState {
  const {
    cameraReady,
    captureFrame,
    connectionStatus,
    sendMessage,
    subscribeToEnvelopes,
  } = options;
  const [state, setState] = useState<ReadyToVerifyState>(IDLE_STATE);
  const cameraReadyRef = useRef(cameraReady);
  const captureFrameRef = useRef(captureFrame);
  const sendMessageRef = useRef(sendMessage);
  const activeAttemptRef = useRef<string | null>(null);
  const captureInFlightRef = useRef(false);

  useEffect(() => {
    cameraReadyRef.current = cameraReady;
  }, [cameraReady]);

  useEffect(() => {
    captureFrameRef.current = captureFrame;
  }, [captureFrame]);

  useEffect(() => {
    sendMessageRef.current = sendMessage;
  }, [sendMessage]);

  useEffect(() => {
    if (connectionStatus === "disconnected" || connectionStatus === "error") {
      activeAttemptRef.current = null;
      captureInFlightRef.current = false;
      setState(IDLE_STATE);
    }
  }, [connectionStatus]);

  useEffect(() => {
    return subscribeToEnvelopes((envelope) => {
      if (envelope.type !== "verification_state") {
        return;
      }

      const payload = parseVerificationStatePayload(envelope.payload);
      if (payload === null) {
        return;
      }

      if (payload.status === "cancelled") {
        activeAttemptRef.current = null;
        captureInFlightRef.current = false;
        setState(IDLE_STATE);
        return;
      }

      if (payload.status === "pending") {
        setState({
          attemptId: payload.attemptId,
          error: null,
          expectedFrames: payload.expectedFrames,
          holdStillSeconds: payload.holdStillSeconds,
          isBusy: true,
          localCapturedFrames: 0,
          operatorLine: buildOperatorLine("pending", payload.holdStillSeconds),
          phase: "pending",
          receivedFrames: payload.receivedFrames,
          source: payload.source,
          taskContext: payload.taskContext,
        });

        if (activeAttemptRef.current !== payload.attemptId && !captureInFlightRef.current) {
          activeAttemptRef.current = payload.attemptId;
          void runCaptureWindow(payload);
        }
        return;
      }

      activeAttemptRef.current = null;
      captureInFlightRef.current = false;
      setState({
        attemptId: payload.attemptId,
        error: null,
        expectedFrames: payload.expectedFrames,
        holdStillSeconds: payload.holdStillSeconds,
        isBusy: false,
        localCapturedFrames: payload.expectedFrames,
        operatorLine: buildOperatorLine("captured", payload.holdStillSeconds),
        phase: "captured",
        receivedFrames: payload.receivedFrames,
        source: payload.source,
        taskContext: payload.taskContext,
      });
    });
  }, [subscribeToEnvelopes]);

  async function runCaptureWindow(
    payload: VerificationStateEnvelopePayload,
  ): Promise<void> {
    if (!cameraReadyRef.current) {
      activeAttemptRef.current = null;
      setState((current) => ({
        ...current,
        error: "Camera preview must be live before Ready to Verify can capture a bounded frame window.",
        isBusy: false,
        operatorLine: "I can't verify that yet. The room feed is not live.",
        phase: "idle",
      }));
      return;
    }

    captureInFlightRef.current = true;
    setState((current) => ({
      ...current,
      error: null,
      isBusy: true,
      operatorLine: buildOperatorLine("capturing_window", payload.holdStillSeconds),
      phase: "capturing_window",
    }));

    try {
      const captureWindow = await captureVerificationWindow({
        captureFrame: captureFrameRef.current,
        frameCount: payload.expectedFrames,
        onFrameCaptured: (_frame, frameIndex) => {
          if (activeAttemptRef.current !== payload.attemptId) {
            return;
          }

          setState((current) => ({
            ...current,
            localCapturedFrames: frameIndex,
          }));
        },
        windowDurationMs: payload.captureWindowMs,
      });

      if (activeAttemptRef.current !== payload.attemptId) {
        captureInFlightRef.current = false;
        setState(IDLE_STATE);
        return;
      }

      setState((current) => ({
        ...current,
        operatorLine: buildOperatorLine("uploading_frames", payload.holdStillSeconds),
        phase: "uploading_frames",
      }));

      captureWindow.frames.forEach((frame, index) => {
        if (activeAttemptRef.current !== payload.attemptId) {
          return;
        }
        const didSend = sendMessageRef.current("frame", {
          verificationAttemptId: payload.attemptId,
          captureType: "ready_to_verify",
          captureWindowMs: payload.captureWindowMs,
          data: frame.data,
          capturedAt: frame.capturedAt,
          mimeType: frame.mimeType,
          qualityMetrics: captureWindow.qualityMetrics,
          sequence: index + 1,
          taskContext: payload.taskContext,
          totalFrames: captureWindow.frames.length,
          width: frame.width,
          height: frame.height,
        });

        if (!didSend) {
          throw new Error(
            "The verification window was captured, but a frame could not be sent to the backend.",
          );
        }
      });
    } catch (error) {
      activeAttemptRef.current = null;
      captureInFlightRef.current = false;
      setState((current) => ({
        ...current,
        error:
          error instanceof Error
            ? error.message
            : "Verification capture failed.",
        isBusy: false,
        operatorLine: "I can't verify that yet. The capture window failed.",
        phase: "idle",
      }));
      return;
    }
  }

  return state;
}

