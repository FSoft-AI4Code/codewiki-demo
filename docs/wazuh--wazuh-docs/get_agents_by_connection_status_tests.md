# get_agents_by_connection_status_tests

## Introduction

get_agents_by_connection_status_tests documents the CMocka coverage for
wdb_global_get_agents_by_connection_status(), the Wazuh DB global-database
query that returns agents matching a connection status. This leaf covers the
basic status-filter form; node-filtered cases belong to the related
get_agents_by_connection_status_and_node_tests leaf.

This is a focused leaf of [test_wdb_global.md](test_wdb_global.md), implemented
in src/unit_tests/wazuh_db/test_wdb_global.c. It validates transaction setup,
statement caching, SQLite parameter binding, paginated JSON retrieval,
response-size handling, and error propagation. Fixture allocation and wrapper
mechanics are shared with
[test_wdb_global_test_infrastructure.md](test_wdb_global_test_infrastructure.md).

## Position in the system

The production function belongs to the global Wazuh database layer. A caller
supplies a cursor (last_id), a connection-status value, and optionally a
cluster node and limit. The function executes a bounded query and reports its
outcome through wdbc_result.

~~~mermaid
flowchart LR
    Caller[Wazuh DB caller] --> Parser[wdb command/parser layer]
    Parser --> Query[wdb_global_get_agents_by_connection_status]
    Query --> Global[(global.db)]
    Global --> Json[cJSON agent array]
    Tests[get_agents_by_connection_status_tests] -. direct call .-> Query
    Tests -. scripted wrappers .-> Tx[Transactions and statements]
    Tests -. assertions .-> Outcome[WDBC result and JSON pointer]
~~~

The surrounding database daemon, command routing, and schema are documented by
[wazuh_db_daemon_core.md](wazuh_db_daemon_core.md),
[wazuh_db_command_parser.md](wazuh_db_command_parser.md), and
[wazuh_db_global.md](wazuh_db_global.md). This page focuses on the function's
observable contract rather than duplicating those module descriptions.

## Contract under test

The function is called with the following shape:

~~~c
wdb_global_get_agents_by_connection_status(
    wdb, last_id, connection_status, node_name_or_null, limit, &status
)
~~~

The tests establish this pipeline:

1. Begin a transaction with wdb_begin2().
2. Cache the prepared statement with wdb_stmt_cache().
3. Bind last_id as SQLite parameter 1.
4. Bind connection_status as parameter 2.
5. Execute through wdb_exec_stmt_sized() in STMT_MULTI_COLUMN mode with
   WDB_MAX_RESPONSE_SIZE.
6. Return the JSON result and set the output status to WDBC_OK, WDBC_DUE, or
   WDBC_ERROR.

~~~mermaid
flowchart TD
    Start([Query agents by connection status]) --> Tx{Transaction starts?}
    Tx -- no --> E1[WDBC_ERROR and NULL]
    Tx -- yes --> Cache{Statement cached?}
    Cache -- no --> E2[WDBC_ERROR and NULL]
    Cache -- yes --> B1[Bind last_id]
    B1 -- fail --> E3[WDBC_ERROR and NULL]
    B1 -- ok --> B2[Bind connection_status]
    B2 -- fail --> E4[WDBC_ERROR and NULL]
    B2 -- ok --> Exec[Execute sized multi-column query]
    Exec -- SQL error --> E7[WDBC_ERROR and NULL]
    Exec -- response fits --> OK[JSON array and WDBC_OK]
    Exec -- response too large --> Due[JSON array and WDBC_DUE]
~~~

## Test architecture

The module does not open SQLite or depend on live agent records. It calls the
production function directly and scripts linker-wrapped dependencies.

~~~mermaid
graph TD
    C[CMocka cases] --> F[Shared setup and teardown]
    F --> W[wdb_t with id global]
    C --> G[wdb_global_get_agents_by_connection_status]
    G --> T[wdb_begin2]
    G --> S[wdb_stmt_cache]
    G --> I[sqlite3_bind_int]
    G --> X[sqlite3_bind_text]
    G --> Q[wdb_exec_stmt_sized]
    I --> M[sqlite3_errmsg on bind failure]
    X --> M
    Q --> J[cJSON agent array]
    C --> A[Assert WDBC status and result]
~~~

The common fixture creates a synthetic global wdb_t, initializes Wazuh DB
configuration, and releases it after each case. See
[test_wdb_global_test_infrastructure.md](test_wdb_global_test_infrastructure.md)
for the complete lifecycle and wrapper catalog.

## Dependencies

