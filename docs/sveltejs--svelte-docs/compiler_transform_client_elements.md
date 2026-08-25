# compiler_transform_client_elements

## What this module does

This module is the part of the Svelte compiler that turns **elements** in a
`.svelte` file into browser JavaScript.

An "element" here means anything in the template that is a tag rather than a
component or a block:

| Template code | Handled by |
| --- | --- |
| `<div class="a" onclick={fn}>` | `RegularElement` |
| `<svelte:element this={tag}>` | `SvelteElement` |
| `<input {...props}>` | `SpreadAttribute` + shared attribute code |
| `<svelte:window>` `<svelte:body>` `<svelte:document>` | `visit_special_element` |
| `<svelte:head>` `<title>` | `SvelteHead`, `TitleElement` |

The module runs in **phase 3 (transform), client target**. It receives an AST
node that phase 1 parsed and phase 2 analyzed, and it writes two things:

1. **Static HTML** — pushed into a shared `Template` object. This becomes one
   big HTML string that the browser clones at runtime. Cheap.
2. **JavaScript statements** — pushed into `state.init`, `state.update`, and
   `state.after_update`. These call runtime helpers such as `$.set_attribute`,
   `$.set_class`, and `$.attribute_effect`. Needed only for the parts that can
   change.

The whole design is about **moving as much as possible into group 1**. A
`class="box"` that never changes costs nothing at runtime — it just lives in the
cloned HTML. A `class={expr}` needs a real effect.

## Where it sits in the compiler

```mermaid
graph LR
    A["Source .svelte"] --> B["compiler_parse<br/>phase 1"]
    B --> C["compiler_analyze<br/>phase 2"]
    C --> D["compiler_transform_client<br/>phase 3"]
    D --> E["JS module"]

    subgraph D2["inside phase 3 / client"]
        F["elements<br/>(this module)"]
        G["blocks"]
        H["components"]
        I["directives"]
        J["javascript"]
        K["template"]
        L["core"]
    end

    D --- D2
    F -.->|"emits calls into"| M["client_dom_elements<br/>runtime"]

    style F fill:#dbeafe,stroke:#2563eb,stroke-width:2px
```

Related modules:

- [compiler_transform_client](compiler_transform_client.md) — the parent visitor
  set and the dispatch table that routes each AST node type here.
- [compiler_transform_client_core](compiler_transform_client_core.md) —
  `Memoizer`, `build_expression`, `build_template_chunk`, `build_getter`, and the
  `ComponentClientTransformState` type this module reads and mutates.
- [compiler_transform_client_template](compiler_transform_client_template.md) —
  the `Template` class that collects the static HTML, and `process_children`
  which walks child nodes.
- [compiler_transform_client_directives](compiler_transform_client_directives.md)
  — `bind:`, `use:`, `transition:`, `on:`, and `{@attach}` are visited *from*
  this module but implemented there.
- [compiler_transform_client_components](compiler_transform_client_components.md)
  — the sibling module for `<Foo />` rather than `<div>`.
- [client_dom_elements](client_dom_elements.md) and
  [client_blocks](client_blocks.md) — the runtime functions the generated code
  actually calls.
- [compiler_transform_server](compiler_transform_server.md) — the SSR
  counterpart, which emits HTML strings instead of DOM operations.
- [compiler_ast_types](compiler_ast_types.md) — the node shapes
  (`AST.RegularElement`, `AST.Attribute`, …).

## Internal architecture

```mermaid
graph TD
    subgraph Entry["Visitor entry points"]
        RE["RegularElement"]
        SE["SvelteElement"]
        AT["Attribute"]
        SA["SpreadAttribute"]
        TE["TitleElement"]
        SH["SvelteHead"]
        SW["SvelteWindow"]
        SB["SvelteBody"]
        SD["SvelteDocument"]
    end

    subgraph Shared["shared/ helpers"]
        BAV["build_attribute_value"]
        BAE["build_attribute_effect"]
        BSC["build_set_class"]
        BSS["build_set_style"]
        GAN["get_attribute_name"]
        VSE["visit_special_element"]
    end

    subgraph Dirs["directive object builders"]
        BCD["build_class_directives_object"]
        BSD["build_style_directives_object"]
    end

    RE --> BAV & BAE & BSC & BSS & GAN
    SE --> BAV & BAE & BSC
    AT --> EV["visit_event_attribute<br/>(directives module)"]
    RE --> EV
    TE --> BTC["build_template_chunk<br/>(core module)"]
    SW --> VSE
    SB --> VSE
    SD --> VSE

    BAE --> BCD & BSD
    BSC --> BCD
    BSS --> BSD
    BCD & BSD --> MEM["Memoizer<br/>(core module)"]
    BAV --> MEM

    style Entry fill:#eff6ff,stroke:#2563eb
    style Shared fill:#f0fdf4,stroke:#16a34a
    style Dirs fill:#fefce8,stroke:#ca8a04
```

