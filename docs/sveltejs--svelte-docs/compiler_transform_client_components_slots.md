# compiler_transform_client_components_slots

## Introduction

This module is the **slot-consumer side** of Svelte's client-side code generator. It holds two small visitors that run during phase 3 (transform) of the compiler:

| Visitor | Handles | Turns it into |
| --- | --- | --- |
| `SlotElement` | `<slot name="x" {a}>fallback</slot>` | a `$.slot(...)` runtime call |
| `SvelteFragment` | `<svelte:fragment slot="x" let:y>` | inlined statements + `let:` bindings |

The word "slots" here means the **legacy slot API** (Svelte 3/4 style), which Svelte 5 still supports for backwards compatibility. Snippets (`{#snippet}` / `{@render}`) are the modern replacement and live in [compiler_transform_client_blocks_snippets](compiler_transform_client_blocks_snippets.md).

The two halves of the slot system are split across modules:

- **Producer** — a parent writes `<Child><p slot="header">…</p></Child>`. The parent's children are packed into a `$$slots` object by `build_component`. See [compiler_transform_client_components_builder](compiler_transform_client_components_builder.md).
- **Consumer** — the child writes `<slot name="header" />`. That is **this module**. It emits the call that looks the slot function up and runs it.

---

## Where this module sits

```mermaid
graph TD
    subgraph parse["compiler_parse"]
        P["parse to AST<br/>SlotElement / SvelteFragment nodes"]
    end

    subgraph analyze["compiler_analyze"]
        A1["SvelteFragment visitor<br/>placement + attribute checks"]
        A2["scope.js<br/>creates child scope for let: bindings"]
    end

    subgraph transform["compiler_transform_client"]
        subgraph components["compiler_transform_client_components"]
            B["shared/component.js<br/>build_component<br/>(PRODUCER)"]
            E["Component / SvelteComponent / SvelteSelf"]
            subgraph slots["compiler_transform_client_components_slots<br/>(CONSUMER - this module)"]
                S1["SlotElement.js"]
                S2["SvelteFragment.js"]
            end
        end
        D["LetDirective visitor"]
        T["Fragment / Template builder"]
        U["Memoizer, build_attribute_value"]
    end

    subgraph runtime["client_blocks (runtime)"]
        R["slot() helper<br/>sanitize_slots() helper"]
    end

    P --> A1 --> transform
    A2 --> transform
    S1 --> D
    S2 --> D
    S1 --> U
    S1 --> T
    S2 --> T
    B -. "builds the slots record<br/>that slot() reads" .-> R
    S1 -- "emits call to" --> R
```

> In the diagram above (and in the sequence diagram that follows) the `$.` and `$$` prefixes are dropped for readability. The real generated names are `$.slot`, `$.sanitize_slots`, `$$props`, `$$slots`, `$$anchor` and `$$slotProps`.

Related docs: [compiler_transform_client](compiler_transform_client.md) · [compiler_transform_client_components_entries](compiler_transform_client_components_entries.md) · [compiler_transform_client_directives](compiler_transform_client_directives.md) · [compiler_transform_client_core_expressions](compiler_transform_client_core_expressions.md) · [compiler_transform_client_elements_attributes](compiler_transform_client_elements_attributes.md) · [compiler_transform_client_template](compiler_transform_client_template.md) · [client_blocks](client_blocks.md) · [compiler_ast_types](compiler_ast_types.md)

---

## The mental model in one picture

A parent packs children into `$$slots`; a child unpacks them with `$.slot`.

```mermaid
sequenceDiagram
    participant Parent as Parent.svelte<br/>(build_component)
    participant Props as props object
    participant Slot as slot() runtime
    participant Child as Child.svelte<br/>(SlotElement - this module)

    Parent->>Props: slots record gets an entry:<br/>header maps to fn(anchor, slotProps)
    Note over Parent,Props: default slot may instead become<br/>the children prop (snippet interop)
    Child->>Slot: slot(anchor, props, "header", slotProps, fallback)
    Slot->>Props: look up slots record entry "header"
    alt slot function found
        Slot->>Parent: slot_fn(anchor, slotProps)
        Note over Parent: parent markup renders here,<br/>let: bindings read slotProps
    else nothing passed
        Slot->>Child: fallback(anchor)
    end
```

---

## Component 1 — `SlotElement`

**File:** `packages/svelte/src/compiler/phases/3-transform/client/visitors/SlotElement.js`

### What it produces

