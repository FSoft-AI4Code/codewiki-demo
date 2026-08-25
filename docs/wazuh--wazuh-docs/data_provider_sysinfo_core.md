# Data Provider — SysInfo Core

## 1. Purpose

`data_provider_sysinfo_core` is the **platform dispatch layer** of Wazuh's `SysInfo` C++ library (part of the broader [System_Information_Data_Provider (C++)](System_Information_Data_Provider_(C++).md) module, referred to in this wiki simply as the data provider). It implements the concrete, OS-specific bodies of the `SysInfo` class methods (`getHardware()`, `getPackages()`, `getOsInfo()`, `getProcessesInfo()`, `getNetworks()`, `getPorts()`, `getHotfixes()`, `getGroups()`, `getUsers()`) and exposes a stable **C API** (`sysinfo_*` functions) that is consumed by native Wazuh daemons and modules such as `wazuh_modules/wm_syscollector.c` and the [syscollector native daemon](syscollector_module.md) (`syscollector_module_native_daemon`).

In short, this module answers the question **"how do I get hardware, OS, process, network, port, package, hotfix, group and user information on *this* operating system?"** for every platform Wazuh supports: Linux, macOS (Darwin/BSD-based), FreeBSD, OpenBSD, Solaris, generic Unix, and Windows.

The module itself contains no public interface class — it is a set of `.cpp` translation units that provide the implementation for the `SysInfo` class declared in [`SysInfo_Provider`](SysInfo_Provider.md) (`sysInfo.hpp`). Exactly **one** of the platform-specific `.cpp` files is compiled into the final binary, selected at build time based on the target OS.

## 2. Architecture Overview

```mermaid
graph TB
    subgraph "Public API Layer"
        SysInfoClass["SysInfo class<br/>(sysInfo.hpp)"]
        CAPI["C API Bridge<br/>sysInfo.cpp<br/>(sysinfo_* functions)"]
    end

    subgraph "data_provider_sysinfo_core (this module)"
        direction TB
        subgraph "Unix-family Implementations"
            Linux["sysInfoLinux.cpp"]
            Mac["sysInfoMac.cpp"]
            FreeBSD["sysInfoFreeBSD.cpp"]
            OpenBSD["sysInfoOpenBSD.cpp"]
            Solaris["sysInfoSolaris.cpp"]
            UnixGeneric["sysInfoUnix.cpp"]
            UnixUtils["UtilsWrapperUnix / UtilsWrapperLinux /<br/>UtilsWrapperMac"]
        end
        subgraph "Windows Implementation"
            Win["sysInfoWin.cpp"]
            WinUtils["utilsWrapperWin.cpp/.hpp<br/>(ComHelper)"]
        end
    end

    subgraph "Supporting Data Provider Sub-modules"
        Hardware["data_provider_hardware"]
        Network["data_provider_network"]
        Packages["data_provider_packages"]
        OsInfo["data_provider_osinfo"]
        Ports["data_provider_ports"]
        Groups["data_provider_groups"]
        Users["data_provider_users"]
        WrappersUnix["data_provider_wrappers_unix"]
        WrappersWin["data_provider_wrappers_windows"]
    end

    subgraph "Consumers"
        Syscollector["syscollector_module<br/>(wm_syscollector.c / syscollectord)"]
        InventoryHarvester["inventory_harvester_module"]
    end

    CAPI --> SysInfoClass
    SysInfoClass -.->|"one impl. selected<br/>at build time"| Linux
    SysInfoClass -.-> Mac
    SysInfoClass -.-> FreeBSD
    SysInfoClass -.-> OpenBSD
    SysInfoClass -.-> Solaris
    SysInfoClass -.-> UnixGeneric
    SysInfoClass -.-> Win

    Linux --> Hardware
    Linux --> Network
    Linux --> Packages
    Linux --> OsInfo
    Linux --> Ports
    Linux --> Groups
    Linux --> Users
    Linux --> UnixUtils
    Linux --> WrappersUnix

    Mac --> Hardware
    Mac --> Packages
    Mac --> Groups
    Mac --> Users
    Mac --> WrappersUnix

    Win --> WinUtils
    Win --> Packages
    Win --> Groups
    Win --> Users
    Win --> WrappersWin

    Syscollector --> CAPI
    InventoryHarvester -.->|"consumes syscollector<br/>output indirectly"| Syscollector
```

### Key Design Points

- **Single Responsibility per File**: Each `sysInfo<Platform>.cpp` file provides the full set of `SysInfo::get*()` overrides for exactly one platform family. Only one file participates in any given compiled binary.
- **Callback-based Streaming**: Several methods (`getProcessesInfo`, `getPackages`) have both a "collect-and-return" overload (`nlohmann::json getX() const`) and a "streaming" overload (`void getX(std::function<void(nlohmann::json&)> callback) const`) used to avoid materializing very large in-memory JSON documents (e.g., thousands of processes/packages) when the caller wants to process items one at a time (see the `sysinfo_packages_cb` / `sysinfo_processes_cb` C API functions).
- **C API Bridge**: `sysInfo.cpp` wraps the C++ `SysInfo` class with a plain-C, `cJSON`-based interface (`sysinfo_hardware`, `sysinfo_packages`, `sysinfo_os`, `sysinfo_processes`, `sysinfo_networks`, `sysinfo_ports`, `sysinfo_hotfixes`, `sysinfo_groups`, `sysinfo_users`, plus the `_cb` streaming variants and `sysinfo_free_result`). This is the ABI boundary used by C daemons (e.g., `wm_syscollector.c`) that cannot link directly against C++ STL types.
- **Delegation to Specialized Sub-modules**: The platform files themselves delegate heavy-lifting to focused sub-modules documented elsewhere in this wiki:
  - Hardware detection → [data_provider_hardware](data_provider_hardware.md)
  - Network interface enumeration → [data_provider_network](data_provider_network.md)
  - Package inventory (native + PyPI/NPM/etc.) → [data_provider_packages](data_provider_packages.md)
  - OS release/version parsing → [data_provider_osinfo](data_provider_osinfo.md)
  - Open port enumeration → [data_provider_ports](data_provider_ports.md)
  - Group/user enumeration → [data_provider_groups](data_provider_groups.md) and [data_provider_users](data_provider_users.md)
  - Low-level OS primitive wrappers → [data_provider_wrappers_unix](data_provider_wrappers_unix.md) and [data_provider_wrappers_windows](data_provider_wrappers_windows.md)
