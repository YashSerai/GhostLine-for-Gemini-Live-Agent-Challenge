Ghostline Fix Tracker

This document turns the audit into a working fix queue. It is meant to be the shared source of truth for fixing the project one issue at a time.

Rules for using this tracker:
Fix items in order unless a dependency forces a reorder.
After each fix, run `npm run build` in `client` and then do a manual end-to-end check in the live app.
Treat file existence as non-authoritative. Always trace the runtime path before changing code.
Update the related docs in the same pass when a user-facing behavior changes.

## 0. Current Completion Status

This block is the authoritative status summary. Some older per-item `Status:` lines below are stale and should be read together with this section until the doc pass cleans them up.

- `1` Home page mode selection: implemented in code, pending live verification. Files: `client/src/App.tsx`, `client/src/session/useSessionWebSocket.ts`
- `2` Demo mode extras: runtime behavior and demo-doc pass completed in docs. Files: `server/app/websocket_gateway.py`, `server/app/demo_dialogue.py`, `docs/DEMO_GUIDE.md`, `docs/DEMO_MODE.md`
- `3` Mode selection starts call / reaches backend mode: implemented in code, pending live verification. Files: `client/src/App.tsx`, `client/src/session/useSessionWebSocket.ts`
- `4` Adaptive mic permission flow: implemented in code, pending live verification. Files: `client/src/App.tsx`, `server/app/session_state_machine.py`, `server/app/operator_guidance.py`
- `5` Interruptible setup / early actions: implemented in code, pending live verification. Files: `client/src/App.tsx`, `server/app/session_state_machine.py`, `server/app/gemini_live.py`, `server/app/audio_bridge.py`
- `6` Name capture / baseline: implemented in code, pending live verification. Files: `server/app/session_state_machine.py`, `server/app/operator_guidance.py`
- `7` Camera permission flow sync: implemented in code, pending live verification. Files: `client/src/App.tsx`, `client/src/session/useSessionState.ts`, `server/app/session_state_machine.py`, `server/app/operator_guidance.py`
- `8` Room scan grounding: implemented in code, pending live verification. Files: `client/src/media/useRoomScan.ts`, `client/src/media/frameCapture.ts`, `server/app/websocket_gateway.py`, `server/app/audio_bridge.py`
- `9` Scan image streaming to Gemini: implemented in code, pending live verification. Files: `client/src/media/useRoomScan.ts`, `server/app/websocket_gateway.py`, `server/app/audio_bridge.py`
- `10` Threat/task transition grounding: implemented in code, pending live verification. Files: `server/app/operator_guidance.py`, `server/app/audio_bridge.py`, `server/app/gemini_verification.py`, `server/app/verification_flow.py`, `server/app/real_verification.py`
- `11` Regular-mode random task selection: implemented in code, pending live verification. Files: `server/app/protocol_planner.py`, `server/app/session_state_machine.py`
- `12` UI state sync / transcript: implemented in code, pending live verification. Files: `client/src/App.tsx`, `client/src/session/useSessionState.ts`, `client/src/transcript/useTranscriptLayer.ts`, `client/src/hud/groundingHud.ts`
- `13` Continuous task vision delivery: implemented in code, pending live verification. Files: `client/src/media/useTaskVision.ts`, `server/app/websocket_gateway.py`, `server/app/audio_bridge.py`, `server/app/verification_flow.py`
- `14` Before/after verification grounding: implemented in code, pending live verification. Files: `client/src/verification/useReadyToVerifyFlow.ts`, `server/app/verification_engine.py`, `server/app/verification_flow.py`, `server/app/websocket_gateway.py`, `server/app/gemini_verification.py`, `server/app/real_verification.py`
- `A` Shared contract constants: implemented in code, pending live verification. Files: `shared/contracts/product_constants.json`, `shared/typescript/productConstants.ts`, `shared/python/product_constants.py`
- `B` Demo/rehearsal references: docs cleanup completed. Files: `README.md`, `docs/DEMO_GUIDE.md`, `docs/DEMO_MODE.md`, `docs/DEMO_PROCEDURE.md`, `docs/DEMO_SCRIPT.md`, `docs/DEVPOST_SUBMISSION.md`, `docs/ARCHITECTURE_DIAGRAM.md`, `docs/ARCHITECTURE_DIAGRAM.mmd`
- `C` HUD stale-title logic: implemented in code, pending live verification. Files: `client/src/App.tsx`, `client/src/hud/groundingHud.ts`
- `D` Demo dialogue live-path verification: implemented in code, pending live verification. Files: `server/app/websocket_gateway.py`, `server/app/demo_dialogue.py`
## 1. Runtime Responsibility Map

