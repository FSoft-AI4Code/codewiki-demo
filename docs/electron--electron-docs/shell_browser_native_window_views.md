# Shell Browser Native Window Views

## Introduction

`shell_browser_native_window_views` provides the **Views-toolkit backed** implementation of Electron's cross-platform `NativeWindow` abstraction. It is compiled on **Windows** and **Linux** (the macOS equivalent lives in [shell_browser_native_window_mac](shell_browser_native_window_mac.md)), and is responsible for turning the platform-agnostic window API exposed to JavaScript into concrete `views::Widget` objects, handling OS message loops, frame decoration, menu bars, taskbar integration, and window state transitions (maximize/minimize/fullscreen/always-on-top/etc.).

The module's centerpiece is the `NativeWindowViews` class, which:

- Subclasses `NativeWindow` (the platform-neutral base defined in [shell_browser_native_window_core](shell_browser_native_window_core.md)) and `views::WidgetObserver`/`ui::EventHandler`.
- Owns a `views::Widget` and a `RootView` (from [Menu (Model & Views)](Menu_%28Model_%26_Views%29.md)) that hosts the window's content view and optional in-window menu bar.
- Delegates frame painting to platform-specific `NonClientFrameView` implementations (see [Frame Views](Frame_Views.md)).
- Integrates with Windows-only facilities such as `TaskbarHost` (jump lists, thumbnail toolbars, progress bars) and with Linux-only facilities such as `GlobalMenuBarX11` and `EventDisabler`.

This document focuses on the internals of this module; for the JS-facing `BrowserWindow`/`BaseWindow` APIs that consume `NativeWindowViews`, see [shell_browser_api_window_ui](shell_browser_api_window_ui.md).

---

## 1. Purpose & Scope

| Concern | Handled here | Handled elsewhere |
|---|---|---|
| Cross-platform window contract | No (base class) | [shell_browser_native_window_core](shell_browser_native_window_core.md) (`NativeWindow`) |
| Views/Aura-backed window (Win/Linux) | **Yes** (`NativeWindowViews`) | — |
| Cocoa-backed window (macOS) | No | [shell_browser_native_window_mac](shell_browser_native_window_mac.md) |
| Frame/non-client area rendering | Delegates to frame view classes | [Frame Views](Frame_Views.md) |
| In-window (non-global) menu bar rendering | Uses `RootView`/`MenuBar` | [Menu (Model & Views)](Menu_%28Model_%26_Views%29.md) |
| Global (X11/DBus) menu bar | **Yes** (`GlobalMenuBarX11`) | [Menu (Model & Views)](Menu_%28Model_%26_Views%29.md) (class definition) |
| Windows taskbar (jump list, thumbnails, progress) | Uses `TaskbarHost` | [Windows UI (Desktop Widgets)](Windows_UI_%28Desktop_Widgets%29.md) |
| JS `BrowserWindow`/`BaseWindow` bindings | No | [shell_browser_api_window_ui](shell_browser_api_window_ui.md) |
| Window registry / lifecycle tracking | No | [Window List](Window_List.md) |

---

## 2. Component Inventory

