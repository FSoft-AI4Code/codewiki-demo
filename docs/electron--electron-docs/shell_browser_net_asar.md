# `shell_browser_net_asar` Module Documentation

## Introduction

The **`shell_browser_net_asar`** module is a leaf sub-module of Electron's
[Networking Layer](Networking_Layer.md) (specifically of the
[`shell_browser_net`](shell_browser_net.md) group). It is responsible for
serving content that lives **inside `.asar` archives** through the standard
Chromium `network::mojom::URLLoader` / `URLLoaderFactory` Mojo interfaces.

When Electron packages an application, source files, resources and other
assets are frequently bundled into a single `.asar` archive (a tar-like
container format defined in the [`Asar`](Asar.md) common module). Renderer
and browser code, however, still needs to access these files as if they were
normal files on disk (e.g. via `file://` URLs, `require()`, or `fs` calls).
This module bridges that gap at the network layer: it intercepts `file://`
(and other) URL loads that target paths inside an `.asar` archive, transparently
extracts/streams the requested bytes, and — critically — **cryptographically
validates** the integrity of every byte served, protecting against tampering
of the packaged application.

The module has three primary responsibilities, one per file:

| Component | Responsibility |
|---|---|
| `AsarURLLoaderFactory` | Mojo `URLLoaderFactory` implementation that is registered for `file://`-like schemes and creates a loader for each request that targets a path inside (or outside) an asar archive. |
| `CreateAsarURLLoader` (in `asar_url_loader.h`) | Free function that does the actual work of resolving a URL to a location inside an archive (or a plain file) and starts streaming the response back to the requester. |
| `AsarFileValidator` | A `mojo::FilteredDataSource::Filter` that hashes each block of data as it is read from disk and compares it against the integrity metadata stored in the archive header, aborting the read if validation fails. |

## Position in the System

```mermaid
graph TD
    NL[Networking_Layer] --> BN[shell_browser_net]
    BN --> ASAR[shell_browser_net_asar<br/><b>this module</b>]
    BN --> URLL[shell_browser_net_url_loader]
    BN --> PROXY[shell_browser_net_proxying]
    BN --> CTX[shell_browser_net_context]
    BN --> RES[shell_browser_net_resolution]
    NL --> PREG[Protocol_Registry]

    ASAR -.uses.-> ASARCOMMON[Asar<br/>shell/common/asar]
    PREG -.registers factories from.-> ASAR
    PREG -.registers factories from.-> URLL

    click NL "Networking_Layer.md"
    click BN "shell_browser_net.md"
    click URLL "shell_browser_net_url_loader.md"
    click PROXY "shell_browser_net_proxying.md"
    click CTX "shell_browser_net_context.md"
    click RES "shell_browser_net_resolution.md"
    click PREG "Protocol_Registry.md"
    click ASARCOMMON "Asar.md"
```

The module sits at a specific, well-scoped point in the URL-loading pipeline:
it is one of several **non-network URL loader factories** that
[`ProtocolRegistry`](Protocol_Registry.md) and
[`ElectronBrowserContext`](shell_browser_context.md) install for `file:` and
custom schemes. Once installed, any `file://` request whose path resolves
into an `.asar` file is transparently handled here rather than going through
the OS filesystem loader directly.

It depends on:
- **[`Asar`](Asar.md)** (`shell/common/asar/archive.h`, `asar_util.h`) — the
  archive-format parser that knows how to look up file offsets/sizes and
  integrity hashes (`IntegrityPayload`) inside a `.asar` container.
- Chromium's **Mojo** `network::mojom::URLLoader` / `URLLoaderFactory` /
  `SelfDeletingURLLoaderFactory` interfaces, and `mojo::FileDataSource` /
  `mojo::FilteredDataSource` for streaming file bytes with an interposed
  filter.

It is depended on by:
- **[`Protocol_Registry`](Protocol_Registry.md)**, which registers the
  factory produced by `AsarURLLoaderFactory::Create()` for handling
  `file://`-scheme non-network navigations and subresource loads.
- **[`shell_browser_context`](shell_browser_context.md)**, indirectly, since
  `ElectronBrowserContext` wires up `ProtocolRegistry` during browser
  context construction.

## Architecture

