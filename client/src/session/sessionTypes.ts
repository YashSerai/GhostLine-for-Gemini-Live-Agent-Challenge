export const CLIENT_SESSION_MESSAGE_TYPES = [
  "client_connect",
  "mic_status",
  "camera_status",
  "transcript",
  "frame",
  "verify_request",
  "swap_request",
  "pause",
  "stop",
] as const;

export type ClientSessionMessageType =
  (typeof CLIENT_SESSION_MESSAGE_TYPES)[number];

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