Use this section to save context before diving into a fix.

`client/src/App.tsx`
 - Main runtime shell.
 - Owns splash flow, call start UI, permission-stage display, transcript panel, task controls, and HUD assembly.
`client/src/session/useSessionWebSocket.ts`
 - Creates the WebSocket session manager and prepares the client connect payload.
 - Critical for mode propagation into the backend.
`client/src/session/webSocketSessionManager.ts`
 - Lower-level WebSocket transport and client message sending.
`client/src/session/useSessionState.ts`
 - Client-side projection of backend session events and session state.
`client/src/media/useCameraPreview.ts`
 - Camera acquisition and preview state.
`client/src/media/useRoomScan.ts`
 - Room-scan frame capture and room-scan completion signaling.
`client/src/media/useTaskVision.ts`
 - Continuous post-scan task monitoring frame capture.
`client/src/media/frameCapture.ts`
 - Shared frame capture utilities.
`client/src/audio/useMicrophoneBridge.ts`
 - Mic capture and audio upload path.
`client/src/audio/useOperatorAudioPlayback.ts`
 - Operator speech playback path.
`client/src/transcript/useTranscriptLayer.ts`
 - Transcript state, persistence, and rendering data for the client transcript panel.
`client/src/verification/*`
 - Ready-to-verify UI and verification result presentation.
`client/src/hud/groundingHud.ts`
 - HUD section generation for protocol, active task, and verification context.
`server/app/main.py`
 - FastAPI app boot, dependency setup, default verification engine selection.
`server/app/websocket_gateway.py`
 - Main runtime orchestrator for WebSocket envelopes, Gemini bridge setup, task vision routing, room-scan routing, and verification engine wiring.
`server/app/session_state_machine.py`
 - Backend truth for setup progression and high-level protocol state transitions.
`server/app/audio_bridge.py`
 - Prompt/context injection into Gemini Live and vision priming directives.
`server/app/gemini_live.py`
 - Gemini Live session transport and streaming turn handling.
`server/app/operator_guidance.py`
 - Operator dialogue and state guidance.
`server/app/demo_mode.py`
 - Fixed demo task sequence.
`server/app/demo_recovery.py`
 - Demo-only corrective beats and near-failure scripting.
`server/app/demo_barge_in.py`
 - Demo-only barge-in scripting.
`server/app/demo_dialogue.py`
 - Demo dialogue constants; some appear unused and need verification.
`server/app/task_library.py`
 - Task definitions and metadata.
`server/app/protocol_planner.py`
 - Regular-mode protocol planner. Currently deterministic, not random.
`server/app/verification_flow.py`
 - Verification lifecycle, attempt tracking, and protocol advancement after verification results.
`server/app/gemini_verification.py`
 - Gemini-based visual verification engine. Currently the main risk area for real visual confirmation.
`server/app/real_verification.py`
 - Rule-based verification engine with stronger explicit confirm/unconfirm branches, but it is not the active normal runtime path right now.
`shared/contracts/product_constants.json`
 - Shared contract file. Needs to stay aligned with real backend session states.
`shared/typescript/productConstants.ts`
 - TS constants generated from shared contracts.
`shared/python/product_constants.py`
 - Python constants generated from shared contracts.
`README.md`, `docs/DEMO_GUIDE.md`, `docs/DEMO_MODE.md`, `docs/DEMO_PROCEDURE.md`, `docs/DEMO_SCRIPT.md`, `docs/DEVPOST_SUBMISSION.md`, `docs/ARCHITECTURE_DIAGRAM.md`
 - Primary product/demo docs. Several are currently ahead of the implementation or describe stale paths.

