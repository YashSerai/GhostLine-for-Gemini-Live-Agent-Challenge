import { useEffect, useRef, useState } from "react";

import { AudioCaptureController } from "./AudioCaptureController";
import type {
  ClientSessionMessageType,
  SessionConnectionStatus,
} from "../session/sessionTypes";

export type MicrophonePermissionState =
  | "idle"
  | "requesting"
  | "granted"
  | "denied";

export interface MicrophoneBridgeState {
  error: string | null;
  isStreaming: boolean;
  micChunkCount: number;
  permission: MicrophonePermissionState;
  startMicrophone: () => Promise<void>;
  stopMicrophone: (reason?: string) => Promise<void>;
}

interface UseMicrophoneBridgeOptions {
  connectionStatus: SessionConnectionStatus;
  sendMessage: <T extends ClientSessionMessageType>(
    type: T,
    payload?: Record<string, unknown>,
  ) => boolean;
}

export function useMicrophoneBridge(
  options: UseMicrophoneBridgeOptions,
): MicrophoneBridgeState {
  const { connectionStatus, sendMessage } = options;
  const streamRef = useRef<MediaStream | null>(null);
  const captureControllerRef = useRef<AudioCaptureController | null>(null);
  const connectionStatusRef = useRef(connectionStatus);
  const sendMessageRef = useRef(sendMessage);
  const permissionRef = useRef<MicrophonePermissionState>("idle");
  const isStreamingRef = useRef(false);

  const [permission, setPermission] =
    useState<MicrophonePermissionState>("idle");
  const [isStreaming, setIsStreaming] = useState(false);
  const [micChunkCount, setMicChunkCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    connectionStatusRef.current = connectionStatus;
  }, [connectionStatus]);

  useEffect(() => {
    sendMessageRef.current = sendMessage;
  }, [sendMessage]);

  useEffect(() => {
    permissionRef.current = permission;
  }, [permission]);

  useEffect(() => {
    isStreamingRef.current = isStreaming;
  }, [isStreaming]);

  useEffect(() => {
    if (connectionStatus === "disconnected" || connectionStatus === "error") {
      void stopMicrophoneInternal({
        notifyBackend: false,
        reason: "transport_closed",
        resetPermission: true,
      });
    }
  }, [connectionStatus]);

  useEffect(
    () => () => {
      void stopMicrophoneInternal({
        notifyBackend: false,
        reason: "component_unmounted",
        resetPermission: false,
      });
    },
    [],
  );

  async function startMicrophone(): Promise<void> {
    if (isStreamingRef.current) {
      return;
    }

    if (connectionStatusRef.current !== "connected") {
      setError(
        "The hotline transport must be connected before the microphone stream starts.",
      );
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      setPermission("denied");
      setError("This browser does not support microphone capture.");
      sendMessageRef.current("mic_status", {
        permission: "denied",
        reason: "unsupported_browser",
        streaming: false,
      });
      return;
    }

    setError(null);
    setPermission("requesting");
    sendMessageRef.current("mic_status", {
      permission: "requesting",
      reason: "permission_prompt",
      streaming: false,
    });

    let stream: MediaStream | null = null;

    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          autoGainControl: true,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
        video: false,
      });

      if (connectionStatusRef.current !== "connected") {
        stream.getTracks().forEach((track) => track.stop());
        setPermission("idle");
        setError("The hotline transport closed before the microphone stream could start.");
        return;
      }

      const controller = new AudioCaptureController({
        stream,
        onChunk: (chunk) => {
          if (connectionStatusRef.current !== "connected") {
            return;
          }

          const didSend = sendMessageRef.current("audio_chunk", {
            byteCount: chunk.byteCount,
            data: chunk.data,
            mimeType: chunk.mimeType,
            sampleCount: chunk.sampleCount,
            sequence: chunk.sequence,
          });

          if (didSend) {
            setMicChunkCount((count) => count + 1);
          }
        },
      });

      const startInfo = await controller.start();
      const didAnnounceStart = sendMessageRef.current("mic_status", {
        chunkDurationMs: startInfo.chunkDurationMs,
        deviceSampleRate: startInfo.deviceSampleRate,
        mimeType: startInfo.mimeType,
        permission: "granted",
        sampleRate: startInfo.sampleRate,
        streaming: true,
      });

      if (!didAnnounceStart) {
        await controller.stop();
        stream.getTracks().forEach((track) => track.stop());
        setPermission("idle");
        setError("The hotline transport closed before the microphone stream could be announced.");
        return;
      }

      streamRef.current = stream;
      captureControllerRef.current = controller;
      setPermission("granted");
      setIsStreaming(true);
      setMicChunkCount(0);
      setError(null);
    } catch (startError) {
      stream?.getTracks().forEach((track) => track.stop());
      const detail =
        startError instanceof Error
          ? startError.message
          : "Microphone permission was denied or the stream could not start.";
      setPermission("denied");
      setError(detail);
      setIsStreaming(false);

      sendMessageRef.current("mic_status", {
        permission: "denied",
        reason: "start_failed",
        streaming: false,
      });
    }
  }

  async function stopMicrophone(reason = "client_requested"): Promise<void> {
    await stopMicrophoneInternal({
      notifyBackend: true,
      reason,
      resetPermission: false,
    });
  }

  async function stopMicrophoneInternal(options: {
    notifyBackend: boolean;
    reason: string;
    resetPermission: boolean;
  }): Promise<void> {
    const { notifyBackend, reason, resetPermission } = options;

    if (captureControllerRef.current !== null) {
      await captureControllerRef.current.stop();
      captureControllerRef.current = null;
    }

    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;

    if (
      notifyBackend &&
      connectionStatusRef.current === "connected" &&
      (isStreamingRef.current || permissionRef.current !== "idle")
    ) {
      sendMessageRef.current("mic_status", {
        permission: resetPermission ? "idle" : permissionRef.current,
        reason,
        streaming: false,
      });
    }

    setIsStreaming(false);
    setError(null);

    if (resetPermission) {
      setPermission("idle");
    }
  }

  return {
    error,
    isStreaming,
    micChunkCount,
    permission,
    startMicrophone,
    stopMicrophone,
  };
}
