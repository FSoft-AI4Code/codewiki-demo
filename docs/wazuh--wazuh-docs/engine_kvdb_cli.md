# engine_kvdb_cli

## Introduction

`engine_kvdb_cli` is the Python command-line front-end for managing the Wazuh Engine's **Key-Value Database (KVDB)** subsystem. It provides the `engine-kvdb` executable, an argparse-based tool that lets administrators, integration developers, and automation scripts create, delete, inspect, and mutate KVDB instances and their key-value entries without writing code against the Engine's native API.

The tool does not implement any database logic itself. Instead, it is a thin, well-structured client that:

1. Parses CLI arguments into subcommands (`list`, `create`, `delete`, `dump`, `get`, `search`, `remove`, `upsert`).
2. Builds Protocol Buffer request messages defined by the Engine API contract (`api_communication.proto.kvdb_pb2`).
3. Sends those requests over a Unix domain socket to the running `wazuh-engine` process using the shared `APIClient`.
4. Parses/validates the Protobuf response and renders the result as human-readable YAML or JSON.

This module is the CLI counterpart to the C++ KVDB engine core (`engine_kvdb_cpp_core`), which implements the actual on-disk RocksDB-backed key-value storage and exposes it through the Engine's internal API handlers.

---

## Purpose and Core Functionality

| Responsibility | Description |
|---|---|
| **Database (manager) lifecycle** | `manager_list`, `manager_create`, `manager_delete`, `manager_dump` — create/enumerate/remove named KVDB instances and dump their full contents. |
| **Entry-level operations** | `db_get`, `db_search`, `db_remove`, `db_upsert` — read, prefix-search, delete, and insert/update individual key-value pairs within a named database. |
| **API transport** | Delegates all socket I/O, request/response (de)serialization, and error normalization to the shared `APIClient` (`engine_misc_tools`/`engine_suite_shared` ecosystem). |
| **Output formatting** | Uses the shared `EngineDumper`/`dict_to_str_yml`/`dict_to_str_json` helpers (see `engine_suite_shared`) to render Protobuf responses as YAML (default) or JSON (`-j/--json` flag), including pagination and an "as object" export mode for `search`/`dump`. |

Because the CLI is a pure client, its "business logic" is limited to:
- Argument validation (e.g., pagination `page`/`page_size` must be provided together, JSON value parsing for `upsert`).
- Translating CLI flags into Protobuf request fields.
- Translating Protobuf/JSON error responses into actionable CLI error messages and non-zero exit codes.

---

## Architecture Overview

```mermaid
graph TB
    subgraph "engine_kvdb_cli (this module)"
        MAIN["__main__.py::main<br/>argparse entrypoint"]
        subgraph "cmds/"
            ML["manager_list.py"]
            MC["manager_create.py"]
            MD["manager_delete.py"]
            MDU["manager_dump.py"]
            GET["db_get.py"]
            SEARCH["db_search.py"]
            REMOVE["db_remove.py"]
            UPSERT["db_upsert.py"]
        end
        MAIN --> ML
        MAIN --> MC
        MAIN --> MD
        MAIN --> MDU
        MAIN --> GET
        MAIN --> SEARCH
        MAIN --> REMOVE
        MAIN --> UPSERT
    end

    subgraph "engine_suite_shared"
        CONST["default_settings.Constants<br/>(SOCKET_PATH default)"]
        DUMP["dumpers.py<br/>dict_to_str_yml / dict_to_str_json / EngineDumper"]
    end

    subgraph "engine_misc_tools"
        APICLIENT["api_communication.client.APIClient"]
    end

    ML --> APICLIENT
    MC --> APICLIENT
    MD --> APICLIENT
    MDU --> APICLIENT
    GET --> APICLIENT
    SEARCH --> APICLIENT
    REMOVE --> APICLIENT
    UPSERT --> APICLIENT

    ML --> DUMP
    MDU --> DUMP
    GET --> DUMP
    SEARCH --> DUMP
    MAIN --> CONST

    APICLIENT -- "Unix Domain Socket<br/>HTTP over UDS" --> ENGINE["wazuh-engine process<br/>Engine API (kvdb handlers)"]
    ENGINE --> KVDBCORE["engine_kvdb_cpp_core<br/>KVDBManager / KVDBHandler<br/>(RocksDB storage)"]
```

