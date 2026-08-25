# Protocol & NetLog APIs (`shell_browser_api_session_net_protocol_netlog`)

## Introduction

This module implements two of the JavaScript-facing networking APIs that are exposed on Electron's `Session` object: the **`protocol`** module (custom/standard scheme registration and interception) and the **`net-log`** module (capturing Chromium NetLog diagnostic traces to disk). Both APIs are thin Gin/V8 wrappers around native Chromium/Electron networking primitives, and both are owned indirectly by a `Session`/`ElectronBrowserContext` instance.

The module is one of four siblings under `shell_browser_api_session_net` (the browser-context-scoped networking API family), alongside:
- [shell_browser_api_session_net_session_core](shell_browser_api_session_net_session_core.md) — the `Session` object that owns/exposes `protocol` and `netLog`
- [shell_browser_api_session_net_cookies_datapipe](shell_browser_api_session_net_cookies_datapipe.md) — `Cookies` and `DataPipeHolder`
- [shell_browser_api_session_net_web_request](shell_browser_api_session_net_web_request.md) — `WebRequest` interception API
- [shell_browser_api_session_net_service_workers](shell_browser_api_session_net_service_workers.md) — Service Worker context/main bindings

It depends heavily on the lower-level networking infrastructure documented in [Networking_Layer](Networking_Layer.md) (specifically `ProtocolRegistry` and `ElectronURLLoaderFactory`), and on the generic native-binding scaffolding described in [Gin_Helper](Gin_Helper.md).

---

## Purpose & Core Functionality

### 1. `Protocol` API (`electron_api_protocol.h/.cc`)

Exposes the `session.protocol` object to JavaScript, allowing applications to:
- **Register custom protocol schemes as privileged** (`protocol.registerSchemesAsPrivileged`) — must be called before `app.whenReady()`, since it configures Chromium's `url::AddStandardScheme`, CSP-bypass lists, CORS-enabled schemes, fetch-API support, service-worker eligibility, streaming, and V8 code-cache eligibility, and mirrors these flags to child processes via command-line switches.
- **Register handlers for a scheme** — `registerStringProtocol`, `registerBufferProtocol`, `registerFileProtocol`, `registerHttpProtocol`, `registerStreamProtocol`, and the unified `registerProtocol`. Each of these installs a `ProtocolHandler` into the browser-context-scoped `ProtocolRegistry`.
- **Intercept an already-handled scheme** (e.g. override `file://` handling) via the parallel `interceptXProtocol` family, which delegates to `ProtocolRegistry::InterceptProtocol`.
- **Query/undo registration** — `unregisterProtocol`, `isProtocolRegistered`, `uninterceptProtocol`, `isProtocolIntercepted`, and the deprecated `isProtocolHandled` (kept for backward compatibility, checks both registries plus a hard-coded builtin scheme list).

The `Protocol` class itself holds only a `raw_ptr<ProtocolRegistry>` — all actual scheme bookkeeping and Mojo `URLLoaderFactory` wiring lives in `ProtocolRegistry` (see [Networking_Layer](Networking_Layer.md)). This keeps the JS-facing wrapper stateless with respect to the underlying scheme tables, while `ProtocolRegistry`'s lifetime (owned per `ElectronBrowserContext`) is guaranteed to outlive the wrapper.

### 2. `NetLog` API (`electron_api_net_log.h`)

Exposes `session.netLog`, mirroring the behavior of `net_log::NetExportFileWriter`:
- **`startLogging(path[, options])`** — opens a log file and instructs the network service (via a Mojo `network::mojom::NetLogExporter` remote) to begin writing a Chromium NetLog trace, with a configurable `net::NetLogCaptureMode` and optional maximum file size / custom constants JSON.
- **`stopLogging()`** — asynchronously halts the exporter and resolves a `gin_helper::Promise<void>`.
- **`isCurrentlyLogging()`** — synchronous check of whether the exporter Mojo remote is bound.

Both `startLogging`/`stopLogging` are asynchronous, backed by `gin_helper::Promise`, since they hop across the file-I/O thread (`file_task_runner_`) to open/close the log file and across the Mojo IPC boundary to the network service process.

---

## Architecture

