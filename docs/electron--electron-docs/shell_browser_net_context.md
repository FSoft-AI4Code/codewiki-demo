# Network Context Service (`shell_browser_net_context`)

## Introduction

The **Network Context Service** module is the layer inside Electron's C++ browser process that owns and configures Chromium's `network::mojom::NetworkContext` instances — the low-level objects that back every HTTP(S)/WebSocket request, cookie jar, cache, and proxy resolution performed by the app.

It provides two complementary responsibilities:

1. **Per-`BrowserContext` network configuration** — via `NetworkContextService` / `NetworkContextServiceFactory`, each Electron `Session` (backed by an `ElectronBrowserContext`) gets its own configured `NetworkContextParams` (cookie store location, cache path, proxy settings, HTTP auth, etc.).
2. **Process-wide ("system") networking** — via `SystemNetworkContextManager`, a singleton that owns the `NetworkContext` used for requests that are *not* tied to any particular session (e.g. update checks, crash reporting, DNS/proxy resolution helpers), and that also configures global `NetworkService` state shared by all contexts.

Additionally, `CertVerifierClient` bridges Chromium's out-of-process certificate verification service back into Electron's JS-configurable `setCertificateVerifyProc` callback mechanism, allowing custom TLS certificate trust decisions to be threaded through the network stack.

This module sits at the heart of the [Networking Layer](Networking_Layer.md) and is a direct dependency of session/browser-context management, URL loading, proxying, and host/proxy resolution.

---

## Module Position in the System

```mermaid
graph TB
    subgraph Networking_Layer["Networking Layer"]
        Context["shell_browser_net_context\n(this module)"]
        Asar["shell_browser_net_asar"]
        UrlLoader["shell_browser_net_url_loader"]
        Proxying["shell_browser_net_proxying"]
        Resolution["shell_browser_net_resolution"]
        ProtoReg["Protocol_Registry"]
    end

    BCtx["Browser Context & Session Management\n(shell_browser_context)"]
    SessionAPI["shell_browser_api_session_net\n(Session / Cookies / WebRequest JS API)"]
    AppAPI["System & App-Level Services API\n(electron_api_app / auto_updater)"]
    Bootstrap["Browser Process Core & Lifecycle\n(shell_browser_main_parts)"]

    BCtx -->|owns/queries| Context
    SessionAPI -->|configures proxy, cert verify proc| Context
    AppAPI -->|update checks, misc requests| Context
    Bootstrap -->|creates singleton at startup| Context

    Context --> UrlLoader
    Context --> Proxying
    Context --> Resolution
    Context --> ProtoReg
    Context -.shares NetworkService state.-> Asar

    click BCtx "shell_browser_context.md"
    click SessionAPI "shell_browser_api_session_net.md"
    click AppAPI "System_&_App-Level_Services_API.md"
    click Bootstrap "shell_browser_main_parts.md"
    click Asar "shell_browser_net_asar.md"
    click UrlLoader "shell_browser_net_url_loader.md"
    click Proxying "shell_browser_net_proxying.md"
    click Resolution "shell_browser_net_resolution.md"
    click ProtoReg "Protocol_Registry.md"
```

See also: [Networking_Layer.md](Networking_Layer.md) for the parent module overview, and [shell_browser_context.md](shell_browser_context.md) for how `ElectronBrowserContext` (the owner of a `NetworkContextService`) is created and managed.

---

## Core Components

| Component | File | Responsibility |
|---|---|---|
| `NetworkContextService` | `shell/browser/net/network_context_service.h` | `KeyedService` — one instance per `BrowserContext`/`ElectronBrowserContext`. Builds `NetworkContextParams` for that session (cookies, cache, proxy). |
| `NetworkContextServiceFactory` | `shell/browser/net/network_context_service_factory.h` | `BrowserContextKeyedServiceFactory` singleton that creates/looks up the `NetworkContextService` for a given `BrowserContext`. |
| `SystemNetworkContextManager` | `shell/browser/net/system_network_context_manager.h` | Global (process-wide) singleton owning the "system" `NetworkContext`, not tied to any session. Also configures global `NetworkService` parameters (e.g. HTTP auth dynamic params). |
| `SystemNetworkContextManager::URLLoaderFactoryForSystem` | (nested, same header) | `SharedURLLoaderFactory` implementation wrapping the system `NetworkContext`'s `URLLoaderFactory`, reconnecting automatically if the underlying mojo pipe disconnects. |
| `CertVerifierClient` | `shell/browser/net/cert_verifier_client.h` | Implements `network::mojom::CertVerifierClient`; receives certificate verification results from the network/cert-verifier service and forwards them to a JS-overridable `CertVerifyProc` callback. |
| `VerifyRequestParams` | `shell/browser/net/cert_verifier_client.h` | POD struct carrying hostname, default verify result, error code, certificate chain, and known-root flag into the custom verify callback. |

