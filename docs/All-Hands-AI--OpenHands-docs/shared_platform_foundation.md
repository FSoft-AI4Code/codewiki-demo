# Shared Platform Foundation

The `shared_platform_foundation` module provides OpenHands’ cross-cutting platform services and contracts. It standardizes configuration, shared schemas, event transport, persistence, and observability so that agents, controllers, runtimes, memory, servers, and clients can interoperate without depending on implementation-specific details.

## Architecture

```mermaid
graph TB
    subgraph Foundation["shared_platform_foundation"]
        CFG["Core configuration"]
        SCHEMA["Core schemas and runtime support"]
        EVENTS["Event system"]
        STORE["Storage backends"]
        LOG["Logging and observability"]
    end

    INPUT["CLI / environment / programmatic input"] --> CFG
    CFG --> AGENT["Agents and controllers"]
    CFG --> RUNTIME["Runtime implementations"]
    CFG --> MEMORY["Memory and condensers"]

    AGENT <--> SCHEMA
    RUNTIME <--> SCHEMA
    MEMORY <--> SCHEMA

    AGENT --> EVENTS
    RUNTIME --> EVENTS
    MEMORY --> EVENTS
    EVENTS --> STORE
    EVENTS --> CLIENTS["Server, frontend, and integrations"]

    AGENT --> LOG
    RUNTIME --> LOG
    EVENTS --> LOG
    STORE --> LOG
```

The primary runtime interaction is an event-driven action/observation loop:

```mermaid
sequenceDiagram
    participant Agent
    participant Schema as Shared schemas
    participant Stream as EventStream
    participant Runtime
    participant Memory
    participant Store as FileStore
    participant Logger

    Agent->>Schema: Create typed Action
    Agent->>Stream: Publish action event
    Stream->>Store: Persist serialized event
    Stream->>Runtime: Dispatch action
    Runtime->>Schema: Create Observation
    Runtime->>Stream: Publish observation event
    Stream->>Memory: Update conversation history
    Memory->>Agent: Provide recalled or condensed context
    Agent->>Logger: Emit diagnostic records
    Stream->>Logger: Emit event activity
```

## Core components

- [Core Configuration](core_configuration.md) — typed and validated settings for CLI behavior, Kubernetes runtimes, security controls, and conversation condensation.
- [Core Schema and Runtime Support](core_schema_and_runtime_support.md) — shared action, observation, agent-state, message, prompt, serialization, bootstrap, and terminal-support contracts.
- [Logging](logging.md) — application and LLM logging, JSON or colored output, secret redaction, rotating files, exception context, and runtime progress display.
- [Event System](event_system.md) — typed event hierarchy, ordered event streams, subscriber dispatch, event serialization, and durable event persistence.
- [Storage Backends](storage_backends.md) — the `FileStore` abstraction with local, in-memory, Google Cloud Storage, S3-compatible, and webhook-enabled implementations.

Together, these components form the platform boundary beneath OpenHands’ agent reasoning, sandbox execution, conversation service, integrations, and user-facing clients.