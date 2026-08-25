# API Core Infrastructure – Authentication & Configuration

## Introduction

This module contains the two foundational building blocks that secure and configure the Wazuh REST API server:

- **`api/api/authentication.py`** — implements JWT-based authentication and authorization for every API request: credential validation, token generation/decoding, token revocation checks, and the RBAC policy attachment that downstream endpoints rely on.
- **`api/api/configuration.py`** — loads, validates, and defaults the API's own YAML configuration (`api.yaml`) and the RBAC security configuration (`security.yaml`), and provides TLS certificate/key bootstrap utilities used when the API starts in HTTPS mode.

Together these two files answer two questions that must be resolved before any API request can be processed: **"Is the caller who they claim to be, and what are they allowed to do?"** and **"How is this API instance configured to run?"**

This module is a child of [api_core_infrastructure](api_core_infrastructure.md), which aggregates all core API plumbing (logging, middleware, request utilities, server lifecycle, and Pydantic-style models). Sibling modules under that parent include:

- [api_core_infrastructure_server_lifecycle](api_core_infrastructure_server_lifecycle.md) — process bootstrap, SSL context creation, signal handling (`configure_ssl` consumes the certs generated here).
- [api_core_infrastructure_middleware](api_core_infrastructure_middleware.md) — request-level middlewares (rate limiting, blocked IP checks, secure headers) that run around the authentication flow.
- [api_core_infrastructure_logging](api_core_infrastructure_logging.md) — API logger setup consumed by the `DistributedAPI` calls made in this module.
- [api_core_infrastructure_request_utils](api_core_infrastructure_request_utils.md) and [api_core_infrastructure_models](api_core_infrastructure_models.md) — request parsing/validation and response models used across all controllers, including the security controller.

For the actual RBAC data model, permission resolution, and user/role/policy management, see [security_rbac_module](security_rbac_module.md) — that module owns `AuthenticationManager`, `TokenManager`, `UserRolesManager`, and the `optimize_resources` permission preprocessor that this module calls into. For distributed request execution (`DistributedAPI`) and cluster-aware configuration reads (`read_config`), see [cluster_dapi](cluster_dapi.md) and [cluster_utils](cluster_utils.md).

---

## 1. Purpose and Core Functionality

### 1.1 `authentication.py` — Identity & Access Control

| Responsibility | Function(s) |
|---|---|
| Validate username/password against the RBAC database | `check_user_master`, `check_user` |
| Manage the API's asymmetric signing keys (EC P-521 / ES512) | `generate_keypair`, `change_keypair` |
| Read cached security configuration (token TTL, RBAC mode) | `get_security_conf` |
| Mint a signed JWT for an authenticated session | `generate_token` |
| Validate a token's freshness/role consistency against the master node | `check_token` (memoized via `@rbac_utils.token_cache()`) |
| Fully decode, verify, and enrich an incoming request's bearer token | `decode_token` |

### 1.2 `configuration.py` — API & Security Configuration

| Responsibility | Function(s) |
|---|---|
| Provide baseline defaults for `api.yaml` / `security.yaml` | `default_api_configuration`, `default_security_configuration` |
| Merge user overrides on top of defaults, validating against JSON Schema | `fill_dict`, `read_yaml_config` |
| Normalize configuration quirks (lowercase strings, yes/no → bool) | `dict_to_lowercase`, `read_yaml_config._replace_bools` |
| Rewrite relative TLS paths to absolute paths under the SSL directory | `append_wazuh_prefixes` |
| Generate a private key and self-signed certificate for first-run HTTPS | `generate_private_key`, `generate_self_signed_certificate` |
| Make the authentication worker pool ignore `SIGINT` | `init_auth_worker` |
| Expose ready-to-use, validated, module-level configuration objects | `api_conf`, `security_conf` |

`configuration.py` executes its defaults-validation and `api_conf`/`security_conf` construction **at import time**, so simply importing this module performs I/O (reading `api.yaml`/`security.yaml` from disk) and can raise `APIError(2000)`/`APIError(2004)` if the files are malformed.

---

## 2. Architecture Overview

