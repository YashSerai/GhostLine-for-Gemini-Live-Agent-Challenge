class PcmCaptureProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0];
    if (!input || input.length === 0 || !input[0]) {
      return true;
    }

    const frameLength = input[0].length;
    const channelCount = input.length;
    const monoSamples = new Float32Array(frameLength);

    let sumSquares = 0;
    for (let frameIndex = 0; frameIndex < frameLength; frameIndex += 1) {
      let sample = 0;
      for (let channelIndex = 0; channelIndex < channelCount; channelIndex += 1) {
        sample += input[channelIndex][frameIndex] || 0;
      }
      const monoSample = sample / channelCount;
      monoSamples[frameIndex] = monoSample;
      sumSquares += monoSample * monoSample;
    }

    const rms = Math.sqrt(sumSquares / frameLength);
    if (rms < 0.01) {
      monoSamples.fill(0);
    }

    this.port.postMessage(
      {
        type: "samples",
        sampleRate,
        data: monoSamples.buffer,
      },
      [monoSamples.buffer],
    );

    return true;
  }
}

registerProcessor("pcm-capture-processor", PcmCaptureProcessor);
