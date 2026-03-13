import { useEffect, useRef, useState } from "react";

import type {
  SessionConnectionStatus,
  SessionEnvelope,
  SessionEnvelopeListener,
} from "../session/sessionTypes";
import type { VerificationTaskContext } from "../verification/useReadyToVerifyFlow";

type TaskControlMessageType = "verify_request" | "swap_request" | "pause" | "stop";
type TaskControlNoticeTone = "pending" | "ready" | "warning";
type PauseActionMode = "pause" | "resume";
type SwapOutcomeStatus = "clarifying_question" | "substituted" | "partial_handling";

export interface TaskControlNotice {
  body: string;
  title: string;
  tone: TaskControlNoticeTone;
}

export interface TaskControlState {
  activeTaskContext: VerificationTaskContext | null;
  endSessionPending: boolean;
  lastNotice: TaskControlNotice | null;
  pausePending: boolean;
  readyToVerifyPending: boolean;
  requestEndSession: () => boolean;
  requestPauseSession: (paused?: boolean) => boolean;
  requestReadyToVerify: (options?: {
    taskContext?: VerificationTaskContext | null;
  }) => boolean;
  requestSwapTask: (options?: {
    taskContext?: VerificationTaskContext | null;
  }) => boolean;
  swapCount: number;
  swapLimit: number | null;
  swapOperatorLine: string | null;
  swapPending: boolean;
}

interface UseTaskControlsOptions {
  connectionStatus: SessionConnectionStatus;
  sendEnvelope: <T extends TaskControlMessageType>(
    envelope: SessionEnvelope<T>,
  ) => boolean;
  subscribeToEnvelopes: (listener: SessionEnvelopeListener) => () => void;
}

interface PendingTaskControlState {
  pause: boolean;
  stop: boolean;
  swap_request: boolean;
  verify_request: boolean;
}

interface SwapOutcomePayload {
  clarifyingQuestion: string | null;
  operatorLine: string | null;
  status: SwapOutcomeStatus;
  substituteTaskName: string | null;
  swapCount: number;
  swapLimit: number | null;
  taskContext: VerificationTaskContext | null;
}

const IDLE_PENDING_STATE: PendingTaskControlState = {
  pause: false,
  stop: false,
  swap_request: false,
  verify_request: false,
};

