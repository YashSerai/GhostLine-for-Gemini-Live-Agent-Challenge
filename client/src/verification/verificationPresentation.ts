import type {
  GroundingHudOverrides,
  GroundingHudTone,
  GroundingHudValueOverride,
} from "../hud/groundingHud";
import type { ReadyToVerifyPhase } from "./useReadyToVerifyFlow";
import type { VerificationResultState } from "./useVerificationResultState";

function createHudOverride(
  value: string,
  tone: GroundingHudTone,
): GroundingHudValueOverride {
  return { tone, value };
}

function buildResultProtocolStep(
  verificationResult: VerificationResultState,
): GroundingHudValueOverride {
  switch (verificationResult.status) {
    case "confirmed":
      return createHudOverride("Verification confirmed", "success");
    case "user_confirmed_only":
      return createHudOverride("Verification logged as caller-confirmed", "live");
    case "unconfirmed":
      return createHudOverride("Verification recovery required", "warning");
    default:
      return createHudOverride("Verification pending", "placeholder");
  }
}

function buildAwaitingDecisionOverrides(): GroundingHudOverrides {
  return {
    protocolStep: createHudOverride("Verification engine review", "live"),
    verificationStatus: createHudOverride("Awaiting verification result", "live"),
    blockReason: createHudOverride("Backend verification in progress", "live"),
    recoveryStep: createHudOverride("Hold the line until the verdict returns", "live"),
  };
}

export function buildVerificationHudOverrides(
  verificationPhase: ReadyToVerifyPhase,
  verificationResult: VerificationResultState,
): GroundingHudOverrides {
  if (verificationResult.hasResolvedResult) {
    const taskContext = verificationResult.taskContext;

    return {
      activeTaskId: taskContext?.taskId ?? undefined,
      activeTaskName: taskContext?.taskName ?? undefined,
      blockReason:
        verificationResult.blockReason !== null
          ? createHudOverride(verificationResult.blockReason, "warning")
          : createHudOverride("None active", "success"),
      lastVerifiedItem:
        verificationResult.lastVerifiedItem !== null
          ? createHudOverride(
              verificationResult.lastVerifiedItem,
              verificationResult.statusTone,
            )
          : undefined,
      pathMode:
        verificationResult.currentPathMode ?? taskContext?.pathMode ?? undefined,
      protocolStep: buildResultProtocolStep(verificationResult),
      recoveryStep:
        verificationResult.recoveryStep !== null
          ? createHudOverride(
              verificationResult.recoveryStep,
              verificationResult.status === "unconfirmed" ? "warning" : "live",
            )
          : undefined,
      taskRoleCategory: taskContext?.taskRoleCategory ?? undefined,
      taskTier: taskContext?.taskTier ?? undefined,
      verificationStatus: createHudOverride(
        verificationResult.statusLabel,
        verificationResult.statusTone,
      ),
    };
  }

  if (verificationResult.awaitingDecision) {
    return buildAwaitingDecisionOverrides();
  }

  switch (verificationPhase) {
    case "pending":
    case "capturing_window":
      return {
        protocolStep: createHudOverride("Ready to Verify window", "warning"),
        verificationStatus: createHudOverride("Hold still - verification pending", "warning"),
        blockReason: createHudOverride("Verification window in progress", "warning"),
        recoveryStep: createHudOverride("Keep the frame steady for one second", "warning"),
      };
    case "uploading_frames":
      return {
        protocolStep: createHudOverride("Ready to Verify upload", "live"),
        verificationStatus: createHudOverride("Uploading staged verification window", "live"),
        blockReason: createHudOverride("Waiting for backend frame intake", "live"),
        recoveryStep: createHudOverride("Hold the line while staged frames upload", "live"),
      };
    case "captured":
      return buildAwaitingDecisionOverrides();
    default:
      return {};
  }
}

export function buildVerificationControlCopy(
  isTransportActive: boolean,
  permissionStage: string,
  verificationPhase: ReadyToVerifyPhase,
  verificationResult: VerificationResultState,
): string {
  if (!isTransportActive) {
    return "Start Call arms the live hotline. Ready to Verify, swap, pause, and end controls stay hidden until the line is active.";
  }

  if (permissionStage !== "permissions_ready") {
    return "Task controls stay locked until camera and microphone are granted in-call. End Session remains available so the user keeps a clean exit.";
  }

  if (verificationResult.awaitingDecision) {
    return "The staged verification window is with the backend now. Wait for the verdict before sending another verification, swap, or pause request.";
  }

  if (verificationResult.hasResolvedResult) {
    if (verificationResult.progressionDirective === "advance") {
      return "The last verification returned a visual confirmation. Await the next operator instruction before treating the session as advanced.";
    }

    if (verificationResult.progressionDirective === "wait") {
      return "The last verification is logged as caller-confirmed only. It remains visibly distinct from a full visual confirmation and should wait for operator review.";
    }

    return `The last verification was unconfirmed. ${verificationResult.recoveryStep ?? "Adjust the framing or task setup, then retry Ready to Verify."}`;
  }

  if (verificationPhase === "pending" || verificationPhase === "capturing_window") {
    return "Ready to Verify is active now. Hold still for one second while the bounded verification window is captured.";
  }

  if (verificationPhase === "uploading_frames") {
    return "The bounded verification window was captured. Frame data is being sent to the backend now.";
  }

  if (verificationPhase === "captured") {
    return "The verification window is staged on the backend and awaiting the real verification result.";
  }

  return "Ready to Verify, swap, pause, and end now send structured WebSocket envelopes to the backend. Verification requests trigger a bounded hold-still capture window instead of a background stream.";
}
