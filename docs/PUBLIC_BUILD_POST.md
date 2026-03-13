# Ghostline Public Build Post Draft

## Working Title

Building Ghostline: A Live Paranormal Hotline with Gemini Live, Honest Verification, and Real Interruption Handling

## Short Summary

Ghostline is a live paranormal containment hotline built for the Gemini Live Agent Challenge. Instead of making a chatbot with spooky copy, I built a realtime voice-and-camera experience where a caller speaks with **The Archivist, Containment Desk**, performs short containment tasks in their room, interrupts the operator in real time, and only advances when the system can honestly verify what happened.

## Draft Post

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

The experience is not just “talk to a model.” The user enters a live call, gets permissions requested in context, performs real-world steps in the room, triggers staged verification, and can interrupt the operator while the operator is still speaking.

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

#### 1. Realtime voice and camera, but staged camera verification

One important choice was not pretending the system had richer scene understanding than it really did.

Instead of doing freeform continuous visual reasoning, Ghostline uses a staged **Ready to Verify** pattern:

1. the user performs a task
2. the user says or presses **Ready to Verify**
3. the operator says `Hold still for one second.`
4. the client captures a short verification window
5. the backend returns `confirmed`, `unconfirmed`, or `user_confirmed_only`

That pattern made the product more honest and easier to understand. It also gave the experience a clear rhythm that plays well in a live demo.

#### 2. Deterministic task system instead of freeform agent improvisation

Another major decision was to keep the task system deterministic.

Ghostline uses a curated task library, story-role helpers, a capability profile, a deterministic protocol planner, and an authoritative session state machine. That let the product feel adaptive without turning into a brittle freeform agent loop.

The result is easier to debug, easier to rehearse, and much easier to demo credibly.

#### 3. Interruption handling had to be real

The interruption path is one of the most important parts of the project.

Ghostline streams operator audio back to the client and tracks playback epochs so stale audio can be discarded after a barge-in. When the user interrupts, the playback buffer is flushed and the UI reflects the interrupted/listening state. That behavior is visible both in the transcript layer and the grounding HUD.

Without that, the experience immediately feels fake.

#### 4. Honest recovery instead of fake certainty

I also wanted the product to degrade gracefully. If verification fails, Ghostline uses a deterministic recovery ladder: move closer, adjust angle or lighting, hold still again, retry, and only then reroute or substitute.

If the user cannot do a task at all, the system can accept the constraint and move to a substitute with the same story function.

This keeps the hotline procedural instead of brittle, and it avoids the common failure mode where an AI demo either dead-ends or bluffs.

### Google Cloud hosting

The backend is built with FastAPI and is prepared for deployment on **Cloud Run**.

The cloud path includes:

- Cloud Run for hosting
- Firestore for persisted session state and case reports
- Cloud Logging for structured proof-grade session events
- Vertex AI / Gemini Live for realtime multimodal interaction

That matters both technically and for the challenge itself. The project is not only using Gemini Live; it is also instrumented so a session can be followed through logs, Firestore, and cloud proof artifacts.

### Demo mode mattered as much as core functionality

One thing I learned quickly is that a hackathon project like this is judged both as a product and as a demonstration.

So Ghostline includes a first-class **Demo Mode** with:

- a fixed safe task path
- one scripted diagnosis beat
- one scripted barge-in moment
- one controlled near-failure and recovery beat
- a rehearsal harness
- a fast reset path between takes

That did not make the product less real. It made the project more communicative. The same core systems are still there, but the best presentation path is fixed and repeatable.

### What I learned

A few things became very clear while building this:

- A Live Agents project needs more than voice output. It needs visible grounding and a coherent interaction structure.
- Interruption quality is one of the fastest ways to tell whether the experience feels live or staged.
- Staged verification is much better than overclaiming what the camera can understand.
- Deterministic architecture is not the enemy of immersion. In a system like this, it is what makes the product reliable enough to feel intentional.
- Submission assets are part of the product. README, architecture diagram, cloud proof, and the timed demo script all affect whether judges understand what they are seeing.

### Built for the hackathon

Ghostline was created for the Gemini Live Agent Challenge, and that constraint shaped the project in a good way. It pushed the build toward realtime behavior, interruption handling, camera-aware interaction, and cloud-native credibility instead of settling for a themed wrapper around a generic chat loop.

That was the right constraint. It forced the product to become much more concrete.

## Optional Article Outline

If you want to publish a shorter public post instead of the full draft above, use this structure:

1. Hook: why most AI voice demos still feel like chatbots
2. Project idea: a live paranormal containment hotline
3. Why it qualifies as a Live Agents project
4. Realtime voice + staged camera verification
5. Deterministic tasks and recovery ladders
6. Real interruption handling
7. Google Cloud + Gemini Live architecture
8. Demo mode and what it taught me about presentation
9. Closing reflection on building for the hackathon
