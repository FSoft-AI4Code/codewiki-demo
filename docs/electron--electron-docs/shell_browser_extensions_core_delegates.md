# Extensions Core Delegates (`shell_browser_extensions_core_delegates`)

## Introduction

The **Extensions Core Delegates** module provides a small but essential set of
delegate and data-carrier classes that plug Electron's browser process into
several Chromium `//extensions` subsystems. These classes implement narrow,
well-defined interfaces expected by the upstream extensions code, allowing
Electron to customize (or intentionally restrict) extension behavior without
forking the underlying Chromium extensions machinery.

The module contains three components:

| Component | Base Class (Chromium) | Purpose |
|---|---|---|
| `ElectronProcessManagerDelegate` | `extensions::ProcessManagerDelegate` | Controls whether extension background pages are allowed/created |
| `ElectronKioskDelegate` | `extensions::KioskDelegate` | Reports kiosk-mode/auto-launch status for extensions & apps |
| `ElectronNavigationUIData` | `content::NavigationUIData` | Carries extension-specific navigation metadata from the UI thread to the IO/network thread during navigations |

These delegates are consumed and owned primarily by
[`ElectronExtensionsBrowserClient`](shell_browser_extensions_core_browser_client.md),
which is the central integration point between Electron and the Chromium
extensions system.

---

## 1. Purpose & Core Functionality

### 1.1 `ElectronProcessManagerDelegate`

Implements `extensions::ProcessManagerDelegate`, the hook that Chromium's
`ProcessManager` uses to decide extension background-page policy. Electron
uses this to answer three key questions for any given `BrowserContext`:

- **`AreBackgroundPagesAllowedForContext`** — Are background pages allowed at
  all in this context?
- **`IsExtensionBackgroundPageAllowed`** — Is a specific extension allowed to
  have a background page?
- **`DeferCreatingStartupBackgroundHosts`** — Should creation of background
  hosts be deferred until later in startup?

Because Electron does not have the same profile/session lifecycle as Chrome,
this delegate typically returns conservative/simple answers, essentially
enabling background pages without the additional guardrails Chrome uses for
multi-profile scenarios.

### 1.2 `ElectronKioskDelegate`

Implements `extensions::KioskDelegate`, used by extension APIs (such as
`chrome.app.window` kiosk-related checks) to determine whether a given
extension is an auto-launched kiosk app:

```cpp
bool IsAutoLaunchedKioskApp(const extensions::ExtensionId& id) const override;
```

Electron does not have a native concept of ChromeOS-style kiosk sessions, so
this delegate generally returns `false`, disabling kiosk-specific extension
behavior while still satisfying the interface contract required by the
extensions system.

### 1.3 `ElectronNavigationUIData`

Implements `content::NavigationUIData`, a per-navigation data container that
Chromium clones and threads through the navigation pipeline (UI thread →
IO/network thread). Electron uses it to carry an
`extensions::ExtensionNavigationUIData` payload, which lets the extensions
subsystem correctly attribute a navigation to a `<webview>` guest, tab, or
frame originating from an extension.

Key responsibilities:
- **`Clone()`** — Deep-copies itself (and its `ExtensionNavigationUIData`) so
  that the network stack can safely use it after the original object on the
  UI thread goes away.
- **`SetExtensionNavigationUIData` / `GetExtensionNavigationUIData`** —
  Accessors for attaching/reading the extension-specific navigation context.

---

## 2. Architecture & Component Relationships

```mermaid
graph TB
    subgraph "shell_browser_extensions_core_delegates"
        PMD[ElectronProcessManagerDelegate]
        KD[ElectronKioskDelegate]
        NUD[ElectronNavigationUIData]
    end

    subgraph "Chromium extensions interfaces"
        PMDBase["extensions::ProcessManagerDelegate"]
        KDBase["extensions::KioskDelegate"]
        NUDBase["content::NavigationUIData"]
        ENUData["extensions::ExtensionNavigationUIData"]
    end

    PMD -->|implements| PMDBase
    KD -->|implements| KDBase
    NUD -->|implements| NUDBase
    NUD -->|owns/carries| ENUData

    EBC["ElectronExtensionsBrowserClient"] -->|owns, exposes via GetProcessManagerDelegate| PMD
    EBC -->|owns, exposes via GetKioskDelegate| KD

    NavThrottle["ElectronNavigationThrottle /\nContent navigation code"] -->|creates per-navigation| NUD

    click EBC "shell_browser_extensions_core_browser_client.md"
```

