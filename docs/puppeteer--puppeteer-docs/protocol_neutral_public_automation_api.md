# Protocol-Neutral Public Automation API

## Purpose

The `protocol_neutral_public_automation_api` module, located at `packages/puppeteer-core/src/api`, defines Puppeteer’s public automation contracts independently of the underlying browser protocol.

It provides abstractions for:

- Browser and isolated browser-context ownership
- Pages, frames, navigation, querying, and lifecycle events
- JavaScript realms, remote handles, and retryable locators
- Network requests, responses, and interception
- Keyboard, mouse, touchscreen, and JavaScript-dialog interaction
- Browser targets and Web Workers

Concrete implementations are supplied by the Chrome DevTools Protocol (CDP) backend and WebDriver BiDi adapters.

## Architecture

### Public API and protocol implementations

```mermaid
flowchart TD
    Application[Automation application] --> PublicAPI[Protocol-neutral public API]

    PublicAPI --> Browser[Browser and BrowserContext]
    PublicAPI --> Page[Page and Frame]
    PublicAPI --> Handles[Realms, handles, and locators]
    PublicAPI --> Network[Network API]
    PublicAPI --> Input[Input and Dialog API]
    PublicAPI --> Targets[Targets and Web Workers]

    PublicAPI --> Backend{Protocol implementation}
    Backend --> CDP[CDP backend]
    Backend --> BiDi[WebDriver BiDi adapters]

    CDP --> CDPSession[CDP sessions and transport]
    BiDi --> BiDiSession[WebDriver BiDi sessions and transport]
```

The API layer owns shared contracts, lifecycle semantics, convenience methods, event models, validation, timeout behavior, and cross-component orchestration. Protocol-specific command execution and browser event translation remain below this layer.

### Object ownership and automation flow

```mermaid
flowchart TD
    Browser[Browser] --> Context[BrowserContext]
    Context --> Page[Page]
    Page --> Frame[Main and child Frames]
    Frame --> Realm[Main or isolated Realm]
    Realm --> Handle[JSHandle / ElementHandle]
    Handle --> Locator[Locator actions]

    Page --> Network[HTTPRequest / HTTPResponse]
    Page --> Input[Mouse / Keyboard / Touchscreen]
    Page --> Dialog[Dialog]
    Page --> Target[Target / WebWorker]

    Realm --> Protocol[CDP or WebDriver BiDi protocol]
    Network --> Protocol
    Input --> Protocol
    Dialog --> Protocol
    Target --> Protocol
```

Browser contexts isolate profile state such as cookies and storage. Pages contain frame trees and workers; frames execute code through realms; handles and locators provide DOM-level interaction. Network, input, dialog, target, and worker objects expose related browser events through stable public abstractions.

### Typical interaction sequence

```mermaid
sequenceDiagram
    participant App as Application
    participant Page as Page
    participant Frame as Frame
    participant Locator as Locator
    participant Realm as Execution realm
    participant Backend as CDP/BiDi backend

    App->>Page: navigate or select page
    Page->>Frame: delegate main-frame operation
    App->>Locator: locator(selector).click()
    Locator->>Frame: resolve element
    Frame->>Realm: query and check readiness
    Realm->>Backend: execute protocol command
    Backend-->>Realm: element / evaluation result
    Locator->>Backend: dispatch input
    Backend-->>App: action completion and page events
```

## Core component documentation

- [Browser and context API](browser_and_context_api.md) — browser sessions, isolated contexts, pages, cookies, permissions, targets, and disposal.
- [Page and frame API](page_and_frame_api.md) — navigation, frame hierarchies, DOM querying, evaluation, waiting, emulation, screenshots, and page events.
- [Handles, realms, and locators API](handles_realms_and_locators_api.md) — remote values, DOM handles, execution realms, selector resolution, waits, and retryable actions.
- [Network API](network_api.md) — request/response objects, interception, redirects, response bodies, and network lifecycle.
- [Input and Dialog API](input_and_dialog_api.md) — keyboard, mouse, touchscreen, touch handles, and JavaScript dialogs.
- [Targets and workers API](targets_and_workers_api.md) — target discovery, page/worker capability conversion, worker evaluation, and target ownership.

These components depend on shared runtime and selector infrastructure for event emitters, timeouts, waits, mutexes, query handlers, and disposal. Their concrete behavior is implemented by the CDP backend and WebDriver BiDi adapters, using the protocol transport and session infrastructure.