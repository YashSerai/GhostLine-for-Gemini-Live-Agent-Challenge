/**
 * useTaskVision — streams camera frames at ~1fps to Gemini during task execution.
 *
 * Similar to useRoomScan but:
 *  - Activates when the session is in task_assigned or waiting_ready state
 *  - Sends as "task_vision_frame" instead of "room_scan_frame"
 *  - Does NOT auto-complete — runs continuously until state changes
 *  - Gemini uses these frames to guide the caller in real time
 */

import { useEffect, useRef, type RefObject } from "react";

import type {
  ClientSessionMessageType,
  SessionConnectionStatus,
} from "../session/sessionTypes";

const VISION_INTERVAL_MS = 2000; // 0.5fps — balanced for interactive guidance without overloading Gemini
const VISION_FRAME_QUALITY = 0.55; // Slightly lower quality for continuous streaming

// Frame quality thresholds — skip frames that are too dark or too uniform
const MIN_BRIGHTNESS = 15; // average luma 0-255; below this = black/covered lens
const MIN_DETAIL = 0.05; // detail score 0-1; below this = completely uniform/blank

export interface UseTaskVisionOptions {
  /** Whether task vision streaming is active */
  isActive: boolean;
  /** Connection status — only send when connected */
  connectionStatus: SessionConnectionStatus;
  /** Reference to the live camera video element */
  videoRef: RefObject<HTMLVideoElement>;
  /** Canvas for frame capture */
  canvasRef: RefObject<HTMLCanvasElement>;
  /** Session sendMessage function */
  sendMessage: <T extends ClientSessionMessageType>(
    type: T,
    payload?: Record<string, unknown>,
  ) => boolean;
}

/**
 * Quick frame quality check — samples an 8×6 grid of pixels to compute
 * average brightness and a rough detail score without analyzing the full frame.
 * Returns { brightness (0-255), detail (0-1) }.
 */
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
        detailCount++;
      }
      prevLuma = luma;
    }
  }

  const brightness = lumaSum / (cols * rows);
  const detail = detailCount > 0 ? Math.min(1, (detailSum / detailCount) / 96) : 0;
  return { brightness, detail };
}

export function useTaskVision(options: UseTaskVisionOptions): void {
  const { isActive, connectionStatus, videoRef, canvasRef, sendMessage } =
    options;

  const sendMessageRef = useRef(sendMessage);
  const connectionStatusRef = useRef(connectionStatus);

  useEffect(() => {
    sendMessageRef.current = sendMessage;
  }, [sendMessage]);

  useEffect(() => {
    connectionStatusRef.current = connectionStatus;
  }, [connectionStatus]);

  useEffect(() => {
    if (!isActive) return;

    const intervalId = setInterval(() => {
      const video = videoRef.current;
      const canvas = canvasRef.current;

      if (!video || !canvas) return;
      if (connectionStatusRef.current !== "connected") return;
      if (video.readyState < 2) return; // HAVE_CURRENT_DATA

      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      // Scale down for faster transfer — 640px wide max
      const scale = Math.min(1, 640 / video.videoWidth);
      const w = Math.round(video.videoWidth * scale);
      const h = Math.round(video.videoHeight * scale);

      canvas.width = w;
      canvas.height = h;
      ctx.drawImage(video, 0, 0, w, h);

      // Quality gate: skip black, blank, or extremely blurry frames
      const { brightness, detail } = quickFrameQuality(ctx, w, h);
      if (brightness < MIN_BRIGHTNESS || detail < MIN_DETAIL) {
        return; // frame too dark or too uniform — do not send
      }

      const capturedAt = new Date().toISOString();
      const dataUrl = canvas.toDataURL("image/jpeg", VISION_FRAME_QUALITY);
      const base64 = dataUrl.split(",")[1];

      if (base64) {
        sendMessageRef.current("task_vision_frame", {
          data: base64,
          capturedAt,
          width: w,
          height: h,
        });
      }
    }, VISION_INTERVAL_MS);

    return () => clearInterval(intervalId);
  }, [isActive, videoRef, canvasRef]);
}