## 2. Priority Fix Queue

### 1. Home page mode selection needs to be fixed

Status: confirmed fix needed

Problem:
The splash is not a strict two-option gate.
It can be dismissed by clicking the backdrop.
Selecting a mode does not itself start the live call.

Key files:
`client/src/App.tsx:1153`
`client/src/App.tsx:1171`
`client/src/App.tsx:1182`
`client/src/App.tsx:1525-1528`

Evidence:
`client/src/App.tsx:1153` dismisses the splash with `onClick={() => setShowSplash(false)}`.
`client/src/App.tsx:1171` and `client/src/App.tsx:1182` expose the two launch buttons.
`client/src/App.tsx:1525-1528` still requires a separate `Start Call`.

Fix intent:
The home page should present exactly Demo Mode and Regular Mode.
Choosing either mode should move directly into session connection.
Remove the accidental bypass path through backdrop click.

Definition of done:
No non-mode path out of the splash.
Demo and Regular remain the only top-level entry options.
Selecting a mode immediately starts the call flow.

### 2. Demo mode extras are acceptable, but the docs and scripted use need to be corrected and fleshed out

Status: confirmed doc/runtime alignment needed

Problem:
Demo mode contains extra scripting beyond task selection.
That is acceptable for judged reliability, but the docs need to accurately describe what demo-only behavior exists and how to intentionally use it.

Key files:
`server/app/demo_mode.py:12-22`
`server/app/demo_recovery.py`
`server/app/demo_barge_in.py`
`server/app/demo_dialogue.py`
`client/src/App.tsx:938`
`client/src/App.tsx:1082-1096`
`client/src/App.tsx:1672`
`docs/DEMO_GUIDE.md`
`docs/DEMO_SCRIPT.md:9`
`docs/DEMO_SCRIPT.md:32`
`docs/DEMO_SCRIPT.md:47`
`docs/DEMO_SCRIPT.md:50`
`docs/DEMO_MODE.md:324-344`

Evidence:
Demo flow is explicitly fixed to `T2`, `T5`, `T14`, `T7`.
Demo reset logic exists in the client.
Demo script already references controlled barge-in and deterministic recovery, but the overall docs are not yet the authoritative description of the current demo runtime.

Fix intent:
Keep demo-only enhancements if they improve judged reliability.
Make the demo docs explicit about what is scripted, what is optional, what is demo-only, and how barge-in/recovery/reset are supposed to be demonstrated.
Verify whether `server/app/demo_dialogue.py` is live or stale and either wire it properly or document/remove it.

Definition of done:
Demo-only behavior is intentional, documented, and testable.
Demo docs match the real runtime path.
No hidden demo behavior surprises judges or future contributors.

### 3. Selecting mode should connect the live call and operator begins

Status: confirmed fix needed

Problem:
There is a mode propagation bug between splash selection and backend session creation.

Key files:
`client/src/App.tsx:1058-1068`
`client/src/session/useSessionWebSocket.ts:31-36`
`client/src/session/useSessionWebSocket.ts:49-54`
`client/src/session/useSessionWebSocket.ts:85-103`

Evidence:
`client/src/session/useSessionWebSocket.ts:49-54` initializes the manager only once.
`client/src/App.tsx:1068` updates only `browserMicPermission` before connect.
The selected splash mode can differ from the backend session mode if the manager was created before the splash selection.

Fix intent:
Selecting the mode must authoritatively decide the backend session mode.
Session creation and call start need to happen from the chosen mode, not from stale defaults or URL-only state.

Definition of done:
The selected mode is guaranteed to reach the backend connect payload.
Call start is initiated from mode selection, not from a second disconnected control path.

### 4. Operator adapts if permission is already granted vs not granted

Status: confirmed fix needed

Problem:
The app captures browser mic permission, but the operator flow is not meaningfully branching on it.
Camera permission adaptation is even weaker.

Key files:
`client/src/App.tsx:609-613`
`client/src/App.tsx:1068`
`server/app/session_state_machine.py:203-206`
`server/app/operator_guidance.py`
`server/app/demo_dialogue.py:11-17`