```mermaid
graph TB
    subgraph "api_core_infrastructure_auth_config"
        AUTH[authentication.py]
        CONF[configuration.py]
    end

    subgraph "Consumers (sibling/parent modules)"
        MW["middlewares.py<br/>(api_core_infrastructure_middleware)"]
        SIGNALS["signals.py / wazuh_apid.py<br/>(api_core_infrastructure_server_lifecycle)"]
        CTRLS["controllers/*<br/>(all API controller modules)"]
        SEC["security_controller.py<br/>(security_rbac_module)"]
    end

    subgraph "RBAC and Data Layer (security_rbac_module)"
        ORM["rbac/orm.py<br/>AuthenticationManager, TokenManager,<br/>UserRolesManager"]
        PRE["rbac/preprocessor.py<br/>optimize_resources"]
    end

    subgraph "Distributed Execution (cluster_module)"
        DAPI["cluster/dapi/dapi.py<br/>DistributedAPI"]
        CUTIL["cluster/utils.py<br/>read_config"]
    end

    subgraph "Filesystem"
        APIYAML[("api.yaml")]
        SECYAML[("security.yaml")]
        KEYS[("private_key.pem<br/>public_key.pem")]
        CERTS[("server.key / server.crt")]
    end

    CONF -->|read_yaml_config| APIYAML
    CONF -->|read_yaml_config| SECYAML
    CONF -->|generate_private_key /<br/>generate_self_signed_certificate| CERTS
    SIGNALS -->|configure_ssl uses| CERTS
    CONF -->|api_conf / security_conf| AUTH

    AUTH -->|generate_keypair| KEYS
    AUTH -->|DistributedAPI f=check_user_master,<br/>get_security_conf, check_token| DAPI
    DAPI --> ORM
    DAPI --> CUTIL
    AUTH --> PRE

    MW -->|calls before controller| AUTH
    CTRLS -->|Depends: decode_token| AUTH
    SEC -->|login_user, logout_user| AUTH
```

---

## 3. Component Relationships

```mermaid
classDiagram
    class authentication_py {
        +check_user_master(user, password) dict
        +check_user(user, password) dict
        +generate_keypair() tuple
        +change_keypair() tuple
        +get_security_conf() dict
        +generate_token(user_id, data, auth_context) str
        +check_token(username, roles, token_nbf_time, run_as) dict
        +decode_token(token) dict
    }

    class configuration_py {
        +default_api_configuration dict
        +default_security_configuration dict
        +dict_to_lowercase(mydict)
        +append_wazuh_prefixes(dictionary, path_fields)
        +fill_dict(default, config, json_schema) dict
        +generate_private_key(path) RSAPrivateKey
        +generate_self_signed_certificate(key, path)
        +read_yaml_config(config_file, default_conf) dict
        +init_auth_worker()
        +api_conf dict
        +security_conf dict
    }

    class DistributedAPI {
        <<cluster_dapi>>
        +distribute_function()
    }

    class AuthenticationManager {
        <<security_rbac_module>>
        +check_user(user, password) bool
        +get_user(username) dict
        +user_allow_run_as(username) bool
    }

    class TokenManager {
        <<security_rbac_module>>
        +is_token_valid(role_id, user_id, token_nbf_time, run_as) bool
    }

    class UserRolesManager {
        <<security_rbac_module>>
        +get_all_roles_from_user(user_id) list
    }

    authentication_py --> DistributedAPI : submits check_user_master, get_security_conf, check_token
    authentication_py --> AuthenticationManager : uses via check_user_master/check_token
    authentication_py --> TokenManager : uses via check_token
    authentication_py --> UserRolesManager : uses via check_token
    authentication_py ..> configuration_py : conf.security_conf, conf.read_yaml_config
```

---

## 4. Login / Token Lifecycle (Data Flow)

The following sequence shows how a client obtains and later reuses a JWT, and how validity is checked against RBAC state that may only live on the master node in a clustered deployment.

