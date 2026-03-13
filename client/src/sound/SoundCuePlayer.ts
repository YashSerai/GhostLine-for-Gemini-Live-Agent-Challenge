import {
  SOUND_ASSET_IDS,
  SOUND_ASSET_MANIFEST,
  SOUND_EVENT_MANIFEST,
  type SoundAssetId,
  type SoundManifestEntry,
  type SoundSemanticEvent,
} from "./soundManifest";

export type SoundPlaybackStatus = "idle" | "preparing" | "ready" | "error";

interface SoundCuePlayerOptions {
  onAmbientStateChange?: (state: {
    isActive: boolean;
    isDucked: boolean;
  }) => void;
  onStatusChange?: (status: SoundPlaybackStatus) => void;
}

const AMBIENT_DUCK_FACTOR = 0.35;
const AMBIENT_DUCK_FADE_DURATION_MS = 180;
const AMBIENT_RECOVER_FADE_DURATION_MS = 260;
const AMBIENT_STOP_FADE_DURATION_MS = 240;

export class SoundCuePlayer {
  private ambientAnimationFrame: number | null = null;
  private ambientDucked = false;
  private ambientPlaying = false;
  private assetElements = new Map<SoundAssetId, HTMLAudioElement>();
  private operatorSpeaking = false;
  private preparePromise: Promise<void> | null = null;
  private status: SoundPlaybackStatus = "idle";

  constructor(private readonly options: SoundCuePlayerOptions = {}) {}

  async prepare(): Promise<void> {
    if (this.status === "ready") {
      return;
    }

    if (this.preparePromise !== null) {
      return this.preparePromise;
    }

    this.setStatus("preparing");
    this.preparePromise = Promise.all(
      SOUND_ASSET_IDS.map(async (assetId) => {
        const element = this.getOrCreateElement(assetId);
        await this.primeElement(element);
      }),
    )
      .then(() => {
        this.setStatus("ready");
      })
      .catch((error: unknown) => {
        this.setStatus("error");
        throw error;
      })
      .finally(() => {
        this.preparePromise = null;
      });

    return this.preparePromise;
  }

  async playCue(eventName: SoundSemanticEvent): Promise<boolean> {
    await this.prepare();

    const assetId = SOUND_EVENT_MANIFEST[eventName];
    if (assetId === "ambient_bed") {
      await this.startAmbientBed();
      return true;
    }

    const element = this.getOrCreateElement(assetId);
    element.pause();
    element.currentTime = 0;
    element.volume = SOUND_ASSET_MANIFEST[assetId].volume;

    try {
      await element.play();
      return true;
    } catch {
      this.setStatus("error");
      return false;
    }
  }

  async startAmbientBed(): Promise<boolean> {
    await this.prepare();

    const element = this.getOrCreateElement("ambient_bed");
    this.clearAmbientAnimation();
    element.pause();
    element.currentTime = 0;
    element.volume = this.getAmbientTargetVolume();

    try {
      await element.play();
      this.ambientPlaying = true;
      this.ambientDucked = this.operatorSpeaking;
      this.emitAmbientState();
      return true;
    } catch {
      this.setStatus("error");
      return false;
    }
  }

  stopAmbientBed(): void {
    const element = this.assetElements.get("ambient_bed");
    if (!element) {
      this.ambientPlaying = false;
      this.ambientDucked = false;
      this.emitAmbientState();
      return;
    }

    this.clearAmbientAnimation();
    this.ambientPlaying = false;
    this.ambientDucked = false;
    this.emitAmbientState();
    this.animateAmbientVolume({
      durationMs: AMBIENT_STOP_FADE_DURATION_MS,
      onComplete: () => {
        element.pause();
        element.currentTime = 0;
        element.volume = this.getAmbientTargetVolume();
      },
      targetVolume: 0,
    });
  }

  setOperatorSpeaking(isSpeaking: boolean): void {
    this.operatorSpeaking = isSpeaking;
    if (!this.ambientPlaying) {
      this.ambientDucked = false;
      this.emitAmbientState();
      return;
    }

    this.animateAmbientVolume({
      durationMs: isSpeaking
        ? AMBIENT_DUCK_FADE_DURATION_MS
        : AMBIENT_RECOVER_FADE_DURATION_MS,
      targetVolume: this.getAmbientTargetVolume(),
    });
    this.ambientDucked = isSpeaking;
    this.emitAmbientState();
  }

