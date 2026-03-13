# Ghostline Devpost Submission Support

This document is the draft support package for the Ghostline Devpost submission.

It is written to stay honest to the implemented system and aligned with the Live Agents judging criteria.

## Concise Project Summary

Ghostline is a live paranormal containment hotline built for the Gemini Live Agent Challenge. A caller speaks with **The Archivist, Containment Desk**, who requests camera access in-call, guides the room through a short containment protocol, verifies progress during staged **Ready to Verify** moments, reacts to interruption in real time, and ends the session with a formal case report.

## Fuller Features / Functionality Summary

Ghostline is designed as a Live Agents experience rather than a chatbot or text-box wrapper. The user enters a live hotline call where the operator can hear the user, request camera access in context, assign a curated sequence of household containment tasks, and only advance the protocol when the system can honestly verify the step.

The product combines realtime voice, staged camera verification, and a visible grounding HUD. The user performs 5-6 curated tasks chosen from a deterministic library, then triggers **Ready to Verify** moments so the backend can capture a short verification window and return one of three honest outcomes: `confirmed`, `unconfirmed`, or `user_confirmed_only`.

Ghostline also includes:

- real operator interruption / barge-in handling that stops audio immediately
- deterministic recovery ladders for failed verification and `I can't do that` capability failures
- authored diagnosis and flavor beats between tasks
- a structured case report artifact at the end of the call
- a fixed Demo Mode with a rehearsal harness for a repeatable judged path
- Firestore persistence and structured logging for cloud-proof recording

## Technologies Used

- React
- Vite
- TypeScript
- Python
- FastAPI
- WebSocket realtime transport
- Google GenAI SDK
- Gemini Live on Vertex AI
- Cloud Run
- Firestore
- Cloud Logging
- Mermaid for architecture diagram source

## Data Sources And Non-AI Assets

Ghostline does not depend on external live data feeds or third-party datasets.

The main non-AI assets are:

- authored task library and deterministic planner rules
- authored flavor text and diagnosis libraries
- authored demo script and rehearsal path
- pre-baked sound assets for ambience and cueing
- structured verification and recovery logic

The primary live AI dependency is Gemini Live on Vertex AI for realtime voice interaction and multimodal call behavior.

## Findings / Learnings

- The strongest Live Agents experiences are not just voice chat with a camera attached. They need a clear interaction structure, visible grounding, and honest uncertainty handling.
- Barge-in quality matters a lot. If interruption is slow or stale audio continues, the experience immediately feels less credible.
- Staged verification worked better than pretending to do continuous vision. It let the product stay honest about what it could and could not confirm.
- Deterministic planning and recovery made the demo much more filmable and stable than a freeform agent loop would have.
- Submission assets are part of the product. README quality, architecture clarity, cloud proof, and the timed demo script materially affect how understandable the system is to judges.

## Explicit Live Agents Alignment

### Beyond Text Box

Ghostline is not a text chat interface with a voice option. The core interaction is a live hotline call with:

- in-call permission requests
- realtime operator speech
- camera-aware staged verification
- visible grounding HUD
- session state, recovery, and report generation

### Live Interruption

The user can interrupt the operator during a live spoken exchange. When that happens:

- operator audio stops immediately
- stale queued audio is flushed
- the HUD and transcript reflect interruption state
- the operator restates briefly and cleanly

This is a real product behavior, not a scripted pause in a prerecorded response.

### Grounding

Ghostline keeps grounding visible at all times through the HUD, including:

- protocol step
- active task
- path mode
- verification state
- block reason
- recovery step
- swap count
- turn status
- transcript context

The system also avoids bluffing. It uses explicit verification outcomes instead of claiming visual certainty it does not have.

### Google Cloud Hosting

The backend is built for Cloud Run, uses Firestore for persisted session state, emits structured logs for Cloud Logging, and uses Gemini Live on Vertex AI for realtime multimodal interaction.

## Optional Short "How We Built It" Paragraph

We built Ghostline as a deterministic live-agent system on top of Gemini Live. The React/Vite frontend handles the hotline UI, staged media capture, transcript layer, HUD, and demo harness. The FastAPI backend owns the WebSocket bridge, Gemini Live session management, authoritative session state machine, task planner, verifier, recovery ladders, Firestore persistence, structured logging, and final case report generation. The result is a filmable live-call experience that keeps the operator responsive while still remaining inspectable and honest.

## Honesty Notes For Submission

These are the constraints we should keep explicit in the Devpost copy:

- verification is staged, not freeform continuous scene understanding
- the task system is curated and deterministic by design
- the demo mode is intentionally fixed and rehearsable
- sound design uses pre-baked assets, not live AI-generated sound
- the product is optimized for a strong judged demo without pretending to be an unlimited paranormal sandbox
