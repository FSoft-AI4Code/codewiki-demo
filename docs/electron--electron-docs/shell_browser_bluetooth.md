# Bluetooth Module (`shell_browser_bluetooth`)

## Introduction

The `shell_browser_bluetooth` module implements Electron's browser-process integration with Chromium's **Web Bluetooth** and **Web Bluetooth Scanning API**. It is the concrete implementation of Chromium's `content::BluetoothDelegate` interface, allowing web content running inside `WebContents`/`RenderFrameHost` instances to discover, pair, and communicate with Bluetooth Low Energy (BLE) devices, subject to per-origin permission and user-consent gating.

This module is intentionally small and focused: it acts as the **policy and permission bridge** between Chromium's device-agnostic Bluetooth content layer and Electron-specific concerns such as the device chooser UI, permission persistence, and JS-facing events. It is one of several "device delegate" modules that plug into `ElectronBrowserClient`, sitting alongside HID, Serial, USB, and WebAuthn delegates under the broader Device & Peripheral Access family.

---

## Purpose & Responsibilities

`ElectronBluetoothDelegate` is responsible for:

- **Device chooser UI**: Launching a native/JS-driven Bluetooth device picker (`RunBluetoothChooser`) when a page calls `navigator.bluetooth.requestDevice()`.
- **Scanning prompts**: Presenting a prompt for the Web Bluetooth Scanning API (`ShowBluetoothScanningPrompt`).
- **Pairing UX**: Driving native device pairing flows (`ShowDevicePairPrompt`) including PIN entry, and returning the result back to Blink via `PairPromptCallback`.
- **Device identity mapping**: Maintaining/mapping between Blink's opaque `blink::WebBluetoothDeviceId` and the underlying platform `device::BluetoothDevice` address (`GetWebBluetoothDeviceId`, `GetDeviceAddress`, `AddScannedDevice`).
- **Permission enforcement**: Granting, checking, and revoking per-origin/per-frame permissions to access Bluetooth devices, specific GATT services, and manufacturer data (`GrantServiceAccessPermission`, `HasDevicePermission`, `IsAllowedToAccessService`, `IsAllowedToAccessManufacturerData`, `RevokeDevicePermissionWebInitiated`).
- **Frame lifecycle observation**: Notifying observers (`FramePermissionObserver`) of permission changes scoped to a `content::RenderFrameHost`.

It does **not** implement Bluetooth transport/GATT logic itself — that remains in Chromium's `device::bluetooth` layer. This delegate is purely about **who is allowed to see/use which devices**, and **how the chooser UI is surfaced**.

---

## Core Component

### `ElectronBluetoothDelegate`

Defined in `shell/browser/bluetooth/electron_bluetooth_delegate.h`, this class derives from `content::BluetoothDelegate` and is instantiated once per `ElectronBrowserClient` (see [shell_browser_main_parts](shell_browser_main_parts.md)).

Key characteristics:
- **Move/copy disabled** — it is a singleton-like delegate owned by the browser client.
- Uses `base::WeakPtrFactory` to safely handle async callbacks (e.g., pairing prompt responses) that may outlive the delegate's synchronous call stack.
- Stateless with respect to per-device bookkeeping in this header — actual bookkeeping (chooser state, device list, id mapping) is delegated to companion classes like `BluetoothChooser` (see below) and Chromium's underlying `content::BluetoothAllowedDevicesMap` machinery accessed indirectly through the base class.

