import { useEffect, useRef, useState, type RefObject } from "react";

import type {
  ClientSessionMessageType,
  SessionConnectionStatus,
} from "../session/sessionTypes";
import { captureVideoFrame, type CapturedFrame } from "./frameCapture";

export type CameraPermissionState = "idle" | "requesting" | "granted" | "denied";
export type CameraCaptureType = "calibration" | "ready_to_verify" | "manual_test";

export interface CameraPreviewState {
  cameraReady: boolean;
  captureFrame: (captureType: CameraCaptureType) => Promise<CapturedFrame | null>;
  captureFrameCount: number;
  canvasRef: RefObject<HTMLCanvasElement>;
  error: string | null;
  lastCapturedFrame: CapturedFrame | null;
  permission: CameraPermissionState;
  requestCameraAccess: () => Promise<void>;
  stopCamera: () => Promise<void>;
  videoRef: RefObject<HTMLVideoElement>;
}

interface UseCameraPreviewOptions {
  connectionStatus: SessionConnectionStatus;
  sendMessage: <T extends ClientSessionMessageType>(
    type: T,
    payload?: Record<string, unknown>,
  ) => boolean;
}

export function useCameraPreview(
  options: UseCameraPreviewOptions,
): CameraPreviewState {
  const { connectionStatus, sendMessage } = options;
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const connectionStatusRef = useRef(connectionStatus);
  const sendMessageRef = useRef(sendMessage);

  const [permission, setPermission] = useState<CameraPermissionState>("idle");
  const [cameraReady, setCameraReady] = useState(false);
  const [captureFrameCount, setCaptureFrameCount] = useState(0);
  const [lastCapturedFrame, setLastCapturedFrame] =
    useState<CapturedFrame | null>(null);
  const [error, setError] = useState<string | null>(null);
  const permissionRef = useRef<CameraPermissionState>("idle");
  const cameraReadyRef = useRef(false);

  useEffect(() => {
    connectionStatusRef.current = connectionStatus;
  }, [connectionStatus]);

  useEffect(() => {
    sendMessageRef.current = sendMessage;
  }, [sendMessage]);

  useEffect(() => {
    permissionRef.current = permission;
  }, [permission]);

  useEffect(() => {
    cameraReadyRef.current = cameraReady;
  }, [cameraReady]);

  useEffect(() => {
    if (connectionStatus === "disconnected" || connectionStatus === "error") {
      void stopCameraInternal({
        notifyBackend: false,
        reason: "transport_closed",
        resetPermission: true,
      });
    }
  }, [connectionStatus]);

  useEffect(
    () => () => {
      void stopCameraInternal({
        notifyBackend: false,
        reason: "component_unmounted",
        resetPermission: false,
      });
    },
    [],
  );

  async function requestCameraAccess(): Promise<void> {
    if (streamRef.current !== null) {
      return;
    }

    if (connectionStatusRef.current !== "connected") {
      setError("The hotline transport must be connected before camera access is requested.");
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      setPermission("denied");
      setError("This browser does not support camera capture.");
      sendMessageRef.current("camera_status", {
        permission: "denied",
        preview: false,
        reason: "unsupported_browser",
      });
      return;
    }

    setError(null);
    setPermission("requesting");
    sendMessageRef.current("camera_status", {
      permission: "requesting",
      preview: false,
      reason: "permission_prompt",
    });

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: "environment" },
          height: { ideal: 720 },
          width: { ideal: 1280 },
        },
        audio: false,
      });

      if (connectionStatusRef.current !== "connected") {
        stream.getTracks().forEach((track) => track.stop());
        setPermission("idle");
        setError("The hotline transport closed before the camera could be linked.");
        return;
      }

      streamRef.current = stream;
      if (videoRef.current !== null) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => undefined);
      }

      const videoTrack = stream.getVideoTracks()[0];
      const settings = videoTrack?.getSettings();

      setPermission("granted");
      setCameraReady(true);
      setError(null);
      sendMessageRef.current("camera_status", {
        permission: "granted",
        preview: true,
        width: settings?.width ?? videoRef.current?.videoWidth,
        height: settings?.height ?? videoRef.current?.videoHeight,
      });
    } catch (requestError) {
      const detail =
        requestError instanceof Error
          ? requestError.message
          : "Camera permission was denied or the preview could not start.";
      setPermission("denied");
      setCameraReady(false);
      setError(detail);
      sendMessageRef.current("camera_status", {
        permission: "denied",
        preview: false,
        reason: "request_failed",
      });
    }
  }

  async function captureFrame(
    captureType: CameraCaptureType,
  ): Promise<CapturedFrame | null> {
    if (videoRef.current === null || canvasRef.current === null) {
      setError("Camera preview is not ready yet.");
      return null;
    }

    try {
      const frame = captureVideoFrame(videoRef.current, canvasRef.current, {
        captureType,
      });
      setCaptureFrameCount((count) => count + 1);
      setLastCapturedFrame(frame);
      setError(null);
      if (
        captureType === "calibration" &&
        connectionStatusRef.current === "connected"
      ) {
        sendMessageRef.current("calibration_status", {
          status: "captured",
          capturedAt: frame.capturedAt,
          width: frame.width,
          height: frame.height,
          lightingScore: frame.analysis.lightingScore,
          detailScore: frame.analysis.detailScore,
        });
      }
      return frame;
    } catch (captureError) {
      const detail =
        captureError instanceof Error
          ? captureError.message
          : "Frame capture failed.";
      setError(detail);
      return null;
    }
  }

  async function stopCamera(): Promise<void> {
    await stopCameraInternal({
      notifyBackend: true,
      reason: "client_requested",
      resetPermission: true,
    });
  }

  async function stopCameraInternal(options: {
    notifyBackend: boolean;
    reason: string;
    resetPermission: boolean;
  }): Promise<void> {
    const { notifyBackend, reason, resetPermission } = options;

    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;

    if (videoRef.current !== null) {
      videoRef.current.pause();
      videoRef.current.srcObject = null;
    }

    if (
      notifyBackend &&
      connectionStatusRef.current === "connected" &&
      (cameraReadyRef.current || permissionRef.current !== "idle")
    ) {
      sendMessageRef.current("camera_status", {
        permission: resetPermission ? "idle" : permissionRef.current,
        preview: false,
        reason,
      });
    }

    setCameraReady(false);
    setError(null);

    if (resetPermission) {
      setPermission("idle");
    }
  }

  return {
    cameraReady,
    captureFrame,
    captureFrameCount,
    canvasRef,
    error,
    lastCapturedFrame,
    permission,
    requestCameraAccess,
    stopCamera,
    videoRef,
  };
}

