# `test_win_whodata_test_infrastructure`

## Introduction

`test_win_whodata_test_infrastructure` documents the shared CMocka fixtures and suite orchestration used by the Windows Who-Data tests in `src/unit_tests/syscheckd/whodata/test_win_whodata.c`. It is not production Who-Data logic. Its purpose is to create deterministic Syscheck state, model Windows security and Event Log responses, isolate operating-system effects behind wrappers, and restore global state between tests.

The behavioral scope of the complete test module is documented in [`test_win_whodata.md`](test_win_whodata.md). Production behavior is described in [`syscheckd_whodata.md`](syscheckd_whodata.md), while Windows-specific audit/SACL implementation details belong to the corresponding production source and its parent FIM documentation.

## Position in the test hierarchy

The infrastructure is a logical child of the [`test_win_whodata`](test_win_whodata.md) test module. It supports four CMocka execution groups: callback processing, state checking, directory-hash cleanup, and the general Windows Who-Data suite.

```mermaid
graph TD
    A[test_win_whodata.c] --> B[test_win_whodata_test_infrastructure]
    B --> C[whodata callback group]
    B --> D[state checker group]
    B --> E[wdata directory cleanup group]
    B --> F[general test group]

    C --> G[Windows Event Log wrappers]
    D --> H[ACL and audit-policy wrappers]
    E --> I[OSHash directory tracking]
    F --> J[architecture, paths, SACLs, policies, resources]

    C --> K[Windows Who-Data implementation]
    D --> K
    E --> K
    F --> K
```

## Responsibilities

| Infrastructure component | Responsibility |
|---|---|
| `CMUnitTest` arrays | Declare test cases and associate setup/teardown callbacks. |
| `test_group_setup` / `test_group_teardown` | Load the shared Syscheck configuration, enable wrapper test mode, and release global state. |
| `setup_whodata_callback_group` | Create the handle-event hash, configure a whodata-enabled directory, and establish callback prerequisites. |
| `setup_state_checker` | Create a monitored directory and whodata directory hash, and provide synthetic audit-policy data. |
| `setup_wdata_dirs_cleanup` | Isolate tests that exercise stale/non-stale directory entries in `syscheck.wdata.directories`. |
| `setup_policy_check` / `teardown_policy_check` | Allocate GUIDs, audit-policy arrays, and category metadata used by policy validation tests. |
| Specialized teardown helpers | Free event objects, path/device arrays, policy structures, hash tables, and reset `errno` or global flags. |
| `main` | Run all groups in a defined order and return the accumulated CMocka status. |

## Fixture lifecycle

The test file uses process-wide `syscheck` state because the production code also uses the global Syscheck configuration. Setups therefore establish only the state needed by a group, and teardowns explicitly rebuild or clear shared containers before another group runs.

```mermaid
sequenceDiagram
    participant M as main
    participant C as CMocka group runner
    participant S as group setup
    participant G as global syscheck state
    participant T as test case
    participant D as group/test teardown

    M->>C: cmocka_run_group_tests(...)
    C->>S: initialize fixtures
    S->>G: load config / create lists and hashes
    S->>G: install synthetic directory and policy state
    C->>T: execute test
    T->>G: call production Windows Who-Data function
    T-->>C: assert return values, state, logs, wrapper calls
    C->>D: teardown
    D->>G: free hashes, lists, strings, event data
    D->>G: reset flags and global pointers
```

### General group

`test_group_setup` expects the Syscheck configuration parser to read `../test_syscheck.conf`. It configures the ignore and no-diff regular expressions, sets `test_mode`, initializes the event-buffer size, and establishes the lock expectations required by configuration and cleanup code.

`test_group_teardown` disables test mode and delegates to `syscheck_teardown`. The teardown frees whodata handle/directory hashes, volume-device arrays, the configured directory list, and the broader `syscheck` configuration before clearing pointers that production cleanup may otherwise retain.

### Callback group

`setup_whodata_callback_group` creates `syscheck.wdata.directories`, assigns `free` as its data destructor, creates a configured `c:\windows` directory, enables the full FIM metadata option set plus `WHODATA_ACTIVE`, and marks the directory as `WD_CHECK_WHODATA`.

