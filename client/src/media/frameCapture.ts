export interface FrameAnalysis {
  detailScore: number;
  lightingScore: number;
  motionSignature: number[];
}

export interface CapturedFrame {
  analysis: FrameAnalysis;
  captureType: string;
  capturedAt: string;
  data: string;
  dataUrl: string;
  height: number;
  mimeType: string;
  width: number;
}

export interface CaptureFrameOptions {
  captureType: string;
  mimeType?: string;
  maxWidth?: number;
  quality?: number;
}

export function captureVideoFrame(
  videoElement: HTMLVideoElement,
  canvasElement: HTMLCanvasElement,
  options: CaptureFrameOptions,
): CapturedFrame {
  if (videoElement.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
    throw new Error("Camera preview is not ready for capture yet.");
  }

  const videoWidth = videoElement.videoWidth;
  const videoHeight = videoElement.videoHeight;
  if (videoWidth <= 0 || videoHeight <= 0) {
    throw new Error("Camera preview does not have a valid frame size yet.");
  }

  const maxWidth = options.maxWidth ?? 960;
  const scale = Math.min(1, maxWidth / videoWidth);
  const width = Math.max(1, Math.round(videoWidth * scale));
  const height = Math.max(1, Math.round(videoHeight * scale));
  const mimeType = options.mimeType ?? "image/jpeg";
  const quality = options.quality ?? 0.82;

  canvasElement.width = width;
  canvasElement.height = height;

  const context = canvasElement.getContext("2d");
  if (context === null) {
    throw new Error("Frame capture canvas could not get a 2D context.");
  }

  context.drawImage(videoElement, 0, 0, width, height);
  const analysis = analyzeFrame(context, width, height);
  const dataUrl = canvasElement.toDataURL(mimeType, quality);
  const data = dataUrl.split(",", 2)[1];
  if (!data) {
    throw new Error("Frame capture returned an empty image payload.");
  }

  return {
    analysis,
    captureType: options.captureType,
    capturedAt: new Date().toISOString(),
    data,
    dataUrl,
    height,
    mimeType,
    width,
  };
}

function analyzeFrame(
  context: CanvasRenderingContext2D,
  width: number,
  height: number,
): FrameAnalysis {
  const imageData = context.getImageData(0, 0, width, height);
  const sampleColumns = Math.max(6, Math.min(12, width));
  const sampleRows = Math.max(6, Math.min(12, height));
  const signature: number[] = [];
  let lumaSum = 0;
  let lumaCount = 0;
  let detailSum = 0;
  let detailCount = 0;
  let previousRow: number[] | null = null;

  for (let rowIndex = 0; rowIndex < sampleRows; rowIndex += 1) {
    const y = Math.min(
      height - 1,
      Math.max(0, Math.round(((rowIndex + 0.5) * height) / sampleRows - 0.5)),
    );
    const currentRow: number[] = [];
    let previousLuma: number | null = null;

    for (let columnIndex = 0; columnIndex < sampleColumns; columnIndex += 1) {
      const x = Math.min(
        width - 1,
        Math.max(0, Math.round(((columnIndex + 0.5) * width) / sampleColumns - 0.5)),
      );
      const offset = (y * width + x) * 4;
      const luma = getLuma(
        imageData.data[offset],
        imageData.data[offset + 1],
        imageData.data[offset + 2],
      );

      signature.push(luma);
      currentRow.push(luma);
      lumaSum += luma;
      lumaCount += 1;

      if (previousLuma !== null) {
        detailSum += Math.abs(luma - previousLuma);
        detailCount += 1;
      }
      if (previousRow !== null) {
        detailSum += Math.abs(luma - previousRow[columnIndex]);
        detailCount += 1;
      }

      previousLuma = luma;
    }

    previousRow = currentRow;
  }

  const averageLuma = lumaCount > 0 ? lumaSum / lumaCount : 0;
  const averageDetail = detailCount > 0 ? detailSum / detailCount : 0;

  return {
    detailScore: clamp01(averageDetail / 96),
    lightingScore: clamp01(averageLuma / 255),
    motionSignature: signature,
  };
}

function getLuma(red: number, green: number, blue: number): number {
  return Math.round(red * 0.2126 + green * 0.7152 + blue * 0.0722);
}

function clamp01(value: number): number {
  if (Number.isNaN(value)) {
    return 0;
  }
  return Math.max(0, Math.min(1, value));
}