```mermaid
classDiagram
    class AsarURLLoaderFactory {
        <<network::SelfDeletingURLLoaderFactory>>
        +Create() PendingRemote~URLLoaderFactory~
        -CreateLoaderAndStart(loader, request_id, options, request, client, traffic_annotation)
        -AsarURLLoaderFactory(factory_receiver)
    }

    class CreateAsarURLLoader {
        <<free function>>
        +CreateAsarURLLoader(request, loader, client, extra_response_headers)
    }

    class AsarFileValidator {
        <<mojo::FilteredDataSource::Filter>>
        -base::File file_
        -IntegrityPayload integrity_
        -uint64 read_start_
        -uint64 extra_read_
        -uint64 read_max_
        -int current_block_
        -int max_block_
        -optional~Hasher~ current_hash_
        +OnRead(buffer, result)
        +OnDone()
        +SetRange(read_start, extra_read, read_max)
        +SetCurrentBlock(current_block)
        #FinishBlock() bool
        -EnsureBlockHashExists()
    }

    class Archive {
        <<shell/common/asar>>
        +Init() bool
        +GetFileInfo(path, info) bool
        +Stat(path, stats) bool
        +Readdir(path, files) bool
        +Realpath(path, realpath) bool
        +CopyFileOut(path, out) bool
        +GetUnsafeFD() int
        +HeaderIntegrity() optional~IntegrityPayload~
    }

    class FilteredDataSourceFilter {
        <<mojo interface>>
    }

    class SelfDeletingURLLoaderFactory {
        <<network interface>>
    }

    AsarURLLoaderFactory --|> SelfDeletingURLLoaderFactory
    AsarURLLoaderFactory ..> CreateAsarURLLoader : delegates to
    CreateAsarURLLoader ..> Archive : resolves path and integrity via
    CreateAsarURLLoader ..> AsarFileValidator : attaches as read filter
    AsarFileValidator --|> FilteredDataSourceFilter
    AsarFileValidator ..> Archive : uses IntegrityPayload from
```

### Key design points

- **`AsarURLLoaderFactory`** follows the `SelfDeletingURLLoaderFactory`
  pattern used throughout Electron's non-network loaders: it deletes itself
  once its Mojo receiver disconnects, so callers only need to hold the
  `PendingRemote` returned by `Create()`.
- **`CreateAsarURLLoader`** is intentionally a free function (not a class)
  because loader lifetime is entirely managed via Mojo bindings
  (`PendingReceiver<URLLoader>` / `PendingRemote<URLLoaderClient>`) rather
  than an owning C++ object graph — this mirrors the pattern in the sibling
  [`shell_browser_net_url_loader`](shell_browser_net_url_loader.md) module's
  `NodeStreamLoader`.
- **`AsarFileValidator`** is a *filter*, not a data source itself. It is
  composed into a `mojo::FilteredDataSource` wrapping a
  `mojo::FileDataSource`, intercepting each `OnRead` callback to verify
  block-level hashes before data is forwarded to the client, and calling
  `OnDone` to check that the terminal/partial block was fully validated.
  This design cleanly separates *I/O* (handled by `mojo::FileDataSource`)
  from *integrity checking* (handled here), following the decorator pattern.

## Data Flow: Serving a File Inside an `.asar` Archive

```mermaid
sequenceDiagram
    participant Client as URLLoaderClient (renderer/browser consumer)
    participant Registry as ProtocolRegistry
    participant Factory as AsarURLLoaderFactory
    participant Loader as CreateAsarURLLoader
    participant Archive as asar::Archive
    participant Validator as AsarFileValidator
    participant FS as base::File (disk)

    Client->>Registry: file:// request for path inside app.asar
    Registry->>Factory: CreateLoaderAndStart(loader, request, client, ...)
    Factory->>Loader: CreateAsarURLLoader(request, loader, client, headers)
    Loader->>Archive: Resolve path -> Stat()/GetFileInfo()
    Archive-->>Loader: FileInfo{offset, size, integrity}
    Loader->>Validator: new AsarFileValidator(integrity, file)
    Loader->>Validator: SetRange(read_start, extra_read, read_max)
    Loader->>FS: Open archive file, seek to offset

    loop For each read chunk
        FS-->>Validator: OnRead(buffer, result)
        Validator->>Validator: EnsureBlockHashExists() / hash chunk
        alt Hash matches
            Validator-->>Loader: buffer passes through
            Loader-->>Client: OnStartLoadingResponseBody / data
        else Hash mismatch
            Validator-->>Loader: mark result as error
            Loader-->>Client: OnComplete(integrity error)
        end
    end

    Validator->>Validator: OnDone() - finalize last block via FinishBlock()
    Loader-->>Client: OnComplete(net::OK)
```

### Notes on the flow

1. **Resolution** — `CreateAsarURLLoader` uses the `asar` archive APIs
   (see [`Asar`](Asar.md)) to translate the request path into either:
   - an offset/size range inside a `.asar` file (packed asset), or
   - a real filesystem path (unpacked asset, e.g. native `.node` binaries
     marked `unpacked` in `Archive::FileInfo`).
2. **Streaming with validation** — For packed files, a
   `mojo::FileDataSource` reads raw bytes from the underlying archive file
   descriptor (`Archive::GetUnsafeFD()`), and the response is wrapped in a
   `mojo::FilteredDataSource` using `AsarFileValidator` as the filter. This
   guarantees that **no unvalidated byte ever reaches the client** — even
   though the OS-level read might be optimistically buffered.
