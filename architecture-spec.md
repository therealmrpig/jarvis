# J.A.R.V.I.S. Implementation Specification

**Version:** 1.0 (Python Stack)  
**Date:** 2026-07-12  
**Status:** Approved  

---

## 1. High-Level Architecture
J.A.R.V.I.S. operates as a **Client/Server hybrid** hosted locally on the user's LAN. 
*   **The Client** is strictly I/O bound (Hardware: Mic/Speaker). It performs offline STT (Speech-to-Text) and sends only `Text-In` to the server.
*   **The Server** is the autonomous brain. It handles all AI logic, memory management, and "secretary" background processes via a persistent WebSocket connection.

### Core Contract: Pure Text-In / Text-Out
Network transport layers (WebSocket) handle audio streaming as bytes or text; however, core modules adhere to strict text contracts. Audio encoding/decoding is strictly isolated on the client and TTS service sides.

---

## 2. File System Layout

### **Client Layer (`./client`)**
*   `audio.py`: Singleton hardware handler. Opens the microphone once, streams raw PCM chunks into an in-memory queue forever.
*   `wakeword.py`: Passive listener on the audio queue. Detects "Jarvis" and signals the pipeline to wake up.
*   `vad.py`: Active detector. Listens to the active stream for 0.5-second silence gaps (end-of-sentence).
*   `stt.py`: Transcribes the identified sentence chunks into text strings locally.
*   `streamer.py`: WebSocket client. Sends transcribed text to the Server; receives response text and handles playback triggers.

### **Server Layer (`./server`)**
*   `entrypoint.py`: **The Message Loop**. A central asynchronous engine that manages the persistent connection with the client, routes incoming messages to Orchestrators, and pushes background alerts back to the client. *(Replaces routing.py)*
*   `orchestrators/`:
    *   `conversation_orchestrator.py`: Manages real-time dialogue and LLM calls.
    *   `secretary_orchestrator.py`: Background process for scanning active data (Email/Calendar).
    *   `working_memory_orchestrator.py`: Auto-summarizes RAM into long-term memory after idle thresholds.
    *   `rem_orchestrator.py`: Nightly engine for vector memory conflict resolution.
*   `vault/indexing.py`: The abstraction layer for all Vector DB interactions (embedding, tagging, persistence).

---

## 3. Critical Module Behaviors & Protocols

### 3.1 Client Audio Pipeline
The client uses a **Stream Handover Model** to eliminate latency between sentences:
1.  `audio.py` maintains a constant connection to the OS mic.
2.  `wakeword.py` watches for activation.
3.  Upon activation, `vad.py` watches for silence boundaries.
4.  `stt.py` immediately transcribes the chunk and sends it via WebSocket to `entrypoint.py`.

### 3.2 Server "Message Loop" (entrypoint)
Instead of a static router, `entrypoint.py` acts as a dynamic switchboard:
*   **Upstream (Client):** When the client sends `{"text": "..."}`, the loop dispatches it to `conversation_orchestrator`.
*   **Downstream (Server):** When the `secretary_orchestrator` finds a high-priority item, it injects data back through the WebSocket to the client.

### 3.3 Interruption Policy: "Stream-Then-Switch"
To maintain conversational clarity:
1.  If an urgent message arrives via SecretaryFlow while J.A.R.V.I.S. is speaking, the response must **finish its current utterance** first.
2.  The urgent text is queued and injected after a ~1s pause.
3.  No mid-stream cutting or regeneration is permitted.

### 3.4 Memory Lifecycle (ReM)
1.  **Creation:** `SilencePulseTrackerModule` on the server tracks idle time. Once >15 minutes of silence, `working_memory_orchestrator.py` triggers an LLM summarization of current RAM chunks.
2.  **Storage:** Summarized text strings are passed to `vault/indexing.py` for embedding and storage in the Central Vault.
3.  **Consolidation:** Nightly, `rem_orchestrator.py` (ReM) scans vectors for ambiguous pairs. It uses an LLM Reviewer to resolve factual conflicts or applies a "Protected Truce" protocol if unresolved after several nights.

---

## 4. Payload Standards
*   **Client → Server:** 
    *   `{"text": "...", "priority": "HIGH", "session_id": "..."}`
*   **Server → Client (Response):** 
    *   `{"type": "text", "text": "..."}` for standard TTS.
    *   `{"type": "interruption", "text": "..."}` for urgent background updates.

---

## 5. Implementation Notes
*   **Tools Registry:** Live data tools (Calendar, Email) are stored in `tools/registry.py` purely as definitions provided to the LLM's function-calling interface. The Orchestrators do not import these APIs directly.
*   **Vault Abstraction:** `vault/indexing.py` is the only file with access to database schemas. Orchestrators interact exclusively with abstract text chunks and IDs to prevent data leakage between memory domains.
