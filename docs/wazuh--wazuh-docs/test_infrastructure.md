# Test infrastructure for `logcollector/journal_log`

`test_infrastructure` is the deterministic CMocka test harness for the journald reader implementation. It is centered on [`src/unit_tests/logcollector/test_journal_log.c`](src/unit_tests/logcollector/test_journal_log.c) and verifies library loading, journal navigation, filtering, entry conversion, resource cleanup, and journal rotation handling without requiring a live systemd journal.

The module is a leaf of the logcollector journal-test area. Production behavior is described in [`logcollector_journald.md`](logcollector_journald.md); broader logcollector responsibilities are covered by [`logcollector.md`](logcollector.md) and [`logcollector_core.md`](logcollector_core.md). This document focuses on how the tests isolate and exercise that behavior.

## Scope and role

The test file supplies four related capabilities:

- A CMocka runner that registers the complete test inventory and provides suite setup and teardown.
- Linker/runtime wrappers for systemd journal functions, dynamic loading, filesystem access, time conversion, logging, JSON, and regular-expression seams.
- Scripted interaction tests for the journald implementation exposed by `journal_log.h`.
- Assertions for both normal results and failure contracts, including return values, null results, warnings, and cleanup calls.

It is not a production journald implementation and does not replace integration tests against the real `libsystemd` API. Its value is precise control over each external result and repeatable coverage of error branches.

## Architecture

```mermaid
flowchart TD
    Runner[cmocka_run_group_tests] --> Setup[group_setup]
    Setup --> Cases[Registered CMUnitTest cases]
    Cases --> SUT[Production journal_log functions]

    SUT --> JournalWrap[Wrapped sd_journal_* API]
    SUT --> LoaderWrap[dlopen / dlsym / dlclose wrappers]
    SUT --> FileWrap[fopen / getline / fclose / stat wrappers]
    SUT --> TimeWrap[gmtime_r / time-related wrappers]
    SUT --> DataWrap[cJSON / PCRE2 / logging wrappers]

    JournalWrap --> Expectations[CMocka expectations and scripted returns]
    LoaderWrap --> Expectations
    FileWrap --> Expectations
    TimeWrap --> Expectations
    DataWrap --> Expectations

    Cases --> Assertions[Assertions on values, calls, warnings, and ownership]
    Assertions --> Teardown[group_teardown]
```

The harness sits between the test cases and the production code. Tests call the real journald functions under test, while external dependencies are intercepted at the wrapper boundary. This preserves production control flow while removing environmental variability.

## Components

| Component | Location or symbol | Responsibility |
|---|---|---|
| Test suite | `test_journal_log.c` | Declares fixtures, wrappers, tests, and `main`. |
| Suite setup | `group_setup` | Enables test mode and disables live PCRE2 wrappers. |
| Suite teardown | `group_teardown` | Restores global test mode and re-enables PCRE2 wrappers. |
| Test runner | `main` | Builds the `CMUnitTest` array and invokes CMocka. |
| Journal API seams | `__wrap_sd_journal_*` | Script calls and out-parameters for journal open, seek, iteration, field access, timestamps, file descriptors, and rotation processing. |
| Loader seams | `__wrap_dlopen`, `__wrap_dlsym`, `__wrap_dlclose`, `__wrap_dlerror` | Simulate secure library discovery, symbol resolution, and unloading. |
| Filesystem seams | `__wrap_fopen`, `__wrap_getline`, `__wrap_fclose`, `__wrap_stat` | Model `/proc/self/maps`, library ownership, and path-discovery failures. |
| Conversion seams | `__wrap_gmtime_r`, JSON and logging wrappers | Control timestamp conversion, JSON construction, output formatting, and diagnostic assertions. |

The extracted `stat`, `timeval`, and `tm` components are test seams or C library data types rather than independent modules.

## Test execution lifecycle

```mermaid
sequenceDiagram
    participant C as CMocka
    participant S as Test case
    participant J as journal_log implementation
    participant W as Wrapped dependency

    C->>C: group_setup()
    C->>S: Invoke registered test
    S->>S: Configure expect_* and will_return()
    S->>J: Call function under test
    J->>W: Call journal, loader, file, or time dependency
    W-->>J: Return scripted value / out-parameter
    J-->>S: Return result or allocated entry
    S->>S: Assert result and expected calls
    S->>J: Free context, entry, or buffer
    C->>C: group_teardown()
```

