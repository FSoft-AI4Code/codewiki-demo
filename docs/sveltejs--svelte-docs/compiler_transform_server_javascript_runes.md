# compiler_transform_server_javascript_runes

## Introduction

Runes (`$state`, `$derived`, `$effect`, `$inspect`, `$host`, …) are the reactivity primitives of Svelte 5. On the client they compile into live signals. On the server there is **no reactivity at all** — a component is rendered once into a string and thrown away.

This module is the part of the server (SSR) transform that deals with that mismatch. It walks the JavaScript inside `<script>` blocks and inside template expressions, and rewrites every rune call into something that makes sense for a one-shot render:

- values are **unwrapped** (`$state(x)` becomes plain `x`),
- side effects are **deleted** (`$effect(...)` becomes nothing),
- a few runes are replaced with **tiny server stubs** (`$.derived`, `$.snapshot`, `$.inspect`),
- `await` in the wrong place becomes a **runtime error call**.

It also enforces one rule that has no client equivalent: a blocking `await` in the component body cannot be rendered on the server, because there is no `<svelte:boundary>` pending state to fall back to.

This module is a leaf of [compiler_transform_server_javascript](compiler_transform_server_javascript.md), which itself is part of [compiler_transform_server](compiler_transform_server.md).

---

## Core components

| Component | File | Role |
| --- | --- | --- |
| `CallExpression` | `server/visitors/CallExpression.js` | Rewrites rune calls used as **expressions** |
| `ExpressionStatement` | `server/visitors/ExpressionStatement.js` | Deletes rune calls used as **statements** |
| `AwaitExpression` | `server/visitors/AwaitExpression.js` | Guards `await` outside a function |
| `transform_inspect_rune` | `3-transform/utils.js` | Shared `$inspect` / `$inspect().with` lowering |
| `get_rune` | `phases/scope.js` | Decides whether a call *is* a rune (scope aware) |

---

## Where the module sits

```mermaid
graph TD
    subgraph pipeline["Compilation pipeline"]
        P["1-parse<br/>compiler_parse"] --> A["2-analyze<br/>compiler_analyze"]
        A --> T["3-transform"]
    end

    subgraph T3["3-transform"]
        C["client<br/>compiler_transform_client"]
        S["server<br/>compiler_transform_server"]
    end

    T --> T3
    S --> SC["server core<br/>transform-server.js"]
    SC --> GV["global_visitors<br/>(JS everywhere)"]
    SC --> TV["template_visitors<br/>(markup)"]

    GV --> RUNES["compiler_transform_server_javascript_runes<br/><b>this module</b>"]
    GV --> DECL["…_declarations"]
    GV --> CLS["…_classes"]
    GV --> STO["…_stores"]

    RUNES --> OUT["$.derived / $.snapshot / $.inspect<br/>server_runtime"]

    style RUNES fill:#ff9800,color:#000
```

`global_visitors` in `transform-server.js` is a flat map of AST node type → visitor. `CallExpression`, `ExpressionStatement` and `AwaitExpression` are registered there, so they fire for **every** JavaScript expression in the component: module script, instance script, and every `{expression}` in the markup. See [compiler_transform_server_core](compiler_transform_server_core.md) for how the visitor map is assembled and driven.

---

## Dependencies

```mermaid
graph LR
    CE["CallExpression"]
    ES["ExpressionStatement"]
    AE["AwaitExpression"]

    GR["get_rune<br/>phases/scope.js"]
    TIR["transform_inspect_rune<br/>3-transform/utils.js"]
    B["builders (b.*)<br/>utils/builders.js"]
    ST["is_ignored / dev<br/>compiler/state.js"]
    SCOPE["Scope<br/>function_depth"]

    CE --> GR
    CE --> TIR
    CE --> B
    CE --> ST
    ES --> GR
    ES --> B
    AE --> B
    AE --> SCOPE
    TIR --> B
    TIR --> ST
    GR --> SCOPE

    style CE fill:#ff9800,color:#000
    style ES fill:#ff9800,color:#000
    style AE fill:#ff9800,color:#000
```

