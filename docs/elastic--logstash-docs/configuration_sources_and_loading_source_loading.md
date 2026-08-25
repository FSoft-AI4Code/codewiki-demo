# Source selection and local loading

This submodule implements the single-pipeline configuration-source contract. It turns an inline string, a local path/glob, or an HTTP(S) URI into ordered `SourceWithMetadata` fragments and then wraps those fragments in one `org.logstash.config.ir.PipelineConfig`.

## Components

### `LogStash::Config::Source::Base`

`Base` stores the settings object and exposes the common source API:

- `pipeline_configs` returns pipeline definitions and is abstract.
- `match?` indicates whether the source applies.
- `config_conflict?` reports incompatible settings.
- `config_reload_automatic`, `config_string`, and `config_path` read typed settings and provide predicates for whether they were configured.

It also owns `conflict_messages`, allowing callers to present all detected conflicts together.

### `Local`

`Local#match?` selects the source when either `config.string` or `path.config` is present, except when automatic reload is requested with only an inline string. `#pipeline_configs` first checks conflicts, loads fragments, and returns either an empty list or one `PipelineConfig` using the configured `pipeline.id`.

```mermaid
flowchart LR
    B[Base settings helpers] --> L[Local]
    L -->|config.string| CSL[ConfigStringLoader]
    L -->|local path/file URI| CPL[ConfigPathLoader]
    L -->|http/https URI| CRL[ConfigRemoteLoader]
    CSL --> SWM[SourceWithMetadata[]]
    CPL --> SWM
    CRL --> SWM
    SWM --> PC[PipelineConfig]
```

### `ConfigStringLoader`

The inline loader creates one source fragment identified as `config_string`. For backward compatibility, it appends default input and output fragments when the string does not contain an `input {` or `output {` block. This ensures an inline fragment can still form a runnable pipeline under the historical defaults.

### `ConfigPathLoader`

The path loader expands the path, removes a `file://` prefix, treats directories as `*`, and reads sorted glob matches. It accepts regular files and named pipes, skips editor temporary files ending in `~`, forces UTF-8, and raises `ConfigLoadingError` when any matched file is not valid UTF-8. Empty matches are allowed and logged.

### `ConfigRemoteLoader`

The remote loader parses the URI, performs a GET over HTTP or HTTPS, and returns one fragment using the URI scheme as protocol. Statuses such as 404, 403, 500, redirects, and all other non-200 responses become localized `ConfigLoadingError`s. Redirects are intentionally not followed.

## Conflict and classification flow

```mermaid
flowchart TD
    SETTINGS[config.string / path.config / reload setting] --> CONFLICT{conflict?}
    CONFLICT -->|automatic reload + string| ERR[ConfigurationError]
    CONFLICT -->|string + path| ERR
    CONFLICT -->|no| CLASSIFY{path scheme}
    CLASSIFY -->|file or absent| FILE[Read local path/glob]
    CLASSIFY -->|http(s)| NET[Fetch remote URI]
    SETTINGS -->|string only| INLINE[Read inline config]
    INLINE --> BUILD[Build PipelineConfig]
    FILE --> BUILD
    NET --> BUILD
```

## Integration notes

The source layer does not parse Logstash syntax. It preserves source metadata for downstream parser/IR diagnostics and delegates interpretation to the compiler documented in [pipeline_configuration_parser.md](pipeline_configuration_parser.md). Startup selection and validation are coordinated by [application_bootstrap_and_settings.md](application_bootstrap_and_settings.md).