---

## Architecture Diagram

```mermaid
classDiagram
    class NetworkContextService {
        -ElectronBrowserContext* browser_context_
        -ProxyConfigMonitor proxy_config_monitor_
        +ConfigureNetworkContextParams(params, cert_verifier_params)
        -CreateNetworkContextParams(in_memory, path) NetworkContextParamsPtr
    }

    class NetworkContextServiceFactory {
        +GetForContext(BrowserContext*) NetworkContextService*
        +GetInstance() NetworkContextServiceFactory*
        -BuildServiceInstanceForBrowserContext(context) unique_ptr~KeyedService~
        -GetBrowserContextToUse(context) BrowserContext*
    }

    class SystemNetworkContextManager {
        -ProxyConfigMonitor proxy_config_monitor_
        -Remote~NetworkContext~ network_context_
        -scoped_refptr~URLLoaderFactoryForSystem~ shared_url_loader_factory_
        -Remote~URLLoaderFactory~ url_loader_factory_
        +CreateInstance(PrefService*) SystemNetworkContextManager*$
        +GetInstance() SystemNetworkContextManager*$
        +DeleteInstance()$
        +IsNetworkSandboxEnabled() bool$
        +ConfigureDefaultNetworkContextParams(params)
        +CreateDefaultNetworkContextParams() NetworkContextParamsPtr
        +GetContext() NetworkContext*
        +GetURLLoaderFactory() URLLoaderFactory*
        +GetSharedURLLoaderFactory() SharedURLLoaderFactory
        +OnNetworkServiceCreated(network_service)
        -CreateNetworkContextParams() NetworkContextParamsPtr
    }

    class URLLoaderFactoryForSystem {
        <<nested, SharedURLLoaderFactory>>
    }

    class CertVerifierClient {
        -CertVerifyProc cert_verify_proc_
        +Verify(default_error, default_result, certificate, hostname, flags, ocsp_response, callback)
    }

    class VerifyRequestParams {
        +hostname string
        +default_result string
        +error_code int
        +certificate X509Certificate
        +validated_certificate X509Certificate
        +is_issued_by_known_root bool
    }

    class ElectronBrowserContext {
        <<from shell_browser_context>>
    }

    class BrowserContextKeyedServiceFactory {
        <<Chromium base class>>
    }

    class KeyedService {
        <<Chromium base class>>
    }

    NetworkContextServiceFactory --|> BrowserContextKeyedServiceFactory
    NetworkContextService --|> KeyedService
    NetworkContextServiceFactory ..> NetworkContextService : creates/owns lookup
    NetworkContextService --> ElectronBrowserContext : raw_ptr
    SystemNetworkContextManager *-- URLLoaderFactoryForSystem
    CertVerifierClient --> VerifyRequestParams : constructs & passes to callback
```

---

## Two Networking Scopes: Per-Session vs. System

Electron applications may have many `Session`s (default session + any custom `partition` sessions created from JS). Each maps to one `ElectronBrowserContext`. However, some browser-process work (auto-update checks, crash reporting uploads, proxy/host resolution helpers not bound to a page) needs networking **without** a session context. These two needs are served by two distinct singletons/keyed-services:

```mermaid
graph LR
    subgraph "Per-Session (KeyedService)"
        EBC1["ElectronBrowserContext\n(default session)"]
        EBC2["ElectronBrowserContext\n(partition: persist:foo)"]
        NCS1["NetworkContextService"]
        NCS2["NetworkContextService"]
        EBC1 --> NCS1
        EBC2 --> NCS2
    end

    subgraph "Process-wide (Singleton)"
        SNCM["SystemNetworkContextManager"]
        SysNC["system NetworkContext\n(mojo::Remote)"]
        SNCM --> SysNC
    end

    NCSF["NetworkContextServiceFactory"] -->|GetForContext| NCS1
    NCSF -->|GetForContext| NCS2

    NCS1 --> NC1["session NetworkContext"]
    NCS2 --> NC2["session NetworkContext"]

    AppAPI["App / AutoUpdater\n(no session)"] --> SNCM
    ResolveHelpers["ResolveHostFunction /\nResolveProxyHelper"] -.may use.-> SNCM
```