Most tests that need a journal context repeat the same controlled initialization: load `libsystemd.so.0`, inspect a mocked `/proc/self/maps` line, verify root ownership, resolve the required symbols, and open the journal. The corresponding teardown verifies journal close and dynamic-library unload.

## Dependency and isolation model

```mermaid
graph LR
    T[test_journal_log.c]
    T --> C[CMocka]
    T --> H[journal_log.h]
    H --> P[journal_log.c]
    T --> L[Dynamic loader wrappers]
    T --> F[Filesystem wrappers]
    T --> J[Systemd journal wrappers]
    T --> X[Time / JSON / PCRE2 / logging wrappers]
    J --> E[Scripted CMocka values]
    L --> E
    F --> E
    X --> E
```

The tests validate the production implementation through its public or test-visible function contracts. They do not invoke actual journal sockets, `dlopen`, `/proc` parsing, or host-specific timestamp behavior. This makes branch-level tests reproducible, but it also means deployment and ABI compatibility still require higher-level testing.

## Mocking strategy

### Dynamic loading and library discovery

`w_journal_lib_init` is tested as a staged pipeline:

```mermaid
flowchart TD
    Start[w_journal_lib_init] --> Open[dlopen libsystemd.so.0]
    Open -->|failure| E1[Return failure and log]
    Open --> Maps[find_library_path via /proc/self/maps]
    Maps -->|failure| E2[Return failure]
    Maps --> Owner[stat library and require root ownership]
    Owner -->|failure| E3[Return failure]
    Owner --> Symbols[Resolve required sd_journal_* symbols]
    Symbols -->|failure| E4[Return failure]
    Symbols -->|success| Ready[Library interface ready]
```

Tests explicitly cover `dlopen` failure, map-file failure, non-root ownership, symbol-resolution failure, and successful initialization. The success path expects all journal symbols used by the implementation, so adding a new external symbol should be accompanied by a wrapper expectation and a failure-path test.

### Journal operations

The `__wrap_sd_journal_*` functions use CMocka return queues. Functions that write through pointers copy the scripted value into the supplied output, including journal timestamps, field payloads, enumerated entry data, cutoff timestamps, and realtime timestamps. This allows tests to distinguish:

- no entry (`0`), new entry (`1`), and rotation (`2`) results;
- successful field retrieval versus `-1` failure;
- valid `name=value` payloads versus malformed payloads;
- unchanged, changed, and rotated journal state.

### Other seams

- `fopen`, `getline`, `fclose`, and `stat` control `/proc/self/maps` parsing and ownership checks.
- `gmtime_r` controls valid and failed timestamp conversion.
- `isDebug` controls diagnostic-only filtering behavior.
- cJSON wrappers verify object creation, field insertion, printing, and deletion.
- PCRE2 wrappers are disabled for the suite so regex behavior can be tested without live wrapper side effects.
- Logging wrappers verify warnings and debug messages where failure behavior is observable.

## Functional coverage

| Area | Functions exercised | Representative scenarios |
|---|---|---|
| Ownership and symbol loading | `is_owned_by_root`, `load_and_validate_function`, `find_library_path`, `w_journal_lib_init` | Root/non-root files, `stat` failure, missing symbols, loader failure, successful symbol table creation. |
| Time conversion | `w_get_epoch_time`, `w_timestamp_to_string`, `w_timestamp_to_journalctl_since` | Valid timestamps, exact formatted output, failed `gmtime_r`. |
| Context lifecycle | `w_journal_context_create`, `w_journal_context_free`, `w_journal_context_update_timestamp` | Null arguments, open failure, timestamp failure fallback, close and unload. |
| Journal navigation | `w_journal_context_seek_most_recent`, `w_journal_context_seek_timestamp`, `w_journal_context_next_newest` | Tail seek failure, old/future timestamps, end of journal, timestamp updates, new entries. |
| Filtering | `w_journal_filter_apply`, `w_journal_context_next_newest_filtered` | Missing fields, ignored fields, malformed fields, empty values, regex match/non-match, debug logging. |
| JSON conversion | `entry_as_json`, `get_field_ptr` | Empty entries, malformed data, empty values, successful key/value extraction, cleanup after failure. |
| Syslog conversion | `create_plain_syslog`, `entry_as_syslog` | PID, system PID fallback, no PID, missing hostname/message, unknown tag, timestamp failure. |
| Entry abstraction | `w_journal_entry_dump`, `w_journal_entry_to_string` | JSON and syslog variants, invalid type, null input, failed conversion, serialized output. |
| Rotation detection | `w_journal_rotation_detected` | Null context, missing descriptor, no change, file change, rotation result. |

