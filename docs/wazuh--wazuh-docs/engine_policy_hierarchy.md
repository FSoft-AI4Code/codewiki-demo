# Engine Policy Hierarchy Module

## Introduction

The **`engine_policy_hierarchy`** module is a small but important part of the `engine_policy` Python CLI tool (see [engine_policy_store.md](engine_policy_store.md) and [engine_policy_assets.md](engine_policy_assets.md) for sibling modules). It provides the command-line surface for managing **namespace hierarchy and default-parent relationships** within a Wazuh Engine policy.

In the Wazuh Engine, a *policy* is a named collection of decoder/rule/output *assets* grouped into *namespaces*. When an event is processed, assets belonging to different namespaces are chained together according to a *default parent* relationship — i.e., which asset (typically a decoder) should act as the entry point/parent for all assets in a given namespace when no explicit relationship is defined. This module exposes three CLI subcommands that let operators:

1. **Set** the default parent asset for a namespace (`parent-set`)
2. **Remove** the default parent asset for a namespace (`parent-remove`)
3. **List** all namespaces registered within a policy (`namespace-list`)

These commands are thin, stateless wrappers: they build a Protocol-Buffer request, send it over a Unix domain socket to the running `wazuh-engine` daemon's HTTP-over-UDS API, and print/interpret the response. All business logic and persistence live server-side in the C++ Engine (see [engine_api_policy.md](engine_api_policy.md) and the [engine_builder.md](engine_builder.md) policy subsystem).

---

## 1. Purpose and Core Functionality

| Command | CLI Name | Purpose |
|---|---|---|
| `parent_set.py` | `parent-set` | Assigns a default parent asset to a namespace within a policy. All un-parented assets in that namespace will implicitly attach to this parent. |
| `parent_remove.py` | `parent-remove` | Removes a previously configured default parent for a namespace. |
| `namespace_get.py` | `namespace-list` | Retrieves and prints (YAML) the full list of namespaces currently defined in a policy. |

### Common Design Pattern

Every command file in this module follows the exact same structure, consistent with all `engine_policy` subcommands:

```python
def run(args: dict) -> int:
    # 1. Extract CLI args (api_socket, policy, namespace, ...)
    # 2. Build a protobuf request message (api_communication.proto.policy_pb2)
    # 3. Send it via APIClient.send_recv()
    # 4. Parse/validate the response (engine_pb2.ERROR check)
    # 5. Print results / exit with error message
    return 0

def configure(subparsers) -> None:
    # Registers the subcommand, its arguments and defaults with argparse
    parser.set_defaults(func=run)
```

This pattern is shared across the entire [engine_policy](engine_policy.md) tool family (`engine_policy_store`, `engine_policy_assets`, and this module), making the CLI easy to extend with new subcommands.

---

## 2. Architecture

### 2.1 Component Diagram

```mermaid
graph TB
    subgraph "engine_policy_hierarchy (this module)"
        PS[parent_set.py]
        PR[parent_remove.py]
        NG[namespace_get.py]
    end

    subgraph "engine_policy CLI (parent module)"
        MAIN[engine_policy/__main__.py]
        STORE[engine_policy_store<br/>create/get/list/delete]
        ASSETS[engine_policy_assets<br/>asset-add/list/delete/clean]
    end

    subgraph "engine_suite_shared"
        APICLIENT[api_communication.client.APIClient]
        CONST[shared.default_settings.Constants]
        DUMP[shared.dumpers.dict_to_str_yml / EngineDumper]
    end

    subgraph "Wazuh Engine Core (C++ daemon)"
        HTTPSRV[engine_httpsrv<br/>IServer]
        HANDLERS[engine_api_policy<br/>policy handlers.hpp]
        POLICYAPI[Policy class<br/>IPolicy impl]
        STOREBACK[Store<br/>policy documents]
        VALIDATOR[Schemf Validator]
    end

    MAIN --> PS
    MAIN --> PR
    MAIN --> NG
    MAIN --> STORE
    MAIN --> ASSETS

    PS --> APICLIENT
    PR --> APICLIENT
    NG --> APICLIENT
    PS --> CONST
    PR --> CONST
    NG --> CONST
    NG --> DUMP

    APICLIENT -- "Unix Domain Socket<br/>HTTP POST /policy/default_parent/*<br/>/policy/namespaces/list" --> HTTPSRV
    HTTPSRV --> HANDLERS
    HANDLERS --> POLICYAPI
    POLICYAPI --> STOREBACK
    POLICYAPI --> VALIDATOR
```