The shape is: **thin visitors, fat shared helpers**. `Attribute.js` and
`SpreadAttribute.js` are three lines each. `shared/element.js` holds the real
logic, and both `RegularElement` and `SvelteElement` call into it.

## The central decision: static, init, or update?

Every attribute goes through the same triage. This is the single most important
idea in the module.

```mermaid
flowchart TD
    A["An attribute on an element"] --> B{"Is there a<br/>spread anywhere<br/>on this element?"}
    B -->|yes| C["build_attribute_effect<br/>one $.attribute_effect for<br/>the whole element"]
    B -->|no| D{"Is it an event<br/>attribute (onclick…)?"}
    D -->|yes| E["visit_event_attribute<br/>delegate or addEventListener"]
    D -->|no| F{"Static text or true,<br/>and settable via HTML?"}
    F -->|yes| G["template.set_prop<br/>baked into the HTML string.<br/>Zero runtime cost."]
    F -->|no| H{"Does the value<br/>read reactive state?"}
    H -->|no| I["push to state.init<br/>runs once on mount"]
    H -->|yes| J["push to state.update<br/>wrapped in $.template_effect"]

    style G fill:#dcfce7,stroke:#16a34a
    style I fill:#fef9c3,stroke:#ca8a04
    style J fill:#fee2e2,stroke:#dc2626
```

`build_attribute_value` returns `{ value, has_state }`, and `has_state` is what
picks between `init` and `update` at the bottom of that tree. The pattern

```js
(has_state ? context.state.update : context.state.init).push(b.stmt(...));
```

appears in `build_set_class`, `build_set_style`, `TitleElement`, and the generic
attribute path in `RegularElement`. It is the module's signature line.

### Why spread forces a different path

Without a spread the compiler knows every attribute name at build time, so it
can emit one targeted call per attribute. With `{...props}` it does not — a name
could appear, disappear, or collide with a previous one. So the whole element
switches to `$.attribute_effect`, which takes a thunk returning one object of
all attributes and diffs it at runtime. Class and style directives ride along in
that same object under the `$.CLASS` and `$.STYLE` symbol keys, so they stay in
the correct order relative to a spread `class` key.

## Generated code, before and after

Static only — no JS at all, it is pure template:

```svelte
<div class="card" id="main">hello</div>
```

```js
var root = $.from_html(`<div class="card" id="main">hello</div>`);
```

One reactive attribute — a targeted effect:

```svelte
<div title={name}>hello</div>
```

```js
var div = root();
$.template_effect(() => $.set_attribute(div, 'title', name()));
```

A spread — one combined effect:

```svelte
<div {...props} class:active={on}>hello</div>
```

```js
var div = root();
$.attribute_effect(div, ($0) => ({ ...props(), [$.CLASS]: $0 }), [() => ({ active: on() })]);
```

## Sub-modules

The module splits into four areas. Each has its own document.

```mermaid
graph TD
    M["compiler_transform_client_elements"]
    M --> S1["…_regular<br/>static elements"]
    M --> S2["…_dynamic<br/>svelte:element"]
    M --> S3["…_attributes<br/>shared attribute engine"]
    M --> S4["…_special<br/>window / body / document / head / title"]

    S1 --> S3
    S2 --> S3
    S4 -.->|"minimal overlap"| S3

    style M fill:#dbeafe,stroke:#2563eb,stroke-width:2px
```

### Regular elements

Handles `<div>`, `<input>`, `<select>`, `<video>`, custom elements — every
ordinary tag. This is the largest piece. It sorts an element's attributes into
seven buckets, applies per-tag workarounds (`remove_input_defaults`, textarea
child removal, `<select>` value sync, the Chromium `dir="auto"` bug), decides
whether children can be collapsed into a single `textContent` assignment, and
builds the class/style directive objects.

See [compiler_transform_client_elements_regular](compiler_transform_client_elements_regular.md).

### Dynamic elements

Handles `<svelte:element this={tag}>`, where the tag name is only known at
runtime. Because the tag is unknown, this path cannot use the static HTML
template and cannot know whether the element is a custom element — so it almost
always routes attributes through the spread path. It emits a `$.element(...)`
call with the element body as a callback, plus dev-mode tag validation and
`$.async` wrapping when the tag expression awaits.

See [compiler_transform_client_elements_dynamic](compiler_transform_client_elements_dynamic.md).

