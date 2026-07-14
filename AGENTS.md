# J.A.R.V.I.S. Project Context

## Mission
J.A.R.V.I.S. is a local, multi-tenant, AI-powered voice assistant. It operates as a Client/Server hybrid where the Client handles hardware I/O (Audio $\rightarrow$ Text) and the Server serves as the central intelligence hub (Text $\rightarrow$ Intelligence $\to$ Text/Nudge).

## Agent Instruction: Start Here
**DO NOT explore the codebase blindly.** To understand the design patterns, communication protocols, and module boundaries, you **must** load and read these files first. Load them on the first turn of the conversation, before answering any prompt. THIS IS AN INSTRUCTION YOU NEED TO FOLLOW.

1.  `architecture.md`: The Single Source of Truth (SSoT) for the system's design, protocol, and logic.

---

## Core Architectural Principles
- **Asynchronous Task-Future Pattern**: Orchestrators trigger heavy modules (LLM/Embeddings) via queues and `await` their results via `asyncio.Future`.
- **Reactive Dispatching**: The `entrypoint` does not block; it dispatches events to orchestrators, which manage their own lifecycle and interruption (Barge-in) logic.
- **Multi-Tenant Isolation**: Every user is assigned a distinct, isolated database instance.
- **Lazy Provisioning**: Databases are only created when the `STM` orchestrator confirms a session needs persistence.
