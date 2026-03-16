# Ghostline Devpost Submission

This document is the concise submission copy for Ghostline.

## Project Summary

Ghostline is a live paranormal containment hotline built for the Gemini Live Agent Challenge. A caller speaks with **The Archivist, Containment Desk**, grants microphone and camera access inside the call, scans the room, completes containment tasks, and is challenged or confirmed based on camera evidence before the session ends with a structured case report.

## Core Functionality

- real-time voice interaction through Gemini Live on Vertex AI
- camera-aware room scan during the live session
- interruptible operator audio with barge-in handling
- live transcript and grounding HUD during the call
- task progression with visual verification outcomes
- honest recovery guidance when a task cannot be confirmed
- fixed judged demo mode and session-random regular mode
- structured case report with verdict and task outcomes

## What Makes It A Live Agents Project

Ghostline is not a turn-based chatbot. The operator is meant to feel like a live incident desk:

- hears the caller in real time
- speaks back in real time
- reacts to interruption
- requests camera access in context
- watches the room during scan and task execution
- uses camera evidence during verification

## Demo Mode

Demo Mode exists for judged reliability.

It keeps the same core flow, but constrains the run to:

- fixed task order: `T2 -> T5 -> T14 -> T7`
- one controlled diagnosis beat
- one controlled barge-in phrase
- optional natural recovery if the caller intentionally fails a step on camera

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React, Vite, TypeScript |
| Backend | Python, FastAPI, WebSocket |
| AI | Google GenAI SDK, Gemini Live on Vertex AI |
| Cloud | Cloud Run, Firestore, Cloud Logging |

## Key Learnings

1. barge-in quality strongly affects whether the product feels live or scripted
2. staged verification works better than bluffing continuous certainty
3. visible HUD state makes the operator feel more trustworthy
4. a constrained demo path is better for judging than a fragile open-ended path
5. recovery lines are more convincing when they explicitly mention what is missing from view

## Architecture Reference

See [docs/ARCHITECTURE_DIAGRAM.md](docs/ARCHITECTURE_DIAGRAM.md) and [docs/ARCHITECTURE_DIAGRAM.mmd](docs/ARCHITECTURE_DIAGRAM.mmd).

## Honesty Notes

- verification is evidence-based and can return `unconfirmed`
- demo mode is intentionally constrained for repeatability
- regular mode is still bounded by the authored task library and verification flow
- the product aims to say when something is missing from frame instead of pretending to see it