### 2.2 File-to-Endpoint Mapping

| CLI File | Protobuf Request | Server Endpoint (registered in [engine_api_policy.md](engine_api_policy.md) `handlers.hpp`) | Server-side `Policy` method |
|---|---|---|---|
| `parent_set.py` | `DefaultParentPost_Request` | `POST /policy/default_parent/post` | `Policy::setDefaultParent` |
| `parent_remove.py` | `DefaultParentDelete_Request` | `POST /policy/default_parent/delete` | `Policy::delDefaultParent` |
| `namespace_get.py` | `NamespacesGet_Request` | `POST /policy/namespaces/list` | `Policy::listNamespaces` |

---

## 3. Data Flow

The request/response life cycle is identical for all three commands; only the protobuf message type and target field differ.

```mermaid
sequenceDiagram
    participant User
    participant CLI as engine_policy CLI<br/>(parent_set / parent_remove / namespace_get)
    participant Client as APIClient
    participant Sock as Unix Domain Socket
    participant Server as Engine httpsrv
    participant Policy as Policy (C++)
    participant Store as Store backend

    User->>CLI: engine-policy parent-set -p <policy> -n <ns> <parent>
    CLI->>CLI: Build protobuf request<br/>(policy, namespace, parent)
    CLI->>Client: send_recv(request)
    Client->>Client: MessageToDict(request)<br/>resolve endpoint from message type
    Client->>Sock: HTTP POST /policy/default_parent/post
    Sock->>Server: dispatch to registered route
    Server->>Policy: setDefaultParent(policyName, namespaceId, parentName)
    Policy->>Store: read/upsert policy document
    Store-->>Policy: success / error
    Policy-->>Server: RespOrError<string> (warning or error)
    Server-->>Sock: JSON response {status, error, warning}
    Sock-->>Client: HTTP 200 + JSON body
    Client-->>CLI: (error, response_dict)
    CLI->>CLI: ParseDict into typed Response message<br/>check status == ERROR
    alt status == OK
        CLI-->>User: print warning (if any), exit 0
    else status == ERROR
        CLI-->>User: sys.exit(error message)
    end
```

---

## 4. Component Interaction — CLI Argument Wiring

Each command registers itself with the shared `argparse` subparsers object exposed by the `engine_policy` `__main__.py` entry point (see [engine_policy.md](engine_policy.md)).

```mermaid
graph LR
    A["engine_policy/__main__.py<br/>main()"] --> B[argparse subparsers]
    B --> C["parent_set.configure(subparsers)"]
    B --> D["parent_remove.configure(subparsers)"]
    B --> E["namespace_get.configure(subparsers)"]
    C --> F["'parent-set' command<br/>args: -p/--policy, -n/--namespace, parent_name"]
    D --> G["'parent-remove' command<br/>args: -p/--policy, -n/--namespace, parent_name"]
    E --> H["'namespace-list' command<br/>args: -p/--policy"]
    F -.default.-> I[Constants.DEFAULT_POLICY<br/>Constants.DEFAULT_NS]
    G -.default.-> I
    H -.default.-> I
```

All three commands rely on `shared.default_settings.Constants` (see [engine_suite_shared.md](engine_suite_shared.md)) for default values:
- `DEFAULT_POLICY = 'policy/wazuh/0'`
- `DEFAULT_NS = 'user'`

