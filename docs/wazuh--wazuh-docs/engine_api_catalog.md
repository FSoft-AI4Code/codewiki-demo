# Engine API Catalog Module

## Introduction

The **`engine_api_catalog`** module implements the HTTP API surface for the Wazuh Engine's **Catalog** subsystem. The Catalog is the component responsible for managing the lifecycle (create, read, update, delete, validate) of all the *content* artifacts that drive the engine's detection and processing logic — decoders, rules, outputs, filters, integrations, schemas, and policies. This module does **not** implement the storage or validation logic itself; instead it exposes the `ICatalog` interface (implemented by the `Catalog` class) through a set of HTTP route handlers that are registered on the engine's internal HTTP server.

This module is a thin, focused layer in the Wazuh Engine's API stack: it translates protobuf-based HTTP requests/responses into calls against the `Catalog`/`ICatalog` interface, delegating the actual persistence to the Store module and content validation to the Builder module's `IValidator` interface.

## Purpose and Core Functionality

The module provides:

1. **`Catalog` class** — the concrete implementation of `ICatalog` that:
   - Manages CRUD operations for catalog **resources** (a `Resource` identifies a document or a collection, e.g., a decoder, a rule, a schema, scoped to a namespace).
   - Delegates persistence to an injected `IStore` implementation (see [Wazuh_Engine_Core_(C++).md](Wazuh_Engine_Core_(C++).md), `Store` component).
   - Delegates content validation to an injected `IValidator` implementation (see `engine_builder` sub-module in [Wazuh_Engine_Core_(C++).md](Wazuh_Engine_Core_(C++).md)).
   - Converts between different content formats (JSON, YAML) using format converter maps (`m_inFormat` / `m_outFormat`).
   - Enumerates available namespaces.

2. **`Config` struct** — the dependency-injection configuration object used to construct a `Catalog` instance. It bundles:
   - A `store::IStore` shared pointer (storage backend).
   - A `builder::IValidator` shared pointer (asset/environment validator).
   - The schema names used to validate assets and environments.

3. **`registerHandlers` function** — wires up the Catalog's HTTP API by registering a fixed set of POST routes on an `httpsrv::IServer` instance. Each route handler adapts an incoming protobuf request into a call on the `ICatalog` interface and serializes the result back into a protobuf-based HTTP response.

## Architecture Overview

The module sits inside `engine_api`, a child of the broader `engine_api` API layer within the [Wazuh_Engine_Core_(C++)](Wazuh_Engine_Core_(C++).md) module. It has three primary axes of interaction:

- **Upstream**: HTTP requests arrive via the engine's `IServer` (see `engine_httpsrv`), routed to Catalog handlers.
- **Downstream — Storage**: `Catalog` reads/writes documents and collections through `store::IStore` (implemented by `Store`, see `Store` sub-module in [Wazuh_Engine_Core_(C++).md](Wazuh_Engine_Core_(C++).md)).
- **Downstream — Validation**: `Catalog` validates asset/environment content through `builder::IValidator` (see `engine_builder` sub-module in [Wazuh_Engine_Core_(C++).md](Wazuh_Engine_Core_(C++).md)).
- **Sibling modules**: Other API sub-modules such as `engine_api_policy`, `engine_api_router_tester`, and `engine_api_resource_handlers` follow the identical handler-registration pattern using the shared `api/adapter` utilities (`createRequest`/`userResponse`), documented in `engine_api_adapter` (part of [Wazuh_Engine_Core_(C++).md](Wazuh_Engine_Core_(C++).md)).

```mermaid
graph TB
    subgraph "engine_api (parent)"
        Adapter["engine_api_adapter<br/>(createRequest / userResponse)"]
        Catalog["engine_api_catalog<br/>(this module)"]
        Policy["engine_api_policy"]
        RouterTester["engine_api_router_tester"]
        ResourceHandlers["engine_api_resource_handlers<br/>(kvdb / geo / archiver)"]
    end

    HTTPServer["engine_httpsrv::IServer"]
    Store["Store<br/>(store::IStore)"]
    Builder["engine_builder<br/>(builder::IValidator)"]
    CLI["Engine_Administration_CLI_Tools<br/>(engine_catalog Python tool)"]
    Client["api-communication<br/>APIClient"]

    CLI -->|"HTTP requests"| Client
    Client -->|"Unix socket"| HTTPServer
    HTTPServer -->|"routes /catalog/*"| Catalog
    Catalog -->|"uses"| Adapter
    Catalog -->|"CRUD documents/collections"| Store
    Catalog -->|"validate content"| Builder
    Policy -.->|"same server"| HTTPServer
    RouterTester -.->|"same server"| HTTPServer
    ResourceHandlers -.->|"same server"| HTTPServer
```

## Component Relationships

