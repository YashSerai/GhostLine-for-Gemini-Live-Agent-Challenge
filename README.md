# Ghostline

Ghostline is a live paranormal containment hotline built for the Gemini Live Agent Challenge.

The experience is voice-first, camera-aware, interruptible, and cloud-hosted. A caller speaks with **The Archivist, Containment Desk**, who requests camera access in-call, guides the room through a short containment protocol, verifies progress during staged **Ready to Verify** moments, handles interruption and recovery honestly, and ends the session with a structured case report.

`HauntLens` appears in some UI and historical prompt text because it was the earlier working name. Ghostline is the primary product identity.

## Why This Is A Live Agents Submission

Ghostline is designed around the challenge's Live Agents criteria:

- real-time voice interaction
- camera-aware interaction with staged verification
- natural barge-in that stops operator audio immediately
- a distinct operator persona with visible grounding
- Google Cloud hosting and persistence
- Gemini Live on Vertex AI for live multimodal interaction

This is not a chatbot skin or a fake call simulation. The call path, interruption handling, verification flow, recovery ladders, state machine, persistence, and case report are all explicit parts of the implementation.

## Feature Summary

- Live hotline call flow with **The Archivist, Containment Desk**
- In-call camera and mic permission flow
- Gemini Live audio input and output bridged through the FastAPI backend
- Always-on subtitles for user and operator transcript lines
- Grounding HUD with task, path, verification, recovery, and turn-state visibility
- Curated deterministic task system with verification and swap controls
- Honest verification results: `confirmed`, `unconfirmed`, `user_confirmed_only`
- Deterministic recovery ladders for verification failure and capability failure
- Structured case report artifact with alternate ending templates
- Demo mode with fixed path, fixed beats, and rehearsal harness
- Firestore session persistence and structured cloud-proof logging support

## Architecture Summary

### Client

- React + Vite + TypeScript
- WebSocket session manager for realtime transport
- Operator audio playback, mic capture, staged frame capture, HUD, transcript layer, control bar, demo-mode rehearsal support

### Server

- Python + FastAPI
- WebSocket gateway and authoritative session state machine
- Gemini Live session manager on Vertex AI
- Deterministic planner, verification engine, recovery logic, flavor/diagnosis libraries, case report generation
- Firestore persistence and structured logging

### Cloud

- Cloud Run for backend hosting
- Firestore for session persistence
- Cloud Logging for proof-grade operational logs
- Vertex AI / Gemini Live for realtime multimodal interaction

## Repo Layout

- `client/` frontend app
- `server/` FastAPI backend
- `shared/` shared constants and mirrored contracts
- `docs/` product, demo, build, deployment, and recording guidance
- `assets/audio/` source audio assets and notes
- `assets/demo/` demo support assets

## Source Of Truth

These documents govern the build and should be treated as canonical:

- [docs/PRODUCT_CONTEXT.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\PRODUCT_CONTEXT.md)
- [docs/DEMO_MODE.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\DEMO_MODE.md)
- [docs/BUILD_GUIDE.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\BUILD_GUIDE.md)

## Local Setup

### Prerequisites

- Node.js with `npm`
- Standard **CPython 3.11+** for the backend
- Google Cloud project with Vertex AI enabled
- Application Default Credentials or a service account JSON path

Do **not** use MSYS Python for the backend in this repo. The Google GenAI and FastAPI dependency stack expects standard CPython wheels.

### Environment Variables

Copy `.env.example` to `.env` and fill in the required values.

Important variables:

- `APP_NAME`
- `APP_ENV`
- `LOG_LEVEL`
- `VITE_SESSION_WS_URL`
- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_LOCATION`
- `VERTEX_AI_MODEL`
- `GOOGLE_APPLICATION_CREDENTIALS`
- `GEMINI_LIVE_INPUT_TRANSCRIPTION`
- `GEMINI_LIVE_OUTPUT_TRANSCRIPTION`
- `MOCK_VERIFICATION_ENABLED`
- `DEMO_MODE_DEFAULT`
- `FIRESTORE_DATABASE`
- `FIRESTORE_SESSIONS_COLLECTION`

Reference:
- [.env.example](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\.env.example)

Credential note:
- keep the credential JSON outside the repo when possible
- store only its path in `.env`
- on Cloud Run, prefer a runtime service account instead of credential files

## Running The Server

From the repo root:

```powershell
cd server
& "C:\Users\yashs\AppData\Local\Programs\Python\Python311\python.exe" -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install --upgrade pip
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
& '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If `.venv` already exists:

