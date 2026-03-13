# Ghostline Cloud Run Backend Deployment

## Scope

This document covers Prompt 49 only: preparing the Ghostline backend for Cloud Run deployment.

It covers:

- backend container build
- Cloud Run deploy
- required runtime environment variables
- health and WebSocket expectations

It does not cover Prompt 50 cloud-proof recording workflow.

For the recording workflow itself, use [C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\CLOUD_PROOF_CHECKLIST.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\CLOUD_PROOF_CHECKLIST.md).

For the optional deployment helper added in Prompt 55, use [C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\AUTOMATED_DEPLOY.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\AUTOMATED_DEPLOY.md).

## Prerequisites

You need:

- a Google Cloud project
- Artifact Registry enabled
- Cloud Run enabled
- Vertex AI enabled
- Firestore enabled if you want session persistence in production
- `gcloud` authenticated against the target project

Recommended APIs:

- `run.googleapis.com`
- `artifactregistry.googleapis.com`
- `cloudbuild.googleapis.com`
- `aiplatform.googleapis.com`
- `firestore.googleapis.com`

## Container Layout

The backend container is defined by:

- [C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\server\Dockerfile](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\server\Dockerfile)
- [C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\server\cloud_run_entrypoint.py](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\server\cloud_run_entrypoint.py)
- [C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\server\.dockerignore](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\server\.dockerignore)
- [C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\server\.gcloudignore](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\server\.gcloudignore)

Cloud Run behavior:

- listens on `0.0.0.0`
- uses `PORT` from Cloud Run, defaulting to `8080`
- preserves FastAPI health routes
- preserves the session WebSocket route
- uses structured stdout logging for Cloud Logging

## Runtime Configuration

The backend is already environment-driven. The main runtime variables are:

- `APP_NAME`
- `APP_ENV`
- `LOG_LEVEL`
- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_LOCATION`
- `VERTEX_AI_MODEL`
- `GEMINI_LIVE_VOICE_NAME`
- `GEMINI_LIVE_VOICE_LANGUAGE_CODE`
- `GEMINI_LIVE_INPUT_TRANSCRIPTION`
- `GEMINI_LIVE_OUTPUT_TRANSCRIPTION`
- `MOCK_VERIFICATION_ENABLED`
- `DEMO_MODE_DEFAULT`
- `FIRESTORE_DATABASE`
- `FIRESTORE_SESSIONS_COLLECTION`

For Cloud Run, prefer attaching a service account to the service instead of setting `GOOGLE_APPLICATION_CREDENTIALS` to a JSON file path.

## Build And Push

Set your deployment values first:

```powershell
$PROJECT_ID = "your-gcp-project-id"
$REGION = "us-central1"
$REPOSITORY = "ghostline-images"
$IMAGE_NAME = "ghostline-backend"
$IMAGE_URI = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME"
```

If the Artifact Registry repository does not exist yet:

```powershell
gcloud artifacts repositories create $REPOSITORY --repository-format=docker --location=$REGION
```

Build and push from the server directory context:

```powershell
gcloud builds submit server --tag $IMAGE_URI
```

## Deploy To Cloud Run

Basic deploy:

```powershell
gcloud run deploy ghostline-backend `
  --image $IMAGE_URI `
  --region $REGION `
  --platform managed `
  --allow-unauthenticated `
  --port 8080 `
  --timeout 3600 `
  --set-env-vars APP_NAME=ghostline,APP_ENV=production,LOG_LEVEL=INFO,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION,VERTEX_AI_MODEL=gemini-live-2.5-flash-native-audio,GEMINI_LIVE_INPUT_TRANSCRIPTION=true,GEMINI_LIVE_OUTPUT_TRANSCRIPTION=true,MOCK_VERIFICATION_ENABLED=false,DEMO_MODE_DEFAULT=false,FIRESTORE_DATABASE=(default),FIRESTORE_SESSIONS_COLLECTION=ghostline_sessions
```

If you are using a dedicated runtime service account, attach it during deploy:

```powershell
gcloud run deploy ghostline-backend `
  --image $IMAGE_URI `
  --region $REGION `
  --platform managed `
  --service-account ghostline-backend@$PROJECT_ID.iam.gserviceaccount.com `
  --allow-unauthenticated `
  --port 8080 `
  --timeout 3600 `
  --set-env-vars APP_NAME=ghostline,APP_ENV=production,LOG_LEVEL=INFO,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION,VERTEX_AI_MODEL=gemini-live-2.5-flash-native-audio,GEMINI_LIVE_INPUT_TRANSCRIPTION=true,GEMINI_LIVE_OUTPUT_TRANSCRIPTION=true,MOCK_VERIFICATION_ENABLED=false,DEMO_MODE_DEFAULT=false,FIRESTORE_DATABASE=(default),FIRESTORE_SESSIONS_COLLECTION=ghostline_sessions
```

## Health Checks After Deploy

Replace the URL with your deployed service URL.

```powershell
Invoke-RestMethod "https://your-cloud-run-url/healthz"
Invoke-RestMethod "https://your-cloud-run-url/readyz"
```

Expected:

- `/healthz` returns `status=ok`
- `/readyz` returns `status=ready`

## WebSocket Route

The backend WebSocket route remains:

- `/ws/session`

Cloud Run supports WebSocket traffic over the same service URL. The client should connect to:

```text
wss://your-cloud-run-url/ws/session
```

## Notes

- Do not hardcode project IDs, secrets, or credential file paths in the image.
- Prefer Cloud Run service-account auth over shipping credential files.
- Keep `MOCK_VERIFICATION_ENABLED=false` in production.
- If Firestore is not configured yet, the backend still runs, but persistence will report as disabled in `/readyz`.




