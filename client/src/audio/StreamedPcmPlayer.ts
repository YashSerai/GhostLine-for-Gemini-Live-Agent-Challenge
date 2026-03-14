import {
  TARGET_PCM_SAMPLE_RATE,
  base64ToBytes,
  parsePcmSampleRate,
  pcm16BytesToFloat32,
} from "./pcmUtils";


export type StreamedPcmPlayerState = "idle" | "speaking";

export interface StreamedPcmPlayerOptions {
  onStateChange?: (state: StreamedPcmPlayerState) => void;
}

export class StreamedPcmPlayer {
  private readonly onStateChange?: (state: StreamedPcmPlayerState) => void;

  private audioContext: AudioContext | null = null;
  private gainNode: GainNode | null = null;
  private nextStartTime = 0;
  private activeSources = new Set<AudioBufferSourceNode>();
  private state: StreamedPcmPlayerState = "idle";
  private currentPlaybackEpoch = 0;
  private flushedPlaybackEpoch = -1;

  constructor(options: StreamedPcmPlayerOptions = {}) {
    this.onStateChange = options.onStateChange;
  }

  async resume(): Promise<void> {
    const audioContext = this.ensureContext();
    if (audioContext.state !== "running") {
      await audioContext.resume();
    }
  }

  async enqueueChunk(
    data: string,
    mimeType: string,
    playbackEpoch: number = 0,
  ): Promise<boolean> {
    if (!this.shouldAcceptChunk(playbackEpoch)) {
      return false;
    }

    await this.resume();

    const audioContext = this.ensureContext();
    const bytes = base64ToBytes(data);
    const samples = pcm16BytesToFloat32(bytes);
    const channelSamples = new Float32Array(samples.length);
    channelSamples.set(samples);
    const sampleRate = parsePcmSampleRate(mimeType, TARGET_PCM_SAMPLE_RATE);
    const audioBuffer = audioContext.createBuffer(1, channelSamples.length, sampleRate);
    audioBuffer.copyToChannel(channelSamples, 0);

    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(this.ensureGainNode(audioContext));

    const startTime = Math.max(audioContext.currentTime + 0.03, this.nextStartTime);
    source.start(startTime);
    this.nextStartTime = startTime + audioBuffer.duration;
    this.activeSources.add(source);
    this.updateState("speaking");

    source.onended = () => {
      this.activeSources.delete(source);
      if (this.activeSources.size === 0) {
        this.nextStartTime = this.audioContext?.currentTime ?? 0;
        this.updateState("idle");
      }
    };

    return true;
  }

  interrupt(playbackEpoch?: number): void {
    const interruptedEpoch = playbackEpoch ?? this.currentPlaybackEpoch;
    this.flushedPlaybackEpoch = Math.max(
      this.flushedPlaybackEpoch,
      interruptedEpoch,
    );
    this.currentPlaybackEpoch = Math.max(
      this.currentPlaybackEpoch,
      interruptedEpoch,
    );

    for (const source of this.activeSources) {
      try {
        source.stop(0);
      } catch {
        // Ignore sources that have already finished.
      }
    }

    this.activeSources.clear();
    this.nextStartTime = this.audioContext?.currentTime ?? 0;
    this.updateState("idle");
  }

  reset(): void {
    this.interrupt();
    this.currentPlaybackEpoch = 0;
    this.flushedPlaybackEpoch = -1;
  }

  async close(): Promise<void> {
    this.reset();

    if (this.gainNode !== null) {
      this.gainNode.disconnect();
      this.gainNode = null;
    }

    if (this.audioContext !== null) {
      await this.audioContext.close();
      this.audioContext = null;
    }
  }

  private ensureContext(): AudioContext {
    if (this.audioContext === null) {
      this.audioContext = new AudioContext({ latencyHint: "interactive" });
    }

    return this.audioContext;
  }

  private ensureGainNode(audioContext: AudioContext): GainNode {
    if (this.gainNode === null) {
      this.gainNode = audioContext.createGain();
      this.gainNode.gain.value = 1;
      this.gainNode.connect(audioContext.destination);
    }

    return this.gainNode;
  }

  private shouldAcceptChunk(playbackEpoch: number): boolean {
    if (playbackEpoch <= this.flushedPlaybackEpoch) {
      return false;
    }

    if (playbackEpoch < this.currentPlaybackEpoch) {
      return false;
    }

    if (playbackEpoch > this.currentPlaybackEpoch) {
      this.currentPlaybackEpoch = playbackEpoch;
    }

    return true;
  }

  private updateState(state: StreamedPcmPlayerState): void {
    if (this.state === state) {
      return;
    }

    this.state = state;
    this.onStateChange?.(state);
  }
}
