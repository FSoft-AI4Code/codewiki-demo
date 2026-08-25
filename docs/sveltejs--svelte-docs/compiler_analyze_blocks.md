# compiler_analyze_blocks

## Introduction

`compiler_analyze_blocks` is the part of Svelte's **analysis phase** (phase 2) that
checks and annotates *template blocks and tags* — the `{#...}` and `{@...}`
constructs you write in a `.svelte` file.

It handles seven node types:

| Node | Template syntax |
| --- | --- |
| `IfBlock` | `{#if ...}` / `{:else if ...}` / `{:else}` |
| `EachBlock` | `{#each items as item, i (key)}` |
| `AwaitBlock` | `{#await ...}` / `{:then ...}` / `{:catch ...}` |
| `KeyBlock` | `{#key ...}` |
| `ConstTag` | `{@const x = ...}` |
| `DebugTag` | `{@debug x}` |
| `HtmlTag` | `{@html ...}` |

Each visitor does three kinds of work:

1. **Validate** — report errors and warnings for malformed or misplaced blocks.
2. **Annotate** — write facts onto the node's `metadata` (for example, "this
   `{#each}` is keyed", "this fragment is dynamic") that later phases read.
3. **Recurse** — hand control back to the walker with the right `state`, so the
   block's expression is analysed against the right scope and the right
   `ExpressionMetadata` bucket.

The visitors never rewrite the AST. They only read it, decorate it, and raise
diagnostics. Code generation happens later in
[compiler_transform_client](compiler_transform_client.md) and
[compiler_transform_server](compiler_transform_server.md).

---

## Where this module sits

```mermaid
graph LR
    SRC[".svelte source"] --> P["Phase 1: parse<br/>compiler_parse"]
    P --> AST["Template AST<br/>compiler_ast_types"]
    AST --> SCOPE["create_scopes<br/>compiler_core"]
    SCOPE --> A["Phase 2: analyze<br/>compiler_analyze"]
    A --> BLK["compiler_analyze_blocks<br/>(this module)"]
    A --> SE["compiler_analyze_special_elements"]
    A --> EM["compiler_analyze_expression_metadata"]
    A --> EX["compiler_analyze_exports"]
    A --> CSS["compiler_analyze_css"]
    BLK --> ANL["ComponentAnalysis<br/>+ decorated AST"]
    SE --> ANL
    EM --> ANL
    EX --> ANL
    CSS --> ANL
    ANL --> TC["Phase 3: transform client"]
    ANL --> TS["Phase 3: transform server"]
    TC --> RT["client_blocks runtime"]
```

Read [compiler_analyze](compiler_analyze.md) for how the whole phase is wired,
and [compiler_parse](compiler_parse.md) for how these block nodes are produced.

---

## Files in the module

```
phases/2-analyze/visitors/
├── IfBlock.js            {#if} / {:else if}
├── EachBlock.js          {#each}
├── AwaitBlock.js         {#await}
├── KeyBlock.js           {#key}
├── ConstTag.js           {@const}
├── DebugTag.js           {@debug}
├── HtmlTag.js            {@html}
└── shared/
    ├── utils.js          validate_block_not_empty, validate_opening_tag, ...
    └── fragment.js       mark_subtree_dynamic
```

### Component map

```mermaid
graph TD
    subgraph "Block visitors"
        IF["IfBlock"]
        EACH["EachBlock"]
        AWAIT["AwaitBlock"]
        KEY["KeyBlock"]
    end
    subgraph "Tag visitors"
        CONST["ConstTag"]
        DEBUG["DebugTag"]
        HTML["HtmlTag"]
    end
    subgraph "shared/utils.js"
        VOT["validate_opening_tag"]
        VBNE["validate_block_not_empty"]
    end
    subgraph "shared/fragment.js"
        MSD["mark_subtree_dynamic"]
    end
    subgraph "Diagnostics"
        ERR["errors.js"]
        WARN["warnings.js"]
    end

    IF --> VOT & VBNE & MSD
    EACH --> VOT & VBNE & MSD
    AWAIT --> VOT & VBNE & MSD
    KEY --> VOT & VBNE & MSD
    CONST --> VOT
    DEBUG --> VOT
    HTML --> VOT & MSD

    VOT --> ERR
    VBNE --> WARN
    EACH --> ERR
    AWAIT --> ERR
    CONST --> ERR
```

