# Logstash Logging

## Purpose

The logging module is the JVM/JRuby logging boundary for Logstash. It adapts Log4j2 to Logstash’s Ruby runtime, exposes Ruby-compatible logger objects, creates Logstash-specific log events, serializes structured log parameters as JSON, supports runtime log-level and configuration changes, and optionally routes records into per-pipeline appenders.

The module is used by core startup, pipeline execution, plugins, and operational tooling. It is not the source of metrics or HTTP logging endpoints; those consumers are described in [monitoring_http_api.md](monitoring_http_api.md) and [metrics_and_instrumentation.md](metrics_and_instrumentation.md) when those module documents are present.

## Architecture overview

~~~mermaid
flowchart LR
    Ruby[Logstash Ruby code] --> Loggable[Loggable module]
    Loggable --> Logger[LoggerExt]
    Loggable --> Slow[SlowLoggerExt]
    Loggable --> Dep[DeprecationLoggerExt]
    Logger --> Log4j[Log4j2 LoggerContext]
    Slow --> Log4j
    Dep --> Log4j
    Log4j --> Factory[LogstashLogEventFactory]
    Factory --> Event[CustomLogEvent]
    Event --> Serializer[CustomLogEventSerializer]
    Serializer --> JSON[JSON / structured log output]
    Log4j --> Config[LogstashConfigurationFactory]
    Config --> Routing[PipelineRoutingAppender]
    Routing --> Files[Pipeline-specific appenders/files]
    Bootstrap[Early startup warnings] --> Buffer[DeprecationMessage]
    Buffer --> Dep
~~~

At startup, `RubyUtil` registers `Logger`, `SlowLogger`, `DeprecationLogger`, and `Loggable` under the Logstash Ruby namespace. Ruby classes that include `Loggable` receive lazily initialized logger instances whose names are derived from the Ruby class/module name.

Log4j2 then creates `CustomLogEvent` instances through `LogstashLogEventFactory`. When JSON output is selected, `CustomLogEventSerializer` emits the common event metadata and expands `StructuredMessage` parameters into fields. If pipeline separation is enabled, `PipelineRoutingAppender` uses the event context’s `pipeline.id` to create or reuse a child appender.

## Sub-module map

| Area | Responsibility | Documentation |
|---|---|---|
| JRuby logging bridge | Ruby-facing logger classes, logger lookup, level checks, runtime reconfiguration, slow/deprecation logger construction | [logging_jruby_bridge.md](logging_jruby_bridge.md) |
| Event and configuration | Log4j event creation, structured JSON serialization, and conditional configuration customization | [logging_event_and_configuration.md](logging_event_and_configuration.md) |
| Pipeline routing | Dynamic per-pipeline appender creation and event dispatch | [logging_pipeline_routing.md](logging_pipeline_routing.md) |
| Deferred deprecation messages | Temporary storage for warnings emitted before Log4j initialization | [logging_deprecation_buffer.md](logging_deprecation_buffer.md) |

## Core responsibilities

### Ruby/Java interoperability

`LoggableExt` is a JRuby module extension. Including it installs class methods that delegate to Ruby-visible logger objects. Logger names are normalized from Ruby names such as `LogStash::Runner` to lowercase Log4j names such as `logstash.runner`.

`LoggerExt` wraps a Log4j `Logger` in a Ruby object. It provides Ruby-style methods for `debug`, `info`, `warn`, `error`, `fatal`, and `trace`, matching level predicates, access to the active `LoggerContext`, and synchronized configuration changes. The Java side keeps the Log4j context stable during reconfiguration through `LogstashLoggerContextFactory`.

The slow logger uses threshold values to emit only events whose measured duration exceeds a configured level threshold. The deprecation logger provides a separate channel for deprecation notices.

### Structured event output

`LogstashLogEventFactory` replaces Log4j’s default event factory with `CustomLogEvent`. The event is annotated for the custom serializer, preserving Log4j metadata while allowing Logstash-specific message handling.

