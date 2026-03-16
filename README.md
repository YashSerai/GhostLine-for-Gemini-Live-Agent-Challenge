# Ghostline

Ghostline is a live paranormal containment hotline built for the **Gemini Live Agent Challenge**. The caller speaks with **The Archivist, Containment Desk**, grants microphone and camera access inside the call, scans the room, receives containment tasks, and is challenged or confirmed based on camera evidence before the session ends with a case report.

The product is voice-first, camera-aware, interruptible, and built around **Gemini Live on Vertex AI** with a React client and FastAPI/WebSocket backend.

## What The App Does

- starts from a two-mode splash: `Launch Demo Mode` or `Launch Regular Mode`
- connects the live call immediately after mode selection
- requests mic and camera access in context, not on a generic preflight page
- streams room-scan and task-monitoring frames into the live Gemini session
- keeps a visible transcript and grounding HUD during the call
- uses visual verification outcomes: `confirmed`, `unconfirmed`, `user_confirmed_only`
- provides correction guidance when a task cannot be confirmed
- ends with a structured case report and containment verdict

## Modes

- `Demo Mode`
  - fixed judged path
  - demo-specific scripted beats for reliability
  - fixed task order: `T2 -> T5 -> T14 -> T7`
- `Regular Mode`
  - same core product flow
  - session-random task path within capability constraints

## Why This Fits Live Agents

- real-time voice interaction through Gemini Live
- live camera awareness during room scan and task execution
- barge-in that interrupts operator output
- operator-led guidance instead of turn-based chat
- visible state through transcript, HUD, and verification outcomes
- Google Cloud deployment and persistence

## Quick Start

Requires **Python 3.11+**, **Node.js 18+**, and a Google Cloud project with **Vertex AI** enabled.

### Server

```powershell
cd server
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Client

```powershell
cd client
npm install
npm run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173) and choose `Launch Demo Mode` or `Launch Regular Mode`.

## Key Runtime Pieces

- `client/`
  - React/Vite UI, media capture, transcript, HUD, and control surface
- `server/`
  - FastAPI backend, WebSocket gateway, Gemini Live bridge, session state machine, verification flow
- `shared/`
  - mirrored product constants for frontend/backend state labels

## Important Docs

- [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md)
  - primary judge-facing demo flow and run guide
- [docs/DEMO_MODE.md](docs/DEMO_MODE.md)
  - concise runtime notes for demo-only behavior
- [docs/DEVPOST_SUBMISSION.md](docs/DEVPOST_SUBMISSION.md)
  - concise submission copy
- [docs/CLOUD_PROOF_CHECKLIST.md](docs/CLOUD_PROOF_CHECKLIST.md)
  - cloud proof recording checklist
- [docs/CLOUD_RUN_DEPLOYMENT.md](docs/CLOUD_RUN_DEPLOYMENT.md)
  - deployment instructions

## Useful Endpoints

- `GET /healthz`
- `GET /readyz`
- `GET /ops/proof/active-session`
- `ws://127.0.0.1:8000/ws/session`

## Notes

- `HauntLens` still appears in some historical UI text and prompt remnants. `Ghostline` is the active product name.
- Demo mode includes controlled scripting for judged reliability; it is not presented as unscripted free play.
- Verification is staged and evidence-based. The operator is expected to say when the target is missing or not visible enough to confirm.

