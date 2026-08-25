# select_agent_name_tests

select_agent_name_tests is the focused Cmocka test slice for the Wazuh DB global helper wdb_global_select_agent_name(). It verifies that an agent-name lookup follows the standard Wazuh DB access sequence: begin a transaction, obtain the cached statement, bind the agent ID, execute the query, and return the JSON result. Failures must produce a NULL result and the expected diagnostic.

The tests live in src/unit_tests/wazuh_db/test_wdb_global.c. The production helper belongs to the global Wazuh DB layer; database handles, transactions, statement caching, SQLite execution, and lifecycle are documented in [wazuh_db_engine.md](wazuh_db_engine.md), while surrounding global agent/group operations are documented in [wazuh_db_global.md](wazuh_db_global.md).

## Position in the system

The test is part of the Unit_Tests_-_Wazuh_DB family and specifically the test_wdb_global translation unit. It does not open a real database or exercise the daemon socket. Instead, it isolates the global lookup helper by replacing Wazuh DB, SQLite, and logging functions with Cmocka wrappers.

~~~mermaid
flowchart LR
    Caller[Wazuh DB caller] --> Global[wdb_global_select_agent_name]
    Global --> Engine[wazuh_db_engine]
    Engine --> SQLite[(SQLite global database)]
    Global --> JSON[cJSON result]
    Tests[select_agent_name_tests] -. isolates .-> Global
    Tests --> Mocks[Cmocka wrappers]
    Mocks -. emulate .-> Engine
    Mocks -. capture .-> Logs[debug/error logging]
~~~

## Test fixture and isolation

Every case is registered with cmocka_unit_test_setup_teardown() and uses the shared test_setup()/test_teardown() fixture from test_wdb_global.c.

Setup creates the minimum runtime state needed by the helper:

- a zeroed wdb_t object;
- the database identifier "global";
- a placeholder sqlite3 pointer storage location;
- a response buffer;
- initialized Wazuh DB configuration via wdb_init_conf().

Teardown releases those allocations and calls wdb_free_conf(). No persistent SQLite file is created, so the test remains deterministic and fast.

~~~mermaid
sequenceDiagram
    participant C as Cmocka case
    participant F as test_setup
    participant H as wdb_global_select_agent_name
    participant W as Wazuh/SQLite wrappers
    participant T as test_teardown
    C->>F: Create wdb_t and global configuration
    C->>H: Pass wdb and agent_id=1
    H->>W: begin transaction
    H->>W: cache statement
    H->>W: bind integer parameter 1
    H->>W: execute statement
    W-->>H: NULL or mocked cJSON pointer
    H-->>C: NULL or result pointer
    C->>T: Free fixture and configuration
~~~

## Function contract exercised

The tested operation accepts a wdb_t pointer and an integer agent ID, and returns a cJSON pointer representing the query result. The tests establish this observable contract:

| Stage | Expected operation | Failure result | Diagnostic asserted |
|---|---|---|---|
| Transaction | wdb_begin2() succeeds | NULL | Cannot begin transaction via debug logging |
| Statement preparation | wdb_stmt_cache() succeeds | NULL | Cannot cache statement via debug logging |
| Parameter binding | sqlite3_bind_int(..., 1, agent_id) returns SQLITE_OK | NULL | DB(global) sqlite3_bind_int(): ERROR MESSAGE |
| Query execution | wdb_exec_stmt() returns JSON | NULL | wdb_exec_stmt(): ERROR MESSAGE via debug logging |
| Successful lookup | wrapper returns a cJSON pointer | same pointer is returned | no error path |

The integer bind is explicitly checked for parameter index 1 and value 1 in all five cases. This protects both the query parameter order and caller-to-SQLite value propagation.

## Test cases

### test_wdb_global_select_agent_name_transaction_fail

Configures wdb_begin2() to return OS_INVALID. The helper must stop before statement caching, log Cannot begin transaction, and return NULL.

### test_wdb_global_select_agent_name_cache_fail

Allows the transaction to begin, then makes wdb_stmt_cache() return OS_INVALID. The helper must not bind or execute the query, must log Cannot cache statement, and must return NULL.

### test_wdb_global_select_agent_name_bind_fail

Makes statement caching succeed but returns SQLITE_ERROR from sqlite3_bind_int(). The wrapper supplies ERROR MESSAGE through sqlite3_errmsg(). The expected behavior is an error log containing the database ID (global) and a NULL result.

### test_wdb_global_select_agent_name_exec_fail

Makes transaction, statement caching, and binding succeed, then makes wdb_exec_stmt() return NULL. The helper reads the SQLite error text and logs wdb_exec_stmt(): ERROR MESSAGE; the result remains NULL.

