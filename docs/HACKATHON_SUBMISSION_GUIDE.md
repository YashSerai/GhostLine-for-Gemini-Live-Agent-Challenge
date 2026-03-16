# Ghostline Hackathon Submission Guide

This is the end-to-end runbook from current repo state to final Devpost submission for the Gemini Live Agent Challenge.

Use this document in order. Do not jump to recording until the earlier verification steps are complete.

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

## 3. Before You Record Anything

### 3.1 Clean repo surface

Before judges see the repo, decide what you want visible.

Recommended keep list:

- `README.md`
- `docs/DEMO_GUIDE.md`
- `docs/DEMO_MODE.md`
- `docs/DEVPOST_SUBMISSION.md`
- `docs/CLOUD_PROOF_CHECKLIST.md`
- `docs/CLOUD_RUN_DEPLOYMENT.md`
- `docs/AUTOMATED_DEPLOY.md`
- `docs/ARCHITECTURE_DIAGRAM.png`
- `docs/ARCHITECTURE_DIAGRAM.mmd`

Recommended internal-only docs:

- `docs/FIX_TRACKER.md`
- `docs/BUILD_GUIDE.md`
- `docs/PRODUCT_CONTEXT.md`


Legacy demo doc stubs have already been removed from the public doc surface.


### 3.2 Verify README

Before submission, confirm the README still matches reality:

- root URL is correct
- server run command is correct
- client run command is correct
- judges can understand Demo vs Regular quickly
- no stale `?demo` or rehearsal-only claims remain

### 3.3 Verify core runtime locally

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

## 4. Cloud Deployment Verification

### 4.1 Deploy backend to Cloud Run

Use one of these:

- manual guide: [docs/CLOUD_RUN_DEPLOYMENT.md](docs/CLOUD_RUN_DEPLOYMENT.md)
- scripted helper: [docs/AUTOMATED_DEPLOY.md](docs/AUTOMATED_DEPLOY.md)

### 4.2 Confirm required cloud surfaces exist

Before recording cloud proof, verify:

- Cloud Run service is healthy
- `/healthz` works
- `/readyz` works
- `/ops/proof/active-session` works
- Firestore writes are visible
- Cloud Logging contains session events
- the deployed frontend or local frontend points to the deployed backend

### 4.3 Verify bonus deployment automation claim

For the automation bonus, confirm these files are in the public repo and still accurate:

- [server/deploy-cloud-run.ps1](../server/deploy-cloud-run.ps1)
- [docs/AUTOMATED_DEPLOY.md](docs/AUTOMATED_DEPLOY.md)

## 5. Record The Cloud Proof Clip

Use [docs/CLOUD_PROOF_CHECKLIST.md](docs/CLOUD_PROOF_CHECKLIST.md).

### Required outcome

Your proof clip should show one session ID across:

1. Cloud Run
2. `/ops/proof/active-session`
3. Cloud Logging
4. Firestore
5. Gemini / Vertex evidence log

### Recommended order

1. open the deployed app
2. start one fresh session
3. open `/ops/proof/active-session`
4. capture the active `sessionId`
5. show the Cloud Run service page
6. search Cloud Logging for that session ID
7. open the matching Firestore document
8. show `gemini_live_session_created` for that same session ID

### Keep this clip short

Target: `45-90 seconds`

It is proof, not a product pitch.

## 6. Prepare The Judged Demo

### 6.1 Room setup

Prepare the environment for the fixed demo path:

- one visible doorway or threshold for `T2`
- one visible flat surface for `T5`
- one stable, well-lit room
- headphones if possible
- camera path that can show doorway, surface, and you moving between them

### 6.2 Demo mode path

Use Demo Mode only for the judged walkthrough.

Fixed path:

1. `T2` Close Boundary
2. `T5` Place Paper on Flat Surface
3. `T14` Describe the Sound
4. `T7` Speak Containment Phrase

### 6.3 Exact moments to land

Your demo should clearly show these product strengths:

- live call starts from mode selection
- in-call permission flow
- live transcript and HUD
- room scan with camera-aware operator commentary
- one honest failed verification
- one clean recovery
- one real interruption moment
- final case report

## 7. Judged Demo Recording Script

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

## 8. Fill Out Devpost Submission

### 8.1 Text description

Use [docs/DEVPOST_SUBMISSION.md](docs/DEVPOST_SUBMISSION.md) as the base.

When filling Devpost, make sure you include:

- summary of features and functionality
- technologies used
- other data sources used or note that there are no external data feeds
- findings and learnings

### 8.2 Repo URL

Use the public GitHub repo URL.

Before submitting, verify:

- README is visible and accurate
- no broken doc links
- architecture diagram is easy to find
- deployment automation file is visible for bonus points

### 8.3 Cloud proof

Upload or link the separate cloud proof recording.

### 8.4 Architecture diagram

Upload [docs/ARCHITECTURE_DIAGRAM.png](docs/ARCHITECTURE_DIAGRAM.png) into the Devpost image carousel or file upload so it is easy for judges to find.

### 8.5 Demo video

Upload the under-4-minute real product demo.

Before uploading, verify:

- no mockups
- real software only
- audio is understandable
- transcript/HUD are readable enough on video
- case report is visible at the end

## 9. Bonus Item 1: Publish Build Content

You already have a draft here:

- [docs/PUBLIC_BUILD_POST.md](docs/PUBLIC_BUILD_POST.md)

Before publishing, make sure the final post includes this exact idea in plain language:

`This post was created for the purposes of entering the Gemini Live Agent Challenge.`

If sharing on social media, include:

- `#GeminiLiveAgentChallenge`

Recommended publish order:

1. finalize the post
2. publish it on your preferred platform
3. save the public URL
4. add that URL to your Devpost submission

## 10. Bonus Item 2: Automated Deployment

You already have this bonus prepared.

Verify that these are present in the public repo:

- [server/deploy-cloud-run.ps1](../server/deploy-cloud-run.ps1)
- [docs/AUTOMATED_DEPLOY.md](docs/AUTOMATED_DEPLOY.md)

On Devpost, mention that backend deployment to Cloud Run is automated with a repo-included script.

## 11. Bonus Item 3: Google Developer Group

This bonus is not repo work. Do it manually:

1. sign up for a Google Developer Group
2. make sure your profile is public
3. save the profile URL
4. include that URL in the Devpost submission if there is a field or mention it in the additional details section

## 12. Final Submission Pass

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

## 13. Recommended Final Order From Here

1. finish live verification of the app
2. clean public repo surface if you still want to delete files
3. deploy or re-verify Cloud Run backend
4. record cloud proof clip
5. rehearse demo once or twice
6. record under-4-minute demo
7. publish build post
8. collect GDG profile link
9. fill Devpost form using `DEVPOST_SUBMISSION.md`
10. upload repo URL, cloud proof, architecture diagram, demo video, and bonus links
11. do one last incognito check
12. submit

