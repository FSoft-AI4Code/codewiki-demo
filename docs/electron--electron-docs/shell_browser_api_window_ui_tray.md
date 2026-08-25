# Shell Browser API — Window UI Tray Module

## Introduction

The `shell_browser_api_window_ui_tray` module implements Electron's **`Tray`** JavaScript API — the object that lets applications place an icon in the operating system's notification area (macOS menu bar, Windows system tray, or Linux status area). This module is the *Gin binding layer* that exposes native tray functionality to JavaScript; it wraps a platform-specific `TrayIcon` implementation and forwards native UI events (clicks, drags, balloon interactions, etc.) as EventEmitter events on the JS-facing `Tray` object.

This module is one of four siblings under the broader **Native Window & Menu Management** area (`shell_browser_api_window_ui`), alongside window (`shell_browser_api_window_ui_windows`), menu (`shell_browser_api_window_ui_menu`), and view (`shell_browser_api_window_ui_views`) bindings. It depends heavily on the platform-agnostic `TrayIcon` interface and its OS-specific implementations, documented in [Desktop_UI_Widgets_&_Dialogs.md](Desktop_UI_Widgets_&_Dialogs.md).

---

## Module Purpose

| Concern | Description |
|---|---|
| **Primary responsibility** | Expose a `Tray` gin-wrappable class to JS that creates, configures, and destroys a native system tray icon. |
| **Core file** | `shell/browser/api/electron_api_tray.h` |
| **Key class** | `electron::api::Tray` |
| **Pattern** | Bridge / Facade over platform-specific `TrayIcon` subclasses, using the PIMPL-like `tray_icon_` member. |
| **Event model** | Implements `TrayIconObserver` privately and re-emits native callbacks as gin `EventEmitterMixin` events (`click`, `double-click`, `right-click`, `drop`, `mouse-move`, etc.) |

---

## Component Overview

### `Tray` (electron::api::Tray)

`Tray` is defined in `shell/browser/api/electron_api_tray.h` and is the sole core component of this module. It combines multiple gin-helper mixins to provide full JS object lifecycle management:

- **`gin_helper::DeprecatedWrappable<Tray>`** — provides the V8 wrapper/unwrap machinery (see [Gin_Helper.md](Gin_Helper.md)).
- **`gin_helper::EventEmitterMixin<Tray>`** — allows `Tray` instances to emit Node.js-style events to JS listeners.
- **`gin_helper::Constructible<Tray>`** — supports `new Tray(...)` construction from JS via the static `New()` factory.
- **`gin_helper::CleanedUpAtExit`** — ensures the native tray icon is torn down safely during app shutdown (`WillBeDestroyed()`).
- **`gin_helper::Pinnable<Tray>`** — keeps the JS wrapper alive as long as necessary (pinned) so short-lived script references don't prematurely garbage collect an active tray icon.
- **`TrayIconObserver` (private)** — receives raw native UI events and translates them into JS-visible events.

#### Key Responsibilities

1. **Construction** (`Tray::New`) — Accepts an image (path, `NativeImage`, or empty), optional GUID (Windows tray icon identity persistence), and general `gin::Arguments`. Internally instantiates a platform-specific `TrayIcon` via `TrayIcon::Create(guid)`.
2. **Image & Appearance** — `SetImage`, `SetPressedImage`, `SetToolTip`, `SetTitle`/`GetTitle` (macOS-only text next to the icon).
3. **Context Menu** — `SetContextMenu`, `PopUpContextMenu`, `CloseContextMenu` bridge to the JS `Menu` object (see [shell_browser_api_window_ui_menu.md](shell_browser_api_window_ui_menu.md)); the menu reference is retained in `menu_` (a `v8::Global<v8::Value>`) to keep the underlying `ElectronMenuModel` alive.
4. **Notifications** — `DisplayBalloon` / `RemoveBalloon` (Windows/Linux balloon-style notifications distinct from the cross-platform `Notification` API — see [Platform-Specific_Integration.md](Platform-Specific_Integration.md)).
5. **Lifecycle** — `Destroy()`, `IsDestroyed()`, `CheckAlive()` guard against use-after-free once the tray icon is removed.
6. **Event forwarding** — Implements every `TrayIconObserver` callback (`OnClicked`, `OnDoubleClicked`, `OnRightClicked`, `OnMiddleClicked`, `OnBalloonShow/Clicked/Closed`, `OnDrop*`, `OnDragEntered/Exited/Ended`, `OnMouse*`) and re-emits them as JS events with position/modifier metadata.
7. **GUID support** (`GetGUID`) — Windows allows tray icons to persist an identity (GUID) across app restarts so the OS remembers taskbar pinning/position.

