# J.A.R.V.I.S. Domain Architecture Specification

**Version:** 0.2  
**Date Created:** 2024-06-15  
**Last Updated:** 2024-06-15 (ReM Integration & Idle Threshold Update)  
**Status:** Locked (Grilling Session Complete)  
**Purpose:** Serves as the single source of truth for domain terminology, module boundaries, and routing logic. 

---

## 1. Architectural Primer

J.A.R.V.I.S. is a modular, client-server voice assistant designed to operate as an autonomous secretary. The architecture strictly enforces **one function per module** with stateless orchestrators handling routing and context assembly. All internal communication between modules uses a strict `Text-In / Text-Out` contract.

- **Client Role:** Handles hardware I/O (Wakeword, VAD, audio streaming). Converts silence-boundary audio to text and forwards it to the server. Acts as an audio renderer for TTS output.
- **Server Role:** Hosts all AI logic, memory vaults, and orchestration engines. Processed data never leaves the LAN unless explicitly routed for playback.
- **RAM Discipline:** Modules live as single shared instances across the server. Orchestrators hold only lightweight session state; they do not duplicate module logic in memory.

---

## 2. Ubiquitous Language (Glossary)

| Term | Definition |
|------|------------|
| `Orchestrator` | A stateless routing engine that assembles prompts, calls modules, and manages flow control. Never holds business data. |
| `Module` | A single-purpose, reusable function wrapped in a strict interface. Callable from any orchestrator. Lives once on the server. |
| `Central Vault` | Persistent server storage split into two domains: **Active Data Index** (Calendar/Email) and **Vector Memory DB** (Long-term facts). |
| `ContextCache` | Ephemeral in-RAM storage holding the active conversation thread. Flushed or overwritten based on silence triggers. |
| `ReMOrchestrator` | The autonomous nightly engine responsible for memory consolidation, conflict resolution, and "sleeping" housekeeping. |
| `SilencePulseTrackerModule` | Idle-time tracker that manages monotonic timestamps to detect conversation boundaries (currently set to 15 min). |
| `DeltaSyncModule` | Background listener that compares the Central Vault's timestamp against JARVIS's local cache and triggers updates when they differ. |
| `UrgencyScorer` | Deterministic rule-set that evaluates incoming data payloads `[Title, Impact_Summary, Alert_Type]`. Returns priority levels to bypass background processing. |
| `Stream-Then-Switch` | Interruption policy: JARVIS finishes his current utterance → pauses ~1s → injects urgent update via TTS. Zero mid-stream cutting or regeneration. |

---

## 3. Module Specifications (Contracts)

All modules strictly adhere to the `Text_In → Text_Out` contract. Network transport layers handle encoding; modules never inspect raw audio or binary payloads.

| Module Name | Responsibility | Input Contract | Output Contract | Hosting |
|-------------|----------------|-------------------------------------------------|-----------|
| `Wakeword_VadAdapter` | Client-side trigger & stream segmentation | Raw audio buffer → VAD silence detection | Transcribed text string (`client_id`, `session_id`, `utterance`) | Client |
| `StreamRouter` | Incoming message partitioning & priority injection | `{"text": "...", "priority": "LOW"|"HIGH"}` | Routes to Orchestrator queue | Server |
| `SilencePulseTrackerModule` monitors idle time by receiving a timestamp update on every input event. It does not hold memory; it only checks `(now() - last_event) > threshold`. | Client or Server | `{last_input_unix_ms: number}` | `{is_idle: boolean, elapsed_seconds: number}` |
| `ConversationOrchestrator` | Real-time dialogue, context assembly, response generation | `{"prompt": "...", "context_cache": [...]}` | `{"response_text": "...", new_context_cache: [...]}` | Server |
| `SecretaryOrchestrator` | Background delta scanning & rule-based filtering | Triggered by `DeltaSyncModule` | `{action: "interruption"|"log", payload: [...]}` | Server |
| `UrgencyScorer` | Deterministic priority evaluation | Raw email/calendar objects / config-driven rules | `{"priority": "HIGH"|"MEDIUM"|"LOW"}` | Server |
| `InterruptionFilter` | Structuring autonomous data for routing | Raw inbox/calendar rows | `[Title, Summary_of_Impact, Alert_Type]` | Server |
| `MemoryOrchestrator` | Auto-flushing idle conversations into long-term memory | Triggered by `SilencePulseTrackerModule` (15m threshold) | List of free-text chunks: `["chunk_1", "chunk_2"]` | Server |
| `ReMOrchestrator` (Consolidation) | Autonomous conflict resolution & vault pruning for long-term memories | Vector DB chunk indices | Review queue payloads / merge/delete directives | Server |
| `MemoryRetrieverModule` | Semantic extraction at generation time | `{query: "...", session_scope: "active"|"historical"}` | Raw context string blocks `[string_1, string_2...]` | Server |
| `DataRetrieverModule` | Precise active data fetching on-demand | `{target: "calendar"|"email", range, filters}` | Structured text blocks (JSON/CSV) | Server |
| `TTSModule` | Voice synthesis & playback routing | `{"text": "...", "priority": "HIGH"|"LOW"}` | Raw audio bytes or local playback trigger | Client or Server (swappable) |

