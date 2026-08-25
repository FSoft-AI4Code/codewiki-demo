# Shell Browser Native Window (macOS)

## Introduction

The `shell_browser_native_window_mac` module provides the **macOS-specific implementation** of Electron's cross-platform `NativeWindow` abstraction. It is defined primarily in `shell/browser/native_window_mac.h` and its companion Objective-C++ implementation, and is responsible for translating the platform-agnostic windowing API used throughout Electron's C++ codebase into native Cocoa (`NSWindow`, `NSView`, `NSToolbar`/Touch Bar, etc.) behavior.

This module is a sibling of [shell_browser_native_window_views](shell_browser_native_window_views.md) (Windows/Linux via `views::Widget`) under the parent [shell_browser_native_window](shell_browser_native_window.md) module, and both extend the shared contract defined in [shell_browser_native_window_core](shell_browser_native_window_core.md) (`NativeWindow`, `NativeWindowObserver`).

`NativeWindowMac` is the C++ "shell" object that owns and coordinates a constellation of Objective-C helper classes (declared as forward-declared `@class`/`@interface` types in the header and implemented in Cocoa-specific `.mm` files) that implement the actual AppKit behavior — window delegate callbacks, Touch Bar support, Quick Look previews, and traffic-light (window control button) positioning.

---

## Purpose & Core Functionality

`NativeWindowMac` implements every pure-virtual and platform-conditional method declared by the base `NativeWindow` class (see [shell_browser_native_window_core](shell_browser_native_window_core.md)) for macOS, including:

- **Window lifecycle**: `Show`, `Hide`, `Close`, `CloseImmediately`, `Focus`, `Minimize`, `Restore`, `Maximize`/`Unmaximize`.
- **Bounds & sizing**: `SetBounds`, `GetBounds`, `GetNormalBounds`, `SetSizeConstraints`, `SetAspectRatio`, and mac-specific zoom-frame tracking (`default_frame_for_zoom_`) needed because macOS's "best fit" zoom logic can override requested aspect ratios.
- **Window chrome/state**: resizable/movable/minimizable/maximizable/closable flags, always-on-top z-order levels, opacity, background color, shadow control, and document-edited/represented-filename metadata (mapped to macOS proxy-icon and edited-dot UI).
- **Fullscreen modes**: native fullscreen (`SetFullScreen`), Simple (pre-Lion) Fullscreen (`SetSimpleFullScreen`), and Kiosk mode (`SetKiosk`), including presentation-option save/restore and deferred-close handling to avoid AppKit fullscreen-transition lockups.
- **Traffic lights / window buttons**: custom positioning and visibility of the close/minimize/zoom buttons via `WindowButtonsProxy`, including redraw-on-demand (`RedrawTrafficLights`) for frameless/hidden-titlebar windows.
- **Touch Bar integration**: `SetTouchBar`, `RefreshTouchBarItem`, `SetEscapeTouchBarItem`, delegated to `ElectronTouchBar`.
- **Tabbed windows**: native macOS window tabbing (`SelectNextTab`, `MergeAllWindows`, `AddTabbedWindow`, tabbing identifiers).
- **Quick Look file preview**: `PreviewFile`/`CloseFilePreview` via `ElectronPreviewItem`.
- **Vibrancy & visual effects**: translucent/vibrant materials rendered through a `views::NativeViewHost` (`vibrant_native_view_host_`).
- **Parent/child window relationships**: attach/detach/remove child `NSWindow`s while respecting visibility state.
- **OS integration hooks**: `ui::NativeThemeObserver` (dark mode changes) and `display::DisplayObserver` (display metric changes, e.g. for repositioning/redrawing on monitor changes).

## Architecture

`NativeWindowMac` acts as a C++ facade/coordinator. It does not itself subclass `NSWindow`; instead it owns (via `__strong` Objective-C references) a set of collaborator objects that implement AppKit protocols and forward events back into the C++ object.

