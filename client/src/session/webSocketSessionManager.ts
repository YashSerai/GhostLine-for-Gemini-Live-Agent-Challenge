import {
  type ClientSessionMessageType,
  type SessionEnvelope,
  type SessionEnvelopeListener,
  type SessionManagerSnapshot,
  type TransportLogEntry,
} from "./sessionTypes";

const DEFAULT_RECONNECT_DELAYS_MS = [1000, 2000, 4000] as const;
const DEFAULT_MAX_RECONNECT_ATTEMPTS = 3;
const MAX_TRANSPORT_LOG_ENTRIES = 6;
const NON_LOGGED_TRANSPORT_TYPES = new Set(["audio_chunk", "operator_audio_chunk", "transcript"]);

type SnapshotListener = (snapshot: SessionManagerSnapshot) => void;

export interface WebSocketSessionManagerOptions {
  url: string;
  reconnectDelaysMs?: readonly number[];
  maxReconnectAttempts?: number;
}

function createRequestId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `client-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
}

function isObjectRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function shouldRecordEnvelopeType(type: string): boolean {
  return !NON_LOGGED_TRANSPORT_TYPES.has(type);
}

function normalizeIncomingEnvelope(raw: unknown): SessionEnvelope<string> {
  if (!isObjectRecord(raw)) {
    throw new Error("Server message must be a JSON object.");
  }

  const { type, payload, requestId, clientTimestamp, sessionId } = raw;
  if (typeof type !== "string" || type.length === 0) {
    throw new Error("Server message type must be a non-empty string.");
  }

  if (!isObjectRecord(payload)) {
    throw new Error("Server message payload must be a JSON object.");
  }

  return {
    type,
    payload,
    requestId: typeof requestId === "string" ? requestId : undefined,
    clientTimestamp:
      typeof clientTimestamp === "string" ? clientTimestamp : undefined,
    sessionId: typeof sessionId === "string" ? sessionId : undefined,
  };
}

function createClientEnvelope<T extends ClientSessionMessageType>(
  type: T,
  payload: Record<string, unknown> = {},
): SessionEnvelope<T> {
  return {
    type,
    payload,
    requestId: createRequestId(),
    clientTimestamp: new Date().toISOString(),
  };
}

export class WebSocketSessionManager {
  private readonly url: string;
  private readonly reconnectDelaysMs: readonly number[];
  private readonly maxReconnectAttempts: number;
  private readonly listeners = new Set<SnapshotListener>();
  private readonly envelopeListeners = new Set<SessionEnvelopeListener>();

  private socket: WebSocket | null = null;
  private reconnectTimer: number | null = null;
  private socketToken = 0;
  private manualDisconnect = false;

  private snapshot: SessionManagerSnapshot = {
    status: "idle",
    sessionId: null,
    reconnectAttempt: 0,
    lastError: null,
    recentMessages: [],
  };

  constructor(options: WebSocketSessionManagerOptions) {
    this.url = options.url;
    this.reconnectDelaysMs =
      options.reconnectDelaysMs ?? DEFAULT_RECONNECT_DELAYS_MS;
    this.maxReconnectAttempts =
      options.maxReconnectAttempts ?? DEFAULT_MAX_RECONNECT_ATTEMPTS;
  }

  subscribe(listener: SnapshotListener): () => void {
    this.listeners.add(listener);
    listener(this.snapshot);

    return () => {
      this.listeners.delete(listener);
    };
  }

  subscribeToEnvelopes(listener: SessionEnvelopeListener): () => void {
    this.envelopeListeners.add(listener);

    return () => {
      this.envelopeListeners.delete(listener);
    };
  }

  getSnapshot(): SessionManagerSnapshot {
    return this.snapshot;
  }

  connect(): void {
    if (this.socket !== null) {
      const state = this.socket.readyState;
      if (state === WebSocket.CONNECTING || state === WebSocket.OPEN) {
        return;
      }
    }

    this.manualDisconnect = false;
    this.clearReconnectTimer();
    this.openSocket(this.snapshot.reconnectAttempt > 0);
  }

  disconnect(): void {
    this.manualDisconnect = true;
    this.clearReconnectTimer();
    this.socketToken += 1;

    const activeSocket = this.socket;
    this.socket = null;

    if (
      activeSocket !== null &&
      activeSocket.readyState !== WebSocket.CLOSED &&
      activeSocket.readyState !== WebSocket.CLOSING
    ) {
      activeSocket.close(1000, "client disconnect");
    }

    this.updateSnapshot({
      status: "disconnected",
      sessionId: null,
      reconnectAttempt: 0,
      lastError: null,
    });
  }

  sendEnvelope<T extends ClientSessionMessageType>(
    envelope: SessionEnvelope<T>,
  ): boolean {
    const socket = this.socket;
    if (socket === null || socket.readyState !== WebSocket.OPEN) {
      this.updateSnapshot({
        lastError: "Cannot send transport messages before the socket is connected.",
      });
      return false;
    }

    const normalizedEnvelope: SessionEnvelope<T> = {
      ...envelope,
      requestId: envelope.requestId ?? createRequestId(),
      clientTimestamp: envelope.clientTimestamp ?? new Date().toISOString(),
    };

    if (normalizedEnvelope.type === "stop") {
      this.manualDisconnect = true;
      this.clearReconnectTimer();
    }

    socket.send(JSON.stringify(normalizedEnvelope));
    if (shouldRecordEnvelopeType(normalizedEnvelope.type)) {
      this.recordTransport("sent", normalizedEnvelope);
    }
    return true;
  }

  sendMessage<T extends ClientSessionMessageType>(
    type: T,
    payload: Record<string, unknown> = {},
  ): boolean {
    return this.sendEnvelope(createClientEnvelope(type, payload));
  }

  private emitSnapshot(): void {
    this.listeners.forEach((listener) => listener(this.snapshot));
  }

  private emitEnvelope(envelope: SessionEnvelope<string>): void {
    this.envelopeListeners.forEach((listener) => listener(envelope));
  }

  private updateSnapshot(patch: Partial<SessionManagerSnapshot>): void {
    this.snapshot = {
      ...this.snapshot,
      ...patch,
    };
    this.emitSnapshot();
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private isCurrentSocket(socket: WebSocket, token: number): boolean {
    return this.socket === socket && this.socketToken === token;
  }

  private openSocket(isReconnect: boolean): void {
    const socket = new WebSocket(this.url);
    const token = ++this.socketToken;

    this.socket = socket;
    this.updateSnapshot({
      status: isReconnect ? "reconnecting" : "connecting",
      sessionId: null,
      lastError: null,
    });

    socket.onopen = () => {
      if (!this.isCurrentSocket(socket, token)) {
        return;
      }

      this.updateSnapshot({
        status: "connected",
        reconnectAttempt: 0,
        lastError: null,
      });

      this.sendMessage("client_connect", {
        client: "ghostline-web",
        transport: "websocket",
      });
    };

    socket.onerror = () => {
      if (!this.isCurrentSocket(socket, token)) {
        return;
      }

      this.updateSnapshot({
        lastError: "WebSocket transport error.",
      });
    };

    socket.onmessage = (event) => {
      void this.handleMessageEvent(event.data, socket, token);
    };

    socket.onclose = (event) => {
      if (!this.isCurrentSocket(socket, token)) {
        return;
      }

      this.socket = null;

      if (this.manualDisconnect) {
        this.updateSnapshot({
          status: "disconnected",
          reconnectAttempt: 0,
          sessionId: null,
          lastError: null,
        });
        return;
      }

      const reason = event.reason || `Socket closed with code ${event.code}.`;
      this.scheduleReconnect(reason);
    };
  }

  private async handleMessageEvent(
    messageData: string | ArrayBuffer | Blob,
    socket: WebSocket,
    token: number,
  ): Promise<void> {
    if (!this.isCurrentSocket(socket, token)) {
      return;
    }

    try {
      const rawText = await this.normalizeMessageData(messageData);
      const parsedEnvelope = normalizeIncomingEnvelope(JSON.parse(rawText));

      if (shouldRecordEnvelopeType(parsedEnvelope.type)) {
        this.recordTransport("received", parsedEnvelope);
      }

      if (parsedEnvelope.sessionId) {
        this.updateSnapshot({ sessionId: parsedEnvelope.sessionId });
      }

      if (parsedEnvelope.type === "error") {
        const detail =
          typeof parsedEnvelope.payload.detail === "string"
            ? parsedEnvelope.payload.detail
            : "Server returned an error envelope.";
        this.updateSnapshot({ lastError: detail });
      }

      this.emitEnvelope(parsedEnvelope);
    } catch (error) {
      const detail =
        error instanceof Error ? error.message : "Invalid server envelope.";
      this.updateSnapshot({ lastError: detail });
    }
  }

  private async normalizeMessageData(
    messageData: string | ArrayBuffer | Blob,
  ): Promise<string> {
    if (typeof messageData === "string") {
      return messageData;
    }

    if (messageData instanceof Blob) {
      return messageData.text();
    }

    if (messageData instanceof ArrayBuffer) {
      return new TextDecoder().decode(messageData);
    }

    throw new Error("Unsupported WebSocket message format.");
  }

  private scheduleReconnect(reason: string): void {
    const nextAttempt = this.snapshot.reconnectAttempt + 1;
    if (nextAttempt > this.maxReconnectAttempts) {
      this.updateSnapshot({
        status: "error",
        reconnectAttempt: this.maxReconnectAttempts,
        lastError: reason,
      });
      return;
    }

    const delayIndex = Math.min(
      nextAttempt - 1,
      this.reconnectDelaysMs.length - 1,
    );
    const delay =
      this.reconnectDelaysMs[delayIndex] ?? DEFAULT_RECONNECT_DELAYS_MS[0];

    this.updateSnapshot({
      status: "reconnecting",
      reconnectAttempt: nextAttempt,
      lastError: reason,
    });

    this.clearReconnectTimer();
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      if (this.manualDisconnect) {
        return;
      }

      this.openSocket(true);
    }, delay);
  }

  private recordTransport(
    direction: TransportLogEntry["direction"],
    envelope: SessionEnvelope<string>,
  ): void {
    const nextEntry: TransportLogEntry = {
      direction,
      envelope,
      timestamp: new Date().toISOString(),
    };

    this.updateSnapshot({
      recentMessages: [nextEntry, ...this.snapshot.recentMessages].slice(
        0,
        MAX_TRANSPORT_LOG_ENTRIES,
      ),
    });
  }
}