Notice the shape: every visitor is a thin, node-specific policy layer sitting on
top of two tiny shared helpers. That is the whole design of the module.

---

## The two shared helpers

### `validate_opening_tag(node, state, expected)`

Checks that the character right after the opening `{` is the expected sigil —
`#` for `{#if}`, `:` for `{:else if}`, `@` for `{@const}`.

It reads the **raw source text** (`state.analysis.source`) rather than the AST,
because the parser in legacy mode tolerates whitespace like `{ #if ...}`. This
check exists so runes-mode components reject that older, looser syntax. When it
fails it calls `e.block_unexpected_character` and highlights only the first ~5
characters, to avoid a wall of red squiggles.

```mermaid
flowchart TD
    S["source[node.start + 1]"] --> Q{"=== expected sigil?"}
    Q -- yes --> OK["continue"]
    Q -- no --> E["e.block_unexpected_character<br/>span = start..start+5"]
```

> Important: most visitors call this **only when `analysis.runes` is true**.
> `EachBlock` is the exception — it validates unconditionally, in both runes and
> legacy mode.

### `validate_block_not_empty(fragment, context)`

Emits the `block_empty` **warning** when a block body contains nothing but
whitespace text. It deliberately stays quiet when the body has zero nodes,
assuming the developer is mid-typing and a warning would just be noise.

### `mark_subtree_dynamic(path)`

The one piece of *annotation* shared across the module. It walks the ancestor
`path` from the innermost node outward and sets `metadata.dynamic = true` on
every `Fragment` it passes. It stops early the moment it finds a fragment
already marked, so repeated calls stay cheap.

```mermaid
flowchart TD
    START["mark_subtree_dynamic(path)"] --> LOOP["walk path from last to first"]
    LOOP --> ISF{"node.type === 'Fragment'?"}
    ISF -- no --> LOOP
    ISF -- yes --> DYN{"metadata.dynamic already true?"}
    DYN -- yes --> RET["return (ancestors already marked)"]
    DYN -- no --> SET["metadata.dynamic = true"]
    SET --> LOOP
```

**Why it matters:** a fragment marked `dynamic` tells phase 3 that the runtime
must walk into this fragment during mount and hydrate, instead of treating it as
a static chunk of HTML that can be cloned wholesale. Any block whose content can
change over time must set this flag, or the generated code would skip creating
the effects that keep it up to date.

---

## Common visitor shape

Every visitor in this module follows the same four-step pattern.

```mermaid
sequenceDiagram
    participant W as zimmerframe walker
    participant V as Block visitor
    participant U as shared/utils.js
    participant F as shared/fragment.js
    participant C as children

    W->>V: visit(node, context)
    V->>U: validate_block_not_empty(bodies)
    alt analysis.runes
        V->>U: validate_opening_tag(node, state, sigil)
    end
    V->>V: node-specific checks + metadata writes
    V->>F: mark_subtree_dynamic(context.path)
    V->>C: context.visit(expression, {...state, expression: node.metadata.expression})
    V->>C: context.visit(body fragments)
    C-->>W: continue traversal
```

The key detail is the `expression` field threaded through `state`. Sibling module
[compiler_analyze_expression_metadata](compiler_analyze_expression_metadata.md)
owns the visitors that *fill in* `ExpressionMetadata` (`dependencies`,
`has_state`, `has_call`, `has_await`, …). Block visitors decide **which bucket**
those facts land in, by setting `state.expression` before descending. That is how
the compiler later knows, for instance, that the `{#if}` test depends on a
particular state variable and therefore needs its own reactive effect.

