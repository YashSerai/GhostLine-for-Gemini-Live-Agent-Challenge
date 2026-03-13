import { useEffect, useState } from "react";

import type {
  SessionConnectionStatus,
  SessionEnvelopeListener,
} from "../session/sessionTypes";

const MAX_TRANSCRIPT_ENTRIES = 40;
const TRANSCRIPT_STORAGE_KEY = "ghostline.transcript.entries";

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
): number {
  for (let index = entries.length - 1; index >= 0; index -= 1) {
    const entry = entries[index];
    if (entry.speaker === speaker && entry.status === "partial") {
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

export function useTranscriptLayer(
  options: UseTranscriptLayerOptions,
): TranscriptLayerState {
  const { connectionStatus, subscribeToEnvelopes } = options;
  const [entries, setEntries] = useState<TranscriptEntry[]>(loadStoredEntries);

  useEffect(() => {
    return subscribeToEnvelopes((envelope) => {
      if (envelope.type !== "transcript") {
        return;
      }

      const speaker = envelope.payload.speaker;
      const text = getPayloadString(envelope.payload, "text");
      if (!isTranscriptSpeaker(speaker) || !text) {
        return;
      }

      const isFinal = envelope.payload.isFinal === true;
      const source = getPayloadString(envelope.payload, "source") ?? "transport";
      const updatedAt = new Date().toISOString();

      setEntries((currentEntries) => {
        const nextEntries = [...currentEntries];
        const pendingIndex = findPendingEntryIndex(nextEntries, speaker);

        if (isFinal) {
          if (pendingIndex >= 0) {
            nextEntries[pendingIndex] = {
              ...nextEntries[pendingIndex],
              source,
              status: "final",
              text,
              updatedAt,
            };
          } else {
            nextEntries.push({
              id: `${speaker}-${updatedAt}`,
              speaker,
              source,
              status: "final",
              text,
              updatedAt,
            });
          }

          return trimTranscriptEntries(nextEntries);
        }

        if (pendingIndex >= 0) {
          nextEntries[pendingIndex] = {
            ...nextEntries[pendingIndex],
            source,
            text,
            updatedAt,
          };
          return nextEntries;
        }

        nextEntries.push({
          id: `${speaker}-${updatedAt}`,
          speaker,
          source,
          status: "partial",
          text,
          updatedAt,
        });
        return trimTranscriptEntries(nextEntries);
      });
    });
  }, [subscribeToEnvelopes]);

  useEffect(() => {
    void connectionStatus;
    persistEntries(entries);
  }, [connectionStatus, entries]);

  function resetTranscript(): void {
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