- **`NetworkContextService`** is looked up per `BrowserContext` through `NetworkContextServiceFactory::GetForContext()`, mirroring the pattern used by other per-context keyed services in Electron such as `HidChooserContextFactory`, `UsbChooserContextFactory`, and `BadgeManagerFactory` (see [Device_&_Peripheral_Access.md](Device_&_Peripheral_Access.md) and [System_&_App-Level_Services_API.md](System_&_App-Level_Services_API.md)).
- **`SystemNetworkContextManager`** is a plain singleton (`CreateInstance` / `GetInstance` / `DeleteInstance`), created once during [browser process startup](shell_browser_main_parts.md) and torn down at shutdown.

---

## Process / Data Flow

### 1. Session `NetworkContext` creation

```mermaid
sequenceDiagram
    participant JS as "JS: session.fromPartition()"
    participant Session as "Session API\n(shell_browser_api_session_net)"
    participant EBC as "ElectronBrowserContext"
    participant Factory as "NetworkContextServiceFactory"
    participant Service as "NetworkContextService"
    participant NS as "content::NetworkService"
    participant NC as "network::mojom::NetworkContext"

    JS->>Session: create/get session for partition
    Session->>EBC: construct or reuse ElectronBrowserContext
    EBC->>Factory: NetworkContextServiceFactory::GetForContext(this)
    Factory->>Factory: BuildServiceInstanceForBrowserContext()
    Factory->>Service: new NetworkContextService(context)
    Note over Service: proxy_config_monitor_ initialized
    EBC->>Service: ConfigureNetworkContextParams(params, cert_verifier_params)
    Service->>Service: CreateNetworkContextParams(in_memory, path)
    EBC->>NS: CreateNetworkContext(params)
    NS->>NC: construct NetworkContext (cookies, cache, proxy from params)
    NC-->>EBC: mojo::Remote<NetworkContext>
```

### 2. System (session-less) request

```mermaid
sequenceDiagram
    participant Caller as "AutoUpdater / App-level code"
    participant SNCM as "SystemNetworkContextManager"
    participant NS as "content::NetworkService"
    participant SysNC as "system NetworkContext"
    participant ULFS as "URLLoaderFactoryForSystem"

    Caller->>SNCM: SystemNetworkContextManager::GetInstance()
    Caller->>SNCM: GetSharedURLLoaderFactory()
    SNCM->>ULFS: return existing or lazily create
    alt NetworkService restarted / disconnected
        ULFS->>NS: reconnect via OnNetworkServiceCreated()
        NS->>SysNC: recreate NetworkContext w/ CreateNetworkContextParams()
    end
    Caller->>ULFS: CreateLoaderAndStart(...)
    ULFS->>SysNC: forward request via URLLoaderFactory
    SysNC-->>Caller: response via mojo pipe
```

### 3. Custom certificate verification

```mermaid
sequenceDiagram
    participant JS as "JS: session.setCertificateVerifyProc(cb)"
    participant SessionAPI as "Session (electron_api_session)"
    participant NCS as "NetworkContextService"
    participant CVFactory as "cert_verifier service"
    participant CVClient as "CertVerifierClient"

    JS->>SessionAPI: register CertVerifyProc callback
    SessionAPI->>NCS: ConfigureNetworkContextParams(..., cert_verifier_creation_params)
    NCS->>CVFactory: pass CertVerifierCreationParams (bound CertVerifierClient)
    CVFactory->>CVClient: Verify(default_error, default_result, certificate, hostname, flags, ocsp, callback)
    CVClient->>CVClient: build VerifyRequestParams
    CVClient->>SessionAPI: invoke cert_verify_proc_ (JS callback via V8)
    SessionAPI-->>CVClient: verification result (net error code)
    CVClient-->>CVFactory: callback(result)
```

This flow is what backs the public `ses.setCertificateVerifyProc()` JS API, defined in [`shell_browser_api_session_net_session_core`](shell_browser_api_session_net.md).

---

## Component Interaction Overview

