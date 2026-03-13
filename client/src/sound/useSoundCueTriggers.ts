import { useEffect, useRef, useState } from "react";

import type { SessionConnectionStatus } from "../session/sessionTypes";
import type { VerificationResultStatus } from "../verification/useVerificationResultState";
import {
  resolveAutomatedSoundTrigger,
  shouldStartAmbientBed,
  shouldStopAmbientBed,
  type AutomatedSoundTrigger,
  type FinalContainmentVerdict,
  type SoundTriggerDecision,
  type SoundTriggerOverrides,
  type SoundTriggerSnapshot,
} from "./soundTriggerRules";
import type { SoundSemanticEvent } from "./soundManifest";

const ONE_SHOT_COOLDOWN_MS = 950;

export interface SoundCueTriggerState {
  lastTriggeredCue: AutomatedSoundTrigger | null;
}

interface UseSoundCueTriggersOptions {
  cameraReady: boolean;
  connectionStatus: SessionConnectionStatus;
  finalVerdict: FinalContainmentVerdict | null;
  overrides?: SoundTriggerOverrides;
  playCue: (eventName: SoundSemanticEvent) => Promise<boolean>;
  startAmbientBed: () => Promise<boolean>;
  stopAmbientBed: () => void;
  taskAssignmentKey: string | null;
  verificationAttemptId: string | null;
  verificationStatus: VerificationResultStatus | null;
}

export function useSoundCueTriggers(
  options: UseSoundCueTriggersOptions,
): SoundCueTriggerState {
  const {
    cameraReady,
    connectionStatus,
    finalVerdict,
    overrides,
    playCue,
    startAmbientBed,
    stopAmbientBed,
    taskAssignmentKey,
    verificationAttemptId,
    verificationStatus,
  } = options;
  const [lastTriggeredCue, setLastTriggeredCue] =
    useState<AutomatedSoundTrigger | null>(null);
  const previousSnapshotRef = useRef<SoundTriggerSnapshot | null>(null);
  const queuedDecisionRef = useRef<SoundTriggerDecision | null>(null);
  const cooldownTimerRef = useRef<number | null>(null);
  const lastOneShotAtRef = useRef(0);

  useEffect(() => {
    return () => {
      if (cooldownTimerRef.current !== null) {
        window.clearTimeout(cooldownTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    const nextSnapshot: SoundTriggerSnapshot = {
      cameraReady,
      connectionStatus,
      finalVerdict,
      taskAssignmentKey,
      verificationAttemptId,
      verificationStatus,
    };
    const previousSnapshot = previousSnapshotRef.current;

    if (shouldStartAmbientBed(previousSnapshot, nextSnapshot)) {
      void startAmbientBed();
      setLastTriggeredCue("call_connected");
    }

    if (shouldStopAmbientBed(previousSnapshot, nextSnapshot)) {
      stopAmbientBed();
    }

    const decision = resolveAutomatedSoundTrigger(
      previousSnapshot,
      nextSnapshot,
      overrides,
    );
    if (decision !== null) {
      queueOneShot(decision);
    }

    previousSnapshotRef.current = nextSnapshot;
  }, [
    cameraReady,
    connectionStatus,
    finalVerdict,
    overrides,
    playCue,
    startAmbientBed,
    stopAmbientBed,
    taskAssignmentKey,
    verificationAttemptId,
    verificationStatus,
  ]);

  function queueOneShot(decision: SoundTriggerDecision): void {
    const queuedDecision = queuedDecisionRef.current;
    if (queuedDecision && queuedDecision.priority > decision.priority) {
      return;
    }

    if (cooldownTimerRef.current !== null) {
      window.clearTimeout(cooldownTimerRef.current);
      cooldownTimerRef.current = null;
    }

    queuedDecisionRef.current = decision;
    const elapsedMs = Date.now() - lastOneShotAtRef.current;
    const cooldownRemainingMs = Math.max(0, ONE_SHOT_COOLDOWN_MS - elapsedMs);
    const delayMs = Math.max(decision.delayMs, cooldownRemainingMs);

    cooldownTimerRef.current = window.setTimeout(() => {
      cooldownTimerRef.current = null;
      const nextDecision = queuedDecisionRef.current;
      if (!nextDecision) {
        return;
      }

      queuedDecisionRef.current = null;
      void playCue(nextDecision.cue).then((didPlay) => {
        if (didPlay) {
          lastOneShotAtRef.current = Date.now();
          setLastTriggeredCue(nextDecision.trigger);
        }
      });
    }, delayMs);
  }

  return {
    lastTriggeredCue,
  };
}



