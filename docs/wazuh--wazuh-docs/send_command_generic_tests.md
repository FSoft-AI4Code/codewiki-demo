# `send_command_generic_tests`

## Introduction

`send_command_generic_tests` documents the CMocka tests for
`wm_agent_upgrade_send_command_to_agent`, the lowest-level manager-side command
transport used by the Wazuh agent-upgrade module. The tests verify connection
setup, command transmission, bounded response reception, response ownership,
and the observable behavior of connection and receive failures.

The tests are a focused part of
`src/unit_tests/wazuh_modules/agent_upgrade/test_wm_agent_upgrade_upgrades.c`.
The same source file also contains tests for WPK transfer and upgrade
orchestration; those broader concerns are covered by the
[agent-upgrade module documentation](agent_upgrade_module.md) and the shared
[upgrades test infrastructure documentation](agent_upgrade_upgrades_test_infrastructure.md).

## Scope and position

| Item | Description |
|---|---|
| Test module | `send_command_generic_tests` |
| Source file | `src/unit_tests/wazuh_modules/agent_upgrade/test_wm_agent_upgrade_upgrades.c` |
| Production symbol | `wm_agent_upgrade_send_command_to_agent` |
| Transport | `REMOTE_LOCAL_SOCK` via `OS_ConnectUnixDomain`, `OS_SendSecureTCP`, and `OS_RecvSecureTCP` |
| Test framework | CMocka, with wrapped networking and logging functions |
| Primary concern | Generic command/response transport, independent of a live agent or socket |

The helper is deliberately below the protocol-specific operations. Functions
such as lock-restart, open, write, close, SHA-1, and upgrade command senders
build the command text and interpret the response; this helper performs the
common local IPC exchange. The relationship is:

```mermaid
flowchart LR
    T[Generic command tests] --> H[wm_agent_upgrade_send_command_to_agent]
    H --> C[OS_ConnectUnixDomain]
    H --> S[OS_SendSecureTCP]
    H --> R[OS_RecvSecureTCP]
    H --> L[Debug and error logging]

    P[Protocol-specific send helpers] --> H
    P --> X[lock_restart / open / write / close / sha1 / upgrade]
```

## Architecture and dependencies

The test does not start `wazuh-modulesd`, connect to a real agent, or exercise
the remote agent command parser. Instead, CMocka wrappers replace the external
seams and make every call observable.

```mermaid
graph TD
    M[send_command_generic_tests]
    M --> F[CMocka expectations and state]
    M --> U[wm_agent_upgrade_upgrades.h]
    U --> I[wm_agent_upgrade_send_command_to_agent]

    I --> N[OS_ConnectUnixDomain]
    I --> TX[OS_SendSecureTCP]
    I --> RX[OS_RecvSecureTCP]
    I --> LG[__wrap__mtdebug2 / __wrap__mterror]

    N --> W[wrapped socket boundary]
    TX --> W
    RX --> W
    LG --> D[wrapped diagnostics]

    F -. controls returns .-> W
    F -. verifies arguments/order .-> W
    F -. verifies diagnostics .-> D
```

The important test dependencies are:

| Dependency | Role in the tests |
|---|---|
| `OS_ConnectUnixDomain` | Supplies a simulated socket or a connection error. |
| `OS_SendSecureTCP` | Verifies the exact command and byte count sent. |
| `OS_RecvSecureTCP` | Supplies the simulated response, receive error, or oversized-response condition. |
| `__wrap__mtdebug2` | Verifies send/receive diagnostic messages. |
| `__wrap__mterror` | Verifies error diagnostics for failed reception or connection. |
| `teardown_string` | Releases the heap response retained in CMocka state. |

For fixture allocation, global test mode, queue state, and suite registration,
see the linked [test infrastructure documentation](agent_upgrade_upgrades_test_infrastructure.md)
instead of duplicating those details here.

## Observable command contract

The tests establish the following behavioral contract:

1. Connect to `REMOTE_LOCAL_SOCK` as a stream socket with `OS_MAXSTR` as the
   maximum message size.
2. Send the caller-provided command with the caller-provided command length.
3. Receive into a bounded buffer using `OS_MAXSTR`.
4. Log the outgoing and incoming messages at debug level.
5. Return the received response as caller-owned memory when a response is
   available.
6. Return `NULL` when the socket connection cannot be established.

The tests intentionally pass the command length explicitly. They therefore
verify the transport call contract rather than treating the helper as a
string-validation routine.

## Test scenarios

