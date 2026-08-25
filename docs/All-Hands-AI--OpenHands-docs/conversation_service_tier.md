# Conversation Service Tier

The `conversation_service_tier` module provides the HTTP and session-management layer for OpenHands conversations. It exposes authenticated API routes, validates request and response data, manages conversation lifecycle, coordinates agent sessions and runtimes, and streams conversation events to clients.

It assembles lower-level components rather than implementing agent reasoning, LLM calls, event persistence, or sandbox backends.

## Architecture

```mermaid
graph TB
    Client["Frontend / CLI / API client"] --> Core["server_core"]
    Core --> API["server_api_models"]
    API --> Sessions["server_sessions"]

    Sessions --> Controller["Agent Controller"]
    Sessions --> LLM["LLM Layer"]
    Sessions --> Memory["Memory and Condensers"]
    Sessions --> Runtime["Sandboxed Execution Layer"]
    Sessions --> Events["Event System"]
    Events --> Storage["Storage Backends"]

    API --> Providers["Provider Integrations"]
    API --> Storage
    Sessions --> Client
```

### Request and conversation lifecycle

```mermaid
sequenceDiagram
    participant C as Client
    participant K as Server Core
    participant A as API Routes
    participant W as WebSession
    participant S as AgentSession
    participant R as Runtime
    participant E as EventStream

    C->>K: HTTP request
    K->>A: Authenticate and dispatch
    A->>A: Validate request models
    A->>W: Create or start conversation
    W->>S: Initialize execution session
    S->>R: Connect runtime
    S->>E: Create or restore event stream
    W-->>C: Conversation status / ID
    E-->>W: Agent and runtime events
    W-->>C: Serialized conversation events
```

### Module boundaries

```mermaid
flowchart LR
    Core["server_core\nHTTP policies, auth, CORS,\nrate limiting, SPA serving"]
    Models["server_api_models\nPydantic contracts and routes"]
    Sessions["server_sessions\nconversation and execution lifecycle"]

    Core --> Models
    Models --> Sessions
    Sessions --> Agent["Agent Controller"]
    Sessions --> Runtime["Sandboxed Execution"]
    Sessions --> Persistence["Events and Storage"]
```

## Main responsibilities

- `server_core` supplies cross-cutting HTTP infrastructure, authentication extension points, CORS and cache policies, rate limiting, SPA fallback serving, and server configuration contracts.
- `server_sessions` owns the lifecycle of a conversation identified by `sid`, including web sessions, agent sessions, runtime and memory initialization, controller restoration, event delivery, shutdown, and LLM statistics.
- `server_api_models` defines validated API contracts and conversation-management endpoints for creating, starting, stopping, updating, searching, deleting, and enriching conversations. It also handles settings, secrets, file uploads, provider validation, and experiment configuration.

## Core component documentation

- [Server Core](server_core.md)
- [Server Sessions](server_sessions.md)
- [Server API Models](server_api_models.md)

The service tier integrates with the broader platform through:

- [Agent Controller](agent_controller.md)
- [LLM Layer](llm_layer.md)
- [Memory and Condensers](memory_and_condensers.md)
- [Sandboxed Execution Layer](sandboxed_execution_layer.md)
- [Event System](event_system.md)
- [Storage Backends](storage_backends.md)