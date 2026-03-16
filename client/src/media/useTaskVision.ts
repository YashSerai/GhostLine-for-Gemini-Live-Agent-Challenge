/**
 * Passive task vision streaming is disabled for the demo.
 *
 * The backend now only receives explicit Ready-to-Verify captures so the live
 * voice turn is not overwhelmed by a continuous frame feed.
 */

import type { RefObject } from "react";

import type {
  ClientSessionMessageType,
  SessionConnectionStatus,
} from "../session/sessionTypes";

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

export function useTaskVision(_options: UseTaskVisionOptions): void {
  return;
}
