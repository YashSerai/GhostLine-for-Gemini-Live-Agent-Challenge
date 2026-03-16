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
- Google Cloud deployment and operational proof

## Quick Start

This repo is currently set up to be judged and reproduced **locally**. The Cloud Run backend used for the submission proof video has been taken down, so judges should follow the local spin-up path below.

Requires **Python 3.11+**, **Node.js 18+**, and a Google Cloud project with **Vertex AI** enabled.

### 1. Configure environment values

From the repo root, copy `.env.example` to `.env` and fill in the Google Cloud values you actually use:

```powershell
Copy-Item .env.example .env
```

Minimum required values in `.env`:

- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_LOCATION=us-central1`
- `GOOGLE_APPLICATION_CREDENTIALS`
- `VITE_SESSION_WS_URL=ws://127.0.0.1:8000/ws/session`

Notes:

- `GOOGLE_APPLICATION_CREDENTIALS` should point to a local service-account JSON file that can access Vertex AI. Keep that JSON file outside the repo.
- `MOCK_VERIFICATION_ENABLED=false` is the intended submission setting.
- Firestore is not required for the current judged path. The current build keeps session state in memory.

### 2. Start the backend

Open a terminal in the repo root and run:

```powershell
cd server
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The backend should now be available at `http://127.0.0.1:8000`.

Quick check:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/readyz"
```

### 3. Start the frontend

Open a second terminal in the repo root and run:

```powershell
cd client
npm install
npm run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173).

### 4. Run the product locally

For the judged walkthrough, choose `Launch Demo Mode`.

For normal product behavior, choose `Launch Regular Mode`.

Local runtime expectations:

- backend websocket endpoint: `ws://127.0.0.1:8000/ws/session`
- frontend dev server: `http://127.0.0.1:5173`
- backend readiness endpoint: `http://127.0.0.1:8000/readyz`

### 5. Judge notes

- The project is reproducible locally with the steps above.
- The separate Cloud proof video shows the backend running on Google Cloud Run during submission.
- If you only want the judged flow, use `Launch Demo Mode` after both local processes are running.

## Important Docs

- [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md)
  - primary judge-facing demo flow and run guide
- [docs/DEMO_MODE.md](docs/DEMO_MODE.md)
  - concise runtime notes for demo-only behavior
- [docs/AUTOMATED_DEPLOY.md](docs/AUTOMATED_DEPLOY.md)
  - automated Cloud Run deployment proof for the bonus category
- [docs/ARCHITECTURE_DIAGRAM.png](docs/ARCHITECTURE_DIAGRAM.png)
  - judge-facing architecture asset
- [docs/ARCHITECTURE_DIAGRAM.mmd](docs/ARCHITECTURE_DIAGRAM.mmd)
  - Mermaid source for the architecture diagram

## Useful Endpoints

- `GET /readyz`
- `GET /ops/proof/active-session`
- `ws://127.0.0.1:8000/ws/session`

## Notes

- `HauntLens` still appears in some historical UI text and prompt remnants. `Ghostline` is the active product name.
- Demo mode includes controlled scripting for judged reliability; it is not presented as unscripted free play.
- Verification is staged and evidence-based. The operator is expected to say when the target is missing or not visible enough to confirm.
- The current submission build keeps session state in memory and proves cloud execution through Cloud Run, `/ops/proof/active-session`, Cloud Logging, and Gemini lifecycle events rather than Firestore persistence.