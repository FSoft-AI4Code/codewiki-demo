# sync_agent_groups_get_tests

## Introduction

sync_agent_groups_get_tests documents the focused CMocka coverage for
wdb_global_sync_agent_groups_get(). This operation reads agent/group
membership from the global Wazuh database for synchronization, supports
incremental retrieval from a last-agent cursor, optionally marks returned
agents as synchronized, and can append the manager-wide group hash.

The selected tests are implemented in
[src/unit_tests/wazuh_db/test_wdb_global.c](../../src/unit_tests/wazuh_db/test_wdb_global.c)
and registered in the broader [test_wdb_global](test_wdb_global.md) suite.
This page concentrates on the synchronization cases listed for this module;
shared fixture and wrapper conventions are described by the parent suite and
[select_group_belong_tests](select_group_belong_tests.md).

## Purpose and system position

The function is a read-side synchronization boundary between global.db and
cluster or manager synchronization callers. It returns a JSON envelope rather
than a raw SQL result. The envelope contains a data array of agents and may
contain a global hash property. Each agent entry can be enriched with its group
membership, and the optional set_synced flag causes the corresponding group
synchronization status to be updated.

~~~mermaid
flowchart LR
    Caller[Cluster or DB synchronization caller]
    API[Wazuh DB command/API boundary]
    Sync[wdb_global_sync_agent_groups_get]
    Global[(global.db)]
    Membership[agent-group belongs records]
    Hash[global group hash]
    Response[JSON synchronization envelope]

    Caller --> API --> Sync
    Sync --> Global
    Global --> Membership
    Sync --> Hash
    Sync --> Response
    Response --> Caller
    Tests[sync_agent_groups_get_tests] -. CMocka call .-> Sync
~~~

The operation is related to, but distinct from, the lower-level membership
query documented in [select_group_belong_tests](select_group_belong_tests.md),
the hash decoration helper in
[add_global_group_hash_to_response_tests](add_global_group_hash_to_response_tests.md),
and the synchronization-status setter in
[set_agent_groups_sync_status_tests](set_agent_groups_sync_status_tests.md).
The production behavior and SQL ownership remain in
[wazuh_db_global](wazuh_db_global.md).

## Contract under test

Conceptually, the tested interface is:

~~~c
wdbc_result wdb_global_sync_agent_groups_get(
    wdb_t *wdb,
    wdb_groups_sync_condition_t condition,
    int last_agent_id,
    bool set_synced,
    bool get_hash,
    int agent_registration_delta,
    cJSON **output);
~~~

The tests establish these observable rules:

1. WDB_GROUP_INVALID_CONDITION is rejected before database work.
2. A no-condition request can return an empty data array and, when enabled, a
   hash field.
3. Filtered requests bind the cursor, last_agent_id, and a registration-time
   threshold calculated as current_time - agent_registration_delta.
4. Agents are read incrementally and their groups are fetched through the
   single-column membership path.
5. set_synced causes a group-sync status update for each returned agent; an
   update failure preserves the data but returns WDBC_ERROR.
6. A response that exceeds the Wazuh DB/socket response limit returns WDBC_DUE,
   allowing the caller to continue with another page.
7. When get_hash is enabled, failure to obtain the global hash changes the
   result to WDBC_ERROR; a successful lookup may produce hash: null when no
   hash value is available.

