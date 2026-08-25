# OS Execd Remote Commands

## Introduction

The **OS Execd Remote Commands** module implements the local command-and-control (C2) interface of the `wazuh-execd` daemon. It exposes a Unix domain socket server (`wcom_main`) that accepts textual requests from trusted local processes — primarily the Wazuh Agent/Manager control tooling and the cluster/API layer — and dispatches them to a family of handler functions (`wcom_unmerge`, `wcom_uncompress`, `wcom_restart`, `wcom_reload`, `wcom_getconfig`, `wcom_check_manager_config`).

This module is the **remote-control surface** of the Active Response execution engine: it allows the rest of the system (installers, upgrade modules, the API, cluster daemon) to instruct `execd` to unpack/verify files delivered during an agent upgrade, restart or reload the Wazuh service, retrieve runtime configuration sections, or validate a manager's configuration before an actual restart. It does **not** execute Active Response scripts itself — that responsibility belongs to the sibling `os_execd_response_engine` module — but it is one of the primary triggers that leads to script execution (e.g., via the `restart-wazuh.exe`/`restart.sh` active-response scripts).

It is a child module of `os_execd` (see [os_execd_daemon_lifecycle.md](os_execd_daemon_lifecycle.md) and [os_execd_response_engine.md](os_execd_response_engine.md) for sibling documentation), and sits within the broader [Agent & Manager Native Daemons (C)](Agent_%26_Manager_Native_Daemons_(C).md) subsystem.

---

## 1. Purpose and Core Functionality

The single source file in this module, `src/os_execd/wcom.c`, provides:

| Responsibility | Function(s) |
|---|---|
| Parse and route incoming socket commands | `wcom_dispatch` |
| Unmerge a bundled file archive (used after WPK/agent upgrade transfers) | `wcom_unmerge` |
| Decompress a gzip-compressed file delivered to the incoming directory | `wcom_uncompress` |
| Trigger a full Wazuh service restart (agent or manager) | `wcom_restart` |
| Trigger a configuration reload without a full restart | `wcom_reload` |
| Retrieve a JSON snapshot of a configuration section (`active-response`, `logging`, `internal`, `cluster`) | `wcom_getconfig` |
| Dry-run `-t` (test) every Wazuh daemon binary to validate a manager configuration before applying it | `wcom_check_manager_config` |
| Serve requests over a local Unix domain socket (`COM_LOCAL_SOCK`) | `wcom_main` |
| Prevent restarts while an upgrade/lock window is active | `lock_restart` |
| Sanitize file paths supplied by the caller to prevent directory traversal | `_jailfile` (static) |

The `wcom_dispatch` function is the **single entry point** exercised by all callers (and by the unit tests in `Unit_Tests_-_OS_Execd`). It parses a space-delimited command line, matches the verb, and calls the corresponding handler, always producing a printable `ok`/`err`-prefixed string response.

---

## 2. Architecture

### 2.1 Component Placement

```mermaid
graph TB
    subgraph os_execd["os_execd daemon"]
        direction TB
        Lifecycle["os_execd_daemon_lifecycle<br/>(main.c)"]
        RespEngine["os_execd_response_engine<br/>(execd.c, exec.c)<br/>Active Response execution"]
        RemoteCmds["os_execd_remote_commands<br/>(wcom.c) - THIS MODULE"]
    end

    Lifecycle -->|spawns thread| RemoteCmds
    Lifecycle -->|initializes queues/timers| RespEngine
    RemoteCmds -.->|shares pending_upg lock flag| RespEngine

    ClusterD["wazuh-clusterd<br/>(cluster_module)"] -->|"getconfig cluster"| RemoteCmds
    APIManager["Manager API controller<br/>(manager_module)"] -->|"restart / getconfig"| RemoteCmds
    AgentUpgrade["Agent Upgrade Module<br/>(agent_upgrade_module)"] -->|"unmerge / uncompress"| RemoteCmds
    InstallerTools["Installer / addagent tooling"] -->|"check-manager-configuration"| RemoteCmds

    RemoteCmds --> SharedLib["shared_lib<br/>(file_op, os_net, os_xml)"]
    RemoteCmds --> OsNet["os_net<br/>Unix domain socket I/O"]
    RemoteCmds --> WmExec["wazuh_modules_core<br/>wm_exec (process spawning)"]

    style RemoteCmds fill:#f9d77e,stroke:#333,stroke-width:2px
```

### 2.2 Internal Structure

