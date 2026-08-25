# Unit Tests – OS Auth

## Purpose

`Unit_Tests_-_OS_Auth` is the CMocka-based unit-test suite for Wazuh’s OS Auth/Authd subsystem. It validates enrollment parsing, agent validation and insertion, replacement policies, key requests, configuration handling, password generation, certificate generation, and SSL read aggregation.

The tests isolate production code with deterministic mocks and wrappers. They do not require a running Authd daemon, live TLS connections, external sockets, persistent `client.keys`, or database services.

## Architecture

### Enrollment and validation coverage

```mermaid
flowchart LR
    Request[Enrollment request] --> Parse[w_auth_parse_data]
    Parse --> Validate[w_auth_validate_data]
    Validate --> Replace[w_auth_replace_agent]
    Validate --> Add[w_auth_add_agent]
    Add --> Keystore[In-memory keystore]
    Replace --> Queue[Removal queue]
    Keystore --> Persist[Authd persistence]

    T1[test_auth_parse.c] -. tests .-> Parse
    T2[test_auth_validate.c] -. tests .-> Validate
    T2 -. tests .-> Replace
    T3[test_auth_add.c] -. tests .-> Add
```

### Authd key-request coverage

```mermaid
flowchart TD
    Message[id:agent-id or ip:agent-ip] --> Worker[run_key_request_main]
    Worker --> Queue[Bounded queue and request deduplication]
    Queue --> Dispatch[key_request_dispatch]
    Dispatch --> Provider{Configured provider}
    Provider -->|Unix socket| Socket[key_request_socket_output]
    Provider -->|Executable| Exec[key_request_exec_output]
    Socket --> JSON[JSON response]
    Exec --> JSON
    JSON --> Parse[get_agent_info_from_json]
    Parse --> Destination{Authd node role}
    Destination -->|Master| Local[Local agent addition]
    Destination -->|Worker| Cluster[Cluster forwarding]

    Test[test_auth_key_request.c] -. verifies .-> Dispatch
```

### TLS and certificate coverage

```mermaid
flowchart LR
    Config[Authd configuration] --> Cert[generate_cert]
    Cert --> Key[Private-key PEM]
    Cert --> X509[X.509 certificate PEM]
    Key --> SSL[SSL context]
    X509 --> SSL
    SSL --> Read[wrap_SSL_read]
    Read --> Authd[Authd server/client]

    T1[test_generate_cert.c] -. tests .-> Cert
    T2[test_ssl.c] -. tests .-> Read
    T3[test_authd-config.c] -. tests .-> Config
```

## Repository structure

```text
src/unit_tests/os_auth/
├── test_auth.c
├── test_auth_add.c
├── test_auth_key_request.c
├── test_auth_parse.c
├── test_auth_validate.c
├── test_authd-config.c
├── test_generate_cert.c
└── test_ssl.c
```

| Test module | Main responsibility |
|---|---|
| `test_auth.c` | Deterministic enrollment-password generation |
| `test_auth_add.c` | Agent creation, key generation, and keystore insertion |
| `test_auth_key_request.c` | Socket/executable key providers, JSON parsing, dispatch, and cluster/local registration |
| `test_auth_parse.c` | Enrollment message parsing, password checks, fields, groups, IPs, and key hashes |
| `test_auth_validate.c` | Duplicate detection, group validation, replacement policy, and keystore mutation |
| `test_authd-config.c` | `allow_higher_versions` configuration parsing and diagnostics |
| `test_generate_cert.c` | Private-key and X.509 generation, signing, PEM persistence, and failure handling |
| `test_ssl.c` | SSL read error handling, buffer offsets, capacity tracking, and multi-record aggregation |

## Core component references

- [OS Auth subsystem](os_auth.md)
- [Enrollment core](os_auth_enrollment_core.md)
- [Authd server daemon](os_auth_server_daemon.md)
- [Authd local server](os_auth_local_server.md)
- [Authd client](os_auth_client.md)
- [SSL and certificate handling](os_auth_ssl_certificates.md)
- [Authd configuration](Authd_Config.md)
- [OS cryptography](os_crypto.md)
- [Shared unit-test infrastructure](test_infrastructure.md)