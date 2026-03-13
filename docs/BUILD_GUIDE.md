HauntLens Full Prompt Guide
Prompt 1: Lock Tech Stack and Create Monorepo Skeleton

PHASE
Phase 1: Foundation and repo scaffolding

GOAL
Create a single monorepo with a locked stack and clear folders for client, server, shared docs, and assets.

WHY IT MATTERS
The previous prompt pack left too many choices open. That creates drift. This project needs one opinionated stack so every future prompt builds on the same assumptions.

DEPENDENCIES
None.

PROMPT TO GIVE THE CODING AGENT
Create a monorepo for a hackathon project called HauntLens with the following locked stack and no substitutions:

Frontend: React + Vite + TypeScript

Backend: Python + FastAPI

Google AI integration: Google GenAI SDK using Gemini Live on Vertex AI

Cloud target: Cloud Run + Firestore + Cloud Logging

Realtime communication between client and backend: WebSocket

No SSR, no Next.js, no Angular, no Vue, no Node backend

Create this structure:

/client

/server

/shared

/docs

/assets/audio

/assets/demo

root README.md

root .gitignore

root .env.example

Set up the monorepo so client and server can be started independently in local development. Keep the scaffold minimal but production-minded. Do not implement product features yet. Include clear comments or placeholder files where future phases will add logic.

EXPECTED OUTPUT
A clean repo tree with client, server, shared, docs, and assets folders, plus root config files.

ACCEPTANCE CRITERIA

Stack is exactly as specified

No alternate framework choices are introduced

Repo structure is present and runnable

Root README explains what each folder is for

.gitignore excludes dependencies, build output, secrets, and editor junk

NOTES / PITFALLS
Do not offer multiple options. The whole point is to eliminate ambiguity.

Prompt 2: Configure Client and Server Dev Commands

PHASE
Phase 1: Foundation and repo scaffolding

GOAL
Make local development predictable with simple commands for running client and server.

WHY IT MATTERS
The coding agent should not improvise how to run the app. Consistent commands reduce friction for every later prompt.

DEPENDENCIES
Prompt 1.

PROMPT TO GIVE THE CODING AGENT
In the HauntLens monorepo, configure local development commands so the frontend and backend can be run independently and clearly.

Requirements:

In /client, initialize a Vite React TypeScript app

In /server, initialize a FastAPI app with a minimal app entrypoint

Add root-level convenience instructions in README for:

installing frontend dependencies

creating Python virtualenv

installing backend dependencies

running frontend locally

running backend locally

Keep client and server separate; do not build a single-process dev environment yet

Add placeholder scripts and command documentation only; no product logic

EXPECTED OUTPUT
Working local startup instructions and minimal scaffold for both client and server.

ACCEPTANCE CRITERIA

Frontend starts with Vite

Backend starts with uvicorn

README contains exact commands

No product feature code is mixed into setup

NOTES / PITFALLS
Avoid fancy tooling that adds time without helping the hackathon build.

Prompt 3: Create Shared Types and Product Constants Skeleton

PHASE
Phase 1: Foundation and repo scaffolding

GOAL
Create a shared place for task IDs, status enums, path modes, and report statuses.

WHY IT MATTERS
This project depends on deterministic state and consistent labels. Shared types prevent frontend/backend mismatch later.

DEPENDENCIES
Prompt 1.

PROMPT TO GIVE THE CODING AGENT
Create a shared constants and type skeleton for HauntLens.

Include placeholders for:

task IDs (T1 through T15)

task tiers (1, 2, 3)

task role categories (containment, diagnostic, flavor)

path modes (threshold, tabletop, low_visibility)

verification result statuses (confirmed, unconfirmed, user_confirmed_only)

session states

case report verdicts (secured, partial, inconclusive)

UI status labels for speaking/listening/interrupted

Implement this in a way that both frontend and backend can mirror consistently, even if language-specific files are needed.

EXPECTED OUTPUT
A shared contract skeleton for future phases.

ACCEPTANCE CRITERIA

All core enums/constants exist

Naming is clean and consistent

Future prompts can reference these exact labels

NOTES / PITFALLS
Do not invent extra categories that drift from the product document.

Prompt 4: Backend FastAPI App Skeleton with Health Endpoints

PHASE
Phase 1: Foundation and repo scaffolding

GOAL
Set up the FastAPI backend with health and readiness endpoints before real-time work begins.

WHY IT MATTERS
Cloud Run deploys and debugging are easier when the service has simple health surfaces.

DEPENDENCIES
Prompt 2.

PROMPT TO GIVE THE CODING AGENT
In /server, create a FastAPI app skeleton with:

app entrypoint

/healthz endpoint

/readyz endpoint

CORS configured for local frontend origin

config module for environment variables

structured startup logging

Do not add WebSocket or Gemini logic yet. Keep this clean and deployment-friendly.

EXPECTED OUTPUT
A minimal FastAPI backend with health endpoints and CORS.

ACCEPTANCE CRITERIA

Backend runs locally

/healthz and /readyz return success JSON

CORS allows the local client

Config loads from environment

NOTES / PITFALLS
No business logic here yet. This is infrastructure hygiene.

Prompt 5: Frontend Hotline UI Shell

PHASE
Phase 2: Live media and interaction shell

GOAL
Create the visual shell for the hotline experience.

WHY IT MATTERS
The user should immediately feel like they are in a paranormal containment call, not a generic prototype.

DEPENDENCIES
Prompt 2.

PROMPT TO GIVE THE CODING AGENT
Build the initial HauntLens UI shell in React + TypeScript.

Requirements:

A hotline-style main screen with:

title: “HauntLens Containment Hotline”

operator panel area

camera preview area

subtitles area

grounding HUD area

control bar

A primary “Start Call” button

Space reserved for operator text before live audio exists

Styling should be clean, dark, readable, and demo-friendly

This is not a final design system; prioritize legibility and functional layout

Do not yet implement real call logic. Build the shell only.

EXPECTED OUTPUT
A working UI shell with visual regions for all major systems.

ACCEPTANCE CRITERIA

Layout clearly separates video, HUD, subtitles, and controls

“Start Call” exists

UI looks intentional enough for future demo recording

No fake functionality beyond placeholders

NOTES / PITFALLS
Do not over-design. Keep the UI readable on video.

Prompt 6: Backend WebSocket Gateway for Session Traffic

PHASE
Phase 2: Live media and interaction shell

GOAL
Create the backend WebSocket endpoint that will carry client session messages.

WHY IT MATTERS
The whole app depends on realtime bidirectional transport.

DEPENDENCIES
Prompt 4.

PROMPT TO GIVE THE CODING AGENT
Add a FastAPI WebSocket endpoint for HauntLens session traffic.

Requirements:

One WebSocket session per client

Accept and send JSON envelope messages

Include placeholder message types for:

client connect

mic status

camera status

transcript

frame

verify request

swap request

pause

stop

Add structured logging for connect/disconnect

No Gemini integration yet

EXPECTED OUTPUT
A functioning WebSocket endpoint and message envelope structure.

ACCEPTANCE CRITERIA

Client can connect and disconnect successfully

JSON messages are parsed safely

Invalid messages are handled gracefully

Logs show session lifecycle events

NOTES / PITFALLS
Keep transport generic enough for later phases, but do not invent unrelated message types.

Prompt 7: Client WebSocket Session Manager

PHASE
Phase 2: Live media and interaction shell

GOAL
Implement the frontend WebSocket manager that connects to the backend and handles reconnect-safe state.

WHY IT MATTERS
Without a real client session layer, later prompts will devolve into ad hoc event handling.

DEPENDENCIES
Prompt 6.

PROMPT TO GIVE THE CODING AGENT
Implement a frontend WebSocket session manager in the React app.

