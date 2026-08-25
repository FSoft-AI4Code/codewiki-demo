# test_wdb_task — Wazuh DB task-operation unit tests

test_wdb_task.c is the CMocka unit-test suite for the Wazuh DB task layer. It verifies the
SQLite-backed operations used to track asynchronous agent-upgrade work: task creation, lookup,
status updates, timeout processing, node cancellation, and historical cleanup.

The suite isolates production functions by replacing transactions, prepared-statement caching,
SQLite binding/stepping, timestamps, and diagnostics with wrappers. It therefore tests success and
failure contracts without opening a real tasks.db. See [task_module.md](task_module.md),
[wazuh_db_command_parser.md](wazuh_db_command_parser.md), and
[wazuh_db_engine.md](wazuh_db_engine.md) for the surrounding production modules.

## Position in the system

At runtime, the task manager and agent-upgrade components send task requests to wazuh-db. The task
parser dispatches them to task operations, which use the shared Wazuh DB engine and task SQLite
database. This file tests that persistence boundary.

~~~mermaid
flowchart TD
    API[API / framework] --> TM[Task manager]
    AU[Agent upgrade] --> TM
    TM -->|task protocol| P[wdb task parser]
    P --> T[Task operations]
    T --> E[Wazuh DB engine]
    E --> DB[(tasks.db)]
    U[test_wdb_task.c] -. tests .-> T
    U --> C[CMocka]
    U --> W[SQLite / WDB / logging wrappers]
    W -. controls .-> T
~~~

API routing, upgrade scheduling, and daemon lifecycle are intentionally outside this suite.

## Components and fixture

| Component | Role |
|---|---|
| test_wdb_task.c | Registers cases and defines wrapper expectations. |
| test_struct_t | Holds a minimal wdb_t and output buffer. |
| test_setup / test_teardown | Allocate and free the fake tasks database context. |
| wdb_task_* | Production functions under test. |
| WDB and SQLite wrappers | Script begin, cache, bind, step, column, time, and error results. |
| CMocka | Provides fixtures, expectations, assertions, and the runner. |

test_setup creates a wdb_t whose id is "tasks", allocates a fake sqlite3 pointer slot, and
allocates a 256-byte output buffer. No real connection or rows exist. Tests that receive dynamic
strings explicitly free them, documenting the ownership contract.

~~~mermaid
sequenceDiagram
    participant R as CMocka
    participant F as Fixture
    participant T as Test
    participant S as wdb_task function
    participant M as Wrappers
    R->>F: allocate fake wdb_t
    T->>M: install expectations
    T->>S: invoke operation
    S->>M: begin, cache, bind, step, time, log
    M-->>S: scripted result
    S-->>T: return value or fields
    T->>T: assert result and calls
~~~

## Task model and lifecycle

The tested record contains an agent id, manager node, module, command, task id, creation/update
times, status, and optional error text.

~~~mermaid
classDiagram
    class Task {
        +int task_id
        +int agent_id
        +string node
        +string module
        +string command
        +int create_time
        +int update_time
        +string status
        +string error
    }
~~~

~~~mermaid
stateDiagram-v2
    [*] --> Pending : insert
    Pending --> InProgress : processing
    InProgress --> Done : successful update
    InProgress --> Failed : failed update
    InProgress --> Timeout : timeout worker
    Pending --> [*] : cancellation / cleanup
    Done --> [*] : retention cleanup
    Failed --> [*] : retention cleanup
    Timeout --> [*] : retention cleanup
~~~

Direct status updates validate their input: the tests show that Timeout is rejected by
wdb_task_update_upgrade_task_status; timeout transitions use the dedicated timeout function.

## Operation coverage

### wdb_task_insert_task

Creates a pending task, binding agent id, node, module, command, creation time, and Pending. It
then performs a second lookup by agent id and returns the generated task id. Coverage includes
transaction-begin failure, first cache failure, insert-step failure, second lookup cache or step
failure, missing task id, and success.

~~~mermaid
flowchart LR
    I[insert task] --> B[begin]
    B --> C1[cache insert statement]
    C1 --> V[bind task fields]
    V --> S1[execute insert]
    S1 --> C2[cache lookup]
    C2 --> S2[read task id]
    S2 --> R[return id]
    B -. failure .-> E[OS_INVALID]
    C1 -. failure .-> E
    S1 -. failure .-> E
    C2 -. failure .-> E
    S2 -. no id .-> E
