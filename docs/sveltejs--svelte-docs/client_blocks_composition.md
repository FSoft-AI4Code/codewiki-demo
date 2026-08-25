# client_blocks_composition

## Introduction

`client_blocks_composition` contains the client DOM runtime primitives that compose rendered
content from component-provided slots and reusable snippet functions. It is the composition layer
between compiler-generated component/block code and the lower-level DOM, hydration, and reactive
effect runtimes.

| Primitive | Responsibility |
| --- | --- |
| `slot` | Select a named slot supplied through component props, invoke it with slot props, or render a fallback. |
| `sanitize_slots` | Convert slot-bearing component props into the boolean slot-shape metadata used by component interop. |
| `snippet` | Reactively select and render a snippet function, replacing the previous snippet effect when the function changes. |
| `wrap_snippet` | Add development-time component ownership context and prevent accidental snippet stringification. |
| `createRawSnippet` | Adapt a user-supplied render/setup pair into a runtime snippet that can render and hydrate one element. |

This module is a child of the broader [client_blocks](client_blocks.md) runtime. Control-flow and
async behavior are documented in [client_blocks_control_flow](client_blocks_control_flow.md) and
[client_blocks_async_boundaries](client_blocks_async_boundaries.md); this document focuses on
content projection and reusable render functions.

## 1. Position in the system

```mermaid
flowchart LR
    SRC[".svelte source"] --> PARSE["parse / analyze"]
    PARSE --> TRANSFORM["client transform"]
    TRANSFORM --> GENERATED["generated component code"]

    subgraph COMPOSE["client_blocks_composition"]
        SLOT["slot.js\nslot() / sanitize_slots()"]
        SNIP["snippet.js\nsnippet() / wrap_snippet() / createRawSnippet()"]
    end

    GENERATED --> SLOT
    GENERATED --> SNIP
    SLOT --> HYDRATE["hydration markers"]
    SLOT --> EFFECTS["component-provided slot functions"]
    SNIP --> EFFECTS2["branch/block effects"]
    SNIP --> DOM["template, reconciler, DOM operations"]
    EFFECTS2 --> REACT["client_reactivity"]
    DOM --> RENDER["client render / hydration"]

    CT["compiler_transform_client_components_slots"] -. emits slot props .-> GENERATED
    ST["compiler_transform_client_blocks_snippets"] -. emits snippet calls .-> GENERATED
    SSR["compiler_transform_server_components / blocks"] -. analogous SSR paths .-> SERVER["server runtime"]
```

The compiler determines *where* slots and snippets are used; this module determines *how* they
are attached to the live DOM. The principal compiler links are:

- [compiler_transform_client_components_slots](compiler_transform_client_components_slots.md)
  for `<slot>` and component slot projection.
- [compiler_transform_client_blocks_snippets](compiler_transform_client_blocks_snippets.md)
  for `{#snippet}` declarations and `{@render ...}` call sites.
- [compiler_transform_client_blocks](compiler_transform_client_blocks.md) for the parent visitor
  group and its relationship to the client transform.
- [compiler_transform_server_components](compiler_transform_server_components.md) and
  [compiler_transform_server_blocks](compiler_transform_server_blocks.md) for server-side output.

## 2. Component relationships

```mermaid
classDiagram
    class ComponentProps {
        +Record $$slots
        +function children
        +function namedSlot
    }
    class SlotRuntime {
        +slot(anchor, props, name, slot_props, fallback_fn)
        +sanitize_slots(props)
    }
    class SnippetRuntime {
        +snippet(node, get_snippet, ...args)
        +wrap_snippet(component, fn)
        +createRawSnippet(fn)
    }
    class EffectRuntime {
        +block(fn, flags)
        +branch(fn)
        +destroy_effect(effect)
        +teardown(fn)
    }
    class HydrationRuntime {
        +hydrate_next()
        +hydrate_node
        +hydrating
    }
    class DOMRuntime {
        +create_fragment_from_html(html)
        +assign_nodes(node, last)
        +get_first_child(fragment)
        +get_next_sibling(node)
    }

    ComponentProps --> SlotRuntime : supplied to
    SlotRuntime --> HydrationRuntime : advances markers
    SlotRuntime --> ComponentProps : reads slot functions
    SnippetRuntime --> EffectRuntime : owns snippet effects
    SnippetRuntime --> HydrationRuntime : renders / hydrates
    SnippetRuntime --> DOMRuntime : raw snippet insertion
```

## 3. Slot projection

### `slot(anchor, $$props, name, slot_props, fallback_fn)`

`slot` renders one named slot at a comment anchor. Its behavior is intentionally small and
compiler-friendly:

1. If hydration is active, call `hydrate_next()` so the runtime consumes the existing SSR marker.
2. Read `$$props.$$slots?.[name]`.
3. Support snippet interop when the slot entry is the sentinel `true`; in that case, use
   `children` for the default slot or the named prop for a named slot.
4. If no slot function exists, invoke `fallback_fn(anchor)` when a fallback was compiled.
5. Otherwise invoke the slot function at the anchor with `slot_props`.

```mermaid
flowchart TD
    START["slot(anchor, props, name, slot_props, fallback)"] --> HYD{"hydrating?"}
    HYD -->|yes| ADV["hydrate_next()"]
    HYD -->|no| LOOKUP["read props.$$slots[name]"]
    ADV --> LOOKUP
    LOOKUP --> SENT{"entry === true?"}
    SENT -->|yes| INTEROP["use props.children or props[name]"]
    SENT -->|no| FOUND["use slot function"]
    INTEROP --> EXISTS{"slot exists?"}
    FOUND --> EXISTS
    EXISTS -->|no| FALLBACK{"fallback_fn exists?"}
    FALLBACK -->|yes| RENDER_F["fallback_fn(anchor)"]
    FALLBACK -->|no| END["no DOM output"]
    EXISTS -->|yes| RENDER_S["slot_fn(anchor, slot_props)"]
```

The slot function receives the anchor and the slot props object. In interop mode, the second
argument is a getter-like function returning `slot_props`, matching the calling convention used
by snippets. This lets component children and snippets participate in the same composition path.

### `sanitize_slots(props)`

`sanitize_slots` creates a shape-only object whose keys identify available slots:

- `props.children` marks the default slot as `default`.
- Every key in `props.$$slots` is copied with the value `true`.

The function does not render content, clone props, or validate slot bodies. It only creates stable
availability metadata for component plumbing. This separation keeps slot discovery independent of
DOM creation and allows the compiler/runtime component layer to pass slot shape information without
exposing arbitrary prop values.

```mermaid
flowchart LR
    P["component props"] --> C{"props.children?"}
    C -->|yes| D["sanitized.default = true"]
    C -->|no| KEYS["iterate props.$$slots"]
    D --> KEYS
    KEYS --> OUT["slot availability map"]
```

## 4. Reactive snippet composition

### `snippet(node, get_snippet, ...args)`

`snippet` renders a potentially changing snippet expression at `node`. It creates a transparent
block effect and tracks the currently selected snippet function:

1. The current snippet starts as `noop`.
2. The block reads `get_snippet()` on each reactive run.
3. If the function identity is unchanged, rendering is skipped.
4. If it changed, the old branch effect is destroyed.
5. In development, a null/undefined result reports an invalid-snippet diagnostic.
6. A new branch invokes the selected function with `anchor` and the supplied arguments.

```mermaid
sequenceDiagram
    participant Generated as generated render code
    participant S as snippet()
    participant B as block effect
    participant G as get_snippet()
    participant E as branch effect
    participant F as selected snippet

    Generated->>S: snippet(anchor, get_snippet, ...args)
    S->>B: create transparent block
    B->>G: read current function
    alt same function identity
        B-->>S: retain existing branch
    else changed function
        B->>E: destroy previous effect
        B->>E: create new branch
        E->>F: F(anchor, ...args)
    end
```

The identity check is significant: changing the snippet expression replaces the rendered branch,
while changes observed by the snippet's own reactive reads are handled by the nested effects it
creates. `EFFECT_TRANSPARENT` prevents this selector wrapper from introducing an unnecessary
reactive boundary in the visible update hierarchy.

If hydration is active, the function initially receives the normal node reference while the local
anchor is then redirected to `hydrate_node`. This allows the snippet runtime to align with existing
SSR DOM markers. Hydration details are shared with [client_render_and_templates](client_render_and_templates.md).

## 5. Development wrapping and raw snippets

### `wrap_snippet(component, fn)`

`wrap_snippet` is used by development builds around compiler-generated snippet functions. The
returned wrapper:

- saves the current component function context;
- sets the owning component while the snippet executes;
- restores the previous context in a `finally` block;
- marks the function so accidental stringification produces a useful diagnostic.

This is runtime validation and ownership bookkeeping; production rendering does not need the
additional wrapper. Related diagnostics and dev-only runtime services are described in
[client_dev_tooling](client_dev_tooling.md).

### `createRawSnippet(fn)`

`createRawSnippet` adapts a programmatic snippet factory. The factory receives getter parameters and
returns `{ render, setup? }`:

```mermaid
flowchart TD
    CALL["rawSnippet(anchor, ...getters)"] --> FACTORY["fn(...getters)"]
    FACTORY --> RESULT["{ render(), setup?() }"]
    RESULT --> HYD{"hydrating?"}
    HYD -->|yes| EXISTING["use hydrate_node; hydrate_next()"]
    HYD -->|no| HTML["render().trim()"]
    HTML --> FRAG["create_fragment_from_html(html)"]
    FRAG --> VALIDATE{"exactly one element?"}
    VALIDATE -->|no in dev| ERROR["invalid raw snippet diagnostic"]
    VALIDATE -->|yes| INSERT["anchor.before(element)"]
    EXISTING --> SETUP["setup(element)"]
    INSERT --> SETUP
    SETUP --> ASSIGN["assign_nodes(element, element)"]
    ASSIGN --> CLEANUP{"setup returned cleanup?"}
    CLEANUP -->|yes| TEARDOWN["teardown(cleanup)"]
    CLEANUP -->|no| DONE["complete"]
    TEARDOWN --> DONE
```

In non-hydrating mode, the rendered HTML is trimmed, parsed into a fragment, and the first child
is inserted before the anchor. Development mode rejects output that is not exactly one element;
this prevents ambiguous ownership and insertion behavior. During hydration, existing DOM is reused
instead of parsing or inserting new HTML.

The optional `setup` callback runs after the element is available. If it returns a function, that
function is registered with `teardown`, tying external resources to the element's effect lifetime.

## 6. End-to-end composition flows

### Component slot flow

```mermaid
sequenceDiagram
    participant Parent as parent component
    participant Child as child generated code
    participant Slot as slot()
    participant Content as parent slot function
    participant DOM as DOM / hydration runtime

    Parent->>Child: pass $$slots / children
    Child->>Slot: slot(anchor, props, name, slot_props, fallback)
    Slot->>DOM: advance hydration marker when needed
    alt slot supplied
        Slot->>Content: invoke at anchor with slot props
        Content->>DOM: create/update projected nodes
    else slot omitted
        Slot->>Child: invoke compiled fallback
    end
```

### Rendered snippet flow

```mermaid
flowchart LR
    R["{@render expression(args)}"] --> C["compiler emits anchor + snippet call"]
    C --> S["snippet() or direct snippet function"]
    S --> B["reactive selector block"]
    B --> BR["branch effect"]
    BR --> T["snippet template / raw element"]
    T --> HY["hydrate existing nodes or insert new nodes"]
    STATE["snippet identity changes"] --> B
    STATE2["reactive argument/body changes"] --> BR
```

## 7. Dependency boundaries and invariants

| Dependency | Role in this module |
| --- | --- |
| `internal/client/reactivity/effects.js` | Creates transparent blocks and snippet branches; destroys and tears down effects. |
| `internal/client/context.js` | Tracks development component ownership while wrapped snippets run. |
| `internal/client/dom/hydration.js` | Advances SSR markers and supplies the current hydration node. |
| `internal/client/dom/reconciler.js` | Parses raw snippet HTML into a fragment. |
| `internal/client/dom/template.js` | Associates raw snippet nodes with an effect/template range. |
| `internal/client/dom/operations.js` | Finds raw snippet element boundaries. |
| `internal/shared/validate.js` | Prevents unsafe snippet stringification. |
| `internal/client/warnings.js` and `errors.js` | Report invalid raw snippets and invalid dynamic snippets. |

Important invariants for maintainers:

- Slot fallback is rendered only when the requested slot is absent; an explicitly supplied slot
  owns the projection decision.
- A dynamic snippet branch must be destroyed before its replacement is created, preventing stale
  DOM and effects from surviving a snippet identity change.
- Hydration paths consume markers rather than inserting duplicate content.
- Raw snippets are single-element compositions in development mode; changing that contract affects
  insertion, node ownership, and cleanup semantics.
- Cleanup returned by raw snippet setup must be registered with the effect system so unmounting or
  branch replacement releases resources.

## 8. Maintenance guidance

When changing `slot.js`, verify default and named slots, missing-slot fallback, snippet interop,
and hydration. When changing `snippet.js`, verify snippet identity replacement, null handling in
development, component-context restoration after exceptions, raw snippet hydration, invalid
multi-node output, and setup cleanup.

The most relevant neighboring tests and implementation areas are the compiler visitors linked
above, [client_blocks](client_blocks.md), [client_reactivity](client_reactivity.md), and
[client_render_and_templates](client_render_and_templates.md). Keep this document focused on
composition semantics; changes to control flow, async boundaries, or element bindings belong in
their respective module documentation.
