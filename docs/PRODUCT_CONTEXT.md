# Ghostline Product Context

## Project Identity

**Ghostline** is a live paranormal containment hotline experience for the Gemini Live Agent Challenge.  
Previous working name: **HauntLens**.  
Use **Ghostline** as the primary product name going forward unless an existing file or prompt explicitly references HauntLens for historical continuity.

Ghostline is a **Live Agents** category project. It is a voice-first, camera-aware, interruptible, cloud-hosted multimodal agent experience where the user is guided through a short real-time room-containment sequence by a calm operator called **The Archivist, Containment Desk**.

The product is not a chatbot.  
The product is not “true AR.”  
The product is not a freeform haunted-house sandbox.

It is a **live hotline call** where an operator hears the user, asks for camera access in-call, assesses the room, assigns a curated sequence of containment tasks, verifies progress in staged “Ready to Verify” moments, adapts when the user cannot do a task, and ends with a formal case report.

---

## Core Product Fantasy

The user should feel:

> “I called a paranormal containment hotline. A specialist is guiding me in real time to secure the room. They can hear me, they can see what I show them, they react when I interrupt, and they only advance the protocol when they can confirm what happened.”

The emotional frame is:

- controlled urgency
- eerie but procedural
- immersive but not chaotic
- tense but not threatening
- professional operator, not theatrical horror narrator

The operator should sound like someone managing an active incident, not roleplaying campy ghost lore.

---

## Challenge Fit

Ghostline is built specifically for the **Gemini Live Agent Challenge** under the **Live Agents** category.

This means the project must visibly demonstrate:

- real-time voice interaction
- camera-aware interaction
- natural interruption / barge-in
- a distinct voice/persona
- Google Cloud hosting
- Gemini Live API usage
- visible grounding and robust handling of uncertainty
- a strong, polished under-4-minute demo

This project is being optimized to score well on:

1. **Innovation & Multimodal User Experience**
2. **Technical Implementation & Agent Architecture**
3. **Demo & Presentation**

The system must not just work — it must be **filmable**, **understandable**, and **credible** to judges.

---

## High-Level Product Summary

Ghostline is a live paranormal hotline where a calm containment operator guides the user through **5–6 containment steps** chosen from a **curated task library of ~15 tasks**.

Tasks are based on **ordinary room interactions**, such as:

- show the doorway or threshold
- close the door
- increase the light
- stabilize the camera
- place paper on a flat surface
- clear a surface
- draw a simple mark
- show a reflective surface
- hold up a vivid object
- say a phrase
- count backward
- declare that a task cannot be done and request a substitute

The task system is **curated and deterministic**, not freeform.  
The experience should feel adaptive, but the backend must always be in control.

---

## Non-Negotiable Product Decisions

The coding system must preserve all of these:

1. This is a **Live Agents** submission.
2. It is **voice-first**, **camera-aware**, and **interruptible**.
3. Camera access happens **in-call**, prompted naturally by the operator.
4. The room is the game board.
5. No advance prep should be required from the user.
6. Household containment tasks are the main mechanic.
7. The task pool is curated and deterministic, not invented live.
8. The library is about 15 tasks, but only 5–6 are used per session.
9. Tasks are divided by **reliability tier** and **story role**.
10. Users can swap tasks by **voice** or **button**.
11. **Ready to Verify** is a core interaction pattern.
12. Verification happens only after the user indicates readiness and holds still briefly.
13. Grounding must be visible in the HUD at all times.
14. The agent must be honest about uncertainty and never bluff.
15. Barge-in is a centerpiece and must stop audio immediately.
16. Diagnosis/flavor beats exist between tasks.
17. Sound design uses **pre-baked audio assets**, not live AI-generated sound.
18. The persona is **The Archivist, Containment Desk**.
19. The system is deterministic under the hood: tools, planner, state machine, substitutions, and recovery ladders.
20. The submission package is part of the product: repo, README, architecture diagram, cloud proof, demo, Devpost writeup.

---

## What Ghostline Is Not

Ghostline is **not**:

- a text chat app with spooky theming
- a fully freeform ghost simulation
- a true AR tracking system
- a requirement-heavy ritual kit
- a prep-heavy escape room
- a system that depends on obscure household objects
- a personalized haunting engine based on sensitive user traits
- a horror product that relies on threats, gore, harassment, or unsafe instructions

Do not drift into those directions.

---

## User Experience Goals

The experience should feel like:

- a live call
- a real operator managing a case
- a system that reacts to what the user says and shows
- a sequence with urgency and pacing
- a product that never overclaims what it verified

The user should experience:

- operator greeting
- in-call permission requests
- room assessment
- containment task assignment
- verification windows
- diagnosis questions between steps
- one interruption moment
- one recovery moment
- final case report

---

## Persona: The Archivist, Containment Desk

### Role

The operator is **The Archivist, Containment Desk**.

This persona is a calm containment specialist with an observational, procedural tone.

### Voice Qualities

- calm
- clipped
- observant
- controlled
- lightly eerie
- never melodramatic
- never comedic
- never panicked

### Instruction Style

- short commands
- one step at a time
- verify before advancing
- acknowledges uncertainty explicitly
- adapts without breaking tone

### Example Tone

Good:
- “I need your camera. Grant access now.”
- “Show me the threshold.”
- “Hold still for one second.”
- “I can’t verify that yet.”
- “No paper is fine. We’ll use the surface instead.”
- “That matches threshold activity.”
- “Stay with me. We keep this controlled.”

Bad:
- “Oh no, the demon is coming.”
- “This ghost targets people like you.”
- “Hurry or you die.”
- “Perfect, I definitely saw that” when the system did not verify it

### Mandatory Uncertainty Language

Use these kinds of phrases:

- “I can’t verify that yet.”
- “The frame is too dark to confirm.”
- “The image is too unstable.”
- “Hold still for one second.”
- “I can offer an alternative step.”
- “Switching to a safer option.”
- “I can record that as completed, but not visually verified.”
- “That matches the pattern, but I can’t confirm it from the frame alone.”

### Boundaries

The operator must:

- refuse identifying people in frame
- refuse invasive surveillance behavior
- refuse unsafe instructions
- avoid content that is threatening, hateful, sexual, or profane
- avoid user profiling as haunting logic

Do **not** tie ghost behavior to user identity, demographics, or personal profile traits.

---

## Core Interaction Structure

Ghostline should follow this general arc:

1. **Call Start**
2. **Operator greeting**
3. **In-call permission request**
4. **Room scan / calibration**
5. **Task assignment**
6. **User performs task**
7. **Ready to Verify**
8. **Verification result**
9. **Diagnosis / flavor beat**
10. **Next task**
11. **Barge-in moment at one planned point**
12. **Recovery moment at one planned point**
13. **Final seal / closure**
14. **Case report**

The system should not feel like a raw checklist.  
Between tasks, there must be short operator dialogue, diagnosis, and pacing lines.

---

## Camera and Mic Access Philosophy

Permissions are part of the hotline call, not pre-session setup.

Correct experience:

- user presses **Start Call**
- operator speaks or displays a line asking for camera access
- browser permission prompt follows
- operator acknowledges access
- same pattern for mic if needed

The product should feel like the operator is driving the session.

Do **not** build a generic “grant camera/mic” setup screen as the primary onboarding identity.

---

## Task System Overview

### Task Pool

There is a curated task library of approximately **15 tasks**.

Only **5–6 tasks** should appear in a given session.

The library should contain a mix of:

- containment tasks
- diagnostic tasks
- flavor tasks

### Reliability Tiers

Each task belongs to a reliability tier:

- **Tier 1:** high-confidence, safe for hard progression gates
- **Tier 2:** medium-confidence, often acceptable as user-confirmed-only if visual proof is weak
- **Tier 3:** flavor/fallback tasks that should not block completion

### Story Roles

Each task also has a story role, such as:

- boundary
- visibility
- stabilization
- anchor
- mark
- reflection
- diagnosis
- seal
- fallback

### Product Principle

The user should feel like the system is adapting naturally, but the backend should actually be choosing from a fixed controlled library.

No freeform invented tasks.

---

## Example Task Categories

Examples of likely tasks include:

### Strong containment / reliable tasks
- show threshold
- close boundary
- increase illumination
- stabilize camera
- place paper on a flat surface
- clear a small surface
- speak the containment phrase

### Medium-confidence ritual/flavor tasks
- draw a simple mark
- show a reflective surface
- hold up a vivid object
- optional water/sink step
- optional salt line

### Flavor / pacing tasks
- count backward
- describe the sound
- answer where it was strongest
- say “I can’t do that” and receive a substitute

Not every task needs to be in the polished demo path.

---

## Verification Philosophy

Verification is **staged**, not continuous.

The system should only attempt meaningful task verification during a deliberate **Ready to Verify** moment.

### Ready to Verify Pattern

1. User completes task
2. User taps **Ready to Verify** or says an equivalent phrase
3. Operator says “Hold still for one second.”
4. System captures a brief verification window
5. Backend returns:
   - `confirmed`
   - `unconfirmed`
   - `user_confirmed_only`

### Important Rule

The system must not bluff.

If it cannot truly verify something visually, it should say so and record it honestly.

