# `os_execd_test_win_execd` — Windows Active Response Execution Tests

## Introduction

`os_execd_test_win_execd` is the CMocka unit-test module for the Windows execution path of Wazuh’s Active Response execution daemon. It validates `ExecdRun()` using a synthetic `wfd_t` process channel and controlled wrappers for command lookup, Windows process creation, standard I/O, timeout handling, and logging.

The module tests execution outcomes rather than starting a real Windows process. Production responsibilities and timeout-list behavior are described in [os_execd.md](os_execd.md) and [os_execd_response_engine.md](os_execd_response_engine.md); this document focuses on the test harness and its behavioral contract.

## Scope and role

The suite verifies that an incoming Active Response JSON message is:

- parsed and mapped to a configured command;
- transformed into the Windows `wazuh-execd` message format;
- sent to the child process through its input stream;
- interpreted from the child response on its output stream;
- converted into `continue`, `abort`, or timeout-list behavior;
- rejected safely for malformed JSON, missing command names, process-launch failures, and output-read failures.

The test file is `src/unit_tests/os_execd/test_win_execd.c`. Its registered test cases are:

| Test | Behavior covered |
|---|---|
| `test_WinExecdRun_ok` | Successful command lookup, process execution, response parsing, and continuation. |
| `test_WinExecdRun_timeout_not_repeated` | A timed command is added to the timeout list when its key is new. |
| `test_WinExecdRun_timeout_repeated` | A repeated key causes an abort/update path instead of a duplicate timeout entry. |
| `test_WinExecdRun_wpopenv_err` | Windows process creation failure. |
| `test_WinExecdRun_fgets_err` | Missing or unreadable child response; no timeout entry is created. |
| `test_WinExecdRun_get_command_err` | Unknown Active Response command after configuration lookup. |
| `test_WinExecdRun_get_name_err` | Missing command name in an otherwise JSON message. |
| `test_WinExecdRun_json_err` | Invalid JSON input. |

## Architecture

```mermaid
graph TB
    Runner[main\ncmocka_run_group_tests] --> Setup[group_setup / group_teardown]
    Runner --> Cases[CMUnitTest registry]

    subgraph SUT[Production code under test]
        ExecdRun[ExecdRun\nshared Windows execution logic]
        Command[GetCommandbyName\nconfigured AR command lookup]
        Timeout[timeout_list\nOSList of timeout_data]
    end

    Cases --> ExecdRun
    ExecdRun --> Command
    ExecdRun --> Timeout

    subgraph Wrappers[Controlled test seams]
        Process[wpopenv / wpclose]
        IO[fprintf / fgets]
        Config[ReadExecConfig]
        Logs[debug and error logging]
    end

    ExecdRun -. wrapped .-> Process
    ExecdRun -. wrapped .-> IO
    Command -. wrapped .-> Config
    ExecdRun -. wrapped .-> Logs

    style ExecdRun fill:#4B8BBE,color:#fff
    style Cases fill:#f9d77e,stroke:#333,stroke-width:2px
```

The suite exercises the same execution function used by the daemon while substituting external effects. `wfd_t` supplies fake `file_in` and `file_out` streams, allowing the test to assert the exact JSON written to and read from the simulated Active Response process.

## Component relationships

```mermaid
classDiagram
    class CMUnitTest {
        +test_WinExecdRun_ok()
        +test_WinExecdRun_timeout_not_repeated()
        +test_WinExecdRun_timeout_repeated()
        +test_WinExecdRun_wpopenv_err()
        +test_WinExecdRun_fgets_err()
        +test_WinExecdRun_get_command_err()
        +test_WinExecdRun_get_name_err()
        +test_WinExecdRun_json_err()
    }
    class group_setup {
        +test_mode = 1
    }
    class group_teardown {
        +test_mode = 0
    }
    class wfd_t {
        +FILE* file_in
        +FILE* file_out
    }
    class timeout_data {
        +char** command
        +char* rkey
        +time_t time_of_addition
        +int time_to_block
    }
    class ExecdRun {
        +parse JSON
        +resolve command
        +launch process
        +exchange messages
        +update timeout list
    }

    CMUnitTest --> group_setup : suite lifecycle
    CMUnitTest --> wfd_t : fixture
    CMUnitTest --> ExecdRun : invokes
    wfd_t --> ExecdRun : stdin/stdout handles
    ExecdRun --> timeout_data : add or refresh
    group_teardown --> timeout_data : FreeTimeoutList()
```