| Dependency | Role |
|---|---|
| wdb.h | Wazuh DB types, wdbc_result, and target API. |
| wdb_global_get_agents_by_connection_status() | Production operation under test. |
| wdb_begin2 wrapper | Transaction success or failure. |
| wdb_stmt_cache wrapper | Prepared-statement cache success or failure. |
| sqlite3_bind_int wrapper | Cursor and limit positions and values. |
| sqlite3_bind_text wrapper | Connection-status binding. |
| sqlite3_errmsg wrapper | Deterministic SQLite diagnostics. |
| wdb_exec_stmt_sized wrapper | Success, oversized-response, or SQL-error outcomes. |
| cJSON | Synthetic multi-column agent arrays. |
| CMocka | Expectations, registration, and assertions. |

The wrapper implementation is shared with the broader Wazuh DB suite; see
[wazuh_db_wrappers_global.md](wazuh_db_wrappers_global.md).

## Test scenarios

### Basic connection-status query

These cases pass node_name = NULL and limit = -1.

| Test case | Simulated condition | Expected behavior |
|---|---|---|
| test_wdb_global_get_agents_by_connection_status_transaction_fail | wdb_begin2() returns -1. | WDBC_ERROR and NULL result. |
| test_wdb_global_get_agents_by_connection_status_cache_fail | Statement cache returns -1. | WDBC_ERROR and NULL result. |
| test_wdb_global_get_agents_by_connection_status_bind1_fail | Binding last_id = 0 at index 1 fails. | SQLite diagnostic, WDBC_ERROR, NULL. |
| test_wdb_global_get_agents_by_connection_status_bind2_fail | Binding active at index 2 fails. | SQLite diagnostic, WDBC_ERROR, NULL. |
| test_wdb_global_get_agents_by_connection_status_ok | Ten synthetic agent objects are returned. | WDBC_OK and non-null result. |
| test_wdb_global_get_agents_by_connection_status_due | Sized execution reports a full socket response. | WDBC_DUE and non-null result. |
| test_wdb_global_get_agents_by_connection_status_err | Sized execution reports SQLITE_ERROR. | WDBC_ERROR and NULL result. |

The related node-filtered leaf extends this contract with node-name and limit
bindings; it is intentionally not duplicated here.

## Component interaction flow

~~~mermaid
sequenceDiagram
    participant T as CMocka test
    participant G as Target function
    participant Tx as wdb_begin2
    participant C as wdb_stmt_cache
    participant B as SQLite bind wrappers
    participant E as wdb_exec_stmt_sized
    T->>G: last_id and connection status
    G->>Tx: Begin transaction
    Tx-->>G: success or error
    G->>C: Cache statement
    C-->>G: success or error
    G->>B: Bind cursor and status
    B-->>G: SQLITE_OK or SQLITE_ERROR
    G->>E: Execute sized multi-column query
    E-->>G: cJSON array, full response, or SQL error
    G-->>T: JSON result and WDBC status
~~~

## Response-size and pagination behavior

last_id is the cursor used by the query to continue retrieving agents. The
tests use 0 as the initial cursor and do not validate a next-page cursor; they
focus on result status and pointer presence.

wdb_exec_stmt_sized() is configured with WDB_MAX_RESPONSE_SIZE and
STMT_MULTI_COLUMN. A normal response maps to WDBC_OK; an oversized socket
response maps to WDBC_DUE while preserving a non-null JSON result in the
tested behavior. SQL execution failure maps to WDBC_ERROR and a null result.

~~~mermaid
stateDiagram-v2
    [*] --> QueryPrepared
    QueryPrepared --> WDBC_OK: response within limit
    QueryPrepared --> WDBC_DUE: response exceeds socket limit
    QueryPrepared --> WDBC_ERROR: transaction/cache/bind/SQL failure
    WDBC_OK --> [*]
    WDBC_DUE --> [*]
    WDBC_ERROR --> [*]
~~~

## Maintenance guidance

When changing the query or prepared-statement contract:

- preserve the basic and node-filtered branches;
- update binding-index assertions if SQL parameter order changes;
- retain separate coverage for transaction, cache, each bind, execution,
  success, and size-limit outcomes;
- keep STMT_MULTI_COLUMN and WDB_MAX_RESPONSE_SIZE assertions aligned with the
  production call;
- update exact logging assertions when diagnostics intentionally change;
- use the parent and infrastructure pages for shared behavior.

## Source reference

- Production test source: src/unit_tests/wazuh_db/test_wdb_global.c
- Target function: wdb_global_get_agents_by_connection_status()
- Registration section: Tests wdb_global_get_agents_by_connection_status
- Broader module: [test_wdb_global.md](test_wdb_global.md)
- Shared fixture: [test_wdb_global_test_infrastructure.md](test_wdb_global_test_infrastructure.md)
- Related sibling: [get_agents_by_connection_status_and_node_tests.md](get_agents_by_connection_status_and_node_tests.md) (when generated)