```mermaid
classDiagram
    class BluetoothDelegate {
        <<content:: interface>>
        +RunBluetoothChooser()
        +ShowBluetoothScanningPrompt()
        +ShowDevicePairPrompt()
        +GetWebBluetoothDeviceId()
        +GetDeviceAddress()
        +AddScannedDevice()
        +GrantServiceAccessPermission()
        +HasDevicePermission()
        +RevokeDevicePermissionWebInitiated()
        +MayUseBluetooth()
        +IsAllowedToAccessService()
        +IsAllowedToAccessAtLeastOneService()
        +IsAllowedToAccessManufacturerData()
        +GetPermittedDevices()
        +AddFramePermissionObserver()
        +RemoveFramePermissionObserver()
    }
    class ElectronBluetoothDelegate {
        -weak_factory_ : WeakPtrFactory
        +OnDevicePairPromptResponse()
    }
    BluetoothDelegate <|-- ElectronBluetoothDelegate

    class BluetoothChooser {
        <<electron::>>
        +SetAdapterPresence()
        +ShowDiscoveryState()
        +AddOrUpdateDevice()
        +OnDeviceChosen()
        +GetDeviceList()
    }
    class content_BluetoothChooser {
        <<content:: interface>>
    }
    content_BluetoothChooser <|-- BluetoothChooser

    ElectronBluetoothDelegate ..> BluetoothChooser : creates via RunBluetoothChooser()
```

---

## Related Component: `BluetoothChooser`

While `ElectronBluetoothDelegate` implements the Chromium-facing policy interface, the actual **chooser UI state machine** lives in `shell/browser/lib/bluetooth_chooser.h` (module: `shell_browser_lib`):

- `BluetoothChooser` implements `content::BluetoothChooser` and is constructed with an `api::WebContents*` and an `EventHandler` callback.
- It tracks discovered devices in `device_id_to_name_map_`, exposes `GetDeviceList()` for the JS-facing chooser UI, and forwards the user's selection back into Blink via `OnDeviceChosen()`.
- `ElectronBluetoothDelegate::RunBluetoothChooser()` is expected to construct and own a `BluetoothChooser` instance, wiring native device discovery events (`SetAdapterPresence`, `ShowDiscoveryState`, `AddOrUpdateDevice`) to JS renderer events (typically surfaced through the `Session`/`WebContents` JS API — see [shell_browser_api_session_net](shell_browser_api_session_net.md) and [shell_browser_api_webcontents](shell_browser_api_webcontents.md)).

```mermaid
sequenceDiagram
    participant Page as Web Page (Renderer)
    participant Blink as Blink (Bluetooth JS binding)
    participant RFH as RenderFrameHost
    participant Delegate as ElectronBluetoothDelegate
    participant Chooser as BluetoothChooser
    participant JS as Electron JS (select-bluetooth-device event)
    participant Adapter as device::BluetoothAdapter

    Page->>Blink: navigator.bluetooth.requestDevice(options)
    Blink->>RFH: Bluetooth request
    RFH->>Delegate: RunBluetoothChooser(frame, event_handler)
    Delegate->>Chooser: new BluetoothChooser(webContents, event_handler)
    Delegate->>JS: emit 'select-bluetooth-device' (via WebContents)
    Adapter->>Chooser: AddOrUpdateDevice(...)
    Chooser->>JS: update device list
    JS->>Chooser: user selects device (callback)
    Chooser->>Delegate: OnDeviceChosen(device_id)
    Delegate->>Blink: event_handler(device_id)
    Blink->>Page: resolve requestDevice() promise
```

---

## Permission & Identity Model

Web Bluetooth uses an opaque per-origin device identifier (`blink::WebBluetoothDeviceId`) to avoid leaking stable hardware addresses to web content. `ElectronBluetoothDelegate` mediates the mapping:

```mermaid
flowchart LR
    A[device::BluetoothDevice<br/>real MAC/address] -->|GrantServiceAccessPermission<br/>AddScannedDevice| B[blink::WebBluetoothDeviceId<br/>opaque per-origin id]
    B -->|GetDeviceAddress| A
    B --> C{HasDevicePermission?}
    C -->|yes| D[IsAllowedToAccessService]
    C -->|yes| E[IsAllowedToAccessManufacturerData]
    D --> F[GATT operations proceed in device layer]
    E --> F
    C -->|no| G[Access denied]
```