~~~mermaid
flowchart TD
    Start([sync request]) --> Validate{Condition valid?}
    Validate -- no --> Invalid[Log invalid groups sync condition] --> Error[WDBC_ERROR]
    Validate -- yes --> Create[Create response and data arrays]
    Create --> Mode{No-condition fast path?}
    Mode -- yes --> HashOpt{get_hash enabled?}
    Mode -- no --> Tx[Begin transaction]
    Tx --> Cache[Cache synchronization statement]
    Cache --> Bind1[Bind last_agent_id]
    Bind1 --> Bind2[Bind registration cutoff]
    Bind2 --> Query[Execute agent query]
    Query --> Agents{Agents returned?}
    Agents -- no --> HashOpt
    Agents -- yes --> Groups[Select each agent's groups]
    Groups --> SetSynced{set_synced enabled?}
    SetSynced -- yes --> SyncStatus[Set group sync status]
    SetSynced -- no --> Size[Check response size]
    SyncStatus --> Size
    Size --> Due{Response too large?}
    Due -- yes --> DueResult[WDBC_DUE]
    Due -- no --> HashOpt
    HashOpt --> HashDecision{Hash retrieval succeeds?}
    HashDecision -- no --> Error
    HashDecision -- yes --> Success[Return envelope and WDBC_OK]
~~~

## Components and dependencies

| Component | Role in these tests |
|---|---|
| test_wdb_global.c | Defines and registers the selected CMocka cases. |
| test_setup / test_teardown | Creates a minimal wdb_t with ID global, a placeholder SQLite handle, output storage, and initialized Wazuh DB configuration. |
| wdb_global_sync_agent_groups_get | Function under test; validates conditions, queries agents, enriches groups, manages sync state, and builds the response. |
| wdb_begin2 | Simulates transaction creation for the main agent query and nested membership operations. |
| wdb_stmt_cache | Controls prepared-statement caching failures and success. |
| sqlite3_bind_int | Verifies cursor and registration-cutoff parameters. |
| wdb_exec_stmt | Supplies agent query results or an execution failure. |
| wdb_exec_stmt_sized | Supplies group arrays and models the socket/response-size boundary. |
| wdb_get_global_group_hash | Controls optional hash retrieval. |
| wdb_global_set_agent_groups_sync_status | Models the set_synced write-back path. |
| cJSON | Builds, mutates, serializes, and deletes response and mock query data. |
| Logging wrappers | Assert exact diagnostics for invalid conditions, bind failures, cache failures, and hash/status errors. |

~~~mermaid
graph TD
    Tests[test cases] --> Fixture[setup / teardown]
    Tests --> Target[wdb_global_sync_agent_groups_get]
    Target --> Tx[wdb_begin2]
    Target --> Cache[wdb_stmt_cache]
    Target --> Bind[sqlite3_bind_int]
    Target --> Exec[wdb_exec_stmt]
    Target --> Groups[wdb_exec_stmt_sized]
    Target --> Hash[wdb_get_global_group_hash]
    Target --> Status[wdb_global_set_agent_groups_sync_status]
    Target --> Json[cJSON]
    Tests --> Logs[debug/error wrappers]
~~~

No live SQLite database, socket, cluster node, or filesystem is required.
The wrappers provide deterministic return values and verify that later stages
are not called after an earlier failure.

## Test scenarios

### Invalid condition

test_wdb_global_sync_agent_groups_get_invalid_condition passes
WDB_GROUP_INVALID_CONDITION and a null output pointer. The function logs
Invalid groups sync condition and returns WDBC_ERROR without creating a
database transaction.

### No-condition request with hash retrieval

test_wdb_global_sync_agent_groups_get_no_condition_get_hash_true exercises
WDB_GROUP_NO_CONDITION with get_hash=true. The expected serialized result is:

~~~json
[{"data":[],"hash":null}]
~~~

This confirms the empty synchronization response shape and the optional hash
decoration path when the hash provider succeeds without supplying a value.

### Transaction, statement-cache, and binding failures

The following cases verify short-circuit behavior and error classification:

| Test case | Injected failure | Expected result | Response assertion |
|---|---|---|---|
| test_wdb_global_sync_agent_groups_get_transaction_fail | wdb_begin2() returns OS_INVALID. | WDBC_ERROR | Output object is cleaned up; no data is returned. |
| test_wdb_global_sync_agent_groups_get_cache_fail | wdb_stmt_cache() returns OS_INVALID. | WDBC_ERROR | Serialized response is [{"data":[]}] without hash decoration. |
| test_wdb_global_sync_agent_groups_get_bind_fail | First integer bind fails. | WDBC_ERROR | Serialized response remains [{"data":[]}]. |
| test_wdb_global_sync_agent_groups_get_bind2_fail | Registration-cutoff bind fails. | WDBC_ERROR | Serialized response remains [{"data":[]}]. |

The bind tests also verify the parameter contract: position 1 receives
last_agent_id, while position 2 receives wrapped_time -
agent_registration_delta.

### No agents and hash disabled

test_wdb_global_sync_agent_groups_get_no_agents_get_hash_false supplies one
mock agent query result followed by an empty query result and disables hash
retrieval. The resulting data is:

~~~json
[{"data":[{"id":1,"groups":[]}]}]
~~~

The case demonstrates cursor advancement, per-agent group lookup, an empty
group array when the membership query has no result, and the absence of a hash
property when get_hash=false.

### Agent query execution failure with hash enabled

test_wdb_global_sync_agent_groups_get_exec_fail_get_hash_true_success makes
the agent query return no JSON result, then allows global hash retrieval. The
function returns WDBC_OK with:

~~~json
[{"data":[],"hash":null}]
~~~

The paired test_wdb_global_sync_agent_groups_get_exec_fail_get_hash_true_fail
case makes hash retrieval fail. It expects Cannot obtain the global group hash,
returns WDBC_ERROR, and leaves the data envelope available as:

~~~json
[{"data":[]}]
~~~

### Synchronization-status update failure

test_wdb_global_sync_agent_groups_get_set_synced_error returns one agent and
its groups, enables set_synced, and makes WDB_STMT_GLOBAL_GROUP_SYNC_SET
unavailable. The returned data remains:

~~~json
[{"data":[{"id":1,"groups":["default","new_group"]}]}]
~~~

The operation logs Cannot set group_sync_status for agent 1 and returns
WDBC_ERROR. This is an important partial-result contract: the read result is
preserved even though the write-back failed.

### Response buffer full

test_wdb_global_sync_agent_groups_get_due_buffer_full creates an artificially
large group list and verifies WDBC_DUE. The test intentionally uses 5,000
group names; production constraints normally limit an agent to
MAX_GROUPS_PER_MULTIGROUP and bounded group-name lengths. The synthetic data
exists only to force the response-size branch.

## Interaction and data flow

~~~mermaid
sequenceDiagram
    participant T as CMocka test
    participant G as sync_agent_groups_get
    participant DB as SQLite wrappers
    participant M as Group membership helper
    participant S as Sync-status setter
    participant H as Global hash provider
    participant J as cJSON response

    T->>G: condition, cursor, flags, cutoff delta
    G->>DB: begin transaction and cache statement
    G->>DB: bind cursor and current_time - delta
    G->>DB: execute agent query
    alt query returns agents
        loop each agent
            G->>M: select group membership
            M-->>G: group-name array
            G->>J: append id and groups
            opt set_synced
                G->>S: mark agent group state synchronized
                S-->>G: success or error
            end
        end
    else no agents or query result is empty
        G->>J: retain empty data array
    end
    opt get_hash
        G->>H: obtain global group hash
        H-->>G: hash, null value, or failure
        G->>J: append hash when successful
    end
    G-->>T: cJSON envelope and WDBC_OK/DUE/ERROR
~~~

## Result semantics

| Result | Meaning in this module |
|---|---|
| WDBC_OK | Request completed; the response may contain zero or more agents and optionally a hash. |
| WDBC_DUE | The response exceeded the transport/database response budget; the caller should retry with a smaller page or advanced cursor. |
| WDBC_ERROR | Validation, transaction, statement, binding, hash, or synchronization-status handling failed. |

The tests distinguish transport-size exhaustion from ordinary database
failure. A size-full result can retain a non-null partial response and return
WDBC_DUE, while transaction, binding, or hash failures return WDBC_ERROR.

## Fixture and ownership model

~~~mermaid
flowchart TD
    Start([test case starts]) --> Setup[test_setup]
    Setup --> WDB[allocate wdb_t, id=global, db placeholder]
    Setup --> Conf[wdb_init_conf]
    Setup --> Out[allocate output buffer]
    WDB --> Invoke[configure wrappers and invoke target]
    Conf --> Invoke
    Out --> Invoke
    Invoke --> Assert[serialize JSON and assert result]
    Assert --> Delete[delete returned cJSON trees]
    Delete --> Teardown[test_teardown]
    Teardown --> Free[free output, id, db, wdb]
    Free --> End[wdb_free_conf]
~~~

The tests explicitly delete mock and returned cJSON objects after assertions.
Wrapper expectations are branch-specific: for example, the invalid-condition
case does not configure transaction calls, proving that validation occurs
before database access. The fixture is shared with the other focused pages
generated from test_wdb_global.c.

## Maintenance notes

- Keep cursor and cutoff assertions synchronized with the production query
  parameters. The cutoff is derived from mocked time() and the supplied
  agent_registration_delta.
- Preserve the distinction between WDBC_DUE and WDBC_ERROR; callers use
  WDBC_DUE to continue pagination or synchronization in a later request.
- If the JSON envelope changes, update the exact serialized assertions in the
  no-condition, no-agent, hash-failure, and set-synced cases.
- Changes to group membership selection should be reviewed with
  [select_group_belong_tests](select_group_belong_tests.md).
- Changes to hash generation or response decoration should be reviewed with
  [add_global_group_hash_to_response_tests](add_global_group_hash_to_response_tests.md)
  and [recalculate_all_agent_groups_hash_tests](recalculate_all_agent_groups_hash_tests.md).
- Changes to group synchronization writes should be reviewed with
  [set_agent_groups_sync_status_tests](set_agent_groups_sync_status_tests.md)
  and the production [wazuh_db_global](wazuh_db_global.md) documentation.

## Source references

- [test_wdb_global.c](../../src/unit_tests/wazuh_db/test_wdb_global.c)
- [test_wdb_global](test_wdb_global.md)
- [wazuh_db_global](wazuh_db_global.md)
- [select_group_belong_tests](select_group_belong_tests.md)
- [add_global_group_hash_to_response_tests](add_global_group_hash_to_response_tests.md)
- [set_agent_groups_sync_status_tests](set_agent_groups_sync_status_tests.md)
