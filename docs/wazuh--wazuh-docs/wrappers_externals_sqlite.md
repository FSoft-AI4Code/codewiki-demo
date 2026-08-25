# `wrappers_externals_sqlite`

`wrappers_externals_sqlite` is Wazuh’s CMocka-based test seam for the SQLite C API. It replaces database handles, prepared statements, binding, stepping, result extraction, transaction state, and cleanup with deterministic mocks so unit tests can exercise database code without depending on a real database file or a particular SQLite result.

The module is test infrastructure, not a database implementation. Production persistence and query behavior remain in consumers such as [`wazuh_db.md`](wazuh_db.md), [`dbsync_sqlite_backend.md`](dbsync_sqlite_backend.md), [`sqlite_wrapper.md`](sqlite_wrapper.md), and the higher-level framework query modules.

## Purpose and system position

The wrappers intercept selected `sqlite3_*` symbols in unit-test builds. Tests register argument expectations and return values with CMocka; the code under test continues to call the normal SQLite API and receives the scripted result.

```mermaid
flowchart LR
    T[Unit test] -->|expectations and mock values| W[SQLite wrapper layer]
    P[Wazuh database code] -->|wrapped sqlite3_* calls| W
    W -->|scripted status, value, or pointer| P
    P --> R[Query, transaction, or persistence result]
    W -. avoids .-> DB[(Real SQLite database)]
```

This boundary makes it possible to test success, constraint errors, preparation failures, empty result sets, transaction failures, and multi-row iteration without creating or mutating a live SQLite database.

## Architecture

```mermaid
graph TD
    M[wrappers_externals_sqlite] --> B[Parameter binding]
    M --> Q[Statement preparation and execution]
    M --> C[Connection and lifecycle]
    M --> X[Result extraction]
    M --> S[Transaction and metadata state]
    M --> CM[CMocka mock queues and expectations]
    B --> P[sqlite3_bind_*]
    Q --> E[sqlite3_prepare_v2 / sqlite3_step / sqlite3_exec]
    C --> L[sqlite3_open_v2 / sqlite3_close_v2]
    X --> D[sqlite3_column_*]
    S --> A[autocommit, changes, rowid, error code]
```

All functions are implemented in one source file:

`src/unit_tests/wrappers/externals/sqlite/sqlite3_wrappers.c`

The source includes SQLite declarations, CMocka, and the shared wrapper support in `../../common.h`. The wrapper functions ignore database and statement pointers unless an argument is explicitly checked; those pointers are supplied by tests as opaque handles.

## Component inventory

### Parameter binding

| Wrapper | Checked arguments | Returned behavior |
|---|---|---|
| `__wrap_sqlite3_bind_int` | `index`, `value` | Returns `mock()`; `expect_sqlite3_bind_int_call()` queues a complete expectation. |
| `__wrap_sqlite3_bind_int64` | `index`, `value` | Returns `mock()`. |
| `__wrap_sqlite3_bind_double` | `index`, `value` | Returns `mock()`. |
| `__wrap_sqlite3_bind_null` | `index` | Returns `mock()`. |
| `__wrap_sqlite3_bind_text` | `pos`, and `buffer` when non-null | Returns `mock()`; length and destructor are intentionally not checked. |
| `__wrap_sqlite3_bind_parameter_index` | `zName` | Returns `mock()`. |
| `__wrap_sqlite3_clear_bindings` | None | Returns `mock()`. |

`check_expected()` runs before the return value is consumed. A mismatch fails the CMocka test, which makes these wrappers useful for verifying that query builders bind the intended position and value. The helper `expect_sqlite3_bind_int64_call()` has a `double` parameter in the source even though the wrapped SQLite value is `sqlite3_int64`; callers should preserve the existing helper signature and use it consistently with the test suite.

### Query preparation and execution

| Wrapper | Behavior |
|---|---|
| `__wrap_sqlite3_prepare_v2` | Places a mocked `sqlite3_stmt *` in `*ppStmt`, sets `*pzTail` to null when supplied, and returns `mock()`. SQL text is not checked by this wrapper. |
| `__wrap_sqlite3_exec` | Checks `sql`, writes a mocked `char *` to `*errmsg`, and returns `mock()`. |
| `__wrap_sqlite3_step` | Uses a two-stage mock protocol: a truthy first mock delegates to `__real_sqlite3_step`; a false first mock returns the next queued value. |
| `__wrap_sqlite3_reset` | Returns `mock()`. |
| `__wrap_sqlite3_finalize` | Returns `mock()`. |

The step wrapper is the module’s main iteration seam. `expect_sqlite3_step_call(ret)` queues the non-delegating path, and `expect_sqlite3_step_count(ret, count)` repeats that setup for a known number of calls. This models common SQLite sequences such as `SQLITE_ROW`, followed by `SQLITE_DONE`, without needing a prepared statement backed by real tables.