Requirements:

Connect to the backend WebSocket after Start Call

Expose send and receive helpers

Track connection status in UI

Handle reconnect attempts cleanly

Use a message envelope shape, not raw strings

Keep it framework-idiomatic and ready for future hooks/state integration

Do not yet integrate Gemini. This is the client-to-backend bridge only.

EXPECTED OUTPUT
A reusable WebSocket manager with connection status surfaced in the UI.

ACCEPTANCE CRITERIA

Connection can be opened and closed from UI lifecycle

Messages can be sent and received

Connection state is reflected in the shell

Reconnect logic does not spam or duplicate state

NOTES / PITFALLS
Do not bake product logic into the transport layer.

Prompt 8: Gemini Live Session Manager on Backend

PHASE
Phase 3: Gemini Live integration

GOAL
Create the backend Gemini Live session manager using the Google GenAI SDK on Vertex AI.

WHY IT MATTERS
This is the actual hackathon core. The previous prompt pack delayed the real integration too much.

DEPENDENCIES
Prompt 4.

PROMPT TO GIVE THE CODING AGENT
Integrate the backend with Gemini Live on Vertex AI using the Google GenAI SDK.

Requirements:

Create a dedicated module for Gemini Live session lifecycle

Load project/location/model config from environment

Use the GA native audio live model appropriate for low-latency voice use

Implement:

session creation

session teardown

send audio input

send image frame input

receive audio output

receive transcript events if available

receive interruption metadata if available

Keep this as a backend-only integration behind the WebSocket bridge

Add strong logging around session creation and errors

Do not yet wire this fully into the frontend. Build the backend Gemini layer first.

EXPECTED OUTPUT
A backend module that can create and manage a Gemini Live session.

ACCEPTANCE CRITERIA

Gemini session creation is isolated in one module

Model config is environment-driven

Error paths are logged clearly

Audio/image send and audio/event receive hooks exist

NOTES / PITFALLS
Do not expose credentials to the client. Do not mix session orchestration with UI logic.

Prompt 9: Bridge Client Audio to Gemini Live Through Backend

PHASE
Phase 3: Gemini Live integration

GOAL
Connect client audio input to the backend and forward it to Gemini Live.

WHY IT MATTERS
Voice-first interaction is core to the product and scoring.

DEPENDENCIES
Prompts 6, 7, 8.

PROMPT TO GIVE THE CODING AGENT
Build the backend and client bridge for live audio input.

Requirements:

Frontend captures microphone audio in low-latency chunks

Backend receives audio chunks over client WebSocket

Backend forwards audio chunks to Gemini Live session

Use a real PCM-oriented approach suitable for the Live API, not a vague MediaRecorder blob hack

Keep chunking low-latency and streaming-oriented

Add clear logs and guardrails for start/stop

Do not add fancy audio UI yet. Focus on correctness.

EXPECTED OUTPUT
A working audio-input bridge from client mic to Gemini Live.

ACCEPTANCE CRITERIA

Audio chunks flow continuously

Backend forwards them to Gemini without buffering giant blobs

Start/stop behavior is stable

Logging proves the bridge is active

NOTES / PITFALLS
Use a proper audio pipeline. Avoid hiding bad assumptions behind “placeholder raw PCM.”

Prompt 10: Bridge Gemini Live Audio Output Back to Client

PHASE
Phase 3: Gemini Live integration

GOAL
Receive Gemini audio output on the backend and stream it back to the frontend for playback.

WHY IT MATTERS
Without real operator voice output, the app does not satisfy the Live Agents fantasy.

DEPENDENCIES
Prompt 8.

PROMPT TO GIVE THE CODING AGENT
Implement the backend-to-client operator audio path.

Requirements:

Receive audio output from Gemini Live session on backend

Stream audio chunks back to frontend via the client WebSocket

On frontend, build a playback pipeline suitable for streamed audio chunks

Keep it low-latency and interruptible

Add hooks so later prompts can stop playback immediately on interruption

Keep transcript and playback decoupled

EXPECTED OUTPUT
A working streamed operator audio output path.

ACCEPTANCE CRITERIA

Audio data reaches the client

Client can play back streamed operator speech

No giant buffering delays

Playback can later be paused/cancelled cleanly

NOTES / PITFALLS
Do not hardcode TTS files. This is streamed live output, not pre-rendered audio.

Prompt 11: Frontend Camera Preview and Low-Frequency Frame Sampler

PHASE
Phase 4: Live media capture

GOAL
Implement the camera preview and a staged frame sampler for verification.

WHY IT MATTERS
The app is camera-aware, but it should not pretend to do continuous high-FPS visual reasoning.

DEPENDENCIES
Prompt 5.

PROMPT TO GIVE THE CODING AGENT
Implement camera capture in the React app.

Requirements:

Camera preview in the hotline UI

Camera access requested only after Start Call and operator prompt

Hidden canvas or equivalent mechanism to capture still frames

Do not continuously spam backend at high frame rates

Build a frame capture helper that can be called for:

calibration sampling

Ready to Verify windows

optional manual test capture

Do not yet send frames to Gemini continuously. Build a clean staged capture mechanism.

EXPECTED OUTPUT
A live preview plus reusable still-frame capture utility.

ACCEPTANCE CRITERIA

Camera preview works

Frame capture helper returns usable images

Capture frequency is controllable

No continuous uncontrolled upload loop exists

NOTES / PITFALLS
The product should look camera-aware but honest, not like fake AR.

Prompt 12: In-Call Permission Flow for Camera and Mic

PHASE
Phase 5: Hotline onboarding and in-call permissions

GOAL
Make permissions part of the call, not a setup screen.

WHY IT MATTERS
This is a core product decision and part of the immersion.

DEPENDENCIES
Prompts 5, 9, 11.

PROMPT TO GIVE THE CODING AGENT
Implement the in-call permission flow so the operator requests camera and mic naturally.

Requirements:

The call begins with the operator panel active

The operator instructs the user to grant camera access in context

Camera permission is requested only after user action plus operator prompt

Mic permission follows in-call as well

Status updates should appear in UI and operator panel

The user should not need to pre-enable anything before the call starts

EXPECTED OUTPUT
An operator-driven permission flow integrated into the hotline UX.

ACCEPTANCE CRITERIA

Permissions are requested only in context

Flow feels like part of the call

UI updates cleanly after grant or denial

Permission denial is handled gracefully

NOTES / PITFALLS
Do not fall back to generic browser onboarding vibes.

Prompt 13: Always-On Subtitles and Transcript Layer

PHASE
Phase 6: Grounding HUD and transcripts

GOAL
Display live user and operator transcripts at all times.

WHY IT MATTERS
Subtitles are crucial for clarity, judging, accessibility, and proving interruption behavior.

DEPENDENCIES
Prompts 9 and 10.

PROMPT TO GIVE THE CODING AGENT
Implement the subtitles/transcript layer in the frontend.

Requirements:

Separate user and operator transcript streams visually

Always visible during active call

Handle partial and final transcript updates if available

Keep transcript area readable on recorded video

Preserve transcript state for later use in the case report

Do not block the UI waiting for transcripts

EXPECTED OUTPUT
A live transcript panel showing both sides of the hotline conversation.

ACCEPTANCE CRITERIA

User and operator text are clearly labeled

Transcript updates in near real time

Styling is readable

Transcript survives longer than one line for context

NOTES / PITFALLS
Do not let transcript UI crowd out the HUD or video.

Prompt 14: Grounding HUD Core Implementation

PHASE
Phase 6: Grounding HUD and transcripts

GOAL
Build the persistent grounding HUD specified in the product document.

WHY IT MATTERS
This is one of the most judge-visible proof systems in the whole project.

