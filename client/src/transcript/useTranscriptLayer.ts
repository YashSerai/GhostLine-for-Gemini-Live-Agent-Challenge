import { useEffect, useRef, useState } from "react";

import type {
  SessionConnectionStatus,
  SessionEnvelopeListener,
} from "../session/sessionTypes";

const MAX_TRANSCRIPT_ENTRIES = 40;
const TRANSCRIPT_STORAGE_KEY = "ghostline.transcript.entries";
const DUPLICATE_WINDOW_MS = 4000;

export type TranscriptSpeaker = "operator" | "user";
export type TranscriptEntryStatus = "partial" | "final";

export interface TranscriptEntry {
  id: string;
  speaker: TranscriptSpeaker;
  source: string;
  status: TranscriptEntryStatus;
  text: string;
  updatedAt: string;
}

export interface TranscriptLayerState {
  entries: readonly TranscriptEntry[];
  finalEntryCount: number;
  hasEntries: boolean;
  resetTranscript: () => void;
}

interface UseTranscriptLayerOptions {
  connectionStatus: SessionConnectionStatus;
  subscribeToEnvelopes: (listener: SessionEnvelopeListener) => () => void;
}

function buildTranscriptEntryId(
  speaker: TranscriptSpeaker,
  source: string,
  updatedAt: string,
  sequence: number,
): string {
  return `${speaker}-${source}-${updatedAt}-${sequence}`;
}
function isTranscriptSpeaker(value: unknown): value is TranscriptSpeaker {
  return value === "operator" || value === "user";
}

function isTranscriptEntry(value: unknown): value is TranscriptEntry {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.id === "string" &&
    isTranscriptSpeaker(candidate.speaker) &&
    (candidate.status === "partial" || candidate.status === "final") &&
    typeof candidate.source === "string" &&
    typeof candidate.text === "string" &&
    typeof candidate.updatedAt === "string"
  );
}

function getPayloadString(
  payload: Record<string, unknown>,
  key: string,
): string | null {
  const value = payload[key];
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : null;
}

function findPendingEntryIndex(
  entries: readonly TranscriptEntry[],
  speaker: TranscriptSpeaker,
  source: string,
): number {
  for (let index = entries.length - 1; index >= 0; index -= 1) {
    const entry = entries[index];
    if (
      entry.speaker === speaker &&
      entry.source === source &&
      entry.status === "partial"
    ) {
      return index;
    }
  }

  return -1;
}

function trimTranscriptEntries(
  entries: readonly TranscriptEntry[],
): TranscriptEntry[] {
  const nextEntries = [...entries];

  while (nextEntries.length > MAX_TRANSCRIPT_ENTRIES) {
    const finalIndex = nextEntries.findIndex((entry) => entry.status === "final");
    if (finalIndex >= 0) {
      nextEntries.splice(finalIndex, 1);
      continue;
    }

    nextEntries.shift();
  }

  return nextEntries;
}

function loadStoredEntries(): TranscriptEntry[] {
  if (typeof window === "undefined") {
    return [];
  }

  try {
    const rawValue = window.sessionStorage.getItem(TRANSCRIPT_STORAGE_KEY);
    if (!rawValue) {
      return [];
    }

    const parsedValue = JSON.parse(rawValue);
    if (!Array.isArray(parsedValue)) {
      return [];
    }

    return trimTranscriptEntries(parsedValue.filter(isTranscriptEntry));
  } catch {
    return [];
  }
}

function persistEntries(entries: readonly TranscriptEntry[]): void {
  if (typeof window === "undefined") {
    return;
  }

  try {
    if (entries.length === 0) {
      window.sessionStorage.removeItem(TRANSCRIPT_STORAGE_KEY);
      return;
    }

    window.sessionStorage.setItem(
      TRANSCRIPT_STORAGE_KEY,
      JSON.stringify(entries),
    );
  } catch {
    // Session transcript persistence is best-effort only.
  }
}