`ElectronProcessManagerDelegate` and `ElectronKioskDelegate` are both owned as
`std::unique_ptr` members inside
[`ElectronExtensionsBrowserClient`](shell_browser_extensions_core_browser_client.md)
and exposed through its overrides of `GetProcessManagerDelegate()` and
`GetKioskDelegate()`. `ElectronNavigationUIData` is instantiated on a
per-navigation basis by the content/navigation layer (see
[`shell_browser_main_parts_content_delegates`](shell_browser_main_parts_content_delegates.md)
for related navigation throttle code) rather than being owned long-term by any
single object.

---

## 3. Dependency Diagram

```mermaid
graph LR
    subgraph Core_Delegates["shell_browser_extensions_core_delegates"]
        PMD[ElectronProcessManagerDelegate]
        KD[ElectronKioskDelegate]
        NUD[ElectronNavigationUIData]
    end

    subgraph Browser_Client["shell_browser_extensions_core_browser_client"]
        EBC[ElectronExtensionsBrowserClient]
    end

    subgraph Browser_Core["shell_browser_core_lifecycle"]
        BR[Browser]
    end

    subgraph Context["shell_browser_context"]
        BC[ElectronBrowserContext]
        Profile["Profile (forward-declared)"]
    end

    subgraph Extensions_System["shell_browser_extensions_core_system"]
        ExtSys[ElectronExtensionSystem]
    end

    PMD -. forward decl .-> BR
    PMD -. forward decl .-> Profile
    PMD -->|queries| BC
    KD -->|checked for| ExtSys
    NUD -->|used during navigation of| BC

    EBC -->|owns| PMD
    EBC -->|owns| KD

    click EBC "shell_browser_extensions_core_browser_client.md"
    click BR "shell_browser_core_lifecycle.md"
    click BC "shell_browser_context.md"
    click ExtSys "shell_browser_extensions_core_system.md"
```

Notes:
- `Browser` and `Profile` are only **forward-declared** in
  `electron_process_manager_delegate.h`; they represent the wider application
  singleton ([`Browser`](shell_browser_core_lifecycle.md)) and the
  Chromium-style profile concept that Electron generally maps onto
  [`ElectronBrowserContext`](shell_browser_context.md).
- The delegate implementations themselves are defined in corresponding `.cc`
  files (not shown in the core snippet) which include the real logic tying
  into `ElectronBrowserContext` and `ElectronExtensionSystem`.

---

## 4. Data Flow

### 4.1 Background Page Decision Flow

```mermaid
sequenceDiagram
    participant PM as extensions::ProcessManager
    participant PMD as ElectronProcessManagerDelegate
    participant BC as ElectronBrowserContext

    PM->>PMD: AreBackgroundPagesAllowedForContext(context)
    PMD->>BC: (optional) inspect context state
    PMD-->>PM: true/false

    PM->>PMD: IsExtensionBackgroundPageAllowed(context, extension)
    PMD-->>PM: true/false

    PM->>PMD: DeferCreatingStartupBackgroundHosts(context)
    PMD-->>PM: true/false
```

### 4.2 Navigation UI Data Lifecycle

```mermaid
sequenceDiagram
    participant UI as UI Thread (Navigation start)
    participant NUD as ElectronNavigationUIData
    participant Clone as Cloned NavigationUIData
    participant IO as IO/Network Thread

    UI->>NUD: new ElectronNavigationUIData(navigation_handle)
    UI->>NUD: SetExtensionNavigationUIData(data)
    UI->>NUD: Clone()
    NUD->>Clone: deep copy (incl. ExtensionNavigationUIData)
    UI->>IO: attach Clone to ResourceRequestInfo
    IO->>Clone: GetExtensionNavigationUIData()
    Clone-->>IO: extension attribution info
```

