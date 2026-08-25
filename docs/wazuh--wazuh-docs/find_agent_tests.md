# find_agent_tests

## Introduction

find_agent_tests is the focused CMocka test module for wdb_global_find_agent(), the global-database lookup used to locate an agent by its name and IP address. It verifies the standard Wazuh DB access sequence—begin a transaction, obtain the cached statement, bind the search parameters, execute the query, and return the resulting cJSON value—while propagating failures at each stage.

The module is a child test area of [test_wdb_global](test_wdb_global.md), in the Unit_Tests_-_Wazuh_DB suite. It tests the production global database layer described in [wazuh_db_global](wazuh_db_global.md), rather than implementing lookup logic itself.

## Purpose and scope

The tests establish the observable contract of:

~~~c
cJSON *wdb_global_find_agent(wdb_t *wdb, const char *name, const char *ip);
~~~

For the representative inputs name = "test_name" and ip = "0.0.0.0", the function must:

- return NULL when transaction initialization fails;
- return NULL when the prepared statement cannot be cached;
- bind the name, IP, and IP parameters in positions 1, 2, and 3;
- return NULL when any SQLite text binding fails;
- return NULL when statement execution fails;
- return the exact cJSON pointer returned by the database execution helper on success.

The third IP binding is intentional: the production SQL statement uses the supplied address more than once, and the test protects that parameter contract.

## Position in the system

The lookup is part of the manager's global agent registry. Other operations—agent registration, group assignment, and management workflows—can use the lookup to resolve an agent identity before performing a subsequent mutation. The test exercises only the server-side database function; callers and socket protocol parsing are documented in [wazuh_db_global](wazuh_db_global.md) and [wazuh_db_command_parser](wazuh_db_command_parser.md).

~~~mermaid
flowchart LR
    Caller["Wazuh DB caller<br/>parser or helper client"] --> Protocol["global lookup request"]
    Protocol --> Core["wdb_global_find_agent()"]
    Core --> Global[("global.db<br/>agent registry")]
    Core --> Result["cJSON agent result<br/>or NULL"]
    Result --> Caller
~~~

## Test architecture

The test uses a minimal synthetic wdb_t fixture and linker-wrapped dependencies. No real SQLite connection or global database file is opened.

~~~mermaid
graph TD
    Test["find_agent_tests<br/>7 CMocka cases"] --> Fixture["test_setup / test_teardown"]
    Fixture --> Context["wdb_t with id global<br/>output buffer and DB config"]
    Test --> SUT["wdb_global_find_agent()"]
    SUT --> Tx["wdb_begin2 wrapper"]
    SUT --> Cache["wdb_stmt_cache wrapper"]
    SUT --> Bind["sqlite3_bind_text wrapper"]
    SUT --> Exec["wdb_exec_stmt wrapper"]
    SUT --> Log["debug/error logging wrappers"]
    Tx --> Mock["CMocka scripted return values"]
    Cache --> Mock
    Bind --> Mock
    Exec --> Mock
    Log --> Mock
    Exec --> JSON["cJSON pointer/result"]
~~~

### Fixture lifecycle

Every test is registered with cmocka_unit_test_setup_teardown, so each case receives an isolated state object.

1. test_setup() allocates test_struct_t, a wdb_t, the "global" database identifier, a 256-byte output buffer, and storage for the SQLite handle slot. It calls wdb_init_conf().
2. The test scripts wrapper expectations and invokes wdb_global_find_agent().
3. test_teardown() frees the fixture allocations and calls wdb_free_conf().

~~~mermaid
sequenceDiagram
    participant C as CMocka
    participant S as test_setup
    participant T as find_agent test
    participant F as wdb_global_find_agent
    participant D as test_teardown
    C->>S: Create isolated fixture
    S->>S: Allocate wdb_t and synthetic DB slot
    S->>S: Set id = global
    S-->>T: Publish state
    T->>T: Configure wrappers
    T->>F: Find by name and IP
    F-->>T: cJSON pointer or NULL
    T->>T: Assert result and expected logs
    T->>D: Release state
    D->>D: Free allocations and DB configuration
~~~

## Dependency and interaction model

~~~mermaid
flowchart TD
    SUT["wdb_global_find_agent"] --> A["wdb_begin2<br/>transaction boundary"]
    SUT --> B["wdb_stmt_cache<br/>prepared statement cache"]
    SUT --> C["sqlite3_bind_text<br/>name + IP + IP"]
    SUT --> D["wdb_exec_stmt<br/>query execution"]
    SUT --> E["sqlite3_errmsg<br/>error detail"]
    SUT --> F["_mdebug1 / _merror<br/>operational diagnostics"]
    D --> J["cJSON result"]
    A -. failure .-> R1["NULL"]
    B -. failure .-> R2["NULL"]
    C -. failure .-> R3["NULL"]
    D -. failure .-> R4["NULL"]
    D -. success .-> R5["same cJSON pointer"]
