# Ghostline Architecture Diagram Notes

This document explains the diagram source files and the intended architectural story.

## Source Files

- [docs/ARCHITECTURE_DIAGRAM.mmd](docs/ARCHITECTURE_DIAGRAM.mmd)
- [docs/ARCHITECTURE_DIAGRAM.png](docs/ARCHITECTURE_DIAGRAM.png)
- [scripts/render-architecture-diagram.ps1](../scripts/render-architecture-diagram.ps1)

## What The Diagram Should Communicate

### Client

- splash screen with `Launch Demo Mode` and `Launch Regular Mode`
- live hotline shell with transcript, camera view, controls, and grounding HUD
- microphone capture and operator audio playback
- room-scan frame capture and task-monitoring frame capture
- ready-to-verify capture flow and case report UI

### Backend

- WebSocket gateway as the main runtime orchestrator
- Gemini Live audio bridge for voice and image-frame delivery
- authoritative session state machine for setup and task progression
- protocol planner for demo or regular path selection
- verification flow coordinating Gemini-based and deterministic checks
- case report generation and session-state emission

### Cloud

- Cloud Build and Artifact Registry for scripted backend deployment
- Cloud Run as the deployed backend surface
- Vertex AI / Gemini Live for live voice and vision
- Cloud Logging for structured operational events

## Render Command

Use this helper to regenerate the PNG after editing the Mermaid source:

```powershell
.\scripts\render-architecture-diagram.ps1
```

## Notes

- avoid describing hidden rehearsal-only routes or harnesses unless they are actively used
- avoid overstating structured room-feature extraction beyond the active runtime path
- keep the diagram readable for judges rather than exhaustive for maintainers
- the current submission build keeps session state in memory, so the public diagram should not claim Firestore-backed persistence



