# Ghostline Hackathon Submission Guide

This is the end-to-end runbook from current repo state to final Devpost submission for the Gemini Live Agent Challenge.

Use this document in order. Do not jump to recording until the earlier verification steps are complete.

## 0. Current Submission Truth

Before you do anything else, keep this aligned across the repo and Devpost:

- backend deployment target: Google Cloud Run
- cloud proof path: Cloud Run + `/readyz` + `/ops/proof/active-session` + Cloud Logging + `gemini_live_session_created`
- current persistence mode: `in_memory`
- local frontend against deployed backend is acceptable for the challenge

Do not claim Firestore-backed proof unless you re-enable and verify it first.

## 1. Submission Checklist

### Required

- text description of the project
- public code repository URL
- README with spin-up instructions
- proof of Google Cloud deployment
- architecture diagram
- under-4-minute demo video showing the real software working

### Bonus

- public build post, video, or podcast about how the project was built
- automated cloud deployment included in the repo
- GDG signup and public profile link

## 2. What You Already Have In The Repo

### Required deliverables already prepared in docs

- project summary and submission copy
  - [docs/DEVPOST_SUBMISSION.md](docs/DEVPOST_SUBMISSION.md)
- spin-up and repo overview
  - [README.md](../README.md)
- cloud proof recording checklist
  - [docs/CLOUD_PROOF_CHECKLIST.md](docs/CLOUD_PROOF_CHECKLIST.md)
- architecture diagram
  - [docs/ARCHITECTURE_DIAGRAM.png](docs/ARCHITECTURE_DIAGRAM.png)
  - [docs/ARCHITECTURE_DIAGRAM.mmd](docs/ARCHITECTURE_DIAGRAM.mmd)
- demo walkthrough
  - [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md)

### Bonus deliverables already partially prepared

- public build post draft
  - [docs/PUBLIC_BUILD_POST.md](docs/PUBLIC_BUILD_POST.md)
- automated deploy helper
  - [docs/AUTOMATED_DEPLOY.md](docs/AUTOMATED_DEPLOY.md)
  - [server/deploy-cloud-run.ps1](../server/deploy-cloud-run.ps1)

## 3. Ordered Next Steps From Here

Do these in order:

1. finish one clean local verification pass
2. deploy the backend to Cloud Run
3. point the local frontend at the deployed backend
4. verify `/readyz` and `/ops/proof/active-session`
5. record the cloud proof clip
6. refresh the architecture diagram PNG from the Mermaid source
7. rehearse and record the judged demo
8. publish the build post and optional X share
9. join a GDG, make your developer profile public, and copy the public URL
10. fill Devpost using [docs/DEVPOST_SUBMISSION.md](docs/DEVPOST_SUBMISSION.md)
11. upload the architecture diagram, demo video, cloud proof clip, repo URL, and bonus links
12. do one incognito pass on every public link

## 4. Before You Record Anything

### 4.1 Clean repo surface

Before judges see the repo, decide what you want visible.

Recommended keep list:

- `README.md`
- `docs/DEMO_GUIDE.md`
- `docs/DEMO_MODE.md`
- `docs/DEVPOST_SUBMISSION.md`
- `docs/HACKATHON_SUBMISSION_GUIDE.md`
- `docs/CLOUD_PROOF_CHECKLIST.md`
- `docs/CLOUD_RUN_DEPLOYMENT.md`
- `docs/AUTOMATED_DEPLOY.md`
- `docs/ARCHITECTURE_DIAGRAM.png`
- `docs/ARCHITECTURE_DIAGRAM.mmd`
- `docs/PUBLIC_BUILD_POST.md`

Recommended internal-only docs:

- `docs/FIX_TRACKER.md`
- `docs/BUILD_GUIDE.md`
- `docs/PRODUCT_CONTEXT.md`

### 4.2 Verify README

Before submission, confirm the README still matches reality:

- root URL is correct
- server run command is correct
- client run command is correct
- judges can understand Demo vs Regular quickly
- no stale `?demo` or rehearsal-only claims remain
- no public docs still claim Firestore-backed cloud proof

### 4.3 Verify core runtime locally

Run a full local pass before touching cloud proof or the judged demo.

Verify all of these manually:

1. selecting Demo Mode connects immediately
2. selecting Regular Mode connects immediately
3. operator asks for mic in-call
4. operator asks for name after mic
5. operator asks for camera after name confirmation
6. room scan starts and operator comments on the room
7. task 1 begins without getting stuck
8. task vision frames reach the backend during active tasks
9. a failed verification can produce `unconfirmed`
10. a corrected retry can produce `confirmed`
11. barge-in interrupts operator audio
12. transcript stays visible and updates correctly
13. case report renders at the end

If any of those fail, fix them before recording.

## 5. Cloud Deployment Verification

### 5.1 Deploy backend to Cloud Run

Use one of these:

- manual guide: [docs/CLOUD_RUN_DEPLOYMENT.md](docs/CLOUD_RUN_DEPLOYMENT.md)
- scripted helper: [docs/AUTOMATED_DEPLOY.md](docs/AUTOMATED_DEPLOY.md)

### 5.2 Fastest backend-only path

Deploy the backend, then keep the frontend local.

Basic sequence:

```powershell
$env:GOOGLE_CLOUD_PROJECT = "your-gcp-project-id"
$env:GOOGLE_CLOUD_LOCATION = "us-central1"
$env:CLOUD_RUN_SERVICE = "ghostline-backend"
$env:ARTIFACT_REGISTRY_REPOSITORY = "ghostline-images"
$env:ARTIFACT_IMAGE_NAME = "ghostline-backend"
$env:APP_ENV = "production"
$env:MOCK_VERIFICATION_ENABLED = "false"
$env:DEMO_MODE_DEFAULT = "false"

& ".\server\deploy-cloud-run.ps1" -CreateRepositoryIfMissing
```

Then point the local frontend at Cloud Run:

```powershell
$env:VITE_SESSION_WS_URL = "wss://YOUR-CLOUD-RUN-URL/ws/session"
cd client
& "C:
vm4w
odejs
pm.cmd" run dev
```

### 5.3 Confirm required cloud surfaces exist

Before recording cloud proof, verify:

- Cloud Run service is healthy
- `/readyz` works
- `/ops/proof/active-session` works
- Cloud Logging contains session events
- the local frontend points to the deployed backend
- `/readyz` reports `sessionPersistence` as `in_memory`

Run these checks after deploy:

```powershell
Invoke-RestMethod "https://YOUR-CLOUD-RUN-URL/readyz"
Invoke-RestMethod "https://YOUR-CLOUD-RUN-URL/ops/proof/active-session"
```

Expected:

- `/readyz` returns `status=ready`
- `/readyz` shows `sessionPersistence=in_memory`
- `/ops/proof/active-session` returns the service name and, during an active call, the current `sessionId`

### 5.4 Verify bonus deployment automation claim

For the automation bonus, confirm these files are in the public repo and still accurate:

- [server/deploy-cloud-run.ps1](../server/deploy-cloud-run.ps1)
- [docs/AUTOMATED_DEPLOY.md](docs/AUTOMATED_DEPLOY.md)

## 6. Record The Cloud Proof Clip

Use [docs/CLOUD_PROOF_CHECKLIST.md](docs/CLOUD_PROOF_CHECKLIST.md).

### Required outcome

Your proof clip should show one session ID across:

1. Cloud Run
2. `/readyz`
3. `/ops/proof/active-session`
4. Cloud Logging
5. Gemini / Vertex evidence log

### Recommended order

1. open the deployed app
2. start one fresh session
3. open `/readyz`
4. open `/ops/proof/active-session`
5. capture the active `sessionId`
6. show the Cloud Run service page
7. search Cloud Logging for that session ID
8. show `gemini_live_session_created` for that same session ID

