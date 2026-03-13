export type WaitingDialogueContext = "frame_guidance" | "task_execution";
export type WaitingDialogueKind = "pacing" | "diagnostic";

export interface WaitingDialogueLine {
  id: string;
  kind: WaitingDialogueKind;
  text: string;
}

const FRAME_GUIDANCE_LINES: readonly WaitingDialogueLine[] = [
  {
    id: "waiting_frame_01",
    kind: "pacing",
    text: "Stay with me.",
  },
  {
    id: "waiting_frame_02",
    kind: "pacing",
    text: "Do not rush the frame.",
  },
  {
    id: "waiting_frame_03",
    kind: "pacing",
    text: "Hold once you've done it.",
  },
] as const;

const TASK_EXECUTION_LINES: readonly WaitingDialogueLine[] = [
  {
    id: "waiting_task_01",
    kind: "pacing",
    text: "Do that now, then stop.",
  },
  {
    id: "waiting_task_02",
    kind: "pacing",
    text: "Good, keep moving.",
  },
  {
    id: "waiting_task_03",
    kind: "diagnostic",
    text: "If the light shifts again, call it once.",
  },
] as const;

// Prompt 26 support dialogue only. This deliberately avoids building the fuller
// diagnosis-question system that belongs to Prompt 27.
export function getWaitingDialogueSequence(
  context: WaitingDialogueContext,
  options: {
    includeDiagnosticPrompt: boolean;
  },
): readonly WaitingDialogueLine[] {
  if (context === "frame_guidance") {
    return FRAME_GUIDANCE_LINES;
  }

  if (options.includeDiagnosticPrompt) {
    return TASK_EXECUTION_LINES;
  }

  return TASK_EXECUTION_LINES.filter((line) => line.kind !== "diagnostic");
}
