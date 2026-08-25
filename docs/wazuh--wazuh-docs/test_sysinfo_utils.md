# `test_sysinfo_utils`

`test_sysinfo_utils` is the CMocka unit-test module for Wazuh's C-side system-information helper layer. It validates the lifecycle of `w_sysinfo_helpers_t`, forwarding of OS and process queries through dynamically loaded SysInfo entry points, extraction of an OS codename, and conversion of a SysInfo process list into a terminated array of child PIDs.

The test suite is located at `src/unit_tests/shared/test_sysinfo_utils.c`. The production contract is declared by `src/headers/sysinfo_utils.h`; the dynamically loaded provider is the C API exposed by the [data provider SysInfo core](data_provider_sysinfo_core.md). This document focuses on the test boundary and its expected behavior. Platform-specific inventory collection is documented in [data_provider_sysinfo_core.md](data_provider_sysinfo_core.md) and its linked submodules.

## Purpose and system position

The helper layer is an adapter between native C Wazuh code and the C++/C SysInfo provider. It loads the `sysinfo` module, resolves a small set of function symbols, invokes those symbols, and releases returned cJSON data through the provider's free callback. The tests isolate this adapter from the host operating system by mocking dynamic loading, cJSON access, and provider functions.

```mermaid
flowchart LR
    T["test_sysinfo_utils.c\nCMocka tests"] --> H["sysinfo_utils.h\nhelper contract"]
    H --> U["SysInfo helper layer\nw_sysinfo_* / w_get_process_childs"]
    U --> L["Dynamic loader\nso_get_module_handle / so_get_function_sym"]
    U --> P["sysinfo provider\nsysinfo_processes / sysinfo_os"]
    P --> D["data_provider_sysinfo_core\ncJSON results"]
    U --> C["Native Wazuh callers\nmodules, daemons, utilities"]
```

The module is a focused unit-test leaf under the shared-library tests. It is adjacent to broader system-information consumers such as the [syscollector module](syscollector_module.md), but it does not test inventory persistence, synchronization, or indexing.

## Architecture

```mermaid
graph TD
    Main["main()"] --> Group["cmocka_run_group_tests"]
    Group --> Setup["group_setup\ntest_mode = 1"]
    Group --> Cases["Registered CMUnitTest cases"]
    Cases --> Lifecycle["w_sysinfo_init / w_sysinfo_deinit"]
    Cases --> Access["w_sysinfo_get_os /\nw_sysinfo_get_processes"]
    Cases --> Children["w_get_process_childs"]
    Cases --> Codename["w_get_os_codename"]
    Lifecycle --> Loader["Dynamic-loader wrappers"]
    Access --> Provider["SysInfo function wrappers"]
    Children --> JSON["cJSON wrappers"]
    Codename --> JSON
    Cases --> Teardown["group_teardown\ntest_mode = 0"]
```

### Components

| Component | Responsibility |
|---|---|
| `CMUnitTest` | CMocka descriptors used to register each test case. |
| `group_setup` / `group_teardown` | Enable and restore Wazuh test mode around the suite. |
| `main` | Registers the test table and returns the CMocka group status. |
| `w_sysinfo_helpers_t` | Holds the loaded module handle, resolved process/OS functions, and provider result-free function. |
| `w_sysinfo_init` | Loads `sysinfo` and resolves `sysinfo_processes`, `sysinfo_os`, and `sysinfo_free_result`. |
| `w_sysinfo_deinit` | Releases the loaded module and clears helper fields. |
| `w_sysinfo_get_processes` / `w_sysinfo_get_os` | Validate helper state and forward requests to the provider. |
| `w_get_process_childs` | Filters provider process JSON by `ppid`, parses child `pid` values, and returns a zero-terminated PID array. |
| `w_get_os_codename` | Retrieves the provider OS object, reads its `codename` field, and returns a copied string. |
| Dynamic-loader and cJSON wrappers | Replace host-dependent behavior with scripted CMocka expectations. |

## Initialization and teardown contract

`w_sysinfo_init` is tested as an all-or-nothing symbol-resolution pipeline. It first requests the module named `sysinfo`, then resolves the process function, OS function, and result-free function. If any stage fails, the module is unloaded and the helper structure is cleared; the function returns `false`. A fully resolved helper retains the mocked handles and returns `true`.

```mermaid
sequenceDiagram
    participant Test as Test case
    participant H as w_sysinfo_init
    participant Loader as Dynamic loader
    participant S as sysinfo module

    Test->>H: initialize helper
    H->>Loader: load("sysinfo")
    alt module unavailable
        Loader-->>H: NULL
        H-->>Test: false
    else module loaded
        H->>Loader: resolve sysinfo_processes
        H->>Loader: resolve sysinfo_os
        H->>Loader: resolve sysinfo_free_result
        alt any symbol missing
            H->>Loader: unload(module)
            H-->>Test: false and cleared fields
        else all symbols found
            H-->>Test: true and populated helper
        end
    end
```

`w_sysinfo_deinit(NULL)` is rejected. For a valid helper, deinitialization calls the unload seam, clears `module`, `processes`, `os`, and `free_result`, and reports success. The tests therefore establish that callers can safely inspect a deinitialized structure and that partial initialization does not leave a usable-looking handle behind.

## Provider forwarding

`w_sysinfo_get_processes` and `w_sysinfo_get_os` are deliberately thin wrappers. They return `NULL` when the helper itself or the requested function pointer is missing. On success, they return the cJSON pointer and status supplied by the mocked provider call. Ownership remains with the provider result lifecycle; callers are expected to use `free_result` when finished.