```js
// <slot name="x" {a}>fallback</slot>
$.slot($$anchor, $$props, 'x', { get a() { return a; } }, ($$anchor) => { /* fallback */ });
```

The generated call always has five arguments:

| Argument | Source | Notes |
| --- | --- | --- |
| anchor node | `context.state.node` | the comment placeholder pushed into the template |
| `$$props` | literal identifier | the runtime reads `$$props.$$slots` and snippet-interop props from it |
| name | the `name` attribute, else `b.literal('default')` | must be a static literal |
| slot props | object of the remaining attributes, optionally wrapped in `$.spread_props` | passed *up* to the parent's slot function |
| fallback | arrow function, or `b.null` | only built when the slot has children |

### Attribute handling

The visitor walks `node.attributes` once and sorts every attribute into one of four buckets:

```mermaid
flowchart TD
    A[for each attribute] --> B{type?}
    B -->|SpreadAttribute| C["thunk(visit(attr))<br/>into spreads[]"]
    B -->|LetDirective| D["visit(attr)<br/>into lets[]"]
    B -->|Attribute| E{name?}
    E -->|"name"| F["name = literal value"]
    E -->|"slot"| G["ignored<br/>(consumed by the parent)"]
    E -->|anything else| H{has_state?}
    H -->|yes| I["b.get(name, return value)<br/>into props[]"]
    H -->|no| J["b.init(name, value)<br/>into props[]"]

    C --> K["spreads.length === 0<br/>? b.object(props)<br/>: $.spread_props(obj, ...spreads)"]
    I --> K
    J --> K
```

Two details are worth calling out:

- **`slot` is skipped.** A `slot="x"` attribute on a `<slot>` element describes where *this* `<slot>` goes inside its own parent component; it is not a prop to hand downward. The parent already read it via `determine_slot`, so passing it on would leak an internal name.
- **Stateful props become getters.** `build_attribute_value` reports `has_state`. When true, the property is emitted as `get a() { return … }` so the parent re-reads a fresh value on every access instead of capturing a stale snapshot. This is the same lazy-prop convention `build_component` uses for component props.

`build_attribute_value` comes from [compiler_transform_client_elements_attributes](compiler_transform_client_elements_attributes.md); the `b.*` builders come from [compiler_core](compiler_core.md).

### Memoization and async values

`SlotElement` creates its **own local `Memoizer`** (see [compiler_transform_client_core_expressions](compiler_transform_client_core_expressions.md)) rather than reusing the fragment-level one. The callback it passes to `build_attribute_value` says: *if this expression contains a call or an `await`, hoist it into a memo slot and read it back through `$.get`.*

```js
(value, metadata) =>
    metadata.has_call || metadata.has_await
        ? b.call('$.get', memoizer.add(value, metadata.has_await))
        : value
```

Why a local memoizer? Because the emitted statements may need to be wrapped in `$.async(...)`, and an async wrapper can only wrap the statements that belong to *this* slot.

`memoizer.apply()` assigns the placeholder ids their real names (`$0`, `$1`, …), then the two kinds of memo diverge:

```mermaid
flowchart TD
    M["memoizer.apply()"] --> S["deriveds(runes)<br/>let $0 = $.derived(() => expr)"]
    M --> A{"async_values()<br/>any awaits?"}
    S --> ST["statements[]"]
    ST --> C["$.slot(...) call<br/>appended to statements"]
    C --> A
    A -->|no| P1["state.init.push(<br/>single stmt or b.block(statements))"]
    A -->|yes| P2["state.init.push(<br/>$.async(node, values,<br/>(node, $0, $1) => block))"]
```

- **Sync memos** become `$.derived(...)` — or `$.derived_safe_equal(...)` in legacy, non-runes mode. The flag is `context.state.analysis.runes`.
- **Async memos** become the value array handed to `$.async`, and their ids become parameters of the callback. The whole slot render is therefore deferred until every awaited value settles.

When there is nothing async and only one statement, that statement is pushed bare instead of inside a block — a small output-size win that avoids a pointless `{ … }`.

### Ordering rules encoded in this visitor

The order of pushes is deliberate and easy to break:

1. `context.state.template.push_comment()` **first** — the anchor comment must exist in the template at the position the slot occupies, before any statement references `context.state.node`.
2. `lets` go into `state.init` **before** the derived/slot statements, because a `let:` binding can be read by an attribute expression on the same `<slot>`.
3. `memoizer.apply()` runs after all attributes have been visited, so ids are numbered in a stable order.