| Component | File | Description |
|---|---|---|
| `NativeWindowViews` | `native_window_views.h/.cc` | Concrete `NativeWindow` implementation using the Chromium Views toolkit. Implements every pure-virtual method of `NativeWindow` (show/hide, resize, fullscreen, always-on-top, menu, taskbar/overlay icon, opacity, etc.) |
| `NativeWindowClientView` | `native_window_views.cc` (anonymous-namespace-adjacent) | A `views::ClientView` subclass that intercepts the OS "close" request and forwards it to `NativeWindowViews::NotifyWindowCloseButtonClicked()`, always returning `kCannotClose` so that Electron (JS) can veto/close the window itself. |
| `ClientFrameViewLinux` (fwd-declared) | consumed from [Frame Views](Frame_Views.md) | Custom-drawn, Wayland-friendly, non-client frame used when `has_frame() && has_client_frame()`. `NativeWindowViews::GetClientFrameViewLinux()` exposes it. |
| `GlobalMenuBarX11` (fwd-declared) | consumed from [Menu (Model & Views)](Menu_%28Model_%26_Views%29.md) | Publishes the window's menu via the `com.canonical.dbusmenu` protocol so desktop environments (Unity, KDE) can render it in a global menu bar instead of in-window. |
| `EventDisabler` (fwd-declared) | consumed from [Menu (Model & Views)](Menu_%28Model_%26_Views%29.md) | An `ui::EventRewriter` installed on the X11 `DesktopWindowTreeHostLinux` to swallow input events while the window is "disabled" (e.g., blocked by a modal child). |
| `gin_helper::Arguments` (fwd-declared) | [Gin Helper](Gin_Helper.md) | Used by `SetTitleBarOverlay()` to throw JS-visible errors when misused. |
| `TaskbarHost` (member, Windows only) | [Windows UI (Desktop Widgets)](Windows_UI_%28Desktop_Widgets%29.md) | Encapsulates `ITaskbarList3` COM usage: thumbnail toolbar buttons, progress bar, overlay icon, thumbnail clipping. |
| `RootView` (member) | [Menu (Model & Views)](Menu_%28Model_%26_Views%29.md) | Hosts the content view plus an optional in-window `MenuBar`; handles accelerator registration and Alt-key menu toggling. |

---

## 3. Class Architecture

```mermaid
classDiagram
    class NativeWindow {
        <<abstract>>
        +widget() views::Widget*
        +content_view() views::View*
        +SetTitle(title)
        +NotifyWindowShow()
        +NotifyWindowClosed()
        +Create(options, parent) NativeWindow*
    }

    class NativeWindowViews {
        -RootView root_view_
        -views::View* focused_view_
        -TaskbarHost taskbar_host_  <<Windows only>>
        -GlobalMenuBarX11 global_menu_bar_ <<Linux only>>
        -EventDisabler event_disabler_ <<Ozone X11 only>>
        -SkColor overlay_button_color_
        -SkColor overlay_symbol_color_
        +Show()
        +Hide()
        +Close()
        +Maximize()/Unmaximize()
        +SetFullScreen(bool)
        +SetBounds(rect, animate)
        +SetMenu(ElectronMenuModel*)
        +SetTitleBarOverlay(options, args)
        +GetClientFrameViewLinux() ClientFrameViewLinux*
        -OnWidgetActivationChanged()
        -OnWidgetBoundsChanged()
        -OnWidgetDestroying()/OnWidgetDestroyed()
        -CreateNonClientFrameView(widget) NonClientFrameView
        -CreateClientView(widget) ClientView
    }

    class WidgetObserver {
        <<interface>>
    }
    class EventHandler {
        <<interface>>
    }

    NativeWindow <|-- NativeWindowViews
    WidgetObserver <|.. NativeWindowViews
    EventHandler <|.. NativeWindowViews

    class NativeWindowClientView {
        -NativeWindowViews& window_
        +OnWindowCloseRequested() CloseRequestResult
    }
    NativeWindowViews ..> NativeWindowClientView : creates via CreateClientView()

    class RootView {
        +SetMenu(model)
        +GetMainView() View*
        +HandleKeyEvent(event)
    }
    NativeWindowViews *-- RootView

    class TaskbarHost {
        +SetProgressBar()
        +SetOverlayIcon()
        +RestoreThumbarButtons()
    }
    NativeWindowViews *-- TaskbarHost : Windows

    class GlobalMenuBarX11 {
        +SetMenu(model)
        +OnWindowMapped()/OnWindowUnmapped()
    }
    NativeWindowViews *-- GlobalMenuBarX11 : Linux (optional)

    class ClientFrameViewLinux {
        +Init(window, widget)
    }
    NativeWindowViews ..> ClientFrameViewLinux : CreateNonClientFrameView()

    class OpaqueFrameView
    class NativeFrameView
    class WinFrameView
    NativeWindowViews ..> OpaqueFrameView
    NativeWindowViews ..> NativeFrameView
    NativeWindowViews ..> WinFrameView
```

