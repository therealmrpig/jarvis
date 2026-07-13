# J.A.R.V.I.S. Architecture (Reconstruction in progress)

## Overview
*Status: Stable development.*

## Core Roles

### Client
Handles user interaction and hardware I/O. 
- **Responsibilities**: STT, TTS, Audio handling, Silence detection, Wakeword.
- **Flow**: Sends transcribed text to Server $\rightarrow$ Receives text from Server $\rightarrow$ Converts text to audio for the user.
- **Interaction**: Capable of "Barge-in" (interrupting playback) locally without server involvement.

### Server
The central intelligence and orchestration hub. Supports multiple concurrent clients.
- **Design Pattern**: Uses a single instance of heavy modules (e.g., LLM, Embeddings) shared across all clients, managed via an asynchronous queue to handle resource contention.
- **Orchestrators**:
    - **Per-User Orchestration**: Each connected user (identified by `session_id`) runs their own dedicated orchestrator instances for the duration of their connection. 
    - **Autonomous Maintenance**: The server also runs maintenance orchestrators (REM, STM) autonomously, scanning all existing user databases to perform nightly tasks regardless of active WebSocket connections.
    - **Conversation Orchestrator**: Manages real-time dialogue, handles incoming text, and manages conversation context for a specific user session. 
        - *Note*: When heavy tasks (Secretary/STM) occupy the LLM queue, this orchestrator waits for its turn before sending a response. No intermediate "processing" ACK is sent.
    - **Secretary (Name TBD)**: Handles external data streams (emails, schedule, news). Processes info to decide if a "nually" needs to be sent to the client. Accesses all available memory chunks, including those awaiting nightly review.
    - **REM Orchestrator**: A nightly process. It performs a similarity pass on existing vectors to identify potential conflicts, followed by an LLM Reviewer pass to resolve them and apply "truce" logic to persistent conflicts.
    - **Short Term Memory (STM) Orchestrator**: Monitors sessions for inactivity. When the threshold is hit, it flushes context into long-term storage. 
        - *Efficiency*: Databases are created lazily by the STM upon the first successful flush of an active session to avoid wasting resources on empty databases.

## Tools & Execution

### Tool Registry (`server/tools/registry.py`)
The capability manifest. Every tool is a standalone function that registers itself (along with its JSON schema) into this registry. 

### Lightweight Executor (`server/executor.py`)
An intermediary that bridges the gap between LLM-generated intent and functional execution. It intercepts tool calls from the `ConversationOrchestrator`, resolves them against the `Registry`, executes the corresponding function, and returns the result to the orchestrator.

## Data & Memory Architecture

### Multi-Tenancy & Isolation
To ensure absolute privacy and prevent cross-context "noise," **each user is assigned a completely separate memory database.**
- **Isolation**: A `session_id` (username) maps to a dedicated, isolated database instance. 
- **Zero Leakage**: No retrieval operation can access data from another user's database.

### Vault Architecture
The vault is split into two layers:
1. **Broker (`server/vault/broker.py`)**: The high-level Orchestrator API. It provides simple methods like `retrieve_context(user_id, query)` and `persist_memory(user_id, text)`.
2. **Storage (`server/vault/storage.py`)**: The low-level engine. Handles embedding generation, vector similarity search ($k=5\text{-}10$), and database I/O.

## Communication Protocol (WebSocket JSON)

### Client $\rightarrow$ Server
- `text`: The transcribed utterance string.
- `session_id`: Identifier for the user context (Username).

### Server $\rightarrow$ Client
- `type`: The nature of the message (`text`, `nugg`).
- `text`: The payload content to be spoken or displayed.
- `priority`: (Optional) Used for nudges/alerts to inform the client of urgency (determines if Barge-in is required).