```mermaid
sequenceDiagram
    participant Client
    participant API as API Worker Node (controller + middleware)
    participant Auth as authentication.py
    participant DAPI as DistributedAPI
    participant Master as Master Node
    participant RBACDB as RBAC DB (orm.py)

    Client->>API: POST /security/user/authenticate (Basic Auth user/password)
    API->>Auth: check_user(user, password)
    Auth->>DAPI: distribute_function(f=check_user_master)
    DAPI->>Master: forward request_type=local_master
    Master->>RBACDB: AuthenticationManager.check_user()
    RBACDB-->>Master: True/False
    Master-->>DAPI: result dict
    DAPI-->>Auth: result
    Auth-->>API: sub/active or None
    API->>Auth: generate_token(user_id, roles_data)
    Auth->>DAPI: distribute_function(f=get_security_conf)
    DAPI->>Master: fetch auth_token_exp_timeout, rbac_mode
    Master-->>Auth: security_conf values
    Auth->>Auth: jwt.encode(payload, private_key, ES512)
    Auth-->>API: signed JWT
    API-->>Client: 200 OK token

    Note over Client,API: Later requests present the token as a Bearer header

    Client->>API: GET /agents (Authorization Bearer token)
    API->>Auth: decode_token(token)
    Auth->>Auth: jwt.decode(token, public_key, ES512)
    Auth->>DAPI: distribute_function(f=check_token, username, roles, nbf, run_as)
    DAPI->>Master: forward
    Master->>RBACDB: get_user / get_all_roles_from_user / is_token_valid per role
    RBACDB-->>Master: validity + roles
    Master-->>Auth: valid true, policies
    alt token invalid or expired policy mismatch
        Auth-->>API: raise Unauthorized (INVALID_TOKEN/EXPIRED_TOKEN)
        API-->>Client: 401
    else token valid
        Auth->>Auth: attach rbac_policies to payload
        Auth-->>API: decoded payload with policies
        API-->>Client: 200 OK request processed
    end
```

Key points:
- `check_token` is wrapped with `@rbac_utils.token_cache()` so repeated validation for the same token/role state is served from cache instead of hitting the RBAC database every request.
- `decode_token` performs a **second** live check against `get_security_conf` to detect that the RBAC mode or token expiration policy hasn't changed since the token was issued — if it has, the token is forcibly invalidated (`EXPIRED_TOKEN`), even if cryptographically valid.
- All cross-node calls go through `DistributedAPI` with `request_type='local_master'`, ensuring RBAC checks always execute against the authoritative master-node database, regardless of which node received the client's request. See [cluster_dapi](cluster_dapi.md).

---

## 5. Configuration Loading Flow

```mermaid
flowchart TD
    START([Module import / API startup]) --> VALDEF["Validate default_security_configuration and default_api_configuration against JSON Schemas"]
    VALDEF -->|invalid defaults| ERR1["raise APIError 2000 (schema drift)"]
    VALDEF -->|valid| READAPI["read_yaml_config(CONFIG_FILE_PATH)"]

    READAPI --> EXISTS{"api.yaml exists?"}
    EXISTS -->|no| DEFAULTSONLY["configuration = deepcopy(default_api_configuration)"]
    EXISTS -->|yes| LOAD["yaml.safe_load(api.yaml)"]
    LOAD -->|IOError| ERR2["raise APIError 2004"]
    LOAD --> REPLACEBOOL["replace_bools() 'yes'/'no' to True/False"]
    REPLACEBOOL --> LOWER["dict_to_lowercase()"]
    LOWER --> FILL["fill_dict(default, user_config, api_config_schema)"]
    FILL -->|schema violation| ERR3["raise APIError 2000"]
    FILL --> MERGED["merged configuration"]

    DEFAULTSONLY --> PREFIX
    MERGED --> PREFIX["append_wazuh_prefixes() https.key/cert/ca to absolute paths under API_SSL_PATH"]
    PREFIX --> APICONF[("api_conf module-level singleton")]

    READAPI -.->|same pipeline, security_config_schema| READSEC["read_yaml_config(SECURITY_CONFIG_PATH, default_security_configuration)"]
    READSEC --> SECCONF[("security_conf module-level singleton")]

    APICONF --> USEDBY1["Server lifecycle: host, port, TLS, CORS, access limits, upload limits"]
    SECCONF --> USEDBY2["authentication.py get_security_conf(): auth_token_exp_timeout, rbac_mode"]
```

### Certificate Bootstrap

