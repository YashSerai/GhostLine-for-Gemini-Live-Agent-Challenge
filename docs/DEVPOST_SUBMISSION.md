# Ghostline Devpost Submission

This document is the submission package for the Ghostline Devpost submission, aligned with the Live Agents judging criteria.

## Concise Project Summary

Ghostline is a live paranormal containment hotline built for the Gemini Live Agent Challenge. A caller speaks with **The Archivist, Containment Desk**, who requests camera access in-call, scans the room with Gemini Vision to identify available objects, guides the caller through an AI-selected containment protocol, verifies progress using Gemini's visual analysis, provides AI-reasoned recovery advice when steps fail, and ends the session with a scored case report.

## Features & Functionality

Ghostline is a **Live Agents** experience — not a chatbot or text-box wrapper. The caller enters a live hotline call where the operator sees the room, hears the caller, and dynamically responds.

### Core Live Agent Capabilities

- **Real-time voice interaction** via Gemini Live (`gemini-live-2.5-flash-native-audio`) on Vertex AI
- **Natural barge-in** — interrupting the operator stops audio immediately and flushes stale output
- **Camera-aware interaction** with in-call permission flow and staged verification windows
- **Distinct operator persona** — The Archivist speaks in character with containment lore and procedural authority

### AI Vision Integration

- **Room Scan Analysis** — Gemini sees the caller's room at ~1 fps during calibration, narrates observations in character, and outputs structured `ROOM_FEATURES` markers
- **AI-Driven Task Selection** — Gemini's room observations feed into an `ObservedAffordances` profile that determines which containment tasks are selected (e.g., if Gemini sees a door, threshold tasks are assigned)
- **Vision Verification** — During "Ready to Verify" moments, captured frames are sent to Gemini for visual analysis of task completion
- **AI-Reasoned Recovery** — When verification fails, Gemini receives the task context and failure reason, then provides specific, actionable recovery advice instead of generic retry instructions

### Adaptive Dialogue

- **Context Directives** — After each verification result, Gemini receives structured context so it can generate operator dialogue that references what just happened
- **Inter-task Flavor** — Between tasks, the operator weaves in containment lore observations
- **Honest Uncertainty** — The system uses explicit verification outcomes (`confirmed`, `unconfirmed`, `user_confirmed_only`) and never bluffs about what it can see

### Session Experience

- **Onboarding Splash** — "What is Ghostline?" intro screen with "Start the Hotline" CTA
- **Session Timer** — Live MM:SS timer visible during the call and on the case report
- **Containment Score** — Calculated from verification outcomes, displayed as a gradient progress bar (green/amber/red)
- **Case Report** — Structured report with verdict, incident classification, task-by-task results, and containment score
- **Share Report** — One-tap sharing via Web Share API (mobile) or clipboard copy (desktop)

### Demo Mode

- Fixed deterministic path for repeatable judged walkthroughs
- Rehearsal harness with path visibility and beat tracking
- Scripted barge-in and near-failure recovery moments

### Cloud Infrastructure

- **Cloud Run** — backend hosting with WebSocket support
- **Firestore** — session snapshots, case report persistence, timing metadata
- **Cloud Logging** — structured proof events for deployment verification
- **Vertex AI** — Gemini Live session management for realtime multimodal interaction

## Technologies Used

| Layer | Technology |
|-------|-----------|
| Frontend | React, Vite, TypeScript |
| Backend | Python, FastAPI, WebSocket |
| AI | Google GenAI SDK, Gemini Live on Vertex AI |
| Cloud | Cloud Run, Firestore, Cloud Logging |
| Infrastructure | Docker, gcloud CLI |

## Data Sources

Ghostline does not depend on external data feeds or third-party datasets. Non-AI assets include:

- Authored task library with verification prompts
- Deterministic planner rules and recovery ladders
- Flavor text and diagnosis state models
- Pre-baked ambient sound assets

The primary live AI dependency is Gemini Live on Vertex AI for realtime voice, vision, and transcription.

## Findings & Learnings

1. **Staged verification > continuous vision** — Discrete "Ready to Verify" moments let the product stay honest about certainty
2. **Barge-in quality is make-or-break** — If interruption is slow, the entire experience feels scripted
3. **AI-driven task selection is the differentiator** — Having Gemini's room scan determine which tasks are available makes every session feel unique
4. **Recovery should be reasoned, not canned** — AI recovery that references the specific failure ("I can see the paper isn't fully folded") is dramatically more convincing
5. **Grounding HUD builds trust** — Showing the session state, verification status, and recovery step makes the AI feel transparent

## Architecture Diagram

See [docs/ARCHITECTURE_DIAGRAM.png](docs/ARCHITECTURE_DIAGRAM.png) and the Mermaid source at [docs/ARCHITECTURE_DIAGRAM.mmd](docs/ARCHITECTURE_DIAGRAM.mmd).

## Live Agents Alignment

### Beyond the Text Box
Voice-first, camera-aware live call — not a chat interface with a voice option.

### See, Hear, Speak
- **See**: Gemini scans the room, analyzes verification frames, identifies objects
- **Hear**: Realtime voice interaction with transcription and barge-in
- **Speak**: The Archivist speaks in character with AI-generated contextual dialogue

### Grounding
Visible HUD showing: protocol step, active task, verification state, block reason, recovery step, swap count, turn status.

### Live & Context-Aware
Room scan observations → AI task selection → vision verification → AI recovery. Every session adapts to what Gemini actually sees.

## Honesty Notes

- Verification is staged (discrete windows), not freeform continuous
- The task system is curated with AI-driven selection
- Demo mode is intentionally fixed for repeatable judging
- Sound design uses pre-baked assets
- The product is optimized for a strong demo without pretending to be unlimited
