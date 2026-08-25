# `wm_osquery_tests`

`wm_osquery_tests` is the CMocka unit-test module for the Wazuh osquery-monitor helper `wm_osquery_already_running`. The helper interprets text returned when `osqueryd` cannot start because another instance is active, extracting a process identifier when available and returning a stable fallback when the response only reports a busy pidfile.

The module is deliberately narrow: it validates the helper's null-input, recognized-message, fallback-message, and unmatched-message behavior. Runtime configuration and daemon orchestration are documented in [Wmodules_Config_osquery_monitor.md](Wmodules_Config_osquery_monitor.md) and [wazuh_modules_core_system_management_process_integrations.md](wazuh_modules_core_system_management_process_integrations.md).

## Scope and responsibilities

The test module covers one externally visible contract:

| Input condition | Expected result | Ownership |
| --- | --- | --- |
| `NULL` input | `NULL` | `wm_osquery_already_running` |
| `osqueryd (1000) is already running` | Newly allocated string containing `1000` | `wm_osquery_already_running` |
| `Pidfile::Error::Busy` | Newly allocated string containing `unknown` | `wm_osquery_already_running` |
| Any unrelated text, such as `No match` | `NULL` | `wm_osquery_already_running` |

The tests also verify ownership expectations for successful non-null results by calling `free(output)`. The null and unmatched cases do not require deallocation.

## Architecture

The module is a standalone unit-test executable. It declares the production helper locally and links against its implementation during the test build. CMocka supplies the test runner and assertions; standard C headers provide allocation and basic runtime support.

```mermaid
flowchart TB
    T[wm_osquery_tests executable]
    R[CMocka runner\ncmocka_run_group_tests]
    C[CMUnitTest table]
    A[Assertions\nassert_null\nassert_non_null\nassert_string_equal]
    H[wm_osquery_already_running\nproduction helper]
    M[Input message text]
    O[Returned PID or fallback\nheap-allocated string]

    T --> R
    R --> C
    C --> A
    C --> H
    M --> H
    H --> O
    O --> A
```

### Component relationships

`main` constructs a fixed array of four `CMUnitTest` entries. Each entry invokes the same production helper with a different input class. The helper is the only production component under test; there are no mocks, fixtures, setup callbacks, teardown callbacks, sockets, databases, or external services in this file.

```mermaid
classDiagram
    class main {
        +build CMUnitTest[]
        +cmocka_run_group_tests()
    }
    class CMUnitTest {
        +test_wm_osquery_already_running_null()
        +test_wm_osquery_already_running_pattern_1()
        +test_wm_osquery_already_running_pattern_2()
        +test_wm_osquery_already_running_no_match()
    }
    class wm_osquery_already_running {
        +char* wm_osquery_already_running(char* text)
    }
    class CMocka {
        +assert_null()
        +assert_non_null()
        +assert_string_equal()
        +cmocka_run_group_tests()
    }

    main --> CMUnitTest : registers
    main --> CMocka : runs
    CMUnitTest --> wm_osquery_already_running : calls
    CMUnitTest --> CMocka : asserts with
```

## Dependencies

### Direct source dependencies

The file includes:

- `<stdarg.h>`, `<stddef.h>`, and `<setjmp.h>` for CMocka-compatible test signatures and platform types.
- `<cmocka.h>` for `CMUnitTest`, test registration, assertions, and the runner.
- `<stdio.h>` and `<stdlib.h>` for standard C support and `free`.

The production function is introduced through the declaration:

```c
char * wm_osquery_already_running(char * text);
```

Its implementation belongs to the osquery-monitor module, represented in the module tree by `wm_osquery_monitor.c` and `wm_osquery_monitor.h`.

```mermaid
flowchart LR
    UT[src/unit_tests/wazuh_modules/osquery/test_wm_osquery_already_running.c]
    CM[cmocka.h / CMocka]
    C[C standard library\nstdlib, stdio, stdarg, stddef, setjmp]
    H[src/wazuh_modules/wm_osquery_monitor.c\nwm_osquery_already_running]
    CFG[src/config/wmodules-osquery-monitor.c\nconfiguration parsing]
    MOD[src/wazuh_modules/wm_osquery_monitor.h\nmodule data types]

    UT --> CM
    UT --> C
    UT --> H
    H --> MOD
    CFG -. runtime configuration context .-> H
```

The configuration parser and module lifecycle are contextual dependencies, not test-time calls. This distinction prevents the unit tests from being mistaken for end-to-end osquery-monitor coverage.

