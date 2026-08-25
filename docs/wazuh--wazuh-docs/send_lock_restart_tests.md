# `send_lock_restart_tests`

## Introduction

`send_lock_restart_tests` documents the focused CMocka tests for
`wm_agent_upgrade_send_lock_restart`. The tests verify the first command sent
to an agent during the Wazuh agent-upgrade protocol: locking agent restart
while the upgrade package is transferred and installed.

The module is a unit-test slice, not a production transport. Socket operations,
agent responses, response parsing, and logging are replaced by wrappers so the
tests assert the command contract deterministically.

## Scope and location

The tests are defined in:

`src/unit_tests/wazuh_modules/agent_upgrade/test_wm_agent_upgrade_upgrades.c`

The focused test cases are:

| Test | Scenario | Expected result |
| --- | --- | --- |
| `test_wm_agent_upgrade_send_lock_restart_ok` | The agent acknowledges `lock_restart` with `ok ` | Returns `0` |
| `test_wm_agent_upgrade_send_lock_restart_err` | The agent returns `err Could not restart agent` | Returns `OS_INVALID` |

These tests are registered directly in the CMocka suite under the
`wm_agent_upgrade_send_lock_restart` section. They do not use a per-test
fixture; the shared test-group setup only enables wrapper test mode.

## Role in the upgrade subsystem

The lock-restart operation is the first phase of the package-transfer path.
The broader upgrade orchestration, task lifecycle, and command family are
documented in [agent_upgrade_upgrades_test_infrastructure.md](agent_upgrade_upgrades_test_infrastructure.md),
[agent_upgrade_tasks_callbacks.md](agent_upgrade_tasks_callbacks.md),
[agent_upgrade_commands.md](agent_upgrade_commands.md), and
[agent_upgrade_module.md](agent_upgrade_module.md).

```mermaid
flowchart LR
    Task[Upgrade task] --> Package[Send WPK to agent]
    Package --> Lock[wm_agent_upgrade_send_lock_restart]
    Lock --> Open[Open remote package file]
    Open --> Write[Write package chunks]
    Write --> Close[Close remote file]
    Close --> Hash[Verify SHA-1]
    Hash --> Run[Run upgrade installer]
```

The focused module validates only `Lock`; the neighboring phases are tested
elsewhere in the same source file and should not be inferred from these two
cases.

## Architecture and component relationships

The subject under test formats the agent command and delegates transport to
the generic agent-upgrade command helper. The helper connects to the manager's
local remoted socket, sends the command, receives one response, and passes the
response to the agent-upgrade response parser.

```mermaid
flowchart TB
    Runner[CMocka runner]
    Tests[Two lock-restart tests]
    Subject[wm_agent_upgrade_send_lock_restart]
    Command[wm_agent_upgrade_send_command_to_agent]
    Connect[OS_ConnectUnixDomain wrapper]
    Send[OS_SendSecureTCP wrapper]
    Receive[OS_RecvSecureTCP wrapper]
    Parse[wm_agent_upgrade_parse_agent_response wrapper]
    Agent[Agent/remoted endpoint]

    Runner --> Tests
    Tests --> Subject
    Subject --> Command
    Command --> Connect
    Command --> Send
    Command --> Receive
    Receive -. simulated response .-> Agent
    Command --> Parse
    Parse --> Subject

    Connect:::mock
    Send:::mock
    Receive:::mock
    Parse:::mock
    classDef mock fill:#fff3cd,stroke:#b8860b,color:#5b4500
```

In the unit-test process, the four wrapper nodes are mocks. No Unix-domain
socket is opened and no live agent is contacted.

## Dependencies

| Dependency | Function in this module | Related documentation |
| --- | --- | --- |
| `wm_agent_upgrade_upgrades.h` | Declares the upgrade command behavior under test | [agent_upgrade_upgrades_test_infrastructure.md](agent_upgrade_upgrades_test_infrastructure.md) |
| `wm_agent_upgrade_tasks.h` | Supplies adjacent upgrade task definitions used by the containing test translation unit | [agent_upgrade_tasks_callbacks.md](agent_upgrade_tasks_callbacks.md) |
| `os_net_wrappers` | Mocks connect, send, and receive calls | [os_net.md](os_net.md) |
| `wm_agent_upgrade_wrappers` | Mocks response parsing and upgrade helpers | [agent_upgrade_upgrades_test_infrastructure.md](agent_upgrade_upgrades_test_infrastructure.md) |
| Shared/debug wrappers | Capture logging and common Wazuh behavior | [test_infrastructure.md](test_infrastructure.md) |
| CMocka | Provides test registration, expectations, and assertions | [test_infrastructure.md](test_infrastructure.md) |
| `REMOTE_LOCAL_SOCK`, `SOCK_STREAM`, `OS_MAXSTR` | Define the expected local transport, socket type, and receive bound | [os_net.md](os_net.md) |

