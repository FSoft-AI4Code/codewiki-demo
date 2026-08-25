# CLI Utilities & Migration Tools

## Purpose

The `CLI_Utilities_&_Migration_Tools` module provides administrative and diagnostic command-line tools for Wazuh. It covers:

- Native utilities for agent control, configuration validation, and regex testing.
- Python tools for building and unpacking signed agent-upgrade packages.
- Migration of legacy FIM records into Wazuh DB.
- Concurrent querying of the Wazuh DB daemon through its Unix socket.

These tools are intentionally thin interfaces. Core responsibilities such as agent state management, database persistence, upgrade orchestration, FIM scanning, and protocol handling remain in their respective framework or daemon modules.

## Architecture

```mermaid
flowchart TD
    Operator[Administrator / Developer] --> CLI[CLI utilities]

    subgraph Tools[CLI Utilities & Migration Tools]
        Util[src/util]
        Upgrade[tools/agent-upgrade]
        Migration[tools/migration]
        WDBTools[tools/wdb]
    end

    CLI --> Util
    CLI --> Upgrade
    CLI --> Migration
    CLI --> WDBTools

    Util --> Agent[Agent and remoted services]
    Util --> Config[Configuration and regex libraries]

    Upgrade --> Package[Signed .wpk packages]
    Package --> AgentUpgrade[Agent upgrade module]

    Migration --> Legacy[Legacy syscheck files]
    Migration --> WDB[Wazuh DB daemon]
    WDBTools --> WDB

    WDB --> Storage[(Wazuh DB / FIM data)]
```

### Operational flow

```mermaid
sequenceDiagram
    participant User as Operator
    participant Tool as CLI tool
    participant Runtime as Runtime or transport layer
    participant Core as Wazuh core component
    participant Output as Terminal / package / database

    User->>Tool: Invoke command or provide input
    Tool->>Runtime: Parse arguments and prepare context
    Runtime->>Core: Execute operation or send request
    Core-->>Runtime: Result or error
    Runtime-->>Tool: Process response
    Tool-->>Output: Print result, create artifact, or persist migration data
```

### Component organization

```mermaid
flowchart LR
    subgraph Native[Native CLI utilities]
        AC[agent_control]
        LA[list_agents]
        PR[parallel-regex]
        VC[verify-agent-conf]
        WR[wazuh-regex]
    end

    subgraph Python[Python administration tools]
        Pack[wpkpack.py]
        Unpack[wpkunpack.py]
        FIM[fim_migrate.py]
        Query[wdb-query.py]
    end

    Native --> Shared[Shared libraries, configuration, remoted, regex]
    Pack --> Signed[Signed WPK artifact]
    Unpack --> Extract[Verified extracted files]
    FIM --> DB[Wazuh DB socket]
    Query --> DB
```

## Child modules

| Component | Description | Documentation |
|---|---|---|
| `util_cli_tools` | Native utilities for agent operations, configuration checks, and regex diagnostics | [util_cli_tools.md](util_cli_tools.md) |
| `tools_agent_upgrade` | Builds, signs, verifies, and extracts `.wpk` agent-upgrade packages | [tools_agent_upgrade.md](tools_agent_upgrade.md) |
| `tools_migration` | Migrates legacy syscheck/FIM records and scan metadata into Wazuh DB | [tools_migration.md](tools_migration.md) |
| `tools_wdb` | Concurrent command-line client for framed queries to `wazuh-db` | [tools_wdb.md](tools_wdb.md) |

## Core component references

- [Agent module](agent_module.md) — agent state, metadata, and management operations.
- [Framework communication](framework_core_communication.md) — sockets, queues, and Wazuh inter-process communication.
- [Framework core utilities](framework_core_utils.md) — paths, runtime helpers, and result handling.
- [Wazuh DB engine](wazuh_db_engine.md) — database execution and persistence.
- [Wazuh DB command parser](wazuh_db_command_parser.md) — textual database commands and request dispatch.
- [Syscheck FIM database](syscheckd_db.md) — ownership and persistence of FIM records.
- [Agent upgrade module](agent_upgrade_module.md) — manager-side package transfer and upgrade orchestration.
- [Agent upgrade configuration](Wmodules_Config_agent_upgrade.md) — package repository and upgrade settings.
- [OS crypto](os_crypto.md) — cryptographic primitives relevant to package signing and verification.