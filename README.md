# Ghostline Monorepo

Ghostline is a live paranormal containment hotline built for the Gemini Live Agent Challenge.
The build guide still references the earlier working name `HauntLens`; this repository uses `Ghostline` as the primary product name while preserving that historical continuity.

This repository is intentionally locked to one stack and one architecture direction:

- Frontend: React + Vite + TypeScript
- Backend: Python + FastAPI
- Google AI integration: Google GenAI SDK using Gemini Live on Vertex AI
- Cloud target: Cloud Run + Firestore + Cloud Logging
- Realtime client/backend transport: WebSocket

No substitutions are planned for this scaffold.
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

These documents define the product concept, demo constraints, and the phased implementation plan.

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

### Backend Setup

From the repo root:

```powershell
cd server
python -m venv .venv
& '.\.venv\bin\python.exe' -m pip install --upgrade pip
& '.\.venv\bin\python.exe' -m pip install -r requirements.txt
& '.\.venv\bin\python.exe' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The FastAPI development server is configured for `http://127.0.0.1:8000`.

## Current Scope

This repository currently covers the foundation and transport checkpoint through Prompts 1-7:

- monorepo scaffold and locked stack
- Vite React TypeScript client workspace
- FastAPI backend workspace with config, logging, and health endpoints
- shared constants skeleton for frontend/backend alignment
- hotline-style frontend shell
- backend WebSocket session gateway
- client WebSocket session manager and shell connection state

No Gemini integration, live media, or product protocol logic has been implemented yet.