### Attribute engine

The shared layer both element kinds depend on: `build_attribute_value`,
`build_attribute_effect`, `build_set_class`, `build_set_style`,
`get_attribute_name`, plus the trivial `Attribute` and `SpreadAttribute`
visitors. Owns the `has_state` contract, CSS-hash injection for scoped styles,
`clsx` handling, the previous-value tracking that lets `$.set_class` diff
cheaply, and `!important` splitting for style directives.

See [compiler_transform_client_elements_attributes](compiler_transform_client_elements_attributes.md).

### Special elements

Handles the tags that target something outside the component's own DOM:
`<svelte:window>`, `<svelte:body>`, `<svelte:document>` (all via the shared
`visit_special_element`), plus `<svelte:head>` and `<title>`. These produce no
element of their own — they retarget `state.node` at an existing global object,
or wrap children in a `$.head(...)` call.

See [compiler_transform_client_elements_special](compiler_transform_client_elements_special.md).

## Data flow through one element

```mermaid
sequenceDiagram
    participant P as parent visitor
    participant RE as RegularElement
    participant T as Template
    participant SH as shared/element.js
    participant D as directives module
    participant ST as transform state

    P->>RE: visit(node, context)
    RE->>T: push_element(name, start)
    RE->>RE: sort attributes into buckets
    RE->>D: visit bind:/use:/transition:/on:
    D-->>ST: init / after_update statements
    RE->>SH: build_set_class / build_set_style / build_attribute_value
    SH->>ST: init or update statements
    RE->>T: set_prop(name, value) for static attrs
    RE->>P: recurse into children (process_children)
    RE->>T: pop_element()
```

Note that `Template` operations are **balanced** — `push_element` at the top,
`pop_element` at every exit, including the early `noscript` return. An
unbalanced pair corrupts the HTML nesting for everything after it.

## Key conventions worth knowing

- **`$.` prefix** — every generated call is namespaced `$.foo`, referring to the
  runtime import namespace. `$.set_attribute` resolves to
  [client_dom_elements](client_dom_elements.md).
- **`b.` builders** — all AST output is built with the `#compiler/builders`
  helpers (`b.call`, `b.stmt`, `b.member`, …) from
  [compiler_core](compiler_core.md), never with string concatenation.
- **Three statement lists** — `init` (once, on mount), `update` (inside
  `$.template_effect`), `after_update` (once, but after children exist — used
  for event listeners so they attach in the right order).
- **`Memoizer`** — when an attribute value contains a function call or an
  `await`, the raw expression is swapped for a generated `$0`, `$1`, … id and
  the real expression moves into a derived. This stops a call from re-running
  once per dependent attribute.
- **Metadata is read, not computed** — flags such as `metadata.has_spread`,
  `metadata.scoped`, `metadata.needs_clsx`, `metadata.delegated`, and
  `metadata.expression.has_state` were all set in phase 2
  ([compiler_analyze](compiler_analyze.md)). This module trusts them.

## Document index

Every file this module's documentation is split across, and the source it covers.

| Document | Source files covered |
| --- | --- |
| [compiler_transform_client_elements_regular](compiler_transform_client_elements_regular.md) | `visitors/RegularElement.js` |
| [compiler_transform_client_elements_dynamic](compiler_transform_client_elements_dynamic.md) | `visitors/SvelteElement.js` |
| [compiler_transform_client_elements_attributes](compiler_transform_client_elements_attributes.md) | `visitors/shared/element.js`, `visitors/Attribute.js`, `visitors/SpreadAttribute.js` |
| [compiler_transform_client_elements_special](compiler_transform_client_elements_special.md) | `visitors/shared/special_element.js`, `visitors/SvelteWindow.js`, `visitors/SvelteBody.js`, `visitors/SvelteDocument.js`, `visitors/SvelteHead.js`, `visitors/TitleElement.js` |

Sibling and dependency modules referenced above:
[compiler_transform_client](compiler_transform_client.md) ·
[compiler_transform_client_core](compiler_transform_client_core.md) ·
[compiler_transform_client_template](compiler_transform_client_template.md) ·
[compiler_transform_client_directives](compiler_transform_client_directives.md) ·
[compiler_transform_client_components](compiler_transform_client_components.md) ·
[compiler_transform_client_blocks](compiler_transform_client_blocks.md) ·
[compiler_transform_server](compiler_transform_server.md) ·
[compiler_analyze](compiler_analyze.md) ·
[compiler_core](compiler_core.md) ·
[compiler_ast_types](compiler_ast_types.md) ·
[client_dom_elements](client_dom_elements.md) ·
[client_blocks](client_blocks.md)
