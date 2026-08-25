# CDP Backend Automation Implementation

## Purpose

The `cdp_backend_automation_implementation` module is Puppeteer’s Chromium/CDP-specific automation backend. It implements the protocol-neutral browser automation API by translating public operations into Chrome DevTools Protocol commands and events.

The module manages:

- Browser contexts, targets, pages, frames, and workers.
- Frame trees, navigation, execution worlds, and JavaScript handles.
- Network requests, responses, interception, authentication, and emulation.
- Keyboard, mouse, touchscreen, viewport, and browser-environment controls.
- Coverage collection, tracing, screencast recording, and console diagnostics.

It depends on the CDP transport/session layer for communication with Chromium and is consumed by the protocol-neutral public API.

## Architecture

```mermaid
flowchart TD
    API[Protocol-neutral public automation API]
    Transport[CDP transport and sessions]
    Browser[Browser and target lifecycle]
    Page[Page and frame lifecycle]
    Runtime[Execution contexts and handles]
    Network[Network stack]
    Input[Input and emulation]
    Observability[Coverage, tracing, and recording]
    Chrome[Chromium via CDP]

    API --> Browser
    API --> Page
    API --> Runtime
    API --> Network
    API --> Input
    API --> Observability

    Browser --> Page
    Page --> Runtime
    Page --> Network
    Page --> Input
    Page --> Observability

    Browser --> Transport
    Page --> Transport
    Runtime --> Transport
    Network --> Transport
    Input --> Transport
    Observability --> Transport
    Transport --> Chrome
```

### Lifecycle and event flow

```mermaid
sequenceDiagram
    participant User as Automation code
    participant API as Public API
    participant Backend as CDP backend
    participant Session as CDP session
    participant Chrome as Chromium

    User->>API: Create page, navigate, evaluate, or interact
    API->>Backend: Invoke CDP implementation
    Backend->>Session: Send protocol command
    Session->>Chrome: CDP command
    Chrome-->>Session: Response and protocol events
    Session-->>Backend: Routed events
    Backend->>Backend: Update targets, frames, contexts, requests, and state
    Backend-->>API: Public objects and events
    API-->>User: Page results or lifecycle notifications
```

### Component relationships

```mermaid
classDiagram
    class CdpBrowser
    class CdpBrowserContext
    class TargetManager
    class CdpTarget
    class CdpPage
    class FrameManager
    class CdpFrame
    class IsolatedWorld
    class ExecutionContext
    class CdpJSHandle
    class NetworkManager
    class EmulationManager
    class CdpKeyboard
    class CdpMouse
    class CdpTouchscreen
    class Coverage
    class Tracing
    class ScreenRecorder

    CdpBrowser --> TargetManager
    CdpBrowser --> CdpBrowserContext
    TargetManager --> CdpTarget
    CdpTarget --> CdpPage
    CdpPage --> FrameManager
    FrameManager --> CdpFrame
    CdpFrame --> IsolatedWorld
    IsolatedWorld --> ExecutionContext
    ExecutionContext --> CdpJSHandle
    CdpPage --> NetworkManager
    CdpPage --> EmulationManager
    CdpPage --> CdpKeyboard
    CdpPage --> CdpMouse
    CdpPage --> CdpTouchscreen
    CdpPage --> Coverage
    CdpPage --> Tracing
    CdpPage --> ScreenRecorder
```

## Core components

- [Browser context and target lifecycle](browser_context_and_target_lifecycle.md) — Browser ownership, context isolation, target discovery, auto-attachment, target classification, and shutdown.
- [Page and frame lifecycle](page_and_frame_lifecycle.md) — `CdpPage`, `CdpFrame`, frame trees, navigation, page events, dialogs, screenshots, PDFs, and workers.
- [Execution contexts and handles](execution_contexts_and_handles.md) — CDP realms, execution contexts, JavaScript evaluation, bindings, `JSHandle`, and `ElementHandle` lifetimes.
- [Network stack](network_stack.md) — Request/response correlation, redirects, interception, authentication, headers, caching, and network-condition emulation.
- [Input and emulation](input_and_emulation.md) — Keyboard, mouse, touchscreen, viewport, device metrics, geolocation, media, timezone, and other emulation controls.
- [Coverage, tracing, and recording](coverage_tracing_and_recording.md) — JavaScript/CSS coverage, performance tracing, screencast recording, and console diagnostics.

## Related infrastructure

The module integrates with:

- [Protocol-neutral public automation API](protocol_neutral_public_automation_api.md)
- [Protocol transport and session infrastructure](protocol_transport_and_session_infrastructure.md)
- [Shared automation runtime and query infrastructure](shared_automation_runtime_and_query_infrastructure.md)
- [Browser provisioning and launch orchestration](browser_provisioning_and_launch_orchestration.md)