For the full `NativeWindow` contract (shared with the macOS implementation), see [shell_browser_native_window_core](shell_browser_native_window_core.md). For frame-view class details, see [Frame Views](Frame_Views.md).

---

## 4. Module Position in the System

```mermaid
graph TD
    subgraph JS_API["Public JS API Bindings"]
        BW[BrowserWindow / BaseWindow]
    end

    subgraph WindowUI["shell_browser_api_window_ui"]
        ApiBaseWindow[electron_api_base_window]
        ApiBrowserWindow[electron_api_browser_window]
        ApiMenu[electron_api_menu / menu_views]
        ApiTray[electron_api_tray]
    end

    subgraph NativeWindowCore["shell_browser_native_window_core"]
        NW[NativeWindow]
    end

    subgraph ThisModule["shell_browser_native_window_views (this module)"]
        NWV[NativeWindowViews]
        NWCV[NativeWindowClientView]
    end

    subgraph FrameViews["Frame Views"]
        OFV[OpaqueFrameView]
        NFV[NativeFrameView]
        WFV[WinFrameView]
        CFVL[ClientFrameViewLinux]
    end

    subgraph MenuViews["Menu (Model & Views)"]
        RV[RootView]
        MB[MenuBar]
        GMB[GlobalMenuBarX11]
        ED[EventDisabler]
    end

    subgraph WinUI["Windows UI (Desktop Widgets)"]
        TH[TaskbarHost]
        EDNW[ElectronDesktopNativeWidgetAura]
        EDWTH[ElectronDesktopWindowTreeHostWin]
    end

    subgraph LinuxFrame["Frame Views (Linux hosts)"]
        EDWTHL[ElectronDesktopWindowTreeHostLinux]
    end

    subgraph WindowList["Window List"]
        WL[WindowList]
    end

    BW --> ApiBrowserWindow
    ApiBaseWindow --> NW
    ApiBrowserWindow --> NW
    NW --> NWV
    NWV --> NWCV
    NWV --> RV
    RV --> MB
    NWV -.Linux optional.-> GMB
    NWV -.Ozone X11 optional.-> ED
    NWV --> OFV
    NWV --> NFV
    NWV --> WFV
    NWV --> CFVL
    NWV -.Windows.-> TH
    NWV --> EDNW
    NWV --> EDWTH
    NWV --> EDWTHL
    NWV --> WL

    style ThisModule fill:#dbeeff,stroke:#333,stroke-width:2px
```

---

## 5. Window Creation Flow

`NativeWindow::Create()` is a factory defined only in this module (Windows/Linux builds), instantiating `NativeWindowViews` directly:

```mermaid
sequenceDiagram
    participant JS as JS (BrowserWindow ctor)
    participant API as electron_api_browser_window
    participant NW as NativeWindow::Create()
    participant NWV as NativeWindowViews ctor
    participant Widget as views::Widget
    participant NWT as Native widget/tree host (Win/Linux)

    JS->>API: new BrowserWindow(options)
    API->>NW: NativeWindow::Create(options, parent)
    NW->>NWV: make_unique<NativeWindowViews>(options, parent)
    NWV->>NWV: Parse options (title, resizable, accentColor, titleBarOverlay...)
    NWV->>NWV: SetContentSizeConstraints() (if larger-than-screen)
    NWV->>Widget: widget()->AddObserver(this)
    NWV->>Widget: Widget::InitParams{...}
    alt Windows
        NWV->>NWT: new ElectronDesktopNativeWidgetAura(this, widget())
    else Linux
        NWV->>NWT: new DesktopNativeWidgetAura + ElectronDesktopWindowTreeHostLinux
    end
    NWV->>Widget: widget()->Init(params)
    NWV->>Widget: SetNativeWindowProperty(kNativeWindowKey, this)
    NWV->>NWV: SetCanResize(resizable_)
    alt Linux + X11
        NWV->>NWV: Set _NET_WM_STATE / WM_WINDOW_TYPE atoms
    else Windows
        NWV->>NWV: Configure WS_* frame styles, rounded corners
    end
    NWV->>NWV: SetContentView(new views::View())
    NWV->>Widget: widget()->CenterWindow(size)
    NWV->>NWV: GetNativeWindow()->AddPreTargetHandler(this)
    NWV-->>NW: unique_ptr<NativeWindow>
    NW-->>API: NativeWindow*
```

