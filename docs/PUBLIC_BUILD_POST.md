# How I Built Ghostline: 56 Prompts and a Paranormal Hotline ðŸ‘»ðŸ“ž

*This post was created for the purposes of entering the Gemini Live Agent Challenge. #GeminiLiveAgentChallenge*

Most people approach building AI apps like a freeform chatâ€”endlessly iterating code back and forth, hoping the LLM doesn't hallucinate and break the entire structure.

For the **Gemini Live Agent Challenge**, I wanted to approach it differently. I wanted to build **Ghostline**, a live paranormal hotline powered by Gemini Live. But rather than chaotic open-ended prompting, I drafted a structured **56-step build guide** and handed it straight to Google Antigravity (Google's AI agent).

It almost one-shot the entire architecture. Here is how I built it and why this method changes the way we should think about AI development. ðŸ§µ

## The Inspiration: "Ghostfacers" ðŸŽ¬

If you've watched *Supernatural*, you probably remember the **"Ghostfacers"**â€”the amateur, reality-show ghost hunters who are always getting in over their heads. I loved that energy.

But for a multimodal AI interaction, I didn't want the user to talk to a theatrical horror narrator. Instead, I wanted the user to step into the shoes of the frantic caller dealing with a *Supernatural*-style breach, dialing into a calm, procedural **Containment Desk**. The operatorâ€”The Archivistâ€”would use Gemini Live's audio and vision capabilities to try to verify and contain the paranormal incident in the user's room.

*(Note: I'll be posting a separate article later detailing what Ghostline is and how to play it. This article is all about HOW I built it).*

## Building by "Build Guide" ðŸ› ï¸

Instead of jumping into an IDE and prompting line-by-line, I spent my time writing a **56-prompt milestone-based build guide**. I treated the AI agent like a senior engineer executing a rigorous spec.

Here is the flow I defined:
1. **Stack Lock:** Define the stack upfront (React/Vite frontend, FastAPI/WebSockets backend).
2. **Session Architecture:** Map out the exact state machine that prevents the AI from just making up tasks.
3. **Live Audio Bridge:** Connect to Vertex AI / Gemini Live for low-latency, interruptible voice.
4. **Task Flow & Vision System:** Implement the "staged verification" where the AI checks the live camera feed honestly.
5. **Deployment:** Push to Google Cloud Run and verify with Cloud Logging.

I handed the 56-prompt guide to the Google agent, and because the instructions were rigorously phased, it practically **one-shot** the core structure of the app. It forced the AI to solve problems phase-by-phase without hallucinating out of scope.

The beauty of this approach is that the build guide is in the public repository. **You can literally pull up my prompt guide and work backwards** to see exactly how the AI built the product from the ground up!

## The Google Cloud Stack â˜ï¸

Using an AI agent to build the code is only half the battle; the architecture needs to be hosted robustly. For Ghostline, the integration with Google Cloud was essential:

ðŸ”¹ **Vertex AI & Gemini Live:** Powered the real-time, interruptible multi-modal voice and vision. 
ðŸ”¹ **Google Cloud Run:** Hosted the FastAPI backend. It gave the app the scale, fast cold starts, and reliability needed for maintaining active live WebSocket connections.
ðŸ”¹ **Cloud Logging:** Handled structured session tracking. This allowed me to provide operational proof that the backend and the Gemini sessions were genuinely running live on GCP.

By forcing the project through explicit phasesâ€”from local audio to Vertex AI integration to a fully automated Cloud Run deploymentâ€”the build guide created a stable spine that the AI could easily execute against.

## The Takeaway ðŸ§ 

Treating AI like an open-ended chatbot makes building software brittle. Treating it like an execution engine for a rigorous, phased **build guide** makes it incredibly reliable and powerful. 

If you want to see exactly how those 56 prompts structured the project, check out the repository. And if you're ever dealing with a containment breach... call The Archivist. ðŸ“¸ðŸ”¦

ðŸ”— **Code & Build Guide:** `https://github.com/YashSerai/GhostLine-for-Gemini-Live-Agent-Challenge/tree/main`
ðŸ“¹ **Demo:** `https://youtu.be/hWQC8xShboc`