- **`GrantServiceAccessPermission`**: Called after the user picks a device in the chooser; creates/reuses a `WebBluetoothDeviceId` and records which GATT services the origin may access.
- **`HasDevicePermission` / `IsAllowedToAccessService` / `IsAllowedToAccessAtLeastOneService` / `IsAllowedToAccessManufacturerData`**: Read-only permission checks consulted by Blink before performing GATT reads/writes or exposing manufacturer data in advertisements.
- **`RevokeDevicePermissionWebInitiated`**: Supports the `BluetoothDevice.forget()` JS API, allowing a page to voluntarily drop its own permission grant.
- **`AddFramePermissionObserver` / `RemoveFramePermissionObserver`**: Lets Blink-side objects (e.g., `BluetoothDevice` JS wrappers) observe permission revocation to fire `gattserverdisconnected` events.

Persistent storage of grants is expected to be backed by Electron's permission infrastructure — see [shell_browser_context](shell_browser_context.md) (`ElectronPermissionManager`) for the general per-origin permission model that Bluetooth grants may interact with at a higher level (e.g., `session.setPermissionRequestHandler`).

---

## Integration with `ElectronBrowserClient`

`ElectronBluetoothDelegate` is one of several device delegates owned/created by `ElectronBrowserClient` (declared in `shell/browser/electron_browser_client.h`, module [shell_browser_main_parts](shell_browser_main_parts.md)), alongside:

- `ElectronHidDelegate` — see `shell_browser_hid`
- `ElectronSerialDelegate` — see `Serial` module (Device & Peripheral Access)
- `ElectronUsbDelegate` — see `USB` module (Device & Peripheral Access)
- `ElectronWebAuthenticationDelegate` — see `WebAuthn` module (Device & Peripheral Access)

These delegates share a common architectural pattern: implement a `content::XxxDelegate` interface, maintain a per-`RenderFrameHost` controller/chooser map, and bridge native device events to JS-facing APIs exposed on `Session` and `WebContents`.

```mermaid
graph TD
    subgraph "content:: layer (Chromium)"
        CBD[content::BluetoothDelegate]
        CHD[content::HidDelegate]
        CSD[content::SerialDelegate]
        CUD[content::UsbDelegate]
    end

    subgraph "Electron Browser Client"
        EBC[ElectronBrowserClient]
    end

    subgraph "Device Delegates (Electron)"
        EBD[ElectronBluetoothDelegate]
        EHD[ElectronHidDelegate]
        ESD[ElectronSerialDelegate]
        EUD[ElectronUsbDelegate]
    end

    EBC -->|GetBluetoothDelegate| EBD
    EBC -->|GetHidDelegate| EHD
    EBC -->|GetSerialDelegate| ESD
    EBC -->|GetUsbDelegate| EUD

    EBD -->|implements| CBD
    EHD -->|implements| CHD
    ESD -->|implements| CSD
    EUD -->|implements| CUD

    EBD --> BC[BluetoothChooser]
    EHD --> HCC[HidChooserController]
    ESD --> SCC[SerialChooserController]
    EUD --> UCC[UsbChooserController]
```