---

## 6. Frame View Selection

`CreateNonClientFrameView()` chooses the non-client (title bar / border) implementation based on platform and window options:

```mermaid
flowchart TD
    Start[CreateNonClientFrameView] --> IsWin{IS_WIN?}
    IsWin -- yes --> WinFV["WinFrameView<br/>Init(this, widget)"]
    IsWin -- no --> HasFrame{has_frame?}
    HasFrame -- no --> Opaque["OpaqueFrameView<br/>Init(this, widget)"]
    HasFrame -- yes --> HasClientFrame{has_client_frame?}
    HasClientFrame -- no --> NativeFV["NativeFrameView<br/>uses OS-drawn frame"]
    HasClientFrame -- yes --> ClientFV["ClientFrameViewLinux<br/>Init(this, widget)<br/>self-drawn shadows/border"]
```

- **Windows**: Always `WinFrameView`, which itself composes `WinCaptionButtonContainer` (see [Frame Views](Frame_Views.md)).
- **Linux, frameless**: `OpaqueFrameView` (used also for custom-drawn *with* frame but no client-frame requirement).
- **Linux, framed, no client frame** (X11 with WM-drawn decorations): `NativeFrameView`.
- **Linux, framed + client frame** (e.g., Wayland where Electron must draw its own decorations): `ClientFrameViewLinux`, retrievable at runtime via `GetClientFrameViewLinux()`.

---

## 7. State Management & Widget Observation

`NativeWindowViews` mixes in `views::WidgetObserver` to react to the underlying `views::Widget` lifecycle and translate Views events into `NativeWindow` notifications consumed by JS listeners (`focus`, `blur`, `resize`, `move`, `closed`, etc.):

```mermaid
sequenceDiagram
    participant Widget as views::Widget
    participant NWV as NativeWindowViews
    participant Base as NativeWindow (Notify*)
    participant JS as JS EventEmitter

    Widget->>NWV: OnWidgetActivationChanged(active)
    NWV->>NWV: MoveBehindTaskBarIfNeeded() (if active)
    alt active
        NWV->>Base: NotifyWindowFocus()
    else
        NWV->>Base: NotifyWindowBlur()
    end
    NWV->>NWV: UpdateWindowAccentColor(active) [Windows]
    NWV->>NWV: Auto-hide menu bar if blurred
    Base->>JS: emit('focus'|'blur')

    Widget->>NWV: OnWidgetBoundsChanged(bounds)
    NWV->>NWV: Compare widget_size_ vs new size
    NWV->>Base: NotifyWindowResize()
    Base->>JS: emit('resize')

    Widget->>NWV: OnWidgetDestroying()
    NWV->>NWV: Remove pre-target handler and decrement parent modal count
    Widget->>NWV: OnWidgetDestroyed()
    NWV->>Base: NotifyWindowClosed()
    Base->>JS: emit('closed')
```

Additionally, `NativeWindowViews` implements `ui::EventHandler::OnMouseEvent` as a pre-target handler on the `aura::Window` to detect mouse-press events for resetting Alt-key menu state and (Linux) mapping mouse back/forward buttons to `NotifyWindowExecuteAppCommand`.

---

## 8. Enable/Disable & Modal Windows

