# client_blocks_dynamic_dom

## Introduction

`client_blocks_dynamic_dom` contains the Svelte client-runtime primitives that update DOM whose
shape, tag name, namespace, head placement, or inline style properties can change at runtime. It
is a child of the client DOM blocks runtime and is used by compiler-generated code for
`{@html}`, `<svelte:element>`, `<svelte:head>`, and `<svelte:style>`/dynamic CSS-property output.

| Primitive | Responsibility |
| --- | --- |
| `html` | Replace or hydrate a raw HTML region, including SVG and MathML fragments. |
| `element` | Create, replace, pause, resume, and hydrate an element whose tag is dynamic. |
| `head` | Render reactive content into `document.head` while coordinating SSR hydration markers. |
| `css_props` | Apply or remove a reactive map of CSS custom properties or inline style properties. |

The module is deliberately small: compiler visitors decide *when* these primitives are called,
while this runtime owns DOM placement and lifecycle. Control-flow blocks, snippets, and async
boundaries are documented separately in [client_blocks_control_flow](client_blocks_control_flow.md),
[client_blocks_composition](client_blocks_composition.md), and
[client_blocks_async_boundaries](client_blocks_async_boundaries.md).

## Position in the system

```mermaid
flowchart LR
    SOURCE[".svelte source"] --> PARSE["parse / analyze"]
    PARSE --> CLIENT["client transform"]
    CLIENT --> GENERATED["generated client component"]

    subgraph DYNAMIC["client_blocks_dynamic_dom"]
        HTML["html()"]
        ELEMENT["element()"]
        HEAD["head()"]
        CSS["css_props()"]
    end

    GENERATED --> HTML
    GENERATED --> ELEMENT
    GENERATED --> HEAD
    GENERATED --> CSS
    DYNAMIC --> EFFECTS["client reactivity / effects"]
    DYNAMIC --> HYDRATION["hydration cursor"]
    DYNAMIC --> DOM["DOM operations / reconciler"]
    DYNAMIC --> BROWSER["live DOM"]

    CT1["compiler_transform_client_blocks_tags"] -. emits raw HTML calls .-> GENERATED
    CT2["compiler_transform_client_elements_dynamic"] -. emits dynamic element calls .-> GENERATED
    CT3["compiler_transform_client_elements_special"] -. emits head/style calls .-> GENERATED
```

The compiler-side dynamic-element visitor is described in
[compiler_transform_client_elements_dynamic](compiler_transform_client_elements_dynamic.md).
The broader client block compiler relationship is described in
[compiler_transform_client_blocks](compiler_transform_client_blocks.md); the runtime’s reactive
primitives are described in [client_reactivity](client_reactivity.md).

## Architecture and dependencies

```mermaid
graph TD
    subgraph API["Dynamic DOM runtime"]
        H["html.js\nhtml"]
        E["svelte-element.js\nelement"]
        HD["svelte-head.js\nhead / reset_head_anchor"]
        CP["css-props.js\ncss_props"]
    end

    subgraph REACT["Reactive lifecycle"]
        TE["template_effect"]
        BL["block / branch"]
        LIFE["remove, pause, resume, destroy"]
        RE["render_effect / teardown"]
    end

    subgraph DOM["DOM and hydration"]
        CURSOR["hydrate_node / hydrate_next\nhydrating"]
        OPS["create element, text, sibling"]
        ASSIGN["assign_nodes"]
        FRAG["create_fragment_from_html"]
    end

    H --> TE & CURSOR & FRAG & ASSIGN
    E --> BL & LIFE & CURSOR & OPS & ASSIGN
    HD --> BL & CURSOR & OPS
    CP --> RE & CURSOR & OPS
    BL --> LIFE
```

### Shared contracts

- A compiler-generated anchor (`Comment`, `Text`, or `Element`) identifies where a dynamic region
  is inserted.
- `template_effect`, `block`, or `render_effect` reruns a getter when its reactive dependencies
  change.
- `hydrate_node`, `hydrate_next`, and `set_hydrate_node` maintain the current SSR DOM cursor.
- `assign_nodes(start, end)` records the DOM interval owned by an effect so it can later be
  removed as one region.
- Element creation and sibling traversal are delegated to the DOM operations layer; the module
  does not implement a separate virtual DOM.

## Component interaction

```mermaid
sequenceDiagram
    participant C as Generated component
    participant R as Dynamic DOM primitive
    participant X as Reactive effect
    participant H as Hydration cursor
    participant D as DOM

    C->>R: pass anchor and reactive getter
    R->>X: register effect/block
    X->>C: read current value/tag/styles
    alt value or tag changed
        R->>H: consume or reposition SSR cursor
        R->>D: remove, create, insert, or update nodes
    else unchanged
        R-->>D: retain existing region
    end
```