```mermaid
graph TD
    subgraph "Browser Context & Session Mgmt"
        EBC["ElectronBrowserContext"]
    end

    subgraph "shell_browser_net_context"
        NCS["NetworkContextService"]
        NCSF["NetworkContextServiceFactory"]
        SNCM["SystemNetworkContextManager"]
        CVC["CertVerifierClient"]
    end

    subgraph "Proxy / Resolution"
        PCM["ProxyConfigMonitor\n(Chromium)"]
        RPH["ResolveProxyHelper"]
    end

    subgraph "URL Loading & Proxying"
        EULF["ElectronURLLoaderFactory"]
        PULF["ProxyingURLLoaderFactory"]
    end

    subgraph "Protocol"
        PR["ProtocolRegistry"]
    end

    EBC -->|GetForContext| NCSF
    NCSF -->|creates| NCS
    NCS --> PCM
    NCS -->|ConfigureNetworkContextParams| EBC
    NCS -.uses.-> CVC
    SNCM --> PCM
    SNCM -->|GetSharedURLLoaderFactory| EULF
    EBC --> PR
    EBC --> RPH
    EULF -.chained by.-> PULF

    click EBC "shell_browser_context.md"
    click RPH "shell_browser_net_resolution.md"
    click EULF "shell_browser_net_url_loader.md"
    click PULF "shell_browser_net_proxying.md"
    click PR "Protocol_Registry.md"
```

---

## Key Design Notes

- **`raw_ptr<ElectronBrowserContext>`**: `NetworkContextService` holds a non-owning back-reference to its owning `ElectronBrowserContext`; lifetime is managed by the `KeyedService`/`BrowserContextKeyedServiceFactory` framework, which guarantees the service is destroyed before (or alongside) its `BrowserContext`.
- **`ProxyConfigMonitor`**: Both `NetworkContextService` (per-session) and `SystemNetworkContextManager` (system-wide) embed their own `ProxyConfigMonitor` instance, since proxy configuration can differ between individual sessions (via `ses.setProxy()`) and the OS/system-level default used for session-less requests.
- **In-memory vs. persistent contexts**: `CreateNetworkContextParams(bool in_memory, const base::FilePath& path)` on `NetworkContextService` determines whether cookies/cache are written to disk (persistent partitions) or kept purely in memory (in-memory/incognito-style sessions).
- **Resilience to `NetworkService` crashes**: `SystemNetworkContextManager::URLLoaderFactoryForSystem` and `OnNetworkServiceCreated()` exist specifically to reconnect mojo pipes automatically if the underlying network process/service restarts, avoiding the need for every system-level caller to manually handle disconnection.
- **Sandboxing**: `SystemNetworkContextManager::IsNetworkSandboxEnabled()` is a static helper callable even before the singleton is constructed, used during early startup policy decisions.

---

## Related Modules

- [Networking_Layer.md](Networking_Layer.md) — parent module; overview of ASAR loading, URL loader factories, proxying, and host/proxy resolution that build on top of the `NetworkContext`s created here.
- [shell_browser_net_asar.md](shell_browser_net_asar.md) — serves `file://`/`asar://` resources through a URL loader factory registered against a `NetworkContext`.
- [shell_browser_net_url_loader.md](shell_browser_net_url_loader.md) — custom protocol and Node stream URL loader factories that plug into the network stack configured here.
- [shell_browser_net_proxying.md](shell_browser_net_proxying.md) — intercepting/proxying `URLLoaderFactory` and WebSocket implementations used to support `webRequest` and extension APIs.
- [shell_browser_net_resolution.md](shell_browser_net_resolution.md) — `ResolveHostFunction`/`ResolveProxyHelper`, which query the `NetworkContext`'s host resolver and proxy resolver.
- [Protocol_Registry.md](Protocol_Registry.md) — per-`BrowserContext` registry of custom protocol handlers, consulted when building `NetworkContextParams`.
- [shell_browser_context.md](shell_browser_context.md) — `ElectronBrowserContext`, the owning object for each `NetworkContextService` instance.
- [shell_browser_api_session_net.md](shell_browser_api_session_net.md) — JS-facing `Session`/`Cookies`/`WebRequest` APIs that ultimately configure proxy settings and certificate verification through this module.
- [System_&_App-Level_Services_API.md](System_&_App-Level_Services_API.md) — consumers of the system-wide `NetworkContext` (e.g., `AutoUpdater`).
- [shell_browser_main_parts.md](shell_browser_main_parts.md) — browser process startup sequence where `SystemNetworkContextManager::CreateInstance()` is invoked.