Evidence:
`client/src/App.tsx:609-613` tracks `browserMicPermission`.
`server/app/session_state_machine.py:203-206` stores `browser_mic_permission`.
No convincing active path was found where operator guidance truly changes based on that value.
Demo adaptive opener constants exist but appear unused.

Fix intent:
Mic and camera prompts must branch based on actual permission/device state.
If already granted, the operator should acknowledge that and ask for the in-app button press.
If not granted, the operator should instruct the user to press the button and accept the browser popup.

Definition of done:
Operator lines differ for granted vs prompt/denied-like states.
Branching is driven by real runtime permission/device state, not hardcoded generic wording.

### 5. Interruptibility during setup needs to work

Status: confirmed fix needed

Problem:
Live interruption exists in the system, but setup progression is brittle if the user acts before the operator finishes speaking.

Key files:
`server/app/gemini_live.py`
`server/app/audio_bridge.py`
`server/app/session_state_machine.py:232-254`
`client/src/App.tsx:142-173`

Evidence:
`server/app/session_state_machine.py:250-254` only honors `camera_button_clicked` while in `camera_request`.
The client computes permission stage locally in `client/src/App.tsx:142-173`, which can advance ahead of backend state.

Fix intent:
If the user presses mic/camera early, the operator should acknowledge the action and continue cleanly.
UI and backend must agree on setup progression so early user actions are not dropped.

Definition of done:
Early mic/camera actions are accepted.
Setup state advances correctly even if the user interrupts or acts ahead of the spoken line.

### 6. Name capture / baseline needs to be real and reusable

Status: implemented in code, pending live verification
Implemented files: `server/app/session_state_machine.py`, `server/app/operator_guidance.py`

Problem:
The state machine includes a `name_request` step, but the user name is not clearly confirmed and stored as a durable session value.

Key files:
`server/app/session_state_machine.py:75-76`
`server/app/session_state_machine.py:284`
`server/app/session_state_machine.py:562`
`server/app/operator_guidance.py`

Evidence:
`server/app/session_state_machine.py:284` transitions into `name_request`.
`server/app/session_state_machine.py:562` advances on any final user transcript while in `name_request`.
No strong evidence was found that the confirmed name is parsed, stored, and reused later.

Fix intent:
Ask for name after mic setup.
Confirm it explicitly.
Store it in session state.
Reuse it in later operator lines where appropriate.

Definition of done:
Name is captured, confirmed, stored, and accessible to later operator prompts and UI if needed.

### 7. Camera permission flow needs the same adaptive and synchronized behavior as mic

Status: confirmed fix needed

Problem:
Camera setup is split between local client heuristics and backend state.
This causes desync and dropped progression.

Key files:
`client/src/App.tsx:142-173`
`client/src/App.tsx:789`
`client/src/App.tsx:1019-1046`
`server/app/session_state_machine.py:223-233`
`server/app/session_state_machine.py:250-254`
`server/app/session_state_machine.py:531`

Evidence:
The client advances permission stage from local state.
The backend only transitions to `room_sweep` when `camera_button_clicked` occurs during `camera_request`.

Fix intent:
Mirror the mic fix for camera.
Make the backend authoritative for setup progression.
Ensure camera button actions and operator dialogue stay in sync.

Definition of done:
Camera step behaves correctly whether permission is already granted or not yet granted.
UI and backend show the same step at the same time.

### 8. Room scan needs to be meaningfully grounded in actual visuals

Status: confirmed fix needed

Problem:
Room scan exists, but the operator’s grounding is weaker than intended and may not be aligned with when scan frames are actually arriving.

Key files:
`client/src/media/useRoomScan.ts:18-20`
`client/src/media/useRoomScan.ts:151`
`client/src/media/useRoomScan.ts:169-170`
`server/app/websocket_gateway.py:699`
`server/app/audio_bridge.py:307`

Evidence:
Client sends scan frames roughly once per second.
Client auto-finishes after five frames.
Backend primes room-scan context after a delay, which can miss most of the actual scan.

Fix intent:
The room scan should be live, perceptually grounded, and operator-commented while it is happening.
Avoid band-aid delays that make the model blind during the actual scan.