## Test fixture lifecycle

`group_setup()` enables global `test_mode`, and `group_teardown()` restores it. Each test receives a fresh `wfd_t` fixture:

1. `test_setup_file()` allocates `wfd_t`, assigns sentinel handles to `file_in` and `file_out`, and creates `timeout_list`.
2. `test_setup_file_timeout()` performs the same setup and additionally inserts `restart-wazuh10` with key `restart-wazuh-10.0.0.1-root`, timestamp `123456789`, and a ten-second timeout.
3. `test_teardown_file()` frees the fixture and calls `FreeTimeoutList()`.

The sentinel streams are intentional: all actual reads and writes are intercepted by the Windows stdio wrappers, so no host file descriptor is required.

```mermaid
sequenceDiagram
    participant C as CMocka
    participant G as group_setup
    participant F as test fixture
    participant T as Test case
    participant E as ExecdRun
    participant D as test_teardown_file

    C->>G: enable test_mode
    C->>F: allocate wfd_t and timeout_list
    F-->>T: fixture state
    T->>T: configure expect_* / will_return()
    T->>E: ExecdRun(message)
    E-->>T: wrapped process and I/O effects
    T->>D: teardown
    D->>D: free wfd_t and timeout list
    C->>G: disable test_mode
```

## Execution data flow

```mermaid
flowchart TD
    Input[Active Response JSON] --> Parse{JSON valid?}
    Parse -->|no| JsonError[Log error 1315\nreturn]
    Parse -->|yes| Name{command name present?}
    Name -->|no| NameError[Log error 1316\nreturn]
    Name -->|yes| Lookup[GetCommandbyName]
    Lookup -->|not found| CommandError[Reload config and retry lookup]
    CommandError -->|still missing| LookupError[Log error 1311\nreturn]
    Lookup -->|found| Build[Build execd message\norigin module = wazuh-execd\ncommand = add]
    Build --> Launch[wpopenv]
    Launch -->|failure| LaunchError[Log error 1317\nreturn]
    Launch -->|success| WriteAdd[fprintf child stdin\nadd message]
    WriteAdd --> Read[fgets child stdout]
    Read -->|failure| ReadError[Log debug message\nclose process\nreturn]
    Read -->|alert keys received| Timeout{Configured timeout > 0?}
    Timeout -->|no| Continue[Write continue message]
    Timeout -->|yes, key absent| Add[Add timeout_data]
    Add --> Continue
    Timeout -->|yes, key already present| Repeat[Write abort message\nrefresh existing timeout]
    Continue --> Close[wpclose]
    Repeat --> Close
```

The input message represents a request from an upstream producer such as `analysisd` or `remoted`; the production pipeline is covered by [active_response_module](active_response_module.md). The test uses a representative `syscheck` alert and verifies the complete serialized message, including the rewritten origin, command, program, and alert payload.

## Behavioral contracts

### Successful execution

`test_WinExecdRun_ok` establishes the normal contract:

- `restart-wazuh0` resolves to `restart-wazuh` with timeout `0`.
- The child receives an `add` message whose origin module is `wazuh-execd` and whose `program` is `restart-wazuh`.
- The child returns an Active Response `check_keys` response.
- The parent writes a matching `continue` message and closes the process with `wpclose`.

### Timeout and repeated-offender handling

The timeout fixture models an existing entry using `timeout_data`. A new key is added to `timeout_list`; an existing key is recognized as repeated, receives an `abort` message, and has its time-of-addition refreshed. The tests also assert the diagnostic distinction between adding a new command and updating an existing command.

