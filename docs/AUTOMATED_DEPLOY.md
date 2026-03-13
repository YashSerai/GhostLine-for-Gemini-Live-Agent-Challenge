# Automated Cloud Run Deploy Helper

This note documents the optional deploy helper added for Prompt 55.

## Script

- [C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\server\deploy-cloud-run.ps1](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\server\deploy-cloud-run.ps1)

## Scope

The script automates the backend Cloud Run deployment steps already described in the deployment guide:

- set the active gcloud project
- optionally create the Artifact Registry repository
- submit the backend build
- deploy the Cloud Run service with environment-driven settings
- print the final service URL

It is intentionally simple. It is not Terraform or full infrastructure-as-code.

## Prerequisites

Before using the script, confirm:

- `gcloud` is installed and on PATH
- you are authenticated with `gcloud auth login`
- if using a runtime service account, it already exists
- the required APIs are enabled as described in [C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\CLOUD_RUN_DEPLOYMENT.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\CLOUD_RUN_DEPLOYMENT.md)

## Required Environment Variables

Set these before running the helper:

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
- `FIRESTORE_DATABASE`
- `FIRESTORE_SESSIONS_COLLECTION`
- `CLOUD_RUN_SERVICE_ACCOUNT`
- `CLOUD_RUN_TIMEOUT_SECONDS`

Defaults are built into the script for the optional variables so the helper stays simple.

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

## Notes

- The script uses environment variables instead of hardcoded project-specific values.
- It is safe to keep as a post-MVP helper because it does not alter product logic.
- For cloud-proof recording after deployment, use [C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\CLOUD_PROOF_CHECKLIST.md](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\CLOUD_PROOF_CHECKLIST.md).