~~~

The wrapper set is supplied by the broader Wazuh DB test infrastructure; see [test_wdb_global_test_infrastructure](test_wdb_global_test_infrastructure.md) and [wazuh_db_wrappers_global](wazuh_db_wrappers_global.md) for wrapper conventions and implementation boundaries.

## Lookup process flow

~~~mermaid
flowchart TD
    Start([Call wdb_global_find_agent(wdb, name, ip)]) --> Tx{Begin transaction succeeds?}
    Tx -- No --> TxErr["Log: Cannot begin transaction"] --> Null([Return NULL])
    Tx -- Yes --> Stmt{Statement cache succeeds?}
    Stmt -- No --> StmtErr["Log: Cannot cache statement"] --> Null
    Stmt -- Yes --> B1["Bind parameter 1: name"]
    B1 --> B1OK{Bind succeeds?}
    B1OK -- No --> BindErr["Log sqlite3_bind_text error"] --> Null
    B1OK -- Yes --> B2["Bind parameter 2: ip"]
    B2 --> B2OK{Bind succeeds?}
    B2OK -- No --> BindErr
    B2OK -- Yes --> B3["Bind parameter 3: ip"]
    B3 --> B3OK{Bind succeeds?}
    B3OK -- No --> BindErr
    B3OK -- Yes --> Execute["wdb_exec_stmt()"]
    Execute --> ExecOK{Execution returns cJSON?}
    ExecOK -- No --> ExecErr["Log wdb_exec_stmt() error"] --> Null
    ExecOK -- Yes --> Return([Return cJSON result])
~~~

## Test matrix

| Test | Injected condition | Expected observation |
|---|---|---|
| test_wdb_global_find_agent_transaction_fail | wdb_begin2 returns -1 | Logs Cannot begin transaction; returns NULL |
| test_wdb_global_find_agent_cache_fail | wdb_stmt_cache returns -1 | Logs Cannot cache statement; returns NULL |
| test_wdb_global_find_agent_bind1_fail | Binding name at position 1 returns SQLITE_ERROR | Logs SQLite binding error; returns NULL |
| test_wdb_global_find_agent_bind2_fail | Binding first IP at position 2 fails | Logs SQLite binding error; returns NULL |
| test_wdb_global_find_agent_bind3_fail | Binding second IP at position 3 fails | Logs SQLite binding error; returns NULL |
| test_wdb_global_find_agent_exec_fail | wdb_exec_stmt returns NULL | Logs wdb_exec_stmt(): ERROR MESSAGE; returns NULL |
| test_wdb_global_find_agent_success | All setup, binds, and execution succeed | Returns the exact mocked cJSON pointer |

The failure tests assert both control flow and diagnostics. SQLite failures use the wrapped sqlite3_errmsg() value (ERROR MESSAGE), ensuring operational context is preserved for maintainers debugging a failed lookup.

## Contract details

### Inputs

- wdb: a valid global database context whose id is "global".
- name: agent name, passed as SQLite text parameter 1.
- ip: agent IP address, passed as SQLite text parameters 2 and 3.

The tests do not define SQL text or schema details. Those remain implementation concerns of [wazuh_db_global](wazuh_db_global.md) and the global database schema.

### Outputs

- Success: the cJSON object/array returned by wdb_exec_stmt() is returned unchanged.
- Transaction, cache, bind, or execution failure: NULL.

The success assertion uses pointer equality rather than JSON serialization, which verifies that the function forwards the database-layer result without replacing or transforming it.

### Error behavior

The expected failure pattern is fail-fast: once a transaction, statement cache, bind, or execution stage fails, no later stage is expected. The test suite therefore also validates the ordering of dependency interactions.

## Relationship to adjacent documentation

- [test_wdb_global](test_wdb_global.md) — parent global-database test module and complete capability overview.
- [test_wdb_global_test_infrastructure](test_wdb_global_test_infrastructure.md) — shared fixture and wrapper configuration helpers.
- [wazuh_db_global](wazuh_db_global.md) — production global database architecture and agent/group responsibilities.
- [wazuh_db_engine](wazuh_db_engine.md) — transaction, statement-cache, and SQLite engine behavior used by the function.
- [wazuh_db_command_parser](wazuh_db_command_parser.md) — command routing that exposes global database operations to socket clients.
- [wazuh_db_wrappers_global](wazuh_db_wrappers_global.md) — wrapper seams and mocked global-database contracts.

## Source references

- Test source: src/unit_tests/wazuh_db/test_wdb_global.c
- Implementation under test: src/wazuh_db/wdb_global.c
- Public declarations: src/wazuh_db/wdb.h
- Test registration: main() in src/unit_tests/wazuh_db/test_wdb_global.c
