# Engine Administration CLI Tools (Python)

## 1. Purpose

The **Engine Administration CLI Tools (Python)** module (`engine-suite`, located under `src/engine/tools`) is a collection of standalone Python command-line utilities used by administrators, integration developers, and CI/testing pipelines to operate, configure, and troubleshoot the **Wazuh Engine** (the C++ analysis/decoding core documented separately in *Wazuh_Engine_Core_(C++)*).

Rather than being a single monolithic program, this module is a **suite of thin CLI clients**, each dedicated to a specific engine resource or workflow:

- **Resource lifecycle management**: `engine_catalog` (decoders/rules/outputs/filters), `engine_policy` (policies, assets, namespaces), `engine_kvdb` (key-value databases), `engine_router` (routes, EPS throttling, event ingestion), `engine_geo` (GeoIP databases).
- **Bulk operations**: `engine_integration` (packages multiple assets/KVDBs as an installable "integration"), `engine_clear` (bulk-deletes engine resources across namespaces).
- **Diagnostics & testing**: `engine_test` (interactive/batch decoder testing via Tester sessions), `engine_diff` (compares expected vs actual event output).
- **Schema & content maintenance**: `engine_schema` (generates/pushes ECS-based field schemas, index templates, and logpar overrides), `engine_decoder` (inspects/refactors decoder YAML files on disk).
- **Operational control**: `engine_archiver` (toggles the engine's raw-event archiver on/off).
- **Shared infrastructure**: `engine_suite_shared` (common constants, YAML/JSON dumpers, transactional task executor, resource handler) and `engine_misc_tools` (the `APIClient` transport plus assorted developer utilities like `agent_simulator`, `engine_bench`, `compare_expected`, `evtx2xml`).

Most tools communicate with a **running `wazuh-engine` process** over a local Unix domain socket using a Protobuf-over-HTTP protocol (via the shared `APIClient`), while a few (`engine_decoder`, parts of `engine_test`/`update_expected.py`) operate directly on local files or spawn the engine binary for testing purposes.

## 2. Architecture

### 2.1 High-Level Composition

```mermaid
graph TB
    subgraph CLI["Engine Administration CLI Tools (engine-suite)"]
        CATALOG[engine_catalog]
        POLICY[engine_policy]
        ROUTER[engine_router]
        KVDB[engine_kvdb]
        GEO[engine_geo]
        SCHEMA[engine_schema]
        INTEGRATION[engine_integration]
        TEST[engine_test]
        DIFF[engine_diff]
        ARCHIVER[engine_archiver]
        DECODER[engine_decoder]
        CLEAR[engine_clear]
        MISC[engine_misc_tools]
    end

    subgraph SHARED["Shared Infrastructure"]
        SS[engine_suite_shared<br/>ResourceHandler, Constants,<br/>Executor, EngineDumper]
        APICLIENT[APIClient<br/>api-communication package]
    end

    CATALOG --> SS
    POLICY --> SS
    ROUTER --> SS
    KVDB --> SS
    GEO --> SS
    SCHEMA --> SS
    INTEGRATION --> SS
    TEST --> SS
    DIFF --> SS
    ARCHIVER --> SS
    CLEAR --> SS

    CATALOG --> APICLIENT
    POLICY --> APICLIENT
    ROUTER --> APICLIENT
    KVDB --> APICLIENT
    GEO --> APICLIENT
    ARCHIVER --> APICLIENT
    CLEAR --> APICLIENT
    TEST --> APICLIENT
    INTEGRATION --> APICLIENT
    SCHEMA --> APICLIENT

    APICLIENT -->|Unix Domain Socket<br/>Protobuf/JSON| ENGINE[Wazuh Engine Process<br/>engine_api handlers]

    DECODER -.->|local file I/O only| FILES[(Decoder YAML files)]

    ENGINE --> CORE[Wazuh_Engine_Core_C++<br/>Catalog / Policy / Router /<br/>KVDB / Tester / Archiver]
```

### 2.2 Typical Request Flow (e.g., `engine-catalog create`)

```mermaid
sequenceDiagram
    participant User
    participant Main as __main__.py (argparse)
    participant Cmd as cmds/<verb>.py
    participant Client as APIClient
    participant Engine as Engine Daemon (C++)

    User->>Main: engine-<tool> <verb> [args]
    Main->>Main: parse_args() / build subparsers
    Main->>Cmd: args.func(vars(args))
    Cmd->>Cmd: build Protobuf *_Request message
    Cmd->>Client: send_recv(request) / jsend(request)
    Client->>Engine: serialize & POST over Unix socket
    Engine->>Engine: dispatch to registered API handler
    Engine-->>Client: serialized Protobuf response
    Client-->>Cmd: (error, response_dict)
    alt error or status == ERROR
        Cmd-->>User: sys.exit(error message)
    else success
        Cmd-->>User: print result (YAML/JSON) or exit 0
    end
```

### 2.3 Transactional Task Pattern (bulk operations)

Tools that mutate multiple resources atomically (`engine_integration`, parts of `engine_policy`) rely on a shared **do/undo task executor**:

```mermaid
sequenceDiagram
    participant Cmd as cmds/(add|update|delete).py
    participant Exec as Executor (shared)
    participant API as APIClient
    participant Engine as Engine Catalog/KVDB API

    Cmd->>Exec: add(RecoverableTask(do, undo, description))
    Cmd->>Exec: execute(dry_run)
    loop for each task in order
        Exec->>API: task.do()
        alt failure
            Exec->>API: undo() for previously succeeded tasks (reverse order)
            Exec-->>Cmd: abort
        end
    end
    Exec-->>Cmd: done
```

### 2.4 Sub-module Breakdown

```mermaid
graph LR
    subgraph Resource_CLIs["Resource Management CLIs"]
        A[engine_archiver]
        B[engine_catalog]
        C[engine_policy]
        D[engine_router]
    end
    subgraph Bulk_Diagnostic["Bulk & Diagnostic CLIs"]
        E[engine_integration]
        F[engine_clear]
        G[engine_test]
        H[engine_diff]
        I[engine_decoder]
    end
    subgraph Schema_Misc["Schema & Misc"]
        J[engine_schema]
        K[engine_misc_tools]
    end
    subgraph Foundation["Foundation"]
        L[engine_suite_shared]
    end

    Resource_CLIs --> L
    Bulk_Diagnostic --> L
    Schema_Misc --> L
    E -.reuses request contracts of.-> B
    E -.reuses request contracts of.-> K
    F -.reuses request contracts of.-> B
    F -.reuses request contracts of.-> C
    F -.reuses request contracts of.-> D
    F -.reuses request contracts of.-> G
```

## 3. Core Components & References

| Sub-module | Responsibility | Documentation |
|---|---|---|
| `engine_archiver` | Activate/deactivate/query the engine's raw-event archiver | [engine_archiver.md](engine_archiver.md) |
| `engine_catalog` | CRUD + validate operations on catalog assets (decoders, rules, outputs, filters, integrations) | [engine_catalog.md](engine_catalog.md) |
| `engine_clear` | Bulk-discovers and deletes routes, sessions, policies, KVDBs, and catalog assets | [engine_clear.md](engine_clear.md) |
| `engine_decoder` | Inspects extracted fields and bulk-renames helper functions in local decoder YAML files | [engine_decoder.md](engine_decoder.md) |
| `engine_diff` | Compares two JSON/YAML event documents and reports differences | [engine_diff.md](engine_diff.md) |
| `engine_integration` | Packages/publishes/updates/removes multi-asset "integrations"; generates docs and dependency graphs | [engine_integration.md](engine_integration.md) |
| `engine_policy` | Manages policy lifecycle, asset attachment, namespace/default-parent hierarchy | [engine_policy_store.md](engine_policy_store.md), [engine_policy_assets.md](engine_policy_assets.md), [engine_policy_hierarchy.md](engine_policy_hierarchy.md) |
| `engine_router` | Manages routes, routing table inspection, manual event ingestion, EPS throttling | [engine_router.md](engine_router.md) |
| `engine_schema` | Generates/pushes ECS-based schemas, indexer templates, and logpar overrides | [engine_schema_cli.md](engine_schema_cli.md), [engine_schema_field_model.md](engine_schema_field_model.md) |
| `engine_test` | Interactive/batch testing of decoders/rules via engine Tester sessions | [engine_test_cli.md](engine_test_cli.md), [engine_test_session_cli.md](engine_test_session_cli.md), [engine_test_config.md](engine_test_config.md), [engine_test_execution.md](engine_test_execution.md), [engine_test_splitters.md](engine_test_splitters.md) |
| `engine_suite_shared` | Shared constants, YAML/JSON dumpers, `Executor`/`RecoverableTask`, `ResourceHandler` | [engine_suite_shared.md](engine_suite_shared.md) |
| `engine_misc_tools` | `APIClient` transport, agent simulator, benchmarking, expected-output comparison/flattening, EVTX conversion | [engine_misc_tools.md](engine_misc_tools.md) |

### Related External Modules

- [Wazuh_Engine_Core_(C++)](Wazuh_Engine_Core_(C++).md) — the C++ engine process these CLIs administer (`engine_api`, `builder_policy`, `Router`, `engine_kvdb`, `Store`, `Schemf`).
- [engine_geo](engine_geo_cli.md) / [engine_kvdb](engine_kvdb_cli.md) — sibling CLI tools following the identical `argparse` + `APIClient` pattern (documented alongside the C++ engine module tree).