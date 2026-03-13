import { useEffect, useMemo, useRef, useState } from "react";

import {
  SoundCuePlayer,
  type SoundPlaybackStatus,
  getSoundManifestEntries,
} from "./SoundCuePlayer";
import {
  SOUND_SEMANTIC_EVENTS,
  type SoundSemanticEvent,
} from "./soundManifest";

declare global {
  interface Window {
    __ghostlineSound?: {
      manifest: ReturnType<typeof getSoundManifestEntries>;
      playCue: (eventName: SoundSemanticEvent) => Promise<boolean>;
      prepare: () => Promise<void>;
      startAmbientBed: () => Promise<boolean>;
      stopAmbientBed: () => void;
    };
  }
}

export interface SoundPlaybackState {
  error: string | null;
  isAmbientActive: boolean;
  isAmbientDucked: boolean;
  manifestEntries: ReturnType<typeof getSoundManifestEntries>;
  playCue: (eventName: SoundSemanticEvent) => Promise<boolean>;
  prepare: () => Promise<void>;
  startAmbientBed: () => Promise<boolean>;
  status: SoundPlaybackStatus;
  statusLabel: string;
  stopAmbientBed: () => void;
}

interface UseSoundPlaybackOptions {
  isOperatorSpeaking: boolean;
}

function formatStatusLabel(status: SoundPlaybackStatus): string {
  switch (status) {
    case "preparing":
      return "Preparing";
    case "ready":
      return "Ready";
    case "error":
      return "Error";
    default:
      return "Idle";
  }
}

export function useSoundPlayback(
  options: UseSoundPlaybackOptions,
): SoundPlaybackState {
  const { isOperatorSpeaking } = options;
  const playerRef = useRef<SoundCuePlayer | null>(null);
  const [status, setStatus] = useState<SoundPlaybackStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [isAmbientActive, setIsAmbientActive] = useState(false);
  const [isAmbientDucked, setIsAmbientDucked] = useState(false);
  const manifestEntries = useMemo(() => getSoundManifestEntries(), []);

  useEffect(() => {
    if (playerRef.current === null) {
      playerRef.current = new SoundCuePlayer({
        onAmbientStateChange: (ambientState) => {
          setIsAmbientActive(ambientState.isActive);
          setIsAmbientDucked(ambientState.isDucked);
        },
        onStatusChange: setStatus,
      });
    }

    return () => {
      playerRef.current?.close();
      playerRef.current = null;
      if (import.meta.env.DEV) {
        delete window.__ghostlineSound;
      }
    };
  }, []);

  useEffect(() => {
    playerRef.current?.setOperatorSpeaking(isOperatorSpeaking);
  }, [isOperatorSpeaking]);

  async function prepare(): Promise<void> {
    try {
      setError(null);
      await playerRef.current?.prepare();
    } catch (prepareError) {
      const detail =
        prepareError instanceof Error
          ? prepareError.message
          : "Static sound assets could not be prepared.";
      setError(detail);
    }
  }

  async function playCue(eventName: SoundSemanticEvent): Promise<boolean> {
    if (!SOUND_SEMANTIC_EVENTS.includes(eventName)) {
      return false;
    }

    try {
      setError(null);
      const didPlay = (await playerRef.current?.playCue(eventName)) ?? false;
      setIsAmbientActive(playerRef.current?.isAmbientActive() ?? false);
      setIsAmbientDucked(playerRef.current?.isAmbientDucked() ?? false);
      return didPlay;
    } catch (playError) {
      const detail =
        playError instanceof Error
          ? playError.message
          : "Static sound cue playback failed.";
      setError(detail);
      return false;
    }
  }

  async function startAmbientBed(): Promise<boolean> {
    try {
      setError(null);
      const didPlay = (await playerRef.current?.startAmbientBed()) ?? false;
      setIsAmbientActive(playerRef.current?.isAmbientActive() ?? false);
      setIsAmbientDucked(playerRef.current?.isAmbientDucked() ?? false);
      return didPlay;
    } catch (playError) {
      const detail =
        playError instanceof Error
          ? playError.message
          : "Ambient bed playback failed.";
      setError(detail);
      return false;
    }
  }

  function stopAmbientBed(): void {
    playerRef.current?.stopAmbientBed();
    setIsAmbientActive(playerRef.current?.isAmbientActive() ?? false);
    setIsAmbientDucked(playerRef.current?.isAmbientDucked() ?? false);
  }

  useEffect(() => {
    if (!import.meta.env.DEV) {
      return;
    }

    window.__ghostlineSound = {
      manifest: manifestEntries,
      playCue,
      prepare,
      startAmbientBed,
      stopAmbientBed,
    };

    return () => {
      delete window.__ghostlineSound;
    };
  }, [manifestEntries]);

  return {
    error,
    isAmbientActive,
    isAmbientDucked,
    manifestEntries,
    playCue,
    prepare,
    startAmbientBed,
    status,
    statusLabel: formatStatusLabel(status),
    stopAmbientBed,
  };
}
