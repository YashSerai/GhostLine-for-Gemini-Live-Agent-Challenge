# Ghostline Demo Script

This document is the timed recording script and shot plan for the Ghostline judged demo.

It is based on the actual implemented demo-mode path and controlled beats:

- fixed path: `T2 -> T5 -> T14 -> T7`
- one diagnosis beat (via T14)
- one controlled barge-in
- one controlled near-failure and recovery beat on `T2`
- final case report

Use this document for the recorded take. Use [C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\DEMO_PROCEDURE.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\DEMO_PROCEDURE.md) for rehearsal and environment prep.

## Runtime Target

Target total runtime: **3:35 to 3:55**

Hard limit: **under 4:00**

## Demo Path Used In This Script

1. `T2` Close Boundary
2. `T5` Place Paper on Flat Surface
3. `T14` Describe the Sound
4. `T7` Speak Containment Phrase

Controlled demo beats:

- near-failure on `T2` with one honest unconfirmed result, one recovery line, and one successful retry
- diagnosis beat after `T14`
- barge-in on the fixed diagnosis interpretation line

Exact interruption phrase:

`Archivist, wait. Say that again.`

## Timed Script And Shot Plan

| Time | Shot / On-Screen Action | User / Operator Action | Optional Presenter Narration | What This Proves |
|---|---|---|---|---|
| `0:00-0:12` | Start on the Ghostline shell with HUD visible. | No call yet. | `Ghostline is a live paranormal containment hotline built for the Gemini Live Agent Challenge.` | Product identity and polished UI |
| `0:12-0:24` | Click `Launch Demo Mode`. Keep operator panel and HUD visible. | User starts the call. | `The Archivist can hear me, request camera access in-call, and guide the room through a short containment protocol.` | Real call start and live-agent framing |
| `0:24-0:38` | Show in-call permission request UI. | Grant camera when prompted. | `Permissions happen in context, not on a generic setup page.` | In-call permission flow |
| `0:38-0:55` | Show doorway / threshold in frame. Keep HUD legible. | Follow camera request and calibration instruction. | `The room is the game board, and the grounding HUD stays visible throughout the session.` | Calibration and visible grounding |
| `0:55-1:15` | Move into `T2 Close Boundary`. Leave the door open on the first verify. | Say `Ready to Verify.` Let it fail once. | `Here the system fails honestly. The boundary is not sealed, so the HUD shows an unconfirmed result and a recovery step.` | Honest near-failure |
| `1:15-1:35` | Close the door fully. Keep the operator panel, HUD, and transcript visible. | Follow the recovery instruction. Say `Ready to Verify.` again. | `The recovery ladder gives one corrective action, then the second attempt succeeds.` | Deterministic recovery |
| `1:35-1:55` | Perform `T5 Place Paper on Flat Surface`. | User says `Ready to Verify.` Hold still. | `Verification is staged. The system only advances when it can honestly confirm the task.` | Ready-to-Verify pattern |
| `1:55-2:15` | Stay in the live call while diagnosis question (`T14 Describe the Sound`) appears. | Answer briefly: `It sounded like a high pitched shriek.` | `Between tasks, the operator adds short diagnosis beats that keep the call feeling alive.` | Diagnosis beat |
| `2:15-2:35` | Let the diagnosis interpretation line begin. Keep transcript and turn-status visible. | Interrupt with: `Archivist, wait. Say that again.` | `This is a real barge-in. Operator audio stops immediately, stale audio is flushed, and the Archivist restates the line.` | Real interruption |
| `2:35-3:15` | Continue through `T7`. Keep the operator text and active task context visible. | Complete the final containment tasks cleanly. | `The demo path is fixed and rehearsable, not random.` | Deterministic planner and state machine |
| `3:15-3:38` | Let the case report render fully. Show verdict, classification, and task outcomes. | End the session if needed and hold on the report. | `The call ends with a structured case report that records confirmed, user-confirmed-only, unverified, and skipped outcomes.` | Final report artifact |
| `3:38-3:52` | Optionally cut to architecture diagram or cloud proof endpoint. | No new call action. | `The backend runs on Google Cloud, persists session state, and emits proof-grade structured logs.` | Quick architecture / cloud reminder |

## Recommended Exact User Lines

Use short, consistent lines during the take:

- `I need containment guidance.`
- `The doorway is in front of me.`
- `Ready to Verify.`
- `It sounded like a high pitched shriek.`
- `Archivist, wait. Say that again.`
- `Ready to Verify.` after the boundary correction

Do not improvise heavily during the recorded take.

## Presenter Voiceover Script

Use this if you want a clean recorded narration track over the screen capture.

### Opening Hook

`Ghostline is a live paranormal containment hotline. The Archivist can hear me, use staged camera verification honestly, react when I interrupt, and end the call with a formal case report.`

### Permission + Grounding

`The session starts as a live call. Camera access is requested in-call, and the grounding HUD keeps the current task, path, verification state, and recovery logic visible the whole time.`

### Verification

`When I say Ready to Verify, the system captures a short hold-still window and returns confirmed, unconfirmed, or user-confirmed-only instead of overclaiming.`

### Diagnosis Beat

`Between steps, the operator adds a short diagnosis beat to classify the incident without turning the session into freeform lore.`

### Barge-In

`This interruption is real. Operator audio stops immediately, queued audio is flushed, and the Archivist restates the line cleanly.`

### Recovery Beat

`This is the controlled near-failure. The boundary appears unsealed on the first attempt, failing honestly. The HUD shows the block reason, and the recovery ladder gets us to a clean second attempt when the door is closed.`

### Closing

`The session ends with a structured case report, persisted session state, and cloud-proof instrumentation designed to make the architecture easy to verify.`

## Recording Guidance

- Keep the HUD visible whenever possible.
- Do not crop out the transcript, operator panel, or active task context.
- Keep the user answers short so the run stays under four minutes.
- Use headphones if possible so the operator audio and interruption are clear.
- If the take drifts, stop and reset with the demo procedure rather than improvising around the fixed script.

## Judged Moments Checklist

The recording is successful if it clearly shows all of these:

- opening hook
- in-call permission request
- calibration / room assessment
- visible grounding HUD
- one diagnosis beat
- one interruption
- one recovery beat
- final case report
- quick cloud / architecture reminder