  getStatus(): SoundPlaybackStatus {
    return this.status;
  }

  isAmbientActive(): boolean {
    return this.ambientPlaying;
  }

  isAmbientDucked(): boolean {
    return this.ambientPlaying && this.ambientDucked;
  }

  close(): void {
    this.clearAmbientAnimation();
    for (const element of this.assetElements.values()) {
      element.pause();
      element.currentTime = 0;
      element.src = "";
      element.load();
    }
    this.assetElements.clear();
    this.ambientPlaying = false;
    this.ambientDucked = false;
    this.preparePromise = null;
    this.emitAmbientState();
    this.setStatus("idle");
  }

  private getOrCreateElement(assetId: SoundAssetId): HTMLAudioElement {
    const existingElement = this.assetElements.get(assetId);
    if (existingElement) {
      return existingElement;
    }

    const manifestEntry = SOUND_ASSET_MANIFEST[assetId];
    const element = new Audio(manifestEntry.path);
    element.loop = manifestEntry.loop;
    element.preload = manifestEntry.preload;
    element.volume = manifestEntry.volume;
    this.assetElements.set(assetId, element);
    return element;
  }

  private async primeElement(element: HTMLAudioElement): Promise<void> {
    if (element.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
      return;
    }

    await new Promise<void>((resolve, reject) => {
      const handleReady = (): void => {
        cleanup();
        resolve();
      };
      const handleError = (): void => {
        cleanup();
        reject(new Error("Static sound asset could not be prepared."));
      };
      const cleanup = (): void => {
        element.removeEventListener("canplaythrough", handleReady);
        element.removeEventListener("loadeddata", handleReady);
        element.removeEventListener("error", handleError);
      };

      element.addEventListener("canplaythrough", handleReady, { once: true });
      element.addEventListener("loadeddata", handleReady, { once: true });
      element.addEventListener("error", handleError, { once: true });
      element.load();
    });
  }

  private animateAmbientVolume(options: {
    durationMs: number;
    onComplete?: () => void;
    targetVolume: number;
  }): void {
    const element = this.assetElements.get("ambient_bed");
    if (!element) {
      options.onComplete?.();
      return;
    }

    this.clearAmbientAnimation();
    const startVolume = element.volume;
    const targetVolume = options.targetVolume;
    if (Math.abs(targetVolume - startVolume) < 0.001 || options.durationMs <= 0) {
      element.volume = targetVolume;
      options.onComplete?.();
      return;
    }

    const startTime = performance.now();
    const step = (timestamp: number): void => {
      const elapsedMs = timestamp - startTime;
      const progress = Math.min(1, elapsedMs / options.durationMs);
      element.volume = startVolume + (targetVolume - startVolume) * progress;

      if (progress >= 1) {
        this.ambientAnimationFrame = null;
        options.onComplete?.();
        return;
      }

      this.ambientAnimationFrame = window.requestAnimationFrame(step);
    };

    this.ambientAnimationFrame = window.requestAnimationFrame(step);
  }

  private getAmbientTargetVolume(): number {
    const manifestEntry = SOUND_ASSET_MANIFEST.ambient_bed;
    return this.operatorSpeaking
      ? manifestEntry.volume * AMBIENT_DUCK_FACTOR
      : manifestEntry.volume;
  }

  private clearAmbientAnimation(): void {
    if (this.ambientAnimationFrame !== null) {
      window.cancelAnimationFrame(this.ambientAnimationFrame);
      this.ambientAnimationFrame = null;
    }
  }

  private emitAmbientState(): void {
    this.options.onAmbientStateChange?.({
      isActive: this.ambientPlaying,
      isDucked: this.isAmbientDucked(),
    });
  }

  private setStatus(status: SoundPlaybackStatus): void {
    this.status = status;
    this.options.onStatusChange?.(status);
  }
}

export function getSoundManifestEntries(): SoundManifestEntry[] {
  return SOUND_ASSET_IDS.map((assetId) => SOUND_ASSET_MANIFEST[assetId]);
}
