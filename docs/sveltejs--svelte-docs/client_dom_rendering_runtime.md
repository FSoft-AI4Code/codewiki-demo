# `client_dom_rendering_runtime`

## Purpose

The `client_dom_rendering_runtime` module is Svelte’s browser-side runtime for rendering and updating compiled components. It coordinates:

- DOM creation, cloning, insertion, removal, and SSR hydration
- Reactive control-flow blocks and component composition
- Element attributes, events, transitions, and custom elements
- Two-way bindings between component state and browser APIs
- Development diagnostics, source metadata, HMR, and ownership checks

It is located at `packages/svelte/src/internal/client` and bridges compiler-generated client code with the browser DOM and `client_reactivity_core`.

## Architecture

```mermaid
flowchart TD
    Compiler["Client compiler output"] --> Render["client_render_and_templates"]
    Compiler --> Blocks["client_blocks"]
    Compiler --> Elements["client_dom_elements"]
    Compiler --> Bindings["client_bindings"]

    Reactivity["client_reactivity_core"] --> Render
    Reactivity --> Blocks
    Reactivity --> Elements
    Reactivity --> Bindings

    Render --> Blocks
    Render --> Elements
    Blocks --> Elements
    Elements --> Bindings

    Render --> DOM["Browser DOM"]
    Elements --> DOM
    Bindings --> DOM

    Dev["client_dev_tooling"] -. instrumentation .-> Render
    Dev -. diagnostics and HMR .-> Blocks
    Dev -. metadata and validation .-> Elements
```

### Rendering and update lifecycle

```mermaid
sequenceDiagram
    participant C as Compiled component
    participant R as Rendering runtime
    participant X as Reactive effects
    participant B as Blocks/elements/bindings
    participant D as Browser DOM

    C->>R: mount or hydrate component
    R->>D: create, clone, or locate nodes
    R->>X: establish component and render effects
    X->>B: evaluate reactive instructions
    B->>D: update DOM, events, properties, and ranges
    D-->>B: user input or browser events
    B->>X: update component state
    X->>B: reconcile affected DOM
    C->>R: unmount
    R->>X: teardown effects and transitions
    X->>D: remove owned nodes and listeners
```

Hydration reuses SSR-generated nodes through a shared cursor and marker system. If the DOM shape does not match, the runtime can recover by clearing the affected range and performing a client render.

## Core components

| Component | Responsibility | Documentation |
| --- | --- | --- |
| `client_blocks` | Control flow, async boundaries, snippets, dynamic elements, and DOM-range reconciliation | [client_blocks.md](client_blocks.md) |
| `client_dom_elements` | Attributes, events, transitions, utilities, and custom elements | [client_dom_elements.md](client_dom_elements.md) |
| `client_bindings` | DOM-to-state and state-to-DOM synchronization for forms, media, viewport, and components | [client_bindings.md](client_bindings.md) |
| `client_render_and_templates` | Mounting, hydration, template factories, DOM operations, context, CSS, and lifecycle management | [client_render_and_templates.md](client_render_and_templates.md) |
| `client_dev_tooling` | Inspection, source locations, ownership validation, HMR, CSS cleanup, and development diagnostics | [client_dev_tooling.md](client_dev_tooling.md) |

The runtime depends heavily on [client_reactivity_core](client_reactivity_core.md) for signals, derived values, effects, batching, and teardown. It also integrates with the compiler’s client transformation pipeline and the server runtime’s SSR markup and hydration markers.