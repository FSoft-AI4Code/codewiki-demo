# compiler_analyze_css

## Introduction

`compiler_analyze_css` is the CSS brain of Svelte's analysis phase (phase 2). It takes the CSS
AST that the parser produced from a component's `<style>` block, together with the list of
elements in the component's template, and answers three questions:

1. **Is this CSS valid?** — mostly rules about where `:global` and `&` may appear.
2. **Which selector matches which element?** — so the transform phase knows which elements need
   the scoping class and which selectors need the scoping suffix.
3. **Which selectors match nothing?** — so the compiler can warn about dead CSS.

It does not rewrite any CSS. It only *annotates* the AST with metadata. The rewriting happens
later in [compiler_css_transform](compiler_css_transform.md), which reads exactly the flags this
module writes.

The module lives in `packages/svelte/src/compiler/phases/2-analyze/css/` and has four files:

| File | Core exports | Job |
| --- | --- | --- |
| `css-analyze.js` | `analyze_css`, plus internal `is_global_block_selector`, `is_in_global_block`, `is_unscoped` | Walk the stylesheet, validate it, mark globalness, collect keyframes |
| `css-prune.js` | `prune` | Match one template element against every selector; mark matches as used/scoped |
| `css-warn.js` | `warn_unused` | Walk the stylesheet again and warn for every selector still unmarked |
| `utils.js` | `is_global`, `is_unscoped_pseudo_class`, `get_possible_values`, plus `is_outer_global`, `get_parent_rules` | Shared predicates and the class/attribute value estimator |

---

## Where the module sits

```mermaid
graph LR
    subgraph parse["compiler_parse"]
        RS["read_style<br/>(CSS AST)"]
    end

    subgraph analyze["compiler_analyze"]
        AC["analyze_component"]
        subgraph css["compiler_analyze_css"]
            A1["analyze_css"]
            A2["prune (per element)"]
            A3["warn_unused"]
        end
    end

    subgraph transform["compiler_css_transform"]
        RSS["render_stylesheet"]
    end

    RS -->|"AST.CSS.StyleSheet"| AC
    AC --> A1
    A1 -->|"metadata written"| A2
    A2 -->|"used / scoped flags"| A3
    A2 -->|"element.metadata.scoped"| AC
    A1 -->|"css.keyframes, css.has_global"| RSS
    A3 --> RSS
    AC -->|"annotated AST"| RSS
    RSS -->|"css.code + hasGlobal"| OUT["CompileResult.css"]
```

Related modules:

- [compiler_parse_readers_style](compiler_parse_readers_style.md) — produces the CSS AST this
  module consumes (`read_style`, `read_selector`, `read_at_rule`, `read_declaration`).
- [compiler_analyze](compiler_analyze.md) — the parent phase; `analyze_component` is the only
  caller of this module.
- [compiler_css_transform](compiler_css_transform.md) — the consumer of all metadata produced here.
- [compiler_options_and_warnings](compiler_options_and_warnings.md) — defines `css_unused_selector`
  and the `css_*` error factories used below.
- [compiler_ast_types](compiler_ast_types.md) / [css_ast](css_ast.md) — the node and metadata
  shapes (`AST.CSS.Rule`, `RelativeSelector`, `PseudoClassSelector`, …).

### Call site inside `analyze_component`

```js
if (analysis.css.ast) {
    analyze_css(analysis.css.ast, analysis);

    // mark nodes as scoped/unused/empty etc
    for (const node of analysis.elements) {
        prune(analysis.css.ast, node);
    }

    if (!should_ignore_unused) {   // `<!-- svelte-ignore css_unused_selector -->`
        warn_unused(analysis.css.ast);
    }
}
```

Order matters and is strict: `analyze_css` writes the globalness metadata that `prune` reads;
`prune` writes the `used` flags that `warn_unused` reads.

---

## The metadata model

Everything this module does is expressed as flags on AST nodes. Understanding these five groups is
enough to understand the whole module.

```mermaid
classDiagram
    class Rule {
        metadata.parent_rule : Rule | null
        metadata.is_global_block : boolean
        metadata.has_global_selectors : boolean
        metadata.has_local_selectors : boolean
    }
    class ComplexSelector {
        metadata.rule : Rule | null
        metadata.is_global : boolean
        metadata.used : boolean
    }
    class RelativeSelector {
        metadata.is_global : boolean
        metadata.is_global_like : boolean
        metadata.scoped : boolean
    }
    class ComponentAnalysis_css {
        keyframes : string[]
        has_global : boolean
        hash : string
    }
    class Element {
        metadata.scoped : boolean
        metadata.path : SvelteNode[]
    }

    Rule --> ComplexSelector : prelude.children
    ComplexSelector --> RelativeSelector : children
    Rule --> Rule : nested rules
```

