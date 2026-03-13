export const TARGET_PCM_SAMPLE_RATE = 16000;
export const DEFAULT_PCM_CHUNK_DURATION_MS = 100;

export interface EncodedPcmChunk {
  sequence: number;
  mimeType: string;
  data: string;
  byteCount: number;
  sampleCount: number;
}

export function buildPcmMimeType(sampleRate: number): string {
  return `audio/pcm;rate=${sampleRate}`;
}

export function parsePcmSampleRate(mimeType: string, fallback: number): number {
  const match = /rate=(\d+)/i.exec(mimeType);
  if (!match) {
    return fallback;
  }

  const parsed = Number(match[1]);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

export function base64FromBytes(bytes: Uint8Array): string {
  let binary = "";
  for (let index = 0; index < bytes.length; index += 1) {
    binary += String.fromCharCode(bytes[index]);
  }

  return btoa(binary);
}

export function base64ToBytes(base64Value: string): Uint8Array {
  const binary = atob(base64Value);
  const bytes = new Uint8Array(binary.length);

  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }

  return bytes;
}

export function pcm16BytesToFloat32(bytes: Uint8Array): Float32Array {
  const evenLength = bytes.byteLength - (bytes.byteLength % 2);
  const sampleCount = evenLength / 2;
  const samples = new Float32Array(sampleCount);
  const view = new DataView(bytes.buffer, bytes.byteOffset, evenLength);

  for (let index = 0; index < sampleCount; index += 1) {
    const sample = view.getInt16(index * 2, true);
    samples[index] = sample / 32768;
  }

  return samples;
}

export function float32ToPcm16Bytes(samples: Float32Array): Uint8Array {
  const buffer = new ArrayBuffer(samples.length * 2);
  const view = new DataView(buffer);

  for (let index = 0; index < samples.length; index += 1) {
    const clamped = Math.max(-1, Math.min(1, samples[index]));
    const scaled = clamped < 0 ? clamped * 32768 : clamped * 32767;
    view.setInt16(index * 2, Math.round(scaled), true);
  }

  return new Uint8Array(buffer);
}

export function resampleLinear(
  input: Float32Array,
  inputSampleRate: number,
  outputSampleRate: number,
): Float32Array {
  if (inputSampleRate === outputSampleRate || input.length === 0) {
    return input;
  }

  const outputLength = Math.max(
    1,
    Math.round((input.length * outputSampleRate) / inputSampleRate),
  );
  const output = new Float32Array(outputLength);
  const ratio = inputSampleRate / outputSampleRate;

  for (let index = 0; index < outputLength; index += 1) {
    const sourceIndex = index * ratio;
    const leftIndex = Math.floor(sourceIndex);
    const rightIndex = Math.min(leftIndex + 1, input.length - 1);
    const interpolation = sourceIndex - leftIndex;
    const leftValue = input[leftIndex] ?? input[input.length - 1] ?? 0;
    const rightValue = input[rightIndex] ?? leftValue;

    output[index] = leftValue + (rightValue - leftValue) * interpolation;
  }

  return output;
}

export class PcmChunkEncoder {
  private readonly targetSampleRate: number;
  private readonly chunkSampleCount: number;
  private readonly mimeType: string;

  private nextSequence = 0;
  private pendingSamples: number[] = [];

  constructor(
    sampleRate: number = TARGET_PCM_SAMPLE_RATE,
    chunkDurationMs: number = DEFAULT_PCM_CHUNK_DURATION_MS,
  ) {
    this.targetSampleRate = sampleRate;
    this.chunkSampleCount = Math.max(
      1,
      Math.round((sampleRate * chunkDurationMs) / 1000),
    );
    this.mimeType = buildPcmMimeType(sampleRate);
  }

  appendInput(input: Float32Array, inputSampleRate: number): EncodedPcmChunk[] {
    const normalized =
      inputSampleRate === this.targetSampleRate
        ? input
        : resampleLinear(input, inputSampleRate, this.targetSampleRate);

    for (let index = 0; index < normalized.length; index += 1) {
      this.pendingSamples.push(normalized[index] ?? 0);
    }

    const chunks: EncodedPcmChunk[] = [];
    while (this.pendingSamples.length >= this.chunkSampleCount) {
      const nextSamples = Float32Array.from(
        this.pendingSamples.splice(0, this.chunkSampleCount),
      );
      const bytes = float32ToPcm16Bytes(nextSamples);

      chunks.push({
        sequence: this.nextSequence,
        mimeType: this.mimeType,
        data: base64FromBytes(bytes),
        byteCount: bytes.byteLength,
        sampleCount: nextSamples.length,
      });
      this.nextSequence += 1;
    }

    return chunks;
  }

  reset(): void {
    this.pendingSamples = [];
    this.nextSequence = 0;
  }
}
