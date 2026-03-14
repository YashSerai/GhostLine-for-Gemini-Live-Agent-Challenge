# Ghostline Architecture Diagram Source

This document provides the repo-native source and basic rendering instructions for the Ghostline architecture diagram.

## Source File

The Mermaid source lives at:

- [docs/ARCHITECTURE_DIAGRAM.mmd](docs/ARCHITECTURE_DIAGRAM.mmd)

## What The Diagram Shows

The diagram covers the full implemented architecture including:

### Frontend (React + Vite + TypeScript)
- Onboarding splash screen
- Hotline shell with grounding HUD, transcript layer, task controls
- Camera + mic capture with staged frame sampler and room scan streamer (~1 fps)
- Session timer (MM:SS), containment score bar, and share report button
- Demo mode with rehearsal harness

### Backend (FastAPI on Cloud Run)
- WebSocket gateway with session transport
- Gemini Live audio bridge with context directives and barge-in flush
- Authoritative session state machine with AI-observed affordances
- Protocol planner with AI-driven CapabilityProfile from Gemini room scan
- Gemini Vision engine for room scan analysis, verification frame analysis, ROOM_FEATURES parsing, and AI-reasoned recovery directives
- Ready-to-Verify flow with task-aware verifier and case report generator

### Google Cloud Services
- Vertex AI / Gemini Live (`gemini-live-2.5-flash-native-audio`) for realtime voice, vision, and transcription
- Firestore for session snapshots, case report persistence, and timing metadata
- Cloud Logging for structured proof events

## Rendering Options

### Option 1: Mermaid Live Editor

1. Open [https://mermaid.live](https://mermaid.live)
2. Paste the contents of `docs/ARCHITECTURE_DIAGRAM.mmd`
3. Export PNG or SVG

### Option 2: Mermaid CLI

```bash
mmdc -i docs/ARCHITECTURE_DIAGRAM.mmd -o docs/ARCHITECTURE_DIAGRAM.png
```

### Option 3: GitHub / Devpost

GitHub renders `.mmd` files natively. Embed in your Devpost submission by exporting a PNG from the Mermaid Live Editor.

## Notes

- The source uses `Ghostline` as the product name.
- The diagram is intentionally judge-readable rather than overly infrastructure-dense.
- Keep this file updated if the architecture changes.
