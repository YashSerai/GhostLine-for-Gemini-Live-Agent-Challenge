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

const DEMO_FRAME_GUIDANCE_LINES: readonly WaitingDialogueLine[] = [
  {
    id: "demo_waiting_frame_01",
    kind: "pacing",
    text: "Keep the boundary centered. Do not chase the frame.",
  },
  {
    id: "demo_waiting_frame_02",
    kind: "pacing",
    text: "Good. Hold the room exactly where it is.",
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

const DEMO_TASK_EXECUTION_LINES: readonly WaitingDialogueLine[] = [
  {
    id: "demo_waiting_task_01",
    kind: "pacing",
    text: "Do that step once, then stop for my check.",
  },
  {
    id: "demo_waiting_task_02",
    kind: "diagnostic",
    text: "What did the sound resemble. Briefly.",
  },
  {
    id: "demo_waiting_task_03",
    kind: "pacing",
    text: "Good. Keep the room controlled while I place the next step.",
  },
] as const;

// Prompt 26 support dialogue only. This deliberately avoids building the fuller
// diagnosis-question system that belongs to Prompt 27.
export function getWaitingDialogueSequence(
  context: WaitingDialogueContext,
  options: {
    demoModeEnabled?: boolean;
    includeDiagnosticPrompt: boolean;
  },
): readonly WaitingDialogueLine[] {
  if (options.demoModeEnabled) {
    if (context === "frame_guidance") {
      return DEMO_FRAME_GUIDANCE_LINES;
    }

    if (options.includeDiagnosticPrompt) {
      return DEMO_TASK_EXECUTION_LINES;
    }

    return DEMO_TASK_EXECUTION_LINES.filter((line) => line.kind !== "diagnostic");
  }

  if (context === "frame_guidance") {
    return FRAME_GUIDANCE_LINES;
  }

  if (options.includeDiagnosticPrompt) {
    return TASK_EXECUTION_LINES;
  }

  return TASK_EXECUTION_LINES.filter((line) => line.kind !== "diagnostic");
}
