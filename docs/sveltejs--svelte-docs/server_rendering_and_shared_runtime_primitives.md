# Server Rendering and Shared Runtime Primitives

## Purpose

The `server_rendering_and_shared_runtime_primitives` module provides the runtime foundation for Svelte’s server-side rendering and environment-neutral helpers.

It combines:

- `server_runtime`: synchronous SSR execution, HTML serialization, hydration markers, head/CSS collection, component context, stores, snippets, and render cleanup.
- `internal_shared`: reusable utilities, runtime validation, iterable/promise helpers, and compiler/runtime feature flags shared by client, server, and compatibility code.

The module is consumed primarily by compiler-generated components and higher-level client/server runtimes rather than directly by application code.

## Architecture

```mermaid
flowchart TB
    Compiler["Compiler-generated components"] --> Server["server_runtime"]
    Compiler --> Shared["internal_shared"]

    Client["Client runtime"] --> Shared
    Client --> ServerBoundary["Hydration-compatible SSR output"]

    Legacy["Legacy compatibility"] --> Shared
    Legacy --> Server

    Server --> Payload["Payload"]
    Payload --> HTML["Serialized HTML"]
    Payload --> Head["Head and CSS output"]
    Payload --> Markers["Hydration markers and IDs"]

    Shared --> Utilities["Shared utilities"]
    Shared --> Validation["Runtime validation"]
    Shared --> Flags["Async, legacy, tracing flags"]
```

### SSR render flow

```mermaid
sequenceDiagram
    participant Caller as SSR caller
    participant Render as server_runtime.render()
    participant Component as Generated component
    participant Payload as Payload
    participant Result as RenderOutput

    Caller->>Render: render(component, options)
    Render->>Payload: Create payload and render context
    Render->>Component: Invoke with payload and props
    Component->>Payload: Append body, head, CSS, markers, and IDs
    Render->>Payload: Run cleanup and close markers
    Payload-->>Result: body, html, head
    Result-->>Caller: SSR output
```

### Shared primitive flow

```mermaid
flowchart LR
    Input["Generated/runtime value"] --> Utils["Shared utilities"]
    Input --> Validate["Validation guards"]
    Runtime["Client or server runtime"] --> Utils
    Runtime --> Validate
    Compiler["Compiler modes"] --> Flags["Feature flags"]

    Utils --> Output["Normalized values and callbacks"]
    Validate --> Diagnostics["Warnings or errors"]
    Flags --> Behavior["Async, legacy, or tracing behavior"]
```

## Core components

- [server_runtime](server_runtime.md) — SSR payloads, rendering primitives, attributes, blocks, snippets, context, stores, IDs, abort signals, and diagnostics.
- [internal_shared](internal_shared.md) — shared utilities, validation policies, feature flags, and common client/server contracts.

## Module structure

```text
server_rendering_and_shared_runtime_primitives/
├── server_runtime/
│   └── packages/svelte/src/internal/server
└── internal_shared/
    └── packages/svelte/src/internal
```