import { useEffect, useRef, useState } from "react";

import type {
  SessionConnectionStatus,
  SessionEnvelope,
  SessionEnvelopeListener,
} from "../session/sessionTypes";

type TaskControlMessageType = "verify_request" | "swap_request" | "pause" | "stop";
type TaskControlNoticeTone = "pending" | "ready" | "warning";

export interface TaskControlNotice {
  body: string;
  title: string;
  tone: TaskControlNoticeTone;
}

export interface TaskControlState {
  endSessionPending: boolean;
  lastNotice: TaskControlNotice | null;
  pausePending: boolean;
  readyToVerifyPending: boolean;
  requestEndSession: () => boolean;
  requestPauseSession: () => boolean;
  requestReadyToVerify: () => boolean;
  requestSwapTask: () => boolean;
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

function createAcceptedNotice(messageType: TaskControlMessageType): TaskControlNotice {
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
      return {
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

function createQueuedNotice(messageType: TaskControlMessageType): TaskControlNotice {
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
      return {
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

function createSendFailureNotice(messageType: TaskControlMessageType): TaskControlNotice {
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

export function useTaskControls(
  options: UseTaskControlsOptions,
): TaskControlState {
  const { connectionStatus, sendEnvelope, subscribeToEnvelopes } = options;
  const pendingRequestsRef = useRef(new Map<string, TaskControlMessageType>());
  const [pending, setPending] = useState<PendingTaskControlState>(
    IDLE_PENDING_STATE,
  );
  const [lastNotice, setLastNotice] = useState<TaskControlNotice | null>(null);

  useEffect(() => {
    if (connectionStatus === "connecting") {
      setLastNotice(null);
    }

    if (connectionStatus === "disconnected" || connectionStatus === "error") {
      pendingRequestsRef.current.clear();
      setPending(IDLE_PENDING_STATE);
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
        setLastNotice(createAcceptedNotice(messageType));
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
      setLastNotice(createSendFailureNotice(messageType));
      return false;
    }

    pendingRequestsRef.current.set(envelope.requestId as string, messageType);
    setPending((current) => setPendingFlag(current, messageType, true));
    setLastNotice(createQueuedNotice(messageType));
    return true;
  }

  function requestReadyToVerify(): boolean {
    return sendTaskControl("verify_request", {
      action: "ready_to_verify",
      source: "control_bar",
      trigger: "button",
    });
  }

  function requestSwapTask(): boolean {
    return sendTaskControl("swap_request", {
      action: "swap_task",
      reason: "cant_do_this",
      source: "control_bar",
      trigger: "button",
    });
  }

  function requestPauseSession(): boolean {
    return sendTaskControl("pause", {
      action: "pause_session",
      paused: true,
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
    endSessionPending: pending.stop,
    lastNotice,
    pausePending: pending.pause,
    readyToVerifyPending: pending.verify_request,
    requestEndSession,
    requestPauseSession,
    requestReadyToVerify,
    requestSwapTask,
    swapPending: pending.swap_request,
  };
}



