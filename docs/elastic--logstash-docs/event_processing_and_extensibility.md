# Event Processing and Extensibility

## Purpose

The `event_processing_and_extensibility` module defines how Logstash represents and processes events, supports Ruby and Java plugin implementations, discovers and constructs plugins, and manages extensible runtime resources such as GeoIP databases.

It spans:

- Event storage, field access, serialization, and JRuby interoperability.
- Plugin contracts, lifecycle management, discovery, validation, and registration.
- Core Java input, filter, and output plugins.
- Plugin installation and packaging through `bin/logstash-plugin`.
- X-Pack GeoIP database acquisition and lifecycle management.

## Architecture

```mermaid
flowchart LR
    Config[Pipeline configuration] --> Compiler[Pipeline compiler / IR]
    Compiler --> Factory[Plugin factory]
    Factory --> Registry[Plugin registry]
    Registry --> Plugins[Ruby and Java plugins]

    Plugins --> Event[Event model]
    Event --> Bridge[JRuby / Java interop]
    Plugins --> Runtime[Pipeline execution]

    Manager[Plugin manager] --> Registry
    GeoIPMgr[GeoIP database manager] --> GeoIP[GeoIP filter]
    GeoIP --> Event
    Runtime --> Observability[Metrics and reporting]
```

The event model is the shared data contract. Plugin APIs and registries resolve implementations and create runtime wrappers. Core built-ins provide reference Java implementations, while the plugin manager supplies external plugin packages. The GeoIP manager supplies managed database resources to the GeoIP filter.

## Event and plugin flow

```mermaid
sequenceDiagram
    participant C as Pipeline compiler
    participant R as Plugin registry
    participant F as Plugin factory
    participant P as Input/filter/output
    participant E as Event model
    participant G as GeoIP manager

    C->>R: Resolve plugin type and name
    R-->>F: Plugin implementation
    F->>P: Construct and configure plugin
    P->>E: Read, mutate, or emit events
    P->>G: Request managed GeoIP database path
    G-->>P: Database metadata or update
    P-->>C: Execute within compiled pipeline
```

## Core components

- [Event Model and JRuby Interoperability](/home/anhnh/CodeWiki-journal/results/generation/logstash/event_model_and_jruby_interop.md)  
  Defines the internal event representation, field access, Java/Ruby conversion, timestamps, serialization, interpolation, cloning, and merging.

- [Plugin API and Registry](/home/anhnh/CodeWiki-journal/results/generation/logstash/plugin_api_and_registry.md)  
  Defines plugin contracts, lifecycle APIs, configuration validation, discovery, registries, Java factories, and JRuby delegators.

- [Core Built-in Plugins](/home/anhnh/CodeWiki-journal/results/generation/logstash/core_builtin_plugins.md)  
  Documents the built-in `java_stdin`, `java_uuid`, `java_stdout`, and `sink` plugins.

- [Plugin Manager](/home/anhnh/CodeWiki-journal/results/generation/logstash/plugin_manager.md)  
  Documents plugin listing, installation, updates, removal, generation, packaging, Bundler integration, and offline workflows.

- [X-Pack GeoIP Database Management](/home/anhnh/CodeWiki-journal/results/generation/logstash/xpack_geoip_database_management.md)  
  Documents managed GeoLite2 database downloads, validation, storage, expiration, subscriptions, and GeoIP filter integration.