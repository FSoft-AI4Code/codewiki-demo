# Legacy Compatibility and Migration

The `legacy_compatibility_and_migration` module preserves Svelte 3/4 compatibility while enabling migration to Svelte 5. It combines:

- `compiler_migrate`: best-effort Svelte 4 → Svelte 5 source rewriting.
- `compiler_legacy_ast_types`: TypeScript contracts for legacy template and CSS AST nodes.
- `legacy_compat`: client and server runtime adapters for the Svelte 4 component API, lifecycle, events, stores, and modifiers.

## Architecture

```mermaid
flowchart LR
    SOURCE["Legacy Svelte source"] --> PARSE["Compiler parsing and analysis"]
    PARSE --> MIGRATE["compiler_migrate"]
    AST["compiler_legacy_ast_types"] -. describes legacy node shapes .-> PARSE
    AST -. supports traversal .-> MIGRATE
    MIGRATE --> MODERN["Svelte 5 source"]

    MODERN --> TRANSFORM["Client/server compiler transforms"]
    TRANSFORM --> COMPAT["legacy_compat"]
    COMPAT --> CLIENT["Svelte 4 client API"]
    COMPAT --> SERVER["Svelte 4 SSR API"]
    COMPAT --> RUNTIME["Client/server runtime primitives"]
```

### Source migration flow

```mermaid
sequenceDiagram
    participant User as Legacy source
    participant M as compiler_migrate
    participant P as Parse/analyze phases
    participant W as AST visitors
    participant E as MagicString

    User->>M: migrate(source, options)
    M->>P: Parse and analyze component
    P-->>M: AST, scopes, bindings, metadata
    M->>W: Walk instance script and template
    W->>E: Apply rune, prop, event, slot, and component edits
    M->>E: Restore and migrate CSS
    E-->>User: Migrated source
    M-->>User: @migration-task comments when manual work is required
```

### Runtime compatibility flow

```mermaid
flowchart TD
    LEGACY["Svelte 4 component usage"] --> WRAPPER["createClassComponent / asClassComponent"]
    WRAPPER --> MOUNT["mount or hydrate"]
    WRAPPER --> API["$set / $on / $destroy"]
    API --> SIGNALS["Prop signals and legacy effects"]
    SIGNALS --> COMPONENT["Svelte 5 component"]
    EVENTS["DOM and component events"] --> BUBBLE["Bubbling and handlers"]
    BUBBLE --> API
    SSR["SSR entry point"] --> RENDER["component.render()"]
```

## Core component references

| Area | Documentation |
|---|---|
| Compiler phase ordering | [compilation_pipeline](compilation_pipeline.md) |
| Parsing and AST construction | [compiler_parse](compiler_parse.md) |
| Semantic analysis and scopes | [compiler_analyze](compiler_analyze.md) |
| Compiler state and shared helpers | [compiler_core](compiler_core.md) |
| Modern AST declarations | [compiler_ast_types](compiler_ast_types.md) |
| Migration source rewriter | [compiler_migrate](compiler_migrate.md) |
| Legacy AST contracts | [compiler_legacy_ast_types](compiler_legacy_ast_types.md) |
| Runtime compatibility bridge | [legacy_compat](legacy_compat.md) |
| Client compatibility generation | [compiler_transform_client](compiler_transform_client.md) |
| Server compatibility generation | [compiler_transform_server_core](compiler_transform_server_core.md) |
| Client reactivity runtime | [client_reactivity](client_reactivity.md) |
| Client rendering runtime | [client_render_and_templates](client_render_and_templates.md) |
| Server rendering runtime | [server_runtime](server_runtime.md) |