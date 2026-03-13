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

function getDefaultManagerOptions(): WebSocketSessionManagerOptions {
  return {
    url: import.meta.env.VITE_SESSION_WS_URL ?? DEFAULT_SESSION_WS_URL,
  };
}

export function useSessionWebSocket() {
  const managerRef = useRef<WebSocketSessionManager | null>(null);

  if (managerRef.current === null) {
    managerRef.current = new WebSocketSessionManager(getDefaultManagerOptions());
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

  return {
    ...snapshot,
    connect,
    disconnect,
    manager,
    subscribeToEnvelopes,
    sendEnvelope,
    sendMessage,
    sessionUrl: getDefaultManagerOptions().url,
  };
}
