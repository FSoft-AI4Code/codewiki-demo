# `insert_agent_belong_tests`

## Introduction

`insert_agent_belong_tests` documents the focused CMocka tests for
`wdb_global_insert_agent_belong()`, the Wazuh DB operation that creates one
agent-to-group membership in the global database. The tests are defined in
`src/unit_tests/wazuh_db/test_wdb_global.c` and are registered in the global
Wazuh DB unit-test executable.

This is a leaf module within the broader [`test_wdb_global.md`](test_wdb_global.md)
suite. It verifies the database write path, parameter ordering, status-code
propagation, and short-circuit behavior for transaction, statement-cache,
SQLite binding, and statement-execution failures. The common fixture and
wrapper contracts are documented in
[`test_wdb_global_test_infrastructure.md`](test_wdb_global_test_infrastructure.md)
and [`wazuh_db_wrappers_global.md`](wazuh_db_wrappers_global.md).

## Purpose and system role

The target function inserts a row into the global database's agent/group
membership relationship, commonly called the `belongs` table. The row is
identified by a group ID and agent ID and carries a priority used when group
membership is ordered or recalculated.

In the wider system, this operation is composed by higher-level group
assignment workflows such as `wdb_global_assign_agent_group()` and
`wdb_global_set_agent_groups()`. Those workflows, including lookup,
validation, default-group handling, and group-context recalculation, are
covered by the broader global database documentation rather than repeated
here. The focused tests exercise only the primitive membership insertion.

```mermaid
flowchart LR
    Caller[Agent/group management workflow] --> Assign[wdb_global_assign_agent_group]
    Assign --> Target[wdb_global_insert_agent_belong]
    Target --> Belongs[(global.db belongs relationship)]
    Belongs --> GroupState[Agent group membership and priority]

    Tests[insert_agent_belong_tests] -. direct unit call .-> Target
    Tests -. scripted outcomes .-> Wrappers[CMocka linker-wrapped DB/SQLite APIs]
    Wrappers -. isolates .-> Belongs
```

## Architecture and dependencies

```mermaid
graph TD
    Suite[Unit_Tests_-_Wazuh_DB] --> Parent[test_wdb_global.c]
    Parent --> Leaf[insert_agent_belong_tests]
    Leaf --> Fixture[test_setup / test_teardown]
    Leaf --> Function[wdb_global_insert_agent_belong]

    Function --> Begin[wdb_begin2]
    Function --> Cache[wdb_stmt_cache]
    Function --> Bind[sqlite3_bind_int x3]
    Function --> Execute[wdb_exec_stmt_silent]
    Function --> Log[Wazuh debug/error logging]

    Begin --> WDBWrap[Wazuh DB wrappers]
    Cache --> WDBWrap
    Execute --> WDBWrap
    Bind --> SQLiteWrap[SQLite wrappers]
    Log --> LogWrap[Logging wrappers]
    Fixture --> Context[Synthetic global wdb_t]
```

Relevant source-level dependencies are:

| Component | Role in this module |
|---|---|
| `src/wazuh_db/wdb_global.c` | Production implementation under test. |
| `src/wazuh_db/wdb.h` | Declares the database type, status constants, and target API. |
| `wdb_begin2()` | Starts the database transaction boundary. |
| `wdb_stmt_cache()` | Obtains/caches the prepared insert statement. |
| `sqlite3_bind_int()` | Binds group ID, agent ID, and priority in positions 1–3. |
| `wdb_exec_stmt_silent()` | Executes the write without a result-set payload. |
| `sqlite3_errmsg()` | Supplies deterministic text for bind-error assertions. |
| CMocka and linker wrappers | Script dependency outcomes and verify call arguments/order. |

The test does not open a real SQLite database. It supplies a structurally
valid `wdb_t` whose database pointer is synthetic, then controls each
dependency through wrappers.

## Operation contract

The tested call is:

```c
int wdb_global_insert_agent_belong(wdb_t *wdb,
                                   int id_group,
                                   int id_agent,
                                   int priority);
```

The expected prepared-statement parameter contract is:

| Parameter position | Value | Meaning |
|---:|---:|---|
| 1 | `id_group` | Existing group identifier. |
| 2 | `id_agent` | Existing agent identifier. |
| 3 | `priority` | Membership ordering priority. |

The operation returns `OS_SUCCESS` only after all three bindings and silent
statement execution succeed. Transaction setup, statement caching, and
binding failures return `OS_UNDEF` in the tested implementation path; a
silent execution failure returns `OS_INVALID`. These distinctions are part of
the current test contract and should be preserved unless the Wazuh DB status
API changes.

## Test cases

All cases use `id_group = 2`, `id_agent = 2`, and `priority = 0`, except where
the test name describes the injected failure stage.

| Test case | Injected condition | Expected result |
|---|---|---|
| `test_wdb_global_insert_agent_belong_transaction_fail` | `wdb_begin2()` returns `-1`. | Logs `Cannot begin transaction`; returns `OS_UNDEF`. |
| `test_wdb_global_insert_agent_belong_cache_fail` | `wdb_stmt_cache()` returns `-1`. | Logs `Cannot cache statement`; returns `OS_UNDEF`. |
| `test_wdb_global_insert_agent_belong_bind1_fail` | Binding parameter 1 (`id_group`) returns `SQLITE_ERROR`. | Logs the SQLite error; returns `OS_UNDEF`. |
| `test_wdb_global_insert_agent_belong_bind2_fail` | Binding parameter 2 (`id_agent`) returns `SQLITE_ERROR`. | Logs the SQLite error; returns `OS_UNDEF`. |
| `test_wdb_global_insert_agent_belong_bind3_fail` | Binding parameter 3 (`priority`) returns `SQLITE_ERROR`. | Logs the SQLite error; returns `OS_UNDEF`. |
| `test_wdb_global_insert_agent_belong_step_fail` | All binds succeed; silent execution returns `OS_INVALID`. | Returns `OS_INVALID`. |
| `test_wdb_global_insert_agent_belong_success` | Transaction, cache, all bindings, and execution succeed. | Returns `OS_SUCCESS`. |

The bind tests assert both the positional index and value. Consequently, they
detect accidental parameter reordering as well as failure propagation.

## Normal and failure flow

```mermaid
flowchart TD
    Start([Call with group ID, agent ID, priority]) --> Tx{wdb_begin2 succeeds?}
    Tx -- no --> TxErr[Log transaction failure]
    TxErr --> Undef1([Return OS_UNDEF])
    Tx -- yes --> Cache{wdb_stmt_cache succeeds?}
    Cache -- no --> CacheErr[Log cache failure]
    CacheErr --> Undef2([Return OS_UNDEF])
    Cache -- yes --> B1[Bind parameter 1: id_group]
    B1 --> B1OK{SQLITE_OK?}
    B1OK -- no --> BindErr1[Log sqlite3_errmsg]
    B1OK -- yes --> B2[Bind parameter 2: id_agent]
    B2 --> B2OK{SQLITE_OK?}
    B2OK -- no --> BindErr2[Log sqlite3_errmsg]
    B2OK -- yes --> B3[Bind parameter 3: priority]
    B3 --> B3OK{SQLITE_OK?}
    B3OK -- no --> BindErr3[Log sqlite3_errmsg]
    BindErr1 --> Undef3([Return OS_UNDEF])
    BindErr2 --> Undef3
    BindErr3 --> Undef3
    B3OK -- yes --> Exec[wdb_exec_stmt_silent]
    Exec --> ExecOK{OS_SUCCESS?}
    ExecOK -- yes --> Success([Return OS_SUCCESS])
    ExecOK -- no --> Invalid([Return OS_INVALID])
```

