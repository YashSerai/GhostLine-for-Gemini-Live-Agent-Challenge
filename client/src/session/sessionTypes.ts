export const CLIENT_SESSION_MESSAGE_TYPES = [
  "client_connect",
  "mic_status",
  "audio_chunk",
  "camera_status",
  "calibration_status",
  "transcript",
  "frame",
  "room_scan_frame",
  "task_vision_frame",
  "verify_request",
  "swap_request",
  "pause",
  "stop",
] as const;

export const SERVER_SESSION_MESSAGE_TYPES = [
  "case_report",
  "error",
  "operator_audio_chunk",
  "operator_interruption",
  "swap_request",
  "transcript",
  "verification_state",
  "verification_result",
  "session_state",
] as const;

export type ClientSessionMessageType =
  (typeof CLIENT_SESSION_MESSAGE_TYPES)[number];

export type ServerSessionMessageType =
  (typeof SERVER_SESSION_MESSAGE_TYPES)[number];

export type SessionConnectionStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "disconnected"
  | "error";

export interface SessionEnvelope<T extends string = string> {
  type: T;
  payload: Record<string, unknown>;
  requestId?: string;
  clientTimestamp?: string;
  sessionId?: string;
}

export interface TransportLogEntry {
  direction: "sent" | "received";
  envelope: SessionEnvelope<string>;
  timestamp: string;
}

export interface SessionManagerSnapshot {
  status: SessionConnectionStatus;
  sessionId: string | null;
  reconnectAttempt: number;
  lastError: string | null;
  recentMessages: readonly TransportLogEntry[];
}

export type SessionEnvelopeListener = (
  envelope: SessionEnvelope<string>,
) => void;

