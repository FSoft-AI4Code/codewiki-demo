# builder_opmap_mmdb_geo

## Introduction

The **builder_opmap_mmdb_geo** module implements the map-operation builders that expose MaxMind GeoIP database (MMDB) lookups to the Wazuh Engine's decoder/rule pipeline. It provides two operation builders — `geoip` (city/country enrichment) and `as` (Autonomous System enrichment) — that translate a declarative asset definition (e.g. `map: geoip($source.ip)`) into an executable `MapOp` lambda. At runtime, this lambda resolves an IP address referenced in the event, queries the appropriate MMDB database through the `geo` module's locator abstraction, and merges the resulting ECS-compliant geolocation/ASN fields back into the event as a JSON object.

This module is a thin, focused adapter layer: it contains no MMDB parsing logic itself. Instead, it depends heavily on the [engine_geo](engine_geo.md) module (which owns the MMDB file management, download, and low-level lookup) and on the generic [builder_opmap_generic_map](builder_opmap_generic_map.md) / [builder_argument_helper](builder_argument_helper.md) machinery for argument validation and result wrapping. It is one of several sibling "opmap helper" builders — see [builder_opmap_kvdb](builder_opmap_kvdb.md), [builder_opmap_string_regex_helpers](builder_opmap_string_regex_helpers.md), [builder_opmap_numeric_time_hash_helpers](builder_opmap_numeric_time_hash_helpers.md), and [builder_opmap_field_json_helpers](builder_opmap_field_json_helpers.md) — that are all registered together by the parent [builder_opmap_generic_map](builder_opmap_generic_map.md) component and consumed by [builder_core](Wazuh_Engine_Core_(C++).md)'s registry.

## Purpose & Core Functionality

| Capability | Description |
|---|---|
| **`geoip` builder** (`getMMDBGeoBuilder`) | Resolves an IP reference against the MMDB **City** database and produces ECS-style fields: `city_name`, `continent_code`, `continent_name`, `country_iso_code`, `country_name`, `location.lat`/`lon`, `postal_code`, `timezone`, `region_iso_code`, `region_name`. |
| **`as` builder** (`getMMDBASNBuilder`) | Resolves an IP reference against the MMDB **ASN** database and produces `number` (AS number) and `organization.name` (AS organization) fields. |
| **Argument validation** | Both builders enforce exactly one argument, require it to be a **reference** (not a literal value), and — when schema information is available — validate that the referenced field's declared type is `IP`. |
| **Locator resolution at build-time** | The appropriate `geo::ILocator` (city or ASN) is fetched once from the injected `geo::IManager` when the operation is *built*, not on every event, for efficiency. If the locator/database is unavailable, the builder returns a deterministic "always fail" `MapOp`. |
| **Per-event execution** | The returned `MapOp` reads the IP string from the event, performs the MMDB lookup via the locator, and returns either a populated JSON object (success) or a `base::Error` with a descriptive trace (failure: field missing, empty DB result, etc.). |

## Architecture

```mermaid
graph TB
    subgraph "builder_opmap_mmdb_geo (this module)"
        MMDB[mmdb.cpp]
        GeoBuilder["getMMDBGeoBuilder()"]
        AsnBuilder["getMMDBASNBuilder()"]
        MapGeo["mapGeoToECS()"]
        MapAs["mapAStoECS()"]
        DumpFail["dumpFailTransform()"]
        MMDB --> GeoBuilder
        MMDB --> AsnBuilder
        GeoBuilder --> MapGeo
        AsnBuilder --> MapAs
        GeoBuilder --> DumpFail
        AsnBuilder --> DumpFail
    end

    subgraph "engine_geo"
        IManager["geo::IManager"]
        ILocator["geo::ILocator"]
        Manager["geo::Manager"]
        Locator["geo::Locator"]
        Manager -.implements.-> IManager
        Locator -.implements.-> ILocator
        Manager --> Locator
    end

    subgraph "builder_argument_helper"
        Reference["builders::Reference"]
        AssertRef["assertRef()/assertSize()"]
    end

    subgraph "builder_core_context"
        IBuildCtx["IBuildCtx"]
        RunState["RunState"]
    end

    subgraph "Schemf (Schema Validation)"
        IValidator["schemf::IValidator"]
    end

    GeoBuilder -->|"getLocator(Type::CITY)"| IManager
    AsnBuilder -->|"getLocator(Type::ASN)"| IManager
    IManager --> ILocator
    MapGeo -->|"getString/getDouble"| ILocator
    MapAs -->|"getUint32/getString"| ILocator
    GeoBuilder --> Reference
    AsnBuilder --> Reference
    GeoBuilder --> AssertRef
    AsnBuilder --> AssertRef
    GeoBuilder --> IBuildCtx
    AsnBuilder --> IBuildCtx
    IBuildCtx --> RunState
    IBuildCtx --> IValidator
```

