# `process_deleted_groups` Tests

## Introduction

This module documents the CMocka tests for the deleted-group maintenance paths in Wazuh `remoted`. The tests exercise `process_deleted_groups()` and `process_deleted_multi_groups()` from `src/remoted/manager.c`, including hash traversal, stale-record removal, multigroup directory cleanup, initial-scan handling, and fixture cleanup.

These tests are a focused slice of the broader [remoted group management](remoted_group_management.md) subsystem. They do not build merged configuration files or process agent control messages; those responsibilities are covered by the wider [test manager remoted test infrastructure](test_manager_remoted_test_infrastructure.md).

## Purpose and system position

During the periodic shared-configuration refresh, `remoted` reconstructs the set of groups currently present on disk and the multigroups currently reported by Wazuh DB. Records that were present during a previous refresh but are not present in the current scan must be retired. The functions under test perform that retirement before the next refresh is committed.

```mermaid
flowchart LR
    REFRESH[Periodic shared-file refresh] --> DISCOVER[Discover groups and multigroups]
    DISCOVER --> STATE[groups / multi_groups OSHash state]
    STATE --> CLEAN[Deleted-group processing]
    CLEAN --> KEEP[Retained records marked not-current]
    CLEAN --> REMOVE[Stale records removed]
    REMOVE --> DIR[Remove multigroup hash directory]
    KEEP --> NEXT[Next refresh cycle]
    DIR --> NEXT
```

For daemon architecture, lifecycle, database integration, and shared-file generation, see [remoted](remoted.md), [remoted group management](remoted_group_management.md), and [wazuh_db](wazuh_db.md).

## Architecture

The test translation unit includes the production implementation directly. This makes static functions and global hashes observable, while CMocka wrappers isolate filesystem and hash operations.

```mermaid
graph TB
    subgraph Test[process_deleted_groups test slice]
        CMOCKA[CMocka runner]
        TEST[test_manager.c test cases]
        FIX[Group and hash fixtures]
        CMOCKA --> TEST
        TEST --> FIX
    end

    subgraph Production[Included production code]
        MANAGER[src/remoted/manager.c]
        SINGLE[process_deleted_groups]
        MULTI[process_deleted_multi_groups]
        MANAGER --> SINGLE
        MANAGER --> MULTI
    end

    subgraph State[In-memory state]
        GROUPS[groups: OSHash of group_t]
        MGROUPS[multi_groups: OSHash of group_t]
        MHASH[m_hash: discovered multigroup hashes]
    end

    subgraph Boundaries[Wrapped boundaries]
        HASH[OSHash_Begin / Next / Delete_ex / Clean / Create]
        CRYPTO[OS_SHA256_String]
        FS[cldir_ex_ignore / rmdir_ex]
    end

    TEST --> MANAGER
    FIX --> GROUPS
    FIX --> MGROUPS
    FIX --> MHASH
    SINGLE --> GROUPS
    MULTI --> MGROUPS
    MULTI -. initial scan .-> MHASH
    MANAGER --> HASH
    MULTI --> CRYPTO
    MULTI --> FS
```

### Components

| Component | Responsibility in this test slice |
| --- | --- |
| `test_manager.c` | Registers the tests and programs CMocka expectations. |
| `manager.c` | Supplies the production deletion and retention logic. |
| `groups` | Hash of single-group `group_t` records. |
| `multi_groups` | Hash of comma-separated multigroup records. |
| `m_hash` | Hash representing discovered multigroup directories during an initial scan. |
| `group_t.exists` | Per-refresh presence marker. A false value identifies a stale record when cleanup runs. |
| `OSHash_*` wrappers | Make iteration, deletion, cleanup, and allocation deterministic. |
| `OS_SHA256_String` and `rmdir_ex` wrappers | Verify the multigroup name-to-directory cleanup path without deleting real data. |

The `group_t` objects used by the tests contain at least a name, `exists`, `has_changed`, and file-time/checksum state. Their complete ownership and use are described in [remoted group management](remoted_group_management.md).

## Data flow

```mermaid
flowchart TD
    A[Previous hash contents] --> B[OSHash_Begin]
    B --> C{Next node?}
    C -- no --> Z[Finish cleanup]
    C -- yes --> D[Read group_t.exists]
    D -- false --> E[Delete by node key]
    E --> F[Clean deleted record resources]
    D -- true --> G[Retain record]
    F --> H[Advance OSHash_Next]
    G --> H
    H --> C

    M[Deleted multigroup name] --> N[OS_SHA256_String]
    N --> O[Hash-derived directory name]
    O --> P[rmdir_ex(var/multigroups/<hash-prefix>)]
```

The tests show an important refresh-cycle convention: records that survive the pass are expected to remain available but have `exists == false` afterward. This resets the presence marker so the next discovery pass can mark observed records again. A record already marked absent is removed from the hash and its associated resources are cleaned.

For multigroups, the logical key is the comma-separated group list, while the on-disk directory is derived from its SHA-256 value. The deletion test verifies the expected short directory path (`var/multigroups/6e3a1077` for the programmed digest) is passed to `rmdir_ex`.

