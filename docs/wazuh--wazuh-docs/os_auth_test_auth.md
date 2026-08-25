# os_auth_test_auth — Random Enrollment Password Unit Test

## Introduction

os_auth_test_auth is a focused CMocka unit-test module for the Wazuh authentication and enrollment core. It verifies the successful deterministic output of w_generate_random_pass(), the helper used by os_auth to create an authentication password.

The module contains one test case, test_w_generate_random_pass_success, and a CMocka test runner in main. It does not start wazuh-authd, open a socket, perform TLS, access client.keys, or modify wazuh-db. Those responsibilities belong to the production modules documented in [os_auth](os_auth.md), [os_auth_enrollment_core](os_auth_enrollment_core.md), and [os_auth_server_daemon](os_auth_server_daemon.md).

## Scope and role in the system

The test sits at the lowest-level unit-test boundary of the os_auth enrollment path:

~~~mermaid
flowchart LR
    Test["os_auth_test_auth\n(test_auth.c)"]
    Core["os_auth_enrollment_core\n(auth.c/auth.h)"]
    Daemon["wazuh-authd\n(server daemon)"]
    Client["agent-auth\n(client)"]
    Test -->|unit-tests| Core
    Client -->|enrollment request| Daemon
    Daemon -->|calls enrollment helpers| Core
~~~

The production helper is expected to derive a password from runtime inputs. The test replaces those inputs with fixed values so the result can be compared exactly. This makes the test a regression check for input ordering, encoding, and digest-generation behavior without requiring randomness or host-specific state.

## Components

| Component | Responsibility |
|---|---|
| CMUnitTest | CMocka test descriptor type used to register the test function. |
| main() | Registers the single test and executes it with cmocka_run_group_tests. |
| test_w_generate_random_pass_success() | Configures deterministic mocks, calls w_generate_random_pass(), checks the expected string, and frees the returned allocation. |
| w_generate_random_pass() | Production function under test, declared by src/os_auth/auth.h and implemented in the enrollment core. |

## Test architecture and dependencies

~~~mermaid
graph TB
    subgraph TestModule["os_auth_test_auth"]
        Main["main()"]
        Case["test_w_generate_random_pass_success()"]
        Assert["assert_string_equal()\nos_free()"]
    end
    subgraph Production["Production code"]
        Generate["w_generate_random_pass()"]
        AuthH["src/os_auth/auth.h"]
    end
    subgraph Mocks["CMocka-controlled dependencies"]
        Random["__wrap_os_random"]
        Noise["__wrap_GetRandomNoise"]
        Time["__wrap_time"]
        Uname["__wrap_getuname"]
    end
    Shared["shared.h / shared logging"]
    Security["headers/sec.h\nsecurity/key structures"]
    AddAgent["addagent/manage_agents.h"]
    CMocka["cmocka"]
    Main --> Case
    Main --> CMocka
    Case --> Generate
    Case --> Assert
    Generate --> AuthH
    Generate --> Random
    Generate --> Noise
    Generate --> Time
    Generate --> Uname
    Case -. includes .-> Shared
    Case -. includes .-> Security
    Case -. includes .-> AddAgent
~~~

The production headers are included because the test is compiled in the native authentication test environment. In this test case, the observable behavior is limited to the password helper; keynode, keystore, socket, and enrollment APIs are not exercised directly.

## Deterministic input setup

The test programs the following mocked values before invoking the helper:

| Mocked dependency | Values supplied | Purpose |
|---|---|---|
| __wrap_os_random | 146557, then 314159 | Fixed pseudo-random values consumed by the helper. |
| __wrap_GetRandomNoise | "Wazuh", then "The Open Source Security Platform" | Fixed noise material. Returned strings are heap-allocated with strdup. |
| __wrap_time | 1655254875 | Fixed timestamp input. |
| __wrap_getuname | A fixed Linux/Ubuntu/Wazuh version string | Fixed host and software identity input. will_return_always applies to every call. |

The setup is explicit: if the helper changes the number, order, or type of calls to these dependencies, CMocka exposes that contract change rather than allowing a host-dependent result.

## Execution flow

~~~mermaid
sequenceDiagram
    participant Runner as CMocka runner
    participant Test as test_w_generate_random_pass_success
    participant Mocks as Mocked runtime inputs
    participant Helper as w_generate_random_pass
    participant Assert as Assertion and cleanup
    Runner->>Test: invoke test
    Test->>Mocks: queue random values, noise, time, uname
    Test->>Helper: call helper
    Helper->>Mocks: consume configured returns
    Mocks-->>Helper: deterministic inputs
    Helper-->>Test: allocated password string
    Test->>Assert: compare with expected digest
    Test->>Assert: os_free(result)
    Assert-->>Runner: success or failure
~~~

## Assertion and expected behavior

The test requires:

~~~text
w_generate_random_pass() ==
6e0d9a4188ac9de8fa695bd96e276090
~~~

The assertion is an exact string comparison. A successful run confirms that the helper consumes the configured runtime inputs, produces a stable value for that input sequence, returns a NUL-terminated textual value, and returns memory that the caller can release with os_free.

The test does not establish cryptographic strength or randomness quality. It verifies the deterministic transformation implemented by the current production helper. Entropy and cryptographic primitive details belong to the broader [os_crypto](os_crypto.md) and shared-library test suites.

## Resource ownership

__wrap_GetRandomNoise is configured with strdup, so the mocked noise values model dynamically allocated input strings. The helper owns intermediate processing during the call, while the test owns the returned result pointer after the call and releases it with os_free(result).

There is no persistent state, file output, database transaction, or network cleanup associated with this test.

## Failure modes covered by this module

The module has one positive-path test. Failures can indicate:

- a changed call sequence to os_random, GetRandomNoise, time, or getuname;
- a changed combination or ordering of the input material;
- a changed digest or serialization implementation;
- an unexpected result allocation or string representation; or
- a memory-management problem detected while freeing the result.

Null inputs, entropy-source failures, allocation failures, and malformed host identity data are outside this module's current coverage. They should be documented alongside the production implementation in [os_auth_enrollment_core](os_auth_enrollment_core.md) or covered by additional unit tests in the OS Auth test group.

## Relationship to neighboring tests

The enclosing OS Auth test family covers a wider surface:

- os_auth_test_auth_add — agent insertion behavior;
- os_auth_test_auth_parse — enrollment request parsing;
- os_auth_test_auth_validate — validation and replacement policy;
- os_auth_test_auth_key_request — external key-request handling;
- os_auth_test_authd_config — authd configuration parsing;
- os_auth_test_generate_cert — certificate generation and persistence;
- os_auth_test_ssl — SSL read behavior.

Those modules collectively exercise the enrollment daemon described in [os_auth](os_auth.md). os_auth_test_auth remains deliberately narrow so failures in password generation can be diagnosed independently from agent registration, certificate validation, or daemon networking.

## Source reference

- Test implementation: src/unit_tests/os_auth/test_auth.c
- Production declaration: src/os_auth/auth.h
- Parent behavior: [os_auth_enrollment_core](os_auth_enrollment_core.md)
- Cryptographic and key-management context: [os_crypto](os_crypto.md)
- Shared test wrappers: src/unit_tests/wrappers/wazuh/os_auth/ and src/unit_tests/wrappers/wazuh/shared/
