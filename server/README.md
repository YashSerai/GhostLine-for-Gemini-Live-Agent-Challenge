# Server Workspace

This directory contains the Ghostline FastAPI backend and the Gemini Live audio bridge.

Stack:
- Python
- FastAPI
- **Google GenAI SDK** interacting with Gemini Live on Vertex AI

## Local Commands

Use a standard CPython 3.11+ interpreter for Gemini Live dependencies.
The Google GenAI SDK may not install cleanly under MSYS Python builds.

```powershell
& "C:\Users\yashs\AppData\Local\Programs\Python\Python311\python.exe" -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install --upgrade pip
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
& '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If `.venv` already exists, run the server with:

```powershell
& '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Cloud Run Deployment

Cloud Run deployment files now live here:

- [C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\server\Dockerfile](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\server\Dockerfile)
- [C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\server\cloud_run_entrypoint.py](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\server\cloud_run_entrypoint.py)
- [C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\server\.dockerignore](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\server\.dockerignore)
- [C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\server\.gcloudignore](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\server\.gcloudignore)

Deployment notes are in:

- [C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\CLOUD_RUN_DEPLOYMENT.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\CLOUD_RUN_DEPLOYMENT.md)
- [C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\CLOUD_PROOF_CHECKLIST.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\CLOUD_PROOF_CHECKLIST.md)

## Endpoints

Health endpoints:
- `GET /healthz`
- `GET /readyz`
- `GET /ops/proof/active-session`

WebSocket endpoint:
- `ws://127.0.0.1:8000/ws/session`

Accepted client message types:
- `client_connect`
- `mic_status`
- `audio_chunk`
- `camera_status`
- `transcript`
- `frame`
- `verify_request`
- `swap_request`
- `pause`
- `stop`

## Environment Notes

The backend loads the repo-root `.env` automatically in local development.
Relative `GOOGLE_APPLICATION_CREDENTIALS` paths are resolved from the repo root so the same `.env` file can be reused from local dev commands.

Recommended practice:
- keep the Google service-account JSON outside the repo
- store only its path in `.env`
- on Cloud Run, prefer attaching a runtime service account instead of mounting a credentials file



