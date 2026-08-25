# Gin Converters: Network

## Introduction

The **Gin_Converters_network** module provides the type-marshalling glue that lets Electron's C++ networking primitives cross the V8/JavaScript boundary. It is a thin, header-only layer built on top of Chromium's [`gin::Converter`](https://source.chromium.org/chromium/chromium/src/+/main:gin/converter.h) template mechanism, specializing it for the network-related types used throughout Electron's `net` module (`session.cookies`, `net.request`, `webRequest`, certificate handling, host resolution, etc.).

This module contains a single translation unit — `shell/common/gin_converters/net_converter.h` — but it is exercised from many other subsystems whenever a native network object (a certificate, an HTTP header, a resource request, etc.) needs to be exposed to or constructed from JavaScript.

It is one of several sibling "Gin Converter" modules that partition converter specializations by domain:

| Sibling module | Domain |
|---|---|
| [Gin_Converters_graphics.md](Gin_Converters_graphics.md) | Accelerators, `gfx::Point/Rect/Size`, images |
| [Gin_Converters_web_content.md](Gin_Converters_web_content.md) | Blink input events, context menus, frames, media streams |
| [Gin_Converters_misc.md](Gin_Converters_misc.md) | Extensions, login item settings, time |
| **Gin_Converters_network (this module)** | `net::`/`network::` types: certificates, headers, requests, DNS |

All of these sit under the parent [Common_Native_Gin_Infrastructure.md](Common_Native_Gin_Infrastructure.md) umbrella, alongside [Gin_Helper.md](Gin_Helper.md) (which supplies the underlying `gin_helper::Promise`, `Arguments`, `Handle`, and object-template machinery that many of these converters and their call sites depend on).

## Purpose & Scope

Electron's JavaScript API frequently needs to pass complex native network objects into and out of V8, for example:

- Returning certificate chain details to `app.on('certificate-error', ...)` or `net.request` TLS callbacks.
- Serializing/deserializing HTTP request/response headers for `webRequest` and `protocol` handlers.
- Converting `network::ResourceRequest`/`ResourceRequestBody` (including upload bodies) for custom protocol handlers and `net.ClientRequest`.
- Supplying parameters for `net.resolve()` (DNS resolution options and results).
- Bridging Electron's internal `VerifyRequestParams` (used by the custom certificate verifier) into JS-visible objects.

Rather than writing manual V8 object construction/parsing code at every call site, Electron specializes `gin::Converter<T>` for each of these types once, in this module, so any code that uses `gin::ConvertToV8()` / `gin::ConvertFromV8()` (or the higher-level helpers in [Gin_Helper.md](Gin_Helper.md)) gets automatic, consistent conversion.

## Architecture

### Position in the Gin Converter Family

```mermaid
graph TD
    subgraph Common_Native_Gin_Infrastructure
        GH[Gin_Helper<br/>Arguments, Promise, Handle,<br/>ObjectTemplateBuilder]
        GCG[Gin_Converters_graphics]
        GCW[Gin_Converters_web_content]
        GCN["Gin_Converters_network<br/>(this module)"]
        GCM[Gin_Converters_misc]
    end

    GCN -->|uses gin::Converter base template| GinCore["gin::Converter&lt;T&gt;<br/>(Chromium gin library)"]
    GCN -->|depends on| GH
    GCG -.sibling.- GCN
    GCW -.sibling.- GCN
    GCM -.sibling.- GCN
```

### Converter Coverage Map

`net_converter.h` declares `gin::Converter<T>` specializations for the following native types, each mapping to (or from) a plain JS object/array/string:

```mermaid
graph LR
    subgraph "net:: (Chromium network stack)"
        AuthChallengeInfo
        X509Certificate["scoped_refptr&lt;X509Certificate&gt;"]
        CertPrincipal
        HttpResponseHeaders["HttpResponseHeaders*"]
        HttpRequestHeaders
        HttpVersion
        RedirectInfo
        IPEndPoint
        DnsQueryType
        HostResolverSource
    end

    subgraph "network:: (services/network mojom + structs)"
        ResourceRequest
        ResourceRequestBody
        ResourceRequestBodyRef["scoped_refptr&lt;ResourceRequestBody&gt;"]
        ResolveHostParamsCacheUsage["ResolveHostParameters::CacheUsage"]
        SecureDnsPolicy
        ResolveHostParametersPtr
    end

    subgraph "electron:: (Electron-specific)"
        VerifyRequestParams
    end

    NC[net_converter.h]
    NC --> AuthChallengeInfo
    NC --> X509Certificate
    NC --> CertPrincipal
    NC --> HttpResponseHeaders
    NC --> HttpRequestHeaders
    NC --> HttpVersion
    NC --> RedirectInfo
    NC --> IPEndPoint
    NC --> DnsQueryType
    NC --> HostResolverSource
    NC --> ResourceRequest
    NC --> ResourceRequestBody
    NC --> ResourceRequestBodyRef
    NC --> ResolveHostParamsCacheUsage
    NC --> SecureDnsPolicy
    NC --> ResolveHostParametersPtr
    NC --> VerifyRequestParams
```

Note some converters are **bidirectional** (`ToV8` and `FromV8`, e.g. `X509Certificate`, `HttpResponseHeaders*`, `HttpRequestHeaders`, `ResourceRequestBody` ref, DNS-related enums/structs), while others are **one-directional**:
- `ToV8`-only: `AuthChallengeInfo`, `CertPrincipal`, `ResourceRequestBody` (value), `ResourceRequest`, `VerifyRequestParams`, `HttpVersion`, `RedirectInfo`, `IPEndPoint` — these represent data flowing *out* of native code into JS callbacks/events.
- `FromV8`-only: `DnsQueryType`, `HostResolverSource`, `ResolveHostParameters::CacheUsage`, `SecureDnsPolicy`, `ResolveHostParametersPtr` — these represent *options* parsed from JS-supplied dictionaries (e.g., `net.resolve()` options).

A generic helper template, `Converter<std::vector<std::pair<K, V>>>`, is also provided in this header to convert a plain JS object into a vector of key/value pairs — used for things like HTTP header maps where ordering and duplicate keys must be preserved (unlike a JS `Map`/object with unique keys).

## Key Components

### `net::AuthChallengeInfo` → JS
Produces the object passed to the `login` event / `app.on('login', ...)` and similar HTTP auth challenge callbacks (realm, scheme, host, port, is-proxy, etc.).

### `net::X509Certificate` (bidirectional)
Used for certificate objects surfaced in `certificate-error`, `select-client-certificate`, and TLS-related APIs. `FromV8` allows JS code (e.g., in `net.request`) to hand back a certificate reference selected by the user.

### `net::CertPrincipal`
Represents the subject/issuer fields of a certificate (common name, org, org unit, country, etc.) — nested inside the `X509Certificate` conversion.

### `net::HttpResponseHeaders*` / `net::HttpRequestHeaders` (bidirectional)
Converts Chromium's raw header containers to/from a JS object mapping header name → value(s). Used extensively by `webRequest`, `protocol`, and `net.ClientRequest`/`IncomingMessage`.

### `network::ResourceRequestBody` / `scoped_refptr<ResourceRequestBody>`
Represents upload data (raw bytes, files, blobs) attached to a request. The `scoped_refptr` variant is bidirectional, enabling custom protocol handlers to both read and construct request bodies.

### `network::ResourceRequest`
Serializes a full network request descriptor (URL, method, headers, referrer, etc.) to JS — used when intercepting/inspecting requests via `protocol.handle`/`webRequest`.

### `electron::VerifyRequestParams`
Bridges Electron's custom certificate-verification hook (see [`CertVerifierClient`](Networking_Layer.md)) to the JS-level `setCertificateVerifyProc` callback, exposing hostname, default result/error code, and the certificate chain.

### `net::HttpVersion`, `net::RedirectInfo`, `net::IPEndPoint`
Small supporting converters used when reporting response metadata (HTTP version string, redirect chain info, and resolved socket addresses) back to JS, notably from `net.request`'s response/redirect events and DNS resolution results.

### DNS / Host Resolution converters
`net::DnsQueryType`, `net::HostResolverSource`, `network::mojom::ResolveHostParameters::CacheUsage`, `network::mojom::SecureDnsPolicy`, and `network::mojom::ResolveHostParametersPtr` are all `FromV8`-only, parsing the options dictionary passed to `net.resolve()` / `ResolveHostFunction` (see [Networking_Layer.md](Networking_Layer.md)) into Chromium's mojom resolution-parameter types.

## Dependencies

```mermaid
graph TD
    NC[shell/common/gin_converters/net_converter.h]

    NC --> GinConverter["gin::Converter&lt;T&gt; base template<br/>(third_party/gin)"]
    NC --> HostResolverMojom["services/network/public/mojom/host_resolver.mojom(.h)"]
    NC --> CertVerifierClient["shell/browser/net/cert_verifier_client.h<br/>(VerifyRequestParams, CertVerifierClient)"]

    CertVerifierClient -.belongs to.-> NetLayer[Networking_Layer.md]

    Consumers1[shell_browser_api_session_net_web_request<br/>WebRequest] --> NC
    Consumers2[shell_browser_api_session_net_protocol_netlog<br/>Protocol / NetLog] --> NC
    Consumers3[Common_API<br/>electron_api_url_loader.h] --> NC
    Consumers4[shell_browser_net_resolution<br/>ResolveHostFunction] --> NC
    Consumers5[shell_browser_net_context<br/>CertVerifierClient usage] --> NC

    style NC fill:#f9f,stroke:#333,stroke-width:2px
```

- **Upstream dependency**: [`shell/browser/net/cert_verifier_client.h`](Networking_Layer.md) — supplies the `VerifyRequestParams` struct and the `CertVerifierClient` class that this module's converter serializes.
- **Chromium base**: `gin/converter.h` and `services/network/public/mojom/host_resolver.mojom(-forward).h` provide the base template and mojom enum/struct definitions being specialized.
- **Sibling infrastructure**: [Gin_Helper.md](Gin_Helper.md) provides `gin_helper::Dictionary`, `gin_helper::Promise`, and `gin::Wrappable`-based handle types that higher-level API bindings use *together with* these converters (e.g., building a JS options dictionary, then relying on `net_converter.h` to translate individual fields).

## Consumers (Downstream Usage)

The converters declared here are `#include`d wherever native network types must cross into V8. Major consumers include:

```mermaid
graph LR
    NC[Gin_Converters_network]

    NC --> WebRequest["electron_api_web_request.h/.cc<br/>(WebRequest — Browser_Context_&_Session_Management)"]
    NC --> Protocol["electron_api_protocol.h/.cc<br/>(Protocol registration/custom schemes)"]
    NC --> NetLog["electron_api_net_log.h<br/>(NetLog export)"]
    NC --> URLLoader["electron_api_url_loader.h<br/>(net.request / SimpleURLLoaderWrapper)"]
    NC --> ResolveHost["resolve_host_function.h<br/>(net.resolve DNS API)"]
    NC --> ElectronURLLoaderFactory["electron_url_loader_factory.h<br/>(custom protocol responses)"]
    NC --> BrowserClient["electron_browser_client.h<br/>(cert errors, client cert selection)"]
```

For details on these consuming components, see:
- [Browser_Context_&_Session_Management.md](Browser_Context_&_Session_Management.md) — `WebRequest`, `Protocol`, `NetLog`, `Session`
- [Networking_Layer.md](Networking_Layer.md) — `CertVerifierClient`, `ElectronURLLoaderFactory`, `ResolveHostFunction`, `ProxyingURLLoaderFactory`
- [Common_API](Common_Native_Gin_Infrastructure.md) — `electron_api_url_loader.h` (`net.request` implementation)
- [Browser_Process_Core_&_Lifecycle.md](Browser_Process_Core_&_Lifecycle.md) — `ElectronBrowserClient` certificate-error / client-certificate flows

## Data Flow Examples

### Certificate verification callback (native → JS → native)

```mermaid
sequenceDiagram
    participant Net as Chromium net stack
    participant CVC as CertVerifierClient
    participant Conv as net_converter.h<br/>(VerifyRequestParams / X509Certificate)
    participant JS as JS: session.setCertificateVerifyProc(cb)
    participant Cb as User callback

    Net->>CVC: Verify(default_error, cert, hostname, ...)
    CVC->>Conv: ConvertToV8(VerifyRequestParams)
    Conv->>Conv: Converter<X509Certificate>::ToV8 (nested)
    Conv->>JS: v8::Object {hostname, certificate, ...}
    JS->>Cb: invoke(request)
    Cb->>CVC: verificationResult (int)
    CVC->>Net: callback(result)
```

### Request headers round-trip (webRequest / protocol interception)

```mermaid
sequenceDiagram
    participant Native as ProxyingURLLoaderFactory
    participant Conv as net_converter.h<br/>(HttpRequestHeaders / ResourceRequest)
    participant JS as JS: webRequest.onBeforeSendHeaders
    participant User as User handler

    Native->>Conv: ConvertToV8(ResourceRequest)
    Conv->>JS: {url, method, headers: {...}, ...}
    JS->>User: invoke(details)
    User->>JS: callback({requestHeaders: {...}})
    JS->>Conv: ConvertFromV8(HttpRequestHeaders)
    Conv->>Native: modified net::HttpRequestHeaders
```

### DNS resolution options parsing (`net.resolve()`)

```mermaid
sequenceDiagram
    participant JS as JS: net.resolve(host, options)
    participant Func as ResolveHostFunction
    participant Conv as net_converter.h<br/>(ResolveHostParametersPtr, DnsQueryType, ...)
    participant Resolver as network::mojom::HostResolver

    JS->>Func: call(host, options)
    Func->>Conv: ConvertFromV8(options) 
    Conv-->>Func: ResolveHostParametersPtr
    Func->>Resolver: ResolveHost(host, params)
    Resolver-->>Func: AddressList
    Func->>Conv: ConvertToV8(IPEndPoint...)
    Conv-->>JS: resolved addresses
```

## Design Notes

- **Header-only, declarative style**: Like other Gin converter modules, this file only *declares* the `Converter<T>` specializations; implementations live in the corresponding `.cc` file (`net_converter.cc`, not part of this module's core components but implied by the `ToV8`/`FromV8` static methods declared here).
- **No direct V8 object lifetime management**: These converters do not need to manage V8 handles beyond the immediate call — longer-lived JS-exposed network objects (e.g., `Cookies`, `NetLog`, `ProtocolRegistry`) are implemented as `gin::Wrappable`/`gin_helper::TrackableObject` subclasses documented in [Browser_Context_&_Session_Management.md](Browser_Context_&_Session_Management.md), which *use* these converters internally.
- **Consistency with mojom types**: By specializing converters directly on `network::mojom::*` enums (`SecureDnsPolicy`, `CacheUsage`, `ResolveHostParametersPtr`), the module keeps DNS option parsing in sync with the underlying Network Service IPC contract, reducing drift when Chromium updates.
- **Generic pair-vector converter**: The templated `Converter<std::vector<std::pair<K, V>>>` is a general-purpose utility (not net-specific in principle) but lives here because its first use case is preserving multi-valued/ordered HTTP headers; other modules needing similar semantics may reuse it.