### test_wdb_global_select_agent_name_success

Makes each prerequisite succeed and returns the sentinel pointer (cJSON *)1 from wdb_exec_stmt(). The test asserts pointer identity, demonstrating that the helper forwards the execution result rather than rebuilding or altering it.

## Failure short-circuiting

The cases collectively verify a strict left-to-right guard chain. A failure at one stage prevents all later stages from being called.

~~~mermaid
flowchart TD
    Start([select agent name]) --> Tx{wdb_begin2 succeeds?}
    Tx -- No --> TxErr[Log transaction error] --> Null1([Return NULL])
    Tx -- Yes --> Cache{wdb_stmt_cache succeeds?}
    Cache -- No --> CacheErr[Log cache error] --> Null2([Return NULL])
    Cache -- Yes --> Bind{sqlite3_bind_int succeeds?}
    Bind -- No --> BindErr[Log SQLite bind error] --> Null3([Return NULL])
    Bind -- Yes --> Exec{wdb_exec_stmt returns JSON?}
    Exec -- No --> ExecErr[Log SQLite execution error] --> Null4([Return NULL])
    Exec -- Yes --> Done([Return cJSON pointer])
~~~

## Dependencies and mocking boundary

The source includes the production Wazuh DB header and wrapper interfaces for Wazuh DB, SQLite, cJSON, debug/error logging, file/time helpers, POSIX functions, and cluster helpers. The five selected tests directly use only the Wazuh DB, SQLite error, and logging wrappers; the remaining includes support the larger test_wdb_global.c translation unit.

~~~mermaid
graph TD
    Test[test_wdb_global.c selected cases]
    Test --> Cmocka[cmocka]
    Test --> WDBH[wdb.h]
    Test --> WDBW[wdb_wrappers.h]
    Test --> SQLW[sqlite3_wrappers.h]
    Test --> DebugW[debug_op_wrappers.h]
    WDBW --> WDB[wdb_begin2, wdb_stmt_cache, wdb_exec_stmt]
    SQLW --> SQLite[sqlite3_bind_int, sqlite3_errmsg]
    DebugW --> Logging[mdebug1 / merror]
    WDB --> Result[cJSON result]
    SQLite --> Result
~~~

The wrappers are configured with Cmocka will_return(), expect_value(), and expect_string() primitives. This makes the test a behavioral contract for call ordering and error propagation, not a test of SQLite query contents or schema correctness.

## Data-flow view

~~~mermaid
flowchart LR
    ID[agent_id = 1] --> Bind[sqlite3_bind_int parameter 1]
    Bind --> Statement[Cached global-agent-name statement]
    Statement --> Execute[wdb_exec_stmt]
    Execute -->|success| JSON[cJSON query result]
    Execute -->|failure| Error[sqlite3_errmsg text]
    Error --> Log[Wazuh diagnostic log]
    JSON --> Return[Returned unchanged]
    Log --> Null[NULL returned]
~~~

## What is and is not covered

Covered:

- transaction-start failure;
- statement-cache failure;
- integer parameter-binding failure;
- query-execution failure;
- successful result forwarding;
- expected logging for each failure boundary;
- propagation of the global database identifier and agent ID.

Not covered by this module:

- SQL text, schema, indexes, or real SQLite behavior;
- missing-agent semantics when the database returns an empty result;
- malformed JSON returned by the database;
- transaction commit/rollback internals;
- Wazuh DB socket protocol or command dispatch;
- broader agent/group lifecycle behavior.

For those concerns, follow [wazuh_db_engine.md](wazuh_db_engine.md), [wazuh_db_global.md](wazuh_db_global.md), and [test_wdb_global_test_infrastructure.md](test_wdb_global_test_infrastructure.md).

## Maintenance guidance

When changing wdb_global_select_agent_name() or its statement plumbing, preserve the staged expectations unless the production contract intentionally changes:

1. Keep the bind index and agent ID expectation aligned with the SQL statement.
2. Add a wrapper return and logging assertion when introducing a new failure boundary.
3. Keep the success test pointer-based unless the helper intentionally transforms the JSON response.
4. Run the complete test_wdb_global binary because the selected cases share fixture state, wrappers, and configuration with the other global database tests.

## References

- [wazuh_db_engine.md](wazuh_db_engine.md) — wdb_t, transactions, statement caching, SQLite execution, and result handling.
- [wazuh_db_global.md](wazuh_db_global.md) — production global agent/group database operations.
- [test_wdb_global_test_infrastructure.md](test_wdb_global_test_infrastructure.md) — shared test fixture and wrapper infrastructure.
- [get_all_agents_tests.md](get_all_agents_tests.md) — adjacent paginated global-agent query tests using the same execution and size-limit conventions.