The four tests are registered together in `main()` under the
`wm_agent_upgrade_send_command_to_agent` group.

| Test | Simulated condition | Main assertions |
|---|---|---|
| `test_wm_agent_upgrade_send_command_to_agent_ok` | Connect, send, and receive succeed. | Correct socket arguments, command bytes, response size, logs, and returned response. |
| `test_wm_agent_upgrade_send_command_to_agent_recv_error` | Receive returns `-1`. | Receive error `(8111)` is logged and a response object remains available to the caller. |
| `test_wm_agent_upgrade_send_command_to_agent_sockterr_error` | Receive returns `OS_SOCKTERR`. | Oversized-response error `(8112)` is logged and the supplied response is preserved. |
| `test_wm_agent_upgrade_send_command_to_agent_connect_error` | Connection returns `OS_SOCKTERR`. | Connection error `(8114)` is logged and the helper returns `NULL`. |

The success test uses the representative command
`Command to agent: restart agent now.` and response
`Command received OK.`. The exact strings are less important than the fact
that the wrapper expectations prove the command is sent unchanged and the
returned response is unchanged.

## Happy-path data flow

```mermaid
sequenceDiagram
    participant Test as CMocka test
    participant Helper as send_command_to_agent
    participant Socket as wrapped Unix socket
    participant Agent as simulated response

    Test->>Helper: command + command_size
    Helper->>Socket: connect(REMOTE_LOCAL_SOCK, SOCK_STREAM, OS_MAXSTR)
    Socket-->>Helper: socket descriptor
    Helper->>Socket: send(command, command_size)
    Socket-->>Helper: 0
    Helper->>Socket: receive(buffer, OS_MAXSTR)
    Socket-->>Agent: configured response
    Agent-->>Helper: response + response size
    Helper-->>Test: heap-owned response string
```

Every arrow crossing the socket boundary is checked with CMocka
`expect_*` assertions. `will_return` controls the simulated result, so the
test is deterministic and does not depend on timing, agent availability, or
network configuration.

## Error and process flow

```mermaid
flowchart TD
    A[Receive command and size] --> B{Connect succeeds?}
    B -- no --> C[Log 8114]
    C --> D[Return NULL]
    B -- yes --> E[Send command]
    E --> F[Receive response]
    F --> G{Receive result}
    G -- normal --> H[Log received message]
    H --> I[Return response]
    G -- -1 --> J[Log 8111 receive error]
    J --> K[Return available response]
    G -- OS_SOCKTERR --> L[Log 8112 response-size error]
    L --> K
```

The tests distinguish connection failure from receive failure. A connection
failure prevents a usable transport from existing and produces `NULL`; receive
failures are validated as response-side conditions and retain the response
buffer observed by the test. This distinction is important to callers that
map transport errors to stage-specific upgrade failures.

## Interaction with higher-level upgrade operations

The generic helper is reused by the staged WPK transfer path. Higher-level
tests verify the sequencing and error mapping for those stages; this module
only verifies the common command exchange.

```mermaid
flowchart LR
    A[wm_agent_upgrade_send_wpk_to_agent] --> B[send_lock_restart]
    B --> C[send_open]
    C --> D[send_write repeatedly]
    D --> E[send_close]
    E --> F[send_sha1]
    F --> G[send_upgrade]

    B --> H[generic command sender]
    C --> H
    D --> H
    E --> H
    F --> H
    G --> H
    H --> I[local remoted socket]
```

The resulting division of responsibility is:

- generic command tests: connection, send/receive calls, response ownership,
  and transport diagnostics;
- WPK transfer tests: package validation, chunking, retries, SHA-1 matching,
  platform installer selection, and stage-specific error codes;
- orchestration tests: task status updates, worker dispatch, semaphores, and
  queue preparation.

See the [agent upgrade module](agent_upgrade_module.md) for the end-to-end
manager/agent architecture and [agent upgrade manager](agent_upgrade_manager.md)
for the manager-side IPC and task entry points.

## Maintenance guidance

When changing this transport boundary, update these tests whenever any of the
following changes:

- socket path, socket type, or maximum receive size;
- command byte-count semantics;
- response allocation or ownership;
- error-code mapping or diagnostic message IDs;
- retry or response-size handling in the wrapped socket functions.

Keep the test focused on observable transport behavior. Changes to WPK
validation, file chunking, protocol selection, or task status should be
covered in the neighboring tests already registered in
`test_wm_agent_upgrade_upgrades.c` and documented through the linked
agent-upgrade pages.