```mermaid
classDiagram
    class ICatalog {
        <<interface>>
        +postResource(Resource, namespaceStr, content) OptError
        +putResource(Resource, content, namespaceId) OptError
        +getResource(Resource, namespaceId) RespOrError~string~
        +deleteResource(Resource, namespaceId) OptError
        +validateResource(Resource, namespaceId, content) OptError
        +getAllNamespaces() vector~NamespaceId~
    }

    class Config {
        +shared_ptr~IStore~ store
        +shared_ptr~IValidator~ validator
        +string assetSchema
        +string environmentSchema
        +validate() void
    }

    class Catalog {
        -shared_ptr~IStore~ m_store
        -shared_ptr~IValidator~ m_validator
        -unordered_map m_outFormat
        -unordered_map m_inFormat
        +Catalog(Config)
        +postResource(...) OptError
        +putResource(...) OptError
        +getResource(...) RespOrError~string~
        +deleteResource(...) OptError
        +validateResource(...) OptError
        +getAllNamespaces() vector~NamespaceId~
        -getDoc(Resource) RespOrError~Doc~
        -getCol(Resource, namespaceId) RespOrError~Col~
        -delDoc(Resource) OptError
        -delCol(Resource, namespaceId) OptError
        -checkResourceInNamespace(...) OptError
        -validate(Resource, namespaceId, content) OptError
    }

    class IStore {
        <<interface>>
    }
    class IValidator {
        <<interface>>
    }
    class IServer {
        <<interface>>
        +addRoute(Method, path, handler)
    }

    ICatalog <|.. Catalog
    Catalog o-- Config
    Catalog --> IStore : uses
    Catalog --> IValidator : uses
    Config --> IStore
    Config --> IValidator

    class handlers_registerHandlers {
        <<function>>
        +registerHandlers(shared_ptr~ICatalog~, shared_ptr~IServer~)
    }
    handlers_registerHandlers --> ICatalog : invokes
    handlers_registerHandlers --> IServer : registers routes on
```

## Registered API Routes

`registerHandlers` binds six POST endpoints on the injected `IServer`. Every handler is created via a factory function (`resourcePost`, `resourceGet`, etc.) that closes over the shared `ICatalog` instance, decodes the protobuf request body, invokes the corresponding `ICatalog` method, and encodes the protobuf response.

| Route | Handler factory | ICatalog operation |
|---|---|---|
| `POST /catalog/resource/post` | `resourcePost` | `postResource` — create a new resource inside a collection |
| `POST /catalog/resource/get` | `resourceGet` | `getResource` — read a document or collection |
| `POST /catalog/resource/delete` | `resourceDelete` | `deleteResource` — remove a document or collection |
| `POST /catalog/resource/put` | `resourcePut` | `putResource` — update an existing resource |
| `POST /catalog/resource/validate` | `resourceValidate` | `validateResource` — validate content without persisting |
| `POST /catalog/namespaces/get` | `getNamespaces` | `getAllNamespaces` — list all known namespaces |

```mermaid
sequenceDiagram
    participant Client as CLI/API client
    participant Server as IServer
    participant Handler as Catalog Handler
    participant Adapter as api::adapter
    participant Catalog as Catalog (ICatalog)
    participant Store as IStore
    participant Validator as IValidator

    Client->>Server: POST /catalog/resource/put (protobuf body)
    Server->>Handler: dispatch(request, response)
    Handler->>Adapter: parse request (createRequest/eMessage)
    Handler->>Catalog: putResource(item, content, namespaceId)
    Catalog->>Catalog: validate(item, namespaceId, content)
    Catalog->>Validator: validate asset/environment content
    Validator-->>Catalog: OK / Error
    Catalog->>Store: upsertDoc(name, namespaceId, content)
    Store-->>Catalog: OptError
    Catalog-->>Handler: OptError
    Handler->>Adapter: userResponse(result)
    Adapter-->>Server: httplib::Response
    Server-->>Client: HTTP response (protobuf JSON)
```

## Data Flow: Resource Validation and Persistence

The `Catalog::putResource` / `postResource` / `validateResource` operations follow a common internal flow, centered on the private `validate` method and namespace-aware helpers:

```mermaid
flowchart TD
    A["Incoming Resource + content + namespaceId"] --> B{"checkResourceInNamespace"}
    B -->|"not found / mismatch"| E["Return Error"]
    B -->|"OK"| C["validate(item, namespaceId, content)"]
    C --> D{"Resource type: Doc or Collection?"}
    D -->|"Doc"| F["Validate against assetSchema<br/>via IValidator"]
    D -->|"Collection"| G["Validate each item<br/>in the collection"]
    F --> H{"Valid?"}
    G --> H
    H -->|"No"| E
    H -->|"Yes"| I["Persist via IStore<br/>(createDoc/updateDoc/upsertDoc)"]
    I --> J["Return OptError (success = nullopt)"]
```

## Key Types