This means an operator can invoke, e.g., `engine-policy parent-set my_decoder` without specifying `-p`/`-n` and it will target the default Wazuh policy and namespace.

---

## 5. Command Details

### 5.1 `parent-set` (parent_set.py)

- **Request message**: `epolicy.DefaultParentPost_Request` with fields `policy`, `parent`, `namespace`.
- **Response message**: `epolicy.DefaultParentPost_Response` (fields: `status`, `error`, `warning`).
- **Behavior**: On success, prints any non-empty `warning` field (e.g., overriding an existing default parent) and returns 0. On failure (`status == engine.ERROR`), exits the process via `sys.exit` with the server-provided error message.

**Function summary:**
- `configure(subparsers)`: Registers the `parent-set` subcommand with `-p/--policy` (default `Constants.DEFAULT_POLICY`), `-n/--namespace` (default `Constants.DEFAULT_NS`), and the positional `parent_name` argument.
- `run(args)`: Executes the request/response cycle described above.

### 5.2 `parent-remove` (parent_remove.py)

- **Request message**: `epolicy.DefaultParentDelete_Request` — structurally identical fields to the `Post` request (`policy`, `parent`, `namespace`).
- **Response message**: `epolicy.DefaultParentDelete_Response`.
- **Behavior**: Mirrors `parent-set`'s error/warning handling exactly, but invokes the deletion endpoint.

**Function summary:**
- `configure(subparsers)`: Registers the `parent-remove` subcommand with the same argument shape as `parent-set`.
- `run(args)`: Executes the request/response cycle, targeting the delete endpoint.

### 5.3 `namespace-list` (namespace_get.py)

- **Request message**: `epolicy.NamespacesGet_Request` with field `policy`.
- **Response message**: `epolicy.NamespacesGet_Response`, whose `data` field is a list of namespace identifiers.
- **Behavior**: If the response contains data, it is rendered as YAML via `shared.dumpers.dict_to_str_yml` (built on `EngineDumper`, a `yaml.Dumper` subclass with improved scalar formatting for quotes/newlines) and printed to stdout.

**Function summary:**
- `configure(subparsers)`: Registers the `namespace-list` subcommand with only `-p/--policy` (default `Constants.DEFAULT_POLICY`).
- `run(args)`: Executes the request/response cycle and pretty-prints the namespace list.

---

## 6. Process Flow — Typical Usage

```mermaid
flowchart TD
    Start([User runs engine-policy CLI]) --> Choice{Which command?}
    Choice -->|parent-set| PS[Build DefaultParentPost_Request]
    Choice -->|parent-remove| PR[Build DefaultParentDelete_Request]
    Choice -->|namespace-list| NG[Build NamespacesGet_Request]

    PS --> Send[APIClient.send_recv]
    PR --> Send
    NG --> Send

    Send --> Check{Transport error?}
    Check -->|Yes| ExitErr1["sys.exit('Error ...: ' + error)"]
    Check -->|No| ParseResp[ParseDict into typed Response]

    ParseResp --> Status{response.status == ERROR?}
    Status -->|Yes| ExitErr2["sys.exit('Error ...: ' + response.error)"]
    Status -->|No| Result{Command type}

    Result -->|parent-set / parent-remove| Warn{warning != ''?}
    Warn -->|Yes| PrintWarn[print warning]
    Warn -->|No| Done1([Return 0])
    PrintWarn --> Done1

    Result -->|namespace-list| HasData{data non-empty?}
    HasData -->|Yes| PrintYaml[print dict_to_str_yml data]
    HasData -->|No| Done2([Return 0])
    PrintYaml --> Done2
```

---

## 7. Dependencies

### 7.1 Internal (within this repository)