```mermaid
classDiagram
    class wcom_main {
        +void* wcom_main(void* arg)
        -bind COM_LOCAL_SOCK
        -accept loop
        -OS_RecvSecureTCP / OS_SendSecureTCP
    }
    class wcom_dispatch {
        +size_t wcom_dispatch(char* command, char** output)
        -parses verb + args
        -routes to handler
    }
    class wcom_unmerge
    class wcom_uncompress
    class wcom_restart
    class wcom_reload
    class wcom_getconfig
    class wcom_check_manager_config
    class _jailfile {
        -static int _jailfile(finalpath, basedir, filename)
        -prevents path traversal
    }
    class lock_restart {
        +size_t lock_restart(int timeout)
        -sets pending_upg
    }

    wcom_main --> wcom_dispatch : forwards received buffer
    wcom_dispatch --> wcom_unmerge
    wcom_dispatch --> wcom_uncompress
    wcom_dispatch --> wcom_restart
    wcom_dispatch --> wcom_reload
    wcom_dispatch --> wcom_getconfig
    wcom_dispatch --> wcom_check_manager_config
    wcom_dispatch --> lock_restart : "lock_restart <timeout>"
    wcom_unmerge --> _jailfile
    wcom_uncompress --> _jailfile
```

---

## 3. Data Flow

### 3.1 Request/Response Sequence

```mermaid
sequenceDiagram
    participant Caller as Local Client<br/>(API/CLI/Cluster/Upgrade module)
    participant Sock as COM_LOCAL_SOCK<br/>(Unix Domain Socket)
    participant Main as wcom_main()
    participant Dispatch as wcom_dispatch()
    participant Handler as Handler<br/>(e.g. wcom_restart)
    participant OS as OS / Filesystem / Subprocess

    Caller->>Sock: connect() + send("restart")
    Sock->>Main: accept() + OS_RecvSecureTCP()
    Main->>Dispatch: wcom_dispatch(buffer, &response)
    Dispatch->>Dispatch: split verb / args
    Dispatch->>Handler: wcom_restart(&response)
    Handler->>OS: fork()+execv() / wpopenv() (restart-wazuh script)
    OS-->>Handler: process spawned
    Handler-->>Dispatch: "ok " or "err ..."
    Dispatch-->>Main: response string
    Main->>Sock: OS_SendSecureTCP(peer, length, response)
    Sock-->>Caller: response
    Main->>Main: close(peer), loop back to select()
```

### 3.2 Command Routing Logic (`wcom_dispatch`)

```mermaid
flowchart TD
    Start([Receive command buffer]) --> Split[Split at first space:<br/>verb + args]
    Split --> Check{verb value}
    Check -->|unmerge| Unmerge[wcom_unmerge<br/>args = file_path]
    Check -->|uncompress| Uncompress[wcom_uncompress<br/>args = source target]
    Check -->|restart / restart-wazuh| Restart[wcom_restart]
    Check -->|reload| Reload[wcom_reload]
    Check -->|lock_restart| Lock[lock_restart timeout]
    Check -->|getconfig| GetConfig[wcom_getconfig section]
    Check -->|check-manager-configuration| CheckCfg[wcom_check_manager_config]
    Check -->|unknown| Err[return 'err Unrecognized command']

    Unmerge --> Jail1[_jailfile validates path]
    Uncompress --> Jail2[_jailfile validates path x2]
    GetConfig --> Section{section name}
    Section -->|active-response| AR[getARConfig]
    Section -->|logging| Log[getLoggingConfig]
    Section -->|internal| Int[getExecdInternalOptions]
    Section -->|cluster| Clu[connect CLUSTER_SOCK + getClusterConfig]
    Section -->|other| ErrSec[err Could not get requested section]

    Restart --> PendingCheck{pending_upg - now <= 0?}
    Reload --> PendingCheck2{pending_upg - now <= 0?}
    PendingCheck -->|yes| Exec[fork/execv restart script<br/>or restart-wazuh.exe]
    PendingCheck -->|no| Locked[log LOCK_RES, skip restart]
    PendingCheck2 -->|yes| ExecReload[fork/execv restart script reload<br/>or restart-wazuh.exe]
    PendingCheck2 -->|no| Locked2[log LOCK_RES, skip reload]
```

---

## 4. Component Interaction with Other Modules

The remote-command handlers are thin orchestrators; the real work is delegated to functionality owned by other modules/subsystems in the codebase:

| Handler | Delegates to | Related Module |
|---|---|---|
| `wcom_unmerge` | `UnmergeFiles()` | [shared_lib](Agent_%26_Manager_Native_Daemons_(C).md) (`src/shared/file_op.c`) |
| `wcom_uncompress` | `gzopen/gzread` (zlib) | External zlib bundled in `src/external` |
| `wcom_restart` / `wcom_reload` | `fork/execv`, `wpopenv/wpclose` (`wm_exec`) | [wazuh_modules_core](Wazuh_Modules_Daemon_(C).md) |
| `wcom_getconfig("active-response")` | `getARConfig()` | [os_execd_response_engine](os_execd_response_engine.md) / Active Response config (`src/config/active-response.h`, see [Active_Response_Config.md](Active_Response_Config.md)) |
| `wcom_getconfig("internal")` | `getExecdInternalOptions()` | [os_execd_response_engine](os_execd_response_engine.md) (`execd.c`) |
| `wcom_getconfig("cluster")` | `OS_ConnectUnixDomain`, `getClusterConfig()` | [cluster_module](cluster_module.md) (via `CLUSTER_SOCK`) |
| `wcom_check_manager_config` | `wm_exec()` to run `<daemon> -t` for every daemon binary | All native daemons (`wazuh-authd`, `wazuh-remoted`, `wazuh-execd`, `wazuh-analysisd`, `wazuh-logcollector`, `wazuh-syscheckd`, `wazuh-modulesd`, `wazuh-clusterd`) |
| `wcom_main` (socket I/O) | `OS_BindUnixDomain`, `OS_RecvSecureTCP`, `OS_SendSecureTCP` | [os_net](Agent_%26_Manager_Native_Daemons_(C).md) |
| `_jailfile` | `w_ref_parent_folder()` | [shared_lib](Agent_%26_Manager_Native_Daemons_(C).md) |

```mermaid
graph LR
    subgraph This["os_execd_remote_commands"]
        wcom["wcom.c"]
    end

    wcom --> os_net["os_net<br/>Unix domain socket send/recv"]
    wcom --> file_op["shared/file_op.c<br/>UnmergeFiles, w_ref_parent_folder"]
    wcom --> os_xml["os_xml<br/>OS_ReadXML/OS_ClearXML"]
    wcom --> wm_exec["wazuh_modules_core<br/>wm_exec (spawn/verify daemon -t)"]
    wcom --> execd_h["os_execd_response_engine<br/>getARConfig, getLoggingConfig,<br/>getExecdInternalOptions, pending_upg"]
    wcom --> zlib["external/zlib<br/>gzopen/gzread"]
    wcom -.optional.-> cluster["cluster_module<br/>CLUSTER_SOCK / getClusterConfig"]

    Callers["Callers:<br/>Agent Upgrade Module,<br/>Manager API,<br/>Cluster daemon,<br/>CLI tools"] -->|Unix socket requests| wcom
```

---

## 5. Protocol Details

The wire protocol is a simple, human-readable, space-delimited request/response format (consistent with other `*com.c` modules across the codebase, e.g. `syscom_dispatch`, `moncom_dispatch`, `authcom_dispatch`, `wdbcom_dispatch`):

### Supported Commands

| Command | Arguments | Description |
|---|---|---|
| `unmerge <file_path>` | Path to a merged file inside `INCOMING_DIR` | Splits a merged bundle back into individual files |
| `uncompress <source> <target>` | Source (gz) and target paths inside `INCOMING_DIR` | Decompresses a `.gz` file |
| `restart` / `restart-wazuh` | none | Restarts the Wazuh service (agent or manager context) |
| `reload` | none | Reloads configuration without full restart |
| `lock_restart <timeout>` | Integer seconds, or `-1` for max | Prevents restarts for a time window (used during upgrades) |
| `getconfig <section>` | `active-response` \| `logging` \| `internal` \| `cluster` | Returns a JSON configuration snapshot |
| `check-manager-configuration` | none | Runs `-t` against every daemon binary to validate config sanity |

### Response Format
All responses begin with `ok ` (success, optionally followed by payload/JSON) or `err <message>` (failure).

```mermaid
sequenceDiagram
    participant C as Client
    participant W as wcom_dispatch
    C->>W: "getconfig active-response"
    W->>W: getARConfig() -> cJSON
    W-->>C: "ok {active-response:[...]}"

    C->>W: "lock_restart 30"
    W->>W: lock_restart(30) sets pending_upg = now+30
    W-->>C: "ok "

    C->>W: "restart"
    Note over W: pending_upg still in future
    W-->>C: response depends on lock state
```