## Process flows

### Single groups

```mermaid
sequenceDiagram
    participant T as Test
    participant G as groups hash
    participant P as process_deleted_groups()
    participant H as OSHash wrappers

    T->>G: Install group nodes and exists flags
    T->>P: Invoke cleanup
    P->>H: OSHash_Begin(groups)
    loop Each node
        P->>H: OSHash_Next(groups)
        alt exists == false
            P->>H: OSHash_Delete_ex(groups, node key)
            P->>H: Cleanup deleted record/hash state
        else exists == true
            P->>P: Retain record and reset presence marker
        end
    end
    P-->>T: Updated hash state
    T->>T: Assert deletion, retained names, and flags
```

`test_process_deleted_groups_delete` verifies that `test_default` is deleted while iteration continues to `test_test_default`. `test_process_deleted_groups_no_changes` verifies the no-deletion branch when both entries are initially present.

### Multigroups

```mermaid
sequenceDiagram
    participant T as Test
    participant I as m_hash
    participant M as multi_groups
    participant P as process_deleted_multi_groups(initial_scan)
    participant FS as Filesystem wrappers

    alt initial_scan == true
        P->>I: Inspect discovered directory hashes
        P->>FS: cldir_ex_ignore(var/multigroups)
    end
    T->>M: Install multigroup records
    P->>M: Iterate records
    alt record is stale
        P->>M: Delete logical multigroup key
        P->>FS: SHA-256 name, then rmdir_ex(hash directory)
    else record is retained
        P->>P: Reset presence marker
    end
    P-->>T: Updated multigroup state
```

The `initial_scan` flag adds cleanup of directory state discovered before the in-memory multigroup map is rebuilt. The initial-scan test specifically verifies this pre-processing while still retaining the currently supplied multigroup records.

## Test cases and coverage

| Test | Scenario | Expected behavior |
| --- | --- | --- |
| `test_process_deleted_groups_delete` | One group has `exists == false`; another is present. | Delete the stale key, clean its resources, continue iteration, and reset the retained record’s presence marker. |
| `test_process_deleted_groups_no_changes` | Both single-group records are present. | No `OSHash_Delete_ex` call; records remain in the hash and are reset for the next scan. |
| `test_process_deleted_multi_groups_delete` | One multigroup is stale and `initial_scan == false`. | Delete the stale logical key and remove its hash-derived directory. |
| `test_process_deleted_multi_groups_no_changes` | Both multigroup records are present and `initial_scan == false`. | Do not delete records or directories; reset presence markers. |
| `test_process_deleted_multi_groups_no_changes_initial_scan` | Both records are present and `initial_scan == true`. | Clean the discovered multigroup-directory index, then process current records without deletion. |

The test registration also attaches setup and teardown functions. These are not production behavior tests; they establish ownership and prevent group objects, names, and hashes from leaking across cases.

## Fixtures and isolation

```mermaid
flowchart LR
    SETUP[test_process_deleted_groups_setup] --> ALLOC[Allocate two group_t records]
    ALLOC --> FLAGS[Initialize names and state]
    FLAGS --> TEST[Run test]
    TEST --> TEARDOWN[test_process_deleted_groups_teardown]
    TEARDOWN --> FREE[free_group_c_group for each fixture]

    HSETUP[test_process_deleted_multi_groups_setup] --> MALLOC[Allocate multigroup fixtures]
    MALLOC --> MTEST[Run multigroup test]
    MTEST --> MTEARDOWN[Shared group cleanup]
```

The deletion tests use mocked `OSHashNode` values so the iterator sequence is explicit. The tests free those mock nodes after the function returns. Hashes and nested `f_time` state are supplied by the broader group fixtures when required; the suite’s general ownership rules are documented in [test manager remoted test infrastructure](test_manager_remoted_test_infrastructure.md).

## Behavioral contract captured by the tests

The tests collectively specify these invariants:

- Cleanup iterates the complete hash, including the node after a deleted entry.
- A stale entry is deleted by its hash key, not by a reconstructed group name.
- Retained entries are not physically removed during this pass.
- Presence flags are cycle markers and are reset after processing.
- Multigroup cleanup distinguishes the logical comma-separated key from the hash-derived filesystem directory.
- Initial-scan cleanup may inspect the discovered directory hash map before normal multigroup retirement.
- All hash and filesystem effects are observable through wrapper expectations, so accidental extra deletion or cleanup calls fail the test.

## Scope and related documentation

This page intentionally does not duplicate the implementation details of group discovery, merged-file generation, checksum comparison, or agent delivery. Follow these references for those concerns:

- [remoted group management](remoted_group_management.md) — production group, multigroup, and shared-file workflows.
- [test manager remoted test infrastructure](test_manager_remoted_test_infrastructure.md) — complete fixture, wrapper, and test-suite conventions.
- [remoted](remoted.md) — daemon architecture and lifecycle integration.
- [shared library](shared_lib.md) — `OSHash`, filesystem, and crypto utility abstractions.
- [wazuh_db](wazuh_db.md) — source of distinct agent multigroup combinations.

