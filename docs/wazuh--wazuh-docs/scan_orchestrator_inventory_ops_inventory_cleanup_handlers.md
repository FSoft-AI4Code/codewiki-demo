# Inventory Cleanup Handlers

## Scope

`TCleanAgentInventory` and `TCleanInventory` remove persisted vulnerability inventory and invoke a supplied sub-orchestration to publish deletion events.

## Agent/component cleanup

`TCleanAgentInventory` scans rows by agent prefix. For `Agent`, it removes OS and package rows; for a specific affected type, it removes only that column’s rows. It emits `DELETED_BY_QUERY` for whole-agent cleanup, sets `m_isInventoryEmpty`, and removes OS initial-scan state for agent/OS cleanup.

## Full cleanup

`TCleanInventory` iterates the OS and package columns, deletes every matching row, and emits one `DELETED` event per CVE using the unique row/CVE key. It then clears `os_initial_scan`.

```mermaid
flowchart TD
  S[Cleanup context] --> A{Agent-wide?}
  A -- yes --> P[Seek rows by agent prefix]
  A -- no --> T[Seek rows for selected type]
  P --> D[Delete RocksDB rows]
  T --> D
  D --> Q[Sub-orchestration]
  Q --> IDX[Indexer deletion]
  ALL[Full cleanup] --> COL[OS and package columns]
  COL --> DEL[Delete every row and emit per-CVE events]
```

The sub-orchestration is an injected handler, keeping persistence cleanup separate from index publication.

## Source files

- `src/wazuh_modules/vulnerability_scanner/src/scanOrchestrator/cleanAgentInventory.hpp`
- `src/wazuh_modules/vulnerability_scanner/src/scanOrchestrator/cleanInventory.hpp`
