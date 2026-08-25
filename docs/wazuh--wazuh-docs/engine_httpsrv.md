# Engine HTTP Server Interface (`engine_httpsrv`)

## Introduction

The `engine_httpsrv` module defines the **abstract HTTP transport contract** used by the Wazuh Engine to expose its administrative and operational API over a local HTTP(S)-like interface (in practice, a Unix domain socket speaking HTTP semantics). It is a very small, header-only module — a single interface file, `iserver.hpp` — but it plays a foundational architectural role: every other Engine subsystem that needs to expose or consume HTTP-style routes (catalog, policy, router, KVDB, tester, geo, archiver management endpoints, etc.) programs against this interface rather than against a concrete HTTP server implementation.

By isolating the HTTP transport behind `httpsrv::IServer`, the Engine achieves:

- **Decoupling**: The API layer (`engine_api`) registers routes and handlers without knowing which concrete HTTP server library implements the socket/transport logic.
- **Testability**: Components that depend on `IServer` can be unit-tested against mock/stub servers.
- **Compile-time polymorphism**: The interface uses the Curiously Recurring Template Pattern (CRTP) instead of virtual dispatch, avoiding vtable overhead in a hot request path while still enforcing a consistent contract.

This document describes the interface's structure, its position in the Engine architecture, and how it is expected to interact with the rest of the `Wazuh_Engine_Core_(C++)` subsystems.

---

## Module Purpose & Core Functionality

The module exposes two core elements:

1. **`httpsrv::Method`** — an enum representing supported HTTP verbs (`GET`, `POST`, `PUT`, `DELETE`, `ERROR_METHOD`), along with two `constexpr` helper functions:
   - `methodToStr(Method)`: converts an enum value to its string representation.
   - `strToMethod(const char*)`: parses a string into a `Method` enum value (returning `ERROR_METHOD` for unrecognized input).

2. **`httpsrv::IServer<ServerImpl>`** — a CRTP-based interface template that defines the contract any concrete HTTP server implementation must fulfill:
   - `start(socketPath, useThread)`: starts the server listening on a given Unix socket path, optionally on a background thread.
   - `stop()`: stops the server.
   - `addRoute(method, route, handler)`: registers a handler function for a given HTTP method + route path combination. The handler receives a templated `Request` and `Response` pair.
   - `isRunning()`: reports whether the server is currently active.

Because `IServer` uses CRTP (`static_cast<ServerImpl*>(this)->...`), there is **no runtime polymorphism cost** — the compiler resolves calls to the concrete implementation at compile time, while still giving downstream code a single, uniform API surface (`IServer<ConcreteServer>`) to program against.

---

## Architecture

### Interface Position in the Engine

```mermaid
graph TB
    subgraph "engine_httpsrv (this module)"
        IServer["IServer&lt;ServerImpl&gt; (CRTP interface)"]
        Method["Method enum + strToMethod/methodToStr"]
    end

    subgraph "Concrete Implementation (external/engine binary)"
        ConcreteSrv["Concrete HTTP Server Impl\n(implements start/stop/addRoute/isRunning)"]
    end

    subgraph "Consumers (register routes)"
        EngineMain["engine_main (bootstraps server instance)"]
        EngineApiAdapter["engine_api_adapter (createRequest/userResponse)"]
        EngineApiCatalog["engine_api_catalog handlers"]
        EngineApiPolicy["engine_api_policy handlers"]
        EngineApiRouterTester["engine_api_router_tester handlers"]
        EngineApiResourceHandlers["engine_api_resource_handlers (kvdb/geo/archiver)"]
    end

    ConcreteSrv -->|implements| IServer
    EngineMain -->|constructs & starts| ConcreteSrv
    EngineApiAdapter -->|uses Request/Response types compatible with| IServer
    EngineApiCatalog -->|registerHandlers via addRoute| IServer
    EngineApiPolicy -->|registerHandlers via addRoute| IServer
    EngineApiRouterTester -->|registerHandlers via addRoute| IServer
    EngineApiResourceHandlers -->|registerHandlers via addRoute| IServer
```

### CRTP Interface Pattern

```mermaid
classDiagram
    class IServer~ServerImpl~ {
        <<interface (CRTP)>>
        +start(socketPath, useThread) void
        +stop() void
        +addRoute(method, route, handler) void
        +isRunning() bool
    }
    class ConcreteServerImpl {
        +start(socketPath, useThread) void
        +stop() void
        +addRoute(method, route, handler) void
        +isRunning() bool
    }
    class Method {
        <<enum>>
        GET
        POST
        PUT
        DELETE
        ERROR_METHOD
    }
    IServer~ServerImpl~ ..> ConcreteServerImpl : static_cast dispatch
    ConcreteServerImpl --|> IServer~ConcreteServerImpl~ : instantiates template with itself
    IServer~ServerImpl~ ..> Method : uses
```

This pattern mirrors similar CRTP/strategy abstractions used elsewhere in the Engine codebase, such as `engine_base_patterns` (`Builder`, `AbstractHandler`, `Singleton`, `SingletonLocator`), reflecting a consistent design philosophy across `Wazuh_Engine_Core_(C++)` of favoring compile-time composition over heavyweight runtime polymorphism.

---

## Component Interaction & Data Flow

### Route Registration Flow

```mermaid
sequenceDiagram
    participant Main as engine_main
    participant Srv as ConcreteServerImpl (implements IServer)
    participant ApiCatalog as engine_api_catalog::registerHandlers
    participant ApiPolicy as engine_api_policy::registerHandlers
    participant ApiRouter as engine_api_router_tester::registerHandlers
    participant Adapter as engine_api_adapter

    Main->>Srv: construct ConcreteServerImpl
    Main->>ApiCatalog: registerHandlers(server)
    ApiCatalog->>Srv: addRoute(POST, "/catalog/resource/post", handler)
    Main->>ApiPolicy: registerHandlers(server)
    ApiPolicy->>Srv: addRoute(POST, "/policy/...", handler)
    Main->>ApiRouter: registerHandlers(server)
    ApiRouter->>Srv: addRoute(POST, "/router/...", handler)
    Main->>Srv: start(socketPath, useThread=true)
    Srv-->>Main: isRunning() == true
```