Definition of done:
The operator receives usable room visuals during the scan window.
The operator can reference what is actually visible, not just assume a scan happened.

### 9. Image streaming during scan needs to stay live, non-interrupting, and in the same session

Status: confirmed fix needed

Problem:
Scan streaming exists, but its timing and consumption are not trustworthy enough.

Key files:
`client/src/media/useRoomScan.ts:18`
`client/src/media/useRoomScan.ts:169-170`
`server/app/websocket_gateway.py:699`
`server/app/audio_bridge.py:257`

Evidence:
Room-scan frames are sent at `~1 fps`.
Context priming is delayed.
You also reported from runtime testing that backend logs show audio being sent but not images.

Fix intent:
Ensure scan frames are actually sent, received, and forwarded to Gemini Live during the scan.
Ensure they do not interrupt operator speech.
Confirm the same live session receives them.

Definition of done:
Backend logs show scan image delivery during the active scan.
Operator speech remains continuous while vision continues in parallel.

### 10. Transition into threat/task flow needs to be more perceptually driven

Status: implemented in code, pending live verification
Implemented files: `server/app/operator_guidance.py`, `server/app/audio_bridge.py`, `server/app/gemini_verification.py`, `server/app/verification_flow.py`, `server/app/real_verification.py`

Problem:
The scan-to-threat-to-task transition exists, but it is too state/prompt-driven and not grounded enough in what the operator can currently see.

Key files:
`server/app/session_state_machine.py`
`server/app/operator_guidance.py`
`server/app/audio_bridge.py:338-457`
`server/app/verification_flow.py`

Evidence:
The transition is largely state-machine and prompt driven.
Task vision prompts tell the operator to act as a verifier, but the runtime evidence path is weaker than the prompt promises.

Fix intent:
Keep the narrative urgency, but make the transition reflect actual scene visibility.
Accept explicit operator lines like “I can’t see the door yet” or “show me the mirror” when vision is incomplete.
Use a hybrid system: prompt-driven narration plus real visual gating and operator requests for better framing.

Definition of done:
The operator can acknowledge missing visual evidence and ask the user to reframe before advancing.
Threat/task narration feels grounded rather than purely theatrical.

### 11. Task selection needs a real Regular-mode random path

Status: confirmed fix needed

Problem:
Demo is fixed, which is fine.
Regular mode is deterministic and not random.

Key files:
`server/app/demo_mode.py:12-22`
`server/app/protocol_planner.py:1`
`server/app/protocol_planner.py:42`
`server/app/task_library.py`

Evidence:
`server/app/protocol_planner.py:1` calls itself a deterministic planner.
The planner builds a deterministic 5-6 task plan from capability profile inputs.

Fix intent:
Keep Demo fixed.
Make Regular mode random within valid constraints.
Keep the same execution and verification pipeline otherwise.

Definition of done:
Multiple Regular runs can produce different task sequences.
Demo remains fixed and reliable.

### 12. UI state synchronization needs to be authoritative, and transcript needs a dedicated fix

Status: confirmed fix needed

Problem:
The UI should stay synchronized with backend state, but parts of it are inferred locally.
The operator speech transcript is also not working properly and needs focused attention.

Key files:
`client/src/App.tsx:142-173`
`client/src/App.tsx:659`
`client/src/App.tsx:858`
`client/src/App.tsx:1717-1718`
`client/src/session/useSessionState.ts`
`client/src/transcript/useTranscriptLayer.ts:137-223`
`client/src/hud/groundingHud.ts:388-401`

Evidence:
Permission stage is locally computed.
Transcript state is maintained separately in `useTranscriptLayer`.
`client/src/App.tsx:1717-1718` filters HUD sections by old titles that do not match `groundingHud.ts`, which now emits `Protocol`, `Active Task`, and `Verification Surface`.

Fix intent:
Backend session state should be the authority for setup, scan, task, and verification progression.
Transcript rendering should accurately reflect operator speech and user turns.
HUD filtering and visibility logic must match current HUD section titles.

Definition of done:
UI mode, setup stage, scan state, active task, and verification status stay in sync with backend state.
Transcript reliably shows operator speech at the right time.