For details on the native storage layer that ultimately services these requests, see [engine_kvdb_cpp_core.md](engine_kvdb_cpp_core.md) and the broader [Wazuh_Engine_Core_(C++).md](Wazuh_Engine_Core_(C++).md) for the `api/kvdb` request handlers (`registerHandlers`).

---

## Component Relationships

```mermaid
classDiagram
    class main {
        +parse_args() Namespace
        +main() void
    }

    class manager_list_cmd {
        +configure(subparsers)
        +run(args) int
    }
    class manager_create_cmd {
        +configure(subparsers)
        +run(args) int
    }
    class manager_delete_cmd {
        +configure(subparsers)
        +run(args) int
    }
    class manager_dump_cmd {
        +configure(subparsers)
        +run(args) int
        +export_as_object(entries) dict
    }
    class db_get_cmd {
        +configure(subparsers)
        +run(args) int
    }
    class db_search_cmd {
        +configure(subparsers)
        +run(args) int
        +export_as_object(entries) dict
    }
    class db_remove_cmd {
        +configure(subparsers)
        +run(args) int
    }
    class db_upsert_cmd {
        +configure(subparsers)
        +run(args) int
    }

    class APIClient {
        +send_recv(message) tuple
        +send(reqProtoMsg, resProtoMsg) tuple
        +jsend(json_body, reqProtoMsg, resProtoMsg) tuple
    }

    class Constants {
        +SOCKET_PATH
        +DEFAULT_POLICY
    }

    class dumpers {
        +dict_to_str_yml(data) str
        +dict_to_str_json(data, pretty) str
    }

    main --> manager_list_cmd : configures
    main --> manager_create_cmd : configures
    main --> manager_delete_cmd : configures
    main --> manager_dump_cmd : configures
    main --> db_get_cmd : configures
    main --> db_search_cmd : configures
    main --> db_remove_cmd : configures
    main --> db_upsert_cmd : configures
    main --> Constants : uses default socket

    manager_list_cmd ..> APIClient : uses
    manager_create_cmd ..> APIClient : uses
    manager_delete_cmd ..> APIClient : uses
    manager_dump_cmd ..> APIClient : uses
    db_get_cmd ..> APIClient : uses
    db_search_cmd ..> APIClient : uses
    db_remove_cmd ..> APIClient : uses
    db_upsert_cmd ..> APIClient : uses

    manager_list_cmd ..> dumpers : formats output
    manager_dump_cmd ..> dumpers : formats output
    db_get_cmd ..> dumpers : formats output
    db_search_cmd ..> dumpers : formats output
```

---

## Command Reference

| Subcommand | File | Protobuf Request | Protobuf Response | Purpose |
|---|---|---|---|---|
| `list` | `manager_list.py` | `ekvdb.managerGet_Request` | `ekvdb.managerGet_Response` | Lists all KVDB instances known to the engine. |
| `create` | `manager_create.py` | `ekvdb.managerPost_Request` | `engine.GenericStatus_Response` | Creates a new named KVDB, optionally seeded from a server-side file path. |
| `delete` | `manager_delete.py` | `ekvdb.managerDelete_Request` | `engine.GenericStatus_Response` | Deletes a named KVDB instance. |
| `dump` | `manager_dump.py` | `ekvdb.managerDump_Request` | `ekvdb.managerDump_Response` | Dumps all entries of a KVDB, with optional pagination and object/YAML/JSON export. |
| `get` | `db_get.py` | `ekvdb.dbGet_Request` | `ekvdb.dbGet_Response` | Retrieves the value for a specific key. |
| `search` | `db_search.py` | `ekvdb.dbSearch_Request` | `ekvdb.dbSearch_Response` | Searches entries by key prefix, with optional pagination. |
| `remove` | `db_remove.py` | `ekvdb.dbDelete_Request` | `engine.GenericStatus_Response` | Removes a single key-value pair. |
| `upsert` | `db_upsert.py` | `ekvdb.dbPut_Request` | `engine.GenericStatus_Response` | Inserts or updates a key-value pair; value is parsed as JSON when possible, otherwise treated as a raw string. |