### Fallback content

```js
node.fragment.nodes.length === 0
    ? b.null
    : b.arrow([b.id('$$anchor')], context.visit(node.fragment))
```

The fallback is a normal fragment visit — see [compiler_transform_client_template](compiler_transform_client_template.md). Passing `b.null` (not an empty function) lets the runtime cheaply test `fallback_fn !== null`.

---

## Component 2 — `SvelteFragment`

**File:** `packages/svelte/src/compiler/phases/3-transform/client/visitors/SvelteFragment.js`

`<svelte:fragment>` is a **transparent wrapper**. It exists so an author can attach `slot="x"` and `let:` directives to a group of nodes without introducing a real DOM element.

```js
export function SvelteFragment(node, context) {
    for (const attribute of node.attributes) {
        if (attribute.type === 'LetDirective') {
            context.state.init.push(context.visit(attribute));
        }
    }
    context.state.init.push(...context.visit(node.fragment).body);
}
```

Two steps only:

1. Visit each `LetDirective` and push the resulting `const x = $.derived(() => $$slotProps.x)` declaration.
2. Visit the child fragment and **splice its statements inline** (`...block.body`) instead of nesting a block. Because the `let:` declarations were pushed first, the children can read them.

Notice what is *absent*: no template comment, no wrapper node, no handling of the `slot` attribute. That attribute is read by the **parent** during `build_component`, which groups children by `determine_slot(child)` and creates a separate slot function per name. By the time this visitor runs, the grouping already happened.

```mermaid
flowchart LR
    subgraph parent["Parent - build_component"]
        A["svelte:fragment slot='x' let:y"] --> B["determine_slot returns 'x'"]
        B --> C["children['x'] = [...]"]
        C --> D["slot_fn = ($$anchor, $$slotProps) => {...}"]
        D --> E["$$slots = { x: slot_fn }"]
    end
    subgraph here["This module - SvelteFragment"]
        F["let: becomes const y = $.derived(() => $$slotProps.y)"]
        G["children statements spliced inline"]
    end
    C --> here
```

### Scope note

`scope.js` registers `SvelteFragment` (and `SlotElement`) as scope-creating nodes, so `let:` bindings declared on them are visible to descendants and nowhere else. See [compiler_core](compiler_core.md).

### Validation happens earlier

Phase 2 already rejected bad usage before this visitor ever runs: `<svelte:fragment>` must be a direct child of a component, and it may only carry `slot` attributes and `let:` directives. See [compiler_analyze_special_elements](compiler_analyze_special_elements.md).

---

## `let:` bindings — how the two sides meet

`let:` is transformed by the `LetDirective` visitor in [compiler_transform_client_directives](compiler_transform_client_directives.md), but it only makes sense together with slots, so the contract is summarised here.

| Author writes | Generated |
| --- | --- |
| `let:x` | `const x = $.derived(() => $$slotProps.x)` |
| `let:x={y}` | `const y = $.derived(() => $$slotProps.x)` |
| `let:x={{ y, z }}` | one derived that destructures `$$slotProps.x` and returns `{ y, z }`; each binding reads through `$.get(name).y` |

The identifier `$$slotProps` is the **second parameter of the slot function** created by `build_component`:

```js
($$anchor, $$slotProps) => { /* let: deriveds, then children */ }
```

So the data path is: child's `<slot {a}>` → `$.slot` slot-props object → parent's `$$slotProps` → parent's `let:a` derived → parent's markup.

```mermaid
graph LR
    A["Child: slot with {a}"] -->|"{ get a() {...} }"| B["$.slot()"]
    B -->|"slot_props"| C["Parent slot_fn($$anchor, $$slotProps)"]
    C -->|"$$slotProps.a"| D["const a = $.derived(...)"]
    D --> E["Parent markup reads $.get(a)"]
```

---

## Runtime counterpart

**File:** `packages/svelte/src/internal/client/dom/blocks/slot.js` — documented in [client_blocks](client_blocks.md).

```mermaid
flowchart TD
    A["$.slot(anchor, $$props, name, slot_props, fallback_fn)"] --> B{hydrating?}
    B -->|yes| C[hydrate_next]
    B -->|no| D
    C --> D["slot_fn = $$props.$$slots?.[name]"]
    D --> E{"slot_fn === true?"}
    E -->|yes| F["INTEROP: slot_fn = $$props[name === 'default' ? 'children' : name]<br/>is_interop = true"]
    E -->|no| G
    F --> G{"slot_fn === undefined?"}
    G -->|yes| H{"fallback_fn !== null?"}
    H -->|yes| I["fallback_fn(anchor)"]
    H -->|no| J["render nothing"]
    G -->|no| K["slot_fn(anchor, is_interop ? () => slot_props : slot_props)"]
```

