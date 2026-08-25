# Shell Browser API: Window & UI

## Introduction

The **`shell_browser_api_window_ui`** module implements the browser-process JavaScript-visible APIs for Electron's core desktop UI primitives:

- **Windows** — `BaseWindow` and `BrowserWindow`, the classes that back Electron's `BrowserWindow`/`BaseWindow` JS classes.
- **Menus** — `Menu` and its platform-specialized subclasses `MenuMac` (Cocoa native menus) and `MenuViews` (Chromium Views-based menus on Windows/Linux).
- **Tray** — `Tray`, backing the JS `Tray` (system tray icon) class.
- **Views** — the low-level `View` composable UI primitive (and `ImageView`), which underlies `BrowserWindow`'s content view tree, plus small event-related helpers (`electron_api_event_emitter.h`, `ui_event.h`) shared by all `gin_helper::EventEmitter`-derived wrappers in this module.

These classes are all exposed to Node/Chromium-embedder JavaScript through Electron's `gin`/`gin_helper` binding layer (see [Common_Native_Gin_Infrastructure](Common_Native_Gin_Infrastructure.md)) and sit on top of the platform-neutral windowing primitives documented in [shell_browser_native_window](shell_browser_native_window.md).

This module is part of the larger **Native_Window_&_Menu_Management** area of Electron's browser process, and works closely with:

- [shell_browser_native_window](shell_browser_native_window.md) – the underlying `NativeWindow`/`NativeWindowMac`/`NativeWindowViews` platform window implementations that `BaseWindow` wraps.
- [Window_List](Window_List.md) – global registry of all open `NativeWindow` instances.
- [Menu_(Model_&_Views)](Menu_(Model_&_Views).md) – the `ElectronMenuModel` and platform menu-controller/menu-bar implementations that back `Menu`.
- [Tray_Icon](Tray_Icon.md) – the platform `TrayIcon` implementations (Cocoa, GTK, Windows) that `Tray` drives.
- [shell_browser_api_webcontents](shell_browser_api_webcontents.md) – `WebContents`, which every `BrowserWindow` owns and renders.
- [Common_Native_Gin_Infrastructure](Common_Native_Gin_Infrastructure.md) – `gin_helper` wrapping, event-emitter, and converter infrastructure used pervasively here.

## Architecture Overview

```mermaid
graph TB
    subgraph "shell_browser_api_window_ui"
        BaseWindow["BaseWindow\n(electron_api_base_window.h)"]
        BrowserWindow["BrowserWindow\n(electron_api_browser_window.h)"]
        Menu["Menu\n(electron_api_menu.h)"]
        MenuMac["MenuMac\n(electron_api_menu_mac.h)"]
        MenuViews["MenuViews\n(electron_api_menu_views.h)"]
        Tray["Tray\n(electron_api_tray.h)"]
        View["View\n(electron_api_view.h/.cc)"]
        ImageView["ImageView\n(views/electron_api_image_view.h)"]
        JSLayoutManager["JSLayoutManager\n(electron_api_view.cc)"]
        EventEmitterHelper["GetEventEmitterPrototype\n(electron_api_event_emitter.h)"]
        UiEvent["CreateEventFromFlags\n(ui_event.h)"]
    end

    BrowserWindow -->|extends| BaseWindow
    MenuMac -->|extends| Menu
    MenuViews -->|extends| Menu
    ImageView -->|extends| View
    View -->|uses| JSLayoutManager
    BaseWindow -->|manages| View
    BrowserWindow -->|owns content view / web contents| WebContents["WebContents\n(shell_browser_api_webcontents)"]
    BaseWindow -->|wraps| NativeWindow["NativeWindow\n(shell_browser_native_window)"]
    BaseWindow -->|SetMenu / RemoveMenu| Menu
    Tray -->|PopUpContextMenu| Menu
    Tray -->|drives| TrayIcon["TrayIcon\n(Tray_Icon module)"]
    Menu -->|"model()"| ElectronMenuModel["ElectronMenuModel - Menu Model and Views module"]
    BaseWindow -.->|EventEmitterMixin uses| EventEmitterHelper
    View -.->|EventEmitter uses| EventEmitterHelper
    BaseWindow -.->|mouse/keyboard events| UiEvent
```

