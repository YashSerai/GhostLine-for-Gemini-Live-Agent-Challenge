/**
 * useRoomScan — captures camera frames at ~1fps during room scan
 * and sends them to the backend as `room_scan_frame` messages.
 *
 * The hook activates when `isScanning` is true and a camera video
 * element is available. It captures a JPEG frame every second and
 * sends it as base64 data via the session WebSocket.
 */

import { useEffect, useRef, useState, type RefObject } from "react";

import type {
  ClientSessionMessageType,
  SessionConnectionStatus,
} from "../session/sessionTypes";
import type { CapturedFrame } from "./frameCapture";

const SCAN_INTERVAL_MS = 1000; // ~1fps for Gemini Live
const SCAN_FRAME_QUALITY = 0.6; // JPEG quality (0-1)
const SNAPSHOT_INTERVAL_FRAMES = 5; // Stash a frame for the UI every 5 seconds

export interface UseRoomScanOptions {
  /** Whether room scan capture is active */
  isScanning: boolean;
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

export interface RoomScanState {
  /** Frames captured recently for UI display */
  snapshots: CapturedFrame[];
}

export function useRoomScan(options: UseRoomScanOptions): RoomScanState {
  const { isScanning, connectionStatus, videoRef, canvasRef, sendMessage } =
    options;

  const sendMessageRef = useRef(sendMessage);
  const connectionStatusRef = useRef(connectionStatus);
  
  const frameCountRef = useRef(0);
  const [snapshots, setSnapshots] = useState<CapturedFrame[]>([]);

  useEffect(() => {
    sendMessageRef.current = sendMessage;
  }, [sendMessage]);

  useEffect(() => {
    connectionStatusRef.current = connectionStatus;
  }, [connectionStatus]);

  // Clear snapshots when scanning starts
  useEffect(() => {
    if (isScanning) {
      setSnapshots([]);
      frameCountRef.current = 0;
    }
  }, [isScanning]);

  useEffect(() => {
    if (!isScanning) return;

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
      const dataUrl = canvas.toDataURL("image/jpeg", SCAN_FRAME_QUALITY);
      const base64 = dataUrl.split(",")[1];

      if (base64) {
        sendMessageRef.current("room_scan_frame", {
          data: base64,
          capturedAt,
          width: w,
          height: h,
        });

        // Stash snapshot for UI gallery
        if (frameCountRef.current % SNAPSHOT_INTERVAL_FRAMES === 0) {
          setSnapshots((prev) => [
            ...prev,
            { 
              data: base64, 
              capturedAt, 
              width: w, 
              height: h, 
              captureType: "room_scan" as const,
              dataUrl: dataUrl,
              mimeType: "image/jpeg",
              analysis: null as any,
            },
          ]);
        }
        frameCountRef.current += 1;

        // Auto-complete calibration after 5 frames
        if (frameCountRef.current >= SNAPSHOT_INTERVAL_FRAMES) {
          sendMessageRef.current("calibration_status", {
            status: "captured",
            capturedAt,
            width: w,
            height: h,
          });
          // Clear interval so we don't keep firing
          clearInterval(intervalId);
        }
      }
    }, SCAN_INTERVAL_MS);

    return () => clearInterval(intervalId);
  }, [isScanning, videoRef, canvasRef]);

  return { snapshots };
}
