# Ghostline Monorepo

Ghostline is a live paranormal containment hotline built for the Gemini Live Agent Challenge.
The build guide still references the earlier working name `HauntLens`; this repository uses `Ghostline` as the primary product name while preserving that historical continuity.

This repository is intentionally locked to one stack and one architecture direction:

- Frontend: React + Vite + TypeScript
- Backend: Python + FastAPI
- Google AI integration: Google GenAI SDK using Gemini Live on Vertex AI
- Cloud target: Cloud Run + Firestore + Cloud Logging
- Realtime client/backend transport: WebSocket

No substitutions are planned for this build.
That means no SSR, no Next.js, no Angular, no Vue, and no Node backend.

## Repo Structure

- `client/`: React + Vite + TypeScript frontend workspace
- `server/`: Python + FastAPI backend workspace
- `shared/`: contracts and shared definitions mirrored across client and server
- `docs/`: source-of-truth product, demo, and build guidance
- `assets/audio/`: pre-baked audio assets for the hotline experience
- `assets/demo/`: demo and rehearsal support assets

## Source Of Truth

Before implementing features, follow these documents:

- `docs/PRODUCT_CONTEXT.md`
- `docs/DEMO_MODE.md`
- `docs/BUILD_GUIDE.md`

## Local Development

Client and server are started independently on purpose.
This repository does not use a single-process dev command at this stage.

### Frontend Setup

From the repo root:

```powershell
cd client
npm install
npm run dev
```

If `npm` is not on your PATH on this machine, use:

```powershell
& 'C:\nvm4w\nodejs\npm.cmd' install
& 'C:\nvm4w\nodejs\npm.cmd' run dev
```

The Vite dev server is configured for `http://127.0.0.1:5173`.
`client/vite.config.ts` points `envDir` at the repo root, so `VITE_SESSION_WS_URL` can live in the root `.env` file.

### Backend Setup

Use a standard CPython 3.11+ interpreter for Gemini Live dependencies.
The Google GenAI SDK may not install cleanly under MSYS Python builds.
On this machine, do not use plain `python` for backend setup because it resolves to `C:\msys64\mingw64\bin\python.exe`.

From the repo root:

```powershell
cd server
& "C:\Users\yashs\AppData\Local\Programs\Python\Python311\python.exe" -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install --upgrade pip
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
& '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If `.venv` already exists, run the backend with:

```powershell
cd server
& '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The FastAPI development server is configured for `http://127.0.0.1:8000`.
The backend loads the repo-root `.env` automatically, and relative `GOOGLE_APPLICATION_CREDENTIALS` paths are resolved from the repo root.

### Credential Note

Keep the Google service-account JSON outside this repo when possible and store only its filesystem path in `.env`.
If your credentials file is already outside the repo, you do not need to move it.
If it is currently inside the repo, move it out and keep only the path in `.env`.

## Current Scope

This repository now covers Prompts 1-13 from `docs/BUILD_GUIDE.md`:

- monorepo scaffold and locked stack
- Vite React TypeScript client workspace
- FastAPI backend workspace with config, logging, and health endpoints
- shared constants skeleton for frontend/backend alignment
- hotline UI shell
- backend WebSocket session gateway
- client WebSocket session manager and connection state
- backend Gemini Live session manager for Vertex AI
- client mic PCM capture streamed through the backend to Gemini Live
- Gemini operator audio streamed back to the client for low-latency playback
- in-call camera preview with low-frequency staged frame capture for calibration and Ready to Verify windows
- in-call camera and microphone permission flow driven from the operator panel
- always-on user and operator transcript layer with preserved short-call context

Planner logic, verification, and case reports remain out of scope for this checkpoint.



