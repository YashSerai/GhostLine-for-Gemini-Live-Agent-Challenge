# Ghostline Architecture Diagram Source

This document provides the repo-native source and basic rendering instructions for the Ghostline architecture diagram.

## Source File

The Mermaid source lives at:

- [C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\ARCHITECTURE_DIAGRAM.mmd](C:\Users\yashs\OneDrive\Desktop\Yash Stuff\Ghostline\GhostLine-for-Gemini-Live-Agent-Challenge\docs\ARCHITECTURE_DIAGRAM.mmd)

## What The Diagram Shows

The diagram is scoped to the actual implemented architecture and includes:

- frontend hotline UI
- camera and mic capture
- client WebSocket bridge
- FastAPI backend on Cloud Run
- Gemini Live integration on Vertex AI
- authoritative session state machine, planner, verifier, and recovery logic
- Firestore persistence
- Cloud Logging proof events

## Rendering Options

### Option 1: Mermaid Live Editor

1. Open [https://mermaid.live](https://mermaid.live)
2. Paste the contents of `docs/ARCHITECTURE_DIAGRAM.mmd`
3. Export PNG or SVG

### Option 2: Mermaid CLI

If you already have Mermaid CLI available:

```powershell
mmdc -i docs/ARCHITECTURE_DIAGRAM.mmd -o docs/ARCHITECTURE_DIAGRAM.svg
```

You can also render PNG:

```powershell
mmdc -i docs/ARCHITECTURE_DIAGRAM.mmd -o docs/ARCHITECTURE_DIAGRAM.png
```

## Notes

- The source uses `Ghostline` as the product name while preserving the actual `HauntLens` historical continuity elsewhere in the repo.
- The diagram is intentionally judge-readable rather than overly infrastructure-dense.
- Keep this file updated if the realtime transport, backend orchestration, persistence, or cloud deployment model changes.