~~~

### Query operations

wdb_task_get_upgrade_task_status looks up an agent task, checks the requested node, and returns a
duplicated status string. Missing task ids are successful no-result cases. An old-node Pending
task is deleted as stale; delete cache or SQL failures are returned.

wdb_task_get_upgrade_task_by_agent_id returns the task id and allocated node, module, command,
status, error, update time, and last-update values. No task id yields OS_NOTFOUND; transaction,
cache, and SQL failures yield OS_INVALID.

~~~mermaid
flowchart TD
    Q[lookup by agent] --> ID{task id?}
    ID -->|no| NF[OS_NOTFOUND / empty result]
    ID -->|yes| N{node matches?}
    N -->|yes| R[return status or full record]
    N -->|no and Pending| D[delete stale task]
    D --> OK[success with no status]
    D -. failure .-> E[OS_INVALID]
    Q -. begin/cache/step failure .-> E
~~~

### Status updates

wdb_task_update_upgrade_task_status locates a task, validates task id, node, old status, and
requested status, then updates status, timestamp, optional error text, and task id. The success
case changes In progress to Done.

- Missing task id or incompatible old status returns OS_NOTFOUND.
- Unsupported status, such as Timeout, returns OS_INVALID before mutation.
- Transaction, cache, bind/step, and SQL failures return OS_INVALID.
- Valid changes return OS_SUCCESS.

### Timeout, cancellation, and retention

wdb_task_set_timeout_status scans In progress tasks and compares update time with the current time
and timeout interval. Expired tasks become Timeout; next_timeout receives the next wake-up
deadline. Tests cover expired and non-expired paths and preserve the caller's initial deadline on
failure.

wdb_task_cancel_upgrade_tasks handles upgrade work associated with a node using the current
timestamp. wdb_task_delete_old_entries removes records older than a supplied timestamp. Both
verify parameter binding, successful completion, transaction/cache failures, and SQL-step failures.

## Error-handling contract

~~~mermaid
flowchart TD
    Start[task operation] --> Tx[begin transaction]
    Tx -->|failure| I[OS_INVALID]
    Tx --> Cache[obtain prepared statement]
    Cache -->|failure| I
    Cache --> Bind[bind parameters]
    Bind --> Step[sqlite3_step]
    Step -->|expected row/done| Sem[apply task semantics]
    Step -->|SQL error| Log[log SQLite errmsg]
    Log --> I
    Sem -->|missing / incompatible| NF[OS_NOTFOUND or empty success]
    Sem -->|valid| S[OS_SUCCESS or task id]
~~~

The tests check both return codes and interactions. SQL failures must pass wrapped SQLite error
text to the Wazuh error logger; begin and statement-cache failures must produce a debug diagnostic.
This protects operation ordering as well as outcomes.

## Registration and execution

main registers 44 CMocka cases in seven operation groups:

| Group | Focus |
|---|---|
| wdb_task_delete_old_entries | Retention cutoff and SQL failures |
| wdb_task_set_timeout_status | Expired versus non-expired deadlines |
| wdb_task_insert_task | Bindings and generated task id |
| wdb_task_get_upgrade_task_status | Node-aware status and stale cleanup |
| wdb_task_update_upgrade_task_status | Validation and mutation |
| wdb_task_get_upgrade_task_by_agent_id | Full task retrieval |
| wdb_task_cancel_upgrade_tasks | Node-wide cancellation |

Run the suite through the repository's normal unit-test build. Because dependencies are mocked,
success does not validate live SQLite migrations or Unix-socket protocol behavior. Shared test
patterns are documented in [test_infrastructure.md](test_infrastructure.md).

## Related documentation

- [task_module.md](task_module.md) — task manager API and processing context.
- [wazuh_db_command_parser.md](wazuh_db_command_parser.md) — task actor parsing and dispatch.
- [wazuh_db_engine.md](wazuh_db_engine.md) — transactions, statement caching, pooling, and SQLite lifecycle.
- [wazuh_db.md](wazuh_db.md) — Wazuh DB architecture and daemon relationships.
- [test_infrastructure.md](test_infrastructure.md) — shared CMocka fixtures and wrappers.