### Keep this clip short

Target: `45-90 seconds`

It is proof, not a product pitch.

## 7. Update The Architecture Diagram

If you change the architecture story, update both files:

- `docs/ARCHITECTURE_DIAGRAM.mmd`
- `docs/ARCHITECTURE_DIAGRAM.png`

Recommended render command:

```powershell
.\scripts\render-architecture-diagram.ps1
```

Direct Mermaid CLI equivalent:

```powershell
& "C:\nvm4w\nodejs\npm.cmd" exec --yes @mermaid-js/mermaid-cli -- -i docs/ARCHITECTURE_DIAGRAM.mmd -o docs/ARCHITECTURE_DIAGRAM.png -w 2400 --backgroundColor white
```

Current diagram story should show:

- local or hosted frontend
- Cloud Run backend
- Vertex AI / Gemini Live
- Cloud Logging
- automated deployment path through the repo deploy helper and Cloud Build / Artifact Registry
- no Firestore claim in the public submission build

## 8. Prepare The Judged Demo

### 8.1 Room setup

Prepare the environment for the fixed demo path:

- one visible doorway or threshold for `T2`
- one visible flat surface for `T5`
- one stable, well-lit room
- headphones if possible
- camera path that can show doorway, surface, and you moving between them

### 8.2 Demo mode path

Use Demo Mode only for the judged walkthrough.

Fixed path:

1. `T2` Close Boundary
2. `T5` Place Paper on Flat Surface
3. `T14` Describe the Sound
4. `T7` Speak Containment Phrase

### 8.3 Exact moments to land

Your demo should clearly show these product strengths:

- live call starts from mode selection
- in-call permission flow
- live transcript and HUD
- room scan with camera-aware operator commentary
- one honest failed verification
- one clean recovery
- one real interruption moment
- final case report

## 9. Judged Demo Recording Script

This is the recommended recording sequence.

### Opening setup

Before recording:

- open the app at the root URL
- make sure the camera view, transcript area, and HUD are visible
- make sure audio output is working

### Step-by-step walkthrough

1. Start screen recording.
2. Show the splash briefly.
3. Click `Launch Demo Mode`.
4. Grant microphone access when prompted.
5. Say your name clearly.
6. Confirm your name when asked.
7. Grant camera access when prompted.
8. Slowly scan the room.
9. Move into `T2`.
10. Intentionally leave the door open.
11. Say `Ready to Verify.`
12. Let the system fail honestly.
13. Follow the correction, close the door fully, and say `Ready to Verify.` again.
14. Complete `T5`.
15. During `T14`, answer the diagnosis question briefly.
16. During the diagnosis interpretation beat, interrupt with the exact line: `Archivist, wait. Say that again.`
17. Complete `T7`.
18. Hold on the case report screen for a few seconds.
19. Stop recording.

### Recommended user lines

Keep these short and consistent:

- `I need containment guidance.`
- `My name is ...`
- `Yes.`
- `Ready to Verify.`
- `It sounded like it came from the doorway.`
- `Archivist, wait. Say that again.`

### What to verify while recording

Make sure the captured video visibly includes:

- operator speaking
- transcript changing
- HUD updating
- room feed visible
- failed verification state
- recovery line
- interrupted operator turn
- final report

### Demo timing target

Stay under `4:00`.

Recommended timing:

- `0:00-0:20` problem + call start
- `0:20-0:50` permissions + name + camera
- `0:50-1:15` room scan
- `1:15-1:55` `T2` with fail then recovery
- `1:55-2:25` `T5`
- `2:25-2:50` `T14` diagnosis beat
- `2:50-3:10` barge-in
- `3:10-3:35` `T7`
- `3:35-3:55` case report + close

## 10. Fill Out Devpost Submission

### 10.1 Text description

