import type { CapturedFrame } from "../media/frameCapture";
import type { CameraCaptureType } from "../media/useCameraPreview";

export interface VerificationWindowQualityMetrics {
  blur: number;
  lighting: number;
  motionStability: number;
}

export interface VerificationWindowCapture {
  frames: readonly CapturedFrame[];
  qualityMetrics: VerificationWindowQualityMetrics;
}

interface CaptureVerificationWindowOptions {
  captureFrame: (captureType: CameraCaptureType) => Promise<CapturedFrame | null>;
  frameCount: number;
  onFrameCaptured?: (frame: CapturedFrame, frameIndex: number) => void;
  windowDurationMs: number;
}

function delay(durationMs: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, durationMs);
  });
}

export async function captureVerificationWindow(
  options: CaptureVerificationWindowOptions,
): Promise<VerificationWindowCapture> {
  const { captureFrame, frameCount, onFrameCaptured, windowDurationMs } = options;
  const safeFrameCount = Math.max(1, frameCount);
  const intervalMs =
    safeFrameCount > 1
      ? Math.max(120, Math.round(windowDurationMs / (safeFrameCount - 1)))
      : windowDurationMs;

  const frames: CapturedFrame[] = [];
  for (let frameIndex = 0; frameIndex < safeFrameCount; frameIndex += 1) {
    const frame = await captureFrame("ready_to_verify");
    if (frame === null) {
      throw new Error("Verification capture did not return a usable frame.");
    }

    frames.push(frame);
    onFrameCaptured?.(frame, frameIndex + 1);

    if (frameIndex < safeFrameCount - 1) {
      await delay(intervalMs);
    }
  }

  return {
    frames,
    qualityMetrics: summarizeWindowMetrics(frames),
  };
}

function summarizeWindowMetrics(
  frames: readonly CapturedFrame[],
): VerificationWindowQualityMetrics {
  const lighting =
    frames.reduce((sum, frame) => sum + frame.analysis.lightingScore, 0) /
    Math.max(1, frames.length);
  const detail =
    frames.reduce((sum, frame) => sum + frame.analysis.detailScore, 0) /
    Math.max(1, frames.length);

  return {
    blur: clamp01(1 - detail),
    lighting: clamp01(lighting),
    motionStability: calculateMotionStability(frames),
  };
}

function calculateMotionStability(
  frames: readonly CapturedFrame[],
): number {
  if (frames.length < 2) {
    return 1;
  }

  let deltaSum = 0;
  let deltaCount = 0;
  for (let index = 1; index < frames.length; index += 1) {
    const previous = frames[index - 1].analysis.motionSignature;
    const current = frames[index].analysis.motionSignature;
    const limit = Math.min(previous.length, current.length);

    if (limit === 0) {
      continue;
    }

    let signatureDelta = 0;
    for (let signatureIndex = 0; signatureIndex < limit; signatureIndex += 1) {
      signatureDelta += Math.abs(current[signatureIndex] - previous[signatureIndex]);
    }

    deltaSum += signatureDelta / (limit * 255);
    deltaCount += 1;
  }

  if (deltaCount === 0) {
    return 1;
  }

  return clamp01(1 - deltaSum / deltaCount);
}

function clamp01(value: number): number {
  if (Number.isNaN(value)) {
    return 0;
  }
  return Math.max(0, Math.min(1, value));
}
