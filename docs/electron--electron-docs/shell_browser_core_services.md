# Shell Browser Core Services

## Introduction

The **Shell Browser Core Services** module provides the foundational, process-wide services that back Electron's browser process. It is the C++ layer that mirrors and extends Chromium's `BrowserProcess` abstraction, offering lazily-created singleton-style services (proxy resolution, print job management, background-mode stubbing) as well as two supporting subsystems used throughout the browser process:

- **Auto-updating** (`auto_updater::AutoUpdater` / `Delegate`) — a thin static façade that bridges the native auto-update backends (Squirrel.Mac, Squirrel.Windows) to the JS-exposed `autoUpdater` API.
- **Certificate management** (`CertificateManagerModel`) — a data/business-logic layer for inspecting and mutating the NSS certificate database, used by certificate-management UI and import/export flows.

Together with `Browser` and `BrowserObserver` (documented in [shell_browser_core_lifecycle.md](shell_browser_core_lifecycle.md)), these components make up the `shell_browser_core` parent grouping — the backbone that `ElectronBrowserMainParts` (see [shell_browser_main_parts.md](shell_browser_main_parts.md)) instantiates during startup and keeps alive for the lifetime of the application.

This module sits low in the dependency graph: almost every other browser-process subsystem (networking, sessions, extensions, UI) either consults `BrowserProcessImpl` for a shared service or is orchestrated by code that owns an instance of it.

## Module Position in the System

```mermaid
graph TB
    subgraph BootstrapLayer["Application Bootstrap & Process Entry"]
        MainDelegate["ElectronMainDelegate"]
    end

    subgraph MainParts["shell_browser_main_parts"]
        EBMP["ElectronBrowserMainParts"]
    end

    subgraph CoreLifecycle["shell_browser_core_lifecycle"]
        Browser["Browser"]
        BrowserObserver["BrowserObserver"]
    end

    subgraph ThisModule["shell_browser_core_services (this module)"]
        BPI["BrowserProcessImpl"]
        AU["auto_updater::AutoUpdater / Delegate"]
        CMM["CertificateManagerModel"]
    end

    subgraph Networking["Networking_Layer"]
        RPH["ResolveProxyHelper"]
        SNCM["SystemNetworkContextManager"]
    end

    subgraph Ctx["Browser_Context_&_Session_Management"]
        EBC["ElectronBrowserContext"]
    end

    MainDelegate --> EBMP
    EBMP -- "owns" --> BPI
    EBMP -- "owns" --> Browser
    BPI -- "creates/owns" --> RPH
    BPI -- "creates/owns" --> SNCM
    RPH -- "resolves proxies for" --> EBC
    AU -. "delegate callbacks" .-> Browser
    CMM -. "used by" .-> UI["Desktop_UI_Widgets_&_Dialogs (certificate trust UI)"]

    style ThisModule fill:#dff0d8,stroke:#3c763d,stroke-width:2px
```

## Core Components

### 1. `BrowserProcessImpl`

`BrowserProcessImpl` is Electron's concrete implementation of Chromium's `BrowserProcess` interface. It is a **NOT-thread-safe**, main-thread-only singleton (owned by `ElectronBrowserMainParts`) that lazily creates and exposes process-global services. Most of the interface consists of overridden accessors for Chromium subsystems (metrics, policy, GPU mode, download limiters, etc.), many of which Electron does not use and simply stub out or return `nullptr`/no-op.

Key responsibilities relevant to Electron:

- **Lifecycle hooks** — `PostEarlyInitialization()`, `PreCreateThreads()`, `PreMainMessageLoopRun()`, `PostMainMessageLoopRun()` are called at specific points during startup/shutdown by `ElectronBrowserMainParts`.
- **Locale management** — `SetSystemLocale`/`GetSystemLocale` and `SetApplicationLocale`/`GetApplicationLocale`.
- **Proxy resolution access** — `GetResolveProxyHelper()` returns the shared `electron::ResolveProxyHelper` (see [Networking_Layer](#relationship-to-networking-layer) below).
- **Preferences** — owns `local_state_` (`PrefService`) and an in-memory `ValueMapPrefStore` used to seed proxy configuration from the command line (`ApplyProxyModeFromCommandLine`).
- **Printing** — owns `printing::PrintJobManager` (behind `BUILDFLAG(ENABLE_PRINTING)`).
- **OS Crypt** — creates and exposes `os_crypt_async::OSCryptAsync` for encrypted storage needs.
- **Linux storage backend selection** — tracks which secret-storage backend (kwallet, gnome-keyring, basic-text) was selected for Linux OS Crypt.

`BackgroundModeManager` in this file is an intentionally **empty stub class** — Electron does not implement Chrome's background-mode feature but must supply the type to satisfy `BrowserProcess`'s virtual interface (`std::unique_ptr<BackgroundModeManager>` parameters, etc.).

```mermaid
classDiagram
    class BrowserProcess {
        <<Chromium interface>>
    }
    class BrowserProcessImpl {
        -unique_ptr~PrintJobManager~ print_job_manager_
        -unique_ptr~PrefService~ local_state_
        -string locale_
        -string system_locale_
        -scoped_refptr~ValueMapPrefStore~ in_memory_pref_store_
        -scoped_refptr~ResolveProxyHelper~ resolve_proxy_helper_
        -unique_ptr~NetworkQualityTracker~ network_quality_tracker_
        -unique_ptr~OSCryptAsync~ os_crypt_async_
        +PostEarlyInitialization()
        +PreCreateThreads()
        +PreMainMessageLoopRun()
        +PostMainMessageLoopRun()
        +GetResolveProxyHelper() ResolveProxyHelper
        +local_state() PrefService
        +print_job_manager() PrintJobManager
        +system_network_context_manager() SystemNetworkContextManager
        +ApplyProxyModeFromCommandLine(ValueMapPrefStore*) $
    }
    class BackgroundModeManager {
        <<empty stub>>
    }
    class ResolveProxyHelper {
        <<Networking_Layer>>
    }
    class PrintJobManager {
        <<Chromium printing>>
    }
    class SystemNetworkContextManager {
        <<Networking_Layer, singleton>>
    }

    BrowserProcess <|-- BrowserProcessImpl
    BrowserProcessImpl --> BackgroundModeManager : returns (unused)
    BrowserProcessImpl --> ResolveProxyHelper : owns (scoped_refptr)
    BrowserProcessImpl --> PrintJobManager : owns
    BrowserProcessImpl ..> SystemNetworkContextManager : delegates to global instance
```

### 2. `auto_updater::AutoUpdater` and `Delegate`

`AutoUpdater` is a **static-only class** (non-instantiable, `AutoUpdater() = delete`) that exposes a small, platform-agnostic API surface for the auto-update feature:

- `SetFeedURL(gin::Arguments*)` / `GetFeedURL()`
- `CheckForUpdates()`
- `QuitAndInstall()`
- `IsVersionAllowedForUpdate(current, target)`

All actual update logic lives in platform-specific backends (Squirrel.Mac / Squirrel.Windows, not shown in this module) which call back into the registered `Delegate`. The `Delegate` interface defines the event contract:

- `OnError(message)` / `OnError(message, code, domain)`
- `OnCheckingForUpdate()`
- `OnUpdateAvailable()`
- `OnUpdateNotAvailable()`
- `OnUpdateDownloaded(release_notes, release_name, release_date, update_url)`

The delegate is typically implemented by the JS-facing binding class `electron::api::AutoUpdater` (see [System_&_App-Level_Services_API](System_&_App-Level_Services_API.md) → `electron_api_auto_updater.h`), which converts these callbacks into `autoUpdater` events emitted to JavaScript.

```mermaid
sequenceDiagram
    participant JS as "JS: autoUpdater.checkForUpdates()"
    participant API as "api::AutoUpdater (JS binding)"
    participant AU as "auto_updater::AutoUpdater (static)"
    participant Backend as "Platform Update Backend (Squirrel)"
    participant Delegate as "auto_updater::Delegate (impl = api::AutoUpdater)"

    JS->>API: checkForUpdates()
    API->>AU: AutoUpdater::CheckForUpdates()
    AU->>Backend: trigger platform update check
    Backend-->>Delegate: OnCheckingForUpdate()
    Delegate-->>JS: emit 'checking-for-update'
    Backend-->>Delegate: OnUpdateAvailable() / OnUpdateNotAvailable()
    Delegate-->>JS: emit corresponding event
    Backend-->>Delegate: OnUpdateDownloaded(notes, name, date, url)
    Delegate-->>JS: emit 'update-downloaded'
```

### 3. `CertificateManagerModel`

`CertificateManagerModel` provides the data and mutation operations backing certificate-management UI (import/export/trust). It wraps a `net::NSSCertDatabase` pointer and exposes:

- **Creation** — `Create(CreationCallback)` performs asynchronous, thread-hopping initialization (`GetCertDBOnIOThread` → `DidGetCertDBOnIOThread` → `DidGetCertDBOnUIThread`) because NSS database access must happen on the IO thread while the resulting model is handed back on the UI thread.
- **Import operations** — `ImportFromPKCS12`, `ImportUserCert`, `ImportCACerts`, `ImportServerCert`.
- **Trust management** — `SetCertTrust`.
- **Deletion** — `Delete`.
- **Availability check** — `is_user_db_available()` indicates whether the profile has a public NSS slot, gating whether import operations are permitted.

This model is primarily consumed by the [Desktop_UI_Widgets_&_Dialogs](Desktop_UI_Widgets_&_Dialogs.md) module's certificate-trust dialog (`shell/browser/ui/certificate_trust.h`) and by browser-client SSL/client-certificate flows in [shell_browser_main_parts.md](shell_browser_main_parts.md) (`ElectronBrowserClient`'s `SSLCertRequestInfo` / `ClientCertificateDelegate` handling).

```mermaid
sequenceDiagram
    participant UI as "Certificate Trust UI"
    participant Model as "CertificateManagerModel"
    participant IOThread as "IO Thread"
    participant NSS as "net::NSSCertDatabase"

    UI->>Model: CertificateManagerModel::Create(callback)
    Model->>IOThread: GetCertDBOnIOThread(callback)
    IOThread->>NSS: obtain NSSCertDatabase*
    IOThread->>Model: DidGetCertDBOnIOThread(callback, cert_db)
    Model->>UI: DidGetCertDBOnUIThread(...) -> callback(model)
    UI->>Model: ImportUserCert(data) / SetCertTrust(...) / Delete(cert)
    Model->>NSS: perform operation
    NSS-->>Model: net error code / bool result
    Model-->>UI: result
```

## Component Relationships

```mermaid
graph LR
    subgraph shell_browser_core_services
        BPI[BrowserProcessImpl]
        AU[AutoUpdater/Delegate]
        CMM[CertificateManagerModel]
    end

    EBMP["ElectronBrowserMainParts\n(shell_browser_main_parts)"] -->|"owns fake_browser_process_"| BPI
    Browser["Browser\n(shell_browser_core_lifecycle)"] -.->|"implements Delegate for update events"| AU
    BPI -->|"GetResolveProxyHelper()"| RPH["ResolveProxyHelper\n(Networking_Layer)"]
    BPI -->|"system_network_context_manager()"| SNCM["SystemNetworkContextManager\n(Networking_Layer)"]
    RPH -->|"resolves proxies for"| EBC["ElectronBrowserContext\n(Browser_Context_&_Session_Management)"]
    CMM -->|"backs"| CertUI["certificate_trust.h\n(Desktop_UI_Widgets_&_Dialogs)"]
    CMM -->|"consulted by"| EBCUI["ElectronBrowserClient SSL handling\n(shell_browser_main_parts)"]
    APIAU["api::AutoUpdater JS binding\n(System_&_App-Level_Services_API)"] -->|"calls static methods"| AU
```

### Relationship to Networking Layer

`BrowserProcessImpl::GetResolveProxyHelper()` exposes a shared `electron::ResolveProxyHelper` instance. This class (defined in the [Networking_Layer](Networking_Layer.md) module) queues and dispatches asynchronous proxy lookups via `network::mojom::ProxyLookupClient`, ultimately used by `ElectronBrowserContext` and networking code that needs `session.resolveProxy()`-style behavior.

Similarly, `BrowserProcessImpl::system_network_context_manager()` returns the global `SystemNetworkContextManager` singleton (also in [Networking_Layer](Networking_Layer.md)), which configures default `NetworkContextParams`, exposes a shared `URLLoaderFactory`, and reacts to `OnNetworkServiceCreated`. `BrowserProcessImpl` does not own this singleton directly — it accesses it via `SystemNetworkContextManager::GetInstance()`, which is created/destroyed elsewhere in the startup/shutdown sequence orchestrated by `ElectronBrowserMainParts`.

### Relationship to Browser Lifecycle

`BrowserProcessImpl` is instantiated and owned by `ElectronBrowserMainParts::fake_browser_process_` (see [shell_browser_main_parts.md](shell_browser_main_parts.md)). It is a companion object to `Browser` (owned separately as `ElectronBrowserMainParts::browser_`, documented in [shell_browser_core_lifecycle.md](shell_browser_core_lifecycle.md)) — together, `Browser` handles app-lifecycle events (`will-quit`, `before-quit`, dock/tray hooks, login items) while `BrowserProcessImpl` supplies backing services that Chromium code expects to find via the global `g_browser_process` pointer pattern.

## Startup / Shutdown Sequence

```mermaid
sequenceDiagram
    participant Delegate as ElectronMainDelegate
    participant MainParts as ElectronBrowserMainParts
    participant BPI as BrowserProcessImpl
    participant SNCM as SystemNetworkContextManager

    Delegate->>MainParts: PreCreateThreads()
    MainParts->>BPI: new BrowserProcessImpl()
    MainParts->>BPI: PostEarlyInitialization()
    MainParts->>SNCM: SystemNetworkContextManager::CreateInstance(local_state)
    MainParts->>BPI: PreCreateThreads()
    Note over MainParts,BPI: Threads/services spun up
    MainParts->>BPI: PreMainMessageLoopRun()
    Note over MainParts: Main message loop runs (app is live)
    MainParts->>BPI: PostMainMessageLoopRun()
    MainParts->>SNCM: SystemNetworkContextManager::DeleteInstance()
    MainParts->>BPI: PostDestroyThreads() (no-op)
    MainParts->>BPI: destroy fake_browser_process_
```

## Design Notes

- **Interface stubbing**: `BrowserProcessImpl` overrides a very large Chromium interface (`BrowserProcess`) but only meaningfully implements the subset Electron needs (locale, printing, proxy resolution, network context, OS Crypt, prefs). All unused accessors either return `nullptr` or are no-ops — this is intentional, since Electron reuses Chromium's `//chrome` layer code paths without pulling in the full Chrome browser feature set.
- **Thread-safety caveat**: The header explicitly documents `BrowserProcessImpl` as **NOT THREAD SAFE** — all access must occur on the main (UI) thread.
- **Static delegate pattern for AutoUpdater**: Rather than being an instantiable object, `AutoUpdater` uses a static delegate registration pattern (`SetDelegate`/`GetDelegate`), matching the single-updater-per-process nature of Squirrel-based auto-update flows and simplifying calls from platform-specific `.mm`/`.cc` update implementations.
- **Async NSS access in CertificateManagerModel**: Because `NSSCertDatabase` must be accessed on the IO thread historically, `CertificateManagerModel::Create` follows a hop-to-IO-then-back-to-UI callback chain rather than exposing a synchronous constructor.

## Related Modules

- [shell_browser_core_lifecycle.md](shell_browser_core_lifecycle.md) — `Browser`, `BrowserObserver`: application-level lifecycle events and observer pattern; sibling module under `shell_browser_core`.
- [shell_browser_main_parts.md](shell_browser_main_parts.md) — `ElectronBrowserMainParts`: owns and drives the lifecycle of `BrowserProcessImpl` and `Browser`.
- [Networking_Layer.md](Networking_Layer.md) — `ResolveProxyHelper`, `SystemNetworkContextManager`: services exposed through `BrowserProcessImpl`.
- [Browser_Context_&_Session_Management.md](Browser_Context_&_Session_Management.md) — `ElectronBrowserContext` and session APIs that consume proxy resolution and network context services.
- [System_&_App-Level_Services_API.md](System_&_App-Level_Services_API.md) — JS-facing `electron_api_auto_updater.h` binding that drives `auto_updater::AutoUpdater` and implements `Delegate`.
- [Desktop_UI_Widgets_&_Dialogs.md](Desktop_UI_Widgets_&_Dialogs.md) — certificate trust dialogs and other UI consuming `CertificateManagerModel`.