## Sub-modules

| Sub-module | Description | Documentation |
|---|---|---|
| **Windows** | `BaseWindow` (generic window API surface: bounds, state, menu, touch bar, taskbar integration) and `BrowserWindow` (window that hosts a `WebContents`). | [shell_browser_api_window_ui_windows](shell_browser_api_window_ui_windows.md) |
| **Menu** | `Menu` base class plus platform popup implementations `MenuMac` and `MenuViews`. | [shell_browser_api_window_ui_menu](shell_browser_api_window_ui_menu.md) |
| **Tray** | `Tray` system tray icon API, including balloon notifications, context menu, and mouse/drag event forwarding. | [shell_browser_api_window_ui_tray](shell_browser_api_window_ui_tray.md) |
| **Views & Event Helpers** | `View` composable UI element, `ImageView`, `JSLayoutManager` (JS-driven layout manager), and shared event-emitter/UI-event helper functions. | [shell_browser_api_window_ui_views](shell_browser_api_window_ui_views.md) |

## High-Level Data & Control Flow

```mermaid
sequenceDiagram
    participant JS as JavaScript (main process)
    participant BW as BrowserWindow (api)
    participant NW as NativeWindow
    participant V as View tree
    participant M as Menu
    participant T as Tray

    JS->>BW: new BrowserWindow(options)
    BW->>NW: create platform NativeWindow
    BW->>V: create root ContentView
    JS->>BW: win.setMenu(menu)
    BW->>M: attach ElectronMenuModel
    JS->>T: new Tray(image)
    T->>T: create platform TrayIcon
    JS->>T: tray.setContextMenu(menu)
    T->>M: PopUpContextMenu()
    NW-->>BW: NativeWindowObserver callbacks (resize, focus, close...)
    BW-->>JS: emit('resize' | 'focus' | 'closed' ...)
```

## Key Cross-Module Relationships

- **`BaseWindow`** wraps a platform `electron::NativeWindow` (see [shell_browser_native_window](shell_browser_native_window.md)) and implements `NativeWindowObserver` to translate native window lifecycle/state events into JS `EventEmitter` events.
- **`BrowserWindow`** extends `BaseWindow` and additionally observes `content::WebContentsObserver` / `ExtendedWebContentsObserver` to bridge a `WebContents` (see [shell_browser_api_webcontents](shell_browser_api_webcontents.md)) into the window's lifecycle (title updates, activation, close confirmation dialogs, etc).
- **`Menu`** delegates command dispatch and accelerator resolution through `ElectronMenuModel::Delegate`/`Observer` (see [Menu_(Model_&_Views)](Menu_(Model_&_Views).md)), while `MenuMac`/`MenuViews` provide the actual popup/rendering using Cocoa's `ElectronMenuController` or `views::MenuRunner` respectively.
- **`Tray`** owns a platform `TrayIcon` (see [Tray_Icon](Tray_Icon.md)) and can pop up a `Menu` as its context menu.
- **`View`**/`ImageView` are the building blocks for `BaseWindow`'s content view hierarchy and for standalone composable UI (`WebContentsView`, `ImageView`, custom layouts via `JSLayoutManager`).
- All classes above rely on the shared `gin_helper` wrapping/constructing infrastructure (`Wrappable`, `Constructible`, `EventEmitterMixin`, `Pinnable`, `Handle`) documented in [Common_Native_Gin_Infrastructure](Common_Native_Gin_Infrastructure.md).

## Where This Module Fits

```mermaid
graph LR
    A[Public_JS_API_Bindings] --> B[shell_browser_api_window_ui]
    B --> C[shell_browser_native_window]
    B --> D[shell_browser_api_webcontents]
    B --> E["Menu_(Model_&_Views)"]
    B --> F[Tray_Icon]
    B --> G[Window_List]
    B --> H[Common_Native_Gin_Infrastructure]
    C --> I[Browser_Process_Core_&_Lifecycle]
```

`shell_browser_api_window_ui` is the JavaScript-facing veneer of Electron's **Native_Window_&_Menu_Management** area: it turns low-level, platform-specific window/menu/tray/view primitives into a uniform, cross-platform JS API surface consumed by app developers.