## Component Relationships

```mermaid
classDiagram
    class MapBuilder {
        <<function type>>
        +operator()(opArgs, buildCtx) MapOp
    }
    class MapOp {
        <<function type>>
        +operator()(event) MapResult
    }
    class IBuildCtx {
        <<interface>>
        +validator() IValidator
        +runState() RunState
        +context() Context
    }
    class RunState {
        +bool trace
        +bool sandbox
        +bool check
    }
    class Reference {
        +dotPath() string
        +jsonPath() string
        +isReference() bool
    }
    class IManager {
        <<interface>>
        +getLocator(Type) ILocator
        +listDbs() DbInfo[]
        +addDb(path, type)
    }
    class ILocator {
        <<interface>>
        +getString(ip, path)
        +getUint32(ip, path)
        +getDouble(ip, path)
        +getAsJson(ip, path)
    }
    class Manager {
        +getLocator(Type) ILocator
    }
    class Locator {
        +getString(ip, path)
        +getUint32(ip, path)
        +getDouble(ip, path)
    }

    MapBuilder --> MapOp : creates
    MapBuilder --> IBuildCtx : consumes at build time
    MapBuilder --> Reference : parses argument
    IBuildCtx --> RunState : exposes
    MapBuilder --> IManager : getLocator()
    IManager <|.. Manager
    ILocator <|.. Locator
    Manager --> Locator : creates
    MapOp --> ILocator : queries per event
```

## Data / Execution Flow

The following sequence shows how a `geoip` (or `as`) operation is compiled and later executed for each incoming event.

```mermaid
sequenceDiagram
    participant Policy as "Policy/Asset Definition"
    participant Registry as "builder_core_registry"
    participant GeoBuilder as "getMMDBGeoBuilder (mmdb.cpp)"
    participant GeoMgr as "geo::IManager"
    participant Locator as "geo::ILocator"
    participant MapOp as "Generated MapOp lambda"
    participant Event as "base::Event"

    Note over Policy,Registry: Build-time (once per policy compile)
    Policy->>Registry: "map: geoip($source.ip)"
    Registry->>GeoBuilder: invoke(opArgs=[Reference], buildCtx)
    GeoBuilder->>GeoBuilder: assertSize/assertRef(opArgs)
    GeoBuilder->>GeoBuilder: validate referenced field type == IP (via buildCtx.validator())
    GeoBuilder->>GeoMgr: getLocator(Type::CITY)
    alt Locator unavailable
        GeoMgr-->>GeoBuilder: Error
        GeoBuilder-->>Registry: dumpFailTransform (always-fail MapOp)
    else Locator available
        GeoMgr-->>GeoBuilder: shared_ptr<ILocator>
        GeoBuilder-->>Registry: MapOp closure (captures locator, jsonPath, traces)
    end

    Note over MapOp,Event: Run-time (per event)
    Event->>MapOp: invoke(event)
    MapOp->>Event: getString(srcRef)
    alt IP field missing
        MapOp-->>Event: Failure (notFoundTrace)
    else IP field present
        MapOp->>Locator: getString/getDouble(ip, "city.names.en", ...)
        Locator-->>MapOp: value or error (per field)
        MapOp->>MapOp: mapGeoToECS() assembles JSON object
        alt No fields resolved
            MapOp-->>Event: Failure (emptyDataTrace)
        else Fields resolved
            MapOp-->>Event: Success (JSON object merged into event)
        end
    end
```

