# Ghostline Demo Procedure

## Purpose

This document is the operator-facing runbook for rehearsing and recording the Ghostline demo path that exists today.

It is aligned to:

- [C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\PRODUCT_CONTEXT.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\PRODUCT_CONTEXT.md)
- [C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\DEMO_MODE.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\DEMO_MODE.md)
- [C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\BUILD_GUIDE.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\BUILD_GUIDE.md)

Use this for:

- rehearsal
- recording the judged demo
- repeatable demo resets between takes

## Fixed Demo Path

The implemented fixed demo path is:

1. `T1` Show Threshold
2. `T2` Close Boundary
3. `T3` Increase Illumination
4. `T4` Stabilize Camera
5. `T6` Clear Small Surface
6. `T7` Speak Containment Phrase

The implemented controlled demo beats are:

- one fixed diagnosis beat
- one fixed barge-in moment
- one fixed near-failure and recovery beat

The exact demo barge-in phrase is:

`Archivist, wait. Say that again.`

The controlled near-failure is fixed to:

- task `T3`
- failure type `temporary_low_light`

## Before You Record

Prepare the room so the demo path is easy to execute:

- use a visible doorway or threshold
- use a lamp or overhead light you can brighten on cue
- have one small flat surface visible
- keep the camera handheld but stable enough to recover on cue
- use headphones if possible so operator audio is clean and barge-in is easy to hear

Keep the camera framing simple:

- doorway visible early
- light source reachable
- small surface reachable

## Environment Setup

The backend must use the repo CPython virtualenv, not MSYS Python.

Backend:

```powershell
cd "C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\server"
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Client:

```powershell
cd "C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\client"
& "C:\nvm4w\nodejs\npm.cmd" run dev
```

Optional production-style build check before recording:

```powershell
cd "C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\client"
& "C:\nvm4w\nodejs\npm.cmd" run build
```

## URLs

Use these exact URLs:

- rehearsal mode: [http://127.0.0.1:5173/?demo=1&rehearsal=1](http://127.0.0.1:5173/?demo=1&rehearsal=1)
- recording mode: [http://127.0.0.1:5173/?demo=1](http://127.0.0.1:5173/?demo=1)

Use rehearsal mode until all four rehearsal checks pass. Record from plain demo mode after that.

## Rehearsal Procedure

1. Open rehearsal mode.
2. Confirm the `Demo Rehearsal Harness` panel is visible.
3. Confirm the fixed path check shows:
   `T1 -> T2 -> T3 -> T4 -> T6 -> T7`
4. Run the demo once without recording.
5. Confirm the harness advances through:
   - fixed demo path
   - controlled barge-in
   - near-failure recovery beat
   - final case report
6. Use `Demo Reset` between takes.
7. Do not start recording until the harness gives a clean pass on all key beats.

## Recording Procedure

1. Open plain demo mode at `?demo=1`.
2. Start screen recording with system audio and microphone narration if needed.
3. Click `Start Call`.
4. Follow the fixed path exactly.
5. Use the scripted interruption phrase at the barge-in moment.
6. Intentionally let the first verification on `T3` fail.
7. Correct the lighting and rerun verification.
8. Finish the path through the final case report.
9. Stop recording only after the report and closing line are visible.

## User Demo Script

Use short, clean lines. Do not improvise heavily.

### Opening

User:

`I need containment guidance.`

### Camera Request / Calibration

When the Archivist asks for camera:

- grant camera access
- point the camera at the doorway

If you need a short spoken line:

`The doorway is in front of me.`

### First Task

When the Archivist assigns the first task:

- do the task cleanly
- keep the frame stable

Use:

`Ready to Verify.`

### Diagnosis Beat

When the Archivist asks the diagnosis question, answer briefly.

Recommended answer:

`It sounded like it came from the doorway.`

### Controlled Barge-In

Wait for the scripted diagnosis interpretation line, then interrupt with the exact phrase:

`Archivist, wait. Say that again.`

Do not paraphrase this during the recorded take.

### Controlled Near-Failure

At `T3 Increase Illumination`:

- let the first verification happen while the frame is still slightly too dim
- accept the unconfirmed result
- follow the recovery line
- brighten the light

Then say:

`Ready to Verify.`

### Final Closure

Complete the remaining fixed tasks and let the report render.

## Presenter Narration Script

Use this only if you are narrating over the capture or recording a separate voiceover.

### Opening Hook

`Ghostline is a live paranormal containment hotline built for the Gemini Live Agent Challenge. The Archivist can hear me, react when I interrupt, use staged camera verification honestly, and end the session with a formal case report.`

### Permission and Grounding

`The call starts first. Camera and mic access happen in context, and the HUD stays visible so the current task, path, verification state, and recovery logic are always inspectable.`

### First Verification

`The system does not bluff. I perform a task, say Ready to Verify, hold still, and the backend returns confirmed, unconfirmed, or user-confirmed-only.`

### Barge-In

`This next beat is a real interruption. Operator audio stops immediately, stale audio is flushed, and the Archivist restates the instruction cleanly.`

### Recovery

`This is the controlled demo near-failure. The first verification fails honestly, the HUD shows the block reason, and the recovery ladder gives one corrective instruction before the second attempt succeeds.`

### Closing

`The session ends with a structured case report, stored session state, and a deterministic verdict path designed for a repeatable under-four-minute demo.`

## Timing Guide

Use this target pacing:

- `0:00-0:20` Hook and framing
- `0:20-0:40` Call pickup and in-call permissions
- `0:40-1:05` Threshold and calibration
- `1:05-1:35` First task and first verification
- `1:35-1:55` Diagnosis beat
- `1:55-2:20` Controlled barge-in
- `2:20-2:55` Controlled near-failure and recovery
- `2:55-3:20` Final anchor and closure
- `3:20-3:45` Case report

## What To Watch During The Take

The demo is good if all of these are visible:

- in-call permission flow
- live transcript
- readable grounding HUD
- fixed task progression
- one interruption
- one honest unconfirmed result
- one clean recovery
- final case report

## Current Risks And Known Limits

These are the main remaining risks in the current Prompt 43-48 implementation:

- The rehearsal harness is a developer-facing frontend checklist driven by session-state payloads. It is not an external test runner.
- Demo reset is a client-driven clean teardown plus reload. It is fast and practical, but it is not a separate backend reset protocol.
- The controlled barge-in depends on the exact phrase match:
  `Archivist, wait. Say that again.`
- The controlled near-failure is hard-wired to task `T3`. If the demo drifts off the fixed path, that beat will not land correctly.
- Live browser audio timing, device permissions, and speaker routing still matter. Rehearse on the exact machine and browser you will record with.
- Firestore and Cloud Logging proof still require a live cloud-connected run. This document only covers the local demo procedure.

## Troubleshooting

If the demo drifts:

- use `Demo Reset`
- reopen `?demo=1&rehearsal=1`
- confirm the fixed path is still `T1 -> T2 -> T3 -> T4 -> T6 -> T7`

If the barge-in does not register:

- use the exact phrase
- interrupt on the scripted diagnosis interpretation line
- avoid adding extra words before the phrase

If the near-failure does not trigger:

- make sure you are on `T3`
- keep the first verification slightly dim
- correct the light only after the first unconfirmed result

If the take feels slow:

- shorten user answers
- do not over-explain during the call
- keep presenter narration separate from the operator exchange