DEPENDENCIES
Prompt 5.

PROMPT TO GIVE THE CODING AGENT
Implement the grounding HUD in the frontend with the following fields:

protocol step

active task ID

active task name

task role category

task tier

path mode

verification status

block reason

recovery step

swap count

last verified item

classification label if present

speaking/listening/interrupted status

Use placeholder data if necessary, but wire it so later phases can update these fields from real session state.

EXPECTED OUTPUT
A readable, always-visible grounding HUD.

ACCEPTANCE CRITERIA

All required fields are present

Empty states are handled gracefully

HUD remains readable on a dark UI

Layout does not obscure video or transcript content

NOTES / PITFALLS
Do not relegate this to a debug drawer. It is a core product surface.

Prompt 15: Task Library Schema with 15 Curated Tasks

PHASE
Phase 7: Task library and protocol planner

GOAL
Encode the curated task pool from the design doc in a deterministic schema.

WHY IT MATTERS
This product must not invent arbitrary tasks at runtime.

DEPENDENCIES
Prompt 3.

PROMPT TO GIVE THE CODING AGENT
Create the canonical task library as structured data on the backend.

Requirements:

Exactly 15 tasks

Fields for each task:

id

name

tier

role category

story function

short operator-facing description

verification class

substitution group

whether it can block progression

Populate this from the master design document

Add comments explaining each task’s narrative role

EXPECTED OUTPUT
A backend task schema file with 15 canonical tasks.

ACCEPTANCE CRITERIA

Exactly 15 tasks exist

Tiers and role categories match the design

Story functions are explicit

Substitution groups exist for swap logic later

NOTES / PITFALLS
Do not let the agent improvise extra tasks outside the curated list.

Prompt 16: Reliability Tier and Story-Role Helpers

PHASE
Phase 7: Task library and protocol planner

GOAL
Provide helper functions for tier and role lookups.

WHY IT MATTERS
Recovery, verification, swaps, and reporting all depend on these categories.

DEPENDENCIES
Prompt 15.

PROMPT TO GIVE THE CODING AGENT
Build backend helpers for task tier and role logic.

Requirements:

functions to fetch task by ID

functions to get tier

functions to get role category

functions to determine if a task can hard-gate progression

functions to get tasks by substitution group

clear errors for invalid task IDs

EXPECTED OUTPUT
A task helper module used by planner and state machine code.

ACCEPTANCE CRITERIA

Lookups are deterministic

Invalid IDs are handled safely

Tier/role logic never diverges from task schema

NOTES / PITFALLS
Do not duplicate task facts outside the schema.

Prompt 17: Capability Profile and Environment Classification

PHASE
Phase 7: Task library and protocol planner

GOAL
Build the capability profile used to choose tasks and path mode.

WHY IT MATTERS
The product must adapt to rooms and user constraints without becoming chaotic.

DEPENDENCIES
Prompts 11 and 12.

PROMPT TO GIVE THE CODING AGENT
Implement the capability profile and environment classification system.

Requirements:

track available affordances such as:

threshold available

flat surface available

paper available

light controllable

mirror/reflective surface available

water source nearby

track quality metrics:

lighting

blur

motion stability

derive path mode recommendation:

threshold

tabletop

low_visibility

include user-declared constraints as part of the profile

Do not overcomplicate the vision analysis. Keep it simple and demo-safe.

EXPECTED OUTPUT
A capability profile model plus classification logic.

ACCEPTANCE CRITERIA

Profile supports both observed and user-declared constraints

Path mode can be derived from profile

Logic is deterministic and inspectable

NOTES / PITFALLS
Avoid pretending the model has perfect scene understanding all the time.

Prompt 18: Deterministic Protocol Planner for 5–6 Tasks per Session

PHASE
Phase 7: Task library and protocol planner

GOAL
Select the session’s 5–6 tasks from the curated pool based on protocol step and capability profile.

WHY IT MATTERS
The user experience should feel adaptive, but the underlying sequence must be controlled.

DEPENDENCIES
Prompts 15, 16, 17.

PROMPT TO GIVE THE CODING AGENT
Implement the protocol planner for HauntLens.

Requirements:

choose 5–6 tasks per session

maintain the fixed containment story spine

prefer Tier 1 tasks for the polished path

use Tier 2 tasks only when appropriate

Tier 3 tasks should enhance pacing, not block progress

preserve step order:

assess / boundary

secure

visibility or stabilization

anchor

mark or substitute

seal/closure

include a deterministic algorithm, not random freeform selection

Return both:

the selected task list

the protocol step mapping for the session

EXPECTED OUTPUT
A planner module that generates a bounded, deterministic session plan.

ACCEPTANCE CRITERIA

Session length stays within 5–6 meaningful tasks

Output remains consistent for the same capability profile

Planner respects path mode and constraints

NOTES / PITFALLS
Do not create a sandbox. This is a guided hotline call.

Prompt 19: Frontend Task Controls: Ready to Verify, Swap, Pause, Stop

PHASE
Phase 8: Interaction controls

GOAL
Build the main task control surface.

WHY IT MATTERS
The user needs explicit affordances for the staged flow, swaps, and safe exit.

DEPENDENCIES
Prompts 5 and 14.

PROMPT TO GIVE THE CODING AGENT
Implement the core control buttons in the hotline UI:

Ready to Verify

Can’t Do This / Swap Task

Pause Session

End Session

Requirements:

buttons appear only in appropriate states

each button has clear disabled/enabled states

button actions send structured messages to backend

controls are readable and demo-friendly

Stop should be visually distinct

Do not wire all backend behavior yet if later prompts will handle it; build the UI and message plumbing cleanly.

EXPECTED OUTPUT
A working control bar tied to session events.

ACCEPTANCE CRITERIA

Buttons appear and disappear appropriately

WebSocket messages are emitted correctly

Controls do not allow invalid duplicate actions

NOTES / PITFALLS
Do not clutter the UI with debug-only controls.

Prompt 20: Voice Intent Parsing for “I Can’t Do That” and Related Swap Requests

PHASE
Phase 8: Interaction controls

GOAL
Detect swap-related voice intent from the transcript stream.

WHY IT MATTERS
The user should be able to stay in-character and still recover.

DEPENDENCIES
Prompts 13 and 18.

PROMPT TO GIVE THE CODING AGENT
Implement deterministic voice intent detection for task swaps and task inability.

Requirements:

detect phrases like:

I can’t do that

no paper

no door here

I don’t have that

another option

give me something else

output a structured swap request with:

detected intent

inferred reason

raw transcript snippet

keep the implementation simple and deterministic

do not use heavyweight NLP

EXPECTED OUTPUT
A backend voice-intent parser for swap/can’t-do requests.

ACCEPTANCE CRITERIA

Common swap phrases are detected reliably

Output is structured and easy to consume

False positives are minimized

NOTES / PITFALLS
This should support the product, not become a research project.

Prompt 21: Ready-to-Verify Interaction Flow

PHASE
Phase 9: Ready to Verify and verification engine

GOAL
Implement the staged verification interaction.

WHY IT MATTERS
This is one of the most important product mechanics and one of the clearest grounding moments.

DEPENDENCIES
Prompts 11, 19.

PROMPT TO GIVE THE CODING AGENT
Implement the complete Ready to Verify flow.

Requirements:

when user taps Ready to Verify or says an equivalent phrase:

backend transitions into verification pending state

operator tells user to hold still for one second

frontend captures a short verification window, not arbitrary continuous frames

send the captured frames plus task context to backend

reflect this in HUD and transcript

lock out conflicting controls while a verification attempt is in progress

EXPECTED OUTPUT
A complete staged verification UX flow.

ACCEPTANCE CRITERIA

Verification can only start during appropriate states