```mermaid
graph TD
    T[send_lock_restart_tests]
    T --> C[wm_agent_upgrade_upgrades.h]
    T --> N[os_net wrappers]
    T --> W[agent-upgrade wrappers]
    T --> D[debug/common wrappers]
    T --> M[CMocka]
    C --> H[agent-upgrade command helper]
    H --> S[REMOTE_LOCAL_SOCK]
    H --> P[agent response parser]
```

## Command contract

For agent ID `28`, both tests require the exact command:

```text
028 com lock_restart -1
```

The test therefore documents these behavioral requirements:

1. The numeric agent ID is rendered as a three-character, zero-padded field.
2. The command uses the `com` agent-command namespace.
3. The command operation is `lock_restart`.
4. The command argument is `-1`.
5. The command is sent through `REMOTE_LOCAL_SOCK` as a stream socket.
6. The receive operation is bounded by `OS_MAXSTR`.
7. The parsed agent response status is returned to the caller.

The tests also assert the debug messages emitted around transport:

```text
(8165): Sending message to agent: '028 com lock_restart -1'
(8166): Receiving message from agent: 'ok '
```

## Data flow

```mermaid
sequenceDiagram
    participant T as Test
    participant L as send_lock_restart(28)
    participant C as Command helper
    participant S as Socket wrappers
    participant P as Response parser

    T->>L: invoke with agent_id=28
    L->>C: command = "028 com lock_restart -1"
    C->>S: connect(REMOTE_LOCAL_SOCK, SOCK_STREAM, OS_MAXSTR)
    C->>S: send(command)
    S-->>C: send status = 0
    C->>S: receive(OS_MAXSTR)
    S-->>C: agent response
    C->>P: parse(agent response)
    P-->>L: status
    L-->>T: return status
```

The success case injects `ok ` and makes the parser return `0`. The error case
injects `err Could not restart agent` and makes the parser return `OS_INVALID`.

## Process flows

### Successful acknowledgment

```mermaid
flowchart TD
    A[Call with agent ID 28] --> B[Format 028 com lock_restart -1]
    B --> C[Connect to REMOTE_LOCAL_SOCK]
    C --> D[Send command]
    D --> E[Receive "ok "]
    E --> F[Parser returns 0]
    F --> G[Test asserts return value is 0]
```

### Agent-level failure

```mermaid
flowchart TD
    A[Call with agent ID 28] --> B[Format 028 com lock_restart -1]
    B --> C[Connect and send successfully]
    C --> D[Receive "err Could not restart agent"]
    D --> E[Parser returns OS_INVALID]
    E --> F[Subject propagates OS_INVALID]
    F --> G[Test asserts failure result]
```

Transport failures are intentionally outside this module's focused contract.
They are covered by the neighboring
`wm_agent_upgrade_send_command_to_agent` tests, which exercise connect, send,
and receive failures independently.

## Interaction and assertion matrix

| Stage | Expected interaction | Why it matters |
| --- | --- | --- |
| Formatting | `28` becomes `028` | The agent protocol expects a fixed-width ID prefix |
| Connection | `OS_ConnectUnixDomain(REMOTE_LOCAL_SOCK, SOCK_STREAM, OS_MAXSTR)` | Confirms the manager-side local transport is selected |
| Send | Exact command and `strlen(command)` | Prevents protocol drift and incorrect payload sizing |
| Receive | `OS_RecvSecureTCP(..., OS_MAXSTR)` | Confirms the standard response bound |
| Logging | Send and receive debug records | Preserves operational traceability |
| Parsing | Parser receives the exact response string | Separates protocol interpretation from transport |
| Return | Parser status is returned unchanged | Makes agent acknowledgment/failure visible to upgrade orchestration |

## Maintenance guidance

Update this module and its expectations together when changing any of the
following:

- command formatting or the `lock_restart` protocol token;
- socket path, socket type, or receive-size constants;
- response prefixes (`ok ` / `err `) or parser return codes;
- debug message identifiers or wording;
- the generic command helper's call order.

If the generic transport changes, update the generic command-helper tests and
the [os_net.md](os_net.md) reference as well. If the lock-restart operation is
removed from the package-transfer sequence, update the orchestration
documentation and the end-to-end upgrade tests rather than retaining this
unit-test contract unchanged.

## Source map

| Source | Relevant symbols |
| --- | --- |
| `src/unit_tests/wazuh_modules/agent_upgrade/test_wm_agent_upgrade_upgrades.c` | `test_wm_agent_upgrade_send_lock_restart_ok`, `test_wm_agent_upgrade_send_lock_restart_err` |
| `src/wazuh_modules/agent_upgrade/manager/wm_agent_upgrade_upgrades.h` | `wm_agent_upgrade_send_lock_restart`, command-helper declarations |
| `src/unit_tests/wrappers/wazuh/os_net/os_net_wrappers.c` | Mocked socket connection, send, and receive boundaries |
| `src/unit_tests/wrappers/wazuh/wazuh_modules/wm_agent_upgrade_wrappers.c` | Mocked response parser and upgrade-specific collaborators |