- **Graceful Degradation**: Platforms with limited support (FreeBSD, OpenBSD, Solaris, generic Unix) simply return empty `nlohmann::json{}` objects for unsupported categories (e.g., processes, ports, hotfixes, groups, users) rather than failing, keeping the unified `SysInfo` interface usable everywhere.

## 3. Sub-modules

This module is split into three sub-modules along platform boundaries, each documented in detail in its own file:

| Sub-module | Description | Documentation |
|---|---|---|
| **C API Bridge** | The `extern "C"` `sysinfo_*` functions and cJSON conversion glue that expose the C++ `SysInfo` class to C callers. | [data_provider_sysinfo_core_capi.md](data_provider_sysinfo_core_capi.md) |
| **Unix-family Platform Implementations** | `SysInfo` method implementations for Linux, macOS, FreeBSD, OpenBSD, Solaris and generic Unix, plus their small OS-primitive wrapper helpers (`UtilsWrapperUnix`, `UtilsWrapperLinux`, `UtilsWrapperMac`). | [data_provider_sysinfo_core_unix.md](data_provider_sysinfo_core_unix.md) |
| **Windows Platform Implementation** | `SysInfo` method implementations for Windows, including TCP/UDP port table enumeration (`getTablePorts`), registry-based package/hotfix discovery, and the `ComHelper` WMI/Windows Update Agent COM wrapper (`ConvertStringToBSTR`). | [data_provider_sysinfo_core_windows.md](data_provider_sysinfo_core_windows.md) |

> **Note:** All three sub-module documents, along with this overview, live in the same flat documentation folder as the rest of the wiki (not nested under a `data_provider_sysinfo_core/` path).

## 4. High-Level Data Flow

```mermaid
sequenceDiagram
    participant Daemon as "C Daemon (e.g. syscollector)"
    participant CAPI as "C API Bridge (sysinfo.cpp)"
    participant SysInfo as "SysInfo class"
    participant Platform as "Platform-specific getX()"
    participant SubModules as "Specialized sub-modules<br/>(hardware/network/packages/...)"

    Daemon->>CAPI: sysinfo_hardware(&js_result)
    CAPI->>SysInfo: SysInfo::hardware()
    SysInfo->>Platform: getHardware() [platform impl.]
    Platform->>SubModules: FactoryHardwareFamilyCreator / OS calls
    SubModules-->>Platform: hardware data
    Platform-->>SysInfo: nlohmann::json
    SysInfo-->>CAPI: nlohmann::json
    CAPI->>CAPI: cJSON_Parse(json.dump())
    CAPI-->>Daemon: cJSON* result (retVal 0/-1)
    Daemon->>CAPI: sysinfo_free_result(&js_result)
```

For streaming-style queries (packages, processes), the flow is similar but the daemon supplies a native callback that is invoked once per item, avoiding a full in-memory buildup:

```mermaid
sequenceDiagram
    participant Daemon as "C Daemon"
    participant CAPI as "sysinfo_packages_cb / sysinfo_processes_cb"
    participant SysInfo as "SysInfo::packages(cb) / processes(cb)"
    participant Platform as "Platform getPackages(cb) / getProcessesInfo(cb)"

    Daemon->>CAPI: sysinfo_packages_cb({callback, user_data})
    CAPI->>SysInfo: info.packages(callbackWrapper)
    SysInfo->>Platform: getPackages(callback)
    loop for each package found
        Platform->>CAPI: callbackWrapper(json&)
        CAPI->>Daemon: callback(GENERIC, cJSON*, user_data)
    end
```

## 5. How this module fits into the System

- **Upstream dependency**: [`SysInfo_Provider`](SysInfo_Provider.md) declares the abstract `SysInfo` class interface (`sysInfo.hpp`) that this module implements per-platform.
- **Sibling data-provider sub-modules**: Hardware, network, packages, OS-info, ports, groups and users detection logic is factored out into dedicated sub-modules (see table above); the platform files in this module act as the **orchestration/glue layer** that calls into those factories and assembles the final JSON documents returned by `SysInfo`.
- **Downstream consumers**: The compiled `SysInfo` shared library (and its C API) is consumed by:
  - The native `syscollector` module (see [syscollector_module](syscollector_module.md) and its native daemon sub-module `syscollector_module_native_daemon`), which periodically scans the host and publishes hardware/OS/network/port/package/hotfix/user/group inventory to the Wazuh manager.
  - The [inventory_harvester_module](inventory_harvester_module.md), which indexes syscollector-produced inventory data into the Wazuh indexer.
  - Test tooling under `data_provider_testtool` (`testtool/main.cpp`, `cmdLineActions.h`) used to manually exercise `SysInfo` from the command line.
- **Build-time platform selection**: Only one of the platform `.cpp` files described here is included per target build; there is no runtime dispatch — the correct implementation is selected by the build system (CMake) based on the compilation target OS.
