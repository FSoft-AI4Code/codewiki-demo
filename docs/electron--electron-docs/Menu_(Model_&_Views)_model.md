# Menu (Model & Views) — Model

## Introduction

The **Menu (Model & Views) Model** module defines the core, platform-agnostic data model used by Electron to represent application and context menus. It is centered on a single class, `electron::ElectronMenuModel`, which extends Chromium's `ui::SimpleMenuModel` with Electron-specific behavior such as custom tooltips, roles, sublabels, custom types, macOS sharing items, and accelerator/visibility policy hooks driven by a `Delegate` interface.

This model is the foundation upon which all platform-specific menu rendering is built. It does not draw or manage any native UI itself — instead, it is consumed by platform view/controller layers (macOS `NSMenu` controllers, Chromium Views-based menu widgets, and Linux/X11 global menu integrations), and it is populated and controlled from the JavaScript API layer (`Menu`, `MenuItem`) exposed to Electron applications.

Understanding this module is essential for anyone working on menu construction, menu item behavior, native menu integration, or the JS `Menu`/`MenuItem` API surface, since virtually every menu-related feature flows through `ElectronMenuModel`.

---

## Purpose & Core Functionality

`ElectronMenuModel` is a decorator/extension of `ui::SimpleMenuModel` (from `ui/menus/simple_menu_model.h`), Chromium's generic, platform-independent menu-model abstraction. Electron extends it to support:

- **Per-item metadata** not present in the base Chromium model:
  - Tooltips (`SetToolTip` / `GetToolTipAt`)
  - Custom types (`SetCustomType` / `GetCustomTypeAt`) — used to distinguish special item kinds (e.g., palette items)
  - Roles (`SetRole` / `GetRoleAt`) — string identifiers tying a menu item to a predefined behavior (see [Relationship to Role interface](#relationship-to-role-interface-js-api) below)
  - Secondary labels/sublabels (`SetSecondaryLabel` / `GetSecondaryLabelAt`)
- **Delegate-driven policy hooks** via the nested `Delegate` class:
  - `GetAcceleratorForCommandIdWithParams` — resolves the keyboard accelerator for a command, optionally applying a "default accelerator" fallback
  - `ShouldRegisterAcceleratorForCommandId` — controls whether an accelerator should be globally registered for a given command
  - `ShouldCommandIdWorkWhenHidden` — allows a menu command to still fire even when the associated menu item is hidden (important for global shortcuts/roles)
  - `GetSharingItemForCommandId` (macOS only) — supplies native "Share" sheet content for a command
- **Observer notifications** via the nested `Observer` class (`base::CheckedObserver`):
  - `OnMenuWillShow()` / `OnMenuWillClose()` — lifecycle notifications consumed by higher layers (e.g., JS `Menu` emitting `'menu-will-show'`/`'menu-will-close'` events)
- **macOS Sharing Support** via the `SharingItem` struct (guarded by `BUILDFLAG(IS_MAC)`), holding optional text, URL, and file-path payloads for native share-sheet integration.
- **Submenu access**: `GetSubmenuModelAt(size_t index)` returns an `ElectronMenuModel*` (rather than the base `ui::MenuModel*`), preserving Electron-specific typing through the submenu hierarchy.
- **Weak-pointer safety**: exposes `GetWeakPtr()` so owning/observing code (e.g., native window or menu controllers) can safely hold a reference without keeping the model alive.

The class stores its Electron-specific per-item metadata in `base::flat_map<int, std::u16string>` maps keyed by command ID (`toolTips_`, `roles_`, `sublabels_`, `customTypes_`), and keeps a raw (non-owning) pointer to its `Delegate`.

---

## Architecture

### Class Structure

```mermaid
classDiagram
    class SimpleMenuModel {
        <<ui:: base class>>
        +AddItem()
        +AddSubMenu()
        +GetLabelAt()
        +GetCommandIdAt()
    }

    class ElectronMenuModel {
        -Delegate* delegate_
        -flat_map~int,u16string~ toolTips_
        -flat_map~int,u16string~ roles_
        -flat_map~int,u16string~ sublabels_
        -flat_map~int,u16string~ customTypes_
        -ObserverList~Observer~ observers_
        -optional~SharingItem~ sharing_item_
        -WeakPtrFactory~ElectronMenuModel~ weak_factory_
        +SetToolTip(index, text)
        +GetToolTipAt(index)
        +SetCustomType(index, type)
        +GetCustomTypeAt(index)
        +SetRole(index, role)
        +GetRoleAt(index)
        +SetSecondaryLabel(index, label)
        +GetSecondaryLabelAt(index)
        +GetAcceleratorAtWithParams(index, useDefault, accel)
        +ShouldRegisterAcceleratorAt(index)
        +WorksWhenHiddenAt(index)
        +SetSharingItem(item)
        +sharing_item()
        +MenuWillClose()
        +MenuWillShow()
        +GetWeakPtr()
        +GetSubmenuModelAt(index) ElectronMenuModel*
        +AddObserver(obs)
        +RemoveObserver(obs)
    }

    class Delegate {
        <<interface>>
        +GetAcceleratorForCommandIdWithParams()
        +ShouldRegisterAcceleratorForCommandId()
        +ShouldCommandIdWorkWhenHidden()
        +GetSharingItemForCommandId() macOS
    }

    class Observer {
        <<interface, CheckedObserver>>
        +OnMenuWillShow()
        +OnMenuWillClose()
    }

    class SharingItem {
        <<struct, macOS only>>
        +optional~vector~string~~ texts
        +optional~vector~GURL~~ urls
        +optional~vector~FilePath~~ file_paths
    }

    SimpleMenuModel <|-- ElectronMenuModel
    ElectronMenuModel *-- Delegate : delegate_
    ElectronMenuModel *-- "0..*" Observer : observers_
    ElectronMenuModel *-- "0..1" SharingItem : sharing_item_
    ElectronMenuModel --> ElectronMenuModel : GetSubmenuModelAt() (tree)
```

### Position in the Menu Subsystem

The Model layer sits below the platform-specific view/controller implementations and above the pure Chromium `ui::SimpleMenuModel`:

```mermaid
graph TD
    subgraph JS_API["JS API Layer (Public_JS_API_Bindings)"]
        MenuJS["Menu / MenuItem (JS API)"]
        RoleTS["menu-item-roles.ts::Role"]
    end

    subgraph NativeMenuAPI["Native Menu API (shell_browser_api_window_ui_menu)"]
        ApiMenu["electron_api_menu.h (electron::api::Menu)"]
        ApiMenuMac["electron_api_menu_mac.h (MenuMac)"]
        ApiMenuViews["electron_api_menu_views.h (MenuViews)"]
    end

    subgraph ModelLayer["Menu Model Layer (this module)"]
        Model["ElectronMenuModel"]
        Delegate["Delegate"]
        Observer["Observer"]
        Sharing["SharingItem (macOS)"]
    end

    subgraph ViewsLayer["Menu Views Layer (Platform-specific)"]
        MacCtl["Menu_(Model_&_Views)_macos: ElectronMenuController"]
        ViewsImpl["Menu_(Model_&_Views)_views: MenuBar, MenuDelegate, MenuModelAdapter, SubmenuButton"]
        X11Impl["Menu_(Model_&_Views)_x11: GlobalMenuBarX11, GlobalMenuBarRegistrarX11"]
        GtkImpl["GTK_UI: MenuGtk, menu_util"]
    end

    subgraph Chromium["Chromium ui:: base"]
        SimpleMenuModel["ui::SimpleMenuModel"]
    end

    MenuJS -->|constructs & mutates| ApiMenu
    RoleTS -->|resolved into| ApiMenu
    ApiMenu --> ApiMenuMac
    ApiMenu --> ApiMenuViews
    ApiMenu -->|owns/creates| Model
    ApiMenu -.implements.-> Delegate

    Model --> SimpleMenuModel
    Model --> Delegate
    Model --> Observer
    Model --> Sharing

    ApiMenuMac --> MacCtl
    ApiMenuViews --> ViewsImpl
    ViewsImpl --> X11Impl
    ViewsImpl --> GtkImpl

    MacCtl -->|reads items from| Model
    ViewsImpl -->|adapts via MenuModelAdapter| Model
    X11Impl -->|mirrors items from| Model
    GtkImpl -->|mirrors items from| Model
```

---

## Component Relationships

### `ElectronMenuModel` and its Nested Types

```mermaid
graph LR
    EMM["ElectronMenuModel"]
    Del["Delegate\n(ui::SimpleMenuModel::Delegate subclass)"]
    Obs["Observer\n(base::CheckedObserver)"]
    Share["SharingItem\n(macOS struct)"]

    EMM -->|"holds raw_ptr<Delegate>"| Del
    EMM -->|"notifies via ObserverList"| Obs
    EMM -->|"holds optional<SharingItem>"| Share

    Del -.overrides.-> BaseDel["ui::SimpleMenuModel::Delegate"]
```

- **`Delegate`**: Implemented by the owning native menu object (see [Menu (Model & Views) — macOS](Menu_(Model_&_Views)_macos.md), [Menu (Model & Views) — Views](Menu_(Model_&_Views)_views.md), and ultimately by the `electron::api::Menu` wrapper in [shell_browser_api_window_ui_menu](shell_browser_api_window_ui_menu.md)). It privately overrides the base `ui::SimpleMenuModel::Delegate::GetAcceleratorForCommandId` and forwards it to the richer `GetAcceleratorForCommandIdWithParams`, allowing Electron to pass extra context (e.g., whether default accelerators should apply).
- **`Observer`**: Any component wanting menu open/close lifecycle notifications (e.g., to pause/resume other UI, or to forward JS events) registers via `AddObserver`/`RemoveObserver`.
- **`SharingItem`**: Populated on macOS to drive the native "Share" menu integration; conceptually related to (but distinct from) the higher-level `ShareMenu` JS API in `lib/browser/api/share-menu.ts` (see [lib_browser_api_menu_and_sharing](lib_browser_api_menu_and_sharing.md)).

### Relationship to `Role` Interface (JS API)

The `roles_` map (`SetRole` / `GetRoleAt`) stores a string role identifier per menu item command ID. This is the native-side counterpart to the TypeScript `Role` interface defined in `lib/browser/api/menu-item-roles.ts` (module: [lib_browser_api_menu_and_sharing](lib_browser_api_menu_and_sharing.md)):

```mermaid
sequenceDiagram
    participant JS as JS: MenuItem({role: 'toggleDevTools'})
    participant RoleTable as menu-item-roles.ts (Role table)
    participant ApiMenu as electron_api_menu.h (Menu binding)
    participant Model as ElectronMenuModel

    JS->>RoleTable: look up Role by name
    RoleTable-->>JS: {label, accelerator, windowMethod, ...}
    JS->>ApiMenu: create native MenuItem w/ role metadata
    ApiMenu->>Model: SetRole(index, role)
    ApiMenu->>Model: SetToolTip / SetSecondaryLabel / SetCustomType (as needed)
    Note over Model: Role string is later used by\nDelegate to dispatch windowMethod/\nwebContentsMethod/appMethod on click
```

The `Role` interface (`windowMethod`, `webContentsMethod`, `appMethod`, `accelerator`, `registerAccelerator`, `nonNativeMacOSRole`) is resolved at the JS layer, but the resulting **role name string** is persisted into the native `ElectronMenuModel` so that native code (accelerator registration, visibility policy) can consult it without round-tripping into JS.

---

## Data Flow

### Menu Item Construction & Metadata Population

```mermaid
sequenceDiagram
    participant App as Electron App (JS)
    participant MenuAPI as Menu / MenuItem (JS binding)
    participant NativeMenu as electron::api::Menu (Delegate impl)
    participant Model as ElectronMenuModel
    participant Base as ui::SimpleMenuModel

    App->>MenuAPI: new Menu(template)
    MenuAPI->>NativeMenu: construct native menu
    NativeMenu->>Model: new ElectronMenuModel(this as Delegate)
    loop for each MenuItemConstructorOptions
        MenuAPI->>NativeMenu: append item (label, role, accelerator, submenu, ...)
        NativeMenu->>Base: AddItem/AddCheckItem/AddSubMenu(...)
        NativeMenu->>Model: SetRole(idx, role)
        NativeMenu->>Model: SetToolTip(idx, tooltip)
        NativeMenu->>Model: SetSecondaryLabel(idx, sublabel)
        NativeMenu->>Model: SetCustomType(idx, customType)
    end
    Note right of Model: Submenus become nested\nElectronMenuModel instances via AddSubMenu
```

### Menu Show/Close Lifecycle

```mermaid
sequenceDiagram
    participant Views as Platform View/Controller\n(macOS/Views/X11)
    participant Model as ElectronMenuModel
    participant Obs as Observer(s)

    Views->>Model: (menu about to open)
    Model->>Model: MenuWillShow()
    Model->>Obs: OnMenuWillShow()
    Note over Obs: e.g. JS layer emits 'menu-will-show'

    Views->>Model: (menu closed by user)
    Model->>Model: MenuWillClose()
    Model->>Obs: OnMenuWillClose()
    Note over Obs: e.g. JS layer emits 'menu-will-close'
```

### Accelerator & Visibility Resolution

```mermaid
sequenceDiagram
    participant Views as Platform Menu View
    participant Model as ElectronMenuModel
    participant Delegate as Delegate (native Menu impl)

    Views->>Model: GetAcceleratorAtWithParams(index, useDefault, &accel)
    Model->>Delegate: GetAcceleratorForCommandIdWithParams(cmdId, useDefault, &accel)
    Delegate-->>Model: bool (found?)
    Model-->>Views: bool

    Views->>Model: ShouldRegisterAcceleratorAt(index)
    Model->>Delegate: ShouldRegisterAcceleratorForCommandId(cmdId)
    Delegate-->>Model: bool
    Model-->>Views: bool

    Views->>Model: WorksWhenHiddenAt(index)
    Model->>Delegate: ShouldCommandIdWorkWhenHidden(cmdId)
    Delegate-->>Model: bool
    Model-->>Views: bool
```

---

## How This Module Fits Into the Overall System

`ElectronMenuModel` is a leaf dependency consumed widely across the menu ecosystem but has no dependency on any Electron-specific higher-level module itself (it only depends on Chromium's `ui::SimpleMenuModel`, `base::`, and `url::GURL`). This makes it the stable, shared "contract" for all platform menu implementations.

```mermaid
graph BT
    Model["Menu_(Model_&_Views)_model\n(ElectronMenuModel, Delegate, Observer, SharingItem)"]

    Model --> MacViews["Menu_(Model_&_Views)_macos\n(ElectronMenuController)"]
    Model --> ViewsViews["Menu_(Model_&_Views)_views\n(MenuBar, MenuDelegate, MenuModelAdapter, SubmenuButton)"]
    Model --> X11Views["Menu_(Model_&_Views)_x11\n(GlobalMenuBarX11, GlobalMenuBarRegistrarX11)"]
    Model --> GtkViews["GTK_UI\n(MenuGtk, menu_util)"]

    Model --> WinUIMenu["shell_browser_api_window_ui_menu\n(electron_api_menu.h, MenuMac, MenuViews)"]
    Model --> NativeWindow["shell_browser_native_window\n(NativeWindow::SetMenu)"]
    Model --> Browser["shell_browser_core\n(Browser)"]
    Model --> Tray["Tray_Icon\n(TrayIcon context menus)"]
    Model --> RootView["Menu_(Model_&_Views)_views::RootView"]

    WinUIMenu --> JSMenu["Public_JS_API_Bindings\n(Menu / MenuItem JS API)"]
    JSMenu --> RoleTS["lib_browser_api_menu_and_sharing\n(Role table, ShareMenu)"]
```

Key consumer relationships:

- **[shell_browser_api_window_ui_menu](shell_browser_api_window_ui_menu.md)** — `electron_api_menu.h` defines `electron::api::Menu`, which implements `ElectronMenuModel::Delegate` and owns an `ElectronMenuModel` instance; `electron_api_menu_mac.h`/`electron_api_menu_views.h` (`MenuMac`, `MenuViews`) bridge the model to platform-native menu presentation.
- **[Menu (Model & Views) — macOS](Menu_(Model_&_Views)_macos.md)** — `ElectronMenuController` (Cocoa) reads `ElectronMenuModel` state to build and drive an `NSMenu`.
- **[Menu (Model & Views) — Views](Menu_(Model_&_Views)_views.md)** — `MenuModelAdapter`, `MenuDelegate`, `MenuBar`, and `SubmenuButton` consume `ElectronMenuModel` to render Chromium Views-based menus (used on Windows/Linux non-global-menu paths), and `RootView` uses `ElectronMenuModel` for window-level menu bars.
- **[Menu (Model & Views) — X11](Menu_(Model_&_Views)_x11.md)** — `GlobalMenuBarX11`/`GlobalMenuBarRegistrarX11` mirror `ElectronMenuModel` contents into the Unity/DBusMenu global menu protocol on Linux.
- **[shell_browser_native_window](shell_browser_native_window.md)** — `NativeWindow` holds a pointer to an `ElectronMenuModel` (application/window menu) via `native_window.h`.
- **[shell_browser_core](shell_browser_core.md)** — `Browser` references `ElectronMenuModel` for the application-level menu (e.g., macOS app menu, dock menu).
- **[Tray Icon](Tray_Icon.md)** — Tray context menus are `ElectronMenuModel` instances presented by platform tray implementations.
- **[lib_browser_api_menu_and_sharing](lib_browser_api_menu_and_sharing.md)** — The JS-side `Role` table and `ShareMenu` correspond conceptually to the native `roles_` map and `SharingItem` struct respectively; JS role/sharing configuration is translated into native model state through the `Menu`/`MenuItem` bindings.

---

## Summary

| Aspect | Description |
|---|---|
| **Primary class** | `electron::ElectronMenuModel` |
| **Base class** | `ui::SimpleMenuModel` (Chromium) |
| **Nested types** | `Delegate`, `Observer`, `SharingItem` (macOS) |
| **Key responsibilities** | Per-item metadata (tooltip, role, sublabel, custom type), accelerator/visibility policy delegation, show/close lifecycle notification, macOS sharing payload, weak-pointer safe access, typed submenu traversal |
| **Consumed by** | Native `Menu`/`MenuItem` API binding, macOS `ElectronMenuController`, Views-based menu widgets, X11 global menu bar, Tray context menus, `NativeWindow`, `Browser` |
| **Depends on** | Chromium `ui::SimpleMenuModel`, `base::flat_map`, `base::ObserverList`, `url::GURL`, `base::FilePath` |
| **Related JS-facing concepts** | `Role` interface (`lib/browser/api/menu-item-roles.ts`), `ShareMenu` (`lib/browser/api/share-menu.ts`) |

For platform-specific rendering built on top of this model, see:
- [Menu (Model & Views) — macOS](Menu_(Model_&_Views)_macos.md)
- [Menu (Model & Views) — Views](Menu_(Model_&_Views)_views.md)
- [Menu (Model & Views) — X11](Menu_(Model_&_Views)_x11.md)

For the JS-facing API and role/sharing definitions, see:
- [Public JS API Bindings — Menu & Sharing](lib_browser_api_menu_and_sharing.md)

For the native binding layer that owns and mediates access to `ElectronMenuModel`, see:
- [Native Window & Menu Management — Window UI Menu](shell_browser_api_window_ui_menu.md)