## `html`: raw HTML regions

`html(node, get_value, svg, mathml, skip_warning)` treats the value as an HTML fragment. It keeps
the previous string value and creates a `template_effect` that performs these operations:

1. Read the current value, coercing `null`/`undefined` to the empty string.
2. Do nothing when the resulting value is unchanged; during hydration it still advances the
   hydration cursor.
3. Remove the previous effect-owned DOM interval when the value changes.
4. Parse the new value with `create_fragment_from_html` and insert it immediately before the
   anchor. SVG and MathML values are wrapped in their namespace element before extraction.
5. During hydration, reuse the server nodes between the current hydration node and the empty
   closing marker. A missing closing marker raises `HYDRATION_ERROR` after reporting a mismatch.

The implementation intentionally uses an HTML fragment parser rather than the script-aware helper:
raw `{@html}` insertion must not execute `<script>` tags. In development, a server hash is compared
with the client value and `hydration_html_changed` is reported when content differs; the runtime
does not attempt an expensive mismatch repair.

```mermaid
flowchart TD
    START["html(anchor, get_value)"] --> READ["read and normalize value"]
    READ --> SAME{"same as previous?"}
    SAME -->|yes| KEEP["retain region\nadvance hydration if needed"]
    SAME -->|no| REMOVE["remove previous effect DOM"]
    REMOVE --> EMPTY{"value empty?"}
    EMPTY -->|yes| DONE["region remains empty"]
    EMPTY -->|no| HYD{"hydrating?"}
    HYD -->|yes| REUSE["scan SSR nodes to closing marker\nassign owned interval"]
    HYD -->|no| WRAP["wrap as SVG/MathML when requested"]
    WRAP --> PARSE["parse fragment"]
    PARSE --> INSERT["anchor.before(fragment)"]
    REUSE --> DONE
    INSERT --> DONE
```

## `element`: dynamic element names

`element(node, get_tag, is_svg, render_fn, get_namespace, location)` implements
`<svelte:element this={...}>`. The tag getter is read inside a reactive `block`. When the tag is
unchanged, the block exits without DOM work. When it changes:

- A `null` tag pauses the current effect, producing no element while preserving its lifecycle for
  a possible resumed render.
- Returning to the paused tag resumes that effect and can preserve outro behavior.
- Changing from one non-null tag to another destroys the old effect immediately and suppresses
  intro transitions for the replacement.
- The next tag is created with `document.createElement` or `createElementNS`; an explicit namespace
  getter takes precedence over the `is_svg` flag and automatic `svg` detection.
- `render_fn` receives the new element and a child anchor, allowing generated children, actions,
  bindings, and nested blocks to initialize inside it.

The runtime records the current keyed-each item so an `animate:` directive created inside the
dynamic element can associate itself with the correct row. In development it also attaches source
location metadata. Hydration reuses the existing element when the cursor points at an element and
temporarily disables hydration for a raw-text element with no usable child anchor.

```mermaid
stateDiagram-v2
    [*] --> ReadTag
    ReadTag --> Same: tag unchanged
    Same --> ReadTag: reactive update
    ReadTag --> Create: new non-null tag
    ReadTag --> Pause: tag is null
    Pause --> Create: non-null tag
    Create --> RenderChildren
    RenderChildren --> Active
    Active --> Pause: tag becomes null
    Active --> Replace: tag changes
    Replace --> Create: destroy old, suppress intro
    Active --> Same: tag unchanged
```

## `head`: reactive document head content

`head(render_fn)` creates a `HEAD_EFFECT` block around a renderer that receives a head anchor. In
non-hydrating mode the anchor is a text node appended to `document.head`. The renderer can then
create title, meta, link, style, or other compiler-generated head content relative to that marker.

During hydration, the function searches `document.head` for the next `HYDRATION_START` comment,
sets the cursor to the following node, and lets the nested renderer consume its SSR output. Multiple
head blocks share `head_anchor` so each block starts after the previous block’s marker range. If no
opening marker exists—for example, when a host framework rendered the body but omitted head
content—hydration is disabled for this block and normal client rendering proceeds.

The previous hydration cursor and hydration mode are restored in `finally`, even if the renderer
throws. `reset_head_anchor` clears the shared cursor for a new hydration/rendering session.

