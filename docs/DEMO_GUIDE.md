# GhostLine — Demo & Run Guide

## Quick Start

### Prerequisites
- **Python 3.11+** with `pip`
- **Node.js 18+** with `npm`
- **Google Cloud project** with Vertex AI and Firestore enabled
- **Service account JSON** with Vertex AI permissions

### Environment Setup

```bash
# Server — create .env in server/
GOOGLE_CLOUD_PROJECT=your-gcp-project
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
VERTEX_AI_MODEL=gemini-live-2.5-flash-native-audio
```

### Install & Run

```bash
# Terminal 1 — Server
cd server
python -m venv .venv

# Activate the virtual environment
# On Windows:
.\.venv\Scripts\activate
# On Mac/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Client
cd client
npm install
npm run dev
```

Open **http://localhost:5173** in Chrome.

---

## Demo Mode

Append `?demoMode=true` to the URL for a scripted, repeatable demo:
```
http://localhost:5173?demoMode=true
```

Demo mode provides:
- **Fixed task sequence** — same tasks every run
- **Scripted operator lines** — polished Archivist dialogue
- **Inter-task flavor text** — containment lore between verifications
- **Auto-pass verification** — demo verifications succeed reliably

---

## Call Flow (What Judges Will See)

1. **Start Call** → Click the orange button
2. **Mic Test** → Grant microphone. Archivist confirms audio connection
3. **Camera Access** → Grant camera. Archivist acknowledges visual feed
4. **Room Scan** → Slowly pan camera left-to-right. Gemini describes the room and detects a "haunting presence"
5. **Tasks Begin** → Archivist assigns containment tasks one by one
6. **Verification** → Camera frames sent to Gemini for visual analysis
7. **Flavor Text** → Archivist delivers containment lore between tasks
8. **Case Report** → Session ends with a structured containment report

---

## Recording Tips (Phone)

The UI is **mobile-optimized** for phone screen recordings:

- Camera feed appears **first** (full-width, 16:9)
- Debug panels are **hidden** on mobile
- Buttons have **large touch targets** (56px)
- Subtitles scroll in a compact panel below
- HUD shows summary chips only — no detailed sections

**Recommended setup:**
1. Open the app on phone Chrome
2. Start screen recording
3. Click "Start Call"
4. Follow the Archivist's instructions
5. Pan camera slowly during room scan
6. Complete 2-3 tasks for the demo

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| No audio from Archivist | Check browser autoplay policy — click anywhere first |
| Camera not showing | Grant camera permission in browser settings |
| Gemini not responding | Verify `GOOGLE_APPLICATION_CREDENTIALS` and project |
| "Transport disconnected" | Server may not be running — check terminal |
| Mobile layout not working | Ensure viewport width < 540px |

---

## Key Files

| File | Purpose |
|------|---------|
| `server/app/main.py` | App startup, engine registration |
| `server/app/websocket_gateway.py` | Session orchestration hub |
| `server/app/gemini_verification.py` | Vision verification engine |
| `server/app/audio_bridge.py` | Gemini Live session management |
| `server/app/demo_dialogue.py` | Demo mode scripted lines |
| `client/src/App.tsx` | Main UI component |
| `client/src/media/useRoomScan.ts` | Room scan frame capture |
| `client/src/styles.css` | Styling + mobile responsive |
