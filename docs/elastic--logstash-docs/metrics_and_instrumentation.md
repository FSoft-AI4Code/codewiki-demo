# Metrics and instrumentation

The `metrics_and_instrumentation` module is Logstash’s low-level observability layer. It provides a thread-safe hierarchical registry for metrics, a JRuby-facing API for counters, gauges, and timers, Java metric value abstractions, shared reporting keys, snapshots, and no-op implementations for disabled or unavailable collection. Runtime pipeline reporting builds on these primitives and is documented in [pipeline_lifecycle_and_execution_reporting_runtime_reporting.md](pipeline_lifecycle_and_execution_reporting_runtime_reporting.md).

## Architecture overview

```mermaid
flowchart TB
    PRODUCERS[Pipeline, plugin, and runtime instrumentation]
    BRIDGE[JRuby metric API\nMetricExt / namespaced metrics]
    COLLECTOR[Ruby collector / registration path]
    STORE[MetricStore\nthread-safe hierarchy + flat index]
    VALUES[Java metric values\ncounters, gauges, timers, uptime]
    SNAP[Snapshot\nstore + created_at]
    POLLERS[Periodic pollers and monitors]
    REPORTS[Pipeline/node stats and monitoring outputs]
    NULL[NullMetric\nno-op fallback]
    KEYS[MetricKeys\nshared field vocabulary]

    PRODUCERS --> BRIDGE
    BRIDGE --> COLLECTOR
    COLLECTOR --> STORE
    STORE --> VALUES
    STORE --> SNAP
    POLLERS --> BRIDGE
    SNAP --> REPORTS
    VALUES --> REPORTS
    KEYS --> REPORTS
    BRIDGE -. collection disabled .-> NULL
    NULL --> PRODUCERS
```

The central design is a separation of concerns: `MetricStore` addresses and exposes metrics, while metric implementations own value semantics. JRuby adapters preserve the Ruby instrumentation API and delegate storage through a collector. Reporters consume plain values or snapshots rather than manipulating the registry’s internal maps.

## Sub-modules

| Sub-module | Scope | Documentation |
| --- | --- | --- |
| Metric store and hierarchical lookup | Concurrent registration, dual indexes, path queries, extraction, enumeration, and pruning | [metric_store_and_hierarchical_lookup.md](metric_store_and_hierarchical_lookup.md) |
| Metric API and JRuby bridge | JRuby operations, validation, namespaced views, Java metric contracts, gauge behavior, timer conversion, and shared keys | [metric_api_and_jruby_bridge.md](metric_api_and_jruby_bridge.md) |
| Null metrics and snapshots | No-op metric behavior and timestamped metric-store snapshots | [null_metrics_and_snapshots.md](null_metrics_and_snapshots.md) |

## End-to-end data flow

```mermaid
sequenceDiagram
    participant I as Instrumentation caller
    participant M as MetricExt
    participant C as Collector
    participant S as MetricStore
    participant V as Metric value
    participant R as Reporter/API

    I->>M: increment / gauge / time
    M->>M: validate key and normalize namespace
    M->>C: push or get(namespace, key, type, operation)
    C->>S: fetch_or_store(path, key, default metric)
    S-->>C: existing or newly-created metric
    C->>V: update or measure value
    V-->>R: current value
    S-->>R: hierarchical query or snapshot source
```

For timed operations, `MetricExt#time` either measures a supplied Ruby block immediately or returns `TimedExecution`, whose `stop` method computes elapsed time using `System.nanoTime` and reports whole milliseconds. The no-op path preserves the same calling shape and returns zero or `nil` without modifying the store.

## Metric addressing and output shape

Metrics are addressed by a namespace path plus a leaf key, for example:

```text
pipelines/<pipeline-name>/events/in
pipelines/<pipeline-name>/events/out
flow/input_throughput
```

The store keeps a nested tree for recursive API responses and a flat path index for direct access. Query paths may select multiple siblings with comma-separated names, and API-facing results are converted from `Concurrent::Map` instances into ordinary Ruby hashes. The canonical field names used by reporters—pipeline, plugin, queue, DLQ, flow, and timing fields—are centralized in `MetricKeys`.

## Concurrency and consistency

`MetricStore` uses `Concurrent::Map` for both its structured store and flat lookup. A mutex protects operations that must update or inspect the two representations consistently, especially first insertion, hierarchical reads, and pruning. `compute_if_absent` ensures that concurrent producers do not replace an already-created metric. Individual metric implementations may add their own visibility or atomicity guarantees; the store does not aggregate or mutate metric values itself.

## Integration boundaries

```mermaid
flowchart LR
    METRICS[metrics_and_instrumentation]
    RUNTIME[pipeline lifecycle and runtime reporting]
    HTTP[monitoring HTTP API]
    LOGGING[logging]
    XPACK[X-Pack monitoring]

    RUNTIME -->|polls and updates metrics| METRICS
    HTTP -->|queries snapshots/stats| METRICS
    XPACK -->|exports monitoring events| METRICS
    LOGGING -. operational diagnostics .-> METRICS
```

The module should remain focused on instrumentation primitives. Polling schedules, HTTP routing, monitoring event schemas, and logging configuration belong to their respective neighboring modules; the available runtime-reporting details are linked above rather than duplicated here.

## Typical lifecycle

```mermaid
stateDiagram-v2
    [*] --> Instrumented
    Instrumented --> Registered: first metric path used
    Registered --> Updated: counter/gauge/timer operation
    Updated --> Registered: metric remains addressable
    Registered --> Snapshotted: reporter captures store
    Snapshotted --> Reported: API or monitoring consumer reads values
    Instrumented --> NoOp: collection disabled
    NoOp --> [*]: safe nil/zero behavior
    Reported --> [*]
```

## Maintenance notes

- Keep the flat lookup and nested tree synchronized when changing registration or pruning behavior.
- Preserve JRuby-visible validation and method signatures because plugins and runtime code call these adapters dynamically.
- Add new reporting fields to `MetricKeys` rather than scattering symbol literals across producers and consumers.
- Treat no-op metrics as API-compatible implementations: they should remain safe to call while retaining input validation.