```mermaid
flowchart TD
    START["head(render_fn)"] --> HYD{"hydrating?"}
    HYD -->|no| APPEND["append text anchor to document.head"]
    HYD -->|yes| SEARCH["find next HYDRATION_START marker"]
    SEARCH --> FOUND{"marker found?"}
    FOUND -->|no| DISABLE["disable hydration for this block"]
    FOUND -->|yes| CURSOR["set cursor after marker"]
    APPEND --> BLOCK["run render_fn in HEAD_EFFECT block"]
    DISABLE --> BLOCK
    CURSOR --> BLOCK
    BLOCK --> RESTORE["restore prior hydration cursor/mode"]
```

## `css_props`: reactive inline style maps

`css_props(element, get_styles)` associates a style getter with a `render_effect`. The getter
returns a `Record<string, string>`; each key is applied using `style.setProperty`. Falsy values
remove that property with `style.removeProperty`, which makes the map suitable for both CSS custom
properties and ordinary hyphenated inline properties.

When hydrating, the first child of the element becomes the next hydration node before the effect is
registered. This preserves the cursor contract for nested generated content while style updates are
applied independently of child DOM creation. The primitive does not diff or remove keys absent from
the newest map; callers must return a falsy value for a property that should be removed.

```mermaid
flowchart LR
    GET["get_styles()"] --> ITER["iterate property map"]
    ITER --> VALUE{"value truthy?"}
    VALUE -->|yes| SET["element.style.setProperty"]
    VALUE -->|no| REMOVE["element.style.removeProperty"]
    SET --> NEXT["next property"]
    REMOVE --> NEXT
    NEXT --> ITER
```

## End-to-end process flows

### Client update

```mermaid
sequenceDiagram
    participant S as Reactive source
    participant E as Effect/block
    participant P as Dynamic DOM primitive
    participant D as DOM region

    S->>E: dependency invalidated
    E->>P: rerun getter
    alt raw HTML changed
        P->>D: remove owned interval
        P->>D: parse and insert fragment
    else dynamic tag changed
        P->>D: pause/destroy old element
        P->>D: create element and render children
    else styles changed
        P->>D: set or remove style properties
    else head renderer changed
        P->>D: update head effect-owned content
    end
```

### SSR hydration

```mermaid
flowchart TD
    SSR["SSR HTML + hydration markers"] --> CURSOR["hydration cursor"]
    CURSOR --> RAW["html: scan fragment range"]
    CURSOR --> DYN["element: reuse matching element"]
    CURSOR --> HEAD["head: find head marker"]
    CURSOR --> STYLE["css_props: seed first child cursor"]
    RAW --> CHECK["optional dev hash check"]
    DYN --> CHILDREN["render nested children against child cursor"]
    HEAD --> MULTI["advance shared head anchor"]
    STYLE --> EFFECT["apply reactive styles"]
    CHECK --> LIVE["live reactive runtime"]
    CHILDREN --> LIVE
    MULTI --> LIVE
    EFFECT --> LIVE
```

## Failure modes and maintenance notes

- Raw HTML hydration requires a closing empty comment marker. Missing markers are treated as a
  hydration failure rather than silently attaching an incomplete range.
- A server/client raw HTML difference is diagnosed in development, but the runtime intentionally
  avoids repairing the server DOM during the hydration pass.
- Dynamic element children are rendered even for a void element so actions and related setup code
  can run; invalid children are discarded by the browser/runtime behavior and warned elsewhere.
- Dynamic tag changes destroy the old subtree, whereas a temporary `null` tag pauses it. Changes to
  this distinction affect transitions and resource cleanup.
- `head_anchor` is module state. New render or hydration entry points must call
  `reset_head_anchor` when a previous head cursor must not be reused.
- `css_props` only processes keys returned by the latest map. To clear a property, return an empty
  or falsy value for that key.

## Related modules

- [client_blocks_control_flow](client_blocks_control_flow.md) — lifecycle and DOM reconciliation
  for conditional, keyed, awaited, and repeated blocks.
- [client_blocks_composition](client_blocks_composition.md) — slots and snippets that can render
  inside dynamic elements and head regions.
- [client_blocks_async_boundaries](client_blocks_async_boundaries.md) — async effects and
  boundaries that may contain these primitives.
- [client_reactivity](client_reactivity.md) — source tracking, effects, batching, and store
  interoperability used by the getters and lifecycle wrappers.
- [compiler_transform_client_elements_dynamic](compiler_transform_client_elements_dynamic.md) —
  compiler generation for dynamic element calls.
- [compiler_transform_client_blocks_tags](compiler_transform_client_blocks_tags.md) — compiler
  handling of raw HTML and related leaf tags.
