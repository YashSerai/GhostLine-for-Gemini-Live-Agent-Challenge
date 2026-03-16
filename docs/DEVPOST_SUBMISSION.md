# Ghostline Devpost Submission

This document is the concise submission copy for Ghostline.

## One-Sentence Pitch

Ghostline turns the usual AI voice demo into a live containment hotline: the user talks to a distinct operator, grants camera and microphone access in context, performs real-world steps in the room, interrupts the operator in real time, and only advances when the system can honestly verify what it sees.

## Project Summary

Ghostline is a live paranormal containment hotline built for the Gemini Live Agent Challenge. A caller speaks with **The Archivist, Containment Desk**, grants microphone and camera access inside the call, scans the room, completes containment tasks, and is challenged or confirmed based on camera evidence before the session ends with a structured case report.

## Problem And Why It Matters

Most AI voice demos still feel like chatbots with audio. Ghostline explores a stronger multimodal pattern: a live, camera-aware, interruptible agent with visible grounding, bounded verification, and recovery when visual evidence is weak.

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
| Cloud | Cloud Run, Cloud Logging, Cloud Build, Artifact Registry |

## Cloud And Deployment Notes

- backend deployed to Google Cloud Run
- structured operational events emitted to Cloud Logging
- proof endpoint available at `/ops/proof/active-session`
- repo includes an automated deploy helper in `server/deploy-cloud-run.ps1`
- current submission build keeps session persistence in memory for runtime reliability

## Other Data Sources

- no external third-party data feeds are required for the core experience
- the system relies on live microphone audio, live camera frames, authored task definitions, and bounded backend state

## Key Learnings

1. barge-in quality strongly affects whether the product feels live or scripted
2. staged verification works better than bluffing continuous certainty
3. visible HUD state makes the operator feel more trustworthy
4. a constrained demo path is better for judging than a fragile open-ended path
5. recovery lines are more convincing when they explicitly mention what is missing from view

## Architecture Reference

See [docs/ARCHITECTURE_DIAGRAM.md](docs/ARCHITECTURE_DIAGRAM.md) and [docs/ARCHITECTURE_DIAGRAM.mmd](docs/ARCHITECTURE_DIAGRAM.mmd).

## Submission Links To Replace

- Public repo URL: `https://github.com/YashSerai/GhostLine-for-Gemini-Live-Agent-Challenge/tree/main`
- Demo video URL: `https://youtu.be/hWQC8xShboc`
- Cloud proof clip URL: `https://youtu.be/E_zhS5PGLcA`
- Cloud Run backend URL: `recorded separately in the Cloud proof clip`
- Build article URL: `https://x.com/yashns1/status/2033619323328290956`
- X post or thread URL: `https://x.com/yashns1/status/2033619323328290956`
- GDG or public Google Developer profile URL: `https://gdg.community.dev/u/mjb99k/`

## Bonus Links To Replace

- Automated deployment proof link: `https://github.com/YashSerai/GhostLine-for-Gemini-Live-Agent-Challenge/blob/main/deploy.sh`
- Automated deployment setup doc: `https://github.com/YashSerai/GhostLine-for-Gemini-Live-Agent-Challenge/blob/main/docs/AUTOMATED_DEPLOY.md`
- Architecture diagram upload: `docs/ARCHITECTURE_DIAGRAM.png`

## Additional Details Copy For Devpost

Use a short block like this in the additional details section:

`Cloud proof clip: https://youtu.be/E_zhS5PGLcA.`

`Automated deployment: the backend deploy to Cloud Run is scripted in https://github.com/YashSerai/GhostLine-for-Gemini-Live-Agent-Challenge/blob/main/deploy.sh with setup notes in https://github.com/YashSerai/GhostLine-for-Gemini-Live-Agent-Challenge/blob/main/docs/AUTOMATED_DEPLOY.md.`

`Build article: https://x.com/yashns1/status/2033619323328290956.`

`Optional X share: https://x.com/yashns1/status/2033619323328290956.`

`Google Developer Group / public developer profile: https://gdg.community.dev/u/mjb99k/.`

## Honesty Notes

- verification is evidence-based and can return `unconfirmed`
- demo mode is intentionally constrained for repeatability
- regular mode is still bounded by the authored task library and verification flow
- the product aims to say when something is missing from frame instead of pretending to see it
- the current submission build does not claim Firestore-backed persistence in the cloud proof flow