## Data flow

Each test passes a mutable C string, or a null pointer, into the helper. The helper classifies the message. A recognized PID message produces a heap-allocated PID string; the busy-pidfile message produces a heap-allocated `unknown` string; all other inputs produce `NULL`.

```mermaid
flowchart LR
    I[Input: char* text]
    N{Input is NULL?}
    P{Matches running PID\npattern?}
    B{Matches busy pidfile\npattern?}
    Z[Return NULL]
    PID[Allocate and return\n"1000"-style PID text]
    U[Allocate and return\n"unknown"]
    F[Caller test frees\nnon-null result]

    I --> N
    N -- yes --> Z
    N -- no --> P
    P -- yes --> PID
    P -- no --> B
    B -- yes --> U
    B -- no --> Z
    PID --> F
    U --> F
```

The test does not inspect allocation internals or the matching algorithm. It verifies the observable result and, for successful results, that the returned pointer can be released by the caller.

## Test interaction flow

The CMocka runner executes the registered test cases as a group. The source does not define per-test setup or teardown functions, so each case creates its own input and validates its own result.

```mermaid
sequenceDiagram
    participant Main as main
    participant Runner as CMocka runner
    participant Test as Test case
    participant Helper as wm_osquery_already_running
    participant Assert as CMocka assertions

    Main->>Runner: register four CMUnitTest entries
    Runner->>Test: invoke test case
    Test->>Helper: pass input text
    Helper-->>Test: PID, "unknown", or NULL
    Test->>Assert: validate returned value
    Test->>Test: free non-null result
    Runner-->>Main: group result / exit status
```

## Process flows

### Test execution lifecycle

```mermaid
flowchart TD
    S([Process starts]) --> B[Build CMUnitTest array]
    B --> R[Call cmocka_run_group_tests]
    R --> T1[test null input]
    T1 --> T2[test PID pattern]
    T2 --> T3[test busy pidfile pattern]
    T3 --> T4[test unrelated text]
    T4 --> E{All assertions pass?}
    E -- yes --> OK[Return CMocka success status]
    E -- no --> FAIL[Return non-zero test status]
    OK --> X([Process exits])
    FAIL --> X
```

### Classification behavior exercised by the tests

```mermaid
flowchart TD
    S[Receive text] --> Q{Text pointer valid?}
    Q -- no --> R1[Return NULL]
    Q -- yes --> R{Known osquery response?}
    R -- running with PID --> R2[Extract PID\nexample: 1000]
    R -- pidfile busy --> R3[Return fallback\nunknown]
    R -- no --> R1
```

## Test case details

### `test_wm_osquery_already_running_null`

Passes `NULL` and requires a null result. This establishes defensive behavior before any string matching or allocation occurs.

### `test_wm_osquery_already_running_pattern_1`

Passes `osqueryd (1000) is already running`. It requires a non-null result equal to `1000`, then frees the result. This is the positive extraction path.

### `test_wm_osquery_already_running_pattern_2`

Passes `Pidfile::Error::Busy`. It requires a non-null result equal to `unknown`, then frees the result. This represents an active-instance response without an exposed PID.

### `test_wm_osquery_already_running_no_match`

Passes `No match` and requires a null result. This ensures arbitrary daemon output is not treated as an already-running condition.

## Coverage boundaries

The module verifies the helper's result contract, but does not cover:

- osquery monitor configuration parsing;
- osquery pack and decorator handling;
- process spawning, pidfile creation, or lifecycle cleanup;
- repeated polling, scheduling, or daemon restart behavior;
- message forwarding through Wazuh queues;
- platform-specific process inspection.

For those concerns, follow the references in [Wmodules_Config_osquery_monitor.md](Wmodules_Config_osquery_monitor.md) and [wazuh_modules_core_system_management_process_integrations.md](wazuh_modules_core_system_management_process_integrations.md). Broader module-test conventions are covered by [test_infrastructure.md](test_infrastructure.md).

## Maintenance guidance

When changing `wm_osquery_already_running`, preserve the four-way contract unless the production API intentionally changes. A change to recognized response text should update the positive or fallback fixture and its expected output. If the function changes ownership semantics, update the explicit `free(output)` calls and document the new contract in this file. If matching becomes platform-dependent, add focused cases rather than expanding this unit into daemon or integration testing.

## Source reference

Primary test source: `src/unit_tests/wazuh_modules/osquery/test_wm_osquery_already_running.c`.

Tested production symbol: `wm_osquery_already_running(char * text)`.
