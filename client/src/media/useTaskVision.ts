/**
 * useTaskVision streams camera frames at low frequency to Gemini during task execution.
 *
 * Similar to useRoomScan but:
 *  - Activates when the session is in task_assigned or waiting_ready state
 *  - Sends as "task_vision_frame" instead of "room_scan_frame"
 *  - Does NOT auto-complete - runs continuously until state changes
 *  - Gemini uses these frames to guide the caller in real time
 */

import { useEffect, useRef, type RefObject } from "react";

import { captureVideoFrame } from "./frameCapture";
import type {
  ClientSessionMessageType,
  SessionConnectionStatus,
} from "../session/sessionTypes";

const VISION_INTERVAL_MS = 2000;
const VISION_FRAME_QUALITY = 0.55;
const MIN_LIGHTING_SCORE = 0.06;
const MIN_DETAIL_SCORE = 0.05;

export interface UseTaskVisionOptions {
  isActive: boolean;
  connectionStatus: SessionConnectionStatus;
  videoRef: RefObject<HTMLVideoElement>;
  canvasRef: RefObject<HTMLCanvasElement>;
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
      if (video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) return;

      try {
        const frame = captureVideoFrame(video, canvas, {
          captureType: "task_vision",
          maxWidth: 640,
          quality: VISION_FRAME_QUALITY,
        });

        if (
          frame.analysis.lightingScore < MIN_LIGHTING_SCORE ||
          frame.analysis.detailScore < MIN_DETAIL_SCORE
        ) {
          return;
        }

        sendMessageRef.current("task_vision_frame", {
          data: frame.data,
          capturedAt: frame.capturedAt,
          frameAnalysis: frame.analysis,
          height: frame.height,
          mimeType: frame.mimeType,
          width: frame.width,
        });
      } catch {
        // Ignore transient capture failures while the camera feed is warming up.
      }
    }, VISION_INTERVAL_MS);

    return () => clearInterval(intervalId);
  }, [isActive, videoRef, canvasRef]);
}