- `get_rune` and `Scope` come from [compiler_core](compiler_core.md) (`phases/scope.js`).
- `b.*` builders (`b.call`, `b.thunk`, `b.arrow`, `b.literal`, `b.empty`, `b.void0`, …) also come from [compiler_core](compiler_core.md).
- `is_ignored` and `dev` come from the compiler-wide state module (`compiler/state.js`).
- The emitted `$.` helpers live in [server_runtime](server_runtime.md) (`svelte/internal/server`), imported once as `import * as $ from 'svelte/internal/server'` by the server core.

---

## Rune → server output

### Expression position (`CallExpression`)

| Source | Server output | Why |
| --- | --- | --- |
| `$host()` | `void 0` | No custom element host during SSR |
| `$effect.tracking()` | `false` | Nothing is ever tracked |
| `$effect.root(fn)` | `() => {}` | Only the cleanup function shape is kept |
| `$effect.pending()` | `0` | No pending async work |
| `$state(v)` / `$state.raw(v)` | `v` (visited) — or `void 0` if no arg | State is just a plain value |
| `$derived(expr)` | `$.derived(() => expr)` | Lazy, computed at most once |
| `$derived.by(fn)` | `$.derived(fn)` | `fn` is already a thunk |
| `$state.snapshot(v)` | `$.snapshot(v[, true])` | Deep clone; the extra `true` suppresses the `state_snapshot_uncloneable` warning when it is `svelte-ignore`d |
| `$inspect(...)` / `$inspect(...).with(fn)` | `$.inspect([...])` (dev only) | See below |
| anything else | `context.next()` | Not a rune → keep walking children |

`$.derived` in [server_runtime](server_runtime.md) is a `once()` wrapper: the thunk runs on first read and the value is memoised, so a `$derived` never recomputes during a single render.

The `$derived` vs `$derived.by` split matters: `$derived(a * 2)` receives an **expression**, so the visitor wraps it in `b.thunk(...)`; `$derived.by(() => a * 2)` already receives a **function**, so it is passed through unchanged.

### Statement position (`ExpressionStatement`)

| Source statement | Server output |
| --- | --- |
| `$effect(fn);` | *(removed)* |
| `$effect.pre(fn);` | *(removed)* |
| `$effect.root(fn);` | *(removed)* |
| `$inspect.trace();` | *(removed)* |
| anything else | `context.next()` |

`b.empty` is an empty statement, so the whole line — including its arguments — disappears from the SSR output. Nothing inside an effect body is ever visited, which is exactly right: effects only run in the browser.

Note that `$effect.root` is listed in **both** visitors. As a bare statement it is deleted outright; as an expression (`const stop = $effect.root(...)`) it must still produce *something* callable, so it becomes a noop arrow function.

### Runes handled elsewhere

`$props()`, `$props.id()`, `$bindable()` and `$derived` **declarations** are not rewritten here — they are handled where the variable is declared, in [compiler_transform_server_javascript_declarations](compiler_transform_server_javascript_declarations.md). Class field runes (`$state` inside a class body) are handled by [compiler_transform_server_javascript_classes](compiler_transform_server_javascript_classes.md). Reading a `$derived` variable back is handled by [compiler_transform_server_javascript_stores](compiler_transform_server_javascript_stores.md) via `build_getter`.

---

## How a rune is recognised

`get_rune` is what stops the transform from mangling user code that merely *looks* like a rune.

```mermaid
flowchart TD
    START["node"] --> ISCALL{"is a CallExpression?"}
    ISCALL -- no --> NULL["return null"]
    ISCALL -- yes --> KP["get_global_keypath(callee)"]
    KP --> WALK["walk MemberExpression chain<br/>$inspect().with → '$inspect().with'"]
    WALK --> COMPUTED{"computed member<br/>or non-Identifier?"}
    COMPUTED -- yes --> NULL
    COMPUTED -- no --> BIND{"root identifier declared<br/>in any enclosing scope?"}
    BIND -- yes --> NULL
    BIND -- no --> ISRUNE{"is_rune(keypath)?"}
    ISRUNE -- no --> NULL
    ISRUNE -- yes --> NAME["return '$state' / '$derived' / …"]

    style NAME fill:#4caf50,color:#000
```

Two consequences worth remembering:

1. **Shadowing wins.** If the user writes `import { $state } from './x.js'` or `let $host = ...`, the scope lookup finds a binding and `get_rune` returns `null` — the call is left alone.
2. **Keypaths are joined literally**, including the call in the middle: `$inspect(x).with(fn)` becomes the keypath string `"$inspect().with"`, which is why `CallExpression` matches that exact string.