| Dependency | Module Doc | Role |
|---|---|---|
| `api_communication.client.APIClient` | [engine_misc_tools.md](engine_misc_tools.md) | Handles UDS/HTTP transport, protobuf⇄dict conversion, and generic status checking. |
| `shared.default_settings.Constants` | [engine_suite_shared.md](engine_suite_shared.md) | Supplies default socket path, policy name, and namespace. |
| `shared.dumpers` (`dict_to_str_yml`, `EngineDumper`) | [engine_suite_shared.md](engine_suite_shared.md) | Formats namespace list output as human-readable YAML. |
| `api_communication.proto.policy_pb2` (`epolicy`) | Generated from Engine `.proto` definitions consumed by [engine_api_policy.md](engine_api_policy.md) | Defines `DefaultParentPost/Delete_Request/Response` and `NamespacesGet_Request/Response` message schemas. |
| `api_communication.proto.engine_pb2` (`engine`) | Same as above | Defines the shared `ReturnStatus`/`ERROR` enum used to detect failures. |

### 7.2 External (server-side, C++ Engine)

| Component | Module Doc | Role |
|---|---|---|
| `engine_httpsrv` (`IServer`) | [engine_httpsrv.md](engine_httpsrv.md) | Listens on the Unix domain socket and routes HTTP-like requests to handlers. |
| `engine_api_policy` handlers | [engine_api_policy.md](engine_api_policy.md) | Registers `/policy/default_parent/*` and `/policy/namespaces/list` routes and adapts protobuf requests to `Policy` API calls. |
| `Policy` class (`IPolicy`) | [engine_api_policy.md](engine_api_policy.md) / [builder_policy.md](builder_policy.md) | Implements `setDefaultParent`, `delDefaultParent`, and `listNamespaces` business logic, backed by the [Store.md](Store.md) document store and [Schemf_Validator_Engine.md](Schemf_Validator_Engine.md) for validation. |

---

## 8. How This Module Fits in the Overall System

This module is one of several CLI sub-tools bundled in the `Engine_Administration_CLI_Tools_(Python)` suite that lets administrators and integrators manage the Wazuh Engine (a C++ event-processing daemon) without writing raw protobuf/HTTP calls by hand. It sits at the very edge of the administration tooling stack:

```mermaid
graph TD
    subgraph "Administration CLI Suite"
        EP[engine_policy]
        EC[engine_catalog]
        ER[engine_router]
        EK[engine_kvdb]
        ET[engine_test]
    end
    EP --> EPH["engine_policy_hierarchy<br/>(this module)"]
    EP --> EPS[engine_policy_store]
    EP --> EPA[engine_policy_assets]

    EPH -->|UDS/HTTP| DAEMON[Wazuh Engine Daemon]
    EPS -->|UDS/HTTP| DAEMON
    EPA -->|UDS/HTTP| DAEMON
    EC -->|UDS/HTTP| DAEMON
    ER -->|UDS/HTTP| DAEMON
    EK -->|UDS/HTTP| DAEMON

    DAEMON --> ENGINEAPI[engine_api]
    ENGINEAPI --> BUILDER[engine_builder]
    ENGINEAPI --> STORE2[Store]
    BUILDER --> ROUTER[Router]
```

By managing default-parent relationships and namespace visibility, `engine_policy_hierarchy` directly influences how the [builder_policy.md](builder_policy.md) subsystem constructs the asset execution graph (`PolicyGraph`) at policy-build time, and ultimately how events flow through the [Router.md](Router.md) at runtime.

---

## 9. Summary

`engine_policy_hierarchy` is a lightweight, three-command CLI extension responsible exclusively for **namespace and default-parent hierarchy management** on Wazuh Engine policies. It contains no business logic itself — its sole responsibilities are:

1. Parsing CLI arguments with sensible defaults.
2. Marshaling requests into the correct protobuf message types.
3. Communicating with the Engine daemon via `APIClient` over a Unix domain socket.
4. Interpreting and displaying success/warning/error results to the operator.

All actual state changes (setting/removing default parents, tracking namespaces) are performed by the C++ `Policy` class documented in [engine_api_policy.md](engine_api_policy.md).
