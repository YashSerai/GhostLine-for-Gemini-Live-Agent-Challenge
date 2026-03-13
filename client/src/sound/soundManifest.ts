export type SoundAssetId =
  | "ambient_bed"
  | "light_tension_stinger"
  | "warning_escalation_cue"
  | "verification_success_cue"
  | "containment_result_cue";

export type SoundAssetCategory =
  | "ambient_bed"
  | "tension_stinger"
  | "warning_cue"
  | "verification_success_cue"
  | "containment_result_cue";

export type SoundSemanticEvent =
  | "ambient_bed"
  | "light_tension"
  | "warning_escalation"
  | "verification_success"
  | "containment_result";

export interface SoundManifestEntry {
  assetId: SoundAssetId;
  category: SoundAssetCategory;
  description: string;
  duckable: boolean;
  loop: boolean;
  path: string;
  preload: "auto";
  volume: number;
}

export const SOUND_ASSET_MANIFEST: Record<SoundAssetId, SoundManifestEntry> = {
  ambient_bed: {
    assetId: "ambient_bed",
    category: "ambient_bed",
    description: "Subtle hotline ambience that can sit underneath live voice.",
    duckable: true,
    loop: true,
    path: "/audio/ambient-bed-loop.wav",
    preload: "auto",
    volume: 0.18,
  },
  light_tension_stinger: {
    assetId: "light_tension_stinger",
    category: "tension_stinger",
    description: "Brief tension rise for controlled transitions.",
    duckable: false,
    loop: false,
    path: "/audio/light-tension-stinger.wav",
    preload: "auto",
    volume: 0.22,
  },
  warning_escalation_cue: {
    assetId: "warning_escalation_cue",
    category: "warning_cue",
    description: "Short escalation warning cue for recovery or incident pressure.",
    duckable: false,
    loop: false,
    path: "/audio/warning-escalation-cue.wav",
    preload: "auto",
    volume: 0.24,
  },
  verification_success_cue: {
    assetId: "verification_success_cue",
    category: "verification_success_cue",
    description: "Soft confirmation cue for successful verification.",
    duckable: false,
    loop: false,
    path: "/audio/verification-success-cue.wav",
    preload: "auto",
    volume: 0.2,
  },
  containment_result_cue: {
    assetId: "containment_result_cue",
    category: "containment_result_cue",
    description: "Low-key containment result cue for the close of a case.",
    duckable: false,
    loop: false,
    path: "/audio/containment-result-cue.wav",
    preload: "auto",
    volume: 0.23,
  },
} as const;

export const SOUND_EVENT_MANIFEST: Record<SoundSemanticEvent, SoundAssetId> = {
  ambient_bed: "ambient_bed",
  light_tension: "light_tension_stinger",
  warning_escalation: "warning_escalation_cue",
  verification_success: "verification_success_cue",
  containment_result: "containment_result_cue",
} as const;

export const SOUND_ASSET_IDS = Object.keys(
  SOUND_ASSET_MANIFEST,
) as SoundAssetId[];
export const SOUND_SEMANTIC_EVENTS = Object.keys(
  SOUND_EVENT_MANIFEST,
) as SoundSemanticEvent[];
