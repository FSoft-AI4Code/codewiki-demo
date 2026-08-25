# `test_wdb_syscollector`

## Purpose

`test_wdb_syscollector` is a CMocka unit-test module for the Wazuh DB syscollector persistence layer. It validates parsing, transaction handling, SQLite statement caching, inserts, updates/replacements, deletions, constraint behavior, null values, and error paths for system-inventory data.

Covered inventory domains include:

- Processes
- Packages and hotfixes
- Network interfaces, protocols, and addresses
- Hardware and operating-system information
- Ports
- Users and groups
- JSON-based `wdb_syscollector_save2()` ingestion

## Architecture

### Test architecture

```mermaid
flowchart TD
    T[test_wdb_syscollector.c]
    T --> S[Setup and teardown fixtures]
    T --> C[CMocka test cases]
    C --> W[Wrapper mocks]
    W --> J[cJSON wrappers]
    W --> Q[SQLite wrappers]
    W --> D[Wazuh DB wrappers]
    C --> F[wdb_syscollector.c]
    F --> TX[Transaction management]
    F --> ST[Prepared statement cache]
    F --> SQL[SQLite persistence]
    SQL --> DB[Agent Wazuh DB]
```

The test fixture creates a lightweight `wdb_t` instance and injects mocked cJSON, SQLite, logging, transaction, and statement-cache behavior. Tests then assert return codes, bound values, transaction failures, SQL constraints, and cleanup behavior.

### Syscollector persistence flow

```mermaid
sequenceDiagram
    participant P as Syscollector payload
    participant S as wdb_syscollector_save2()
    participant A as Component adapter
    participant W as wdb_*_save()
    participant I as wdb_*_insert()
    participant DB as SQLite agent database

    P->>S: JSON payload + component
    S->>S: Parse JSON and extract attributes
    S->>A: Dispatch by component
    A->>W: Convert attributes to typed fields
    W->>W: Begin transaction if needed
    W->>I: Insert or replace inventory row
    I->>DB: Cache statement, bind values, execute
    DB-->>I: Success or SQLite error
    I-->>W: Persistence result
    W-->>S: Component result
```

## Repository structure

```text
src/unit_tests/wazuh_db/
└── test_wdb_syscollector.c
    ├── test infrastructure
    ├── groups tests
    ├── hardware tests
    ├── hotfix tests
    ├── netaddr tests
    ├── netinfo tests
    ├── netproto tests
    ├── osinfo tests
    ├── package tests
    ├── port tests
    ├── process tests
    ├── syscollector_save2 tests
    └── users tests
```

## Core component references

- [Syscollector DB implementation](src/wazuh_db/wdb_syscollector.c)
- [Wazuh DB public interfaces and component types](src/wazuh_db/wdb.h)
- [Wazuh DB SQLite statements and schema integration](src/wazuh_db/wdb.c)
- [Agent database schema](src/wazuh_db/schema_agents.sql)
- [Python syscollector API](framework/wazuh/syscollector.py)
- [Python syscollector query and element types](framework/wazuh/core/syscollector.py)
- [System information provider](src/data_provider/include/sysInfo.hpp)
- [DBsync shared infrastructure](src/shared_modules/dbsync)
- [Inventory harvester module](src/wazuh_modules/inventory_harvester)