| Flag | Written by | Read by | Meaning |
| --- | --- | --- | --- |
| `Rule.metadata.parent_rule` | `analyze_css` | `prune`, `utils` | Enclosing rule for CSS nesting; `null` at top level |
| `Rule.metadata.is_global_block` | `analyze_css` | `prune`, `warn_unused`, transform | Rule's prelude starts with bare `:global` |
| `Rule.metadata.has_global_selectors` / `has_local_selectors` | `analyze_css` | transform | Whether any / not-all selectors are global |
| `ComplexSelector.metadata.rule` | `analyze_css` | `prune` | Back-pointer used for nesting resolution |
| `ComplexSelector.metadata.is_global` | `analyze_css` | transform, `prune` | Every relative selector is global(-like) |
| `ComplexSelector.metadata.used` | `analyze_css` + `prune` | `warn_unused`, transform | Selector matched something (or is global) |
| `RelativeSelector.metadata.is_global` | `analyze_css` | `prune`, transform | Truly `:global(...)` / bare `:global` |
| `RelativeSelector.metadata.is_global_like` | `analyze_css` | `prune`, transform | `:root`, `:host`, `::view-transition*`, or sits after `:global` in a global block |
| `RelativeSelector.metadata.scoped` | `prune` | transform | Needs the `.svelte-xyz` suffix appended |
| `Element.metadata.scoped` | `prune` | `analyze_component`, client/server transforms | Element needs the scoping class attribute |
| `analysis.css.keyframes` | `analyze_css` | transform | Local `@keyframes` names to rename |
| `analysis.css.has_global` | `analyze_css` | `render_stylesheet` → `CompileResult.css.hasGlobal` | Component emits CSS affecting things outside itself |

---

## Stage 1 — `analyze_css`

```js
export function analyze_css(stylesheet, analysis) {
    const css_state = { keyframes: analysis.css.keyframes, rule: null, analysis };
    walk(stylesheet, css_state, css_visitors);
}
```

A single `zimmerframe` walk with a `CssState` carrying the *current* rule (so nested selectors know
their owner), the keyframes accumulator, and the whole `ComponentAnalysis`.

### Visitor responsibilities

```mermaid
graph TD
    W["walk(stylesheet, css_state, css_visitors)"]

    W --> AT["Atrule"]
    W --> R["Rule"]
    W --> CS["ComplexSelector"]
    W --> RSel["RelativeSelector"]
    W --> NS["NestingSelector"]

    AT --> AT1["is_keyframes_node?<br/>collect local name<br/>or flag has_global for -global-"]
    R --> R1["set parent_rule"]
    R --> R2["detect :global block<br/>+ validate modifiers/combinator/list"]
    R --> R3["visit prelude, then block<br/>(explicit ordering)"]
    R --> R4["roll up has_global_selectors<br/>/ has_local_selectors / has_global"]
    CS --> CS1["validate :global placement<br/>inside the selector"]
    CS --> CS2["is_global = all children global(-like)"]
    CS --> CS3["used ||= is_global"]
    CS --> CS4["mark &:hover under :global(...) as used"]
    RSel --> RS1["validate leading combinator"]
    RSel --> RS2["is_global via utils.is_global"]
    RSel --> RS3["is_global_like: :root / :host / ::view-transition*"]
    RSel --> RS4["pre-mark nested selectors inside globals as used"]
    NS --> NS1["validate & placement<br/>(needs a parent rule)"]
```

### `Atrule` — keyframes bookkeeping

For `@keyframes` (after vendor-prefix stripping via
[`is_keyframes_node`](compiler_css_transform.md)):

- name **not** starting with `-global-` and **not** inside a `:global {}` block →
  push the name onto `state.keyframes`, so the transform can rename it to `hash-name` and rewrite
  matching `animation` declarations.
- name starting with `-global-` → the keyframes escape the component, so
  `analysis.css.has_global ||= is_unscoped(path)`.

### `Rule` — `:global {}` blocks, nesting and roll-up

The heavy lifting. For each complex selector in the prelude it scans the relative selectors for a
bare `:global` (`is_global_block_selector`: a `PseudoClassSelector` named `global` with
`args === null`).