---

## Per-visitor behaviour

### IfBlock

```javascript
validate_block_not_empty(node.consequent, context);
validate_block_not_empty(node.alternate, context);
if (runes) validate_opening_tag(node, state, node.elseif ? ':' : '#');
mark_subtree_dynamic(context.path);
context.visit(node.test, { ...state, expression: node.metadata.expression });
context.visit(node.consequent);
if (node.alternate) context.visit(node.alternate);
```

The sigil is chosen from the `elseif` flag: an `{:else if}` chain is represented
as a nested `IfBlock` with `elseif: true`, so it expects `:` rather than `#`.

### KeyBlock

The simplest block: check the single fragment is not empty, validate the `#`
sigil in runes mode, mark the subtree dynamic, then visit the key expression and
the fragment.

### AwaitBlock

Handles three optional bodies (`pending`, `then`, `catch`) and adds a check the
other blocks do not need — a **`:then` / `:catch` sigil check for the value
pattern**.

```mermaid
flowchart TD
    A["AwaitBlock(node, context)"] --> B["validate_block_not_empty × 3<br/>(pending, then, catch)"]
    B --> R{"analysis.runes?"}
    R -- no --> M["mark_subtree_dynamic"]
    R -- yes --> V["validate_opening_tag(node, '#')"]
    V --> VAL{"node.value present?"}
    VAL -- yes --> RX1["match source[start-10 .. start]<br/>against /{(\\s*):then\\s+$/"]
    RX1 --> W1{"captured whitespace non-empty?"}
    W1 -- yes --> E1["e.block_unexpected_character(':')"]
    W1 -- no --> ERRB
    VAL -- no --> ERRB
    ERRB{"node.error present?"} -- yes --> RX2["same check with /{(\\s*):catch\\s+$/"]
    RX2 --> W2{"captured whitespace non-empty?"}
    W2 -- yes --> E2["e.block_unexpected_character(':')"]
    W2 -- no --> M
    ERRB -- no --> M
    M --> VIS["visit expression (with metadata bucket),<br/>then pending / then / catch"]
```

**Why the regex?** The `{:then value}` and `{:catch error}` clauses are not
separate AST nodes — the pattern hangs off the `AwaitBlock` as `node.value` /
`node.error`. There is no node whose `start` points at the `{`, so the visitor
looks backwards 10 characters from the pattern's `start` and reconstructs the
clause opening from the raw source. If the captured whitespace group is
non-empty, the source said `{ :then foo}`, which runes mode rejects.

### EachBlock

The largest visitor, because it carries both keying logic and the legacy
reactivity fixups.

```mermaid
flowchart TD
    A["EachBlock(node, context)"] --> VOT["validate_opening_tag(node, '#')<br/>NOTE: unconditional, not runes-only"]
    VOT --> VBNE["validate_block_not_empty(body, fallback)"]
    VBNE --> RUNE{"context is '$state' or '$derived'?"}
    RUNE -- yes --> ERR["e.state_invalid_placement"]
    RUNE -- no --> KEYED

    KEYED{"node.key present?"} -- yes --> CALC["metadata.keyed =<br/>key is not the bare index identifier"]
    KEYED -- no --> EXPR
    CALC --> EXPR

    EXPR["visit(node.expression) in PARENT scope<br/>+ metadata.expression bucket"]
    EXPR --> KIDS["visit body, key, fallback"]
    KIDS --> LEG{"analysis.runes?"}
    LEG -- yes --> MSD["mark_subtree_dynamic"]
    LEG -- no --> MUT["mutated = any identifier in node.context<br/>has a mutated binding"]
    MUT --> TD["collect_transitive_dependencies<br/>for each expression dependency"]
    TD --> PROMOTE{"mutated?"}
    PROMOTE -- yes --> STATE["promote normal const/let/var<br/>transitive deps to kind = 'state'"]
    PROMOTE -- no --> MSD
    STATE --> MSD
```

