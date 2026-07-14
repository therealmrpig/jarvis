# J.A.R.V.I.S. Architecture (Reconstruction in progress)

## Overview
*Status: Being reworked. Previous specs (`architecture-spec.md`, `domain-architecture.md`) are slated for deletion.*

## Core Roles

### Client
Handles user interaction and hardware I/O. 
- **Responsibilities**: STT, TTS, Audio handling, Silence detection, Wakeword.
- **Flow**: Sends transcribed text to Server $\rightarrow$ Receives text from Server $\rightarrow$ Converts text to audio for the user.
- **Interaction**: Capable of "B2B" (Barge-in) locally without server involvement.

### Server
The central intelligence and orchestration hub. Supports multiple concurrent clients.
- **Design Pattern**: Uses a single instance of heavy modules (e.g., LLM, Embeddings) shared across all clients, managed via an asynchronous queue to handle resource contention/RAM constraints.
- **Entrypoint (The Dispatcher)**: A reactive WebSocket server. It does **not** block on task completion. Its sole responsibility is to receive incoming messages and dispatch them immediately to the appropriate Orchestrator instance via a `handle_event()` interface.
- **Orchestrators**:
    - **Lifecycle Management**: Each Orchestrator manages its own internal state, including tracking its currently executing `asyncio.Task`. This allows the Orchestrator to self-interrupt when a "Barge-in" event is dispatched to it via the Entrypoint.
    - **Per-User Orchestration**: Each connected user (identified by `session_id`) runs their own dedicated orchestrator instances for the duration of their connection. 
    - **Conversation Orchestrator**: Manages real-time dialogue, handles incoming text, and manages conversation context for a specific user session. 
        - *Note*: When heavy tasks (Secretary/STM) occupy the LLM queue, this orchestrator waits for its turn before sending a response back to the client. No intermediate "processing" ACK is sent.
    - **Secretary (Name TBD)**: Handles external data streams (emails, schedule, news). Processes info to decide if a "nudge" is required for the client. Accesses all available memory chunks, including those awaiting nightly review.
    - **REM Orchestrator**: A nightly process. It performs a similarity pass on existing vectors to identify potential conflicts, followed by an LLM Reviewer pass to resolve them and apply "truce" logic to persistent conflicts.
    - **Short Term Memory (STM) Orchestrator**: Monitors sessions for inactivity. When the threshold is hit, it flushes context into long-term storage. 
        - *Efficiency*: Databases are created lazily by the STM upon the first successful flush of an active session to avoid wasting resources on empty databases.

## Tools & Execution

### Tool Registry (`server/tools/registry.py`)
The capability manifest. Every tool is a standalone function that registers itself (along with its JSON schema) into this registry. 

### Lightweight Executor (`server/executor.py`)
An intermediary that implements the "Function Calling" loop. It intercepts tool-use intents from the Orchestrator, resolves them against the `Registry`, executes the corresponding function, and returns the result to the Orchestrator.

## Data & Memory Architecture

### Multi-Tenancy & Isolation
To ensure absolute privacy and prevent cross-context "noise," **data is partitioned by user within the shared database.**
- **Isolation**: A `session_id` (username) filters all queries to ensure zero leakage between users. 
- **Zero Leakage**: No retrieval operation can access data from another user's partition.

### Memory Retrieval Mechanism
During the generation phase in `ConversationOrchestrator`:
- **Method**: Semantic retrieval via Embedding Model + Vector Similarity search within the user's specific database.
- **Scope**: Retrieves the top $k$ (where $k=5\text{-}10$) most relevant context chunks from the user's dedicated vault to augment the LLM prompt.

## Communication Protocol (WebSocket JSON)

### Client $\rightarrow$ Server
- `text`: The transcribed utterance string.
- `session_id`: Identifier for the user context (Username).

### Server $\rightarrow$ Client
- `type`: The nature of the message (`text`, `nudge`).
- `text`: The payload content to be spoken or displayed.
- `priority`: (Optional) Used for nudges/alerts to inform the client of urgency (determs if a Barge-in is required).