> **Note on the lock window:** `wcom_restart`/`wcom_reload` check `pending_upg - time(NULL)`. If positive, the restart/reload is **not** executed but the function still logs `LOCK_RES`. This mechanism is used by the [agent_upgrade_module](agent_upgrade_module.md) to prevent races between an in-flight WPK upgrade and an external restart request.

---

## 6. Security Considerations

* **Path traversal protection:** `_jailfile()` calls `w_ref_parent_folder()` to reject any path containing `..` segments before concatenating it with `INCOMING_DIR`, mitigating directory-traversal attacks via the `unmerge`/`uncompress` commands.
* **Local-only exposure:** The socket (`COM_LOCAL_SOCK`) is a Unix domain socket, not network-exposed; only local processes with filesystem access to the socket path can issue commands.
* **Command validation:** Unrecognized verbs are rejected with `err Unrecognized command` rather than silently ignored.
* **Restart lock:** The `lock_restart`/`pending_upg` mechanism avoids self-inflicted denial-of-service during multi-step upgrade sequences (WPK transfer → verify → restart).

---

## 7. Process Lifecycle (`wcom_main`)

```mermaid
stateDiagram-v2
    [*] --> Bind: OS_BindUnixDomain(COM_LOCAL_SOCK)
    Bind --> BindFailed: bind() < 0
    BindFailed --> [*]: return NULL (thread exits)
    Bind --> WaitSelect: enter loop
    WaitSelect --> WaitSelect: select() timeout/EINTR
    WaitSelect --> Accept: socket ready
    Accept --> Recv: accept() succeeded
    Accept --> WaitSelect: accept() failed (EINTR)
    Recv --> Dispatch: OS_RecvSecureTCP() > 0
    Recv --> ClosePeer: recv error / empty / oversized
    ClosePeer --> WaitSelect
    Dispatch --> Send: wcom_dispatch() builds response
    Send --> ClosePeer2: OS_SendSecureTCP()
    ClosePeer2 --> WaitSelect
```

This loop runs on a dedicated thread spawned by the `os_execd` lifecycle (`main.c`, see [os_execd_daemon_lifecycle.md](os_execd_daemon_lifecycle.md)), alongside the Active Response execution loop in [os_execd_response_engine.md](os_execd_response_engine.md).

---

## 8. Related Documentation

- [os_execd_daemon_lifecycle.md](os_execd_daemon_lifecycle.md) — `main.c`, daemon startup/shutdown that spawns the `wcom_main` thread.
- [os_execd_response_engine.md](os_execd_response_engine.md) — `execd.c`/`exec.c`, the Active Response execution engine sharing the `pending_upg` lock and exposing `getARConfig`/`getExecdInternalOptions`.
- [agent_upgrade_module.md](agent_upgrade_module.md) — Sends `unmerge`/`uncompress`/`lock_restart`/`restart` commands during agent WPK upgrades (see also `wm_agent_upgrade_com.c` which implements an analogous protocol on the agent's upgrade module socket).
- [cluster_module.md](cluster_module.md) — Consumer of `getconfig cluster`, connects to `CLUSTER_SOCK` verified by this module.
- [manager_module.md](manager_module.md) — The Manager API `put_restart`/`get_configuration` endpoints ultimately trigger requests handled here.
- [Active_Response_Config.md](Active_Response_Config.md) — Structure of the `active-response` configuration section returned by `wcom_getconfig`.
- Sibling `*com.c` protocol implementations for cross-reference: `os_auth` (`authcom_dispatch`), `logcollector` (`lccom_dispatch`), `monitord` (`moncom_dispatch`), `wazuh_db` (`wdbcom_dispatch`), `syscheckd` (`syscom_dispatch`) — all documented under [Agent_&_Manager_Native_Daemons_(C).md](Agent_%26_Manager_Native_Daemons_(C).md).
- [shared_lib](Agent_%26_Manager_Native_Daemons_(C).md) — Provides `UnmergeFiles`, `w_ref_parent_folder`, and other filesystem helpers used by `wcom_unmerge`/`_jailfile`.
- Unit tests: `Unit_Tests_-_OS_Execd` (`os_execd_test_execd`, `os_execd_test_win_execd`, `os_execd_test_get_command_by_name`) exercise the surrounding execd behavior; wcom-specific coverage relies on the shared `os_net`/`file_op` wrapper mocks under `Unit_Test_Wrappers_&_Mocks`.