## Build-Time Argument Validation

```mermaid
flowchart TD
    Start["Builder invoked with opArgs, buildCtx"] --> SizeCheck{"assertSize(opArgs, 1, MAX)"}
    SizeCheck -- fail --> ThrowSize["throw runtime_error"]
    SizeCheck -- ok --> RefCheck{"assertRef(opArgs, 0)"}
    RefCheck -- fail --> ThrowRef["throw runtime_error"]
    RefCheck -- ok --> TypeCheck{"validator.hasField(dotPath) &&\ntype != schemf::Type::IP ?"}
    TypeCheck -- yes --> ThrowType["throw runtime_error:\n'reference is not an IP'"]
    TypeCheck -- no/unknown --> GetLocator["geoManager->getLocator(Type)"]
    GetLocator --> LocatorOk{"isError(resDB)?"}
    LocatorOk -- yes --> FailOp["Return dumpFailTransform\n(always-fail MapOp)"]
    LocatorOk -- no --> BuildOp["Capture locator + traces\nReturn working MapOp"]
```

## Core Components

### `getMMDBGeoBuilder(geoManager)`
Factory returning a `MapBuilder`. When invoked by the registry with the parsed operator arguments and the current `IBuildCtx`:
1. Validates argument count/type using [builder_argument_helper](builder_argument_helper.md) utilities (`assertSize`, `assertRef`).
2. Optionally validates, via `buildCtx->validator()` (see [Schemf (Schema Validation)](Schemf_(Schema_Validation).md)), that the referenced field is typed as `IP`.
3. Requests a `geo::ILocator` for `geo::Type::CITY` from the injected `geo::IManager` (see [engine_geo](engine_geo.md)).
4. Returns a `MapOp` closure that, per event, reads the IP, calls `mapGeoToECS`, and returns success/failure using the `RETURN_SUCCESS`/`RETURN_FAILURE` macros tied to the build's `RunState` (trace/sandbox/check flags).

### `getMMDBASNBuilder(geoManager)`
Structurally identical to `getMMDBGeoBuilder`, but requests `geo::Type::ASN` and delegates per-event enrichment to `mapAStoECS`.

### `mapGeoToECS(ip, locator)` (internal)
Performs a series of best-effort `locator->getString`/`getDouble` calls against MMDB City-database paths (`city.names.en`, `continent.code`, `country.iso_code`, `location.latitude`, etc.) and assembles them into an ECS-shaped `json::Json` object. Fields that are not present in the DB response are simply omitted rather than causing failure.

### `mapAStoECS(ip, locator)` (internal)
Performs `locator->getUint32("autonomous_system_number")` and `locator->getString("autonomous_system_organization")` lookups and assembles the ASN JSON object (`number`, `organization.name`).

### `dumpFailTransform(trace, runstate)` (internal)
Utility that produces a `MapOp` which unconditionally fails with a fixed trace message — used when the required MMDB database/locator could not be obtained at build time (e.g., database not configured/loaded).

## Dependencies

```mermaid
graph LR
    thisModule["builder_opmap_mmdb_geo"]
    argHelper["builder_argument_helper"]
    coreCtx["builder_core_context"]
    coreRegistry["builder_core_registry"]
    geoModule["engine_geo"]
    schemfModule["Schemf (Schema Validation)"]
    baseModule["engine_base_core_types"]
    optransform["builder_optransform"]
    opfilter["builder_opfilter"]

    thisModule --> argHelper
    thisModule --> coreCtx
    thisModule --> geoModule
    thisModule --> schemfModule
    thisModule --> baseModule
    coreRegistry --> thisModule
    thisModule -.sibling.-> opfilter
    thisModule -.sibling.-> optransform
```

