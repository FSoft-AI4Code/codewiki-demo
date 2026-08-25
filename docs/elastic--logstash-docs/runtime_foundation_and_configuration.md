# Runtime Foundation and Configuration

The `runtime_foundation_and_configuration` module provides Logstash’s process-level foundation. It initializes and validates settings, selects and loads pipeline configuration, manages secrets, supports centralized X-Pack configuration, and supplies shared Ruby/Java data and I/O utilities. Together, these components prepare safe, validated inputs for pipeline compilation and execution.

## Architecture

```mermaid
flowchart TB
    OP[Operator / CLI / logstash.yml] --> BOOT[Application bootstrap and settings]
    BOOT --> SOURCES[Configuration sources and loading]
    BOOT --> SECRET[Secret store]
    BOOT --> XPACK[X-Pack centralized management]
    SOURCES --> EXPAND[Secret and variable expansion]
    SECRET --> EXPAND
    EXPAND --> CONFIG[Pipeline configuration]
    XPACK --> CONFIG
    CONFIG --> COMPILER[Pipeline parser and compiler]
    COMPILER --> RUNTIME[Pipeline lifecycle and execution]
    UTIL[Core data and I/O utilities] -. supports .-> SOURCES
    UTIL -. supports .-> RUNTIME
```

```mermaid
sequenceDiagram
    participant User
    participant Runner
    participant Settings
    participant Sources
    participant Secrets
    participant Compiler
    participant Runtime

    User->>Runner: Start Logstash
    Runner->>Settings: Load YAML and CLI settings
    Settings-->>Runner: Validated typed settings
    Runner->>Sources: Select local, remote, or managed sources
    Sources->>Secrets: Expand secret references
    Secrets-->>Sources: Resolved configuration
    Sources->>Compiler: Provide pipeline configuration
    Compiler-->>Runtime: Compiled pipeline
    Runtime-->>User: Running service or startup diagnostic
```

## Core components

- [Application bootstrap and settings](application_bootstrap_and_settings.md) — runner orchestration, typed settings, validation, resource checks, locking, and startup lifecycle.
- [Configuration sources and loading](configuration_sources_and_loading.md) — inline, file, glob, HTTP(S), and `pipelines.yml` configuration loading.
- [Core data and I/O utilities](core_data_and_io_utilities.md) — tokenization, charset normalization, hashing, plugin-version handling, and JRuby interoperability.
- [Secret store](secret_store.md) — keystore CLI, PKCS#12-backed persistence, secure data handling, and configuration secret expansion.
- [X-Pack centralized pipeline management](xpack_centralized_pipeline_management.md) — Elasticsearch-backed pipeline selection, validation, polling, and reload integration.

These components hand off to the [pipeline configuration parser](pipeline_configuration_parser.md), [pipeline IR and compilation](pipeline_ir_and_compilation.md), and [pipeline lifecycle and execution](pipeline_lifecycle_and_execution.md). Operational visibility is provided by the [monitoring HTTP API](monitoring_http_api.md), [logging](logging.md), and related observability components.