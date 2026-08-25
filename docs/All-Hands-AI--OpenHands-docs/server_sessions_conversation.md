# Server Sessions: Server Conversation

`ServerConversation` is a lightweight runtime facade for server code that needs to
connect to, inspect, or disconnect a conversation runtime without owning the full web
session lifecycle.

Source: `openhands/server/session/conversation.py::ServerConversation`

## Construction modes

```mermaid
flowchart TD
    A[ServerConversation(sid, config)] --> B{Existing EventStream?}
    B -->|No| C[Create EventStream]
    B -->|Yes| D[Reuse EventStream]
    C --> E{Existing Runtime?}
    D --> E
    E -->|No| F[Resolve configured runtime class]
    F --> G[Construct runtime attach_to_existing=True]
    E -->|Yes| H[Reuse runtime; mark attached]
    G --> I[Conversation facade]
    H --> I
```

With no runtime supplied, the class creates one using a fresh `LLMRegistry`, the
conversation configuration, and an attach-to-existing runtime mode. With a runtime
supplied, it assumes another owner manages that runtime and sets `_attach_to_existing`.
An event stream can likewise be injected to share the conversation's event history.

## Lifecycle contract

`connect()` connects only runtimes created by this facade. `disconnect()` closes the
event stream and schedules runtime shutdown only when this facade owns the runtime;
attached runtimes are intentionally left untouched. `security_analyzer` delegates to
the runtime, allowing callers to use the same security policy boundary as the active
execution environment.

This ownership distinction prevents a temporary server helper from terminating a
runtime still used by the primary [Agent Session](server_sessions_agent.md).

## Related components

Runtime implementations and attach semantics belong to the [Sandboxed Execution Layer](sandboxed_execution_layer.md).
The shared stream and file persistence contracts are described in [Event System](event_system.md)
and [Storage Backends](storage_backends.md).

