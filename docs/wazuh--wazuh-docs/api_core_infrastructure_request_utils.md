# API Core Infrastructure — Request Utils

## Introduction

The **Request Utils** module is a foundational part of the Wazuh REST API's core infrastructure. It provides the low-level plumbing that every incoming HTTP request passes through before it reaches a controller: URI parameter normalization, OpenAPI/JSON-Schema format validators, and a collection of parsing/serialization helper functions used throughout the API layer.

This module does not expose its own HTTP endpoints. Instead, it is consumed transparently by the [Connexion](https://connexion.readthedocs.io/) framework (OpenAPI request routing) and by every API controller (via `wazuh.core.exception` translation, parameter parsing, and Swagger `format` keyword validation declared in the `spec.yaml`).

It is one of five sibling sub-modules that together make up the parent `api_core_infrastructure` module:

| Sibling module | Responsibility |
|---|---|
| [api_core_infrastructure_server_lifecycle](api_core_infrastructure_server_lifecycle.md) | Process startup/shutdown, SSL configuration |
| [api_core_infrastructure_auth_config](api_core_infrastructure_auth_config.md) | Authentication/token decoding, worker auth init |
| [api_core_infrastructure_middleware](api_core_infrastructure_middleware.md) | ASGI middlewares (rate limiting, IP blocking, access logging) |
| [api_core_infrastructure_logging](api_core_infrastructure_logging.md) | API logging setup and JSON formatting |
| **api_core_infrastructure_request_utils** (this module) | URI parsing, parameter parsing, field/format validation |
| [api_core_infrastructure_models](api_core_infrastructure_models.md) | Base Connexion models, JSON encoder, default controller |

## Purpose and Core Functionality

This module has three closely related responsibilities, one per file:

1. **`api/api/uri_parser.py` — `APIUriParser`**
   A Connexion `OpenAPIURIParser` subclass that normalizes (lower-cases) a fixed set of query-string parameters (`component`, `configuration`, `hash`, `requirement`, `status`, `type`, `section`, `tag`, `level`, `resource`) before Connexion validates them against the OpenAPI spec enums. This guarantees that case-insensitive user input (e.g. `?type=JSON`) still matches lowercase enum values defined in `spec.yaml`.

2. **`api/api/util.py` — Generic request/response helpers**
   A set of stand-alone functions used across the API layer:
   - `serialize()` / `_deserialize*()` / `deserialize_model()` — convert between Python model objects, primitives, dates and JSON-friendly structures (Swagger codegen style).
   - `_parse_q_param()`, `_parse_search_param()`, `_parse_sort_param()` — convert raw API query string fragments (`q=`, `search=`, `sort=`) into structured dictionaries consumable by the Wazuh framework's DB query engine (see [framework_core_utils](framework_core_utils.md) `WazuhDBQueryGroupBy`, `AffectedItemsWazuhResult`, etc.).
   - `parse_api_param()` — dispatch helper that picks the correct parser (`search`/`sort`) by name.
   - `to_relative_path()` — strips the Wazuh installation base path from an absolute path (delegates to `wazuh.core.common.WAZUH_PATH`).
   - `raise_if_exc()` / `_create_problem()` — central translation point that converts `WazuhException` subclasses (from `framework/wazuh/core/exception.py`) into Connexion `ProblemException` HTTP responses with proper status codes (400/403/404/406/429/500).
   - `deprecate_endpoint()` — decorator that stamps `Deprecated`/`Link` HTTP headers on a controller's response.
   - `only_master_endpoint()` — decorator that rejects requests on a worker node (HTTP 404 / WazuhResourceNotFound 902) unless the API is running on the cluster master; relies on `framework/wazuh/core/cluster/utils.py::running_in_master_node` (see [cluster_utils](cluster_utils.md)).

3. **`api/api/validator.py` — Field-level validators & JSON-Schema format checkers**
   A large collection of compiled regular expressions (`_alphanumeric_param`, `_group_names`, `_wazuh_version`, `_wpk_path`, etc.) each of which is registered as a custom **JSON-Schema `format` checker** via `Draft4Validator.FORMAT_CHECKER.checks(...)`. These are referenced by name (`format: alphanumeric`, `format: wazuh_version`, etc.) inside the OpenAPI `spec.yaml` used by every controller's request/response schema. It also defines:
   - `check_xml()` — validates that a string is well-formed XML (used by CDB list/rule/decoder file upload endpoints).
   - `is_safe_path()` — path-traversal protection, ensuring uploaded/queried paths stay inside `WAZUH_PATH`.
   - `check_component_configuration_pair()` — validates `component`/`configuration` combinations against `WAZUH_COMPONENT_CONFIGURATION_MAPPING` (used by manager/cluster "get configuration on demand" endpoints).
   - `security_config_schema` / `api_config_schema` — full JSON-Schema definitions for the security and API YAML configuration files, used when validating `PUT` requests that change server configuration.

## Architecture

```mermaid
graph TB
    subgraph "HTTP Client"
        C[REST API Client]
    end

    subgraph "Connexion / OpenAPI Layer"
        SPEC[spec.yaml<br/>OpenAPI Definition]
        ROUTER[Connexion Router]
        URIPARSER[APIUriParser<br/>uri_parser.py]
        VALIDATOR[Draft4Validator<br/>+ Custom Format Checkers<br/>validator.py]
    end

    subgraph "api_core_infrastructure_request_utils (this module)"
        UTIL[util.py<br/>parse_api_param<br/>raise_if_exc<br/>only_master_endpoint<br/>deprecate_endpoint]
    end

    subgraph "Controllers"
        CTRL[api/controllers/*.py<br/>e.g. agent_controller, rule_controller]
    end

    subgraph "Framework Core"
        EXC[wazuh.core.exception<br/>WazuhException hierarchy]
        CLUSTERUTIL[wazuh.core.cluster.utils<br/>running_in_master_node]
        DBQUERY[wazuh.core.utils<br/>WazuhDBQueryGroupBy]
    end

    C -->|HTTP request with query string| ROUTER
    ROUTER --> URIPARSER
    URIPARSER -->|lowercased params| VALIDATOR
    SPEC -.->|format: alphanumeric, wazuh_version, etc.| VALIDATOR
    VALIDATOR -->|validated request| CTRL
    CTRL -->|q=, search=, sort=| UTIL
    UTIL -->|structured filter dict| DBQUERY
    CTRL -->|"@only_master_endpoint"| UTIL
    UTIL --> CLUSTERUTIL
    CTRL -->|exceptions| UTIL
    UTIL -->|raise_if_exc / _create_problem| EXC
    UTIL -->|ProblemException| C

    style URIPARSER fill:#e1f5ff
    style UTIL fill:#e1f5ff
    style VALIDATOR fill:#e1f5ff
```

## Component Relationships

```mermaid
classDiagram
    class OpenAPIURIParser {
        <<Connexion base class>>
        +resolve_params(params, _in)
    }

    class APIUriParser {
        +LOWER_FIELDS tuple
        +resolve_params(params, _in) dict
    }

    OpenAPIURIParser <|-- APIUriParser

    class ValidatorFunctions {
        <<module: validator.py>>
        +check_exp(exp, regex) bool
        +check_xml(xml_string) bool
        +is_safe_path(path, basedir, relative) bool
        +check_component_configuration_pair(component, configuration) WazuhError
        +allowed_fields(filters) list
        +format_alphanumeric(value) bool
        +format_alphanumeric_symbols(value) bool
        +format_base64(value) bool
        +format_group_names(value) bool
        +format_group_names_or_all(value) bool
        +format_wazuh_key(value) bool
        +format_wazuh_version(value) bool
        +format_wpk_path(value) bool
        +format_active_response_command(value) bool
        +format_query(value) bool
        +format_range(value) bool
        +format_search(value) bool
        +format_sort(value) bool
        +format_timeframe(value) bool
        +format_date(value) bool
        +format_datetime_or_empty(value) bool
        +format_hash_or_empty(value) bool
        +format_names_or_empty(value) bool
        +format_numbers_or_all(value) bool
        +format_numbers_or_empty(value) bool
        +format_cdb_filename_path(value) bool
        +format_xml_filename(value) bool
        +format_xml_filename_path(value) bool
        +format_get_dirnames_path(value) bool
    }

    class UtilFunctions {
        <<module: util.py>>
        +serialize(item) object
        +_deserialize(data, klass) object
        +deserialize_model(data, klass) object
        +parse_api_param(param, param_type) dict
        +_parse_q_param(query) str
        +_parse_search_param(search) dict
        +_parse_sort_param(sort) dict
        +to_relative_path(full_path) str
        +remove_nones_to_dict(dct) dict
        +get_invalid_keys(original, des) set
        +raise_if_exc(obj) object
        +_create_problem(exc, code) void
        +deprecate_endpoint(link) decorator
        +only_master_endpoint(func) decorator
    }

    class Draft4Validator {
        <<jsonschema library>>
        +FORMAT_CHECKER
    }

    ValidatorFunctions ..> Draft4Validator : registers formats via decorator
    UtilFunctions ..> ValidatorFunctions : independent, both consumed by controllers
```

## Request Processing Data Flow

The following sequence shows how a typical `GET` request with query parameters (`q`, `search`, `sort`, and an enum field) flows through this module's components.

```mermaid
sequenceDiagram
    participant Client
    participant Connexion as Connexion Router
    participant URIParser as APIUriParser
    participant Schema as Draft4Validator (spec.yaml + format checkers)
    participant Controller as API Controller
    participant Util as util.py helpers
    participant Framework as wazuh.core (DBQuery/Exception)

    Client->>Connexion: GET /agents?type=JSON&q=id=001&sort=-name
    Connexion->>URIParser: resolve_params(raw_params, 'query')
    URIParser->>URIParser: lowercase LOWER_FIELDS values (type -> json)
    URIParser-->>Connexion: normalized params
    Connexion->>Schema: validate against spec.yaml (format checkers)
    Schema->>Schema: format_* functions run regex checks
    alt validation fails
        Schema-->>Client: 400 Bad Request
    else validation succeeds
        Schema-->>Connexion: OK
        Connexion->>Controller: invoke controller function(request)
        Controller->>Util: parse_api_param(sort_str, 'sort')
        Util->>Util: _parse_sort_param() -> fields, order
        Controller->>Util: parse_api_param(search_str, 'search')
        Util->>Util: _parse_search_param() -> negation, value
        Controller->>Framework: WazuhDBQueryGroupBy(filters, sort, search)
        Framework-->>Controller: AffectedItemsWazuhResult or WazuhException
        Controller->>Util: raise_if_exc(result)
        alt result is Exception
            Util->>Util: _create_problem(exc)
            Util-->>Client: ProblemException (400/403/404/406/429/500)
        else result is data
            Util-->>Controller: data
            Controller-->>Client: 200 OK + JSON body
        end
    end
```

## Master-Node Restriction Flow

Several cluster/manager endpoints must only run on the master node. `only_master_endpoint` enforces this centrally rather than duplicating the check in every controller.

```mermaid
flowchart TD
    A["Controller function decorated with @only_master_endpoint"] --> B{running_in_master_node?}
    B -->|Yes - master| C[Execute wrapped controller function]
    C --> D[Return awaited response]
    B -->|No - worker| E["raise_if_exc: WazuhResourceNotFound 902"]
    E --> F[_create_problem]
    F --> G[ProblemException 404]
    G --> H[Client receives 404]

    style B fill:#fff3cd
    style E fill:#f8d7da
    style C fill:#d4edda
```

This decorator depends on `framework/wazuh/core/cluster/utils.py::running_in_master_node` — documented in [cluster_utils](cluster_utils.md) — and on the exception hierarchy documented alongside [framework_core_utils](framework_core_utils.md) (`WazuhResourceNotFound`).

## Exception-to-HTTP Mapping

`raise_if_exc` / `_create_problem` in `util.py` is the single translation point between the Wazuh framework's internal exception hierarchy (`framework/wazuh/core/exception.py`, see [framework_core_utils](framework_core_utils.md)) and the HTTP responses the API returns.

```mermaid
flowchart LR
    E[Exception raised by framework/controller code] --> Check{Type check}
    Check -->|WazuhInternalError| R1[HTTP 500 Internal Server Error]
    Check -->|WazuhPermissionError| R2[HTTP 403 Forbidden]
    Check -->|WazuhResourceNotFound| R3[HTTP 404 Not Found]
    Check -->|WazuhTooManyRequests| R4[HTTP 429 Too Many Requests]
    Check -->|WazuhNotAcceptable| R5[HTTP 406 Not Acceptable]
    Check -->|WazuhError generic| R6[HTTP 400 Bad Request]
    Check -->|Not a WazuhException| R7[Exception re-raised unchanged]

    R1 --> P[ProblemException with code, title, detail, remediation, dapi_errors]
    R2 --> P
    R3 --> P
    R4 --> P
    R5 --> P
    R6 --> P
```

## Validator Format Registry

Every regex-based checker in `validator.py` is registered against `jsonschema`'s `Draft4Validator.FORMAT_CHECKER`, which is then wired into Connexion's OpenAPI request validation (declared as `format: <name>` in `api/spec/spec.yaml` for individual path/query parameters). This lets controller authors declare constraints declaratively instead of writing manual validation code.

```mermaid
graph LR
    subgraph SpecYAML["spec.yaml parameter definitions"]
        P1["format: alphanumeric"]
        P2["format: group_names"]
        P3["format: wazuh_version"]
        P4["format: wpk_path"]
        P5["format: query"]
        P6["format: sort / search / range / timeframe"]
        P7["format: hash / names / numbers _or_empty variants"]
        P8["format: xml_filename / xml_filename_path"]
        P9["format: active_response_command"]
    end

    subgraph ValidatorPy["validator.py format checkers"]
        F1["format_alphanumeric / format_alphanumeric_symbols"]
        F2["format_group_names / format_group_names_or_all"]
        F3["format_wazuh_version"]
        F4["format_wpk_path"]
        F5["format_query"]
        F6["format_sort / format_search / format_range / format_timeframe"]
        F7["format_hash_or_empty / format_names_or_empty / format_numbers_or_all / format_numbers_or_empty"]
        F8["format_xml_filename / format_xml_filename_path"]
        F9["format_active_response_command"]
    end

    P1 --> F1
    P2 --> F2
    P3 --> F3
    P4 --> F4
    P5 --> F5
    P6 --> F6
    P7 --> F7
    P8 --> F8
    P9 --> F9

    F4 -.->|calls| SAFE[is_safe_path]
    F9 -.->|calls| SAFE
    F2 -.->|used by| GRP["Agent/CDB group endpoints in agent_module"]
```

Path-related validators (`format_wpk_path`, `format_active_response_command`, `format_get_dirnames_path`, `format_path`) all funnel through `is_safe_path()`, which blocks directory-traversal sequences (`../`, `..\`) and confirms the resolved real path stays inside `WAZUH_PATH` (defined in `framework/wazuh/core/common.py`, see [framework_core_utils](framework_core_utils.md)).

## How Controllers Use This Module

Nearly every controller across the API (see [agent_module](agent_module.md), [rule_module](rule_module.md), [cdb_list_module](cdb_list_module.md), [manager_module](manager_module.md), [cluster_api_controller](cluster_api_controller.md), etc.) uses the utilities in this module in one of these patterns:

1. **Query parameter parsing** — `parse_api_param(request.query_params.get('sort'), 'sort')` to build a filter dict passed into a `WazuhDBQuery*` subclass constructor.
2. **Response/error translation** — `raise_if_exc(await dapi.distributed_api_call())` at the end of nearly every controller function, converting a `DistributedAPI` response (see [cluster_dapi](cluster_dapi.md)) into either the raw result or an HTTP problem.
3. **Master-only restriction** — controllers such as `manager_controller.put_restart` or several `cluster_controller` endpoints are decorated with `@only_master_endpoint`.
4. **Path safety** — file-upload/download endpoints (CDB lists, rules, decoders) rely on `format_cdb_filename_path`, `format_xml_filename_path` and `is_safe_path` declared through the OpenAPI spec to reject malicious paths before the controller body executes.
5. **XML validation** — endpoints accepting raw XML content bodies (rule/decoder/CDB list uploads) call `check_xml()` directly to reject malformed XML before persisting it to disk.

```mermaid
graph TD
    A["PUT /rules/files/filename with XML content body"] --> B["spec.yaml validates filename: format xml_filename_path"]
    B --> C["controller calls check_xml(body)"]
    C -->|invalid XML| D[Return WazuhError via raise_if_exc]
    C -->|valid XML| E["framework/wazuh/rule.py upload_rule_file"]
    E --> F[Written to ruleset directory]
```

## Key Design Notes

- **Stateless & side-effect free**: all functions in this module are pure or rely only on module-level compiled regex objects; there is no persistent state, making the module trivially thread/async safe for use inside the ASGI request pipeline (see [api_core_infrastructure_middleware](api_core_infrastructure_middleware.md) for the surrounding middleware stack that wraps every request).
- **Declarative validation over imperative code**: by registering format checkers against `jsonschema`, most input constraints live in `spec.yaml` rather than scattered across controllers, improving consistency and auditability of allowed input patterns.
- **Centralized exception boundary**: `raise_if_exc`/`_create_problem` is the *only* place where internal Wazuh exceptions are converted into HTTP-facing `ProblemException` objects, ensuring consistent error payload shape (`type`, `title`, `detail`, `remediation`, `dapi_errors`) across the entire API surface.
- **Cluster awareness**: `only_master_endpoint` integrates with the cluster utilities module to keep master-only operations (e.g., certain configuration writes, restarts) from executing on worker nodes, returning a well-formed 404 instead of an inconsistent partial operation.

## Related Documentation

- [api_core_infrastructure_server_lifecycle](api_core_infrastructure_server_lifecycle.md) — process bootstrap, SSL configuration, and signal handling that starts the ASGI app this module's validators run inside.
- [api_core_infrastructure_auth_config](api_core_infrastructure_auth_config.md) — authentication/token decoding that runs before request routing.
- [api_core_infrastructure_middleware](api_core_infrastructure_middleware.md) — ASGI middleware stack (rate limiting, IP blocking, access logging) surrounding the request lifecycle.
- [api_core_infrastructure_logging](api_core_infrastructure_logging.md) — API access/error logging configuration.
- [api_core_infrastructure_models](api_core_infrastructure_models.md) — base Connexion models and JSON encoder used to serialize controller responses.
- [framework_core_utils](framework_core_utils.md) — `WazuhException` hierarchy, `WazuhDBQuery*` classes, and `common.WAZUH_PATH` referenced throughout this module.
- [cluster_utils](cluster_utils.md) — `running_in_master_node`, used by `only_master_endpoint`.
- [cluster_dapi](cluster_dapi.md) — `DistributedAPI`, whose responses are typically passed through `raise_if_exc`.