---

## Control flow inside `CallExpression`

```mermaid
flowchart TD
    IN["CallExpression node"] --> R["rune = get_rune(node, scope)"]

    R --> C1{"$host"}
    C1 -- yes --> O1["b.void0"]
    C1 -- no --> C2{"$effect.tracking"}
    C2 -- yes --> O2["b.false"]
    C2 -- no --> C3{"$effect.root"}
    C3 -- yes --> O3["b.arrow([], b.block([]))"]
    C3 -- no --> C4{"$effect.pending"}
    C4 -- yes --> O4["b.literal(0)"]
    C4 -- no --> C5{"$state / $state.raw"}
    C5 -- yes --> O5["visit(arg0) ?? void 0"]
    C5 -- no --> C6{"$derived / $derived.by"}
    C6 -- yes --> O6["$.derived(thunk? fn : fn)"]
    C6 -- no --> C7{"$state.snapshot"}
    C7 -- yes --> O7["$.snapshot(visit(arg0), ignored?)"]
    C7 -- no --> C8{"$inspect / $inspect().with"}
    C8 -- yes --> O8["transform_inspect_rune"]
    C8 -- no --> NEXT["context.next()<br/>(normal call — visit children)"]

    style NEXT fill:#90caf9,color:#000
```

Every branch that returns a node **replaces** the original call and, importantly, does *not* call `context.next()` — so children are only visited when the visitor explicitly does so (`context.visit(node.arguments[0])`). This is how `$effect` bodies get skipped while `$derived` bodies still get transformed.

---

## `$inspect` — `transform_inspect_rune`

`transform_inspect_rune` lives in the shared `3-transform/utils.js` because both the client and the server transform use it. The single behavioural difference is the `as_fn` flag, derived from `state.options.generate`.

```mermaid
flowchart TD
    IN["$inspect(...) node"] --> DEV{"dev mode?"}
    DEV -- no --> EMPTY["b.empty<br/>(inspect vanishes in prod)"]
    DEV -- yes --> FORM{"callee is MemberExpression?<br/>i.e. $inspect(...).with(fn)"}

    FORM -- yes --> W1["inspect_args = visit(callee.object.arguments)"]
    W1 --> W2["with_arg = visit(node.arguments[0])"]
    W2 --> W3["$.inspect(args, with_arg)"]

    FORM -- no --> N1["args = visit(node.arguments)"]
    N1 --> N2["$.inspect(args)"]

    W3 --> WRAP{"generate === 'client'?"}
    N2 --> WRAP
    WRAP -- yes --> THUNK["args wrapped in a thunk<br/>(re-read on every change)"]
    WRAP -- no --> ARR["args passed as a plain array<br/><b>server path</b>"]

    style ARR fill:#ff9800,color:#000
    style EMPTY fill:#e0e0e0,color:#000
```

On the server, `$.inspect(args)` in [server_runtime](server_runtime.md) simply does `console.log('init', ...args)` once — there are no subsequent updates to report. In production builds the whole call is erased, so `$inspect` costs nothing.

`$inspect.trace()` never reaches here: it is only ever a statement, and `ExpressionStatement` removes it first.

---

## `AwaitExpression` — the boundary guard

Async Svelte lets you `await` directly in the component body. On the client that suspends inside the nearest `<svelte:boundary>` with a `pending` snippet. On the server there is no such mechanism, so the compiler emits a call that throws at render time.

```mermaid
flowchart TD
    IN["await expr"] --> Q1{"scope.function_depth === 0?<br/>(top level of &lt;script module&gt;)"}
    Q1 -- yes --> OK["context.next()<br/>keep the await"]
    Q1 -- no --> Q2{"any ancestor in path is<br/>Arrow / Function decl / Function expr?"}
    Q2 -- yes --> OK
    Q2 -- no --> ERR["$.await_outside_boundary()"]

    style OK fill:#4caf50,color:#000
    style ERR fill:#f44336,color:#fff
```

