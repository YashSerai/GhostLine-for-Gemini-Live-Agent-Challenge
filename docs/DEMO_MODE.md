# Ghostline Demo Mode Notes

This document is the concise runtime note for Demo Mode. It exists to document what is intentionally demo-only in the current implementation.

## Purpose

Demo Mode is the reliability path for recorded judging. It is not a different product. It keeps the same live-call structure while constraining task order and a few operator beats so the walkthrough is repeatable.

## Current Demo-Only Behavior

- fixed task order: `T2 -> T5 -> T14 -> T7`
- demo opener branches on browser mic permission state
- fixed mic-confirmed line
- fixed camera-request line
- fixed room-scan instruction line
- fixed room-scan assessment line
- fixed diagnosis question and interpretation beat
- fixed barge-in phrase target
- demo reset button in the client

## Important Verification Note

Demo Mode no longer forces a failed verification or scripted recovery outcome.

If you want to show recovery during a recording, create it naturally by doing the task incorrectly on purpose, then retrying after the operator rejects it.

## Controlled Demo Beats

### Barge-In

- expected interruption phrase: `Archivist, wait. Say that again.`
- intended effect: operator audio stops, turn state changes, line is restated

## What Demo Mode Does Not Claim

- it does not claim unlimited improvisation
- it does not claim that every line is unscripted
- it does not replace the real verification pipeline
- it does not add a separate hidden game system outside the normal call flow
- it does not force verification failures behind the scenes

## Judge-Facing Reference

Use [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) as the main demo walkthrough.
