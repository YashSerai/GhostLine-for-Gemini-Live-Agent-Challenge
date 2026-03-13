import { useEffect, useRef, useState } from "react";

import {
  StreamedPcmPlayer,
  type StreamedPcmPlayerState,
} from "./StreamedPcmPlayer";
import type {
  SessionConnectionStatus,
  SessionEnvelope,
  SessionEnvelopeListener,
} from "../session/sessionTypes";

export interface OperatorAudioPlaybackState {
  error: string | null;
  interruptPlayback: () => void;
  isSpeaking: boolean;
  operatorAudioChunkCount: number;
  preparePlayback: () => Promise<void>;
}

interface UseOperatorAudioPlaybackOptions {
  connectionStatus: SessionConnectionStatus;
  subscribeToEnvelopes: (listener: SessionEnvelopeListener) => () => void;
}

function getPayloadString(
  payload: Record<string, unknown>,
  key: string,
): string | null {
  const value = payload[key];
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

export function useOperatorAudioPlayback(
  options: UseOperatorAudioPlaybackOptions,
): OperatorAudioPlaybackState {
  const { connectionStatus, subscribeToEnvelopes } = options;
  const playerRef = useRef<StreamedPcmPlayer | null>(null);
  const [playerState, setPlayerState] =
    useState<StreamedPcmPlayerState>("idle");
  const [operatorAudioChunkCount, setOperatorAudioChunkCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (playerRef.current === null) {
      playerRef.current = new StreamedPcmPlayer({
        onStateChange: setPlayerState,
      });
    }

    return () => {
      void playerRef.current?.close();
      playerRef.current = null;
    };
  }, []);

  useEffect(() => {
    return subscribeToEnvelopes((envelope) => {
      void handleEnvelope(envelope);
    });
  }, [subscribeToEnvelopes]);

  useEffect(() => {
    if (connectionStatus === "connecting") {
      setOperatorAudioChunkCount(0);
      setError(null);
    }

    if (connectionStatus === "disconnected" || connectionStatus === "error") {
      playerRef.current?.interrupt();
    }
  }, [connectionStatus]);

  async function preparePlayback(): Promise<void> {
    try {
      setError(null);
      await playerRef.current?.resume();
    } catch (resumeError) {
      const detail =
        resumeError instanceof Error
          ? resumeError.message
          : "Operator audio playback could not be prepared.";
      setError(detail);
    }
  }

  function interruptPlayback(): void {
    playerRef.current?.interrupt();
  }

  async function handleEnvelope(
    envelope: SessionEnvelope<string>,
  ): Promise<void> {
    if (envelope.type === "operator_interruption") {
      interruptPlayback();
      return;
    }

    if (envelope.type !== "operator_audio_chunk") {
      return;
    }

    const data = getPayloadString(envelope.payload, "data");
    const mimeType =
      getPayloadString(envelope.payload, "mimeType") ?? "audio/pcm;rate=16000";
    if (!data) {
      return;
    }

    try {
      await playerRef.current?.enqueueChunk(data, mimeType);
      setOperatorAudioChunkCount((count) => count + 1);
      setError(null);
    } catch (enqueueError) {
      const detail =
        enqueueError instanceof Error
          ? enqueueError.message
          : "Operator audio playback failed.";
      setError(detail);
    }
  }

  return {
    error,
    interruptPlayback,
    isSpeaking: playerState === "speaking",
    operatorAudioChunkCount,
    preparePlayback,
  };
}
