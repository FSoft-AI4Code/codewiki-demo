# Storage Backends

The `storage_backends` module provides a uniform file-oriented persistence boundary for OpenHands. Consumers work with `FileStore` operations—write, read, list, and delete—while deployment configuration selects local disk, memory, Google Cloud Storage, or S3-compatible object storage. Decorators can additionally notify external systems through immediate or batched webhooks.

## Architecture overview

```mermaid
flowchart TB
    Consumers[EventStore / EventStream / controller state / settings] --> Contract[FileStore contract]
    Contract --> Backends[Concrete persistence backends]
    Backends --> Local[LocalFileStore]
    Backends --> Memory[InMemoryFileStore]
    Backends --> GCS[GoogleCloudFileStore]
    Backends --> S3[S3FileStore]
    Contract --> Decorators[Optional notification decorators]
    Decorators --> WebHook[WebHookFileStore]
    Decorators --> Batched[BatchedWebHookFileStore]
    WebHook --> External[External HTTP service]
    Batched --> External
    Status[ConversationStatus] --> ServerModels[ConversationInfo / AgentLoopInfo]
```

The module has three concerns:

1. interchangeable persistence implementations;
2. post-mutation integration notifications;
3. lifecycle vocabulary for conversations associated with persisted and active state.

## Sub-modules

- [Core file stores](storage_backends_core.md) — the `FileStore` contract and local, in-memory, GCS, and S3 implementations.
- [Webhook decorators](storage_backends_webhooks.md) — asynchronous per-operation notifications and lock-protected batching.
- [Conversation status](storage_backends_conversation_status.md) — lifecycle states consumed by server conversation and agent-loop models.

## How it fits into OpenHands

The event subsystem serializes conversation events into logical paths and uses a supplied `FileStore` to persist and retrieve them. Controller state and related services use the same abstraction, which keeps storage choice out of their core logic. Remote backends provide shared durability for deployments with multiple processes or hosts; local and memory stores support simpler or test environments. Webhook decorators extend persistence with external synchronization without changing consumers.

```mermaid
sequenceDiagram
    participant Agent as Agent/controller service
    participant Events as EventStore or state service
    participant FS as FileStore implementation
    participant Notify as Optional webhook decorator
    participant Store as Disk / memory / object store
    Agent->>Events: produce or update conversation data
    Events->>FS: write(path, serialized data)
    FS->>Notify: delegate mutation when configured
    Notify->>Store: persist through wrapped store
    Notify-->>Agent: asynchronous notification work
    Agent->>Events: read/list historical data
    Events->>FS: read/list(path)
    FS->>Store: retrieve data
    Store-->>FS: content or keys
    FS-->>Events: decoded content or paths
```

## Operational notes

- Remote stores use prefix scans to emulate directory listing and recursive deletion; object stores do not require physical directories.
- `InMemoryFileStore` decodes byte writes as UTF-8, so binary fidelity is not equivalent to S3/GCS/local stores.
- Standard webhook delivery is asynchronous after the underlying mutation; batched delivery is also asynchronous unless `flush()` is used.
- Backend and webhook errors should be handled by callers according to whether persistence or external synchronization is the critical operation.