```mermaid
stateDiagram-v2
    [*] --> NoTimeout: timeout = 0
    NoTimeout --> Continued: add -> child ack -> continue

    [*] --> NewTimedCommand: timeout > 0
    NewTimedCommand --> Added: key not in timeout_list
    Added --> Continued: continue written
    Added --> UndoPending: timeout_data stored
    UndoPending --> Removed: later timeout processing sends delete

    [*] --> RepeatedCommand: key already in timeout_list
    RepeatedCommand --> Aborted: abort written
    Aborted --> Refreshed: existing time_of_addition updated
    Refreshed --> UndoPending
```

### Failure behavior

The error tests verify early exits and resource-safe handling:

- invalid input is rejected before command execution;
- a missing command name produces an invalid-AR-command error;
- an unresolved command triggers a configuration reread, then an invalid-command error if still absent;
- `wpopenv` failure logs the launch error and does not perform child I/O;
- `fgets` failure logs that no alert keys were received and avoids timeout registration.

## Dependencies and isolation

```mermaid
graph LR
    Test[src/unit_tests/os_execd/test_win_execd.c] --> CMocka[cmocka]
    Test --> ExecdH[src/os_execd/execd.h]
    Test --> Shared[shared.h / list_op.h]
    Test --> Regex[os_regex.h]
    Test --> Net[os_net.h]
    Test -. wraps .-> ExecWrap[os_execd/exec_wrappers.h]
    Test -. wraps .-> StdioWrap[libc and Windows stdio wrappers]
    Test -. wraps .-> DebugWrap[debug_op_wrappers.h]
    Test -. wraps .-> ProcessWrap[exec_op_wrappers.h]
    ExecWrap --> Production[src/os_execd/exec.c and execd.c]
    StdioWrap --> Production
    DebugWrap --> Production
    ProcessWrap --> Production
```

The suite’s observable external seams are:

| Seam | Purpose in this module |
|---|---|
| `__wrap_GetCommandbyName` | Supplies command timeout and executable name. |
| `__wrap_ReadExecConfig` | Models configuration reload after lookup failure. |
| `__wrap_wpopenv` / `__wrap_wpclose` | Models Windows process creation and closure. |
| `wrap_fprintf` / `wrap_fgets` | Captures parent-to-child messages and supplies child responses. |
| `__wrap__mdebug1` / `__wrap__merror` | Verifies success, timeout, and failure diagnostics. |
| `FreeTimeoutList` and `OSList` | Isolates timeout state between tests. |

The wrappers are shared test infrastructure; their broader inventory is documented in [Unit_Test_Wrappers_&_Mocks.md](Unit_Test_Wrappers_&_Mocks.md). The sibling POSIX execution tests are part of [Unit_Tests_-_OS_Execd.md](Unit_Tests_-_OS_Execd.md), while the production execution engine is documented in [os_execd_response_engine.md](os_execd_response_engine.md).

## Process-flow summary

```mermaid
flowchart LR
    A[Register tests in main] --> B[Run group setup]
    B --> C[Create fixture]
    C --> D[Script wrapper expectations]
    D --> E[Call ExecdRun]
    E --> F{Expected branch}
    F -->|success| G[Assert JSON writes and close]
    F -->|failure| H[Assert error/debug log]
    F -->|timeout| I[Assert add, abort, or refresh]
    G --> J[Free fixture and timeout list]
    H --> J
    I --> J
    J --> K[Run next test / group teardown]
```

## Maintenance guidance

When changing Windows Active Response execution, update this suite when any of the following changes:

- the serialized `add`, `continue`, `abort`, or `delete` message shape;
- command lookup or configuration reload behavior;
- the child-process I/O contract;
- timeout-key construction or repeated-offender semantics;
- error codes or diagnostic messages;
- the ownership or cleanup requirements for `wfd_t` and `timeout_list`.

The exact string assertions are deliberate: they protect the protocol exchanged with Active Response scripts. If the protocol changes, update the expected JSON in the tests and the corresponding execution-engine documentation together.
