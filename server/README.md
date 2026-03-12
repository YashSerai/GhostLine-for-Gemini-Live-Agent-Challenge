# Server Workspace

This directory contains the Ghostline backend scaffold.

Stack:
- Python
- FastAPI

Local commands:

```powershell
python -m venv .venv
& '.\.venv\bin\python.exe' -m pip install --upgrade pip
& '.\.venv\bin\python.exe' -m pip install -r requirements.txt
& '.\.venv\bin\python.exe' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health endpoints:
- `GET /healthz`
- `GET /readyz`

WebSocket endpoint:
- `ws://127.0.0.1:8000/ws/session`

Accepted placeholder message types:
- `client_connect`
- `mic_status`
- `camera_status`
- `transcript`
- `frame`
- `verify_request`
- `swap_request`
- `pause`
- `stop`

Environment-backed settings currently include:
- `APP_NAME`
- `APP_ENV`
- `LOG_LEVEL`
- `SERVER_HOST`
- `SERVER_PORT`
- `CLIENT_HOST`
- `CLIENT_PORT`
- `SERVER_CORS_ORIGINS` (optional comma-separated override)

This workspace intentionally contains only the Prompt 6 and Prompt 7 checkpoint scaffold.
No Gemini or product session logic is implemented yet.