```mermaid
classDiagram
    class NativeWindow {
        <<abstract>>
        +Show()
        +Close()
        +SetBounds()
        +SetFullScreen()
        +AddObserver()
    }

    class NativeWindowMac {
        -ElectronNSWindow* window_
        -ElectronNSWindowDelegate* window_delegate_
        -ElectronPreviewItem* preview_item_
        -ElectronTouchBar* touch_bar_
        -WindowButtonsProxy* buttons_proxy_
        -unique_ptr~RootViewMac~ root_view_
        -unique_ptr~NativeAppWindowFrameViewMacClient~ frame_view_client_
        +SetTouchBar()
        +PreviewFile()
        +SetVibrancy()
        +SetSimpleFullScreen()
    }

    class ElectronNSWindow {
        <<Cocoa NSWindow subclass>>
    }
    class ElectronNSWindowDelegate {
        <<NSWindowDelegate>>
    }
    class ElectronPreviewItem {
        <<QLPreviewItem>>
    }
    class ElectronTouchBar {
        <<NSTouchBarDelegate>>
    }
    class WindowButtonsProxy {
        <<traffic-light positioning>>
    }
    class RootViewMac {
        <<views::View>>
    }
    class ElectronNativeWidgetMac {
        <<views::NativeWidgetMac>>
    }
    class NativeAppWindowFrameViewMacClient

    NativeWindow <|-- NativeWindowMac
    NativeWindowMac "1" o-- "1" ElectronNSWindow
    NativeWindowMac "1" o-- "1" ElectronNSWindowDelegate
    NativeWindowMac "1" o-- "0..1" ElectronPreviewItem
    NativeWindowMac "1" o-- "0..1" ElectronTouchBar
    NativeWindowMac "1" o-- "0..1" WindowButtonsProxy
    NativeWindowMac "1" o-- "1" RootViewMac
    NativeWindowMac "1" o-- "0..1" NativeAppWindowFrameViewMacClient
    NativeWindowMac ..> ElectronNativeWidgetMac : creates via Widget
    ElectronNSWindowDelegate --> NativeWindowMac : callbacks
```

### Key Collaborators

| Component | Role |
|---|---|
| `ElectronNSWindow` | Custom `NSWindow` subclass that backs the `views::Widget`; overrides window behaviors (e.g., key window handling, style mask enforcement) needed by Electron. |
| `ElectronNSWindowDelegate` | Implements `NSWindowDelegate` methods (resize, move, fullscreen transitions, close) and forwards them as `Notify*` calls into `NativeWindowMac`/`NativeWindow`. |
| `ElectronPreviewItem` | Implements `QLPreviewItem` to support `PreviewFile`/`CloseFilePreview` (Quick Look). |
| `ElectronTouchBar` | Implements `NSTouchBarDelegate`, builds `NSTouchBarItem`s from `gin_helper::PersistentDictionary` specs supplied through `SetTouchBar`. |
| `WindowButtonsProxy` | Manages the position/visibility of the native close/minimize/zoom "traffic light" buttons, used for frameless and custom-titlebar windows. |
| `RootViewMac` | A `views::View` subclass that anchors the Views-based content view (e.g. `BrowserView`) inside the native Cocoa window's content view; also defines min/max size for the Views hierarchy. |
| `NativeAppWindowFrameViewMacClient` | Provides app-specific frame customization hooks consumed by non-client frame view creation (`CreateNonClientFrameView`). |
| `ElectronNativeWidgetMac` | (`views::NativeWidgetMac` subclass, declared in `shell/browser/ui/cocoa/electron_native_widget_mac.h`) creates the underlying `NativeWidgetMacNSWindow`/`ElectronNSWindow` and connects the Views `Widget` machinery to `NativeWindowMac`. |

These Cocoa-facing types are further described in the [Cocoa_UI](Cocoa_UI.md) documentation, which covers `electron_ns_window.h`, `electron_ns_window_delegate.h`, `electron_touch_bar.h`, `window_buttons_proxy.h`, `root_view_mac.h`, `views_delegate_mac.h`, and `electron_bundle_mover.h` in detail.

## Relationship to Other Modules

