import {
  DEFAULT_PCM_CHUNK_DURATION_MS,
  type EncodedPcmChunk,
  PcmChunkEncoder,
  TARGET_PCM_SAMPLE_RATE,
  buildPcmMimeType,
} from "./pcmUtils";

import { getSharedAudioContext } from "./sharedAudioContext";


const PCM_CAPTURE_WORKLET_URL = "/audio-worklets/pcmCaptureProcessor.js";

interface CaptureSamplesMessage {
  type: "samples";
  sampleRate: number;
  data: ArrayBuffer;
}

export interface AudioCaptureStartInfo {
  chunkDurationMs: number;
  deviceSampleRate: number;
  mimeType: string;
  sampleRate: number;
}

export interface AudioCaptureControllerOptions {
  stream: MediaStream;
  onChunk: (chunk: EncodedPcmChunk) => void;
  chunkDurationMs?: number;
  targetSampleRate?: number;
}

export class AudioCaptureController {
  private readonly stream: MediaStream;
  private readonly onChunk: (chunk: EncodedPcmChunk) => void;
  private readonly chunkDurationMs: number;
  private readonly targetSampleRate: number;

  private audioContext: AudioContext | null = null;
  private sourceNode: MediaStreamAudioSourceNode | null = null;
  private workletNode: AudioWorkletNode | null = null;
  private scriptProcessorNode: ScriptProcessorNode | null = null;
  private fallbackGainNode: GainNode | null = null;
  private encoder: PcmChunkEncoder;

  constructor(options: AudioCaptureControllerOptions) {
    this.stream = options.stream;
    this.onChunk = options.onChunk;
    this.chunkDurationMs =
      options.chunkDurationMs ?? DEFAULT_PCM_CHUNK_DURATION_MS;
    this.targetSampleRate = options.targetSampleRate ?? TARGET_PCM_SAMPLE_RATE;
    this.encoder = new PcmChunkEncoder(this.targetSampleRate, this.chunkDurationMs);
  }

  async start(): Promise<AudioCaptureStartInfo> {
    if (this.audioContext !== null) {
      return {
        chunkDurationMs: this.chunkDurationMs,
        deviceSampleRate: this.audioContext.sampleRate,
        mimeType: buildPcmMimeType(this.targetSampleRate),
        sampleRate: this.targetSampleRate,
      };
    }

    const audioContext = getSharedAudioContext();
    if (audioContext.state !== "running") {
      await audioContext.resume();
    }

    this.audioContext = audioContext;
    this.sourceNode = audioContext.createMediaStreamSource(this.stream);

    if (typeof AudioWorkletNode !== "undefined" && audioContext.audioWorklet) {
      await audioContext.audioWorklet.addModule(PCM_CAPTURE_WORKLET_URL);
      const workletNode = new AudioWorkletNode(
        audioContext,
        "pcm-capture-processor",
        {
          numberOfInputs: 1,
          numberOfOutputs: 0,
          channelCount: 1,
        },
      );

      workletNode.port.onmessage = (event: MessageEvent<CaptureSamplesMessage>) => {
        this.handleWorkletMessage(event);
      };

      this.sourceNode.connect(workletNode);
      this.workletNode = workletNode;
    } else {
      const processorNode = audioContext.createScriptProcessor(1024, 1, 1);
      const fallbackGainNode = audioContext.createGain();
      fallbackGainNode.gain.value = 0;

      processorNode.onaudioprocess = (event) => {
        const monoSamples = event.inputBuffer.getChannelData(0);
        this.forwardSamples(new Float32Array(monoSamples), audioContext.sampleRate);
      };

      this.sourceNode.connect(processorNode);
      processorNode.connect(fallbackGainNode);
      fallbackGainNode.connect(audioContext.destination);

      this.scriptProcessorNode = processorNode;
      this.fallbackGainNode = fallbackGainNode;
    }

    return {
      chunkDurationMs: this.chunkDurationMs,
      deviceSampleRate: audioContext.sampleRate,
      mimeType: buildPcmMimeType(this.targetSampleRate),
      sampleRate: this.targetSampleRate,
    };
  }

  async stop(): Promise<void> {
    this.encoder.reset();

    if (this.workletNode !== null) {
      this.workletNode.port.onmessage = null;
      this.workletNode.disconnect();
      this.workletNode = null;
    }

    if (this.scriptProcessorNode !== null) {
      this.scriptProcessorNode.onaudioprocess = null;
      this.scriptProcessorNode.disconnect();
      this.scriptProcessorNode = null;
    }

    if (this.fallbackGainNode !== null) {
      this.fallbackGainNode.disconnect();
      this.fallbackGainNode = null;
    }

    if (this.sourceNode !== null) {
      this.sourceNode.disconnect();
      this.sourceNode = null;
    }

    if (this.audioContext !== null) {
      this.audioContext = null;
    }
  }

  private handleWorkletMessage(
    event: MessageEvent<CaptureSamplesMessage>,
  ): void {
    const message = event.data;
    if (!message || message.type !== "samples") {
      return;
    }

    this.forwardSamples(new Float32Array(message.data), message.sampleRate);
  }

  private forwardSamples(samples: Float32Array, sampleRate: number): void {
    const chunks = this.encoder.appendInput(samples, sampleRate);
    chunks.forEach((chunk) => this.onChunk(chunk));
  }
}
