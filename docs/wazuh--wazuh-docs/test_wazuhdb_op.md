# `test_wazuhdb_op`

`test_wazuhdb_op` is the CMocka unit-test module for the native Wazuh DB protocol client declared in `src/headers/wazuhdb_op.h`. It verifies that a caller can send text commands to `wazuh-db` through the local Unix socket, receive bounded responses, classify `ok` and `err` statuses, and reject an unknown DB component name.

The test source is [`src/unit_tests/shared/test_wazuhdb_op.c`](https://github.com/wazuh/wazuh/blob/master/src/unit_tests/shared/test_wazuhdb_op.c). The production protocol implementation is covered in [shared_lib_networking](shared_lib_networking.md); the server-side command routing is documented in [wazuh_db_command_parser](wazuh_db_command_parser.md).

## Purpose and system position

The module protects the narrow boundary between native Wazuh processes and the `wazuh-db` daemon. It does not test SQLite directly and does not start a real daemon. Instead, it isolates the client API from the network implementation with CMocka wrappers.

```mermaid
flowchart LR
    T["test_wazuhdb_op.c\nCMocka cases"] --> H["wazuhdb_op.h\nwdbc_query_ex\nwdbc_parse_result\nwdbc_validate_component"]
    H --> N["OS network abstraction\nUnix socket + secure TCP framing"]
    N --> S["wazuh-db local socket\nWDB_LOCAL_SOCK"]
    S --> D["wazuh-db daemon"]
    D --> P["wdb_parse()\ncommand dispatch"]
    P --> DB["SQLite-backed domain handlers"]
```

## Architecture

| Component | Responsibility |
|---|---|
| `CMUnitTest` | CMocka test descriptor used by the registration table. |
| `main` | Registers five tests and returns `cmocka_run_group_tests()` status. |
| `test_ok_query` | Exercises an agent syscheck-save command and expects an `ok` response. |
| `test_ok2_query` | Exercises an agent syscheck-delete command and expects an `ok` response. |
| `test_okmsg_query` | Exercises an agent scan-info command and expects an `ok` response. |
| `test_err_query` | Sends an incomplete `agent 000` command and expects an `err` response. |
| `test_invalid_component` | Verifies that `random_component` maps to `WB_COMP_INVALID`. |
| `__wrap_OS_ConnectUnixDomain` | Mocks connection creation to `WDB_LOCAL_SOCK`. |
| `__wrap_OS_SendSecureTCP` | Mocks transmission and checks socket, message, and size. |
| `__wrap_OS_RecvSecureTCP` | Mocks the response payload and received byte count. |

```mermaid
graph TD
    Main["main()"] --> Tests["CMUnitTest[]"]
    Tests --> Q1["test_ok_query"]
    Tests --> Q2["test_ok2_query"]
    Tests --> Q3["test_okmsg_query"]
    Tests --> QE["test_err_query"]
    Tests --> VC["test_invalid_component"]
    Q1 --> Query["wdbc_query_ex"]
    Q2 --> Query
    Q3 --> Query
    QE --> Query
    Query --> Connect["__wrap_OS_ConnectUnixDomain"]
    Query --> Send["__wrap_OS_SendSecureTCP"]
    Query --> Recv["__wrap_OS_RecvSecureTCP"]
    Q1 --> Parse["wdbc_parse_result"]
    Q2 --> Parse
    Q3 --> Parse
    QE --> Parse
    VC --> Validate["wdbc_validate_component"]
```

## Tested protocol flow

Each query test follows the same interaction contract:

1. Start with `wdb_sock = -1` and a caller-owned response buffer of `OS_SIZE_6144` bytes.
2. Expect a stream Unix-domain connection to `WDB_LOCAL_SOCK`, with a maximum message size of `OS_SIZE_6144`.
3. Return the mocked descriptor `65555`.
4. Expect the exact query and `strlen(query) + 1` bytes sent through secure TCP framing.
5. Return a response (`"ok"` or `"err"`) and its byte count.
6. Assert that `wdbc_query_ex()` returns `0`.
7. Pass the response to `wdbc_parse_result()` and assert `WDBC_OK` or `WDBC_ERROR`.

```mermaid
sequenceDiagram
    participant C as Test case
    participant W as wdbc_query_ex
    participant Conn as __wrap_OS_ConnectUnixDomain
    participant Tx as __wrap_OS_SendSecureTCP
    participant Rx as __wrap_OS_RecvSecureTCP
    participant Parse as wdbc_parse_result

    C->>W: query, response, OS_SIZE_6144
    W->>Conn: WDB_LOCAL_SOCK, SOCK_STREAM, 6144
    Conn-->>W: socket 65555
    W->>Tx: query + NUL, strlen(query)+1
    Tx-->>W: success (0)
    W->>Rx: socket 65555, capacity 6144
    Rx-->>W: "ok" or "err", byte count
    W-->>C: return 0
    C->>Parse: response, &message
    Parse-->>C: WDBC_OK or WDBC_ERROR
```

## Test cases

### Successful queries

`test_ok_query` uses:

```text
agent 000 syscheck save file 0:0:0:0:0:0:0:0:0:0:0:0!0:0 /tmp/test.file
```

It represents a syscheck/FIM save operation. `test_ok2_query` uses `agent 000 syscheck delete /tmp/test.file`, covering a deletion command. `test_okmsg_query` uses `agent 000 syscheck scan_info_get start_scan`, covering a command whose result is primarily a status message. All three receive `ok` and must parse as `WDBC_OK`.

The tests validate the client-side wire contract, not whether the server actually performs the requested operation. Server interpretation belongs to [wazuh_db_command_parser](wazuh_db_command_parser.md), while FIM/syscheck persistence belongs to the relevant Wazuh DB modules.

### Error query

`test_err_query` sends the incomplete command `agent 000`. The mocked server returns `err`; transport still succeeds, so `wdbc_query_ex()` returns `0`, while `wdbc_parse_result()` returns `WDBC_ERROR`. This distinction is important: transport success and command success are separate outcomes.

```mermaid
flowchart TD
    Query["wdbc_query_ex"] --> Transport{"connect/send/receive succeed?"}
    Transport -->|no| TransportFail["non-zero transport result"]
    Transport -->|yes| Return["0"]
    Return --> Status{"response prefix"}
    Status -->|ok| OK["WDBC_OK"]
    Status -->|err| ERR["WDBC_ERROR"]
    Status -->|due / ignore / unknown| Other["other wdbc_result values\nnot covered by this file"]
```

### Component validation

`test_invalid_component` calls `wdbc_validate_component("random_component")` and expects `WB_COMP_INVALID`. The production header defines the accepted component categories for syscollector, syscheck, and FIM data, with `WB_COMP_INVALID` as the sentinel. Valid-component behavior is outside this test’s scope.

## Dependencies and boundaries

```mermaid
graph LR
    Test["test_wazuhdb_op.c"] --> CMocka["cmocka.h"]
    Test --> Std["stdlib / string / stdio"]
    Test --> Header["wazuhdb_op.h"]
    Header --> Shared["shared.h"]
    Header --> Net["os_net.h"]
    Test --> CommonWrap["wrappers/common.h"]
    Test --> NetWrap["wrappers/wazuh/os_net/os_net_wrappers.h"]
    NetWrap -.mocks.-> Net
    Header --> Impl["src/shared/wazuhdb_op.c"]
    Impl --> Socket["src/shared/os_net/os_net.c"]
    Socket --> Daemon["wazuh-db"]
```

The test intentionally mocks the socket boundary. It therefore avoids filesystem databases, daemon startup, timing variability, and real IPC. See [shared_lib_networking](shared_lib_networking.md) for connection retry, framing, reconnect, result parsing, and socket ownership behavior that is broader than this unit test.

## Ownership and test isolation

- Query literals are string literals and are not freed.
- `response` is stack storage owned by each test.
- `message` points into the parsed response representation and is not independently freed by these cases.
- The mocked descriptor is controlled entirely by the wrapper expectations.
- CMocka verifies every expected call, argument, and return value, so an unexpected connection path or altered message size fails the test.

## Running the tests

The file is part of the native shared-library unit-test suite. Build the project’s unit tests using the repository’s normal build configuration, then run the generated `test_wazuhdb_op` binary or select the corresponding CTest target. The exact binary location is build-system dependent.

## Related documentation

- [shared_lib_networking](shared_lib_networking.md) — production `wazuhdb_op.c` protocol helpers and network abstractions.
- [wazuh_db_command_parser](wazuh_db_command_parser.md) — server-side parsing and dispatch of the commands sent by this test.
- [wazuh_db_daemon_core](wazuh_db_daemon_core.md) — daemon lifecycle and socket listener.
- [wazuh_db_engine](wazuh_db_engine.md) — SQLite handles, transactions, statement caching, and connection pools used after dispatch.
- [test_rootcheck_op](test_rootcheck_op.md) — another unit test exercising a higher-level helper that relies on the same Wazuh DB client boundary.