Hold-still instruction is visible/audible

Captured frame window is bounded and explicit

HUD reflects verification pending and result states

NOTES / PITFALLS
Do not trigger verification continuously behind the user’s back.

Prompt 22: Mock Verification Mode, Clearly Isolated

PHASE
Phase 9: Ready to Verify and verification engine

GOAL
Create a temporary mock verifier to unblock early UI/system testing, but isolate it so it cannot be confused with the real verifier.

WHY IT MATTERS
A mock mode is useful early, but dangerous if not clearly separated.

DEPENDENCIES
Prompt 21.

PROMPT TO GIVE THE CODING AGENT
Build a mockVerificationMode for early development only.

Requirements:

clearly isolate it behind config

do not mix it into the real verifier implementation

allow mock outcomes such as:

auto-confirm Tier 1

user-confirm-only for Tier 2

forced failure for testing recovery

every mock result should be visibly labeled in logs as mock

add TODO markers and comments so this is obviously temporary

EXPECTED OUTPUT
A test-only mock verifier with clean boundaries.

ACCEPTANCE CRITERIA

Mock mode can be enabled/disabled explicitly

Logs clearly indicate mock behavior

Real verifier can replace it later without rewriting the whole flow

NOTES / PITFALLS
This must never become the accidental shipping logic.

Prompt 23: Real Verification Engine with Task-Aware Result Model

PHASE
Phase 9: Ready to Verify and verification engine

GOAL
Implement the real task-aware verification engine.

WHY IT MATTERS
The previous prompt pack was too close to fake verification. This prompt forces the real system.

DEPENDENCIES
Prompts 8, 15, 17, 21.

PROMPT TO GIVE THE CODING AGENT
Implement the real verification engine for HauntLens.

Requirements:

input:

task ID

verification frames

quality metrics

capability profile

current path mode

transcript/user declaration if relevant

output one of:

confirmed

unconfirmed

user_confirmed_only

verification must be task-aware:

threshold/boundary tasks rely more on visible framing

illumination/stability tasks rely on measurable metrics plus scene context

speech tasks rely on transcript/audio

medium-confidence tasks may use visual plus user declaration

keep the logic honest:

if the system cannot verify visually, it should not claim full confirmation

structure the code so future task-specific improvements are easy

EXPECTED OUTPUT
A real verifier module returning structured results by task type.

ACCEPTANCE CRITERIA

Verification is not just tier-based auto-confirm

Result structure includes reason and confidence band

Uncertain outcomes can become user_confirmed_only rather than fake confirmed

Different task classes are handled differently

NOTES / PITFALLS
Do not promise computer vision certainty where the product doc explicitly avoids bluffing.

Prompt 24: Verification Result Handling and HUD Sync

PHASE
Phase 9: Ready to Verify and verification engine

GOAL
Reflect verification results in the UI and control progression accordingly.

WHY IT MATTERS
This is where the system proves its honesty.

DEPENDENCIES
Prompts 14, 21, 23.

PROMPT TO GIVE THE CODING AGENT
Implement end-to-end verification result handling from backend to frontend.

Requirements:

when verification result arrives:

update HUD status

update last verified item if applicable

display block reason if unconfirmed

mark tasks as user-confirmed-only where applicable

advance, recover, or wait based on the task and state machine rules

preserve the distinction between:

visually confirmed

user-confirmed-only

failed/unconfirmed

EXPECTED OUTPUT
A frontend/backend sync path for verification results and session progression.

ACCEPTANCE CRITERIA

HUD updates correctly

Incorrect over-advancement does not occur

User-confirmed-only is visibly distinct from confirmed

Recovery paths trigger properly

NOTES / PITFALLS
This distinction matters for the final case report and user trust.

Prompt 25: Inter-Task Flavor Text Library

PHASE
Phase 10: Diagnosis and flavor layer

GOAL
Create the authored operator patter that makes the hotline feel alive between tasks.

WHY IT MATTERS
Without this, the app becomes task → verify → task → verify and feels dead.

DEPENDENCIES
Product doc only.

PROMPT TO GIVE THE CODING AGENT
Create an authored flavor text library for the operator, organized by conversation state.

Include lines for:

opening / intake

camera request

task introduction

while-user-is-performing-task

post-verification reaction

diagnosis interpretation

urgency / pacing

reassurance / control

swap-task responses

recovery responses

final closure

Requirements:

voice must match The Archivist, Containment Desk

lines should be short, calm, procedural, eerie

do not make the operator melodramatic

build the library as structured content, not hardcoded scattered strings

EXPECTED OUTPUT
A structured operator line library by state/category.

ACCEPTANCE CRITERIA

All major dialogue states are covered

Tone matches the product

Lines are short and reusable

No user-profile-based haunting claims appear

NOTES / PITFALLS
Keep it authored and controlled, not freeform generative rambling.

Prompt 26: Waiting-State Dialogue System

PHASE
Phase 10: Diagnosis and flavor layer

GOAL
Add short operator lines while the user is physically doing a task.

WHY IT MATTERS
This is a major missing realism layer if omitted.

DEPENDENCIES
Prompt 25.

PROMPT TO GIVE THE CODING AGENT
Implement a waiting-state dialogue system for moments when the user is actively performing a task.

Requirements:

select short lines such as:

stay with me

do that now, then stop

don’t rush the frame

good, keep moving

hold once you’ve done it

support short diagnostic prompts during waiting when appropriate

do not speak constantly

use state-aware timing so the operator sounds active but not annoying

EXPECTED OUTPUT
A system that surfaces short operator lines during task execution windows.

ACCEPTANCE CRITERIA

Waiting-state dialogue exists

It does not spam

It does not overlap the main task instruction in a messy way

Tone remains controlled

NOTES / PITFALLS
This is support dialogue, not another instruction layer.

Prompt 27: Diagnostic Question Library

PHASE
Phase 10: Diagnosis and flavor layer

GOAL
Create a small, reusable library of diagnosis questions the operator can ask between tasks.

WHY IT MATTERS
This helps the call feel like an incident assessment, not just a game loop.

DEPENDENCIES
Prompt 25.

PROMPT TO GIVE THE CODING AGENT
Create a small diagnosis question library organized by category:

sound

location

light/reactivity

stillness/motion

escalation

Requirements:

examples include:

what did the sound resemble

where was it strongest

did it change with the light

did it stop when you stood still

store as authored content

mark when each category is appropriate

keep questions short and hotline-like

EXPECTED OUTPUT
A diagnosis question library with category metadata.

ACCEPTANCE CRITERIA

At least a few questions exist in each major category

Questions are short and usable in live pacing

The library is not random filler

NOTES / PITFALLS
Do not turn this into a branching narrative engine.

Prompt 28: Incident Classification Labels and Rules

PHASE
Phase 10: Diagnosis and flavor layer

GOAL
Implement lightweight incident classification for flavor and reporting.

WHY IT MATTERS
This gives the hotline a believable expert flavor without adding huge complexity.

DEPENDENCIES
Prompt 27.

PROMPT TO GIVE THE CODING AGENT
Implement a lightweight incident classification system.

Requirements:

classification labels should be fictional but systematic, such as:

threshold disturbance

reflective anomaly

low-visibility anchor

passive echo

reactive presence

derive label from user descriptions, path mode, and session context

store one primary label per session

let the operator use the label in flavor lines and case report

classification must never depend on user personal profile traits

EXPECTED OUTPUT
A simple incident classifier and label storage path.

ACCEPTANCE CRITERIA

Session ends with a plausible label

Label can be referenced in dialogue

No creepy personalization is introduced

NOTES / PITFALLS
This is flavor and reporting support, not a gameplay tree.

Prompt 29: Flavor Text State Model

PHASE
Phase 10: Diagnosis and flavor layer