```mermaid
flowchart TB
    subgraph Core["shell_browser_native_window_core"]
        NW[NativeWindow]
        NWO[NativeWindowObserver]
    end

    subgraph Mac["shell_browser_native_window_mac (this module)"]
        NWM[NativeWindowMac]
    end

    subgraph Views["shell_browser_native_window_views"]
        NWV[NativeWindowViews]
    end

    subgraph CocoaUI["Cocoa_UI"]
        ENSW[ElectronNSWindow]
        ENSWD[ElectronNSWindowDelegate]
        ENWM[ElectronNativeWidgetMac]
        WBP[WindowButtonsProxy]
        RVM[RootViewMac]
    end

    subgraph WindowUI["shell_browser_api_window_ui"]
        BW[BrowserWindow]
        BaseW[BaseWindow]
        MenuMac[MenuMac]
    end

    subgraph WinList["Window_List"]
        WL[WindowList]
    end

    NWM -.->|implements| NW
    NWV -.->|implements| NW
    NWM --> ENSW
    NWM --> ENSWD
    NWM --> ENWM
    NWM --> WBP
    NWM --> RVM
    BW --> NW
    BaseW --> NW
    MenuMac --> NWM
    WL --> NW
    NWM --> NWO
```

- **[shell_browser_native_window_core](shell_browser_native_window_core.md)**: defines the abstract `NativeWindow` interface and `NativeWindowObserver`; `NativeWindowMac` is one of the concrete implementations (alongside `NativeWindowViews` for Windows/Linux — see [shell_browser_native_window_views](shell_browser_native_window_views.md)).
- **[shell_browser_native_window_support](shell_browser_native_window_support.md)**: `ChildWebContentsTracker` and `ExtendedWebContentsObserver` used generically by window implementations for managing child web contents / dragging regions.
- **[Cocoa_UI](Cocoa_UI.md)**: houses the concrete Objective-C++ implementations of the collaborator classes referenced by `NativeWindowMac` (`ElectronNSWindow`, `ElectronNSWindowDelegate`, `ElectronTouchBar`, `WindowButtonsProxy`, `RootViewMac`, `ElectronNativeWidgetMac`, `ViewsDelegateMac`, `ElectronBundleMover`).
- **[shell_browser_api_window_ui](shell_browser_api_window_ui.md)**: the JS-facing `BaseWindow`/`BrowserWindow` gin wrappers that create and drive `NativeWindow`/`NativeWindowMac` instances in response to renderer/main-process JS API calls.
- **[Menu_(Model_&_Views)](Menu_(Model_&_Views).md)**: `MenuMac` (in `electron_api_menu_mac.h`) attaches native menus to a `NativeWindow`, including mac-specific popup behavior.
- **[Window_List](Window_List.md)**: `WindowList`/`WindowListObserver` track all live `NativeWindow` instances (including `NativeWindowMac`) for app-wide window enumeration (e.g., `app.getAllWindows()` gin API, macOS "quit when all windows closed" logic).
- **[Tray_Icon](Tray_Icon.md)**: `TrayIconCocoa` shares some Cocoa infrastructure conventions (menu controllers, status items) with this module but is a distinct top-level UI surface.
- **[Autofill_Popup](Autofill_Popup.md)** and **OSR (Offscreen Rendering)** consumers rely on `NativeWindow::GetNativeView()`/`GetNativeWindow()` exposed here to anchor overlay UI.

## Data / Control Flow

### Window Creation Flow

```mermaid
sequenceDiagram
    participant JS as JS (BrowserWindow ctor)
    participant BW as api::BrowserWindow
    participant NW as NativeWindow::Create
    participant NWM as NativeWindowMac
    participant Widget as views::Widget
    participant ENWM as ElectronNativeWidgetMac
    participant NSWin as ElectronNSWindow

    JS->>BW: new BrowserWindow(options)
    BW->>NW: NativeWindow::Create(options, parent)
    NW->>NWM: new NativeWindowMac(options, parent)
    NWM->>Widget: Init(WidgetInitParams)
    Widget->>ENWM: CreateNativeWidget()
    ENWM->>NSWin: CreateNSWindow(params)
    NSWin-->>ENWM: ElectronNSWindow instance
    NWM->>NWM: AddContentViewLayers()
    NWM->>NWM: root_view_ = make_unique<RootViewMac>(this)
    NWM-->>BW: NativeWindowMac* (owned by Widget/BrowserWindow)
```

### Fullscreen Transition Flow (illustrating deferred-close handling)