```mermaid
graph TD
    subgraph JS_Layer["JavaScript Layer"]
        JSProto["session.protocol"]
        JSNetLog["session.netLog"]
    end

    subgraph This_Module["shell_browser_api_session_net_protocol_netlog"]
        Protocol["api::Protocol\n(electron_api_protocol.h/.cc)"]
        NetLog["api::NetLog\n(electron_api_net_log.h)"]
        SchemeOpts["CustomScheme / SchemeOptions\n(internal parsing structs)"]
    end

    subgraph Native_Networking["Networking_Layer"]
        ProtoReg["ProtocolRegistry"]
        URLFactory["ElectronURLLoaderFactory"]
    end

    subgraph Session_Owner["shell_browser_api_session_net_session_core"]
        Session["api::Session"]
    end

    subgraph Context["shell_browser_context"]
        EBC["ElectronBrowserContext"]
    end

    NetworkService["network::mojom::NetLogExporter\n(Network Service process)"]

    JSProto --> Protocol
    JSNetLog --> NetLog
    Protocol -->|parses privileges via| SchemeOpts
    Protocol -->|delegates registration to| ProtoReg
    ProtoReg -->|creates on registration| URLFactory
    Session -->|owns & creates| Protocol
    Session -->|owns & creates| NetLog
    EBC -->|owns| ProtoReg
    NetLog -->|Mojo Remote| NetworkService
    NetLog -.->|raw_ptr, non-owning| EBC
```

---

## Component Relationships

```mermaid
classDiagram
    class Protocol {
        -raw_ptr~ProtocolRegistry~ protocol_registry_
        +Create(isolate, registry) Handle~Protocol~
        +RegisterProtocol(type, scheme, handler) Error
        +UnregisterProtocol(scheme, args) bool
        +IsProtocolRegistered(scheme) bool
        +InterceptProtocol(type, scheme, handler) Error
        +UninterceptProtocol(scheme, args) bool
        +IsProtocolIntercepted(scheme) bool
        +IsProtocolHandled(scheme, args) Promise~bool~
    }

    class CustomScheme {
        +string scheme
        +SchemeOptions options
    }

    class SchemeOptions {
        +bool standard
        +bool secure
        +bool bypassCSP
        +bool allowServiceWorkers
        +bool supportFetchAPI
        +bool corsEnabled
        +bool stream
        +bool codeCache
    }

    class NetLog {
        -raw_ptr~ElectronBrowserContext~ browser_context_
        -Remote~NetLogExporter~ net_log_exporter_
        -optional~Promise~void~~ pending_start_promise_
        -scoped_refptr~TaskRunner~ file_task_runner_
        +Create(isolate, context) Handle~NetLog~
        +StartLogging(path, args) Promise
        +StopLogging(args) Promise
        +IsCurrentlyLogging() bool
    }

    class ProtocolRegistry {
        +RegisterProtocol(type, scheme, handler) bool
        +UnregisterProtocol(scheme) bool
        +FindRegistered(scheme) HandlersMap.mapped_type*
        +InterceptProtocol(type, scheme, handler) bool
        +UninterceptProtocol(scheme) bool
        +FindIntercepted(scheme) HandlersMap.mapped_type*
        +RegisterURLLoaderFactories(factories, allow_file_access)
        +CreateNonNetworkNavigationURLLoaderFactory(scheme) PendingRemote
    }

    class ElectronURLLoaderFactory {
        +Create(type, handler) PendingRemote~URLLoaderFactory~
        +CreateLoaderAndStart(...)
        +StartLoading(...)
    }

    Protocol --> ProtocolRegistry : delegates all scheme ops
    Protocol ..> CustomScheme : parses via gin Converter
    CustomScheme *-- SchemeOptions
    ProtocolRegistry --> ElectronURLLoaderFactory : creates per-scheme factory
    NetLog --> NetLogExporter : mojo Remote
```

---

## Data Flow: Registering a Protocol Handler

