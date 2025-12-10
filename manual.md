# VOCEVIBE // MANUAL

**v1.7.0**

--------------------------------------------------------------------------------
## SYSTEM OVERVIEW
--------------------------------------------------------------------------------
VoceVibe is a real-time AI engine that transforms speech into visual prompts and summaries. It uses two parallel "brains" to analyze your conversation:

### 1. FAST BRAIN (SDXL)
*   Listens to every word in real-time.
*   Generates instant, stream-of-consciousness visual prompts.
*   Designed for immediate reaction and vibe visualization.

### 2. SLOW BRAIN (LLM)
*   Analyzes the conversation flow over longer periods.
*   Generates concise summaries and "Visual Context" descriptions.
*   Provides the "Big Picture" understanding.

--------------------------------------------------------------------------------
## CONTROLS & SETTINGS
--------------------------------------------------------------------------------

### ⏱️ HISTORY SLIDER (30s - 300s)
*   Controls the "Memory Span" of the Brain.
*   **Short (30s)**: Brain only remembers the last few sentences. Good for rapidly changing topics.
*   **Long (300s)**: Brain remembers the last 5 minutes. Good for deep conversations and storytelling.

### ⚡ RATE SLIDER (Fastest - 60s)
*   Controls how often the Fast Brain generates a new prompt.
*   **Fastest**: Triggers on every completed phrase/sentence. Highly reactive.
*   **2s - 60s**: Triggers at a fixed interval. More stable, less chaotic.

### ⏸ PAUSE / ▶ START
*   **PAUSE**: Stops the AI engines to save CPU/GPU, but **keeps the memory**. Use this if you need a break but want to continue the same session.
*   **START**: Resumes operation instantly.

### 🗑 MEMORY RESET
*   The "Nuclear Option".
*   Clears all transcript history and Brain memory.
*   Use this when starting a completely new topic.

### ✖ QUIT
*   Performs a clean shutdown of all systems and closes the app.

### 📡 OSC TARGET
*   Sends data to external apps (Resolume, TouchDesigner, etc.).
*   **Default Port**: 2992
*   **Addresses**:
    *   `/visual/prompt` (String)
    *   `/summary/text` (String)
    *   `/summary/image_prompt` (String)

--------------------------------------------------------------------------------
## 📝 GLOBAL CONTEXT
--------------------------------------------------------------------------------
*   Type keywords or style instructions in the **GLOBAL CONTEXT / VIBE** box (bottom right).
*   The Brain will incorporate this "Vibe" into **every** visual prompt.
*   **Examples**: "Cyberpunk Noir", "Focus on nature", "Surreal Dali style".
*   Resetting memory clears this field by default.

--------------------------------------------------------------------------------
## TIPS FOR BEST RESULTS
--------------------------------------------------------------------------------
*   Speak clearly into the microphone.
*   For wild, trippy visuals, use **Fastest** rate and short history.
*   For coherent story illustration, use **~60s** history and **~10s** rate.
*   If the Brain gets stuck on an old topic, hit **MEMORY RESET**.