GOAL
Control which flavor lines are eligible in which state so the operator does not sound repetitive or mistimed.

WHY IT MATTERS
The project needs atmosphere, but it must stay deterministic and coherent.

DEPENDENCIES
Prompts 25, 26, 27.

PROMPT TO GIVE THE CODING AGENT
Implement a flavor-text state model that maps line categories to session states.

States to cover:

opening / intake

camera request

task assignment

task in progress

verification pending

verification success

verification failure

substitution

escalation

final closure

Requirements:

avoid repeating the same line category too frequently

allow the planner/state machine to request an eligible line for the current state

keep randomization constrained and bounded

EXPECTED OUTPUT
A state-aware flavor line selector.

ACCEPTANCE CRITERIA

Lines do not show up in the wrong state

Repetition is controlled

System remains deterministic enough for demo mode overrides later

NOTES / PITFALLS
This is the difference between “alive” and “messy.”

Prompt 30: Pre-Baked Sound Asset Manifest and Playback System

PHASE
Phase 11: Sound cue system

GOAL
Create the controlled sound layer using static audio assets.

WHY IT MATTERS
The project needs atmosphere, but dynamic sound generation is scope creep.

DEPENDENCIES
Prompt 5.

PROMPT TO GIVE THE CODING AGENT
Implement the sound asset manifest and playback system.

Requirements:

asset categories:

ambient bed

light tension stinger

warning/escalation cue

verification success cue

containment result cue

create a manifest mapping semantic event names to asset file paths

build a playback layer in the frontend

preload or prepare assets for low-latency triggering

keep sound subtle and non-overwhelming

Do not use AI-generated dynamic sound. Use static assets only.

EXPECTED OUTPUT
A client-side sound system with manifest and playback functions.

ACCEPTANCE CRITERIA

Sound assets are organized and referenced cleanly

Playback helpers exist

The system is ready for event triggers

No dynamic generation logic is introduced

NOTES / PITFALLS
Do not let audio become the main act. Voice remains primary.

Prompt 31: Sound Cue Trigger Rules

PHASE
Phase 11: Sound cue system

GOAL
Define and implement exactly when sound cues fire.

WHY IT MATTERS
Bad sound timing can make the experience feel cheesy or confusing.

DEPENDENCIES
Prompt 30.

PROMPT TO GIVE THE CODING AGENT
Implement deterministic sound cue trigger rules for HauntLens.

Requirements:

trigger categories:

call connected

camera granted

task assigned

verification success

escalation / recovery

final verdict

keep stingers brief

avoid overlapping multiple cues

allow demo mode to override timing later if needed

EXPECTED OUTPUT
A sound trigger rules module tied to session events.

ACCEPTANCE CRITERIA

Sounds fire on the intended events

No repetitive or overlapping cue spam

Timing feels supportive rather than intrusive

NOTES / PITFALLS
Do not attach a cue to every tiny state change.

Prompt 32: Ambient Audio Ducking

PHASE
Phase 11: Sound cue system

GOAL
Lower ambient sound automatically when the operator is speaking.

WHY IT MATTERS
This was specifically requested and is part of making the demo intelligible.

DEPENDENCIES
Prompts 10 and 30.

PROMPT TO GIVE THE CODING AGENT
Implement ambient audio ducking in the frontend audio system.

Requirements:

when operator speech is playing, ambient bed volume should lower smoothly

when speech ends, ambient should recover smoothly

use gain control/fade logic, not hard cuts

preserve clarity of operator speech and subtitles

keep the system lightweight and reliable

EXPECTED OUTPUT
An ambient ducking layer integrated into sound playback.

ACCEPTANCE CRITERIA

Ambient lowers during operator speech

Transitions are smooth

Speech remains clearly audible

Ducking does not create audio artifacts

NOTES / PITFALLS
Keep it subtle. Over-engineering this wastes time.

Prompt 33: Barge-In Handling and Audio Buffer Flush

PHASE
Phase 12: Barge-in and interruption correctness

GOAL
Implement correct interruption behavior, including immediate audio stop.

WHY IT MATTERS
This is one of the most important judged behaviors in the whole hackathon.

DEPENDENCIES
Prompts 10 and 13.

PROMPT TO GIVE THE CODING AGENT
Implement full barge-in handling for HauntLens.

Requirements:

detect or receive interruption signal from Gemini Live/backend state

immediately stop operator audio playback

flush/discard any queued audio chunks that should not continue after interruption

update UI/HUD to interrupted, then listening

preserve transcript continuity

allow the operator to restate cleanly after interruption

EXPECTED OUTPUT
A real interruption handling system with immediate playback halt.

ACCEPTANCE CRITERIA

Operator stops speaking immediately on interruption

No stale queued speech continues afterward

HUD reflects interrupted state

User can speak immediately after interruption

NOTES / PITFALLS
Do not fake this with delayed pause behavior. It needs to feel instant.

Prompt 34: Recovery Ladder for Verification Failure

PHASE
Phase 13: Recovery and graceful degradation

GOAL
Implement the deterministic recovery ladder for failed verification.

WHY IT MATTERS
Recovery is how the system proves robustness without bluffing.

DEPENDENCIES
Prompts 23 and 24.

PROMPT TO GIVE THE CODING AGENT
Implement the verification-failure recovery ladder.

Requirements:

on unconfirmed verification:

step 1: move closer

step 2: adjust angle or lighting

step 3: hold still again

step 4: retry verification

step 5: switch path mode or substitute task if still blocked

track attempt counts per task

integrate operator recovery dialogue

reflect recovery state in HUD

EXPECTED OUTPUT
A deterministic recovery system for failed verification.

ACCEPTANCE CRITERIA

Recovery steps occur in order

Attempt counts reset when appropriate

System does not loop forever

Recovery is visible in HUD and operator dialogue

NOTES / PITFALLS
Do not make recovery feel like random guessing.

Prompt 35: Recovery Ladder for Capability Failure / “Can’t Do This”

PHASE
Phase 13: Recovery and graceful degradation

GOAL
Handle the user being unable to perform a task without breaking the story.

WHY IT MATTERS
Task substitution is core to the hotline fantasy.

DEPENDENCIES
Prompts 18, 19, 20.

PROMPT TO GIVE THE CODING AGENT
Implement capability-failure recovery and substitution logic.

Requirements:

when user cannot do a task:

accept the constraint

ask at most one clarifying question if needed

choose a substitute with the same story function

prefer same or higher reliability if possible

cap swaps per step

if needed, proceed with graceful partial handling

log all swaps and reasons

surface swap count in HUD

EXPECTED OUTPUT
A deterministic task substitution system.

ACCEPTANCE CRITERIA

Same-function substitutions are used

Swap count is bounded

System avoids dead-ends

Operator language matches the hotline tone

NOTES / PITFALLS
Do not let substitution become freeform task invention.

Prompt 36: Full Session State Machine

PHASE
Phase 14: State machine and persistence

GOAL
Implement the session state machine that governs all legal transitions.

WHY IT MATTERS
This product has enough moving parts that state discipline is mandatory.

DEPENDENCIES
Prompts 18, 21, 24, 34, 35.

PROMPT TO GIVE THE CODING AGENT
Implement the HauntLens session state machine.

States should include at minimum:

init

call_connected

consent

camera_request

calibration

task_assigned

waiting_ready

verifying

diagnosis_beat

recovery_active

swap_pending

paused

completed

case_report

ended

Requirements:

define allowed transitions

reject illegal transitions

store current step, task, task history, verification history, classification label, swap counts, recovery step, and transcript references

EXPECTED OUTPUT
A backend state machine implementation with strong transition rules.

ACCEPTANCE CRITERIA

Illegal transitions are blocked

