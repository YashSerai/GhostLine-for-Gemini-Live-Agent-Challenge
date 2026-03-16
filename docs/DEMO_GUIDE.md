# Ghostline Demo Guide

This is the primary demo document for Ghostline. Use it as the recording runbook for the judged product demo.

## 1. Demo Goal

The demo should prove that Ghostline is:

- a live voice experience
- interruptible
- camera-aware
- visually grounded during room scan and tasks
- honest about verification
- able to recover from failure without bluffing

## 2. Use Demo Mode Only

Open the app at [http://127.0.0.1:5173](http://127.0.0.1:5173) and click `Launch Demo Mode`.

Demo Mode keeps the same product structure as Regular Mode, but fixes the judged path so the run is repeatable.

Fixed demo task order:

1. `T2` Close Boundary
2. `T5` Place Paper on Flat Surface
3. `T14` Describe the Sound
4. `T7` Speak Containment Phrase

## 3. What Is Intentionally Scripted

These beats are controlled for reliability:

- demo opener branches for mic permission state
- fixed diagnosis beat around `T14`
- one controlled near-failure on `T2`
- one fixed interruption phrase
- demo reset button in the UI

These parts are still live:

- microphone access
- name confirmation
- camera access
- room-scan vision frames
- task-monitoring vision frames
- verification results
- recovery outcome
- transcript and HUD state

## 4. Room Setup Before Recording

Prepare the room so the fixed path is easy to show:

- visible doorway or threshold for `T2`
- visible flat surface for `T5`
- room is bright enough for camera verification
- camera can move between doorway and surface without confusion
- headphones if possible

Before you record, check:

- operator audio is audible
- transcript panel is readable
- HUD is visible
- camera feed is stable
- backend is connected

## 5. Exact Controlled Beats

### Near-Failure Beat

This happens on `T2`.

What you do:

1. keep the doorway visible
2. do not close it on the first verification attempt
3. say `Ready to Verify.`
4. let the operator reject the attempt honestly
5. close the door fully
6. say `Ready to Verify.` again

What the demo should show:

- an honest `unconfirmed` result
- a clear recovery line
- a successful retry

### Barge-In Beat

Use this exact phrase once during the diagnosis interpretation beat:

`Archivist, wait. Say that again.`

What the demo should show:

- operator speech interrupted
- turn state changes
- transcript reflects the interruption
- operator restates cleanly

## 6. Step-By-Step Recording Flow

### Start

1. start screen recording
2. show the splash briefly
3. click `Launch Demo Mode`

### Mic + Name

4. grant microphone access
5. say your name clearly
6. confirm your name when asked

Recommended lines:

- `My name is ...`
- `Yes.`

### Camera + Room Scan

7. grant camera access
8. perform a slow room scan
9. keep major room features visible and the motion steady

Recommended spoken line only if needed:

- `The doorway is in front of me.`

### Task 1: T2 Close Boundary

10. keep the doorway visible
11. intentionally leave it open
12. say `Ready to Verify.`
13. let the first verify fail
14. close the door fully
15. say `Ready to Verify.` again

### Task 2: T5 Place Paper on Flat Surface

16. place the paper clearly on the visible surface
17. hold still when verifying
18. say `Ready to Verify.`

### Task 3: T14 Describe the Sound

19. answer briefly when asked what the sound resembled

Recommended line:

- `It sounded like it came from the doorway.`

### Barge-In

20. wait for the diagnosis interpretation line
21. interrupt once with:

`Archivist, wait. Say that again.`

### Task 4: T7 Speak Containment Phrase

22. follow the final task instructions cleanly
23. complete the phrase and hold framing steady as needed

### Ending

24. let the case report render fully
25. hold on the report for a few seconds
26. stop recording

## 7. What Must Be Visible In The Video

A good judged take clearly shows:

- mode selection starts the call immediately
- in-call permission requests
- transcript updating live
- room scan commentary
- HUD changing with the task flow
- one honest failed verification
- one clean recovery
- one clear interruption moment
- final case report

## 8. Recommended User Lines

Keep user speech short and repeatable:

- `I need containment guidance.`
- `My name is ...`
- `Yes.`
- `Ready to Verify.`
- `It sounded like it came from the doorway.`
- `Archivist, wait. Say that again.`

## 9. Demo Timing Target

Stay under `4:00` total.

Recommended pacing:

- `0:00-0:15` splash and call start
- `0:15-0:40` mic, name, camera
- `0:40-1:00` room scan
- `1:00-1:45` `T2` with fail then retry
- `1:45-2:15` `T5`
- `2:15-2:40` `T14` diagnosis beat
- `2:40-3:00` barge-in
- `3:00-3:25` `T7`
- `3:25-3:50` case report

## 10. What To Verify Right Before Recording

Check all of these:

- call connects on mode selection
- operator audio works
- transcript updates
- camera feed is live
- room scan reaches the backend
- `Ready to Verify` works
- `unconfirmed` can appear on the first `T2` attempt
- retry can succeed
- interruption works once
- case report renders at the end

## 11. If A Take Drifts

- use `Demo Reset`
- restart from the root URL
- do not improvise around the fixed beats during the judged take
- if the interruption misses, reset and do another take
- if the first `T2` attempt accidentally succeeds, reset and redo the demo

## 12. Related Docs

- [docs/HACKATHON_SUBMISSION_GUIDE.md](docs/HACKATHON_SUBMISSION_GUIDE.md)
- [docs/DEMO_MODE.md](docs/DEMO_MODE.md)
- [docs/DEVPOST_SUBMISSION.md](docs/DEVPOST_SUBMISSION.md)