```mermaid
sequenceDiagram
    participant Test as CMocka test
    participant Code as Database code
    participant Wrap as SQLite wrappers
    participant Mock as CMocka queue
    participant Real as Real sqlite3_step

    Test->>Mock: queue statement pointer and step results
    Code->>Wrap: sqlite3_prepare_v2
    Wrap->>Mock: mock_type(sqlite3_stmt *)
    Wrap-->>Code: statement handle and status
    loop rows
        Code->>Wrap: sqlite3_step
        Wrap->>Mock: read delegation flag
        alt delegation flag is false
            Wrap->>Mock: read scripted SQLite status
            Mock-->>Wrap: ROW or DONE
        else delegation flag is true
            Wrap->>Real: __real_sqlite3_step
            Real-->>Wrap: native status
        end
        Wrap-->>Code: step result
        Code->>Wrap: sqlite3_column_*
    end
    Code->>Wrap: sqlite3_reset / sqlite3_finalize
```

### Result extraction

| Wrapper | Checked arguments | Mocked result |
|---|---|---|
| `__wrap_sqlite3_column_count` | None | `int` from `mock()`. |
| `__wrap_sqlite3_column_type` | Column index `i` | `int` from `mock()`. |
| `__wrap_sqlite3_column_int` | Column index `iCol` | `int` from `mock()`. |
| `__wrap_sqlite3_column_int64` | Column index `iCol` | `sqlite3_int64` from `mock()`. |
| `__wrap_sqlite3_column_double` | Column index `iCol` | `double` from `mock_type(double)`. |
| `__wrap_sqlite3_column_text` | Column index `iCol` | `const unsigned char *` from `mock_type(...)`. |
| `__wrap_sqlite3_column_name` | Column index `N` | `char *` from `mock_ptr_type(...)`. |
| `__wrap_sqlite3_sql` | None | `char *` from `mock_ptr_type(...)`. |

These functions let tests control both SQLite’s reported type and the converted value. They do not enforce consistency between the type and value; tests that need conversion behavior should queue a coherent combination explicitly.

### Connection, errors, and metadata

| Wrapper | Behavior |
|---|---|
| `__wrap_sqlite3_open_v2` | Checks `filename` and `flags`, stores a mocked `sqlite3 *` in `*ppDb`, and returns `mock()`. |
| `__wrap_sqlite3_close_v2` | Returns `mock()`. |
| `__wrap_sqlite3_extended_errcode` | Returns a mocked extended error code. |
| `__wrap_sqlite3_errmsg` | Returns a mocked `const char *`. |
| `__wrap_sqlite3_free` | No-op; it never frees the supplied pointer. |
| `__wrap_sqlite3_get_autocommit` | Returns a mocked autocommit state. |
| `__wrap_sqlite3_changes` | Returns a mocked affected-row count. |
| `__wrap_sqlite3_last_insert_rowid` | Returns a mocked row identifier. |

The no-op `sqlite3_free` is intentional: ownership of mocked error strings and other SQLite-managed memory remains with the test fixture. It prevents the wrapper from freeing arbitrary mock pointers.

## Dependency relationships

```mermaid
flowchart LR
    H[SQLite declarations / sqlite3_wrappers.h] --> C[sqlite3_wrappers.c]
    C --> S[SQLite ABI types and symbols]
    C --> M[CMocka mock / mock_type]
    C --> E[CMocka check_expected]
    C --> R[wrappers_common test support]
    WDB[Wazuh DB tests] --> C
    DS[DBSync SQLite tests] --> C
    SW[SQLite wrapper/query tests] --> C
    SC[Syscheck and inventory DB tests] --> WDB
```

The module is consumed directly or indirectly by tests for:

- [`wazuh_db.md`](wazuh_db.md), including global, FIM, syscollector, task, integrity, and metadata database behavior.
- [`dbsync.md`](dbsync.md) and [`dbsync_sqlite_backend.md`](dbsync_sqlite_backend.md), where SQLite is the concrete DBSync engine.
- [`sqlite_wrapper.md`](sqlite_wrapper.md), which provides higher-level C++/C++-adjacent SQLite abstractions.
- [`syscheckd_db.md`](syscheckd_db.md) and inventory persistence tests, where SQLite-backed state is exercised through Wazuh DB or DBSync layers.

The external wrapper itself does not know about agents, FIM records, inventory schemas, RBAC, or API responses. Those domain concerns belong to the consuming modules and should be linked rather than reproduced here.

## Data flow through a database operation