When HTTPS is enabled and no certificate/key pair exists yet, `generate_private_key` and `generate_self_signed_certificate` create a 2048-bit RSA key and a one-year self-signed X.509 certificate under the configured SSL path. This is invoked from the [server lifecycle module](api_core_infrastructure_server_lifecycle.md) (`configure_ssl` in `wazuh_apid.py`) before the ASGI server binds its socket.

---

## 6. Sequence: API Process Startup Touching This Module

```mermaid
sequenceDiagram
    participant Proc as wazuh_apid.py (server_lifecycle)
    participant Conf as configuration.py
    participant Auth as authentication.py
    participant FS as Filesystem

    Proc->>Conf: import api.configuration
    Conf->>Conf: validate defaults vs JSON schemas
    Conf->>FS: read api.yaml / security.yaml if present
    Conf-->>Proc: api_conf, security_conf ready

    Proc->>Proc: configure_ssl() [server_lifecycle]
    alt certs missing
        Proc->>Conf: generate_private_key(), generate_self_signed_certificate()
        Conf->>FS: write server.key / server.crt (chmod 0400)
    end

    Proc->>Auth: import api.authentication
    Auth->>Auth: generate_keypair() (lazy, on first token op)
    Auth->>FS: read/write private_key.pem, public_key.pem (chmod 0640)

    Proc->>Proc: init ThreadPoolExecutor for auth pool
    Proc->>Conf: init_auth_worker (worker initializer, ignores SIGINT per worker thread)
```

---

## 7. Key Design Notes

- **Asymmetric JWT signing (ES512):** Unlike HMAC-based JWTs, ES512 lets the API validate tokens using only the public key, while private-key signing is isolated to `generate_token`. Keys are persisted to disk (`SECURITY_PATH`) so tokens remain valid across API restarts and worker processes.
- **Master-authoritative RBAC:** All identity/authorization decisions (`check_user_master`, `check_token`, `get_security_conf`) are executed via `DistributedAPI` with `request_type='local_master'`, so worker nodes never trust locally cached RBAC state for authorization decisions — only for JWT cryptographic validation, which is stateless.
- **Config/Schema coupling:** `configuration.py` self-validates its own defaults against `api.validator.api_config_schema` / `security_config_schema` at import time. Any schema change must be reflected in the defaults or the API will fail to start with `APIError(2000)`. See [api_core_infrastructure_request_utils](api_core_infrastructure_request_utils.md) for the validator module.
- **Path safety:** `append_wazuh_prefixes` ensures user-supplied relative paths for `https.key`/`https.cert`/`https.ca` are always resolved under `API_SSL_PATH`, preventing path traversal via configuration.
- **Deprecation handling:** `read_yaml_config` detects the legacy `cache.enabled` option and logs a deprecation warning (`CACHE_DEPRECATED_MESSAGE`) via the API logger (see [api_core_infrastructure_logging](api_core_infrastructure_logging.md)).
- **Signal isolation for auth pool:** `init_auth_worker` is used as a `ThreadPoolExecutor` initializer so that `SIGINT` delivered to the main process doesn't propagate unhandled exceptions inside auth worker threads during graceful shutdown (coordinated with [api_core_infrastructure_server_lifecycle](api_core_infrastructure_server_lifecycle.md)'s signal handlers).

---

## 8. Related Documentation

- [api_core_infrastructure](api_core_infrastructure.md) — parent module overview.
- [api_core_infrastructure_server_lifecycle](api_core_infrastructure_server_lifecycle.md) — SSL bootstrap and process signal handling.
- [api_core_infrastructure_middleware](api_core_infrastructure_middleware.md) — request middleware chain that runs around authentication.
- [api_core_infrastructure_logging](api_core_infrastructure_logging.md) — API logging configuration.
- [api_core_infrastructure_request_utils](api_core_infrastructure_request_utils.md) — request validators including the JSON Schemas referenced by `configuration.py`.
- [security_rbac_module](security_rbac_module.md) — RBAC ORM, preprocessor, and `security_controller` endpoints (`login_user`, `logout_user`, `revoke_all_tokens`, etc.) that are the primary consumers of this module.
- [cluster_dapi](cluster_dapi.md) — `DistributedAPI` used to route authentication/authorization calls to the master node.
- [cluster_utils](cluster_utils.md) — `read_config` used to determine node type during token decoding.
