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

const VISION_INTERVAL_MS = 1000; // 1fps for continuous task vision
const VISION_FRAME_QUALITY = 0.55; // Slightly lower quality for continuous streaming

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