```mermaid
flowchart TD
    Request["w_sysinfo_get_os/processes"] --> Valid{"helper and function set?"}
    Valid -->|no| Null["return NULL"]
    Valid -->|yes| Call["invoke sysinfo_os or\nsysinfo_processes"]
    Call --> Result["return cJSON result"]
    Result --> Free["free_result(result)"]
```

The provider's platform collection behavior—OS parsing, process enumeration, and cJSON conversion—is covered by [data_provider_sysinfo_core.md](data_provider_sysinfo_core.md). This suite only verifies the adapter's null checks and forwarding behavior.

## Child-process extraction

`w_get_process_childs` obtains one process-list cJSON document, walks its entries, and selects entries whose numeric `ppid` equals the requested parent PID. For each match it reads a numeric or string PID, converts it to `pid_t`, appends it to a dynamically grown array, and terminates the array with `0`.

```mermaid
flowchart TD
    Start["w_get_process_childs(helper, parent_pid, max_count)"] --> Guard{"helper and\nprocess callback valid?"}
    Guard -->|no| NoResult["return NULL"]
    Guard -->|yes| Fetch["request process cJSON\nfrom provider"]
    Fetch --> Iterate["iterate process objects"]
    Iterate --> PPID["read ppid"]
    PPID --> Match{"numeric ppid == parent_pid?"}
    Match -->|no / invalid| Next["skip entry"]
    Match -->|yes| PID["read and parse pid"]
    PID --> ValidPID{"valid numeric pid?"}
    ValidPID -->|no| Next
    ValidPID -->|yes| Limit{"max_count reached?"}
    Limit -->|yes| Finish["stop collecting"]
    Limit -->|no| Append["append PID; grow chunk if needed"]
    Append --> Next
    Next --> Iterate
    Iterate --> Finish
    Finish --> Release["free provider cJSON result"]
    Release --> Terminate["append zero sentinel and return array"]
```

The tests cover both invalid-input and allocation paths:

- null helper or null process callback returns `NULL`;
- empty process lists and no matching children return no result;
- missing or non-numeric `ppid`/`pid` fields are rejected;
- a mismatched parent is skipped;
- the first matching child allocates a new chunk;
- subsequent matches reuse the allocated chunk;
- the result is zero-terminated;
- `max_count` limits collection, while the zero sentinel remains present;
- a process list larger than the initial allocation exercises chunk growth.

The supplied test cases also exercise a process list with more children than the normal initial chunk, confirming that the returned array preserves encounter order (`100`, `200`, …) and remains terminated. The exact chunk size is an implementation detail and should not be treated as API behavior.

## OS codename extraction

`w_get_os_codename` calls the OS provider, looks up the `codename` property, obtains its string value, and returns an allocated copy. A null helper, provider failure, absent property, or absent string value produces `NULL`. The successful case returns the expected copied string and the test frees it explicitly.

```mermaid
sequenceDiagram
    participant T as Test
    participant H as w_get_os_codename
    participant P as sysinfo_os
    participant J as cJSON
    participant F as free_result

    T->>H: request codename
    H->>P: collect OS object
    P-->>H: cJSON OS result
    H->>J: get object item("codename")
    J-->>H: string value or NULL
    H->>F: release provider result
    H-->>T: allocated copy or NULL
```

## Test organization and execution

The suite has no per-test fixture state beyond local cJSON objects and helper structures. CMocka `expect_*` and `will_return` calls script every external result. Provider cJSON objects are released with the provider free callback inside the production path, while test-created cJSON objects and returned PID arrays are cleaned up by the test.

```mermaid
flowchart LR
    Process["test process starts"] --> Register["main registers tests"]
    Register --> Setup["group_setup"]
    Setup --> Run["CMocka invokes case"]
    Run --> Script["configure wrapper expectations"]
    Script --> SUT["call helper under test"]
    SUT --> Assert["assert return value, fields, and ordering"]
    Assert --> Cleanup["free local objects / arrays"]
    Cleanup --> More{"more cases?"}
    More -->|yes| Run
    More -->|no| Teardown["group_teardown and exit status"]
```

## Dependencies and boundaries

```mermaid
graph LR
    Test["test_sysinfo_utils"] --> CMocka["CMocka"]
    Test --> Header["sysinfo_utils.h"]
    Test --> SysInfoHeader["data_provider/include/sysInfo.h"]
    Test --> CJSON["cJSON wrappers"]
    Test --> Loader["dynamic loader wrappers"]
    Header --> Helper["SysInfo helper adapter"]
    Helper --> Provider["data_provider_sysinfo_core"]
    Provider --> Platform["Linux / Windows / Unix-family providers"]
    Helper -. consumed by .-> Consumers["native Wazuh daemons and modules"]
```

This module does not validate platform-specific system calls, package databases, network enumeration, database persistence, or inventory indexing. Follow the references below for those responsibilities:

- [data_provider_sysinfo_core.md](data_provider_sysinfo_core.md) — SysInfo C API bridge and platform implementations.
- [shared_lib.md](shared_lib.md) — common native shared-library infrastructure.
- [syscollector_module.md](syscollector_module.md) — inventory collection and synchronization consumers.
- [data_provider_testtool.md](data_provider_testtool.md) — manual SysInfo provider test tooling, where available.

## Coverage limits

The tests provide strong branch coverage for helper validation, loader failure cleanup, cJSON field failures, PID parsing, result ownership, and bounded collection. They do not establish:

- correctness of the real dynamic library path or ABI on each supported platform;
- correctness of the provider's process or OS data collection;
- behavior with malformed top-level JSON, duplicate fields, or embedded NUL strings;
- allocator failure during every possible reallocation;
- PID overflow beyond the platform's `pid_t` range;
- concurrency or repeated initialization from multiple threads.

Those concerns require provider-level, platform integration, or system tests in addition to this deterministic unit suite.