Electron windows can be temporarily disabled while a modal child is open. `NativeWindowViews` tracks this with a reference count rather than a boolean, since multiple modal children may stack:

```mermaid
flowchart LR
    A["Modal child Show()"] --> B["parent-&gt;IncrementChildModals()"]
    B --> C{"ShouldBeEnabled?<br/>is_enabled_ AND num_modal_children_==0"}
    C -- false --> D["SetEnabledInternal(false)"]
    D -->|Windows| E["EnableWindow(hwnd, FALSE)"]
    D -->|Linux X11| F["Install EventDisabler as EventRewriter"]

    G["Modal child closed/destroyed"] --> H["parent-&gt;DecrementChildModals()"]
    H --> C
    C -- true --> I["SetEnabledInternal(true)"]
    I -->|Windows| J["EnableWindow(hwnd, TRUE)"]
    I -->|Linux X11| K["Remove and reset EventDisabler"]
```

This mechanism is orthogonal to the explicit JS-driven `SetEnabled()`/`is_enabled_` flag; both gate the final `ShouldBeEnabled()` result.

---

## 9. Platform-Specific Feature Matrix

| Feature | Windows implementation | Linux implementation |
|---|---|---|
| Resizable/min-max size | `WS_THICKFRAME` toggling + `UpdateThickFrame()` | Emulated via `SetContentSizeConstraints` clamped to current size |
| Always-on-top "levels" | `behind_task_bar_` flag + `MoveBehindTaskBarIfNeeded()` (`FindWindow(Shell_TrayWnd)`) | Native `ui::ZOrderLevel` only; no dock-relative levels |
| Opacity | `SetLayeredWindowAttributes` (`WS_EX_LAYERED`) | Unsupported (`opacity_` pinned to `1.0`) |
| Ignore mouse events | `WS_EX_TRANSPARENT`/`WS_EX_LAYERED` toggling, optional mouse-message forwarding via `SubclassProc`/`MouseHookProc` | X11 input shape region (`shape().Rectangles`/`Mask`) |
| Menu bar | In-window `RootView`/`MenuBar` only | In-window `RootView`/`MenuBar` **or** `GlobalMenuBarX11` (DBus) when the desktop environment supports it |
| Taskbar/progress/jumplist | `TaskbarHost` (`ITaskbarList3`) | Unity launcher API (`unity::SetProgressFraction`) for progress only; see [shell_browser_linux](shell_browser_linux.md) |
| Background material (Mica/Acrylic) | `DwmSetWindowAttribute(DWMWA_SYSTEMBACKDROP_TYPE)` (Win11 22H2+) | Not supported |
| Window icon | `WM_SETICON` with small/large `HICON` | `DesktopWindowTreeHostLinux::SetWindowIcons` |
| Parent/child ownership | `GWLP_HWNDPARENT` | `WM_TRANSIENT_FOR` X11 property |
| Dark theme hint | N/A (handled via `SetAccentColor`) | `_GTK_THEME_VARIANT` X11 property |

---

## 10. Key Interactions with Other Modules

```mermaid
graph LR
    NWV[NativeWindowViews]

    NWV -->|reads/writes menu model| EMM[ElectronMenuModel<br/>Menu Model and Views]
    NWV -->|frame decoration| FV[Frame Views]
    NWV -->|taskbar/jumplist| WinDW[Windows UI Desktop Widgets]
    NWV -->|window enumeration on close| WL[Window List]
    NWV -->|color parsing| CU[Common Graphics Util<br/>color_util.h]
    NWV -->|options parsing| GH[Gin Helper<br/>Dictionary / Arguments]
    NWV -->|system preferences accent color| SP[electron_api_system_preferences<br/>shell_browser_api_system_device]
    NWV -->|Linux desktop app id| PU[Platform Util]
    NWV -->|X11 utilities| X11U[shell_browser_linux / x11_util]
    NWV -.notifies.-> NWOBS[NativeWindowObserver<br/>shell_browser_native_window_core]
```