### 13. Continuous live visual guidance during tasks needs to be real, not just promised

Status: implemented in code, pending live verification
Implemented files: `client/src/media/useTaskVision.ts`, `server/app/websocket_gateway.py`, `server/app/audio_bridge.py`, `server/app/verification_flow.py`

Problem:
The system claims continuous vision during tasks, but active task frames may be starved from the live Gemini session.

Key files:
`client/src/media/useTaskVision.ts:18`
`client/src/media/useTaskVision.ts:130-137`
`server/app/websocket_gateway.py:718`
`server/app/websocket_gateway.py:740-750`
`server/app/websocket_gateway.py:783`
`server/app/audio_bridge.py:338-457`

Confirmed runtime/code finding:
In `server/app/websocket_gateway.py:740-750`, `message_type == "frame"` stores frames into the verification path buffer instead of forwarding them to Gemini Live for active monitoring.
In `server/app/websocket_gateway.py:783`, `task_vision_frame` is the path that does forward to the bridge.
In `server/app/audio_bridge.py:405-414`, `prime_task_vision_context()` tells Gemini it is receiving continuous camera frames and should act as the verifier.

Fix intent:
Ensure the actual client task-vision path used during active tasks reaches Gemini Live continuously.
Remove the false promise where the prompt claims continuous camera frames if the runtime path is not delivering them.
Make operator urgency react to actual ongoing task visuals.

Definition of done:
Backend logs show task vision frames reaching Gemini during active tasks.
Operator guidance during tasks is based on ongoing vision, not just a verification-time snapshot.

### 14. Task verification / challenge behavior needs real before/after evidence

Status: implemented in code, pending live verification
Implemented files: `client/src/verification/useReadyToVerifyFlow.ts`, `server/app/verification_engine.py`, `server/app/verification_flow.py`, `server/app/websocket_gateway.py`, `server/app/gemini_verification.py`, `server/app/real_verification.py`

Problem:
Verification is one of the biggest gaps.
The active runtime path does not reliably confirm visual tasks from camera evidence.

Key files:
`server/app/main.py:46-49`
`server/app/websocket_gateway.py:338-353`
`server/app/gemini_verification.py:324`
`server/app/gemini_verification.py:404`
`server/app/gemini_verification.py:421-425`
`server/app/gemini_verification.py:436-437`
`server/app/real_verification.py:118`

Evidence:
`server/app/main.py:46-49` boots a `RealVerificationEngine` by default.
`server/app/websocket_gateway.py:338-353` swaps in `GeminiVisionVerificationEngine` for the active runtime path unless mock mode is used.
`server/app/gemini_verification.py:421-425` leaves visual checks as `unconfirmed` while telling the user vision is pending.
`server/app/gemini_verification.py:436-437` falls back to `user_confirmed_only` when vision cannot be analyzed.
`server/app/real_verification.py` contains explicit `confirmed` branches, but it is not the main live runtime path right now.

Fix intent:
Build a verification path that can truly compare before/after visual evidence and challenge false claims.
Distinguish task assigned, in progress, ready to verify, confirmed, rejected, and caller-asserted-only.
Allow the operator to explicitly say it cannot confirm because the target is not visible.

Definition of done:
Visual tasks can be truly confirmed or rejected from camera evidence.
False or incomplete completion claims are challenged.
The operator is grounded enough to say what is missing from the view.

## 3. Additional Fixes That Should Ride Along With the Queue

These were not separate top-level flow steps, but they need to be addressed as part of the same cleanup.

### A. Shared contract constants are stale

Status: confirmed fix needed

Key files:
`shared/contracts/product_constants.json:39`
`shared/typescript/productConstants.ts:59`
`shared/python/product_constants.py:84`
`shared/python/product_constants.py:101`
`server/app/session_state_machine.py`

Problem:
Shared constants currently expose `camera_request` but not other real runtime states like `microphone_request`, `name_request`, and `room_sweep`.

Impact:
Future UI and agent work can be misled by stale shared contracts.

### B. Demo/rehearsal references are ahead of the current visible runtime

