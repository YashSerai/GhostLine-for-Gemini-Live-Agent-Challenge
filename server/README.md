# Server Workspace

This directory contains the Ghostline FastAPI backend and the Gemini Live audio bridge.

Stack:
- Python
- FastAPI
- Google GenAI SDK on Vertex AI

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

## Endpoints

Health endpoints:
- `GET /healthz`
- `GET /readyz`

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

Server-generated transport messages during this checkpoint:
- ack envelopes that mirror the accepted message type
- `operator_audio_chunk`
- `operator_interruption`
- `transcript`
- `error`

## Environment Notes

The backend loads the repo-root `.env` automatically.
Relative `GOOGLE_APPLICATION_CREDENTIALS` paths are resolved from the repo root so the same `.env` file can be reused from local dev commands.

Recommended practice:
- keep the Google service-account JSON outside the repo
- store only its path in `.env`

## Current Backend Scope

The backend now covers Prompts 4, 6, 8, 9, 10, and 13:

- FastAPI app with config, health endpoints, and structured logging
- session WebSocket gateway with guarded JSON envelopes
- backend Gemini Live session manager on Vertex AI
- client mic PCM forwarding to Gemini Live
- Gemini operator audio streamed back to the client as low-latency chunks
- interruption metadata forwarded as a playback-control hook for later prompts
- Gemini Live transcript events forwarded to the client transcript layer
- logging for audio bridge start, stop, input forwarding, output forwarding, and transcript forwarding

Camera frames, planner logic, verification, and case reports remain out of scope until later prompts.