Session progression is deterministic

State contains all necessary context for UI and reporting

Barge-in and pause fit naturally into the model

NOTES / PITFALLS
Do not manage core flow with ad hoc booleans scattered across modules.

Prompt 37: Firestore Session Persistence

PHASE
Phase 14: State machine and persistence

GOAL
Persist the session to Firestore for reliability and proof.

WHY IT MATTERS
Cloud-native proof is part of the judging and part of your architecture story.

DEPENDENCIES
Prompt 36.

PROMPT TO GIVE THE CODING AGENT
Integrate Firestore session persistence.

Requirements:

create a session document on call start

persist key session fields on major transitions

store task history, verification history, classification label, final verdict

keep write shape easy to inspect in the Firestore console

use server credentials only

structure the data so it helps cloud proof recording later

EXPECTED OUTPUT
Firestore-backed session persistence tied to state transitions.

ACCEPTANCE CRITERIA

Session doc is created and updated

Core fields stay in sync with the state machine

Data is legible enough to show in a proof recording

NOTES / PITFALLS
Do not store unnecessary raw media.

Prompt 38: Structured Logging for Cloud Proof

PHASE
Phase 14: State machine and persistence

GOAL
Emit structured logs for every important system event.

WHY IT MATTERS
You need visible backend proof during recording and debugging.

DEPENDENCIES
Prompt 36.

PROMPT TO GIVE THE CODING AGENT
Add structured JSON logging to the backend for key lifecycle events.

Log at minimum:

session started

Gemini session created

task assigned

verify requested

verification result

swap requested

recovery entered

interruption handled

session paused

session ended

case report generated

Requirements:

include session ID and step/task context

keep logs safe and readable

format for Cloud Logging consumption

EXPECTED OUTPUT
Structured logs across the backend lifecycle.

ACCEPTANCE CRITERIA

Logs are emitted for all key events

Logs are easy to scan in Cloud Logging

No secrets are exposed

NOTES / PITFALLS
Too little logging hurts proof. Too much noisy logging hurts usefulness.

Prompt 39: Case Report Artifact Generation

PHASE
Phase 15: Case report artifact

GOAL
Generate the final case report artifact shown at the end of the session.

WHY IT MATTERS
This is the memorable payoff and part of the product identity.

DEPENDENCIES
Prompts 24, 28, 36, 37.

PROMPT TO GIVE THE CODING AGENT
Implement HauntLens case report generation.

Requirements:

case report should include:

session/case ID

timestamp

incident classification label

task list

per-task outcome:

confirmed

user_confirmed_only

unverified/skipped

final verdict:

secured

partial

inconclusive

produce:

structured JSON payload

frontend-renderable report card view

make the visual report demo-friendly

EXPECTED OUTPUT
Backend report generator plus frontend report view.

ACCEPTANCE CRITERIA

Report includes all required fields

Outcomes correctly reflect session state

Report is readable and memorable on screen

NOTES / PITFALLS
Do not flatten confirmed and user-confirmed-only into the same category.

Prompt 40: Alternate Closing Report Templates

PHASE
Phase 15: Case report artifact
Optional polish

GOAL
Add one or two alternate closing report templates.

WHY IT MATTERS
This was specifically requested and adds polish without heavy scope.

DEPENDENCIES
Prompt 39.

PROMPT TO GIVE THE CODING AGENT
Add alternate closing templates for the case report.

Requirements:

at least these verdict styles:

secured

partial containment

inconclusive / unstable but contained for now

vary the closing line and visual tone slightly

keep the system deterministic based on verdict, not random

EXPECTED OUTPUT
Multiple report endings selected by verdict.

ACCEPTANCE CRITERIA

Each verdict renders appropriately

Text still matches product tone

Variation is small and controlled

NOTES / PITFALLS
This is polish, not a branching narrative ending system.

Prompt 41: Previous Case ID Flourish

PHASE
Phase 15: Case report artifact
Optional polish

GOAL
Add a lightweight archive flourish suggesting a larger containment desk history.

WHY IT MATTERS
This supports the fantasy without ballooning scope.

DEPENDENCIES
Prompt 39.

PROMPT TO GIVE THE CODING AGENT
Add a lightweight “archive” flourish to the report or closing view.

Requirements:

display the current case ID prominently

optionally show a very small archival reference element such as:

prior case IDs list

“Containment Desk archive reference”

keep this lightweight and presentation-oriented

do not build a real archive system

EXPECTED OUTPUT
A tiny archive/case flourish in the UI.

ACCEPTANCE CRITERIA

It feels like worldbuilding, not extra product scope

It does not clutter the report

It uses the real session/case ID

NOTES / PITFALLS
Do not turn this into history browsing.

Prompt 42: Pause and Stop Session Flow

PHASE
Phase 16: Session control and graceful exit

GOAL
Implement pause and stop safely.

WHY IT MATTERS
The user must retain control, and the session must end cleanly.

DEPENDENCIES
Prompts 19 and 36.

PROMPT TO GIVE THE CODING AGENT
Implement Pause Session and End Session behavior end-to-end.

Requirements:

pause should:

halt progression

stop new verification attempts

preserve session state

update UI and operator state

end should:

stop media activity

close Gemini session

finalize partial or full report

stop camera and mic tracks

transition to ended/report view

both must be available from the control bar

EXPECTED OUTPUT
Reliable pause and stop flows across client and backend.

ACCEPTANCE CRITERIA

Pause preserves state cleanly

Stop tears down resources cleanly

Partial report generation works

UI clearly reflects the ended session

NOTES / PITFALLS
Do not leave browser media tracks running after stop.

Prompt 43: Demo Mode Fixed Path

PHASE
Phase 17: Demo mode and rehearsal mode

GOAL
Create the deterministic demo-safe task sequence.

WHY IT MATTERS
This is not optional polish. It is how you record the judged demo reliably.

DEPENDENCIES
Prompt 18.

PROMPT TO GIVE THE CODING AGENT
Implement first-class Demo Mode with a fixed safe path.

Requirements:

fixed task sequence using the safest, most reliable tasks

avoid fragile optional-object dependencies unless deliberately scripted

use the same narrative every run

allow this mode to be enabled by config or route param

keep it separate from normal dynamic session planning

EXPECTED OUTPUT
A demo-mode planner branch with a fixed safe sequence.

ACCEPTANCE CRITERIA

Demo mode always produces the same core task path

It stays faithful to the product

Normal mode still exists separately

NOTES / PITFALLS
Do not leave demo mode half-random.

Prompt 44: Demo Mode Fixed Flavor, Diagnosis, and Recovery Script

PHASE
Phase 17: Demo mode and rehearsal mode

GOAL
Lock the operator’s flavor lines, diagnosis beat, interruption restatement, and recovery lines for the polished recording.

WHY IT MATTERS
A judged demo needs repeatability and polish, not “hopefully it sounds good this run.”

DEPENDENCIES
Prompts 25 through 29, 33 through 35, 43.

PROMPT TO GIVE THE CODING AGENT
Implement demo-specific scripted dialogue behavior.

Requirements:

fixed operator lines for the demo path

fixed diagnosis beat timing and wording

fixed waiting-state lines for the demo

fixed recovery line for the intentional near-failure

reduced or eliminated randomness in line selection during demo mode

preserve the same persona and tone as the main product

EXPECTED OUTPUT
A demo dialogue pack and selector override.

ACCEPTANCE CRITERIA

Demo dialogue is repeatable

It still feels like the product, not a different script

Diagnosis and recovery moments happen on cue

NOTES / PITFALLS
Do not make demo mode dialogue robotic; it should just be controlled.

Prompt 45: Controlled Demo Barge-In Moment

PHASE
Phase 17: Demo mode and rehearsal mode