### 4.3 Kiosk Check Flow

```mermaid
sequenceDiagram
    participant API as Extension API (e.g. app.window)
    participant KD as ElectronKioskDelegate

    API->>KD: IsAutoLaunchedKioskApp(extension_id)
    KD-->>API: false (Electron has no kiosk session model)
```

---

## 5. Component Interaction with the Extensions Subsystem

```mermaid
graph TD
    EBC[ElectronExtensionsBrowserClient] -->|GetProcessManagerDelegate| PMD[ElectronProcessManagerDelegate]
    EBC -->|GetKioskDelegate| KD[ElectronKioskDelegate]
    EBC -->|CreateExtensionHostDelegate| EHD["ElectronExtensionHostDelegate\n(see shell_browser_extensions_core_api_client.md)"]
    EBC -->|GetComponentExtensionResourceManager| CERM["ElectronComponentExtensionResourceManager"]

    PM["extensions::ProcessManager"] -->|policy queries| PMD
    KioskAPI["Kiosk-aware extension APIs"] -->|queries| KD
    NavCode["content::NavigationHandle /\nExtensionNavigationThrottle"] -->|creates & clones| NUD[ElectronNavigationUIData]
    NavCode --> ResourceRequestInfo["network::ResourceRequest\nattribution"]
    NUD --> ResourceRequestInfo

    click EBC "shell_browser_extensions_core_browser_client.md"
```

---

## 6. How This Module Fits Into the Overall System

The `shell_browser_extensions_core_delegates` module is a **leaf-level
implementation module** within the broader Extensions Subsystem
(`shell_browser_extensions_core`). It does not contain business logic of its
own beyond simple policy answers; instead it exists to **satisfy interface
contracts** required by Chromium's extensions and content layers so that:

1. **[`ElectronExtensionsBrowserClient`](shell_browser_extensions_core_browser_client.md)**
   can be fully instantiated — Chromium's `ExtensionsBrowserClient` interface
   requires non-null `ProcessManagerDelegate` and `KioskDelegate` instances.
2. **Navigation code** (throttles, resource request pipelines — see
   [`shell_browser_main_parts_content_delegates`](shell_browser_main_parts_content_delegates.md))
   can correctly propagate extension-specific navigation context across
   thread boundaries.

### Relationship to sibling modules

- **[`shell_browser_extensions_core_browser_client`](shell_browser_extensions_core_browser_client.md)** —
  Direct owner/consumer of `ElectronProcessManagerDelegate` and
  `ElectronKioskDelegate`.
- **[`shell_browser_extensions_core_system`](shell_browser_extensions_core_system.md)** —
  The extension system whose background-page and startup-host creation
  behavior is gated by `ElectronProcessManagerDelegate`.
- **[`shell_browser_extensions_core_api_client`](shell_browser_extensions_core_api_client.md)** —
  Sibling delegate module providing API-client-level delegates
  (`ElectronExtensionHostDelegate`, `ElectronMessagingDelegate`, guest view
  delegates) that work alongside these process/kiosk/navigation delegates.
- **[`shell_browser_context`](shell_browser_context.md)** —
  Supplies the `BrowserContext`/`ElectronBrowserContext` instances passed into
  `ElectronProcessManagerDelegate`'s methods.
- **[`shell_browser_core_lifecycle`](shell_browser_core_lifecycle.md)** —
  Home of the `Browser` singleton forward-declared in this module; represents
  the app-wide lifecycle that extensions indirectly interact with (e.g., quit
  behavior interacting with background pages).
- **[`shell_browser_main_parts_content_delegates`](shell_browser_main_parts_content_delegates.md)** —
  Contains `ElectronNavigationThrottle` and related navigation-pipeline code
  that is the primary creator/consumer of `ElectronNavigationUIData`.