3. **Block-based hashing** — `IntegrityPayload` (from `shell/common/asar/archive.h`)
   stores a hash-per-block scheme; `AsarFileValidator` tracks `current_block_`
   / `max_block_` and accumulates `current_hash_byte_count_` /
   `total_hash_byte_count_` to know exactly when a block's hash is complete
   and can be checked (`FinishBlock()`), including the special-case partial
   final block handled in `OnDone()`.
4. **Range requests** — `SetRange(read_start, extra_read, read_max)` supports
   partial/ranged reads (e.g. HTTP Range requests or resumed streams) while
   still being able to correctly align to hash-block boundaries — `extra_read_`
   represents bytes consumed purely for hash computation that are not
   forwarded to the actual response body.

## Component Interaction Within `shell_browser_net`

```mermaid
graph LR
    subgraph shell_browser_net_asar
        AULF[AsarURLLoaderFactory]
        CAUL[CreateAsarURLLoader]
        AFV[AsarFileValidator]
    end

    subgraph shell_browser_net_url_loader
        EULF[ElectronURLLoaderFactory]
        NSL[NodeStreamLoader]
    end

    subgraph Protocol_Registry
        PR[ProtocolRegistry]
    end

    PR -->|RegisterURLLoaderFactories for file scheme| AULF
    PR -->|RegisterProtocol / InterceptProtocol for custom schemes| EULF
    AULF --> CAUL
    CAUL --> AFV
    EULF -.similar self-deleting pattern.- AULF
```

`AsarURLLoaderFactory` and `ElectronURLLoaderFactory`
(from [`shell_browser_net_url_loader`](shell_browser_net_url_loader.md)) are
structural siblings: both extend
`network::SelfDeletingURLLoaderFactory` and are registered by
[`ProtocolRegistry`](Protocol_Registry.md). The key difference is scope —
`AsarURLLoaderFactory` is specialized purely for transparently reading
archive-packed application files (with integrity verification), whereas
`ElectronURLLoaderFactory` implements the full user-scriptable
`protocol.registerFileProtocol` / `registerBufferProtocol` /
`registerStreamProtocol` / `registerHttpProtocol` surface exposed to JS via
the `session.protocol` API (see
[`shell_browser_api_session_net_protocol_netlog`](shell_browser_api_session_net_protocol_netlog.md)).

## Security Model

```mermaid
flowchart TD
    A[App packaged as .asar] --> B[Header contains per-file IntegrityPayload hashes]
    B --> C{Request for file inside asar}
    C --> D[AsarFileValidator computes hash of each block read]
    D --> E{Computed hash equals expected hash?}
    E -->|Yes| F[Bytes forwarded to URLLoaderClient]
    E -->|No| G[Read aborted / error surfaced / Request fails]
```

This validator is Electron's core defense against **asar tampering
attacks**, where an attacker modifies the contents of a shipped `.asar`
archive without recomputing the application's code-signature-protected
header. Because `AsarFileValidator` re-hashes data on every read (not just
once at startup), even runtime modification of the archive file on disk
after the app has launched will be detected and the offending read will
fail rather than silently serving corrupted or malicious bytes.

## Related Modules

- [`Asar`](Asar.md) — the underlying archive format library
  (`Archive`, `IntegrityPayload`, `ScopedTemporaryFile`) consumed by this
  module to resolve paths and obtain integrity metadata.
- [`shell_browser_net`](shell_browser_net.md) — parent module grouping all
  browser-process networking components.
- [`shell_browser_net_url_loader`](shell_browser_net_url_loader.md) — sibling
  module providing the general-purpose custom-protocol URL loader
  (`ElectronURLLoaderFactory`) and Node stream loader (`NodeStreamLoader`).
- [`shell_browser_net_proxying`](shell_browser_net_proxying.md) — sibling
  module implementing `webRequest`-style request/response interception
  (`ProxyingURLLoaderFactory`, `ProxyingWebSocket`).
- [`shell_browser_net_context`](shell_browser_net_context.md) — sibling
  module managing `NetworkContextService` / `SystemNetworkContextManager`
  that ultimately own/host the network service these loaders plug into.
- [`Protocol_Registry`](Protocol_Registry.md) — the registry that installs
  `AsarURLLoaderFactory`'s produced remote for the `file:` scheme and
  dispatches other custom-scheme handlers.
- [`shell_browser_context`](shell_browser_context.md) — owns the
  `ProtocolRegistry` per `BrowserContext`/`Session`.
- [`shell_browser_api_session_net_protocol_netlog`](shell_browser_api_session_net_protocol_netlog.md) —
  JS-facing `protocol` API (`electron_api_protocol.h/.cc`) that lets user
  code register custom protocol handlers alongside the built-in asar
  handling described here.