GOAL
Create the rehearsable interruption moment for the final recording.

WHY IT MATTERS
Barge-in is one of the most important judging beats.

DEPENDENCIES
Prompts 33 and 44.

PROMPT TO GIVE THE CODING AGENT
Implement a deterministic demo interruption scenario.

Requirements:

pick one exact operator line in the demo path to interrupt

define the user interruption phrase

make the system easy to rehearse and trigger reliably

ensure the operator stops instantly and restates cleanly

reflect interruption in transcript and HUD

EXPECTED OUTPUT
A rehearsable barge-in moment in demo mode.

ACCEPTANCE CRITERIA

It happens exactly where expected

Operator audio stops immediately

Restatement is clean and shorter

Transcript and HUD prove it happened

NOTES / PITFALLS
Do not leave this up to random timing.

Prompt 46: Controlled Demo Near-Failure and Recovery Beat

PHASE
Phase 17: Demo mode and rehearsal mode

GOAL
Create one intentional, safe failure moment that triggers recovery.

WHY IT MATTERS
Judges need to see the system handle failure honestly.

DEPENDENCIES
Prompts 34 and 43.

PROMPT TO GIVE THE CODING AGENT
Implement a controlled near-failure beat in demo mode.

Requirements:

choose one safe failure type such as:

slight framing issue

deliberate blur

temporary low-light

first verification should fail in a believable way

operator should issue the recovery line

second verification should succeed after the correction

keep this deterministic and rehearsable

EXPECTED OUTPUT
A demo-mode recovery scene.

ACCEPTANCE CRITERIA

Exactly one controlled failure occurs

Recovery is visible in HUD and transcript

Final session still completes

NOTES / PITFALLS
Do not create cascading demo instability.

Prompt 47: Demo HUD Readability Mode and Fast Reset

PHASE
Phase 17: Demo mode and rehearsal mode

GOAL
Make demo recording easier with a clear HUD and one-step reset.

WHY IT MATTERS
A flexible system is not enough; you need a filmable system.

DEPENDENCIES
Prompts 14, 43, 44, 45, 46.

PROMPT TO GIVE THE CODING AGENT
Implement demo support utilities.

Requirements:

demo-friendly HUD mode that improves readability for recording if needed

one-click or one-command demo reset

reset should:

clear current session state

reset frontend controls

stop and restart Gemini/client/backend session state cleanly

keep this clearly marked as demo support, not core end-user UX

EXPECTED OUTPUT
A demo reset utility and optionally a demo HUD readability mode.

ACCEPTANCE CRITERIA

Rehearsal reruns are fast

Reset does not leave stale media or backend state behind

HUD remains faithful to product content while being readable

NOTES / PITFALLS
Do not overcomplicate this. It is for recording reliability.

Prompt 48: Rehearsal/Test Harness for Demo Path

PHASE
Phase 17: Demo mode and rehearsal mode

GOAL
Create a rehearsal harness for repeatedly testing the demo flow.

WHY IT MATTERS
You should be able to validate the final judged path without manual chaos.

DEPENDENCIES
Prompt 47.

PROMPT TO GIVE THE CODING AGENT
Build a lightweight rehearsal harness for HauntLens demo mode.

Requirements:

validate the fixed task path

validate barge-in

validate recovery beat

validate final case report generation

expose a simple developer-facing checklist or debug view for rehearsal

do not turn this into a full QA dashboard

EXPECTED OUTPUT
A lightweight rehearsal/testing support tool for the demo path.

ACCEPTANCE CRITERIA

Demo flow can be replayed repeatedly

Key moments can be checked quickly

The harness remains simple and focused

NOTES / PITFALLS
This exists to de-risk the recording, not to become another product surface.

Prompt 49: Cloud Run Deployment for Backend

PHASE
Phase 18: Cloud deployment and proof instrumentation

GOAL
Deploy the FastAPI backend to Cloud Run.

WHY IT MATTERS
Hosted on Google Cloud is a hard requirement and part of the judging criteria.

DEPENDENCIES
Prompts 4, 8, 36, 37, 38.

PROMPT TO GIVE THE CODING AGENT
Prepare the backend for Cloud Run deployment.

Requirements:

production-friendly FastAPI entrypoint

Cloud Run-compatible container setup

environment-driven config for project/location/model/etc.

WebSocket support preserved

health endpoints preserved

logging suitable for Cloud Logging

include deployment notes in comments or docs

EXPECTED OUTPUT
A Cloud Run-ready backend deployment setup.

ACCEPTANCE CRITERIA

Backend can run in containerized form

Health endpoints work

WebSocket route remains available

Environment config is externalized

NOTES / PITFALLS
Do not hardcode secrets or project IDs.

Prompt 50: Cloud Proof Instrumentation and Recording Checklist Support

PHASE
Phase 18: Cloud deployment and proof instrumentation

GOAL
Make it easy to record the required cloud proof clip.

WHY IT MATTERS
This is a required submission artifact and often underprepared.

DEPENDENCIES
Prompts 37, 38, 49.

PROMPT TO GIVE THE CODING AGENT
Add cloud-proof-friendly instrumentation and support material.

Requirements:

ensure session IDs are visible in logs and Firestore

expose a clean way to identify the active session during a demo

create a short internal checklist or markdown note for recording the cloud proof clip showing:

Cloud Run service

logs

Firestore session updates

evidence of Gemini/Vertex usage

do not build a special user-facing screen for this; keep it operational

EXPECTED OUTPUT
Cloud-proof support notes plus implementation that makes proof recording easy.

ACCEPTANCE CRITERIA

Session activity is easy to locate in Cloud Run logs

Firestore updates are easy to show

Proof instructions are concise and realistic

NOTES / PITFALLS
Do not wait until the end to think about proof recording.

Prompt 51: README Generation

PHASE
Phase 19: Submission assets

GOAL
Generate the README with setup, architecture, demo reproduction, and submission-oriented framing.

WHY IT MATTERS
The README is a required deliverable and part of perceived quality.

DEPENDENCIES
Most core implementation prompts.

PROMPT TO GIVE THE CODING AGENT
Draft the full project README.

Requirements:

project overview

why it is a Live Agents submission

feature summary

architecture summary

local setup

environment variables

running client and server

deployment overview

how to replay the demo path

privacy/safety notes

cloud proof note

headphones recommended note

Write it as a serious public repo README, not as private dev notes.

EXPECTED OUTPUT
A polished README draft.

ACCEPTANCE CRITERIA

Setup instructions are complete

README matches the actual implemented system

Demo reproduction steps are included

Language aligns with judging and product

NOTES / PITFALLS
Do not leave placeholder prose in the final draft.

Prompt 52: Architecture Diagram Source Generation

PHASE
Phase 19: Submission assets

GOAL
Create the architecture diagram source so it can be rendered consistently.

WHY IT MATTERS
The diagram is a required artifact and should match the actual build.

DEPENDENCIES
Prompts 8, 36, 37, 49.

PROMPT TO GIVE THE CODING AGENT
Generate architecture diagram source for HauntLens.

Requirements:

choose a source format that can live in repo, such as Mermaid

show:

frontend hotline UI

camera/mic capture

client WebSocket bridge

FastAPI backend

Gemini Live integration

state machine / planner / verifier

Firestore

Cloud Logging

Cloud Run

make the diagram clear enough for judges

EXPECTED OUTPUT
Diagram source file plus brief rendering instructions.

ACCEPTANCE CRITERIA

Diagram matches implemented architecture

Components and flow are readable

No major product systems are omitted

NOTES / PITFALLS
Do not make the diagram too abstract.

Prompt 53: Demo Script Generation Support

PHASE
Phase 19: Submission assets

GOAL
Produce a clear, timed demo script for recording.

