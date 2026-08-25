# Shared Automation Runtime and Query Infrastructure

## Purpose

The `shared_automation_runtime_and_query_infrastructure` module provides reusable infrastructure beneath Puppeteer’s public automation APIs and protocol backends.

It combines:

- Selector parsing and execution for CSS, XPath, text, ARIA, piercing, P-query, and custom selectors.
- Asynchronous waiting with visibility checks, polling strategies, timeouts, cancellation, and execution-context recovery.
- Runtime primitives for events, task sequencing, deferred completion, timeout policies, lazy evaluation, lifecycle guards, and deterministic resource disposal.

Together, these components make browser automation operations consistent across CDP and WebDriver BiDi implementations.

## Architecture

```mermaid
flowchart TD
    API[Public Browser / Page / Frame APIs] --> Selector[Selector and Waiting Engine]
    API --> Runtime[Runtime Lifecycle and Scheduling]
    CDP[CDP Backend] --> Runtime
    BIDI[WebDriver BiDi Backend] --> Runtime
    Transport[Protocol Transport and Sessions] --> Runtime

    Selector --> Handlers[Query Handlers]
    Selector --> Injected[Injected Selector Engine]
    Selector --> Waiting[WaitTask and Pollers]

    Waiting --> Runtime
    Handlers --> Injected
    Injected --> DOM[DOM, Shadow DOM, and Accessibility Tree]

    Runtime --> Events[EventEmitter]
    Runtime --> Queue[TaskQueue]
    Runtime --> Timeout[Timeout and Cancellation]
    Runtime --> Deferred[Deferred and LazyArg]
    Runtime --> Lifecycle[Disposal and Lifecycle Guards]
```

The selector subsystem performs queries inside execution realms using injected Puppeteer utilities. The runtime subsystem supplies the scheduling, timeout, event, and cleanup primitives required by selector waits, protocol sessions, and backend lifecycle operations.

## Selector and Waiting Flow

```mermaid
sequenceDiagram
    participant Caller as Page / ElementHandle / Locator
    participant Handler as QueryHandler
    participant Realm as Execution Realm
    participant Engine as Injected Selector Engine
    participant Poller as RAF / Mutation / Interval Poller
    participant Runtime as Runtime Primitives

    Caller->>Handler: query or waitFor(selector)
    Handler->>Realm: evaluate query function
    Realm->>Engine: execute selector
    alt Immediate query
        Engine-->>Caller: ElementHandle(s)
    else Asynchronous wait
        Handler->>Poller: start polling
        Poller->>Engine: retry query
        Engine-->>Poller: match or no match
        Poller->>Runtime: apply timeout, cancellation, and cleanup
        Poller-->>Caller: resolved ElementHandle
    end
```

## Core Component Documentation

- [Selector and Waiting Engine](selector_and_waiting_engine.md) — Selector handlers, injected selector engines, custom handlers, wait tasks, polling, visibility checks, and execution-context recovery.
- [Runtime Lifecycle and Scheduling](runtime_lifecycle_and_scheduling.md) — Event delivery, task queues, timeout settings, deferred promises, lazy arguments, lifecycle guards, disposable stacks, and asynchronous collection utilities.

## Source Boundaries

The module is primarily implemented under `packages/puppeteer-core/src`, especially:

- `common/QueryHandler.ts`
- `common/CustomQueryHandler.ts`
- `common/ScriptInjector.ts`
- `common/WaitTask.ts`
- `injected/PQuerySelector.ts`
- `injected/Poller.ts`
- `injected/util.ts`
- Shared runtime utilities such as event, timeout, deferred, scheduling, and disposal helpers.