- Bare `:global` at position 0 of a relative selector → `node.metadata.is_global_block = true`,
  and everything **after** it in the same complex selector becomes `is_global_like`.
- Any inner selectors of the `:global` compound (`:global.foo`) are walked and force-marked
  `used`, because scoping never applies to them.
- After the prelude is visited, per-selector globalness is rolled up into
  `has_global_selectors` / `has_local_selectors`.
- `analysis.css.has_global` becomes true when a rule has global selectors **and** contains real
  declarations (not just nested rules) **and** every enclosing rule also has global selectors
  (`is_unscoped`).

The prelude is visited explicitly *before* the block, so that when nested rules are visited their
`parent_rule` metadata is already populated:

```js
const state = { ...context.state, rule: node };
context.visit(node.prelude, state);   // populate child selector metadata
/* roll-up happens here */
context.visit(node.block, state);     // nested rules see parent metadata
```

### Helper predicates in this file

| Function | Input | Returns true when |
| --- | --- | --- |
| `is_global_block_selector(simple_selector)` | one simple selector | it is exactly `:global` (no args) |
| `is_in_global_block(path)` | CSS node path | some ancestor rule has `is_global_block` |
| `is_unscoped(path)` | node path | every ancestor `Rule` has `has_global_selectors` |

### Errors raised here

All of these come from `../../../errors.js` and abort compilation:

| Error | Triggered by |
| --- | --- |
| `css_global_block_invalid_placement` | nested `:global` used where it cannot be (e.g. inside a pseudo-class) |
| `css_global_invalid_placement` | `:global(...)` in the middle of a selector, followed by non-global parts |
| `css_global_invalid_selector` | `:global(a, b)` with several selectors inside a larger selector |
| `css_global_invalid_selector_list` | `:global(element)` not first in its compound selector |
| `css_type_selector_invalid_placement` | `:global(.x)element` |
| `css_global_block_invalid_modifier` | `:global` appearing after another selector in a compound (`.x:global`) |
| `css_global_block_invalid_modifier_start` | `:global.x { }` at top level, or `:global { &.foo { } }` |
| `css_global_block_invalid_combinator` | `:global > { }` (combinator other than descendant) |
| `css_global_block_invalid_list` | `:global, :global x { }` — mixing a lone `:global` into a list |
| `css_global_block_invalid_declaration` | `:global { color: red }` — declarations directly in a lone global block |
| `css_selector_invalid` | a leading combinator on a non-nested rule |
| `css_nesting_selector_invalid_placement` | `&` used outside a nested rule (except inside `:global(&)`) |

---

## Stage 2 — `prune`

`prune(stylesheet, element)` is called **once per template element**. Despite the name it deletes
nothing; it decides, for this element, which selectors *could* match it, and records that as
`ComplexSelector.metadata.used`, `RelativeSelector.metadata.scoped` and
`element.metadata.scoped`.

```mermaid
sequenceDiagram
    participant AC as analyze_component
    participant P as prune
    participant AS as apply_selector
    participant RS as relative_selector_might_apply_to_node
    participant AC2 as apply_combinator

    AC->>P: prune(stylesheet, element)
    P->>P: walk stylesheet → each ComplexSelector
    P->>P: get_relative_selectors (truncate + inject &)
    P->>AS: apply_selector(selectors, rule, element, BACKWARD)
    AS->>RS: does the last relative selector fit this element?
    RS-->>AS: true / false
    AS->>AC2: follow the combinator to parents / siblings
    AC2->>AS: apply_selector(rest, rule, other_node, direction)
    AS-->>P: matched?
    P->>P: on match → selector.metadata.scoped,<br/>element.metadata.scoped, node.metadata.used
```

### Direction: matching runs backwards

CSS reads left-to-right, but the AST walk knows only the *current* element, so matching starts at
the **right-most** relative selector and walks up the template (`BACKWARD`). `:has(...)` inverts
this — inside `:has(...)` the algorithm switches to `FORWARD` and looks at descendants, treating
`.x:has(.y)` roughly like `.x .y`.

### Preparing the selector list

`get_relative_selectors(node)`:

1. `truncate(node)` drops **trailing** `:global(...)` / `:global` / global-like relative selectors —
   they contribute nothing to scoping. Special case: for `:root.y:has(...)`, only the `:has(...)`
   part is kept, because `.y` is unscoped but the contents of `:has()` must still be scoped.
2. If the owning rule is nested and no explicit `&` appears anywhere (including inside
   `:is` / `:has` / `:where`), a synthetic `nesting_selector` (`&`) plus a descendant combinator is
   prepended, so matching climbs into the parent rule.