- **[engine_geo](engine_geo.md)** — Provides `geo::IManager`/`geo::ILocator` interfaces and the `Manager`/`Locator` implementations that actually open and query the MMDB files (via libmaxminddb). This module is the *only* place that performs real MMDB I/O; `builder_opmap_mmdb_geo` merely orchestrates calls to it.
- **[builder_core_context](Wazuh_Engine_Core_(C++).md)** (`IBuildCtx`, `RunState`) — Supplies build-time context: the schema validator, the run mode flags (trace/sandbox/check) that determine how success/failure results are reported, and the operator name used in trace messages.
- **[builder_argument_helper](Wazuh_Engine_Core_(C++).md)** (`Reference`, `Value`, `assertRef`, `assertSize`) — Generic argument-shape validation shared by all opmap/opfilter builders.
- **[Schemf (Schema Validation)](Schemf_(Schema_Validation).md)** — Used to check, when schema metadata exists, that the referenced field is declared as an `IP` type, preventing accidental misuse of the `geoip`/`as` operators on non-IP fields.
- **Sibling opmap builders** — [builder_opmap_kvdb](builder_opmap_kvdb.md), [builder_opmap_generic_map](builder_opmap_generic_map.md), [builder_opmap_string_regex_helpers](builder_opmap_string_regex_helpers.md), [builder_opmap_numeric_time_hash_helpers](builder_opmap_numeric_time_hash_helpers.md), [builder_opmap_field_json_helpers](builder_opmap_field_json_helpers.md) are registered alongside this module by [builder_core_registry](Wazuh_Engine_Core_(C++).md)'s `registerOpBuilders` function, all following the same `MapBuilder` factory pattern.
- **[builder_policy](Wazuh_Engine_Core_(C++).md)** — Consumes the built `MapOp` operations when assembling assets (decoders/rules) into the executable policy graph.

## Where This Fits in the System

```mermaid
graph TB
    subgraph "Wazuh_Engine_Core_(C++)"
        subgraph "engine_builder"
            ThisMod["builder_opmap_mmdb_geo"]
            OtherOpmap["other opmap builders"]
            Registry["builder_core_registry"]
            Policy["builder_policy"]
        end
        Geo["engine_geo"]
        Schemf["Schemf"]
        Base["engine_base"]
        ApiGeo["engine_api_resource_handlers\n(api/geo handlers)"]
    end
    EngineGeoCLI["engine_geo CLI tool\n(engine-suite)"]

    Registry --> ThisMod
    Registry --> OtherOpmap
    Policy --> Registry
    ThisMod --> Geo
    ThisMod --> Schemf
    ThisMod --> Base
    ApiGeo --> Geo
    EngineGeoCLI --> ApiGeo
```

The `geoip`/`as` operators built here are ultimately used inside decoder and rule assets processed by the [Router](Router.md) and [engine_bk](engine_bk_rx.md) execution backends when events flow through the engine's pipeline. Administrators manage the underlying MMDB databases out-of-band via the `engine_geo` CLI tool and the `api/geo` HTTP handlers (see [engine_api_resource_handlers](engine_api.md)), which both talk to the same `geo::IManager` this module depends on.

## Key Design Notes

- **Fail-fast at build time, degrade gracefully at runtime**: If a referenced field's schema type is known and is not `IP`, the builder throws at *build* time (compile-time policy error). If the underlying MMDB database is simply not loaded, the builder does not throw — it returns an operation that always fails per-event, allowing the policy to still compile (useful for optional GeoIP enrichment in an environment where the DB hasn't been provisioned yet).
- **Locator resolved once, reused per event**: The `geo::ILocator` shared pointer is captured by value in the returned lambda's closure, avoiding a manager lookup for every event processed.
- **Partial results are still successes**: `mapGeoToECS`/`mapAStoECS` do not fail if only some sub-fields are resolvable (e.g., missing postal code); the operation only fails if the resulting object is completely empty.
- **ECS alignment**: Field names mirror Elastic Common Schema conventions (`city_name`, `country_iso_code`, `location.lat/lon`, `organization.name`) to ensure indexed events are directly compatible with downstream analytics ([engine_indexerconnector](Wazuh_Engine_Core_(C++).md)).