function createRequestId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `control-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
}

function createAcceptedNotice(
  messageType: TaskControlMessageType,
  pauseAction: PauseActionMode = "pause",
): TaskControlNotice {
  switch (messageType) {
    case "verify_request":
      return {
        title: "Ready to Verify Sent",
        body: "The backend accepted the verification request envelope.",
        tone: "ready",
      };
    case "swap_request":
      return {
        title: "Swap Request Sent",
        body: "The backend accepted the substitute-task request.",
        tone: "ready",
      };
    case "pause":
      return pauseAction === "resume"
        ? {
            title: "Resume Request Sent",
            body: "The backend accepted the resume envelope.",
            tone: "ready",
          }
        : {
            title: "Pause Request Sent",
            body: "The backend accepted the pause envelope.",
            tone: "ready",
          };
    case "stop":
      return {
        title: "End Session Sent",
        body: "The backend accepted the end-session envelope. The hotline transport should close next.",
        tone: "ready",
      };
    default:
      return {
        title: "Control Sent",
        body: "The backend accepted the control envelope.",
        tone: "ready",
      };
  }
}

function createQueuedNotice(
  messageType: TaskControlMessageType,
  pauseAction: PauseActionMode = "pause",
): TaskControlNotice {
  switch (messageType) {
    case "verify_request":
      return {
        title: "Sending Verification Request",
        body: "Ready to Verify is being sent to the backend now.",
        tone: "pending",
      };
    case "swap_request":
      return {
        title: "Sending Swap Request",
        body: "The substitute-task request is being sent to the backend now.",
        tone: "pending",
      };
    case "pause":
      return pauseAction === "resume"
        ? {
            title: "Sending Resume Request",
            body: "The resume request is being sent to the backend now.",
            tone: "pending",
          }
        : {
            title: "Sending Pause Request",
            body: "The pause request is being sent to the backend now.",
            tone: "pending",
          };
    case "stop":
      return {
        title: "Ending Session",
        body: "The end-session request is being sent to the backend now.",
        tone: "pending",
      };
    default:
      return {
        title: "Sending Control",
        body: "The control envelope is being sent to the backend now.",
        tone: "pending",
      };
  }
}

function createBlockedNotice(): TaskControlNotice {
  return {
    title: "Control Unavailable",
    body: "Task controls only send once the hotline WebSocket is fully connected.",
    tone: "warning",
  };
}

function createSendFailureNotice(
  messageType: TaskControlMessageType,
  pauseAction: PauseActionMode = "pause",
): TaskControlNotice {
  if (messageType === "pause" && pauseAction === "resume") {
    return {
      title: "Resume Not Sent",
      body: "The session could not be resumed because the transport was not ready.",
      tone: "warning",
    };
  }

  return {
    title: "Control Not Sent",
    body:
      messageType === "stop"
        ? "The session could not be ended because the transport was not ready to send the stop envelope."
        : "The control envelope could not be sent because the transport was not ready.",
    tone: "warning",
  };
}

function createServerErrorNotice(detail: string): TaskControlNotice {
  return {
    title: "Control Rejected",
    body: detail,
    tone: "warning",
  };
}

function formatVoiceSwapReason(reason: unknown): string {
  switch (reason) {
    case "missing_paper":
      return "missing paper";
    case "missing_door_or_threshold":
      return "no usable door or threshold";
    case "missing_required_object":
      return "a required object is missing";
    case "cannot_perform_task":
      return "the user said they cannot do the task";
    case "alternative_requested":
      return "the user asked for another option";
    default:
      return "a swap phrase was detected";
  }
}

function createVoiceSwapDetectedNotice(
  payload: Record<string, unknown>,
): TaskControlNotice {
  const snippet =
    typeof payload.rawTranscriptSnippet === "string" &&
    payload.rawTranscriptSnippet.trim().length > 0
      ? payload.rawTranscriptSnippet.trim()
      : "A live transcript line";

  return {
    title: "Voice Swap Detected",
    body: `${snippet} triggered a structured swap request because ${formatVoiceSwapReason(payload.inferredReason)}.`,
    tone: "warning",
  };
}

function setPendingFlag(
  current: PendingTaskControlState,
  messageType: TaskControlMessageType,
  value: boolean,
): PendingTaskControlState {
  return {
    ...current,
    [messageType]: value,
  };
}

function parseTaskContext(value: unknown): VerificationTaskContext | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return null;
  }

  return value as VerificationTaskContext;
}

function parseSwapOutcomePayload(
  payload: Record<string, unknown>,
): SwapOutcomePayload | null {
  const status = payload.status;
  if (
    status !== "clarifying_question" &&
    status !== "substituted" &&
    status !== "partial_handling"
  ) {
    return null;
  }

  const swapCount =
    typeof payload.swapCount === "number" && Number.isFinite(payload.swapCount)
      ? Math.trunc(payload.swapCount)
      : 0;
  const swapLimit =
    typeof payload.swapLimit === "number" && Number.isFinite(payload.swapLimit)
      ? Math.trunc(payload.swapLimit)
      : null;
  const substituteTaskValue = payload.substituteTask;
  const substituteTaskName =
    typeof substituteTaskValue === "object" &&
    substituteTaskValue !== null &&
    !Array.isArray(substituteTaskValue) &&
    typeof (substituteTaskValue as Record<string, unknown>).taskName === "string"
      ? ((substituteTaskValue as Record<string, unknown>).taskName as string)
      : null;

  return {
    clarifyingQuestion:
      typeof payload.clarifyingQuestion === "string" &&
      payload.clarifyingQuestion.trim().length > 0
        ? payload.clarifyingQuestion.trim()
        : null,
    operatorLine:
      typeof payload.operatorLine === "string" && payload.operatorLine.trim().length > 0
        ? payload.operatorLine.trim()
        : null,
    status,
    substituteTaskName,
    swapCount,
    swapLimit,
    taskContext: parseTaskContext(payload.taskContext),
  };
}

function createSwapOutcomeNotice(payload: SwapOutcomePayload): TaskControlNotice {
  if (payload.status === "clarifying_question") {
    return {
      title: "Clarification Needed",
      body:
        payload.clarifyingQuestion ??
        payload.operatorLine ??
        "The backend needs one clarifying detail before it can place a substitute task.",
      tone: "pending",
    };
  }

  if (payload.status === "substituted") {
    return {
      title: "Task Substituted",
      body:
        payload.operatorLine ??
        (payload.substituteTaskName
          ? `The backend routed the case to ${payload.substituteTaskName}.`
          : "The backend selected a substitute task."),
      tone: "ready",
    };
  }

  return {
    title: "Constraint Logged",
    body:
      payload.operatorLine ??
      "The backend logged the capability constraint and kept the case moving with partial handling.",
    tone: "warning",
  };
}

export function useTaskControls(
  options: UseTaskControlsOptions,
): TaskControlState {
  const { connectionStatus, sendEnvelope, subscribeToEnvelopes } = options;
  const pendingRequestsRef = useRef(new Map<string, TaskControlMessageType>());
  const pauseActionRef = useRef<PauseActionMode>("pause");
  const [pending, setPending] = useState<PendingTaskControlState>(
    IDLE_PENDING_STATE,
  );
  const [lastNotice, setLastNotice] = useState<TaskControlNotice | null>(null);
  const [activeTaskContext, setActiveTaskContext] =
    useState<VerificationTaskContext | null>(null);
  const [swapCount, setSwapCount] = useState(0);
  const [swapLimit, setSwapLimit] = useState<number | null>(null);
  const [swapOperatorLine, setSwapOperatorLine] = useState<string | null>(null);

  useEffect(() => {
    if (connectionStatus === "connecting") {
      setLastNotice(null);
    }

    if (connectionStatus === "disconnected" || connectionStatus === "error") {
      pendingRequestsRef.current.clear();
      pauseActionRef.current = "pause";
      setPending(IDLE_PENDING_STATE);
      setActiveTaskContext(null);
      setSwapCount(0);
      setSwapLimit(null);
      setSwapOperatorLine(null);
    }
  }, [connectionStatus]);

  useEffect(() => {
    return subscribeToEnvelopes((envelope) => {
      const requestId = envelope.requestId;
      const payloadStatus = envelope.payload.status;

      if (
        envelope.type === "swap_request" &&
        envelope.requestId === undefined &&
        envelope.payload.source === "voice_intent" &&
        payloadStatus === "detected"
      ) {
        setLastNotice(createVoiceSwapDetectedNotice(envelope.payload));
        return;
      }

      if (envelope.type === "swap_request") {
        const swapOutcome = parseSwapOutcomePayload(envelope.payload);
        if (swapOutcome !== null) {
          setSwapCount(swapOutcome.swapCount);
          setSwapLimit(swapOutcome.swapLimit);
          setSwapOperatorLine(swapOutcome.operatorLine);
          if (swapOutcome.taskContext !== null) {
            setActiveTaskContext(swapOutcome.taskContext);
          }
          setLastNotice(createSwapOutcomeNotice(swapOutcome));
        }
      }

      if (envelope.type === "error") {
        if (pendingRequestsRef.current.size > 0) {
          pendingRequestsRef.current.clear();
          setPending(IDLE_PENDING_STATE);
        }

        const detail =
          typeof envelope.payload.detail === "string"
            ? envelope.payload.detail
            : "The backend rejected the task control request.";
        setLastNotice(createServerErrorNotice(detail));
        return;
      }

      if (
        typeof requestId !== "string" ||
        !pendingRequestsRef.current.has(requestId)
      ) {
        return;
      }

      const messageType = pendingRequestsRef.current.get(requestId);
      if (!messageType || envelope.type !== messageType) {
        return;
      }

      pendingRequestsRef.current.delete(requestId);
      setPending((current) => setPendingFlag(current, messageType, false));

      if (payloadStatus === "accepted") {
        if (messageType === "swap_request") {
          return;
        }
        setLastNotice(
          createAcceptedNotice(
            messageType,
            messageType === "pause" ? pauseActionRef.current : "pause",
          ),
        );
      }
    });
  }, [subscribeToEnvelopes]);

  function sendTaskControl(
    messageType: TaskControlMessageType,
    payload: Record<string, unknown>,
  ): boolean {
    if (connectionStatus !== "connected") {
      setLastNotice(createBlockedNotice());
      return false;
    }

    if (pending[messageType]) {
      return false;
    }

    const envelope: SessionEnvelope<TaskControlMessageType> = {
      type: messageType,
      payload,
      requestId: createRequestId(),
      clientTimestamp: new Date().toISOString(),
    };

    const didSend = sendEnvelope(envelope);
    if (!didSend) {
      setLastNotice(
        createSendFailureNotice(
          messageType,
          messageType === "pause" ? pauseActionRef.current : "pause",
        ),
      );
      return false;
    }

    pendingRequestsRef.current.set(envelope.requestId as string, messageType);
    setPending((current) => setPendingFlag(current, messageType, true));
    setLastNotice(
      createQueuedNotice(
        messageType,
        messageType === "pause" ? pauseActionRef.current : "pause",
      ),
    );
    return true;
  }

  function requestReadyToVerify(options?: {
    taskContext?: VerificationTaskContext | null;
  }): boolean {
    return sendTaskControl("verify_request", {
      action: "ready_to_verify",
      source: "control_bar",
      trigger: "button",
      taskContext: options?.taskContext ?? activeTaskContext,
    });
  }

  function requestSwapTask(options?: {
    taskContext?: VerificationTaskContext | null;
  }): boolean {
    return sendTaskControl("swap_request", {
      action: "swap_task",
      reason: "cant_do_this",
      source: "control_bar",
      trigger: "button",
      taskContext: options?.taskContext ?? activeTaskContext,
    });
  }

  function requestPauseSession(paused = true): boolean {
    pauseActionRef.current = paused ? "pause" : "resume";
    return sendTaskControl("pause", {
      action: paused ? "pause_session" : "resume_session",
      paused,
      source: "control_bar",
      trigger: "button",
    });
  }

  function requestEndSession(): boolean {
    return sendTaskControl("stop", {
      action: "end_session",
      reason: "user_requested_end",
      source: "control_bar",
      trigger: "button",
    });
  }

  return {
    activeTaskContext,
    endSessionPending: pending.stop,
    lastNotice,
    pausePending: pending.pause,
    readyToVerifyPending: pending.verify_request,
    requestEndSession,
    requestPauseSession,
    requestReadyToVerify,
    requestSwapTask,
    swapCount,
    swapLimit,
    swapOperatorLine,
    swapPending: pending.swap_request,
  };
}