---

## Architecture

### Class Relationships

```mermaid
classDiagram
    class Tray {
        -v8::Global~v8::Value~ menu_
        -optional~base::Uuid~ guid_
        -unique_ptr~TrayIcon~ tray_icon_
        +New(thrower, image, guid, args) Handle~Tray~
        +SetImage(image)
        +SetPressedImage(image)
        +SetToolTip(tool_tip)
        +SetTitle(title, options)
        +GetTitle() string
        +SetContextMenu(arg)
        +PopUpContextMenu(args)
        +CloseContextMenu()
        +DisplayBalloon(options)
        +RemoveBalloon()
        +Focus()
        +GetBounds() Rect
        +GetGUID() Value
        +Destroy()
        +IsDestroyed() bool
        -CheckAlive() bool
    }

    class TrayIconObserver {
        <<interface>>
        +OnClicked()
        +OnDoubleClicked()
        +OnRightClicked()
        +OnMiddleClicked()
        +OnBalloonShow()
        +OnBalloonClicked()
        +OnBalloonClosed()
        +OnDrop()
        +OnDropFiles()
        +OnDropText()
        +OnDragEntered()
        +OnDragExited()
        +OnDragEnded()
        +OnMouseUp()
        +OnMouseDown()
        +OnMouseEntered()
        +OnMouseExited()
        +OnMouseMoved()
    }

    class TrayIcon {
        <<abstract>>
        +Create(guid) TrayIcon*
        +SetImage(image)
        +SetPressedImage(image)
        +SetToolTip(tool_tip)
        +SetContextMenu(menu_model)
        +PopUpContextMenu(pos, menu_model)
        +CloseContextMenu()
        +DisplayBalloon(options)
        +RemoveBalloon()
        +Focus()
        +GetBounds() Rect
        +AddObserver(obs)
        +RemoveObserver(obs)
        +NotifyClicked()
        +NotifyDoubleClicked()
        +NotifyRightClicked()
        +NotifyMiddleClicked()
        +NotifyBalloonShow()
        +NotifyDrop*()
        +NotifyDrag*()
        +NotifyMouse*()
    }

    class TrayIconCocoa {
        -StatusItemView status_item_view_
        -ElectronMenuController menu_
    }
    class TrayIconLinux {
        -StatusIconLinuxDbus status_icon_dbus_
        -StatusIconGtk status_icon_gtk_
    }
    class NotifyIcon {
        -HWND window_
        -GUID guid_
        -MenuRunner menu_runner_
    }

    class ElectronMenuModel
    class Menu

    Tray --|> TrayIconObserver : implements (private)
    Tray "1" o-- "1" TrayIcon : owns
    Tray ..> Menu : references (menu_)
    TrayIcon <|-- TrayIconCocoa
    TrayIcon <|-- TrayIconLinux
    TrayIcon <|-- NotifyIcon
    TrayIcon ..> ElectronMenuModel : SetContextMenu()
    Tray ..> ElectronMenuModel : via Menu wrapper
```

### Platform Abstraction

The `Tray` class never talks to OS APIs directly. It delegates all rendering/interaction to a `TrayIcon` instance created via the platform factory `TrayIcon::Create()`. Platform implementations live in [Desktop_UI_Widgets_&_Dialogs.md](Desktop_UI_Widgets_&_Dialogs.md) under the "Tray_Icon" sub-module:

| Platform | Implementation | Notes |
|---|---|---|
| macOS | `TrayIconCocoa` | Wraps `NSStatusItem` via a custom `StatusItemView`; menu shown through `ElectronMenuController`. |
| Linux | `TrayIconLinux` | Delegates to either D-Bus (`StatusIconLinuxDbus`) or GTK (`StatusIconGtk`) status icon backends depending on desktop environment support. |
| Windows | `NotifyIcon` (owned by `NotifyIconHost`) | Uses the Windows Shell notification area API (`Shell_NotifyIcon`); supports GUID-based icon identity and `views::MenuRunner` for context menus. |

---

## Data Flow

### Tray Creation Flow

```mermaid
sequenceDiagram
    participant JS as JavaScript (new Tray(icon))
    participant Tray as Tray::New (C++)
    participant Factory as TrayIcon::Create
    participant Native as Platform TrayIcon (Cocoa/Linux/NotifyIcon)
    participant OS as OS Shell (NSStatusItem/D-Bus/Shell_NotifyIcon)

    JS->>Tray: new Tray(image, guid?)
    Tray->>Tray: resolve NativeImage from arg
    Tray->>Factory: TrayIcon::Create(guid)
    Factory->>Native: instantiate platform TrayIcon subclass
    Native->>OS: register icon in system tray
    Tray->>Native: SetImage(image)
    Tray->>Native: AddObserver(this)
    Tray-->>JS: return wrapped Tray handle
```

### Native Event → JS Event Flow

```mermaid
sequenceDiagram
    participant OS as OS Shell
    participant Native as TrayIcon subclass
    participant Base as TrayIcon (NotifyXxx)
    participant Tray as Tray (TrayIconObserver)
    participant JS as JS EventEmitter listeners

    OS->>Native: user clicks icon
    Native->>Base: NotifyClicked(bounds, location, modifiers)
    Base->>Tray: OnClicked(bounds, location, modifiers)
    Tray->>JS: Emit("click", event, bounds, position)
```

### Context Menu Flow

```mermaid
sequenceDiagram
    participant JS as JS (tray.setContextMenu(menu))
    participant Tray as Tray::SetContextMenu
    participant Menu as Menu (api)
    participant Model as ElectronMenuModel
    participant Native as TrayIcon::SetContextMenu

    JS->>Tray: setContextMenu(menu)
    Tray->>Tray: store menu in menu_ (v8::Global)
    Tray->>Menu: unwrap gin handle
    Menu->>Model: expose underlying model()
    Tray->>Native: SetContextMenu(model_ptr)
    Note over Native: subsequent right-click / PopUpContextMenu shows model
```

---

## Integration Points

### Dependencies

```mermaid
graph LR
    Tray["Tray (electron_api_tray.h)"]
    TrayIcon["TrayIcon (ui/tray_icon.h)"]
    TrayIconObserver["TrayIconObserver"]
    Menu["Menu (api/electron_api_menu.h)"]
    MenuModel["ElectronMenuModel"]
    GinHelper["gin_helper mixins\n(Wrappable, EventEmitterMixin,\nConstructible, Pinnable,\nCleanedUpAtExit)"]
    NativeImage["gfx::Image / NativeImage"]
    GuidConverter["guid_converter"]

    Tray --> TrayIcon
    Tray -.implements.-> TrayIconObserver
    Tray --> Menu
    Tray --> MenuModel
    Tray --> GinHelper
    Tray --> NativeImage
    Tray --> GuidConverter
```

- **`shell_browser_api_window_ui_menu`** — `Tray::SetContextMenu`/`PopUpContextMenu` take a `Menu` (or `BaseWindow`-adjacent) JS object and extract its `ElectronMenuModel*`, tying tray context menus to the same menu infrastructure used by application and window menus. See [shell_browser_api_window_ui_menu.md](shell_browser_api_window_ui_menu.md).
- **`Desktop_UI_Widgets_&_Dialogs` (Tray_Icon sub-module)** — Supplies the abstract `TrayIcon`/`TrayIconObserver` interfaces and every OS-specific backend (`TrayIconCocoa`, `TrayIconLinux`, `NotifyIcon`/`NotifyIconHost`). See [Desktop_UI_Widgets_&_Dialogs.md](Desktop_UI_Widgets_&_Dialogs.md).
- **`Common_Native_Gin_Infrastructure`** — `Tray` relies on `gin_helper::Wrappable`, `EventEmitterMixin`, `Constructible`, `Pinnable`, `CleanedUpAtExit`, `ErrorThrower`, and `Dictionary`/`Arguments` conversion helpers. See [Gin_Helper.md](Gin_Helper.md) and [Common_API.md](Common_API.md) (for `NativeImage` conversions used when resolving the `image` argument).
- **`Common_Native_Gin_Infrastructure` (Gin_Converters)** — Uses `image_converter.h` to convert JS image arguments (path string, buffer, or `NativeImage` handle) into `gfx::Image`.
- **`shell_browser_api_window_ui_windows` / `_views`** — Sibling bindings sharing the same parent module (`shell_browser_api_window_ui`); not directly coupled to `Tray` but part of the same JS `api` object surface exposed to renderer/main scripts.