function shouldReplaceDuplicateFinalEntry(
  previousEntry: TranscriptEntry | null,
  nextEntry: TranscriptEntry,
): boolean {
  if (previousEntry === null) {
    return false;
  }

  if (
    previousEntry.status !== "final" ||
    nextEntry.status !== "final" ||
    previousEntry.speaker !== nextEntry.speaker
  ) {
    return false;
  }

  if (previousEntry.text.trim().toLowerCase() !== nextEntry.text.trim().toLowerCase()) {
    return false;
  }

  const previousTime = Date.parse(previousEntry.updatedAt);
  const nextTime = Date.parse(nextEntry.updatedAt);
  if (Number.isNaN(previousTime) || Number.isNaN(nextTime)) {
    return false;
  }

  if (Math.abs(nextTime - previousTime) > DUPLICATE_WINDOW_MS) {
    return false;
  }

  return previousEntry.source !== nextEntry.source;
}

export function useTranscriptLayer(
  options: UseTranscriptLayerOptions,
): TranscriptLayerState {
  const { connectionStatus, subscribeToEnvelopes } = options;
  const [entries, setEntries] = useState<TranscriptEntry[]>(loadStoredEntries);
  const activeSessionIdRef = useRef<string | null>(null);
  const transcriptSequenceRef = useRef(0);

  useEffect(() => {
    return subscribeToEnvelopes((envelope) => {
      if (envelope.type !== "transcript") {
        return;
      }

      const incomingSessionId =
        typeof envelope.sessionId === "string" && envelope.sessionId.trim().length > 0
          ? envelope.sessionId
          : null;
      const speaker = envelope.payload.speaker;
      const text = getPayloadString(envelope.payload, "text");
      if (!isTranscriptSpeaker(speaker) || !text) {
        return;
      }

      const isFinal = envelope.payload.isFinal === true;
      const source = getPayloadString(envelope.payload, "source") ?? "transport";
      const updatedAt = new Date().toISOString();
      const sequence = transcriptSequenceRef.current++;

      setEntries((currentEntries) => {
        let nextEntries = currentEntries;

        if (
          incomingSessionId !== null &&
          incomingSessionId !== activeSessionIdRef.current
        ) {
          activeSessionIdRef.current = incomingSessionId;
          nextEntries = [];
        }

        const mutableEntries = [...nextEntries];
        const pendingIndex = findPendingEntryIndex(mutableEntries, speaker, source);

        if (isFinal) {
          const nextFinalEntry: TranscriptEntry = {
            id: buildTranscriptEntryId(speaker, source, updatedAt, sequence),
            speaker,
            source,
            status: "final",
            text,
            updatedAt,
          };

          if (pendingIndex >= 0) {
            mutableEntries[pendingIndex] = {
              ...mutableEntries[pendingIndex],
              source,
              status: "final",
              text,
              updatedAt,
            };
          } else if (
            shouldReplaceDuplicateFinalEntry(
              mutableEntries.length > 0 ? mutableEntries[mutableEntries.length - 1] : null,
              nextFinalEntry,
            )
          ) {
            mutableEntries[mutableEntries.length - 1] = nextFinalEntry;
          } else {
            mutableEntries.push(nextFinalEntry);
          }

          return trimTranscriptEntries(mutableEntries);
        }

        if (pendingIndex >= 0) {
          mutableEntries[pendingIndex] = {
            ...mutableEntries[pendingIndex],
            source,
            text,
            updatedAt,
          };
          return mutableEntries;
        }

        mutableEntries.push({
          id: buildTranscriptEntryId(speaker, source, updatedAt, sequence),
          speaker,
          source,
          status: "partial",
          text,
          updatedAt,
        });
        return trimTranscriptEntries(mutableEntries);
      });
    });
  }, [subscribeToEnvelopes]);

  useEffect(() => {
    void connectionStatus;
    persistEntries(entries);
  }, [connectionStatus, entries]);

  function resetTranscript(): void {
    activeSessionIdRef.current = null;
    setEntries([]);
    persistEntries([]);
  }

  return {
    entries,
    finalEntryCount: entries.filter((entry) => entry.status === "final").length,
    hasEntries: entries.length > 0,
    resetTranscript,
  };
}


