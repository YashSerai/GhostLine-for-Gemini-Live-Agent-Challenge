import { useEffect, useRef, useState } from "react";

import {
  WebSocketSessionManager,
  type WebSocketSessionManagerOptions,
} from "./webSocketSessionManager";
import {
  type ClientSessionMessageType,
  type SessionEnvelope,
  type SessionEnvelopeListener,
  type SessionManagerSnapshot,
} from "./sessionTypes";

const DEFAULT_SESSION_WS_URL = "ws://127.0.0.1:8000/ws/session";

function parseDemoModeRouteFlag(): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  const params = new URLSearchParams(window.location.search);
  const rawValue = params.get("demo");
  if (rawValue === null) {
    return false;
  }

  const normalized = rawValue.trim().toLowerCase();
  return normalized === "1" || normalized === "true" || normalized === "yes" || normalized === "on";
}

function getDefaultManagerOptions(): WebSocketSessionManagerOptions {
  const demoModeRequested = parseDemoModeRouteFlag();
  return {
    url: import.meta.env.VITE_SESSION_WS_URL ?? DEFAULT_SESSION_WS_URL,
    clientConnectPayload: {
      demoMode: demoModeRequested,
    },
  };
}

export interface UseSessionWebSocketOptions {
  clientConnectPayload?: Record<string, unknown>;
}

export function useSessionWebSocket(options?: UseSessionWebSocketOptions) {
  const managerRef = useRef<WebSocketSessionManager | null>(null);

  if (managerRef.current === null) {
    const managerOptions = getDefaultManagerOptions();
    if (options?.clientConnectPayload) {
      managerOptions.clientConnectPayload = {
        ...managerOptions.clientConnectPayload,
        ...options.clientConnectPayload,
      };
    }
    managerRef.current = new WebSocketSessionManager(managerOptions);
  }

  const manager = managerRef.current;
  const [snapshot, setSnapshot] = useState<SessionManagerSnapshot>(
    manager.getSnapshot(),
  );

  useEffect(() => manager.subscribe(setSnapshot), [manager]);
  useEffect(() => () => manager.disconnect(), [manager]);

  const connect = () => manager.connect();
  const disconnect = () => manager.disconnect();
  const subscribeToEnvelopes = (listener: SessionEnvelopeListener) =>
    manager.subscribeToEnvelopes(listener);
  const sendEnvelope = <T extends ClientSessionMessageType>(
    envelope: SessionEnvelope<T>,
  ) => manager.sendEnvelope(envelope);
  const sendMessage = <T extends ClientSessionMessageType>(
    type: T,
    payload: Record<string, unknown> = {},
  ) => manager.sendMessage(type, payload);
  const updateClientConnectPayload = (payload: Record<string, unknown>) =>
    manager.updateClientConnectPayload(payload);

  const managerOptions = getDefaultManagerOptions();

  return {
    ...snapshot,
    connect,
    disconnect,
    manager,
    subscribeToEnvelopes,
    sendEnvelope,
    sendMessage,
    updateClientConnectPayload,
    demoModeRequested: Boolean(managerOptions.clientConnectPayload?.demoMode),
    sessionUrl: managerOptions.url,
  };
}