All commands accept a global `--api-socket` argument (default: `Constants.SOCKET_PATH`, typically `/var/ossec/queue/sockets/analysis`) that overrides which Engine API Unix socket to talk to — useful for testing against non-default Engine instances.

---

## Data Flow: Command Execution

```mermaid
sequenceDiagram
    participant User
    participant CLI as engine-kvdb (__main__.py)
    participant Cmd as cmds/*.py (run)
    participant Client as APIClient
    participant Socket as Unix Domain Socket
    participant Engine as wazuh-engine (kvdb handlers)

    User->>CLI: engine-kvdb <subcommand> [args]
    CLI->>CLI: parse_args() via argparse subparsers
    CLI->>Cmd: args.func(vars(args))  (dispatch to run())
    Cmd->>Cmd: Build Protobuf request from args
    Cmd->>Client: APIClient(api_socket)
    Cmd->>Client: send_recv(request)
    Client->>Client: MessageToDict(request) -> JSON body
    Client->>Socket: HTTP POST /<endpoint> over UDS
    Socket->>Engine: Forward request
    Engine->>Engine: KVDB handler processes request<br/>(engine_kvdb_cpp_core)
    Engine-->>Socket: JSON response
    Socket-->>Client: HTTP response
    Client-->>Cmd: (error, response_dict)
    alt error present
        Cmd->>User: sys.exit(error message)
    else success
        Cmd->>Cmd: ParseDict(response, ExpectedProto)
        alt response.status == ERROR
            Cmd->>User: sys.exit(parsed_response.error)
        else OK
            Cmd->>Cmd: Format via dict_to_str_yml/json
            Cmd->>User: print(formatted output)
        end
    end
```

---

## Process Flow: `upsert` Value Type Resolution

The `upsert` command has special handling to allow both structured (JSON) and plain string values to be stored transparently:

```mermaid
flowchart TD
    A["upsert name key value"] --> B{"Is value valid JSON?<br/>(json.loads)"}
    B -- Yes --> C["ParseDict into protobuf<br/>google.protobuf.Value<br/>(supports objects, arrays, numbers, bool, null)"]
    B -- No / JSONDecodeError --> D["Set as string_value<br/>(raw string fallback)"]
    C --> E["Attach to dbPut_Request.entry.value"]
    D --> E
    E --> F["Send via APIClient.send_recv"]
    F --> G{"Response status"}
    G -- ERROR --> H["sys.exit with error message"]
    G -- OK --> I["Return 0 (success)"]
```

---

## Process Flow: Paginated Read Commands (`search` / `dump`)

`db_search.py` and `manager_dump.py` share nearly identical pagination and export logic:

```mermaid
flowchart TD
    A["Command invoked with optional page/page_size"] --> B{"page and page_size both None?"}
    B -- Yes --> C["No pagination fields set on request"]
    B -- No --> D{"Exactly one of page/page_size provided?"}
    D -- Yes --> E["sys.exit: both must be provided together"]
    D -- No, both provided --> F{"page < 1 or page_size < 1?"}
    F -- Yes --> G["sys.exit: value must be greater than 0"]
    F -- No --> H["Set request.page / request.records"]
    C --> I["Send request via APIClient"]
    H --> I
    I --> J{"error or status == ERROR?"}
    J -- Yes --> K["sys.exit(error)"]
    J -- No --> L{"as-object flag set?"}
    L -- Yes --> M["export_as_object(): flatten entries list<br/>into a single key-to-value dict"]
    L -- No --> N["Keep entries as list of key/value objects"]
    M --> O{"json flag set?"}
    N --> O
    O -- Yes --> P["dict_to_str_json(data, pretty=True)"]
    O -- No --> Q["dict_to_str_yml(data)"]
    P --> R["print(data)"]
    Q --> R
```

---

## Dependencies