For ordinary messages, the serializer writes a single `message` field. For `StructuredMessage`, it writes the base message plus key/value parameters. Primitive and wrapper values are written directly. Other values are serialized with the Logstash JSON mapper so Ruby timestamps and other custom values can be handled; failed mappings fall back to `toString()` and are logged at debug level.

A parameter named `message` can collide with the base message field. When the `ls.log.format.json.fix_duplicate_message_fields` system property is enabled, the parameter is renamed to `message_1`.

### Configuration and routing

`LogstashConfigurationFactory` handles `.properties` Log4j configurations. When `ls.pipeline.separate_logs` is `false` (the default), it removes the `pipeline_routing_appender` from the initialized configuration. This prevents pipeline-specific appenders from being active when separate logs are not requested.

`PipelineRoutingAppender` is a deferred Log4j appender. It does not create a child appender until it sees an event with `pipeline.id` in its context data. The first event for a pipeline causes the configured child appender definition to be materialized with that event’s context; later events reuse the cached `AppenderControl`.

~~~mermaid
sequenceDiagram
    participant P as Pipeline/plugin
    participant L as LoggerExt
    participant C as Log4j LoggerContext
    participant F as LogstashLogEventFactory
    participant R as PipelineRoutingAppender
    participant A as Child appender
    P->>L: log(level, message)
    L->>C: publish Log4j call
    C->>F: createEvent(...)
    F-->>C: CustomLogEvent
    C->>R: append(event)
    alt event has pipeline.id
        R->>R: lookup pipeline.id
        alt first event for pipeline
            R->>A: build and start configured child
            R->>R: cache AppenderControl
        end
        R->>A: callAppender(event)
    else no pipeline.id
        R-->>C: skip routing
    end
~~~

### Early deprecation warnings

Some command-line or bootstrap warnings can occur before Log4j has been initialized. `LogStash::DeprecationMessage` is a singleton-like array used as a holding area for those messages. Later initialization code can consume the buffered values through the normal deprecation logging path.

## Operational behavior and edge cases

- Logger instances are cached on the Ruby class/module instance variables, so repeated calls reuse the same named logger.
- `configure_logging` synchronizes changes to avoid concurrent mutation of the Log4j configuration.
- A missing external Log4j configuration path leaves the default console-oriented configuration active and reports the fallback.
- A routing event without `pipeline.id` is intentionally ignored; this avoids creating a file whose name still contains the unresolved context lookup.
- Child appenders are held in a concurrent map and exposed through an unmodifiable view.
- Structured parameter serialization isolates each non-trivial value in a separate Jackson generator. One malformed value therefore does not invalidate the main JSON generator.
- The `fatal?` and `trace?` predicates currently use the underlying debug-enabled check; callers should treat these as compatibility methods rather than independent level probes.

## Integration points

~~~mermaid
graph TD
    Settings[Application settings] --> Runtime[Application bootstrap and settings]
    Runtime --> Logger[Logging bridge]
    Pipeline[Pipeline lifecycle and execution] --> Logger
    Plugins[Plugin API and registry] --> Logger
    Logger --> Filesystem[Log files / console]
    Logger --> API[Monitoring HTTP API]
    Logger --> Monitoring[X-Pack monitoring]
    Logger --> Deprecation[Deprecation reporting]
~~~

- [application_bootstrap_and_settings.md](application_bootstrap_and_settings.md) supplies startup settings and logging configuration inputs.
- [pipeline_lifecycle_and_execution.md](pipeline_lifecycle_and_execution.md) produces pipeline context and lifecycle events that may be logged or routed.
- [plugin_api_and_registry.md](plugin_api_and_registry.md) is a major caller of the Ruby logger bridge.
- [monitoring_http_api.md](monitoring_http_api.md) exposes operational logging controls and status through the HTTP API.
- [xpack_monitoring.md](xpack_monitoring.md) consumes operational data and may emit monitoring-related logs.

These links are intended as cross-module references; the logging-specific implementation details remain in the four sub-module documents above.