```mermaid
sequenceDiagram
    participant JS as "JS: protocol.registerFileProtocol(scheme, handler)"
    participant Proto as "api::Protocol"
    participant Reg as "ProtocolRegistry"
    participant Factory as "ElectronURLLoaderFactory"
    participant NS as "Network Service"

    JS->>Proto: registerFileProtocol(scheme, handler)
    Proto->>Proto: RegisterProtocolFor<kFile>(scheme, handler, args)
    Proto->>Reg: RegisterProtocol(ProtocolType::kFile, scheme, handler)
    Reg->>Reg: insert into handlers_ map
    Reg-->>Proto: bool added
    Proto->>Proto: HandleOptionalCallback(args, error)
    Note over Proto,JS: legacy callback invoked with null/Error

    Note over Reg,Factory: On subsequent navigation/fetch to `scheme://`
    Reg->>Factory: ElectronURLLoaderFactory::Create(type, handler)
    Factory->>NS: bind as PendingRemote<URLLoaderFactory>
    NS->>Factory: CreateLoaderAndStart(request)
    Factory->>Factory: StartLoadingFile / StartLoadingHttp / StartLoadingStream / StartLoadingBuffer
    Factory-->>NS: response head + body / redirect
```

---

## Data Flow: Registering Privileged Schemes (Startup)

```mermaid
sequenceDiagram
    participant JS as "JS: protocol.registerSchemesAsPrivileged([...])"
    participant Wrapper as "Initialize()::RegisterSchemesAsPrivileged"
    participant Browser as "electron::Browser"
    participant Impl as "api::RegisterSchemesAsPrivileged"
    participant URL as "url::AddStandardScheme / AddSecureScheme / ..."
    participant CSP as "ChildProcessSecurityPolicy"
    participant CmdLine as "base::CommandLine"

    JS->>Wrapper: call with array of {scheme, privileges}
    Wrapper->>Browser: is_ready()?
    alt already ready
        Wrapper-->>JS: throw Error
    else not ready
        Wrapper->>Impl: RegisterSchemesAsPrivileged(thrower, val)
        Impl->>Impl: gin::Converter<CustomScheme> parses array
        loop for each CustomScheme
            Impl->>URL: AddStandardScheme / AddSecureScheme / AddCSPBypassingScheme / AddCorsEnabledScheme / AddCodeCacheScheme
            Impl->>CSP: RegisterWebSafeScheme (if standard)
            Impl->>Impl: AddServiceWorkerScheme (if allowServiceWorkers)
        end
        Impl->>CmdLine: AppendSwitchASCII per category
        Note over CmdLine: propagates scheme lists to child/renderer processes
    end
```

---

## Data Flow: NetLog Capture Lifecycle

```mermaid
sequenceDiagram
    participant JS as "JS: session.netLog.startLogging(path)"
    participant NL as "api::NetLog"
    participant FileTR as "file_task_runner_"
    participant NS as "Network Service (NetLogExporter)"

    JS->>NL: StartLogging(log_path, args)
    NL->>NL: create pending_start_promise_
    NL->>FileTR: PostTask: open base::File at log_path
    FileTR-->>NL: StartNetLogAfterCreateFile(capture_mode, max_size, constants, file)
    NL->>NS: net_log_exporter_->Start(file, constants, capture_mode, max_size)
    NS-->>NL: NetLogStarted(error)
    NL->>JS: resolve/reject pending_start_promise_

    JS->>NL: stopLogging()
    NL->>NS: net_log_exporter_->Stop(...)
    NS-->>NL: completion callback
    NL->>JS: resolve Promise<void>

    Note over NL,NS: OnConnectionError() resets net_log_exporter_ and\nrejects any pending promise if the network service crashes/disconnects