Two module-level constant nodes (`descendant_combinator`, `nesting_selector`, `any_selector`) are
reused for these synthetic insertions.

### `apply_selector` — the recursion core

```js
const relative_selector = direction === FORWARD ? rest.shift() : rest.pop();

const matched =
    !!relative_selector &&
    relative_selector_might_apply_to_node(relative_selector, rule, element, direction) &&
    apply_combinator(relative_selector, rest, rule, element, direction);

if (matched) {
    if (!is_outer_global(relative_selector)) relative_selector.metadata.scoped = true;
    element.metadata.scoped = true;
}
```

Note the deliberate asymmetry: `metadata.scoped` is **not** set for outer-global selectors
(`is_outer_global` — true even for `:global(x):has(y)`), because those must never get the hash
suffix, while the element itself still counts as scoped.

### `apply_combinator` — walking the template

| Combinator | Direction BACKWARD | Direction FORWARD |
| --- | --- | --- |
| `' '` (descendant) | `get_ancestor_elements(node, false)` | `get_descendant_elements(node, false)` |
| `>` (child) | nearest ancestor element only | immediate descendants only |
| `+` / `~` | `get_possible_element_siblings(..., BACKWARD, adjacent)` | same, forwards |
| anything else | assumed to match (`return true`) | same |

When walking backwards and no candidate exists (top of the component, or no parent at all), the
match still succeeds if every remaining selector is global — that is how `:global(.x) > p` matches
a `<p>` at the component root.

### Template traversal helpers

Because Svelte templates contain blocks, slots, components and snippets, "the parent element" is
not a simple parent pointer. These helpers resolve it:

```mermaid
graph TD
    GA["get_ancestor_elements"] -->|"walks metadata.path upwards"| SNIP1["SnippetBlock → recurse into<br/>every render site (metadata.sites)"]
    GD["get_descendant_elements"] -->|"walks fragment downwards"| SNIP2["RenderTag → recurse into<br/>metadata.snippets"]
    GS["get_possible_element_siblings"] --> BL["blocks (if/each/await/key/slot),<br/>Components, RenderTag, SvelteElement"]
    BL --> GNS["get_possible_nested_siblings<br/>(per-branch fragments)"]
    GNS --> LC["loop_child"]
    LC --> BL
    GS --> EX["existence: DEFINITELY vs PROBABLY"]
```

- **Existence tri-state.** A sibling found inside `{#if}` or a `<slot>` only *probably* exists, so
  it is recorded as `NODE_PROBABLY_EXISTS`; a plain element in the same fragment is
  `NODE_DEFINITELY_EXISTS`. `has_definite_elements` uses this to decide whether an adjacent-only
  search (`+`, `>`) may stop early. `add_to_map` / `higher_existence` merge maps keeping the
  stronger claim.
- **Non-exhaustive branches** (a missing `{:else}`, a `<slot>`, a snippet) downgrade every found
  sibling to `PROBABLY`.
- **Snippets and `{@render}`** are followed in both directions via `metadata.sites` /
  `metadata.snippets`, with a `seen` set guarding against cycles.
- **Slotted content** (`<x slot="...">`) is skipped when collecting siblings, since it is
  re-parented at render time.
- **`{#each}` bodies** feed their own nested siblings back in, because the last child of one
  iteration is the previous sibling of the first child of the next.

### `relative_selector_might_apply_to_node` — per-selector checks

The selectors of one relative selector are split into `:has(...)` selectors and everything else.

`:has(...)` first (it forces a downward, `FORWARD` search):

- `get_parent_rules(rule)` is used to decide `include_self` — inside a global or `:root` context
  (`:root:has(.x)`, `:global(.foo):has(.x)`) the element itself is a valid `:has` target.
- Each inner complex selector is tried both including self and excluding self (the latter by
  prefixing the synthetic `any_selector` + descendant combinator).
- If any `:has(...)` argument matches nothing, the whole relative selector fails.

Then the remaining simple selectors:

| Selector type | Rule |
| --- | --- |
| `PseudoClassSelector` `:host` / `:root` | never matches a component element → `false` |
| `:global(x)` alone in the relative selector | recurse into the argument with `apply_selector(..., BACKWARD)` |
| bare `:global` | everything beyond is global → `true` |
| `:not(...)` | contents force-marked `used` and left **unscoped** (scoping `:not` would make it bleed out); complex arguments with descendants pessimistically scope the whole ancestor chain |
| `:is(...)` / `:where(...)` | any matching argument marks that argument `used`; multi-part arguments are optimistically accepted and scoped |
| `PseudoElementSelector` | ignored (always passes) |
| `AttributeSelector` | `attribute_matches`, unless whitelisted (`details[open]`, `dialog[open]`) |
| `ClassSelector` | `attribute_matches(element, 'class', name, '~=')` |
| `IdSelector` | `attribute_matches(element, 'id', name, '=')` |
| `TypeSelector` | tag name compare; `*` and `<svelte:element>` always pass |
| `NestingSelector` (`&`) | try every complex selector of the parent rule; also succeeds if the parent is entirely global |
| `Percentage` / `Nth` | skipped |

The bias is deliberately **optimistic**: when the algorithm cannot prove a mismatch it returns
`true`. A false positive only means a missed prune (extra CSS shipped); a false negative would mean
a wrongly deleted style plus a bogus "unused selector" warning.

### Attribute matching and `get_possible_values`

`attribute_matches` has to reason about attributes whose value is dynamic.

```mermaid
graph TD
    AM["attribute_matches(node, name, expected, op, ci)"]
    AM --> SP["SpreadAttribute → true (bail out)"]
    AM --> BD["bind: with same name → true"]
    AM --> SD["style: directive vs 'style' → true"]
    AM --> CD["class: directive vs 'class'<br/>~= compares directive name, else true"]
    AM --> TXT["static text value → test_attribute"]
    AM --> DYN["dynamic value"]
    DYN --> CHUNKS["get_attribute_chunks"]
    CHUNKS --> GPV["get_possible_values(chunk, is_class)"]
    GPV --> COMBINE["cross-product of chunk values<br/>(whitespace-aware, bails past 20)"]
    COMBINE --> TA["test_attribute per candidate"]
```

`get_possible_values` (in `utils.js`) walks the expression and enumerates every string the chunk
could produce:

- `Literal` → its string value.
- `ConditionalExpression` → both branches.
- `LogicalExpression`: `||` / `??` → both sides; `&&` → the right side plus only the *falsy*
  possibilities of the left side (so `class={[cond && 'blah']}` does not deopt on `cond`).
- With `is_class`, `ArrayExpression` elements and `ObjectExpression` keys are enumerated too,
  matching the `clsx`-style class attribute handling.
- Anything else adds the internal `UNKNOWN` sentinel; if `UNKNOWN` is present the function returns
  `null`, which callers read as "could be anything" → match.

`test_attribute` implements the CSS operators `=`, `~=`, `|=`, `^=`, `$=`, `*=` with optional
case-insensitivity (the `i` flag).

### Globalness inside `prune`

`css-prune.js` has its own, *rule-aware* `is_global(selector, rule)` — distinct from the
`utils.is_global(relative_selector)` used by `analyze_css`. It additionally resolves:

- `:is(...)` / `:where(...)` whose every argument is global,
- `&` (`NestingSelector`), by recursing into the parent rule's prelude.

This is the predicate behind "matching may end early if the rest is global".

---

## Stage 3 — `warn_unused`

A short walk that reports whatever `prune` never touched:

```js
ComplexSelector(node, context) {
    if (!node.metadata.used && /* not a nested duplicate */ …) {
        const text = /* original source slice */;
        w.css_unused_selector(node, text);
    }
    context.next();
}
```

Skip rules that keep the noise down:

- `Atrule`: keyframes bodies are not descended into (percentage selectors are not selectors).
- `PseudoClassSelector`: only `:is` / `:where` are descended into.
- `Rule`: for a `:global {}` block only the prelude is visited — the declarations inside are global
  by definition.
- The duplicate guard in `ComplexSelector` prevents `.unused:is(.unused)` from being reported twice:
  an inner selector is only reported if its outer selector *was* used.

The warning text is sliced out of `stylesheet.content.styles` using the node offsets relative to
`content.start`, so the message shows the selector exactly as written.

See [compiler_options_and_warnings](compiler_options_and_warnings.md) for the warning definition,
and note that `analyze_component` skips this stage entirely when the style block carries
`<!-- svelte-ignore css_unused_selector -->`.

---

## End-to-end data flow