```mermaid
flowchart TD
    I[Input parameters] --> O[sqlite3_open_v2]
    O --> P[sqlite3_prepare_v2]
    P --> B[sqlite3_bind_*]
    B --> T[sqlite3_step]
    T --> D{ROW or DONE?}
    D -->|ROW| X[sqlite3_column_count/type/value/name]
    X --> T
    D -->|DONE| U[sqlite3_changes / last_insert_rowid]
    D -->|error| E[extended_errcode / errmsg]
    U --> R[reset and finalize]
    E --> R
    R --> C[close_v2]
```

Every external interaction in this flow is independently scriptable. A test can therefore isolate whether a failure came from opening the database, preparing SQL, binding a value, stepping, decoding a column, or cleaning up.

## Representative test flows

### Select with multiple rows

```mermaid
flowchart TD
    A[Queue statement pointer] --> B[Queue prepare success]
    B --> C[Queue ROW, ROW, DONE]
    C --> D[Queue column count and values for row 1]
    D --> E[Queue column count and values for row 2]
    E --> F[Code under test iterates]
    F --> G[Queue reset and finalize]
    G --> H[Assert decoded result]
```

The step-count helper is useful for the repeated return values, while column wrappers provide the row payload. The wrapper does not retain row state; the test must queue values in the order the production code reads them.

### Write or transaction failure injection

```mermaid
flowchart LR
    A[Open] --> B[Prepare]
    B --> C[Bind]
    C --> D{Step result}
    D -->|success| E[Changes / rowid]
    D -->|constraint or SQL error| F[Errcode / errmsg]
    E --> G[Finalize and close]
    F --> G
    G --> H[Assert caller rollback/error handling]
```

The same flow covers transaction helpers that invoke `sqlite3_exec` for `BEGIN`, `COMMIT`, or `ROLLBACK`: check the SQL string, queue an error message pointer, and return the desired SQLite status.

### Real-step escape hatch

```mermaid
flowchart TD
    S[sqlite3_step call] --> M{First mock value}
    M -->|0 / false| Q[Return second mock value]
    M -->|non-zero / true| R[Call __real_sqlite3_step]
    Q --> C[Test-controlled result]
    R --> N[Native SQLite result]
```

Most unit tests should use the fully mocked path. The delegation branch exists for tests that construct a real SQLite statement but still need the wrapper symbol in the link. Its use couples a test to SQLite setup and should be documented in that test.

## Test-author guidance

1. Queue all `expect_value()` or `expect_string()` checks before calling the production function.
2. Queue `will_return()` values in the exact order that the wrapper consumes them. This is especially important for `sqlite3_step`, which consumes a delegation flag and, when false, a second status value.
3. Use `mock_type()` or `mock_ptr_type()` for pointers, `double`, and SQLite integer values where the wrapper expects typed extraction.
4. Provide output locations for `sqlite3_open_v2`, `sqlite3_prepare_v2`, and `sqlite3_exec`; the wrappers write to `*ppDb`, `*ppStmt`, `*pzTail`, and `*errmsg` when applicable.
5. Keep mocked text and error pointers valid for the duration of the caller’s use. `sqlite3_free` is a no-op, so cleanup must be handled by the fixture if the test allocated the memory.
6. Do not assume that unchecked arguments are validated. SQL text is checked by `sqlite3_exec`, but not by `sqlite3_prepare_v2`; binding length/destructor and several pointer arguments are intentionally ignored.

## Limitations and maintenance considerations

- The wrappers do not parse SQL, enforce schema constraints, implement transactions, or reproduce SQLite locking and WAL behavior.
- They do not maintain statement or connection state between calls. Any state machine must be represented by the test’s mock queue.
- `sqlite3_free` is deliberately inert and should remain so unless ownership semantics are redesigned across the test suite.
- `sqlite3_step` has an unusual delegation protocol. Changes to it require reviewing every use of `expect_sqlite3_step_call()` and `expect_sqlite3_step_count()`.
- Preserve native SQLite signatures and output-pointer behavior. Link-time wrapping is sensitive to ABI and declaration drift.
- Add argument checks sparingly. A new check can make existing tests fail even when the production behavior remains valid.
- Keep database-domain assertions in the consuming test modules; this layer should remain deterministic, stateless, and focused on the SQLite ABI boundary.

## Related documentation

- [`wrappers_common.md`](wrappers_common.md) — shared CMocka wrapper conventions.
- [`wazuh_db.md`](wazuh_db.md) — Wazuh database daemon and persistence responsibilities.
- [`dbsync.md`](dbsync.md) — database synchronization abstractions.
- [`dbsync_sqlite_backend.md`](dbsync_sqlite_backend.md) — SQLite-backed DBSync implementation.
- [`sqlite_wrapper.md`](sqlite_wrapper.md) — higher-level SQLite wrapper abstractions.
- [`wrappers_externals_audit.md`](wrappers_externals_audit.md) and [`wrappers_externals_openssl.md`](wrappers_externals_openssl.md) — neighboring external-library test seams.