```

---

## Key Design Notes

- **Non-owning pointers, context-scoped lifetime.** Both `Protocol` and `NetLog` hold raw, non-owning pointers (`raw_ptr<ProtocolRegistry>`, `raw_ptr<ElectronBrowserContext>`) back to their owning `ElectronBrowserContext`/`ProtocolRegistry`. These native objects are guaranteed to outlive the JS wrapper because the wrapper is always created *from* and *owned by* the `Session`/`ElectronBrowserContext` (see [shell_browser_api_session_net_session_core](shell_browser_api_session_net_session_core.md) and [shell_browser_context](shell_browser_context.md)).

- **`gin_helper::Constructible` vs plain `Wrappable`.** `Protocol` uses `gin_helper::Constructible<Protocol>` so it can define a `FillObjectTemplate` (method table) shared across instances, while blocking direct JS construction (`New()` throws — instances are only created internally via `Protocol::Create`). `NetLog` uses the simpler `gin_helper::DeprecatedWrappable<NetLog>` pattern with an instance-level `GetObjectTemplateBuilder`. Both patterns are part of the shared native-binding infrastructure in [Gin_Helper](Gin_Helper.md).

- **Legacy API compatibility layer.** Much of `electron_api_protocol.cc`'s complexity (the `RegisterProtocolFor<T>`/`InterceptProtocolFor<T>` templates, `HandleOptionalCallback`, and `IsProtocolHandled`) exists purely to preserve Electron's pre-Promise, per-type (`registerFileProtocol`, `registerBufferProtocol`, etc.) API shape while funneling everything into the unified `ProtocolType` enum and `ProtocolRegistry` internally. Deprecation warnings (`util::EmitWarning`) are emitted for the callback-style and `isProtocolHandled` usages.

- **Scheme privileges vs handler registration are separate concerns.** `registerSchemesAsPrivileged` operates on process-wide/global Chromium scheme tables (`url::AddStandardScheme`, `ChildProcessSecurityPolicy`) and must run before app-ready; it does **not** install any handler. Handler registration (`registerFileProtocol` etc.) operates per-`ProtocolRegistry` (i.e., per `Session`) and can happen at any time. This split is enforced by `Browser::is_ready()` checks in the `Initialize()`-scoped wrapper function.

- **NetLog capture modes and file size limiting** mirror upstream Chromium's `net_log::NetExportFileWriter`, reusing `net::NetLogCaptureMode` and delegating the actual trace serialization to the network service process via Mojo (`network::mojom::NetLogExporter`), rather than doing it in-process — consistent with Electron/Chromium's out-of-process Network Service architecture (see [Networking_Layer](Networking_Layer.md) for `SystemNetworkContextManager` / `NetworkContextService`).

---

## Native Module Registration

`electron_api_protocol.cc` registers itself as a Node.js context-aware linked binding:

```cpp
NODE_LINKED_BINDING_CONTEXT_AWARE(electron_browser_protocol, Initialize)
```

`Initialize()` exposes on the native binding's `exports` object:
- `Protocol` — the constructor/class template (instances created only via `Protocol::Create`, invoked by `Session`)
- `registerSchemesAsPrivileged` — the free function, gated by `Browser::is_ready()`
- `getStandardSchemes` — returns the accumulated `g_standard_schemes` list

`NetLog` does not define its own `Initialize`; instead, `NetLog::Create(isolate, browser_context)` is invoked directly by `Session` (see [shell_browser_api_session_net_session_core](shell_browser_api_session_net_session_core.md)) to construct the `session.netLog` property lazily.

---

## Related Modules

| Module | Relationship |
|---|---|
| [shell_browser_api_session_net_session_core](shell_browser_api_session_net_session_core.md) | Owns and lazily instantiates `Protocol` and `NetLog` as `session.protocol` / `session.netLog` |
| [shell_browser_context](shell_browser_context.md) | Owns the `ProtocolRegistry` per `ElectronBrowserContext`; the ultimate backing store for scheme handlers |
| [Networking_Layer](Networking_Layer.md) | Defines `ProtocolRegistry`, `ElectronURLLoaderFactory`, and the broader Mojo `URLLoaderFactory`/network-context plumbing consumed here |
| [shell_browser_api_session_net_cookies_datapipe](shell_browser_api_session_net_cookies_datapipe.md) | Sibling session-scoped networking API (`Cookies`, `DataPipeHolder`) |
| [shell_browser_api_session_net_web_request](shell_browser_api_session_net_web_request.md) | Sibling session-scoped networking API (`WebRequest` interception) |
| [Gin_Helper](Gin_Helper.md) | Provides `Wrappable`, `Constructible`, `Handle`, `Promise`, `ObjectTemplateBuilder` used to bind these classes to V8 |
| [Common_API](Common_API.md) | `shell/common/gin_converters/net_converter.h` supplies Gin converters for network types used indirectly by protocol handler callbacks |