Three things deserve attention:

**1. The expression is visited in the parent scope.**

```javascript
context.visit(node.expression, {
  ...context.state,
  expression: node.metadata.expression,
  scope: context.state.scope.parent
});
```

`create_scopes` (see [compiler_core](compiler_core.md)) gives an `EachBlock` its
own child scope holding the `as item` binding and the index. But
`{#each items as items}` must resolve `items` to the *outer* variable, not to
itself. Stepping up to `scope.parent` makes that correct.

**2. Keyed vs. indexed.**

```javascript
node.metadata.keyed =
  node.key.type !== 'Identifier' || !node.index || node.key.name !== node.index;
```

`{#each items as item, i (i)}` keys by the index, which is the same thing as not
keying at all — so it is treated as a plain indexed block, which is faster. Any
other key expression makes the block genuinely keyed. Phase 3 reads this flag to
pick the runtime each-block strategy (see [client_blocks](client_blocks.md)).

**3. Legacy transitive state promotion (non-runes only).**

In Svelte 4 semantics, mutating `item` inside `{#each items as item}` must
invalidate `items` — and anything `items` itself derives from. So the visitor:

- checks whether any binding introduced by `node.context` is `mutated`;
- walks the expression's `dependencies`, following `legacy_reactive` bindings
  through their `legacy_dependencies` recursively (`collect_transitive_dependencies`,
  guarded by a `Set` so cycles terminate), storing the closure in
  `metadata.transitive_deps`;
- if the item *was* mutated, promotes every plain `const` / `let` / `var` binding
  in that closure from `kind: 'normal'` to `kind: 'state'`, so phase 3 will back
  them with mutable sources that can be invalidated.

```mermaid
graph LR
    subgraph "collect_transitive_dependencies"
        D1["expression dependency"] --> S["Set&lt;Binding&gt;"]
        D1 --> LR{"kind === 'legacy_reactive'?"}
        LR -- yes --> D2["legacy_dependencies"]
        D2 --> S
        D2 --> LR
    end
    S --> PROM["promote normal → state<br/>if item mutated"]
```

### ConstTag

Does no dynamic marking. Its distinctive job is a **placement check**: `{@const}`
is only legal as a direct child of a fragment whose owner can host it.

```mermaid
flowchart TD
    A["ConstTag(node, context)"] --> R{"runes?"}
    R -- yes --> V["validate_opening_tag(node, '@')"]
    R -- no --> P
    V --> P["parent = path.at(-1)<br/>grand_parent = path.at(-2)"]
    P --> C1{"parent is a Fragment?"}
    C1 -- no --> ERR["e.const_tag_invalid_placement"]
    C1 -- yes --> C2{"grand_parent is one of:<br/>IfBlock, EachBlock, AwaitBlock,<br/>KeyBlock, SnippetBlock, SvelteFragment,<br/>SvelteBoundary, Component, SvelteComponent?"}
    C2 -- yes --> OK
    C2 -- no --> C3{"grand_parent is RegularElement/SvelteElement<br/>WITH a slot attribute?"}
    C3 -- yes --> OK
    C3 -- no --> ERR
    OK["visit(declaration.id)<br/>visit(declaration.init) with metadata bucket"]
```

The element-with-`slot` escape hatch exists because such an element acts as a
slot template, which is a legal `{@const}` host. The declaration is visited in
two parts: the pattern `id` with the ambient state, and `init` with the tag's
own `ExpressionMetadata` bucket.

### HtmlTag

```javascript
if (runes) validate_opening_tag(node, state, '@');
mark_subtree_dynamic(context.path);          // "unfortunately this is necessary"
context.next({ ...state, expression: node.metadata.expression });
```

`{@html}` always marks its subtree dynamic — even for a constant string. The
comment in the source explains why: raw HTML may be malformed, and the browser's
parser will reshape it on insertion. Because the compiler cannot predict the
resulting DOM shape, it cannot rely on static template cloning here, so the
subtree must be traversed at runtime.

