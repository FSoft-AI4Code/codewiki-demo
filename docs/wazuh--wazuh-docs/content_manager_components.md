# Content Manager Components

## Introduction

The **Content Manager Components** module provides the pluggable, strategy-driven building blocks used by the Wazuh **Content Manager** to download, decompress, and version-update external content (CTI feeds, vulnerability databases, offline packages, etc.). It exposes three **factory classes** — `FactoryDownloader`, `FactoryDecompressor`, and `FactoryVersionUpdater` — that instantiate the correct concrete strategy at runtime based on JSON configuration, plus a concrete downloader implementation, `CtiSnapshotDownloader`, used to retrieve full content snapshots from the Wazuh CTI (Cyber Threat Intelligence) API.

These components are consumed by the [Content Manager Orchestration](content_manager_orchestration.md) layer, which builds a **Chain of Responsibility** pipeline (download → decompress → version-update → publish) for each content update run. This module sits below the orchestration layer and above the [Shared Utils](shared_utils.md) primitives (chain-of-responsibility base classes, RocksDB wrapper, compression helpers) that it relies on.

This documentation covers:
1. Purpose and responsibilities of each component
2. Architecture and how components plug into the Content Manager pipeline
3. Data flow and interaction diagrams
4. Relationships to other Content Manager and Shared Modules documentation

---

## Module Position in the System

The Content Manager is part of the **Shared Modules Infrastructure (C++)** family. The diagram below shows where `content_manager_components` sits relative to its sibling modules.

```mermaid
graph TB
    subgraph "Shared Modules Infrastructure (C++)"
        CM_API["content_manager_public_api<br/>(ContentModule, ContentRegister)"]
        CM_FACADE["content_manager_facade<br/>(ContentModuleFacade, ContentProvider, OnDemandManager)"]
        CM_ORCH["content_manager_orchestration<br/>(ActionOrchestrator, UpdaterContext)"]
        CM_COMP["content_manager_components<br/>(THIS MODULE)"]
        UTILS["shared_utils<br/>(chainOfResponsability, RocksDB, xz/zip/gzip helpers)"]
    end

    CM_API --> CM_FACADE
    CM_FACADE --> CM_ORCH
    CM_ORCH --> CM_COMP
    CM_COMP --> UTILS

    style CM_COMP fill:#f9d77e,stroke:#333,stroke-width:2px
```

See also: [content_manager_public_api](content_manager_public_api.md), [content_manager_facade](content_manager_facade.md), [content_manager_orchestration](content_manager_orchestration.md), [shared_utils](shared_utils.md).

---

## Core Components

| Component | File | Responsibility |
|---|---|---|
| `FactoryDownloader` | `factoryDownloader.hpp` | Selects and instantiates the concrete downloader (API, CTI-offset, CTI-snapshot, file, offline) based on `contentSource`. |
| `FactoryDecompressor` | `factoryDecompressor.hpp` | Selects and instantiates the concrete decompressor (xz, gzip, zip, raw/skip) based on `compressionType`, with auto-deduction for offline sources. |
| `FactoryVersionUpdater` | `factoryVersionUpdater.hpp` | Selects and instantiates the concrete version-updater (cti-api, offline, or no-op) based on `versionedContent`. |
| `CtiSnapshotDownloader` | `CtiSnapshotDownloader.hpp` | Concrete `CtiDownloader` implementation that fetches a full content snapshot from the CTI API. |