Use [docs/DEVPOST_SUBMISSION.md](docs/DEVPOST_SUBMISSION.md) as the base.

When filling Devpost, make sure you include:

- summary of features and functionality
- technologies used
- other data sources used or note that there are no external data feeds
- findings and learnings
- the cloud proof clip URL
- the automated deployment proof links
- the build post URL
- the GDG or public developer profile URL

### 10.2 Repo URL

Use the public GitHub repo URL.

Before submitting, verify:

- README is visible and accurate
- no broken doc links
- architecture diagram is easy to find
- deployment automation file is visible for bonus points

Use the placeholder section in [docs/DEVPOST_SUBMISSION.md](docs/DEVPOST_SUBMISSION.md) to fill:

- repo URL
- demo video URL
- cloud proof URL
- Cloud Run backend URL
- build post or article URL
- automated deployment proof links
- GDG or public developer profile URL

### 10.3 Cloud proof

Upload or link the separate cloud proof recording.

### 10.4 Architecture diagram

Upload [docs/ARCHITECTURE_DIAGRAM.png](docs/ARCHITECTURE_DIAGRAM.png) into the Devpost image carousel or file upload so it is easy for judges to find.

### 10.5 Demo video

Upload the under-4-minute real product demo.

Before uploading, verify:

- no mockups
- real software only
- audio is understandable
- transcript and HUD are readable enough on video
- case report is visible at the end

## 11. Bonus Item 1: Publish Build Content

You already have a draft here:

- [docs/PUBLIC_BUILD_POST.md](docs/PUBLIC_BUILD_POST.md)

Before publishing, make sure the final post includes this exact idea in plain language:

`This post was created for the purposes of entering the Gemini Live Agent Challenge.`

If sharing on social media, include:

- `#GeminiLiveAgentChallenge`

Recommended publishing approach:

- publish the longer article on Medium, Dev.to, LinkedIn, or another public page
- optionally share that article on X with the hashtag
- use the article URL as the main bonus link in Devpost

## 12. Bonus Item 2: Automated Deployment

You already have this bonus prepared.

Verify that these are present in the public repo:

- [server/deploy-cloud-run.ps1](../server/deploy-cloud-run.ps1)
- [docs/AUTOMATED_DEPLOY.md](docs/AUTOMATED_DEPLOY.md)

On Devpost, mention that backend deployment to Cloud Run is automated with a repo-included script.

Use these links:

- `server/deploy-cloud-run.ps1`
- `docs/AUTOMATED_DEPLOY.md`

## 13. Bonus Item 3: Google Developer Group

This bonus is not repo work. Do it manually:

1. sign up for a Google Developer Group
2. make sure your profile is public
3. save the profile URL
4. include that URL in the Devpost submission if there is a field or mention it in the additional details section

Recommended proof path:

- join a GDG on the Google Developer Groups site
- make your Google Developer Program profile public
- use that public profile URL as the link you paste into Devpost

## 14. Final Submission Pass

Before pressing submit, verify this exact checklist:

- README accurate
- repo public
- text description polished
- architecture diagram uploaded
- cloud proof clip ready
- demo clip ready
- public build post published and URL copied
- deployment automation file visible in repo
- GDG profile link copied
- all links open correctly in an incognito window

## 15. Recommended Final Order From Here

1. finish live verification of the app
2. clean the public repo surface if you still want to delete files
3. deploy or re-verify the Cloud Run backend
4. record the cloud proof clip
5. refresh `docs/ARCHITECTURE_DIAGRAM.png` from `docs/ARCHITECTURE_DIAGRAM.mmd`
6. rehearse the demo once or twice
7. record the under-4-minute demo
8. publish the build post
9. collect the GDG profile link
10. fill the Devpost form using `DEVPOST_SUBMISSION.md`
11. upload repo URL, cloud proof, architecture diagram, demo video, and bonus links
12. do one last incognito check
13. submit