### Upstream (consumed by this module)
- **`engine_misc_tools`** — provides `api_communication.client.APIClient`, the shared HTTP-over-Unix-socket transport used by *all* `engine-suite` CLI tools (not just KVDB). See [Engine_Administration_CLI_Tools_(Python).md](Engine_Administration_CLI_Tools_(Python).md).
- **`engine_suite_shared`** — provides:
  - `shared.default_settings.Constants` for the default API socket path and other shared constants.
  - `shared.dumpers` (`EngineDumper`, `dict_to_str_yml`, `dict_to_str_json`) for consistent YAML/JSON rendering across all engine-suite tools.
- **Protobuf contracts** (`api_communication.proto.engine_pb2`, `api_communication.proto.kvdb_pb2`) — generated message classes defining the wire format for KVDB requests/responses and the generic `GenericStatus_Response` / `ERROR` status enum shared by all Engine API endpoints.

### Downstream (serves requests from this module)
- **`engine_kvdb_cpp_core`** (sibling module) — the C++ implementation (`KVDBManager`, `KVDBHandler`, `KVDBHandlerCollection`) that backs the actual database operations invoked by this CLI. See [engine_kvdb_cpp_core.md](engine_kvdb_cpp_core.md).
- **`engine_api_resource_handlers`** — the Engine-side HTTP/UDS handler registration (`api/kvdb/include/api/kvdb/handlers.hpp::registerHandlers`) that receives and routes the JSON/Protobuf requests sent by this CLI to the KVDB core. See [Wazuh_Engine_Core_(C++).md](Wazuh_Engine_Core_(C++).md).
- **`engine_builder`** — the `opmap_kvdb` builders (`getOpBuilderKVDBGet`, `getOpBuilderKVDBMatch`, etc.) consume the same KVDB instances managed by this CLI when evaluating decoder/rule pipelines, meaning changes made via `engine-kvdb upsert/remove` directly affect live rule evaluation. See [Wazuh_Engine_Core_(C++).md](Wazuh_Engine_Core_(C++).md).

---

## How It Fits Into the Overall System

```mermaid
graph LR
    subgraph "Operators / Automation"
        ADMIN["Administrator / Script"]
    end

    subgraph "Engine Administration CLI Tools (Python)"
        KVDBCLI["engine_kvdb_cli<br/>(this module)"]
        OTHERCLI["engine_catalog, engine_policy,<br/>engine_router, engine_test, ..."]
    end

    subgraph "Wazuh Engine Core (C++)"
        API["engine_api<br/>(HTTP/UDS request routing)"]
        KVDBCORE["engine_kvdb (cpp_core)<br/>RocksDB-backed storage"]
        BUILDER["engine_builder<br/>(opmap_kvdb helpers used<br/>by decoders/rules)"]
    end

    ADMIN -->|"engine-kvdb create/upsert/get/..."| KVDBCLI
    KVDBCLI -->|"UDS + Protobuf/JSON"| API
    API --> KVDBCORE
    BUILDER -->|"kvdb_get / kvdb_match helpers"| KVDBCORE
    KVDBCLI -.->|"shares APIClient with"| OTHERCLI
```

`engine_kvdb_cli` is one of several sibling CLI tools under **Engine_Administration_CLI_Tools_(Python)** (alongside `engine_catalog`, `engine_policy`, `engine_router`, `engine_test`, etc.). All of them share the same transport (`APIClient`) and formatting (`shared.dumpers`) infrastructure, giving operators a consistent experience across the entire Engine toolchain. Within the KVDB feature area specifically, this CLI is the operational counterpart to:

- **`engine_kvdb_cpp_core`** — the actual storage engine.
- **`builder_opmap_kvdb`** — the rule/decoder-time consumers of KVDB data (`kvdb_get`, `kvdb_match`, etc., defined in `src/engine/source/builder/src/builders/opmap/kvdb.cpp`), which read the same databases this CLI manages.

Typical usage patterns include:
- Bootstrapping reference-data databases (e.g., IP reputation lists, asset inventories) via `create` + `upsert`/bulk import.
- Debugging rule behavior by using `get`/`search` to inspect what a `kvdb_get`/`kvdb_match` helper would see at rule-evaluation time.
- Exporting/backing up KVDB contents via `dump --as-object --json` for version control or migration.
- Cleaning up stale databases via `delete`/`remove` as part of configuration lifecycle management.