Each failure case stops at its injected boundary. CMocka expectations are
therefore also ordering checks: a failed transaction must not cache a
statement, a failed cache must not bind parameters, and a failed bind must
not execute the statement.

## Component interaction

```mermaid
sequenceDiagram
    participant T as CMocka test
    participant F as wdb_global_insert_agent_belong
    participant Tx as wdb_begin2
    participant C as wdb_stmt_cache
    participant B as sqlite3_bind_int
    participant E as wdb_exec_stmt_silent
    participant L as Logging wrapper

    T->>F: wdb, id_group, id_agent, priority
    F->>Tx: Begin transaction
    Tx-->>F: success / failure
    alt transaction failure
        F->>L: debug("Cannot begin transaction")
        F-->>T: OS_UNDEF
    else transaction success
        F->>C: Cache insert statement
        C-->>F: success / failure
        alt cache failure
            F->>L: debug("Cannot cache statement")
            F-->>T: OS_UNDEF
        else cache success
            F->>B: Bind 1 = id_group
            B-->>F: SQLITE_OK / SQLITE_ERROR
            F->>B: Bind 2 = id_agent
            B-->>F: SQLITE_OK / SQLITE_ERROR
            F->>B: Bind 3 = priority
            B-->>F: SQLITE_OK / SQLITE_ERROR
            alt bind failure
                F->>L: error with sqlite3_errmsg()
                F-->>T: OS_UNDEF
            else all binds succeed
                F->>E: Execute silently
                E-->>F: OS_SUCCESS / OS_INVALID
                F-->>T: Matching status code
            end
        end
    end
```

The operation is a write-only database primitive. No cJSON result is
expected, and the test module deliberately asserts status codes and
diagnostics rather than a returned payload.

## Fixture and isolation

The cases are registered with `cmocka_unit_test_setup_teardown()`. The shared
fixture behavior is maintained in
[`test_wdb_global_test_infrastructure.md`](test_wdb_global_test_infrastructure.md);
the focused lifecycle is:

```mermaid
sequenceDiagram
    participant C as CMocka runner
    participant S as test_setup
    participant T as Focused test
    participant D as test_teardown

    C->>S: Allocate test_struct_t
    S->>S: Create wdb_t with id = "global"
    S->>S: Allocate synthetic sqlite3* storage
    S->>S: wdb_init_conf()
    S-->>T: Publish fixture state
    T->>T: Configure wrapper returns and expectations
    T->>T: Call insertion function and assert status
    T-->>D: Return state
    D->>D: Free fixture allocations
    D->>D: wdb_free_conf()
    D-->>C: Test isolated
```

This prevents wrapper return values, configuration state, or fixture memory
from leaking between success and failure scenarios.

## Maintenance guidance

When changing the production insert path or its prepared SQL statement:

1. Keep coverage for transaction start, statement caching, all three bind
   positions, execution failure, and success.
2. Update the parameter-position assertions if the SQL statement changes.
3. Preserve the distinction between `OS_UNDEF` setup/bind failures and
   `OS_INVALID` execution failures unless the public status contract changes.
4. Add higher-level assignment behavior to the relevant group-management
   tests, not to this primitive leaf, to keep responsibilities separated.
5. Update links if the parent global-database or wrapper documentation is
   renamed.

## References

- [`test_wdb_global.md`](test_wdb_global.md) — complete global database test scope.
- [`test_wdb_global_test_infrastructure.md`](test_wdb_global_test_infrastructure.md) — fixture and composite wrapper helpers.
- [`wazuh_db_global.md`](wazuh_db_global.md) — production global database behavior and group-membership context.
- [`wazuh_db_wrappers_global.md`](wazuh_db_wrappers_global.md) — linker-wrapper contracts used by the tests.
- [`Unit_Tests_-_Wazuh_DB.md`](Unit_Tests_-_Wazuh_DB.md) — parent unit-test suite.