```powershell
cd server
& '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Useful endpoints:

- `GET /healthz`
- `GET /readyz`
- `GET /ops/proof/active-session`
- `ws://127.0.0.1:8000/ws/session`

## Running The Client

From the repo root:

```powershell
cd client
npm install
npm run dev
```

If `npm` is not on PATH on this machine:

```powershell
cd client
& 'C:\nvm4w\nodejs\npm.cmd' install
& 'C:\nvm4w\nodejs\npm.cmd' run dev
```

Default local URL:

- `http://127.0.0.1:5173`

## Demo Replay

### Normal Demo Mode

Open:

- [http://127.0.0.1:5173/?demo=1](http://127.0.0.1:5173/?demo=1)

Demo mode locks the judged path to a deterministic sequence and fixed beats.

### Rehearsal Harness

Open:

- [http://127.0.0.1:5173/?demo=1&rehearsal=1](http://127.0.0.1:5173/?demo=1&rehearsal=1)

The rehearsal harness shows the fixed demo path and whether the scripted barge-in, near-failure recovery, and final report all landed.

### Demo Procedure

Supporting demo docs:

- [docs/DEMO_PROCEDURE.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\DEMO_PROCEDURE.md) for setup and rehearsal
- [docs/DEMO_SCRIPT.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\DEMO_SCRIPT.md) for the timed recording script and shot plan
- [docs/DEVPOST_SUBMISSION.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\DEVPOST_SUBMISSION.md) for Devpost-ready submission copy
- [docs/PUBLIC_BUILD_POST.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\PUBLIC_BUILD_POST.md) for the public build post draft

## Deployment Overview

The backend is prepared for Cloud Run deployment with:

- FastAPI app entrypoint
- Dockerfile
- `.dockerignore`
- `.gcloudignore`
- environment-driven runtime config
- health endpoints and WebSocket route

Deployment docs:

- [docs/CLOUD_RUN_DEPLOYMENT.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\CLOUD_RUN_DEPLOYMENT.md)
- [docs/AUTOMATED_DEPLOY.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\AUTOMATED_DEPLOY.md)

The deployed backend is intended to run with:

- Cloud Run
- Vertex AI / Gemini Live
- Firestore
- Cloud Logging

## Cloud Proof Note

Prompt 50 adds operational support for recording the required cloud-proof clip.

Use:

- `GET /ops/proof/active-session` to identify the active demo session
- Firestore `proof.*` fields to find the same session document
- structured log events such as `cloud_proof_session_locator`, `session_started`, `gemini_live_session_created`, and `case_report_generated`

Recording checklist:

- [docs/CLOUD_PROOF_CHECKLIST.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\CLOUD_PROOF_CHECKLIST.md)

## Privacy And Safety Notes

Ghostline is designed around procedural containment fiction, but the implementation still takes privacy and safety boundaries seriously.

- camera and mic are requested **in-call**, not as generic pre-setup
- the system should only use staged verification windows, not pretend to see more than it can verify
- the operator is required to express uncertainty honestly
- the product should not identify people in frame, profile users, or tie behavior to personal traits
- raw media is not intended as long-term storage; the cloud-native path emphasizes structured state and event persistence instead
- mock verification should remain disabled for serious demo and cloud-proof runs unless a prompt explicitly requires it

## Headphones Recommended

Headphones are recommended for the best demo and rehearsal experience.

They are not required, but they help with:

- hearing subtle operator lines
- keeping pre-baked ambience readable without masking speech
- making the barge-in and audio-ducking behavior easier to hear clearly

## Additional Docs

- [server/README.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\server\README.md)
- [docs/CLOUD_RUN_DEPLOYMENT.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\CLOUD_RUN_DEPLOYMENT.md)
- [docs/AUTOMATED_DEPLOY.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\AUTOMATED_DEPLOY.md)
- [docs/CLOUD_PROOF_CHECKLIST.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\CLOUD_PROOF_CHECKLIST.md)
- [docs/DEMO_PROCEDURE.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\DEMO_PROCEDURE.md)
- [docs/DEMO_SCRIPT.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\DEMO_SCRIPT.md)
- [docs/DEVPOST_SUBMISSION.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\DEVPOST_SUBMISSION.md)
- [docs/PUBLIC_BUILD_POST.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\PUBLIC_BUILD_POST.md)

## Status

This repository now includes the core Ghostline lifecycle end to end:

- live call transport
- Gemini Live audio bridge
- staged verification
- deterministic planner and state machine
- interruption and recovery
- case report generation
- demo mode and rehearsal support
- cloud deployment and proof instrumentation






