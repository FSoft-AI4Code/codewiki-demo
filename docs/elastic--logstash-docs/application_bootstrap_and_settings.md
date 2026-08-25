# Application bootstrap and settings

The `application_bootstrap_and_settings` module is Logstash’s process-level foundation. It turns command-line and YAML inputs into validated typed settings, performs safety and resource preflight checks, resolves pipeline configuration, and starts the agent under exclusive ownership of the data path. It spans Ruby orchestration and Java-backed primitives because startup configuration is shared by both runtimes.

## Architecture overview

```mermaid
flowchart TB
    USER[CLI / logstash.yml] --> RUN[Runner]
    RUN --> SETTINGS[Settings registry]
    SETTINGS --> BRIDGE[Ruby–Java setting bridge]
    RUN --> CHECKS[Bootstrap and resource validators]
    RUN --> SOURCES[Configuration sources]
    SOURCES --> COMPILER[Pipeline parser/compiler]
    RUN --> LOCK[FileLockFactory]
    LOCK --> AGENT[Pipeline agent and lifecycle]
    SETTINGS --> API[Operational/API settings]
    RUN --> LOG[Logging and deprecation reporting]
```

## Submodules

- [Bootstrap, settings, and startup validation](application_bootstrap_and_settings_runtime.md) covers `Runner`, the Ruby settings registry and setting classes, bootstrap checks, persistent-queue validation, and pipeline resource estimation.
- [Bootstrap platform utilities](application_bootstrap_and_settings_platform_utilities.md) covers `FileLockFactory`, Java-version handling, shared setting-key constants, and Elastic Cloud ID/auth parsing.
- [Ruby–Java setting bridge](application_bootstrap_and_settings_setting_bridge.md) covers `Coercible`, `Boolean`, `SettingDelegator`, deprecated aliases, and the lifecycle shared by Ruby and Java settings.

## End-to-end process

```mermaid
sequenceDiagram
    participant U as Operator
    participant R as Runner
    participant S as Settings
    participant L as Source loader
    participant V as Validators
    participant A as Agent

    U->>R: command line
    R->>S: merge YAML and CLI values
    S->>S: coerce, post-process, validate
    R->>V: run bootstrap/resource checks
    R->>L: resolve pipeline sources
    alt invalid or conflicting input
        V-->>R: error or warning
        R-->>U: diagnostic and non-zero exit
    else valid input
        R->>R: acquire path.data/.lock
        R->>A: create and execute agent
        A-->>R: shutdown status
        R-->>U: exit status
    end
```

## Module boundaries and dependencies

Configuration source discovery is described in [configuration_sources_and_loading.md](configuration_sources_and_loading.md); this module consumes its results and owns the decision to proceed. Pipeline parsing and IR compilation are documented in [pipeline_configuration_parser.md](pipeline_configuration_parser.md) and [pipeline_ir_and_compilation.md](pipeline_ir_and_compilation.md). Agent lifecycle behavior belongs to [pipeline_lifecycle_and_execution.md](pipeline_lifecycle_and_execution.md), while persistent queue implementation details belong to [persistent_queue.md](persistent_queue.md). Secret material is handled by [secret_store.md](secret_store.md), and runtime diagnostics are exposed through [monitoring_http_api.md](monitoring_http_api.md) and [logging.md](logging.md).

The bootstrap layer therefore acts as an orchestrator and policy boundary: it validates enough context to start safely, delegates configuration interpretation and execution to neighboring modules, and guarantees process-level cleanup when startup or runtime fails.