- **Menu wiring**: `SetMenu()` chooses between the in-process `RootView` menu bar and, on Linux desktop environments that advertise `supports_global_application_menus`, a lazily-created `GlobalMenuBarX11`. See [Menu (Model & Views)](Menu_%28Model_%26_Views%29.md).
- **Window enumeration**: `Close()` consults `WindowList::WindowCloseCancelled(this)` when the window has been marked non-closable, integrating with the global window registry described in [Window List](Window_List.md).
- **Content view plumbing**: `SetContentView()` swaps the child `views::View` under `RootView::GetMainView()`; the content view is typically a `WebView`/`InspectableWebContentsView` supplied by [shell_browser_api_webcontents](shell_browser_api_webcontents.md) or [Inspectable Web Contents](Inspectable_Web_Contents.md).

---

## 11. Notable Implementation Details

- **`NativeWindowClientView::OnWindowCloseRequested()`** always returns `views::CloseRequestResult::kCannotClose`. This is intentional: Electron's close semantics are driven from JS (`close`/`beforeunload` events), so the native Views layer never unilaterally closes the window; `NativeWindow::Close()` performs the actual `widget()->Close()` after JS has had a chance to veto.
- **Transparent/frameless windows on Windows** receive special-cased `Maximize()`/`Unmaximize()`/`Restore()`/`IsMaximized()` logic that manually resizes to the display's work area instead of using native Win32 maximize, because transparent windows cannot reliably use `WS_MAXIMIZE`.
- **`GetContentSizeConstraints()` (Windows only)** deliberately reproduces a Chromium rounding quirk (`WindowSizeToContentSizeBuggy`) so that min/max size constraints match what Chromium's `HWNDMessageHandler::OnGetMinMaxInfo` computes, avoiding off-by-one-pixel resize glitches.
- **Background material (Mica/Acrylic/Tabbed)** is only wired up on Windows 11 22H2+ and requires synchronizing translucency state across `ElectronDesktopWindowTreeHostWin` and `ElectronDesktopNativeWidgetAura` in addition to calling `DwmSetWindowAttribute`.
- **Mouse-message forwarding** (`SetForwardMouseMessages`, `SubclassProc`, `MouseHookProc`) is a Windows-only mechanism enabling click-through windows (`ignore=true, forward=true`) to still deliver mouse move/enter/leave events to the app for custom hover UI, using a static `HHOOK` and a process-wide set of forwarding windows.

---

## Related Modules

- [shell_browser_native_window_core](shell_browser_native_window_core.md) — the `NativeWindow` base class and cross-platform window contract.
- [shell_browser_native_window_mac](shell_browser_native_window_mac.md) — the Cocoa-backed sibling implementation.
- [shell_browser_native_window_support](shell_browser_native_window_support.md) — `ChildWebContentsTracker` and draggable-region support shared across window backends.
- [shell_browser_api_window_ui](shell_browser_api_window_ui.md) — JS-facing `BrowserWindow`, `BaseWindow`, `Menu`, `Tray`, and `View` bindings that ultimately drive `NativeWindowViews`.
- [Frame Views](Frame_Views.md) — `OpaqueFrameView`, `NativeFrameView`, `WinFrameView`, `ClientFrameViewLinux`, and related caption-button widgets.
- [Menu (Model & Views)](Menu_%28Model_%26_Views%29.md) — `RootView`, `MenuBar`, `GlobalMenuBarX11`, `EventDisabler`, `ElectronMenuModel`.
- [Windows UI (Desktop Widgets)](Windows_UI_%28Desktop_Widgets%29.md) — `TaskbarHost`, `ElectronDesktopNativeWidgetAura`, `ElectronDesktopWindowTreeHostWin`, jump lists.
- [Window List](Window_List.md) — global registry of `NativeWindow` instances.
- [Gin Helper](Gin_Helper.md) — `gin_helper::Dictionary`/`Arguments` used for options parsing and error reporting.
