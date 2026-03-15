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

const INTERRUPTED_HOLD_MS = 650;

export type OperatorTurnState = "idle" | "speaking" | "interrupted" | "listening";

export interface OperatorAudioPlaybackState {
  error: string | null;
  interruptPlayback: () => void;
  isInterrupted: boolean;
  isSpeaking: boolean;
  operatorAudioChunkCount: number;
  preparePlayback: () => Promise<void>;
  turnState: OperatorTurnState;
  getAnalyserNode: () => AnalyserNode | null;
}

interface UseOperatorAudioPlaybackOptions {
  connectionStatus: SessionConnectionStatus;
  isMicStreaming: boolean;
  subscribeToEnvelopes: (listener: SessionEnvelopeListener) => () => void;
}

function getPayloadString(
  payload: Record<string, unknown>,
  key: string,
): string | null {
  const value = payload[key];
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function getPayloadNumber(
  payload: Record<string, unknown>,
  key: string,
): number | null {
  const value = payload[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function useOperatorAudioPlayback(
  options: UseOperatorAudioPlaybackOptions,
): OperatorAudioPlaybackState {
  const { connectionStatus, isMicStreaming, subscribeToEnvelopes } = options;
  const playerRef = useRef<StreamedPcmPlayer | null>(null);
  const interruptionTimerRef = useRef<number | null>(null);
  const [playerState, setPlayerState] =
    useState<StreamedPcmPlayerState>("idle");
  const [operatorAudioChunkCount, setOperatorAudioChunkCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isInterrupted, setIsInterrupted] = useState(false);

  useEffect(() => {
    if (playerRef.current === null) {
      playerRef.current = new StreamedPcmPlayer({
        onStateChange: setPlayerState,
      });
    }

    return () => {
      clearInterruptionTimer();
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
      clearInterruptionTimer();
      setIsInterrupted(false);
      setOperatorAudioChunkCount(0);
      setError(null);
      playerRef.current?.reset();
    }

    if (connectionStatus === "disconnected" || connectionStatus === "error") {
      clearInterruptionTimer();
      setIsInterrupted(false);
      playerRef.current?.reset();
    }
  }, [connectionStatus]);

  useEffect(() => {
    if (playerState === "speaking") {
      clearInterruptionTimer();
      setIsInterrupted(false);
    }
  }, [playerState]);

  function clearInterruptionTimer(): void {
    if (interruptionTimerRef.current !== null) {
      window.clearTimeout(interruptionTimerRef.current);
      interruptionTimerRef.current = null;
    }
  }

  function scheduleListeningState(): void {
    clearInterruptionTimer();
    interruptionTimerRef.current = window.setTimeout(() => {
      interruptionTimerRef.current = null;
      if (connectionStatus === "connected" && isMicStreaming) {
        setIsInterrupted(false);
      }
    }, INTERRUPTED_HOLD_MS);
  }

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

  function interruptPlayback(playbackEpoch?: number): void {
    playerRef.current?.interrupt(playbackEpoch);
    setIsInterrupted(true);
    scheduleListeningState();
  }

  async function handleEnvelope(
    envelope: SessionEnvelope<string>,
  ): Promise<void> {
    if (envelope.type === "operator_interruption") {
      const playbackEpoch = getPayloadNumber(envelope.payload, "playbackEpoch") ?? undefined;
      interruptPlayback(playbackEpoch);
      return;
    }

    if (envelope.type !== "operator_audio_chunk") {
      return;
    }

    const data = getPayloadString(envelope.payload, "data");
    const mimeType =
      getPayloadString(envelope.payload, "mimeType") ?? "audio/pcm;rate=16000";
    const playbackEpoch = getPayloadNumber(envelope.payload, "playbackEpoch") ?? 0;
    if (!data) {
      return;
    }

    try {
      const accepted =
        (await playerRef.current?.enqueueChunk(data, mimeType, playbackEpoch)) ?? false;
      if (!accepted) {
        return;
      }

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

  let turnState: OperatorTurnState = "idle";
  if (playerState === "speaking") {
    turnState = "speaking";
  } else if (isInterrupted) {
    turnState = "interrupted";
  } else if (connectionStatus === "connected" && isMicStreaming) {
    turnState = "listening";
  }

  return {
    error,
    interruptPlayback: () => interruptPlayback(),
    isInterrupted,
    isSpeaking: playerState === "speaking",
    operatorAudioChunkCount,
    preparePlayback,
    turnState,
    getAnalyserNode: () => playerRef.current?.getAnalyserNode() ?? null,
  };
}
