/**
 * useRoomScan retains local room snapshots for UI feedback during room setup.
 *
 * Passive room frame streaming is disabled for the demo because it competes
 * with live turn-taking. The backend now relies on explicit Ready-to-Verify
 * captures instead of a background image loop.
 */

import { useEffect, useRef, useState, type RefObject } from "react";

import type {
  ClientSessionMessageType,
  SessionConnectionStatus,
} from "../session/sessionTypes";
import type { CapturedFrame } from "./frameCapture";

const SCAN_INTERVAL_MS = 1000;
const SCAN_FRAME_QUALITY = 0.6;
const SNAPSHOT_INTERVAL_FRAMES = 3;

const MIN_BRIGHTNESS = 15;
const MIN_DETAIL = 0.05;

type RoomScanQualityReason = "too_dark" | "low_detail";

export interface UseRoomScanOptions {
  calibrationCapturedAt: string | null;
  isScanning: boolean;
  connectionStatus: SessionConnectionStatus;
  videoRef: RefObject<HTMLVideoElement>;
  canvasRef: RefObject<HTMLCanvasElement>;
  sendMessage: <T extends ClientSessionMessageType>(
    type: T,
    payload?: Record<string, unknown>,
  ) => boolean;
}

export interface RoomScanState {
  snapshots: CapturedFrame[];
}

function quickFrameQuality(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
): { brightness: number; detail: number } {
  const cols = 8;
  const rows = 6;
  const imageData = ctx.getImageData(0, 0, w, h);
  const d = imageData.data;
  let lumaSum = 0;
  let detailSum = 0;
  let detailCount = 0;
  let prevLuma: number | null = null;

  for (let r = 0; r < rows; r++) {
    const y = Math.min(h - 1, Math.round(((r + 0.5) * h) / rows));
    prevLuma = null;
    for (let c = 0; c < cols; c++) {
      const x = Math.min(w - 1, Math.round(((c + 0.5) * w) / cols));
      const off = (y * w + x) * 4;
      const luma = d[off] * 0.2126 + d[off + 1] * 0.7152 + d[off + 2] * 0.0722;
      lumaSum += luma;
      if (prevLuma !== null) {
        detailSum += Math.abs(luma - prevLuma);
        detailCount += 1;
      }
      prevLuma = luma;
    }
  }

  const brightness = lumaSum / (cols * rows);
  const detail = detailCount > 0 ? Math.min(1, (detailSum / detailCount) / 96) : 0;
  return { brightness, detail };
}

function getQualityReason(brightness: number, detail: number): RoomScanQualityReason | null {
  if (brightness < MIN_BRIGHTNESS) {
    return "too_dark";
  }
  if (detail < MIN_DETAIL) {
    return "low_detail";
  }
  return null;
}

export function useRoomScan(options: UseRoomScanOptions): RoomScanState {
  const {
    calibrationCapturedAt: _calibrationCapturedAt,
    isScanning,
    connectionStatus,
    videoRef,
    canvasRef,
    sendMessage: _sendMessage,
  } = options;

  const connectionStatusRef = useRef(connectionStatus);
  const usableFrameCountRef = useRef(0);
  const [snapshots, setSnapshots] = useState<CapturedFrame[]>([]);

  useEffect(() => {
    connectionStatusRef.current = connectionStatus;
  }, [connectionStatus]);

  useEffect(() => {
    if (isScanning) {
      setSnapshots([]);
      usableFrameCountRef.current = 0;
    }
  }, [isScanning]);

  useEffect(() => {
    if (!isScanning) {
      return;
    }

    const intervalId = setInterval(() => {
      const video = videoRef.current;
      const canvas = canvasRef.current;

      if (!video || !canvas) {
        return;
      }
      if (connectionStatusRef.current !== "connected") {
        return;
      }
      if (video.readyState < 2) {
        return;
      }

      const ctx = canvas.getContext("2d");
      if (!ctx) {
        return;
      }

      const scale = Math.min(1, 640 / video.videoWidth);
      const w = Math.round(video.videoWidth * scale);
      const h = Math.round(video.videoHeight * scale);

      canvas.width = w;
      canvas.height = h;
      ctx.drawImage(video, 0, 0, w, h);

      const { brightness, detail } = quickFrameQuality(ctx, w, h);
      const capturedAt = new Date().toISOString();
      const dataUrl = canvas.toDataURL("image/jpeg", SCAN_FRAME_QUALITY);
      const base64 = dataUrl.split(",")[1];
      if (!base64) {
        return;
      }

      const qualityReason = getQualityReason(brightness, detail);

      if (qualityReason !== null) {
        usableFrameCountRef.current = 0;
        return;
      }

      if (usableFrameCountRef.current % SNAPSHOT_INTERVAL_FRAMES === 0) {
        setSnapshots((prev) => [
          ...prev,
          {
            data: base64,
            capturedAt,
            width: w,
            height: h,
            captureType: "room_scan" as const,
            dataUrl,
            mimeType: "image/jpeg",
            analysis: null as any,
          },
        ]);
      }

      usableFrameCountRef.current += 1;
    }, SCAN_INTERVAL_MS);

    return () => clearInterval(intervalId);
  }, [isScanning, videoRef, canvasRef]);

  return { snapshots };
}