```mermaid
sequenceDiagram
    participant JS as JS API
    participant NWM as NativeWindowMac
    participant Del as ElectronNSWindowDelegate
    participant NSWin as ElectronNSWindow (AppKit)

    JS->>NWM: SetFullScreen(true)
    NWM->>NSWin: toggleFullScreen:
    NSWin->>Del: windowWillEnterFullScreen:
    Del->>NWM: NotifyWindowWillEnterFullScreen()
    NSWin->>Del: windowDidEnterFullScreen:
    Del->>NWM: NotifyWindowEnterFullScreen()
    Note over NWM: is_transitioning_fullscreen_ = true during transition
    JS->>NWM: Close() (during transition)
    NWM->>NWM: SetHasDeferredWindowClose(true)
    Note over NWM: Actual close deferred until transition completes
    NSWin->>Del: windowDidEnterFullScreen: (completes)
    NWM->>NWM: HandleDeferredClose() -> [NSWindow close]
```

### Touch Bar Update Flow

```mermaid
sequenceDiagram
    participant JS as JS (win.setTouchBar(items))
    participant NWM as NativeWindowMac
    participant TB as ElectronTouchBar
    participant AppKit as NSTouchBar (AppKit)

    JS->>NWM: SetTouchBar(items)
    NWM->>TB: init/update with PersistentDictionary items
    TB->>AppKit: build NSTouchBarItems
    AppKit-->>TB: user interacts with item
    TB->>NWM: NotifyTouchBarItemInteraction(item_id, details)
    NWM->>NWM: NotifyTouchBarItemInteraction() (base NativeWindow)
    NWM-->>JS: emits 'touch-bar-interaction' event
```

## Key State & Design Notes

- **Weak vs. strong references**: `window_` (the `ElectronNSWindow*`) is a *weak* reference — its lifetime is owned by the `views::Widget`/`ElectronNativeWidgetMac` machinery. The delegate, preview item, touch bar, and buttons proxy are held with `__strong` ARC references directly by `NativeWindowMac`.
- **Deferred close pattern**: Because closing an `NSWindow` mid-fullscreen-transition can hang AppKit, `has_deferred_window_close_` + `HandleDeferredClose()` implement a safe deferred-close pattern coordinated with the `ElectronNSWindowDelegate` fullscreen callbacks.
- **Zoom/maximize semantics on macOS**: Since native macOS "zoom" (green button) doesn't map 1:1 onto a simple maximize concept — especially with aspect ratios — `default_frame_for_zoom_` caches the OS-provided "best fit" frame from `windowWillUseStandardFrame:defaultFrame:` so `IsMaximized()`/`Unmaximize()` can be computed correctly.
- **Style mask & collection behavior helpers**: `HasStyleMask`, `SetStyleMask`, `SetCollectionBehavior`, and `SetWindowLevel` are low-level escape hatches used internally (and by `WindowButtonsProxy`) to work around AppKit quirks, e.g. zoom button enable/disable bugs.
- **Vibrancy**: implemented by inserting a `views::NativeViewHost` (`vibrant_native_view_host_`) wrapping an `NSVisualEffectView` into the Views hierarchy, toggled via `SetVibrancy`/`UpdateVibrancyRadii`.
- **Theme & display observation**: `NativeWindowMac` mixes in `ui::NativeThemeObserver` and `display::DisplayObserver` to react to macOS dark-mode toggles and multi-monitor changes (e.g., re-applying vibrancy corner radii or repositioning traffic lights).

## Where This Fits in the Broader System

`NativeWindowMac` is instantiated indirectly through the JS-exposed `BrowserWindow`/`BaseWindow` gin wrappers (see [shell_browser_api_window_ui](shell_browser_api_window_ui.md)), which call the platform-agnostic `NativeWindow::Create()` factory. On macOS, this factory resolves to `NativeWindowMac`. All subsequent window operations invoked from JavaScript (resize, fullscreen, vibrancy, touch bar, traffic lights, tabs) are dispatched through this class into the Cocoa collaborator objects described above.

For the equivalent Windows/Linux implementation, see [shell_browser_native_window_views](shell_browser_native_window_views.md). For the platform-neutral contract both implementations fulfill, see [shell_browser_native_window_core](shell_browser_native_window_core.md).