This fixture supports event IDs 4656, 4663, 4658, and 4719. The tests mutate recursion depth, monitoring status, scan state, and hash contents; `teardown_whodata_callback_group` restores the common Syscheck state and re-enables hash insertion checks.

### State-checker group

`setup_state_checker` creates a `c:\a\path` whodata directory with existence and directory-type status, allocates the whodata directory hash, and attaches synthetic policy metadata. The tests then model file deletion, directory re-addition, invalid/valid SACLs, policy mismatch, and fallback from whodata to realtime monitoring.

`teardown_state_checker` releases policy metadata and the complete Syscheck fixture. Additional teardown logic recreates directory entries when individual tests intentionally modify global status bits.

### Directory-cleanup group

`setup_wdata_dirs_cleanup` creates only the directory hash and policy fixture. Tests insert timestamped `whodata_directory` records using real hash operations, then verify that `state_checker` preserves current entries and removes stale entries. The hash is destroyed and recreated after tests so the next case starts empty.

## Dependency and wrapper architecture

The infrastructure calls the real Windows Who-Data functions but replaces external effects with wrapper functions. CMocka expectations determine return values, output buffers, error codes, and required call ordering.

```mermaid
graph LR
    T[test_win_whodata.c fixtures] --> W[Windows Who-Data functions]
    T --> E[CMocka expectations]

    W --> WIN[Windows API wrappers\nRegistry / ACL / token / Event Log / volumes]
    W --> SYS[Syscheck wrappers\nconfiguration / DB / FIM / hash / MQ]
    W --> LIB[Shared-library wrappers\nfilesystem / strings / memory / logging]
    W --> MOD[Module execution wrappers\nwm_exec / auditpol]

    E -. controls .-> WIN
    E -. controls .-> SYS
    E -. controls .-> LIB
    E -. controls .-> MOD
    W --> STATE[syscheck global state]
```

The included wrapper families cover:

- Windows Event Log calls such as `EvtRender`, `EvtSubscribe`, `EvtCreateRenderContext`, and `EvtClose`;
- registry and volume discovery calls used for architecture and device-path handling;
- token privilege and ACL calls such as `OpenProcessToken`, `LookupPrivilegeValue`, `AdjustTokenPrivileges`, `GetNamedSecurityInfo`, `SetNamedSecurityInfo`, `GetAce`, `AddAce`, and `DeleteAce`;
- Wazuh hash, filesystem, string, random, message-queue, logging, configuration, and FIM operations;
- `auditpol` backup/restore through the module execution wrapper.

This boundary prevents tests from depending on the host Windows installation, real Security-channel events, actual ACLs, or real audit policy files.

## Data model established by the fixtures

```mermaid
classDiagram
    class syscheck_config {
        +directory_t* directories
        +whodata wdata
        +test_mode
    }
    class directory_t {
        +path
        +options
        +recursion_level
        +dirs_status
    }
    class whodata {
        +OSHash* fd
        +OSHash* directories
        +char** drive
        +char** device
    }
    class whodata_evt {
        +path
        +user_name
        +process_name
        +process_id
        +user_id
        +mask
        +event_time
        +scan_directory
    }
    class policy_info {
        +category_guid
        +subcategory_guid1
        +subcategory_guid2
        +audit_event_info
        +paudit_policy
    }

    syscheck_config --> directory_t : configured list
    syscheck_config --> whodata : global runtime state
    whodata --> whodata_evt : handle hash values
    state_checker_tests --> policy_info : CMocka state
```

The central fixture is the `syscheck` global. `directory_t` entries provide monitoring options, recursion limits, path identity, and status bits. `syscheck.wdata.fd` correlates Windows handle IDs with `whodata_evt` objects, while `syscheck.wdata.directories` tracks directories awaiting or requiring scans. `policy_info` is test-only state that supplies the GUID and audit-policy arrays expected by `policy_check` and `state_checker`.

## Execution and behavioral flows

### Suite execution

