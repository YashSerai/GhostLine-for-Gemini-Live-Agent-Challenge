import { useEffect, useMemo, useRef, useState } from "react";

import {
  getWaitingDialogueSequence,
  type WaitingDialogueContext,
  type WaitingDialogueKind,
  type WaitingDialogueLine,
} from "./waitingDialogueLibrary";

const INITIAL_DELAY_MS = 6500;
const RESUME_DELAY_MS = 5500;
const BETWEEN_LINES_DELAY_MS = 8500;

export interface WaitingDialogueState {
  currentKind: WaitingDialogueKind | null;
  currentLine: string | null;
  isActive: boolean;
}

interface UseWaitingDialogueOptions {
  active: boolean;
  allowDiagnosticPrompt: boolean;
  context: WaitingDialogueContext;
  demoModeEnabled?: boolean;
  isOperatorSpeaking: boolean;
}

export function useWaitingDialogue(
  options: UseWaitingDialogueOptions,
): WaitingDialogueState {
  const { active, allowDiagnosticPrompt, context, demoModeEnabled = false, isOperatorSpeaking } = options;
  const [currentLine, setCurrentLine] = useState<WaitingDialogueLine | null>(null);
  const lineIndexRef = useRef(0);
  const timerRef = useRef<number | null>(null);
  const windowKeyRef = useRef<string | null>(null);

  const sequence = useMemo(
    () =>
      getWaitingDialogueSequence(context, {
        demoModeEnabled,
        includeDiagnosticPrompt: allowDiagnosticPrompt,
      }),
    [allowDiagnosticPrompt, context, demoModeEnabled],
  );
  const windowKey = `${demoModeEnabled ? "demo" : "normal"}:${context}:${allowDiagnosticPrompt ? "diagnostic" : "paced"}`;

  function clearScheduledLine(): void {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }

  function scheduleNextLine(delayMs: number): void {
    clearScheduledLine();

    if (lineIndexRef.current >= sequence.length) {
      return;
    }

    timerRef.current = window.setTimeout(() => {
      timerRef.current = null;

      const nextLine = sequence[lineIndexRef.current];
      if (!nextLine) {
        return;
      }

      lineIndexRef.current += 1;
      setCurrentLine(nextLine);
      scheduleNextLine(BETWEEN_LINES_DELAY_MS);
    }, delayMs);
  }

  useEffect(() => {
    return () => {
      clearScheduledLine();
    };
  }, []);

  useEffect(() => {
    if (!active) {
      clearScheduledLine();
      lineIndexRef.current = 0;
      windowKeyRef.current = null;
      setCurrentLine(null);
      return;
    }

    if (isOperatorSpeaking) {
      clearScheduledLine();
      setCurrentLine(null);
      return;
    }

    if (windowKeyRef.current !== windowKey) {
      windowKeyRef.current = windowKey;
      lineIndexRef.current = 0;
      setCurrentLine(null);
      scheduleNextLine(INITIAL_DELAY_MS);
      return;
    }

    if (currentLine === null && timerRef.current === null && lineIndexRef.current < sequence.length) {
      scheduleNextLine(RESUME_DELAY_MS);
    }
  }, [active, currentLine, isOperatorSpeaking, sequence.length, windowKey]);

  return {
    currentKind: currentLine?.kind ?? null,
    currentLine: currentLine?.text ?? null,
    isActive: active && !isOperatorSpeaking && currentLine !== null,
  };
}
