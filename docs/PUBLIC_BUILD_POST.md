# Ghostline Public Build Post Draft

## Working Title

Building Ghostline: A Live Paranormal Hotline with Gemini Live, Honest Verification, and Real Interruption Handling

## Required Hackathon Line

Include this sentence somewhere near the top of the final published version:

`This post was created for the purposes of entering the Gemini Live Agent Challenge.`

If you share the post on social media, include:

`#GeminiLiveAgentChallenge`

## Short Summary

Ghostline is a live paranormal containment hotline built for the Gemini Live Agent Challenge. Instead of making a chatbot with spooky copy, I built a realtime voice-and-camera experience where a caller speaks with **The Archivist, Containment Desk**, performs short containment tasks in their room, interrupts the operator in real time, and only advances when the system can honestly verify what happened.

## Draft Post

This post was created for the purposes of entering the Gemini Live Agent Challenge.

Most AI demos still collapse into the same pattern: a text box, a voice mode, and a thin illusion of interactivity layered on top.

For the Gemini Live Agent Challenge, I wanted to build something that actually felt like a **Live Agents** project. The result was **Ghostline**, a live paranormal containment hotline where a caller speaks with a calm operator called **The Archivist, Containment Desk**. The caller grants camera and mic access in-call, is guided through a short room-containment protocol, gets interrupted and recovered in real time, and ends with a formal case report.

The core idea was simple: if this product is supposed to feel like a live hotline, it cannot behave like a chatbot with a horror theme. It needs realtime audio, camera-aware behavior, visible grounding, and honest uncertainty.

### Why this is a Live Agents project

Ghostline was designed specifically around the Live Agents category.

It is:

- voice-first
- camera-aware
- interruptible
- stateful across a live session
- grounded in visible UI state
- hosted on Google Cloud

The experience is not just "talk to a model." The user enters a live call, gets permissions requested in context, performs real-world steps in the room, triggers staged verification, and can interrupt the operator while the operator is still speaking.

That last part matters. A lot of AI voice demos still feel linear because the interruption path is weak. In Ghostline, barge-in is a first-class interaction. Operator audio stops immediately, stale queued audio is flushed, and the Archivist restates briefly instead of continuing to talk over the user.

### The product idea

The hotline fantasy is that you have called a containment desk during an active paranormal incident. The operator is procedural, clipped, and calm. They are not a theatrical horror narrator.

The user is guided through a short sequence of household containment tasks like:

- show the threshold
- close the boundary
- increase the light
- stabilize the camera
- clear a small surface
- speak a containment phrase

These tasks are not invented on the fly. They come from a deterministic, curated library. The user should feel like the system is adapting to the room, but the backend remains in control of task choice, verification, recovery, and final reporting.

### Key technical decisions

#### 1. Realtime voice and camera with staged verification

One important choice was not pretending the system had richer scene understanding than it really did.

Instead of bluffing continuous certainty, Ghostline uses a staged **Ready to Verify** pattern:

1. the user performs a task
2. the user says or presses **Ready to Verify**
3. the operator asks them to hold still
4. the client captures the verification window
5. the backend returns `confirmed`, `unconfirmed`, or `user_confirmed_only`

That pattern made the product more honest and easier to understand. It also gave the experience a clear rhythm that plays well in a live demo.

#### 2. Deterministic task system instead of freeform improvisation

Ghostline uses a curated task library, a protocol planner, and an authoritative session state machine. That lets the experience feel adaptive without turning into a brittle freeform agent loop.

The result is easier to debug, easier to rehearse, and easier to demonstrate credibly.

#### 3. Interruption handling had to be real

The interruption path is one of the most important parts of the project.

Ghostline streams operator audio back to the client and tracks playback epochs so stale audio can be discarded after a barge-in. When the user interrupts, the playback buffer is flushed and the UI reflects the interrupted/listening state. That behavior is visible in both the transcript layer and the grounding HUD.

Without that, the experience immediately feels fake.

#### 4. Honest recovery instead of fake certainty

If verification fails, Ghostline uses a deterministic recovery ladder: adjust framing, correct the physical task, retry, and only then reroute if needed.

This keeps the hotline procedural instead of brittle, and avoids the common failure mode where an AI demo either dead-ends or bluffs.

### Google Cloud hosting

The backend is built with FastAPI and prepared for deployment on **Cloud Run**.

The cloud path includes:

- Cloud Run for hosting
- Firestore for persisted session state and case reports
- Cloud Logging for structured session events
- Vertex AI / Gemini Live for realtime multimodal interaction

That matters both technically and for the challenge itself. The project is not only using Gemini Live; it is also instrumented so a session can be followed through logs, Firestore, and cloud proof artifacts.

### Demo mode mattered too

A hackathon project like this is judged both as a product and as a demonstration.

So Ghostline includes a first-class **Demo Mode** with:

- a fixed safe task path
- one scripted diagnosis beat
- one scripted barge-in moment
- optional natural recovery beat if the operator rejects a real failed verify
- a fast reset path between takes

That does not make the product less real. It makes the best presentation path more repeatable.

### What I learned

A few things became very clear while building this:

- a Live Agents project needs more than voice output
- interruption quality is one of the fastest ways to tell whether the experience feels live
- staged verification is better than overclaiming what the camera can understand
- deterministic architecture is not the enemy of immersion; in a system like this it is what makes the product reliable
- submission assets are part of the product because they shape how judges understand what they are seeing

## Optional Shorter Outline

If you publish a shorter post instead of the full draft, use this structure:

1. why most AI voice demos still feel like chatbots
2. the Ghostline idea
3. why it qualifies as a Live Agents project
4. realtime voice + staged camera verification
5. deterministic tasks and recovery ladders
6. real interruption handling
7. Google Cloud + Gemini Live architecture
8. what Demo Mode taught you about presentation
9. closing reflection