### DebugTag

The thinnest visitor in the module: validate the `@` sigil in runes mode, then
`context.next()`. It does *not* mark the subtree dynamic — `{@debug}` produces no
DOM. Note also that `DebugTag` in the AST has no `metadata.expression`; it carries
a plain `identifiers` array instead, so there is no bucket to thread.

---

## Behaviour comparison

| Visitor | Empty-body warning | Opening-tag check | Marks subtree dynamic | Extra validation | Writes metadata |
| --- | --- | --- | --- | --- | --- |
| `IfBlock` | consequent, alternate | runes only, `:` or `#` | yes | — | — |
| `EachBlock` | body, fallback | **always**, `#` | yes | `$state`/`$derived` as context name | `keyed`, `transitive_deps`, binding kinds |
| `AwaitBlock` | pending, then, catch | runes only, `#` | yes | `:then` / `:catch` sigil via source regex | — |
| `KeyBlock` | fragment | runes only, `#` | yes | — | — |
| `ConstTag` | — | runes only, `@` | **no** | parent / grandparent placement | — |
| `DebugTag` | — | runes only, `@` | **no** | — | — |
| `HtmlTag` | — | runes only, `@` | yes (always) | — | — |

---

## Data flow: what the module reads and writes

```mermaid
graph TD
    subgraph "Reads"
        SRC["state.analysis.source<br/>(raw text)"]
        RUNES["state.analysis.runes"]
        SCOPE["state.scope / scope.parent"]
        PATH["context.path"]
        BIND["Binding.mutated / .kind /<br/>.declaration_kind / .legacy_dependencies"]
    end

    V["Block & tag visitors"]

    subgraph "Writes"
        FDYN["Fragment.metadata.dynamic"]
        EK["EachBlock.metadata.keyed"]
        ETD["EachBlock.metadata.transitive_deps"]
        BK["Binding.kind → 'state'<br/>(legacy mode)"]
        DIAG["errors + warnings"]
        EXPR["state.expression routing<br/>→ ExpressionMetadata buckets"]
    end

    SRC --> V
    RUNES --> V
    SCOPE --> V
    PATH --> V
    BIND --> V
    V --> FDYN & EK & ETD & BK & DIAG & EXPR
```

### Consumers downstream

```mermaid
graph LR
    FDYN["Fragment.metadata.dynamic"] --> TCF["transform/client Fragment.js<br/>walk vs. static clone"]
    EK["metadata.keyed"] --> TCE["transform/client EachBlock.js<br/>keyed vs. indexed strategy"]
    ETD["transitive_deps + promoted<br/>binding kinds"] --> TCS["transform: mutable sources<br/>and invalidation"]
    EXPR["ExpressionMetadata"] --> TCX["transform: derived wrapping,<br/>effect dependencies"]
    TCF --> RT["client_blocks / server_runtime"]
    TCE --> RT
    TCS --> RT
    TCX --> RT
```

See [compiler_transform_client](compiler_transform_client.md),
[compiler_transform_server](compiler_transform_server.md), and
[client_blocks](client_blocks.md) for the consuming side.

---

## Runes mode vs. legacy mode

`analysis.runes` splits behaviour in two places, and it is the main source of
conditional logic in the module.

```mermaid
graph TD
    R{"analysis.runes"}
    R -- true --> A1["Strict opening-tag sigils enforced<br/>on all blocks and tags"]
    R -- true --> A2["AwaitBlock :then / :catch<br/>whitespace check runs"]
    R -- true --> A3["EachBlock: no state promotion —<br/>runes already track reactivity"]
    R -- false --> B1["Whitespace like { #if } tolerated<br/>(except EachBlock, always strict)"]
    R -- false --> B2["EachBlock: transitive deps collected<br/>and normal bindings promoted to state"]
```

The comment on `validate_opening_tag` states the intent plainly: once legacy mode
is removed, this check should move into the parser and disappear from analysis.
The same is true of the whole legacy branch of `EachBlock`.