---

## 4. Orchestrator Routing Logic

### 4.1 ConversationFlow (Primary Path)
1. Client detects `0.5s VAD silence` → transcribes → sends text to server.
2. `StreamRouter` evaluates priority. Spoken input always injects as `HIGH`.
3. `ConversationOrchestrator` preempts background work, pulls fresh data via `DataRetrieverModule`, appends free-text blocks from `MemoryRetrieverModule`, and feeds the prompt to the local LLM (Gemma).
4. Response text → `TTSModule` → queued for playback.

### 4.2 SecretaryFlow (Background Path)
1. Runs statelessly on its own cycle. **Never references conversation context.**
2. `DeltaSyncModule` detects vault updates → feeds raw rows to `InterruptionFilter`.
3. `UrgencyScorer` applies local config rules (`family_email`, `starts_in_minutes < 15`, etc.).
4. High-priority results bypass the queue and trigger a TTS injection via `Stream-Then-Switch` policy.

### 4.3 MemorySynthesisFlow (Idle Path)
1. Monitored exclusively by `SilencePulseTrackerModule`. 
2. Once the tracker signals **15 minutes** of continuous silence, it triggers the `MemoryOrchestrator`.
3. **Flushing:** The `MemoryOrchestrator` summarizes active `ContextCache` and outputs a concrete list of free-text chunks to the Vector DB vault.

---

## 5. Memory Lifecycle & Conflict Protocol (ReM)

| Phase | Mechanism | Domain Rule |
|-------|-----------|-------------|
| **Creation** | Auto-flush after **15m idle threshold** → `MemoryOrchestrator` outputs raw string list. | No LLM in daytime autonomous loops. Free-text initially stored. |
| **Retrieval** | On demand during generation or via `Stream-Then-Switch`. | `MemoryRetrieverModule` returns unfiltered text blocks. Orchestrator stitches context manually. |
| **Aging** | Nightly consolidation pass triggers automatic roll-up of distant memories into period memos via `ReMOrchestrator`. | Keeps vault size bounded & semantically dense. |
| **Conflict Resolution** | Vector-similarity check flags ambiguous pairs → `LLMReviewer` analyzes textually within ReM. | If a conflict pair is rejected 5 consecutive nights → **Protected Truce**: stops triggering alerts for those pairs until one appears in an unprotected state. |
| **Storage** | Centralized Vault Index (Active) + Vector DB (Long-Term). Multi-user differentiated by lightweight LAN ID. | Strict separation of transient session RAM from persistent disk layers. |

---

## 6. Key Design Decisions & Rationale

| Decision | Tradeoff Explained | Future-Proofing |
|----------|-------------------|-----------------|
| `Pure Text-In / Text-Out` | Trades initial audio latency complexity for flawless module portability and zero binary coupling. | Allows STT/TTS to be hosted client/server dynamically based on real-time machine specs without touching core logic. |
| `0.5s VAD Silence Trigger` | Risks capturing mid-sentence breaths vs. guarantees responsive listening. Validated by advanced local VAD to prevent false positives. | Keeps input contract predictable for server routing. |
| `Stream-Then-Switch` Interruption | Trades "instant cutting" for absolute conversational clarity and zero hallucination/regen overhead during playback. | Matches human turn-taking latency; simplifies TTS buffer management. |
| `Deterministic Secretary + LLM Reviewer` | Banning LLMs from daytime scanning prevents token burn & unpredictable latency. Offloads nuance to bounded nightly review. | Guarantees 100% uptime for background tasks while preserving AI flexibility safely. |
| `Protected Truce Protocol` | Prevents infinite LLM loops on ambiguous or newly rephrased memories. Stops vector drift from degrading vault quality over months of autonomy. | Requires zero manual curation but maintains mathematical safety boundaries. |

---

## 7. How to Read This Document Later

1. **Looking for a specific feature?** → Check Section 4 (Orchestrator Routing) or Section 5 (Memory Lifecycle).
2. **Debugging a module error?** → Review Section 3 contracts. If input/output doesn't match the table, routing will fail.
3. **Adding a new autonomous task?** → Use `SecretaryOrchestrator` as a template. Remember: daytime tasks MUST be rule-based or vector-filtered. LLMs belong only in bounded review layers or the conversation loop.
4. **Scaling to multiple LAN users?** → All stateful routing keys (`user_id`, `session_id`) are passed per-payload in the text contract. Vault queries must prefix filters with `{user_id}`.

---
*Document locked upon shared understanding confirmation. Architecture matches grilling session conclusions.*