### `Config`
Dependency bundle required to construct a `Catalog`:
- `store` — pointer to the storage backend (`store::IStore`).
- `validator` — pointer to the content validator (`builder::IValidator`).
- `assetSchema` / `environmentSchema` — schema names used during validation.
- `validate()` — asserts that the configuration itself is well-formed (non-null pointers, non-empty schema names) before being used to construct a `Catalog`.

### `Catalog`
Concrete `ICatalog` implementation. Internally maintains two format-conversion maps (`m_inFormat`, `m_outFormat`) keyed by `Resource::Format` (e.g., JSON, YAML) that convert between the wire format and the internal `json::Json` representation used by the store. Private helpers (`getDoc`, `getCol`, `delDoc`, `delCol`, `checkResourceInNamespace`) centralize namespace-aware resource resolution and error handling, which are reused across the public `ICatalog` methods.

### `registerHandlers`
A free function template that takes a `shared_ptr<ICatalog>` and a `shared_ptr<httpsrv::Server>` and registers the six catalog routes described above. This function is invoked once during engine API server bootstrap (alongside sibling `registerHandlers` calls from `engine_api_policy`, `engine_api_router_tester`, and `engine_api_resource_handlers`).

## How This Module Fits Into the Overall System

- **Parent context**: `engine_api_catalog` is a child of `engine_api`, which aggregates all HTTP-facing API sub-modules of the Wazuh Engine (`engine_api_adapter`, `engine_api_policy`, `engine_api_router_tester`, `engine_api_resource_handlers`). See [Wazuh_Engine_Core_(C++).md](Wazuh_Engine_Core_(C++).md) for the full engine architecture.
- **Serialization/adapter layer**: Request/response (de)serialization relies on the shared adapter utilities (`createRequest`, `userResponse`) documented under `engine_api_adapter`, part of the same parent module.
- **Storage backend**: All persistence operations delegate to the `Store` class (`store::IStore`), documented in the `Store` sub-module of [Wazuh_Engine_Core_(C++).md](Wazuh_Engine_Core_(C++).md). The `Store` also manages namespace-to-real-name translation, which underlies the Catalog's namespace-scoped operations.
- **Validation backend**: Content validation is delegated to `builder::IValidator`, implemented within the `engine_builder` sub-module of [Wazuh_Engine_Core_(C++).md](Wazuh_Engine_Core_(C++).md) (specifically the `builder_core` component group, e.g., `Builder`, `IBuildCtx`, `Registry`).
- **HTTP transport**: Routes are served by `IServer`, defined in the `engine_httpsrv` sub-module of [Wazuh_Engine_Core_(C++).md](Wazuh_Engine_Core_(C++).md).
- **CLI consumers**: The Catalog HTTP API is the backend for the `engine_catalog` command-line tool (see [Engine_Administration_CLI_Tools_(Python).md](Engine_Administration_CLI_Tools_(Python).md)), which exposes `create`, `delete`, `get`, `update`, and `validate` sub-commands that map 1:1 onto the routes registered by this module. It is also consumed indirectly by higher-level tools such as `engine_integration`, `engine_policy`, and `engine_test` (also documented in [Engine_Administration_CLI_Tools_(Python).md](Engine_Administration_CLI_Tools_(Python).md)) via the shared `api-communication` `APIClient`.
- **Sibling API modules**: `engine_api_policy` manages policy documents (which reference catalog assets), and `engine_api_router_tester` uses catalog-validated assets when building test environments — both rely on the Catalog being available and consistent.

```mermaid
graph LR
    subgraph "Python CLI Tools"
        EngineCatalogCLI["engine_catalog<br/>(create/get/update/delete/validate)"]
        EngineIntegration["engine_integration"]
        EnginePolicy["engine_policy"]
        EngineTest["engine_test"]
    end

    APIClient["api-communication.APIClient"]

    subgraph "Wazuh Engine Process"
        Catalog["engine_api_catalog"]
        Policy["engine_api_policy"]
        RouterTester["engine_api_router_tester"]
        Store["Store"]
        Builder["engine_builder"]
    end

    EngineCatalogCLI --> APIClient
    EngineIntegration --> APIClient
    EnginePolicy --> APIClient
    EngineTest --> APIClient
    APIClient -->|"unix socket / HTTP"| Catalog

    Policy -->|"resolves assets via"| Catalog
    RouterTester -->|"builds env from"| Catalog
    Catalog --> Store
    Catalog --> Builder
```

## Related Documentation

- [Wazuh_Engine_Core_(C++).md](Wazuh_Engine_Core_(C++).md) — parent module tree, including `engine_api_adapter`, `engine_api_policy`, `engine_api_router_tester`, `engine_api_resource_handlers`, `engine_builder`, `Store`, and `engine_httpsrv`.
- [Engine_Administration_CLI_Tools_(Python).md](Engine_Administration_CLI_Tools_(Python).md) — Python CLI tools (`engine_catalog`, `engine_integration`, `engine_policy`, `engine_test`) that consume this module's HTTP API.
