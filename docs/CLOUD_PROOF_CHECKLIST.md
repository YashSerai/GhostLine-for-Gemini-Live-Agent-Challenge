# Ghostline Cloud Proof Recording Checklist

## Purpose

This document is the internal runbook for recording the required cloud proof clip for Ghostline.

It assumes the backend is already deployed to Cloud Run.

Use this document to capture proof of:

- Cloud Run service
- readiness and proof endpoint availability
- active session ID
- Cloud Logging events
- Gemini / Vertex usage evidence

## Prerequisites

Before recording, confirm:

- the backend is deployed to Cloud Run
- Vertex AI is enabled in the same project
- the frontend is pointing at the deployed backend
- you can open `/readyz` on the deployed backend
- you can open `/ops/proof/active-session` on the deployed backend

## Required Service Surfaces

You need these available during the recording:

- Cloud Run service details page
- Cloud Logging Logs Explorer
- Ghostline running against the deployed backend
- readiness endpoint:
  - `/readyz`
- proof endpoint:
  - `/ops/proof/active-session`

## Recommended Recording Order

Use this order so the proof clip is short and easy to follow.

1. Show the Cloud Run service.
2. Show `/readyz` returning `status=ready`.
3. Show the running Ghostline session start.
4. Open `/ops/proof/active-session` and capture the active session ID.
5. Use that session ID in Cloud Logging.
6. Show a Gemini / Vertex evidence log event.

## Step-By-Step Procedure

### 1. Show the Cloud Run service

In the Cloud Console, show:

- the Cloud Run service name
- the region
- the service URL
- the latest healthy revision

Optional but useful:

- environment variables panel
- attached service account

### 2. Show readiness quickly

Open:

```text
https://your-cloud-run-url/readyz
```

Capture these fields if possible:

- `status`
- `service`
- `verificationEngine`
- `sessionPersistence`
- `cloudProofEndpoint`

For the current submission build, `sessionPersistence` should read `in_memory`.

### 3. Open the deployed app and start a session

Start one clean live session against the deployed backend.

You want a fresh session because the proof endpoint will then show one clear active session.

### 4. Open the proof locator endpoint

Open:

```text
https://your-cloud-run-url/ops/proof/active-session
```

Capture these fields on screen:

- `serviceName`
- `project`
- `activeSession.sessionId`
- `activeSession.state`
- `activeSession.currentStep`
- `activeSession.logQueryHint`
- `expectedLogEvents`

That `activeSession.sessionId` is the session ID you will reuse in Cloud Logging.

### 5. Show Cloud Logging for the active session

In Logs Explorer, filter by the active session ID from the proof endpoint.

Use a filter like:

```text
resource.type="cloud_run_revision"
jsonPayload.session_id="YOUR_SESSION_ID"
```

If you want to show the exact proof event first, use:

```text
resource.type="cloud_run_revision"
jsonPayload.event="cloud_proof_session_locator"
jsonPayload.session_id="YOUR_SESSION_ID"
```

Recommended events to show:

- `cloud_proof_session_locator`
- `session_started`
- `gemini_live_session_created`
- `verification_result`
- `case_report_generated`

### 6. Show Gemini / Vertex evidence

The simplest evidence is the structured backend log event:

- `gemini_live_session_created`

Use this Logs Explorer filter:

```text
resource.type="cloud_run_revision"
jsonPayload.event="gemini_live_session_created"
jsonPayload.session_id="YOUR_SESSION_ID"
```

That proves the live session touched the Gemini / Vertex path for the same session you just showed through the proof endpoint and Cloud Logging.

## Minimal Proof Clip Script

Use this as a concise narration guide.

1. `This is the Ghostline backend deployed on Cloud Run.`
2. `This readiness endpoint shows the deployed service is healthy and that the current submission build is using in-memory session persistence.`
3. `I start one live session and open the proof endpoint to capture the active session ID.`
4. `Now I use that same session ID in Cloud Logging to show the structured session lifecycle.`
5. `Finally, I show the Gemini Live session creation event for that same session ID.`

## What Good Proof Looks Like

The proof clip is successful if a viewer can easily follow one session ID through all of these surfaces:

- Cloud Run service
- readiness endpoint
- operational proof endpoint
- Cloud Logging
- Gemini / Vertex evidence log

## Troubleshooting

If `/ops/proof/active-session` returns no active session:

- start a fresh call in Ghostline
- refresh the endpoint
- confirm the backend is the deployed backend, not local dev

If logs are noisy:

- filter by `jsonPayload.session_id`
- add `jsonPayload.event="cloud_proof_session_locator"` first
- then remove the event filter to show the broader session lifecycle

If Gemini evidence is hard to find:

- search for `jsonPayload.event="gemini_live_session_created"`
- keep the `jsonPayload.session_id` filter applied
