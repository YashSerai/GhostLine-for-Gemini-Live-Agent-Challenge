# Automated Cloud Run Deploy Helper

This document exists to prove the automated deployment bonus in the public repo.

## Script

- `server/deploy-cloud-run.ps1`
- `deploy.sh`

## What It Does

The helper automates the backend Cloud Run path:

- sets the active gcloud project
- optionally creates the Artifact Registry repository
- submits the backend image build
- deploys the Cloud Run service with environment-driven settings
- prints the final service URL

It is intentionally simple. It is not full infrastructure-as-code.

## Prerequisites

Before using the helper, confirm:

- `gcloud` is installed and on PATH
- you are authenticated with `gcloud auth login`
- these APIs are enabled on the project: `run.googleapis.com`, `artifactregistry.googleapis.com`, `cloudbuild.googleapis.com`, `aiplatform.googleapis.com`
- if using a runtime service account, it already exists

## Required Environment Variables

Set at least:

- `GOOGLE_CLOUD_PROJECT`

Recommended variables:

- `GOOGLE_CLOUD_LOCATION`
- `CLOUD_RUN_SERVICE`
- `ARTIFACT_REGISTRY_REPOSITORY`
- `ARTIFACT_IMAGE_NAME`
- `APP_NAME`
- `APP_ENV`
- `LOG_LEVEL`
- `VERTEX_AI_MODEL`
- `GEMINI_LIVE_INPUT_TRANSCRIPTION`
- `GEMINI_LIVE_OUTPUT_TRANSCRIPTION`
- `MOCK_VERIFICATION_ENABLED`
- `DEMO_MODE_DEFAULT`
- `CLOUD_RUN_SERVICE_ACCOUNT`
- `CLOUD_RUN_TIMEOUT_SECONDS`

The current submission build keeps session state in memory, so Firestore configuration is not required for the judged deploy path.

## Example Usage

Basic deploy:

```powershell
$env:GOOGLE_CLOUD_PROJECT = "your-gcp-project-id"
$env:GOOGLE_CLOUD_LOCATION = "us-central1"
$env:CLOUD_RUN_SERVICE = "ghostline-backend"
$env:ARTIFACT_REGISTRY_REPOSITORY = "ghostline-images"
$env:ARTIFACT_IMAGE_NAME = "ghostline-backend"
$env:APP_ENV = "production"
$env:MOCK_VERIFICATION_ENABLED = "false"
$env:DEMO_MODE_DEFAULT = "false"

& ".\server\deploy-cloud-run.ps1"
```

First deploy where the Artifact Registry repository might not exist yet:

```powershell
& ".\server\deploy-cloud-run.ps1" -CreateRepositoryIfMissing
```

Deploy without rebuilding the image first:

```powershell
& ".\server\deploy-cloud-run.ps1" -SkipBuild
```

Deploy with a runtime service account and no public unauthenticated access:

```powershell
$env:CLOUD_RUN_SERVICE_ACCOUNT = "ghostline-backend@your-gcp-project-id.iam.gserviceaccount.com"
& ".\server\deploy-cloud-run.ps1" -NoAllowUnauthenticated
```

## Point The Local Frontend At Cloud Run

After deployment, keep the frontend local and point it at the deployed backend:

```powershell
$env:VITE_SESSION_WS_URL = "wss://YOUR-CLOUD-RUN-URL/ws/session"
cd client
& "C:\nvm4w\nodejs\npm.cmd" run dev
```

## How To Prove The Automation Bonus

In the public repo, make sure judges can see:

- `server/deploy-cloud-run.ps1`
- `deploy.sh`
- `docs/AUTOMATED_DEPLOY.md`

In Devpost, use direct GitHub links to the deploy script and this doc.

## Notes

- The helper uses environment variables instead of hardcoded project-specific values.
- It is safe to keep as a post-MVP helper because it does not alter product logic.
- The Cloud Run proof itself is already covered by the separate proof video.