### Position within the Overall System

```mermaid
graph TB
    subgraph "Native_Window_&_Menu_Management"
        WinUI["shell_browser_api_window_ui"]
        Windows["shell_browser_api_window_ui_windows\n(BaseWindow / BrowserWindow)"]
        MenuMod["shell_browser_api_window_ui_menu\n(Menu / MenuMac / MenuViews)"]
        TrayMod["shell_browser_api_window_ui_tray\n(Tray) — this module"]
        Views["shell_browser_api_window_ui_views\n(View / ImageView)"]
        NativeWin["shell_browser_native_window\n(NativeWindow*)"]
    end

    WinUI --> Windows
    WinUI --> MenuMod
    WinUI --> TrayMod
    WinUI --> Views
    TrayMod --> MenuMod
    Windows --> NativeWin
    MenuMod --> NativeWin

    subgraph "Desktop_UI_Widgets_&_Dialogs"
        TrayIconIface["Tray_Icon sub-module\n(TrayIcon, TrayIconCocoa,\nTrayIconLinux, NotifyIcon)"]
    end
    TrayMod --> TrayIconIface

    subgraph "Common_Native_Gin_Infrastructure"
        GinHelperMod["Gin_Helper"]
        GinConvMod["Gin_Converters"]
    end
    TrayMod --> GinHelperMod
    TrayMod --> GinConvMod
```

---

## Lifecycle & Memory Management

```mermaid
stateDiagram-v2
    [*] --> Constructed : Tray_New (TrayIcon Create + observer registration)
    Constructed --> Active : SetImage / SetToolTip / SetContextMenu
    Active --> Active : Native events emit JS events
    Active --> Destroyed : Destroy or app exit (CleanedUpAtExit)
    Destroyed --> [*] : tray_icon_ reset, observer removed via dtor

    note right of Active
        Pinnable keeps JS wrapper alive
        while tray_icon_ is active, even
        if no JS reference remains, so
        native icon persists until
        explicitly destroyed.
    end note
```

Key points:
- **`CheckAlive()`** is called at the top of most JS-exposed methods to throw a JS error rather than crash if `Destroy()` was already called.
- **`WillBeDestroyed()`** (from `CleanedUpAtExit`) guarantees native cleanup happens during Electron's app shutdown sequence, preventing dangling OS tray icons.
- **`Pinnable<Tray>`** prevents premature garbage collection: since a tray icon has externally visible OS effects, it must stay alive independent of JS reachability until explicitly destroyed.

---

## Summary

The `shell_browser_api_window_ui_tray` module is a thin, single-class binding (`Tray`) that adapts the cross-platform `TrayIcon` abstraction (and its Cocoa/Linux/Windows implementations) into Electron's JavaScript API surface. It cleanly separates concerns:

- **Native platform logic** lives in `TrayIcon` subclasses (documented under [Desktop_UI_Widgets_&_Dialogs.md](Desktop_UI_Widgets_&_Dialogs.md)).
- **JS object lifecycle & event plumbing** lives in this module, using shared gin-helper infrastructure ([Gin_Helper.md](Gin_Helper.md)).
- **Menu integration** is delegated to the sibling menu module ([shell_browser_api_window_ui_menu.md](shell_browser_api_window_ui_menu.md)).

This separation allows the JS-facing `Tray` API to remain stable across platforms while each OS's native tray/status-icon quirks are encapsulated behind the `TrayIcon` interface.