Status: confirmed fix needed

Key files:
`README.md:45`
`README.md:133`
`README.md:168-174`
`docs/DEMO_MODE.md:324-344`
`client/src/styles.css:1270-1459`

Problem:
README and docs refer to a rehearsal harness or route.
Active visible runtime evidence for that path is weak.
CSS includes rehearsal panel styles that should be validated as live or removed.

### C. HUD filtering logic references stale titles

Status: confirmed fix needed

Key files:
`client/src/App.tsx:1717-1718`
`client/src/hud/groundingHud.ts:388-401`

Problem:
`App.tsx` filters on `Initial Scan & Calibration` and `Active Containment Step`.
`groundingHud.ts` now emits `Protocol`, `Active Task`, and `Verification Surface`.

Impact:
UI visibility logic can silently drift from the actual HUD payload.

### D. Demo dialogue constants need a live-path verification pass

Status: investigate during demo-doc pass

Key files:
`server/app/demo_dialogue.py:11-17`
`server/app/websocket_gateway.py:16`
`server/app/websocket_gateway.py:279-291`

Problem:
Adaptive demo dialogue constants and `ROOM_SCAN_STRUCTURED_PROMPT` are imported or referenced, but a convincing active runtime path was not confirmed.

## 4. Documentation Fix List

Update these docs as the relevant runtime fixes land:

`README.md`
 - Replace “Beta Mode” with the final intended naming if Regular Mode is the product truth.
 - Remove or correct rehearsal-harness claims unless the harness is real and reachable.
 - Remove or correct claims that imply stronger visual verification than the code actually supports.
`docs/DEMO_GUIDE.md`
 - Make it the actual judge-facing sequence.
 - Document demo-only barge-in, recovery, and reset behavior clearly.
`docs/DEMO_MODE.md`
 - Treat demo extras as intentional demo features, not hidden implementation quirks.
 - Align reset/rehearsal text with what actually exists.
`docs/DEMO_SCRIPT.md`
 - Keep it synchronized with the real demo flow after the fixes.
`docs/DEVPOST_SUBMISSION.md`
 - Remove or qualify claims about `ROOM_FEATURES`, dynamic unscripted Regular/Beta behavior, and rehearsal support if those are not real at runtime.
`docs/ARCHITECTURE_DIAGRAM.md`
 - Align the diagram text with the actual live runtime path, especially verification engine selection and room/task vision behavior.

## 5. What Still Needs Explicit Decisions

These are not blockers for starting the queue, but they need explicit calls as we fix things:

Should the backend state machine become the single source of truth for setup/UI progression, with the client only reflecting server state?
Should `GeminiVisionVerificationEngine` remain the main path, or should the stronger explicit logic in `real_verification.py` be merged into the live path instead of sitting unused?
Should there be one unified live frame message type for active monitoring and verification, or two separate paths with strict roles?
How much demo-only scripting is acceptable before Demo mode stops being “same product, polished demo path” and becomes a different experience?

## 6. Notes From Current Manual Testing

These observations should be treated as confirmed operator-facing pain points:

You reported that backend logs show audio being sent but not images.
You reported the app behaves worse at runtime than the static code already suggests.
The current `15s` room-scan delay appears to be a band-aid to avoid operator overlap and likely causes more harm than it solves.

## 7. Suggested Execution Order

Work in this order:

1. Home page mode selection and session start coupling.
2. Mode propagation bug between splash selection and backend connect.
3. Mic permission adaptation.
4. Setup interruptibility and early action handling.
5. Name capture and storage.
6. Camera permission flow synchronization.
7. Room-scan frame delivery and delayed priming removal/rework.
8. Continuous task vision delivery.
9. Task verification pipeline.
10. Regular-mode random task selection.
11. UI/backend synchronization and transcript fix.
12. Demo-specific documentation and stale-demo cleanup.
13. Shared constants and stale HUD-title cleanup.
14. Final doc trustworthiness pass.

## 8. Per-Fix Testing Reminder

For each fix:
Run `npm run build` in `client`.
You run the live server/client manually and verify the actual behavior.
Only move to the next fix after the previous behavior is verified in the live app.