### Design Rationale

Electron intentionally keeps these delegates minimal:

- Electron apps typically run in a **single, developer-controlled process
  model** without Chrome's multi-profile, incognito, or ChromeOS kiosk-session
  concepts. Hence `ElectronKioskDelegate` and much of
  `ElectronProcessManagerDelegate`'s logic reduce to simple/permissive
  defaults.
- `ElectronNavigationUIData` exists purely as **plumbing** — it has no
  Electron-specific policy logic, it just ensures Chromium's own
  `ExtensionNavigationUIData` survives the UI-to-IO thread hop during
  navigation, which downstream extension APIs (e.g., web request blocking,
  `<webview>` attribution) rely on.

---

## 7. Class Diagram

```mermaid
classDiagram
    class ProcessManagerDelegate {
        <<interface>>
        +AreBackgroundPagesAllowedForContext()
        +IsExtensionBackgroundPageAllowed()
        +DeferCreatingStartupBackgroundHosts()
    }
    class ElectronProcessManagerDelegate {
        +ElectronProcessManagerDelegate()
        +~ElectronProcessManagerDelegate()
        +AreBackgroundPagesAllowedForContext(context) bool
        +IsExtensionBackgroundPageAllowed(context, extension) bool
        +DeferCreatingStartupBackgroundHosts(context) bool
    }
    ProcessManagerDelegate <|-- ElectronProcessManagerDelegate

    class KioskDelegate {
        <<interface>>
        +IsAutoLaunchedKioskApp(id)
    }
    class ElectronKioskDelegate {
        +ElectronKioskDelegate()
        +~ElectronKioskDelegate()
        +IsAutoLaunchedKioskApp(id) bool
    }
    KioskDelegate <|-- ElectronKioskDelegate

    class NavigationUIData {
        <<interface>>
        +Clone()
    }
    class ElectronNavigationUIData {
        -unique_ptr~ExtensionNavigationUIData~ extension_data_
        +ElectronNavigationUIData()
        +ElectronNavigationUIData(navigation_handle)
        +Clone() unique_ptr~NavigationUIData~
        +SetExtensionNavigationUIData(data)
        +GetExtensionNavigationUIData() ExtensionNavigationUIData*
    }
    NavigationUIData <|-- ElectronNavigationUIData
    ElectronNavigationUIData *-- "0..1" ExtensionNavigationUIData

    class ElectronExtensionsBrowserClient {
        -unique_ptr~ElectronProcessManagerDelegate~ process_manager_delegate_
        -unique_ptr~ElectronKioskDelegate~ kiosk_delegate_
        +GetProcessManagerDelegate() ProcessManagerDelegate*
        +GetKioskDelegate() KioskDelegate*
    }
    ElectronExtensionsBrowserClient --> ElectronProcessManagerDelegate
    ElectronExtensionsBrowserClient --> ElectronKioskDelegate
```

---

## 8. Summary

| Aspect | Detail |
|---|---|
| **Layer** | Browser process, Extensions subsystem (delegate layer) |
| **Pattern** | Delegate / Strategy pattern implementing Chromium interfaces |
| **Lifetime** | `ElectronProcessManagerDelegate` & `ElectronKioskDelegate`: owned by `ElectronExtensionsBrowserClient` (process lifetime). `ElectronNavigationUIData`: per-navigation, cloned across threads. |
| **Key Consumers** | `extensions::ProcessManager`, extension Kiosk-aware APIs, content navigation/network pipeline |
| **Extensibility** | To customize Electron's extension background-page or kiosk policy, modify the `.cc` implementations of these delegates; to add new per-navigation extension metadata, extend `ElectronNavigationUIData` |

For the broader extension bootstrap and client wiring, see
[`shell_browser_extensions_core_browser_client`](shell_browser_extensions_core_browser_client.md)
and [`shell_browser_extensions_core_system`](shell_browser_extensions_core_system.md).