- **`function_depth === 0`** identifies the module scope. Top-level `await` in `<script module>` runs once when the module is imported, which is fine on the server.
- **An enclosing function** means the `await` only runs when that function is called — also fine.
- Anything else is a component-body `await`, and is replaced by `$.await_outside_boundary()` from `internal/shared/errors.js`, which throws `Cannot await outside a <svelte:boundary> with a pending snippet`.

Note the replacement swallows the awaited expression: the whole `await x` node becomes the error call, so `x` is never evaluated.

Compare with the client path, where `await` is compiled into real suspension machinery — see [compiler_transform_client_javascript](compiler_transform_client_javascript.md) and [client_blocks](client_blocks.md).

---

## End-to-end example

Input component:

```svelte
<script>
  let count = $state(0);
  let doubled = $derived(count * 2);

  $effect(() => {
    console.log('only in the browser');
  });

  $inspect(count);
</script>

<p>{doubled}</p>
```

What this module contributes to the SSR output:

```js
let count = 0;                            // $state unwrapped
let doubled = $.derived(() => count * 2); // lazy, memoised
                                          // $effect statement removed entirely
$.inspect([count]);                       // dev only, plain array (no thunk)
```

Declaration handling (`let count = ...`) and reading `doubled` back through a getter belong to the sibling modules linked above; this module is responsible only for the right-hand sides and the deleted statement.

---

## Interaction sequence

```mermaid
sequenceDiagram
    participant Core as transform-server.js<br/>(compiler_transform_server_core)
    participant Walk as zimmerframe walk
    participant CE as CallExpression
    participant GR as get_rune (scope.js)
    participant TIR as transform_inspect_rune
    participant B as builders

    Core->>Walk: walk(ast, state, global_visitors)
    Walk->>CE: visit CallExpression node
    CE->>GR: get_rune(node, state.scope)
    GR->>GR: build keypath, check scope bindings
    GR-->>CE: returns '$derived', '$inspect', or null

    alt rune is $derived
        CE->>Walk: context.visit(arguments[0])
        Walk-->>CE: transformed expression
        CE->>B: b.call('$.derived', b.thunk(expr))
        B-->>CE: new node
        CE-->>Walk: replacement node
    else rune is $inspect
        CE->>TIR: transform_inspect_rune(node, context)
        TIR->>B: b.call('$.inspect', b.array(args))
        TIR-->>CE: new node
        CE-->>Walk: replacement node
    else not a rune
        CE->>Walk: context.next()
    end
```

---

## Design notes

**Why replace instead of erase for `$derived`?** A `$derived` value may be read many times in a template, and its expression may be expensive or have observable ordering. `$.derived` memoises with `once()`, giving "compute at most once, only if read" — the closest server analogue of a lazy signal.

**Why do effects disappear rather than run once?** Effects are explicitly documented as browser-only. Running them during SSR would produce output that hydration cannot reproduce, and would frequently touch DOM APIs that do not exist.

**Why is `$state` a plain unwrap?** SSR has no mutation-after-render phase, so proxying would only cost time. The client transform, by contrast, wraps state in proxies — see [compiler_transform_client_javascript](compiler_transform_client_javascript.md).

**Why is the rune check scope-aware?** Rune names are not reserved words. `get_rune` returning `null` for any shadowed identifier means user code that happens to define `$state` keeps working, and the compiler never silently rewrites a normal function call.

---

## Related modules

- [compiler_transform_server_javascript](compiler_transform_server_javascript.md) — parent module, all JS visitors of the server transform
- [compiler_transform_server_javascript_declarations](compiler_transform_server_javascript_declarations.md) — `$props`, `$bindable`, `$derived` declarations
- [compiler_transform_server_javascript_classes](compiler_transform_server_javascript_classes.md) — rune fields in class bodies
- [compiler_transform_server_javascript_stores](compiler_transform_server_javascript_stores.md) — store access, assignments, `build_getter`
- [compiler_transform_server_core](compiler_transform_server_core.md) — visitor map, program assembly, `ServerTransformState`
- [compiler_transform_client_javascript](compiler_transform_client_javascript.md) — the client counterpart of the same runes
- [compiler_core](compiler_core.md) — `Scope`, `get_rune`, AST builders
- [server_runtime](server_runtime.md) — `$.derived`, `$.snapshot`, `$.inspect`, `$.await_outside_boundary`
- [compiler_analyze](compiler_analyze.md) — rune validation that runs before this transform