---

## Traversal example

For this template:

```svelte
{#each rows as row (row.id)}
  {#if row.open}
    {@const label = row.name.toUpperCase()}
    {@html row.body}
  {/if}
{/each}
```

```mermaid
sequenceDiagram
    participant E as EachBlock
    participant I as IfBlock
    participant C as ConstTag
    participant H as HtmlTag
    participant F as mark_subtree_dynamic

    E->>E: validate_opening_tag '#'
    E->>E: metadata.keyed = true (key is row.id, not index)
    E->>E: visit(rows) in PARENT scope
    E->>I: visit(body)
    I->>I: validate consequent not empty
    I->>F: mark ancestor Fragments dynamic
    I->>I: visit(row.open) into IfBlock metadata bucket
    I->>C: visit(consequent) → ConstTag
    C->>C: parent = Fragment, grand_parent = IfBlock → legal
    C->>C: visit(label pattern), visit(init) into ConstTag bucket
    I->>H: visit HtmlTag
    H->>F: mark dynamic (already marked → early return)
    H->>H: visit(row.body) into HtmlTag bucket
    E->>F: mark_subtree_dynamic (runes mode)
```

Note the early return in `mark_subtree_dynamic`: the `IfBlock` marked the chain
first, so the later calls from `HtmlTag` and `EachBlock` cost almost nothing.

---

## Extending the module

To add a new block or tag visitor:

1. Create `visitors/MyBlock.js` exporting `MyBlock(node, context)`.
2. Register it in the visitor table used by `analyze_component`
   (see [compiler_analyze](compiler_analyze.md)).
3. Call `validate_opening_tag(node, context.state, sigil)` — gate it on
   `context.state.analysis.runes` unless the syntax was always strict.
4. Call `validate_block_not_empty` for each optional body fragment.
5. Call `mark_subtree_dynamic(context.path)` **if and only if** the block can
   produce DOM that changes at runtime. Skipping this on a dynamic block causes
   subtle "the UI never updates" bugs; adding it needlessly costs performance.
6. Thread `expression: node.metadata.expression` into the state you pass when
   visiting the block's own expressions, so expression facts land in the right
   bucket.
7. Add matching transform visitors in
   [compiler_transform_client](compiler_transform_client.md) and
   [compiler_transform_server](compiler_transform_server.md), plus node types in
   [compiler_ast_types](compiler_ast_types.md).

---

## Related modules

| Module | Relationship |
| --- | --- |
| [compiler_analyze](compiler_analyze.md) | Parent phase; owns the visitor table and `ComponentAnalysis` |
| [compiler_analyze_expression_metadata](compiler_analyze_expression_metadata.md) | Fills the `ExpressionMetadata` buckets these visitors route into |
| [compiler_analyze_special_elements](compiler_analyze_special_elements.md) | Sibling: `<svelte:*>` elements; shares the `shared/` helpers |
| [compiler_analyze_exports](compiler_analyze_exports.md) | Sibling; also uses `shared/utils.js` |
| [compiler_analyze_css](compiler_analyze_css.md) | Sibling; runs after the AST walk and also calls `mark_subtree_dynamic` |
| [compiler_parse](compiler_parse.md) | Produces the block nodes consumed here |
| [compiler_core](compiler_core.md) | `create_scopes`, `Scope`, `Binding`, builders |
| [compiler_ast_types](compiler_ast_types.md) | `AST.IfBlock`, `AST.EachBlock`, `ExpressionMetadata`, … |
| [compiler_transform_client](compiler_transform_client.md) | Reads `keyed`, `dynamic`, promoted binding kinds |
| [compiler_transform_server](compiler_transform_server.md) | Server-side counterpart |
| [client_blocks](client_blocks.md) | Runtime implementations these decisions target |
| [compiler_options_and_warnings](compiler_options_and_warnings.md) | Defines `block_empty` and friends |