```mermaid
flowchart TD
    START["root.css (AST.CSS.StyleSheet)"] --> AZ

    subgraph AZ["analyze_css"]
        AZ1["Rule: parent_rule, is_global_block,<br/>has_global/local_selectors"]
        AZ2["ComplexSelector: rule, is_global, used"]
        AZ3["RelativeSelector: is_global, is_global_like"]
        AZ4["errors on invalid :global / &"]
        AZ5["analysis.css.keyframes<br/>analysis.css.has_global"]
    end

    AZ --> LOOP{"for each element<br/>in analysis.elements"}
    LOOP --> PR

    subgraph PR["prune(stylesheet, element)"]
        PR1["truncate + inject &"]
        PR2["apply_selector BACKWARD"]
        PR3["combinators → ancestors /<br/>descendants / siblings"]
        PR4[":has → FORWARD sub-match"]
        PR5["attribute / class / id / type checks"]
    end

    PR -->|"match"| MARK["ComplexSelector.used = true<br/>RelativeSelector.scoped = true<br/>element.metadata.scoped = true"]
    LOOP --> WU

    subgraph WU["warn_unused"]
        WU1["report every unused ComplexSelector"]
    end

    MARK --> TR
    AZ5 --> TR

    subgraph TR["compiler_css_transform"]
        TR1["append .hash to scoped selectors"]
        TR2["strip :global(...) wrappers"]
        TR3["rename local @keyframes"]
        TR4["drop unused rules"]
    end

    MARK --> EL["client / server transforms:<br/>add class attribute to scoped elements"]
    TR --> RESULT["CompileResult.css"]
```

`analyze_component` also uses `element.metadata.scoped` right after pruning: for a scoped element
without a `class` attribute it synthesises an empty `class=""`, so the transform phase has
somewhere to write the hash. Custom elements that end up scoped additionally trigger
`mark_subtree_dynamic`.

---

## Component interaction summary

```mermaid
graph LR
    subgraph mod["compiler_analyze_css"]
        CA["css-analyze.js<br/>analyze_css"]
        CP["css-prune.js<br/>prune"]
        CW["css-warn.js<br/>warn_unused"]
        U["utils.js"]
    end

    ZF["zimmerframe walk"] --- CA
    ZF --- CP
    ZF --- CW

    CA --> U
    CP --> U

    CA --> ERR["errors.js (css_* errors)"]
    CW --> WARN["warnings.js (css_unused_selector)"]
    CA --> KF["phases/css.js<br/>is_keyframes_node"]
    CW --> KF
    CP --> AST["utils/ast.js<br/>get_attribute_chunks, is_text_attribute"]
    CP --> PAT["phases/patterns.js<br/>whitespace regexes"]
```

| Consumer | What it reads |
| --- | --- |
| `render_stylesheet` ([compiler_css_transform](compiler_css_transform.md)) | `used`, `scoped`, `is_global`, `is_global_block`, `keyframes`, `has_global` |
| `RegularElement` / `SvelteElement` visitors ([compiler_transform_client](compiler_transform_client.md), [compiler_transform_server](compiler_transform_server.md)) | `element.metadata.scoped` |
| `analyze_component` ([compiler_analyze](compiler_analyze.md)) | `element.metadata.scoped` for class/style attribute synthesis |
| `CompileResult.css.hasGlobal` ([compiler_api](compiler_api.md)) | `analysis.css.has_global` |

---

## Notes for maintainers

- **Two `is_global`s.** `utils.is_global(relative_selector)` is structural and used during analysis;
  `css-prune.js`'s private `is_global(selector, rule)` is rule-aware (resolves `&`, `:is`,
  `:where`). Also present: `is_outer_global`, which is looser — `:global(x):has(y)` is outer-global
  but not global. Picking the wrong one is the most common source of scoping bugs.
- **`prune` is O(elements × selectors).** Each call re-walks the whole stylesheet, and combinator
  handling recurses over the template. Complexity guards exist (`prev_values.length > 20` bail-out
  in `attribute_matches`, `seen` sets for snippets, `adjacent_only` early exits) — keep them when
  editing.
- **Module-level `seen` set.** `css-prune.js` declares one `seen` set at module scope and clears it
  at the start of each `ComplexSelector` visit. The traversal helpers otherwise take their own
  local `seen` defaults; do not conflate the two.
- **Flags are monotonic.** Almost everything is written with `||=`. `prune` runs once per element,
  so a selector used by *any* element stays used. Never reset these flags mid-phase.
- **Optimism is the contract.** When in doubt, return `true` / mark `used`. Being too strict emits
  false "unused selector" warnings and deletes working styles; being too loose only ships a little
  extra CSS.
- **`analyze_css` is the only stage that throws.** `prune` and `warn_unused` never error, which is
  why validation must be complete before pruning starts.
