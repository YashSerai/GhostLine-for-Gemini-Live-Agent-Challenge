let sharedContext: AudioContext | null = null;

export function getSharedAudioContext(): AudioContext {
  if (sharedContext === null) {
    sharedContext = new AudioContext({ latencyHint: "interactive" });
  }
  return sharedContext;
}

export function resetSharedAudioContext(): void {
  if (sharedContext !== null) {
    void sharedContext.close();
    sharedContext = null;
  }
}