Note the architectural asymmetry: HID/Serial/USB delegates each maintain their own `ChooserController` map keyed by `RenderFrameHost*` (visible in their headers), whereas the Bluetooth delegate's per-frame/per-device bookkeeping is largely delegated to Chromium's built-in `BluetoothAllowedDevicesMap` (inherited via `content::BluetoothDelegate`'s base machinery) plus the standalone `BluetoothChooser` class for UI state — it does not expose an explicit `controller_map_` in its own header.

---

## Dependency Overview

```mermaid
graph LR
    ElectronBluetoothDelegate -->|depends on| ContentBluetoothDelegate[content::BluetoothDelegate]
    ElectronBluetoothDelegate -->|uses| WebBluetoothDeviceId[blink::WebBluetoothDeviceId]
    ElectronBluetoothDelegate -->|uses| DeviceBluetoothDevice[device::BluetoothDevice]
    ElectronBluetoothDelegate -->|uses| DeviceBluetoothUUID[device::BluetoothUUID]
    ElectronBluetoothDelegate -->|operates on| RenderFrameHost[content::RenderFrameHost]
    ElectronBluetoothDelegate -.creates.-> BluetoothChooser
    BluetoothChooser -->|references| APIWebContents["api::WebContents"]

    ElectronBrowserClientMod["ElectronBrowserClient<br/>(shell_browser_main_parts)"] -->|owns| ElectronBluetoothDelegate
    APIWebContents -.belongs to.-> WebContentsMod["shell_browser_api_webcontents"]
```

**Upstream dependents:**
- [shell_browser_main_parts](shell_browser_main_parts.md) — `ElectronBrowserClient::GetBluetoothDelegate()` returns/owns this delegate.

**Sibling modules (same parent: Device & Peripheral Access):**
- `shell_browser_hid` — analogous delegate for WebHID.
- `Serial` and `USB` delegate modules — analogous patterns for `navigator.serial` / `navigator.usb`.
- `WebAuthn` — `ElectronWebAuthenticationDelegate`, another content-layer security delegate.
- `shell_browser_lib` — houses `BluetoothChooser`, the chooser-UI counterpart used by this delegate.

**Downstream/consumer relationship:**
- [shell_browser_api_webcontents](shell_browser_api_webcontents.md) — `WebContents` emits JS events (e.g. `select-bluetooth-device`) that the chooser UI relies on.
- [shell_browser_context](shell_browser_context.md) — general permission infrastructure (`ElectronPermissionManager`) that complements device-specific grants.

---

## Typical Request Flow (End-to-End)

```mermaid
flowchart TD
    Start([Renderer calls navigator.bluetooth.requestDevice]) --> A[Blink invokes<br/>content::BluetoothDelegate::RunBluetoothChooser]
    A --> B[ElectronBluetoothDelegate::RunBluetoothChooser]
    B --> C[Construct BluetoothChooser]
    C --> D[Emit JS 'select-bluetooth-device' event<br/>on WebContents]
    D --> E{App provides<br/>event.callback?}
    E -- no --> F[Default native UI /<br/>auto-reject]
    E -- yes --> G[App JS selects device id]
    G --> H[BluetoothChooser::OnDeviceChosen]
    H --> I[event_handler invoked with device id]
    I --> J[ElectronBluetoothDelegate::GrantServiceAccessPermission]
    J --> K[WebBluetoothDeviceId returned to Blink]
    K --> L[Blink resolves requestDevice Promise<br/>with BluetoothDevice object]
    L --> M[Subsequent GATT calls check<br/>HasDevicePermission / IsAllowedToAccessService]
```

---

## Summary

| Aspect | Detail |
|---|---|
| **Interface implemented** | `content::BluetoothDelegate` |
| **Owning component** | `ElectronBrowserClient` |
| **Primary responsibilities** | Chooser UI orchestration, pairing prompts, device-id/address mapping, permission grant/check/revoke |
| **Companion class** | `BluetoothChooser` (`shell/browser/lib/bluetooth_chooser.h`) |
| **Related delegates** | `ElectronHidDelegate`, `ElectronSerialDelegate`, `ElectronUsbDelegate`, `ElectronWebAuthenticationDelegate` |
| **JS surface** | Exposed indirectly via `WebContents`/`Session` events (e.g. `select-bluetooth-device`), not a direct gin-wrapped API in this header |

For broader context on how device permission delegates fit into the browser process bootstrap, see [shell_browser_main_parts](shell_browser_main_parts.md). For the JS-facing session/permission APIs that applications use to respond to these native prompts, see [shell_browser_api_session_net](shell_browser_api_session_net.md) and [shell_browser_context](shell_browser_context.md).