WHY IT MATTERS
The project is optimized for one polished recorded path.

DEPENDENCIES
Prompts 43 through 48.

PROMPT TO GIVE THE CODING AGENT
Generate a demo recording script and shot plan for HauntLens.

Requirements:

keep total runtime under four minutes

include:

opening hook

in-call permission request

calibration

visible grounding

one diagnosis beat

one interruption

one recovery beat

final case report

quick architecture/proof reminder

include approximate timestamps

reflect the actual demo mode path, not a theoretical one

EXPECTED OUTPUT
A timed demo script outline for recording.

ACCEPTANCE CRITERIA

Script fits under four minutes

Script matches demo mode behavior

All judged moments are included

NOTES / PITFALLS
Do not write a pitch disconnected from the actual implemented flow.

Prompt 54: Devpost Submission Support Materials

PHASE
Phase 19: Submission assets

GOAL
Generate support text for the Devpost submission.

WHY IT MATTERS
Submission quality influences how clearly judges understand the build.

DEPENDENCIES
Prompts 51, 52, 53.

PROMPT TO GIVE THE CODING AGENT
Draft the Devpost submission support materials for HauntLens.

Requirements:

one concise project summary

one fuller features/functionality summary

technologies used

what data sources or non-AI assets are used

findings/learnings

explicit alignment with Live Agents judging:

beyond text box

live interruption

grounding

Google Cloud hosting

keep wording honest and consistent with the implementation

EXPECTED OUTPUT
A clean Devpost draft package.

ACCEPTANCE CRITERIA

Content matches the built system

Judging language is reflected naturally

No exaggerated claims are made

NOTES / PITFALLS
Do not promise features that only existed in planning.

Prompt 55: Automated Deploy Script

PHASE
Phase 20: Optional polish after core stability

GOAL
Create an automated deploy helper for bonus-point deployment automation.

WHY IT MATTERS
This was specifically requested and can support bonus scoring.

DEPENDENCIES
Prompt 49.

PROMPT TO GIVE THE CODING AGENT
Create an optional automated deployment helper for HauntLens.

Requirements:

automate backend deploy steps to Cloud Run as far as practical

use environment variables, not hardcoded values

document prerequisites and auth expectations

keep the script simple and maintainable

this is post-MVP polish, not core product logic

EXPECTED OUTPUT
A deploy helper script and brief usage notes.

ACCEPTANCE CRITERIA

Script is understandable

Project-specific values are parameterized

README can reference it later

NOTES / PITFALLS
Do not burn time building full infrastructure-as-code if the core product is unstable.

Prompt 56: Public Build Post / Thought Leadership Draft

PHASE
Phase 20: Optional polish after core stability

GOAL
Draft the public build post or thought-leadership asset for the hackathon bonus.

WHY IT MATTERS
This was missing from the weaker prompt pack and can help with optional bonus criteria.

DEPENDENCIES
Core system should already be stable enough to describe honestly.

PROMPT TO GIVE THE CODING AGENT
Draft a public build post or article outline about building HauntLens for the Gemini Live Agent Challenge.

Requirements:

explain the project idea clearly

explain why it is a Live Agents submission

explain key technical decisions:

realtime voice and camera

staged verification

deterministic task system

interruption handling

Google Cloud hosting

mention that it was created for the hackathon

keep it public-facing and clear, not deeply internal

treat this as post-MVP content, not core build logic

EXPECTED OUTPUT
A draft public build post or article outline.

ACCEPTANCE CRITERIA

The piece matches the actual implementation

It is suitable for public posting

It does not oversell or invent missing features

NOTES / PITFALLS
Do not write hype disconnected from what was truly built.
Prompt 57: Live Operator Guidance Orchestrator for Normal Mode

PHASE
Phase 20: Normal-mode dialogue polish after core architecture

GOAL
Wire authored operator guidance into the live spoken call path so key hotline beats are not left to generic reactive voice behavior.

WHY IT MATTERS
The product already has flavor text, diagnosis questions, and a state model, but the caller still needs explicit spoken guidance for calibration, task starts, and next-step transitions. If those beats remain under-directed, the hotline feels vague even when the transport works.

DEPENDENCIES
Prompts 25 through 29, 36 through 42.

PROMPT TO GIVE THE CODING AGENT
Integrate the authored flavor/state systems into the live operator path for normal mode.

Requirements:

make state transitions trigger authored spoken guidance, not just HUD or transcript updates

at minimum cover:

camera request

calibration

task assignment

post-verification success/failure

swap/substitution result

final closure

keep the wording deterministic and bounded by state

do not add a freeform narrative generator

preserve Gemini Live for operator voice, but let backend-authored lines drive the key beats

EXPECTED OUTPUT
A live operator guidance orchestrator that pushes authored hotline lines into the spoken call path.

ACCEPTANCE CRITERIA

critical hotline beats are spoken clearly

operator text and operator voice stay aligned

state-driven guidance is inspectable and deterministic

NOTES / PITFALLS
Do not let the user hear a vague live voice while the real instructions only exist in side-panel text.

Prompt 58: Calibration Explanation and First Task Coaching

PHASE
Phase 20: Normal-mode dialogue polish after core architecture

GOAL
Make calibration and the first task understandable to a cold-start user without relying on prior knowledge.

WHY IT MATTERS
Calibration is a product mechanic, not a familiar consumer term. The operator must explain what it means, why it matters, and what the user should physically do. The first task also needs a clear spoken action, not just a label in the HUD.

DEPENDENCIES
Prompts 11, 12, 21, 36, 57.

PROMPT TO GIVE THE CODING AGENT
Improve the live onboarding language for calibration and first-task coaching.

Requirements:

when calibration is requested, explicitly explain that it means one clean still frame of the room

state what should be centered in frame during calibration

explain what happens after calibration

when the first task is assigned, speak:

the task name

the exact action

how the user should signal completion

mirror the same instruction in visible operator text so the caller is never dependent on hearing perfectly

EXPECTED OUTPUT
A clearer first-minute operator experience that explains calibration and the first task directly.

ACCEPTANCE CRITERIA

a first-time user can understand calibration without guessing

the first task is spoken clearly and concretely

visible operator text and spoken instruction match

NOTES / PITFALLS
Do not use product-internal wording without explanation. �Capture calibration� alone is not enough.

Prompt 59: Low-Visibility / Low-Context Guidance Compensation

PHASE
Phase 20: Normal-mode dialogue polish after core architecture

GOAL
Compensate for intentionally low-frequency vision by making the operator ask stronger grounding questions and give clearer corrective guidance.

WHY IT MATTERS
Ghostline is honest about staged verification and low-frequency vision. That means the dialogue has to carry more of the experience. If the room feed is weak, the operator should become more directive and diagnostic rather than sounding passive.

DEPENDENCIES
Prompts 17, 21, 23, 27, 28, 34, 57.

PROMPT TO GIVE THE CODING AGENT
Add a bounded dialogue compensation layer for weak visual context.

Requirements:

when current path mode is low_visibility or verification confidence is weak, increase the clarity of operator guidance

prefer short grounded questions such as:

where is it strongest

is there a doorway in front of you

what flat surface is available

did the sound change when the light changed

make recovery instructions more concrete when the frame is dark, unstable, or poorly centered

keep this deterministic and state-driven

do not pretend the camera saw more than it did

EXPECTED OUTPUT
A state-aware guidance layer that makes the operator more helpful when visual certainty is low.

ACCEPTANCE CRITERIA

low-visibility sessions feel guided rather than vague

diagnostic questions improve task routing clarity

recovery language becomes more concrete under weak visual conditions

NOTES / PITFALLS
This is not permission to fake rich vision. The improvement should come from better questions and clearer instructions.