```mermaid
flowchart TD
    A[main] --> B[callback tests]
    B --> C[setup_whodata_callback_group]
    C --> D[run callback cases]
    D --> E[teardown_whodata_callback_group]
    E --> F[state checker tests]
    F --> G[setup_state_checker]
    G --> H[run state cases]
    H --> I[teardown_state_checker]
    I --> J[directory cleanup tests]
    J --> K[setup_wdata_dirs_cleanup]
    K --> L[run stale-entry cases]
    L --> M[recreate clean hash]
    M --> N[general tests]
    N --> O[test_group_setup]
    O --> P[run SACL, policy, parsing, startup, utility tests]
    P --> Q[test_group_teardown]
    Q --> R[return accumulated status]
```

### Callback fixture data flow

```mermaid
flowchart LR
    A[synthetic EVT_VARIANT array] --> B[whodata_event_render]
    B --> C[extract event ID / handle ID / access mask]
    C --> D[whodata_event_parse]
    D --> E[normalize UTF-16 path and identity fields]
    E --> F[whodata_callback]
    F --> G{event ID}
    G -->|4656| H[add or replace handle entry]
    G -->|4663| I[update mask and directory scan state]
    G -->|4658| J[remove handle and emit FIM event]
    G -->|4719| K[mark audit-policy change]
    H --> L[syscheck.wdata.fd]
    I --> M[syscheck.wdata.directories / directory status]
    J --> N[fim_whodata_event wrapper]
```

The fixture deliberately uses event-field positions and Windows variant types expected by the implementation. Cases cover 32-bit and 64-bit handle/process representations, invalid types, missing identities, recycled paths, duplicate handles, non-monitored paths, recursion limits, and scan-abort states.

### SACL and audit-policy fixture flow

```mermaid
flowchart TD
    A[test invokes SACL or policy function] --> B[wrapper returns token / registry / ACL result]
    B --> C{operation succeeds?}
    C -- no --> D[assert error log and failure code]
    C -- yes --> E[construct or validate SACL]
    E --> F[temporarily enable SeSecurityPrivilege]
    F --> G[copy existing ACEs and Everyone SID]
    G --> H[set security information or restore it]
    H --> I[remove privilege and close token]
```

The SACL tests are intentionally granular: they inject failures at privilege lookup, token opening, security descriptor retrieval, ACL sizing, allocation, ACL initialization, ACE retrieval/copy/addition, and final security-info update. This makes cleanup behavior and the return-value contract observable at each boundary.

## Cleanup and isolation rules

The test source has several important isolation conventions:

1. Hash tables that own values receive `free` through `OSHash_SetFreeDataPointer`.
2. `syscheck_teardown` frees both whodata-specific state and the broader Syscheck configuration.
3. Tests that return allocated paths or rendered event buffers register a teardown such as `teardown_memblock` or `teardown_win_whodata_evt`.
4. Tests that mutate directory status, recursion, or options restore those fields in teardown callbacks.
5. `errno`, `test_mode`, `restore_policies`, `policies_checked`, and hash insertion controls are reset before later groups execute.
6. Windows handles returned by wrappers are explicitly closed in the expected call sequence.

These rules are necessary because a failure to reset one global hash or status bit can change the branch taken by later callback or state-checker tests.

## References

- [Windows Who-Data test module](test_win_whodata.md) — complete functional test coverage and production call relationships.
- [Syscheckd Whodata](syscheckd_whodata.md) — production Whodata responsibilities and relationships to FIM.
- [Syscheckd core](syscheckd_core.md) — FIM orchestration and runtime state consumed by the tests.
- [Syscheckd realtime](syscheckd_core_realtime.md) — fallback behavior when whodata monitoring is disabled.
- [FIM realtime Whodata tests](fim_realtime_whodata_tests.md) — related realtime/whodata behavioral coverage.
- [Syscheckd wrappers](syscheckd_wrappers.md) — shared wrapper boundary used by the test harness.
- [Syscheck configuration](Syscheck_Config.md) — `directory_t`, `whodata`, and status structures referenced by fixtures.

## Source location

```text
src/unit_tests/syscheckd/whodata/test_win_whodata.c
```

The infrastructure symbols documented here are the CMocka test descriptor type, `main`, `test_group_setup`, group-specific setup/teardown callbacks, policy fixture helpers, and cleanup helpers defined in that translation unit.