This is core to the product identity and judging strategy.

---

## Grounding Requirements

The UI must contain a visible grounding HUD showing at minimum:

- current protocol step
- active task ID and name
- task tier
- task role category
- current path mode
- verification status
- last verified item
- block reason
- recovery step
- swap count
- operator/user transcript
- speaking/listening/interrupted status
- incident classification label if available

The HUD should be clearly readable during demo recording.

This is not a debug-only panel.  
It is a core trust and judging surface.

---

## Diagnosis / Flavor Layer

Ghostline must not feel like pure task progression.

Between tasks, the operator should ask short diagnosis questions or provide short interpretive statements, such as:

- “What did the sound resemble?”
- “Where was it strongest?”
- “Did it change with the light?”
- “That matches threshold activity.”
- “This pattern stabilizes under stronger light.”
- “Stay with me. We keep this controlled.”

These are **authored or structured lines**, not unrestricted freeform lore generation.

Diagnosis exists to:

- keep the hotline alive between tasks
- provide flavor
- create realism
- support pacing
- generate an incident classification label

Diagnosis does **not** exist to create a huge branching narrative system.

---

## Sound Design Layer

Sound is part of the product, but it should be subtle.

Use **pre-baked assets**, not live AI-generated sound.

Recommended categories:
- ambient bed
- tension stinger
- escalation warning cue
- verification success cue
- final containment result cue

Sound should support:
- hotline tension
- transitions
- recovery moment
- completion moment

Use **ambient ducking** when the operator is speaking so voice remains clear.

Headphones can be recommended, but should not be required.

---

## Barge-In Requirement

Barge-in is a first-class feature.

When the user interrupts:
- operator audio must stop immediately
- queued audio should be flushed
- UI/HUD should visibly enter interrupted/listening state
- the operator should restate briefly and cleanly

This must be demonstrable in the final demo.

---

## Recovery Requirements

Ghostline must handle two failure types:

1. **Verification failure**
2. **Capability failure** (“I can’t do that”)

### Verification Failure Recovery

Typical ladder:
- move closer
- adjust angle
- increase light
- hold still again
- retry
- switch path / substitute if necessary

### Capability Failure Recovery

Typical ladder:
- accept user constraint
- optionally ask one clarifying question
- choose substitute task with same story function
- keep progression moving
- record constraint honestly

The system must degrade gracefully and never dead-end unnecessarily.

---

## State Machine Requirement

This product must be governed by a real state machine, not loose booleans.

Expected states include:
- init
- call connected
- consent
- camera request
- calibration
- task assigned
- waiting ready
- verifying
- diagnosis beat
- recovery active
- swap pending
- paused
- completed
- case report
- ended

The system should reject illegal transitions and remain inspectable.

---

## Persistence and Cloud-Native Requirements

The backend should run on **Cloud Run** and persist session data to **Firestore**.

Structured logs should be emitted for:
- session start
- Gemini session creation
- task assignment
- verification attempt
- verification result
- swap
- recovery
- interruption
- session end
- case report generation

This supports:
- reliability
- debugging
- cloud proof recording
- architecture credibility

Do not store raw media unless absolutely necessary. Prefer structured event and state storage.

---

## Demo Strategy Requirement

This product is not just being built for flexible play.  
It is being built for **one polished judged demo**.

A first-class **Demo Mode / Rehearsal Mode** must exist.

Demo mode should provide:
- fixed safe task path
- fixed safe flavor lines
- fixed diagnosis beat
- one controlled barge-in moment
- one controlled recovery moment
- deterministic sound timing
- easy reset between takes
- readable HUD
- repeatable final case report

This is not optional polish.

---

## Submission Artifact Philosophy

The repo, README, architecture diagram, cloud proof clip, demo script, and Devpost text are part of the product.

The codebase and docs should make it easy to produce:
- public repo
- README with setup and demo replay steps
- architecture diagram
- cloud proof recording
- under-4-minute demo
- Devpost writeup aligned with rubric language

---

## Build Priorities

When making implementation choices, prioritize in this order:

1. Real Gemini Live integration
2. Stable audio input/output
3. Camera staging and Ready to Verify
4. Grounding HUD
5. Deterministic task planner and state machine
6. Barge-in correctness
7. Recovery and substitution
8. Case report
9. Demo mode
10. Submission assets
11. Optional polish

---

## What Success Looks Like

A successful Ghostline build will let a judge quickly understand:

- this is a live hotline, not a chatbot
- the operator can hear, speak, and react
- the operator uses the camera honestly
- the product has visible grounding
- interruption is real
- failure/recovery is real
- the build is hosted on Google Cloud
- the experience ends with a memorable report

That is the bar for this project.