### Request Processing Flow

```mermaid
flowchart LR
    A["Client / engine-suite CLI\ne.g. engine_catalog, engine_policy, engine_router"] -->|HTTP request over Unix socket| B[ConcreteServerImpl]
    B --> C{"strToMethod matches\nregistered route?"}
    C -->|Yes| D["Invoke registered handler\nfunction(Request, Response)"]
    C -->|No| E["Return ERROR_METHOD / 404"]
    D --> F["Handler builds domain response\nusing adapter::userResponse"]
    F --> G[ConcreteServerImpl serializes Response]
    G --> H[Client receives HTTP response]
```

This request flow underlies every administrative operation exposed by the Engine: catalog CRUD (`engine_api_catalog`), policy management (`engine_api_policy`), router/tester operations (`engine_api_router_tester`), and resource handlers for KVDB, Geo, and Archiver (`engine_api_resource_handlers`). All of these ultimately call `IServer::addRoute` to bind their business logic to an HTTP method + path pair.

---

## Method Resolution Logic

```mermaid
flowchart TD
    Start["strToMethod(str)"] --> CheckGET{"str == 'GET'?"}
    CheckGET -->|yes| RetGET["Return Method::GET"]
    CheckGET -->|no| CheckPOST{"str == 'POST'?"}
    CheckPOST -->|yes| RetPOST["Return Method::POST"]
    CheckPOST -->|no| CheckPUT{"str == 'PUT'?"}
    CheckPUT -->|yes| RetPUT["Return Method::PUT"]
    CheckPUT -->|no| CheckDELETE{"str == 'DELETE'?"}
    CheckDELETE -->|yes| RetDELETE["Return Method::DELETE"]
    CheckDELETE -->|no| RetError["Return Method::ERROR_METHOD"]
```

Both `methodToStr` and `strToMethod` are `constexpr`, allowing method/string translation to potentially be resolved at compile time when literal method values are used (e.g., in route registration macros), and cheaply at runtime otherwise (e.g., when parsing an incoming raw HTTP request line).

---

## Relationships to Other Modules

| Related Module | Relationship |
|---|---|
| [engine_api.md](engine_api.md) | The API layer's `registerHandlers` functions (catalog, policy, router, tester, kvdb, geo, archiver) are the primary consumers of `IServer::addRoute`. They bind Engine business logic to HTTP routes exposed through this interface. |
| `engine_api_adapter` (see [engine_api.md](engine_api.md)) | Provides `createRequest`/`userResponse` helpers that produce the `Request`/`Response` objects passed through `IServer::addRoute` handlers. |
| [engine_main.md](engine_main.md) | The Engine's main entry point is responsible for constructing the concrete `IServer` implementation, wiring in all API handler registrations, and calling `start()`/`stop()` as part of the daemon lifecycle. |
| [Router.md](Router.md) | The Router/Tester subsystem exposes control-plane operations (route add/delete/reload, EPS control, session testing) through routes registered via this interface. |
| [engine_kvdb.md](engine_kvdb.md), [engine_geo.md](engine_geo.md) | KVDB and Geo management CLIs (`engine_kvdb`, `engine_geo` Python tools) communicate with the Engine daemon over HTTP routes implemented through handlers registered on an `IServer` instance. |
| [engine_base.md](engine_base.md) (`engine_base_patterns`) | Shares the same design philosophy of compile-time composition patterns (`Builder`, `AbstractHandler`, `Singleton`) used throughout `Wazuh_Engine_Core_(C++)`. |
| [Engine_Administration_CLI_Tools_(Python).md](Engine_Administration_CLI_Tools_(Python).md) | Python CLI tools such as `engine_catalog`, `engine_policy`, `engine_router`, and `api-communication`'s `APIClient` act as HTTP clients issuing requests against routes registered through this server interface. |

---

## Design Notes

- **Header-only / interface-only module**: There is no `.cpp` implementation file in this module — `iserver.hpp` purely defines the contract. Concrete server implementations (e.g., built atop a third-party HTTP/Unix-socket library) live outside this interface module and are wired together at the `engine_main` composition root.
- **Templated Request/Response**: `addRoute` is templated on `Request`/`Response` types, allowing different concrete server implementations to use different underlying request/response representations (e.g., wrapping a third-party library's types) while still conforming to a uniform signature.
- **Socket-based transport**: `start()` takes a `std::filesystem::path` socket path rather than a host/port pair, reflecting the Engine's use of Unix domain sockets for local inter-process administration rather than network-exposed HTTP.
- **Threading model**: The `useThread` parameter on `start()` indicates the interface supports both blocking (foreground) and non-blocking (background thread) startup modes, letting `engine_main` decide whether the server loop should occupy the calling thread or run independently while the main daemon performs other work (e.g., running the `Router`/`Orchestrator`).

---

## Summary

`engine_httpsrv` is a minimal but architecturally important interface module. It defines the single abstraction point (`IServer`) through which all Engine administrative HTTP functionality — catalog, policy, router, tester, KVDB, geo, and archiver management — is exposed, without coupling those subsystems to any particular HTTP server implementation. Its CRTP-based design keeps this abstraction free of runtime dispatch overhead, consistent with the broader compile-time-composition patterns used throughout the `Wazuh_Engine_Core_(C++)` codebase.