The test suite intentionally asserts the implementation’s conventions rather than assuming one universal return convention. For example, `0` can mean “no new entry” or successful completion depending on the function, while `1` represents a matching/new condition in several navigation and filtering paths.

## Key process flows

### Context initialization and cleanup

```mermaid
flowchart LR
    A[Create context] --> B[Initialize library]
    B --> C[Open journal]
    C --> D[Use context]
    D --> E[Close journal]
    E --> F[Unload libsystemd]
    F --> G[Free context]
    B -. failure .-> H[Return error]
    C -. failure .-> H
```

Tests verify that failure before ownership of a resource does not trigger an invalid cleanup, while successful paths always close the journal and unload the library.

### Navigation and filtering

```mermaid
flowchart TD
    N[Seek or request next entry] --> R[Wrapped sd_journal_* result]
    R -->|0| No[No usable new entry]
    R -->|1| Timestamp[Update entry timestamp]
    R -->|2 during process| Rot[Report journal rotation]
    Timestamp --> Filters{Filters supplied?}
    Filters -->|no| Accept[Return entry available]
    Filters -->|yes| Apply[Read field and apply regex]
    Apply -->|match| Accept
    Apply -->|no match| Continue[Continue iteration]
    Apply -->|data/parse error| Fail[Return failure or discard]
```

### Entry serialization

```mermaid
flowchart TD
    E[Current journal entry] --> Type{Requested type}
    Type -->|JSON| Fields[Enumerate name=value fields]
    Fields --> Obj[cJSON object]
    Obj --> JsonString[Unformatted JSON string]
    Type -->|Syslog| Required[Read hostname, identifier, message]
    Required --> Optional[Read SYSLOG_PID, then _PID fallback]
    Optional --> Date[Convert timestamp]
    Date --> SyslogString[Create plain syslog line]
    Required -. missing required data .-> Discard[Return null and log]
```

For syslog output, a missing identifier becomes `unknown`; PID is optional, and `_PID` is used when `SYSLOG_PID` is unavailable. Missing hostname, message, or timestamp causes the entry to be discarded.

## Maintainer guidance

When changing the journald implementation or adding a systemd call:

1. Add or update the corresponding wrapper in `test_journal_log.c`.
2. Add the symbol to the successful initialization expectations and test the resolution failure path if it changes initialization requirements.
3. Script every out-parameter explicitly; implicit mock values make failures order-dependent.
4. Preserve the resource pattern: successful contexts close the journal and unload the library, and allocated JSON/string/entry values are freed.
5. Keep setup and teardown global-state changes balanced, especially `test_mode` and PCRE2 wrapper enablement.
6. Add both the success case and the relevant null, malformed-input, dependency-failure, or cleanup case.

The repeated context bootstrap code is verbose but documents the exact external interactions required by each scenario. Refactoring it should retain the same expectation visibility and should not hide which dependency failure a test is exercising.

## Limitations

- The suite is primarily unit and interaction testing; it does not validate a real systemd journal, installed library ABI, permissions, or host journal rotation.
- Tests depend on linker wrapping and Linux-style `/proc/self/maps` behavior.
- CMocka return queues are order-sensitive. Adding a production call can invalidate several tests even when the final result is unchanged.
- The source file is the authoritative test inventory; this document groups cases by behavior instead of duplicating every test name.

## Related documentation

- [`logcollector_journald.md`](logcollector_journald.md) — production journald reader behavior.
- [`logcollector.md`](logcollector.md) — logcollector module context.
- [`logcollector_core.md`](logcollector_core.md) — shared logcollector lifecycle and infrastructure.
- [`Localfile_Config_journald.md`](Localfile_Config_journald.md) — journald configuration and configuration-facing behavior.