The **interop branch** is the bridge between the old and new APIs. When a parent passes a *snippet*, `build_component` records `$$slots: { default: true }` alongside the real `children` prop. The sentinel `true` tells the runtime "the content is a snippet, look in `$$props`", and snippets expect their props as a **thunk**, hence `() => slot_props`.

`$.sanitize_slots(props)` builds the `$$slots` boolean map a component sees when it references `$$slots` itself; it is injected once per component by `transform-client.js` as `const $$slots = $.sanitize_slots($$props)`.

---

## End-to-end example

**Child.svelte**

```svelte
<slot name="row" item={data[i]} count={items.length}>
  <em>nothing here</em>
</slot>
```

**Generated (shape, simplified)**

```js
var comment = $.comment();          // from template.push_comment()
var node = $.first_child(comment);

let $0 = $.derived(() => items.length);   // memoized: contains a call

$.slot(
  node,
  $$props,
  'row',
  {
    get item() { return data[i]; },       // has_state -> getter
    get count() { return $.get($0); }
  },
  ($$anchor) => { /* <em>nothing here</em> */ }
);
```

**Parent.svelte**

```svelte
<Child>
  <svelte:fragment slot="row" let:item let:count>
    {item} of {count}
  </svelte:fragment>
</Child>
```

**Generated (shape, simplified)**

```js
Child(node, {
  $$slots: {
    row: ($$anchor, $$slotProps) => {
      const item  = $.derived(() => $$slotProps.item);
      const count = $.derived(() => $$slotProps.count);
      /* text nodes reading $.get(item), $.get(count) */
    }
  }
});
```

---

## Comparison with the server transform

The server has its own `SlotElement` and `SvelteFragment` visitors (see [compiler_transform_server](compiler_transform_server.md)). They share the same *shape* but differ in every reactivity-related detail:

| Aspect | Client (this module) | Server |
| --- | --- | --- |
| Anchor | `template.push_comment()` + `state.node` | `empty_comment` before and after |
| Stateful props | `get a() { … }` getters | plain `b.init` values |
| Memoization / async | `Memoizer`, `$.derived`, `$.async` | none — rendering is one synchronous pass |
| Spread | `$.spread_props(obj, ...spreads)` | `$.spread_props([obj, ...spreads])` |
| Fallback | `($$anchor) => { … }` | `() => { … }` thunk |
| `let:` on `<slot>` | visited and pushed to `init` | not handled here |
| `SvelteFragment` | pushes `let:` deriveds, then inlines statements | just visits the fragment |
| Output target | `$.slot($$anchor, …)` into `state.init` | `$.slot($$payload, …)` into `state.template` |

---

## Design rationale

- **Two tiny files, one concept.** Both visitors exist only to bridge legacy slot syntax onto the snippet-shaped runtime. Keeping them separate from `build_component` keeps the producer/consumer split clean.
- **A local `Memoizer`, not the shared one.** Async slot props need their own `$.async` wrapper scoped to just this slot's statements; borrowing the fragment-level memoizer would pull unrelated expressions into that wrapper.
- **Getters instead of eager values.** Slot props cross a component boundary. A getter keeps the read lazy so the parent's effects track the right dependencies.
- **`b.null` fallback sentinel.** Cheaper at runtime than always allocating an empty function, and lets `$.slot` skip a call entirely.
- **`<svelte:fragment>` emits no node.** Inlining `block.body` keeps the DOM free of wrapper elements, which is the whole point of the tag.

## Common pitfalls when modifying

| Pitfall | Consequence |
| --- | --- |
| Pushing `lets` after the slot statements | attributes on the same `<slot>` reference undeclared bindings |
| Forgetting `push_comment()` before using `state.node` | anchor mismatch, hydration breaks |
| Forwarding the `slot` attribute as a slot prop | leaks an internal name into user-visible props |
| Calling `memoizer.apply()` before all attributes are visited | memo ids get renumbered incorrectly |
| Dropping the `runes` flag on `deriveds()` | legacy components lose `derived_safe_equal` semantics and over-fire |