All factories produce objects that implement `AbstractHandler<std::shared_ptr<UpdaterContext>>` (from [shared_utils](shared_utils.md)'s Chain of Responsibility pattern), allowing them to be chained together transparently by the orchestration layer.

---

## Architecture

### Class/Component Relationships

```mermaid
classDiagram
    class AbstractHandler~T~ {
        <<abstract>>
        +setNext(next) shared_ptr~Handler~
        +setLast(last) shared_ptr~Handler~
        +handleRequest(data) T
        +next() shared_ptr~AbstractHandler~
    }

    class FactoryDownloader {
        +create(config) shared_ptr~AbstractHandler~
    }
    class FactoryDecompressor {
        +create(config) shared_ptr~AbstractHandler~
        -deduceCompressionType(inputFile) string
    }
    class FactoryVersionUpdater {
        +create(config) shared_ptr~AbstractHandler~
    }

    class CtiDownloader {
        <<abstract>>
        #performQueryWithRetry()
        #getCtiBaseParameters(url)
        #download(context)*
    }
    class CtiSnapshotDownloader {
        +download(context)
    }
    class APIDownloader
    class CtiOffsetDownloader
    class FileDownloader
    class OfflineDownloader

    class XZDecompressor
    class GzipDecompressor
    class ZipDecompressor
    class SkipStep

    class UpdateCtiApiOffset
    class UpdateOffline

    AbstractHandler <|-- CtiDownloader
    CtiDownloader <|-- CtiSnapshotDownloader
    CtiDownloader <|-- CtiOffsetDownloader
    AbstractHandler <|-- APIDownloader
    AbstractHandler <|-- FileDownloader
    AbstractHandler <|-- OfflineDownloader
    AbstractHandler <|-- XZDecompressor
    AbstractHandler <|-- GzipDecompressor
    AbstractHandler <|-- ZipDecompressor
    AbstractHandler <|-- SkipStep
    AbstractHandler <|-- UpdateCtiApiOffset
    AbstractHandler <|-- UpdateOffline

    FactoryDownloader ..> APIDownloader : creates
    FactoryDownloader ..> CtiOffsetDownloader : creates
    FactoryDownloader ..> CtiSnapshotDownloader : creates
    FactoryDownloader ..> FileDownloader : creates
    FactoryDownloader ..> OfflineDownloader : creates

    FactoryDecompressor ..> XZDecompressor : creates
    FactoryDecompressor ..> GzipDecompressor : creates
    FactoryDecompressor ..> ZipDecompressor : creates
    FactoryDecompressor ..> SkipStep : creates

    FactoryVersionUpdater ..> UpdateCtiApiOffset : creates
    FactoryVersionUpdater ..> UpdateOffline : creates
    FactoryVersionUpdater ..> SkipStep : creates
```

### Dependency Diagram

```mermaid
graph LR
    subgraph content_manager_components
        FD[FactoryDownloader]
        FDec[FactoryDecompressor]
        FVU[FactoryVersionUpdater]
        CSD[CtiSnapshotDownloader]
    end

    subgraph content_manager_orchestration
        UC[UpdaterContext / UpdaterBaseContext]
        AO[ActionOrchestrator]
    end

    subgraph shared_utils
        AH[AbstractHandler / Handler]
        RB[RocksDBWrapper]
        XZ[XzHelper]
        ZL[ZlibHelper]
        AR[ArchiveHelper]
    end

    AO -->|builds pipeline via| FD
    AO -->|builds pipeline via| FDec
    AO -->|builds pipeline via| FVU
    FD -->|instantiates| CSD
    CSD -->|uses IURLRequest, mutates| UC
    FD -.implements.-> AH
    FDec -.implements.-> AH
    FVU -.implements.-> AH
    FDec -->|uses| XZ
    FDec -->|uses| ZL
    FDec -->|uses| AR
    UC -->|references| RB
```

---

## Component Details

### 1. `FactoryDownloader`

**Purpose:** Given the `contentSource` field of the run configuration, creates the appropriate downloader handler:

| `contentSource` value | Concrete class created |
|---|---|
| `api` | `APIDownloader` |
| `cti-offset` | `CtiOffsetDownloader` |
| `cti-snapshot` | `CtiSnapshotDownloader` |
| `file` | `FileDownloader` |
| `offline` | `OfflineDownloader` |

All downloaders use the singleton `HTTPRequest::instance()` (except `FileDownloader`, which reads from the local filesystem). An invalid `contentSource` value throws `std::invalid_argument`.

### 2. `FactoryDecompressor`

**Purpose:** Given the `compressionType` field, creates the appropriate decompressor handler:

| `compressionType` value | Concrete class created |
|---|---|
| `xz` | `XZDecompressor` |
| `gzip` | `GzipDecompressor` |
| `zip` | `ZipDecompressor` |
| `raw` | `SkipStep` (no-op) |

**Special behavior:** When `contentSource == "offline"`, the compression type is **auto-deduced** from the URL's file extension (`.gz` → gzip, `.xz` → xz, `.zip` → zip, otherwise raw) via the private `deduceCompressionType()` helper, and the `config` JSON is mutated in place to reflect the deduced type.

### 3. `FactoryVersionUpdater`

**Purpose:** Given the `versionedContent` field, creates the appropriate version-updater handler:

| `versionedContent` value | Concrete class created |
|---|---|
| `cti-api` | `UpdateCtiApiOffset` |
| `offline` | `UpdateOffline` |
| `false` | `SkipStep` (no-op, content is not versioned) |

An unrecognized value throws `std::invalid_argument`.

### 4. `CtiSnapshotDownloader`

**Purpose:** Concrete downloader (extending the abstract `CtiDownloader` base) that retrieves a **full content snapshot** from the CTI API, used typically for the first synchronization or full re-sync scenarios (as opposed to `CtiOffsetDownloader`, which fetches incremental changes).

**Behavior:**
1. Reads the CTI base `url` from `context.spUpdaterBaseContext->configData`.
2. Calls `getCtiBaseParameters(baseURL)` (inherited from `CtiDownloader`) to retrieve consistency metadata, including `lastSnapshotLink` and `lastSnapshotOffset`.
3. Throws `std::runtime_error` if snapshot metadata is missing.
4. Computes the output file path inside `context.spUpdaterBaseContext->downloadsFolder`.
5. Performs the HTTP download with retry logic (`performQueryWithRetry`), and on success:
   - Appends the downloaded file path to `context.data["paths"]`.
   - Sets `context.data["offset"]` to the new snapshot offset.
   - Updates `context.currentOffset`.

---

## Data Flow

### Content Update Pipeline (Chain of Responsibility)

```mermaid
sequenceDiagram
    participant Orchestrator as ActionOrchestrator<br/>(content_manager_orchestration)
    participant FD as FactoryDownloader
    participant FDec as FactoryDecompressor
    participant FVU as FactoryVersionUpdater
    participant Chain as Handler Chain
    participant CSD as CtiSnapshotDownloader
    participant CTI as CTI API / File / Offline Source

    Orchestrator->>FD: create(config)
    FD-->>Orchestrator: downloader handler
    Orchestrator->>FDec: create(config)
    FDec-->>Orchestrator: decompressor handler
    Orchestrator->>FVU: create(config)
    FVU-->>Orchestrator: version-updater handler

    Orchestrator->>Chain: setNext(downloader, decompressor, version-updater, ...)
    Orchestrator->>Chain: handleRequest(UpdaterContext)

    Chain->>CSD: handleRequest(context)  [if contentSource=cti-snapshot]
    CSD->>CTI: getCtiBaseParameters(url)
    CTI-->>CSD: lastSnapshotLink, lastSnapshotOffset
    CSD->>CTI: performQueryWithRetry(downloadURL)
    CTI-->>CSD: file data written to downloadsFolder
    CSD->>CSD: update context.data.paths, context.data.offset
    CSD->>Chain: forward to next handler (decompressor)
    Chain-->>Orchestrator: final UpdaterContext (ready to publish)
```

### Decompression Type Resolution Flow

```mermaid
flowchart TD
    A[FactoryDecompressor::create] --> B{contentSource == offline?}
    B -- Yes --> C[deduceCompressionType URL]
    C --> D{file extension}
    D -->|.gz| E[gzip]
    D -->|.xz| F[xz]
    D -->|.zip| G[zip]
    D -->|other| H[raw]
    E --> I[mutate config.compressionType]
    F --> I
    G --> I
    H --> I
    B -- No --> J[use config.compressionType as-is]
    I --> K{decompressorType}
    J --> K
    K -->|xz| L[XZDecompressor]
    K -->|gzip| M[GzipDecompressor]
    K -->|zip| N[ZipDecompressor]
    K -->|raw| O[SkipStep]
    K -->|other| P[throw invalid_argument]
```

---

## Interaction with UpdaterContext

All factory-created handlers, and `CtiSnapshotDownloader` specifically, operate on a shared `UpdaterContext` object (defined in `content_manager_orchestration`'s `updaterContext.hpp`):

- **`UpdaterBaseContext`**: Holds run-scoped, immutable-ish configuration: `configData` (JSON config used by all factories), `downloadsFolder`, `contentsFolder`, `outputFolder`, RocksDB handle, stop-condition, and the file-processing callback.
- **`UpdaterContext`**: Holds per-run mutable state: `data` (JSON payload eventually published, including `paths`, `offset`, `stageStatus`) and `currentOffset`.

```mermaid
graph TD
    UBC[UpdaterBaseContext] -->|configData used by| FD[FactoryDownloader]
    UBC -->|configData used by| FDec[FactoryDecompressor]
    UBC -->|configData used by| FVU[FactoryVersionUpdater]
    UBC -->|downloadsFolder used by| CSD[CtiSnapshotDownloader]
    UC[UpdaterContext] -->|data.paths and data.offset written by| CSD
    UBC -.contained in.-> UC
```

For full details on `UpdaterContext`/`UpdaterBaseContext` and how the pipeline is assembled and executed, see [content_manager_orchestration](content_manager_orchestration.md).

---

## Design Patterns Used

- **Factory Method**: Each `Factory*` class encapsulates object-creation logic keyed off configuration strings, decoupling the orchestrator from concrete downloader/decompressor/updater classes.
- **Chain of Responsibility**: All created objects implement `AbstractHandler<std::shared_ptr<UpdaterContext>>` (see [shared_utils → design_patterns](shared_utils.md)), allowing the orchestrator to link them into a single processing pipeline and invoke `handleRequest()` once.
- **Template Method** (inherited): `CtiSnapshotDownloader` overrides only the `download()` step of the `CtiDownloader` base class, reusing shared retry/query logic (`performQueryWithRetry`, `getCtiBaseParameters`) common to all CTI-based downloaders (e.g., `CtiOffsetDownloader`).

---

## Error Handling

| Component | Failure Condition | Behavior |
|---|---|---|
| `FactoryDownloader` | Unknown `contentSource` | Throws `std::invalid_argument` |
| `FactoryDecompressor` | Unknown `compressionType` | Throws `std::invalid_argument` |
| `FactoryVersionUpdater` | Unknown `versionedContent` | Throws `std::invalid_argument` |
| `CtiSnapshotDownloader` | Missing `lastSnapshotLink`/`lastSnapshotOffset` in CTI metadata | Throws `std::runtime_error` |

These exceptions propagate up to the orchestration layer, which is responsible for logging and reporting failure status (see `content_manager_orchestration`'s `ActionOrchestrator`).

---

## Related Documentation

- [content_manager_public_api](content_manager_public_api.md) — Public `ContentModule`/`ContentRegister` API that clients use to register and start content update tasks.
- [content_manager_facade](content_manager_facade.md) — Facade layer (`ContentModuleFacade`, `ContentProvider`, `OnDemandManager`) that drives scheduled/on-demand content updates.
- [content_manager_orchestration](content_manager_orchestration.md) — Builds and executes the Chain of Responsibility pipeline using the factories documented here, and owns `UpdaterContext`/`UpdaterBaseContext`.
- [shared_utils](shared_utils.md) — Provides `AbstractHandler`/`Handler` (chain-of-responsibility base), `RocksDBWrapper`, and compression helpers (`XzHelper`, `ZlibHelper`, `ArchiveHelper`) consumed by these components.
