# public_package_entry_points

## Purpose

The `public_package_entry_points` module defines the package-level surfaces consumers import from `svelte`. It combines:

- Runtime APIs for component lifecycle, mounting, hydration, context, scheduling, events, actions, and attachments.
- TypeScript contracts for components, snippets, props, events, HTML/SVG attributes, bindings, and editor tooling.
- Environment-specific client and server behavior.
- Compatibility declarations for legacy Svelte components and APIs.

The module is located at `packages/svelte` and consists of two primary child modules:

- `public_api` — runtime exports and component-facing TypeScript APIs.
- `html_typings` — markup typings and language-server integration.

## Architecture

```mermaid
flowchart TB
    Consumer["Application / component / editor tooling"]
    Package["packages/svelte"]

    Consumer --> Package
    Package --> API["public_api\npackages/svelte/src"]
    Package --> HTML["html_typings\npackages/svelte"]

    API --> Client["Client entry\nindex-client.js"]
    API --> Server["Server entry\nindex-server.js"]
    API --> Types["Component and runtime declarations\nindex.d.ts"]
    API --> Actions["Actions and attachments"]

    Client --> Reactivity["Client reactivity core"]
    Client --> Rendering["Client DOM rendering runtime"]
    Server --> SSR["Server rendering runtime"]

    HTML --> Elements["HTML/SVG element declarations\n elements.d.ts"]
    HTML --> Intrinsic["svelteHTML.IntrinsicElements\n svelte-html.d.ts"]
    Intrinsic --> Tooling["TypeScript / language-server tooling"]
```

### Runtime entry-point split

```mermaid
flowchart LR
    Component["Shared component code"] --> Select{"Execution environment"}

    Select -->|Browser| Client["index-client.js"]
    Select -->|SSR| Server["index-server.js"]

    Client --> Mount["mount / hydrate / unmount"]
    Client --> Lifecycle["effects and lifecycle"]
    Client --> DOM["DOM rendering and bindings"]

    Server --> SafeLifecycle["SSR-safe lifecycle"]
    Server --> Context["server component context"]
    Server --> HTML["HTML output"]

    Mount -. unavailable during SSR .-> Server
```

The public API is an adapter boundary over the compiler-generated component shape and internal runtimes. Client APIs delegate to reactivity and DOM-rendering systems, while server APIs provide SSR-safe alternatives and reject browser-only operations.

### Markup type-checking flow

```mermaid
flowchart TD
    Markup["Svelte markup"] --> Intrinsic["svelteHTML.IntrinsicElements"]
    Intrinsic --> Map["SvelteHTMLElements"]
    Map --> Specialized["HTML/SVG element attribute interfaces"]
    Specialized --> Shared["DOM, ARIA, event, and binding types"]
    Shared --> Diagnostics["Editor and TypeScript diagnostics"]

    Markup --> Dynamic{"Dynamic or custom element?"}
    Dynamic --> Fallback["Generic/custom-element fallback types"]
    Fallback --> Diagnostics
```

`elements.d.ts` provides the reusable public vocabulary, while `svelte-html.d.ts` bridges that vocabulary into global intrinsic-element declarations used by Svelte tooling.

## Core component references

- [public_api](public_api.md) — package runtime exports, client/server behavior, lifecycle, mounting, context, events, actions, attachments, and component types.
- [html_typings](html_typings.md) — HTML/SVG attributes, DOM events, ARIA metadata, bindings, intrinsic elements, and editor integration.
- [compilation_pipeline](compilation_pipeline.md) — produces the component structures consumed by the public runtime API.
- [client_reactivity_core](client_reactivity_core.md) — signals, effects, scheduling, teardown, and abortable reactive work.
- [client_dom_rendering_runtime](client_dom_rendering_runtime.md) — DOM blocks, elements, bindings, hydration, and rendering lifecycle.
- [server_rendering_and_shared_runtime_primitives](server_rendering_and_shared_runtime_primitives.md) — SSR context, payload generation, and server helpers.
- [published_type_declaration_surface](published_type_declaration_surface.md) — aggregated published TypeScript declarations.
- [legacy_compatibility_and_migration](legacy_compatibility_and_migration.md) — legacy components, lifecycle APIs, event dispatching, and migration support.