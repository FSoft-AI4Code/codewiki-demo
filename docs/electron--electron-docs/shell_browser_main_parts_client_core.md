# Shell Browser Main Parts & Client Core

## Introduction

The **Shell Browser Main Parts & Client Core** module contains the two most central classes that glue Electron's browser process into the Chromium `//content` layer:

- **`ElectronBrowserClient`** — Electron's implementation of `content::ContentBrowserClient`, the primary extension point Chromium provides for embedders to customize browser-process behavior (network stack wiring, permission delegates, navigation throttles, process lifecycle hooks, etc.).
- **`ElectronBrowserMainParts`** — Electron's implementation of `content::BrowserMainParts`, which drives the ordered startup/shutdown sequence of the browser process (locale setup, toolkit initialization, Node.js/V8 environment bring-up, extension subsystem registration, and graceful teardown).

Together these two classes form the "root" of the browser process: `ElectronBrowserClient::CreateBrowserMainParts()` instantiates `ElectronBrowserMainParts`, which in turn owns/bootstraps most of the other browser-process subsystems documented elsewhere in this wiki (Node.js bindings, `Browser` singleton, `BrowserProcessImpl`, extensions, toolkit/views delegates, etc.).

This module is a direct child of [shell_browser_main_parts](shell_browser_main_parts.md) (the parent grouping for browser-main-parts related code), which itself sits under the broader [Browser Process Core & Lifecycle](shell_browser_core_lifecycle.md) area of the codebase.

## Architecture Overview

```mermaid
graph TB
    subgraph "shell_browser_main_parts_client_core"
        EBC["ElectronBrowserClient<br/>(content::ContentBrowserClient)"]
        EBMP["ElectronBrowserMainParts<br/>(content::BrowserMainParts)"]
        LUG["LinuxUiGetterImpl<br/>(.cc-local helper)"]
    end

    ContentLayer["Chromium //content layer<br/>(BrowserMainRunner, RenderProcessHost, etc.)"]

    ContentLayer -->|"invokes"| EBC
    EBC -->|"CreateBrowserMainParts()"| EBMP
    EBMP -.->|"IS_LINUX toolkit init"| LUG

    EBMP --> Browser["Browser singleton<br/>(shell_browser_main_parts_client_core_bootstrap.md)"]
    EBMP --> BPI["BrowserProcessImpl<br/>(shell_browser_core_services.md)"]
    EBMP --> JSENV["JavascriptEnvironment / NodeBindings<br/>(shell_browser_main_parts_js_environment.md)"]
    EBMP --> EXT["ElectronExtensionsClient/BrowserClient<br/>(shell_browser_extensions_core.md)"]
    EBMP --> VIEWSDEL["ViewsDelegate / ViewsDelegateMac<br/>(Cocoa_UI.md / Frame_Views.md)"]

    EBC --> DELEGATES["Bluetooth/HID/Serial/USB/WebAuthn Delegates<br/>(shell_browser_bluetooth.md, shell_browser_hid.md, Serial.md, USB.md, WebAuthn.md)"]
    EBC --> NOTIF["PlatformNotificationService<br/>(shell_browser_notifications.md)"]
    EBC --> THROTTLE["NavigationThrottleRegistry<br/>(shell_browser_main_parts_content_delegates.md)"]
    EBC --> CTX["ElectronBrowserContext<br/>(shell_browser_context.md)"]

    classDef core fill:#fce8b2,stroke:#333;
    class EBC,EBMP,LUG core;
```

## Sub-modules

This module is split into two focused sub-modules, one per core class family:

| Sub-module | Documentation | Scope |
|---|---|---|
| Browser Client | [shell_browser_main_parts_client_core_browser_client.md](shell_browser_main_parts_client_core_browser_client.md) | `ElectronBrowserClient` and the `content::ContentBrowserClient` extension points it implements: certificate/permission delegates, device delegates hookup, network/URL-loader factory wiring, process lifecycle observation. |
| Bootstrap / Main Parts | [shell_browser_main_parts_client_core_bootstrap.md](shell_browser_main_parts_client_core_bootstrap.md) | `ElectronBrowserMainParts` and its staged startup/shutdown sequence (`PreEarlyInitialization` → `PostMainMessageLoopRun`), including the Linux-only `LinuxUiGetterImpl` helper and ownership of the Node.js/V8 bring-up, `Browser`, and toolkit delegates. |

## High-level Functionality

### `ElectronBrowserClient`

`ElectronBrowserClient` is a singleton (`ElectronBrowserClient::Get()`) that Chromium's `//content` layer calls into at well-defined extension points throughout the life of the browser process. Its main responsibilities include:

- Supplying device/permission delegates: Bluetooth, HID, Serial, USB, WebAuthn (see [Device & Peripheral Access](shell_browser_bluetooth.md)).
- Creating the `content::BrowserMainParts` instance (`ElectronBrowserMainParts`) via `CreateBrowserMainParts()`.
- Configuring network context parameters and URL loader factories (see [shell_browser_net](shell_browser_net.md)).
- Handling certificate errors/selection and client certificate stores.
- Registering Mojo interface binders for renderer/service-worker frames.
- Tracking pending render processes and their associated `WebContents`.
- Providing the `PlatformNotificationService` and `NotificationPresenter` (see [shell_browser_notifications](shell_browser_notifications.md)).
- Creating navigation throttles (`CreateThrottlesForNavigation`) delegated to [shell_browser_main_parts_content_delegates](shell_browser_main_parts_content_delegates.md).

Full details: [shell_browser_main_parts_client_core_browser_client.md](shell_browser_main_parts_client_core_browser_client.md).

### `ElectronBrowserMainParts`

`ElectronBrowserMainParts` implements the ordered set of virtual hooks that `content::BrowserMainParts` defines, driving the browser process from cold start to shutdown. It:

- Owns the `NodeBindings` / `ElectronBindings` / `JavascriptEnvironment` used to run Electron's Node.js main process environment (see [shell_browser_main_parts_js_environment](shell_browser_main_parts_js_environment.md)).
- Owns the `Browser` singleton (app lifecycle, see [shell_browser_core_lifecycle](shell_browser_core_lifecycle.md)) and the fake `BrowserProcessImpl` (see [shell_browser_core_services](shell_browser_core_services.md)).
- Initializes platform toolkits: `views::LayoutProvider`, `ViewsDelegate`/`ViewsDelegateMac`, `wm::WMState`, `display::Screen`/`ScopedNativeScreen`, and (on Linux) `ui::DarkModeManagerLinux` / `ui::LinuxUiGetter` (via the local `LinuxUiGetterImpl`).
- Sets up the extensions subsystem (`ElectronExtensionsClient`, `ElectronExtensionsBrowserClient`) when extensions are enabled (see [shell_browser_extensions_core](shell_browser_extensions_core.md) and [Extensions_(Common)](Extensions_(Common).md)).
- Manages locale/resource-bundle loading, field trials, signal handlers, and OS-crypt configuration.
- Cleanly shuts down Node.js, utility processes, and browser contexts on `PostMainMessageLoopRun`.

Full details: [shell_browser_main_parts_client_core_bootstrap.md](shell_browser_main_parts_client_core_bootstrap.md).

## Process Lifecycle Data Flow

```mermaid
sequenceDiagram
    participant Content as content::BrowserMainRunner
    participant Client as ElectronBrowserClient
    participant Parts as ElectronBrowserMainParts
    participant Node as NodeBindings/JavascriptEnvironment
    participant Browser as Browser singleton

    Content->>Client: CreateBrowserMainParts()
    Client->>Parts: new ElectronBrowserMainParts()
    Content->>Parts: PreEarlyInitialization()
    Content->>Parts: PostEarlyInitialization()
    Parts->>Node: Initialize isolate + CreateEnvironment()
    Parts->>Node: LoadEnvironment() / JoinAppCode()
    Content->>Parts: PreCreateThreads()
    Parts->>Browser: PreCreateThreads()
    Content->>Parts: ToolkitInitialized()
    Content->>Parts: PreMainMessageLoopRun()
    Parts->>Browser: WillFinishLaunching() / DidFinishLaunching()
    Content->>Parts: WillRunMainMessageLoop()
    Note over Content,Parts: Main message loop runs
    Content->>Parts: PostMainMessageLoopRun()
    Parts->>Node: DestroyMicrotasksRunner() / node::Stop()
    Parts->>Browser: (contexts destroyed)
```

## Relationship to Other Modules

- **Parent module:** [shell_browser_main_parts](shell_browser_main_parts.md) — groups this module with [shell_browser_main_parts_js_environment](shell_browser_main_parts_js_environment.md), [shell_browser_main_parts_content_delegates](shell_browser_main_parts_content_delegates.md), and [shell_browser_main_parts_support_utils](shell_browser_main_parts_support_utils.md).
- **Sibling area:** [shell_browser_core_lifecycle](shell_browser_core_lifecycle.md) and [shell_browser_core_services](shell_browser_core_services.md) provide the `Browser` and `BrowserProcessImpl` objects owned by `ElectronBrowserMainParts`.
- **Consumed by:** [shell_app](shell_app.md) (`ElectronMainDelegate`) which drives process entry and ultimately reaches `ElectronBrowserClient`/`ElectronBrowserMainParts` for the browser process type.
- **Delegates out to:** device subsystems ([shell_browser_bluetooth](shell_browser_bluetooth.md), [shell_browser_hid](shell_browser_hid.md), [Serial](Serial.md), [USB](USB.md), [WebAuthn](WebAuthn.md)), notifications ([shell_browser_notifications](shell_browser_notifications.md)), networking ([shell_browser_net](shell_browser_net.md)), and extensions ([shell_browser_extensions_core](shell_browser_extensions_core.md), [Extensions_(Common)](Extensions_(Common).md)).
