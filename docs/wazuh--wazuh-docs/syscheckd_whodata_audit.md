# Syscheckd Whodata Audit Module

## Introduction

The **Syscheckd Whodata Audit** module is the Linux-specific "who-data" subsystem of Wazuh's File Integrity Monitoring (FIM) daemon (`syscheckd`). It integrates with the Linux Audit subsystem (`auditd`) to capture **who** (user, process) performed a file system change, in addition to **what** changed. This enriches FIM alerts with attribution data (PID, UID, process name, command line) that plain inotify-based real-time monitoring cannot provide.

The module is responsible for:
- Verifying that `auditd` is installed, running, and properly configured to forward events to Wazuh via a Unix socket (`audisp`/`auditd` plugin).
- Adding and removing Linux Audit watch rules (`-w <path> -p wa -k wazuh_fim`) for directories configured with the `whodata` option.
- Performing a **health check** at startup to make sure that audit events actually reach the daemon before relying on this mode.
- Continuously reading raw audit events from the audit socket, buffering/caching partial records, and dispatching complete events for parsing.
- Falling back to realtime (inotify) monitoring for directories whose audit rules cannot be established or when the audit connection is lost.
- Reloading rules if they are externally deleted/tampered with, and cleaning them up on daemon shutdown.

This module is part of the [Syscheck / FIM Daemon (C/C++)](Syscheck___FIM_Daemon_(C_C++).md) parent module, alongside its siblings `syscheckd_core`, `syscheckd_db`, `syscheckd_ebpf` (the Linux eBPF-based alternative to audit), `syscheckd_file`, and `syscheckd_registry`.

---

## Purpose and Scope

| Concern | Description |
|---|---|
| **Startup validation** | Detects `auditd`, checks/repairs its plugin configuration, opens the audit netlink/unix socket. |
| **Health check** | Confirms the audit pipeline is functioning end-to-end before enabling whodata for real. |
| **Rule management** | Adds "watch" rules per configured directory; detects rules removed by users/other tools; reloads them periodically. |
| **Event ingestion** | Non-blocking `select()`-driven read loop that assembles multi-line audit records into complete events using an internal cache keyed by audit event ID. |
| **Dispatch** | Pushes assembled event strings onto an internal queue (`audit_queue`) consumed by a dedicated parser thread (`audit_parse_thread`). |
| **Graceful degradation** | Switches monitored directories back to `REALTIME_ACTIVE` (inotify) if audit rules cannot be applied or if the audit connection drops permanently. |

This module only compiles on Linux (`#ifdef __linux__`) and only when audit support is enabled (`#ifdef ENABLE_AUDIT`).

---

## Core Components

### Files and Symbols

| File | Symbol | Role |
|---|---|---|
| `src/syscheckd/src/whodata/syscheck_audit.h` | `whodata_directory_t` | Lightweight struct tracking a directory path pending removal from audit rules. |
| `src/syscheckd/src/whodata/syscheck_audit.c` | `audit_data_t` (`_audit_data_s`) | Internal struct bundling the audit socket FD and the detected audit mode (`AUDIT_DISABLED`/`AUDIT_ENABLED`/`AUDIT_IMMUTABLE`), passed to the main audit thread. |
| `src/syscheckd/src/whodata/syscheck_audit.c` | `timeval` (usage) | Used for `select()` timeout control in the event-reading loop. |
| `src/syscheckd/src/whodata/audit_healthcheck.c` | `timespec` (usage) | Used for timed condition waits (`pthread_cond_timedwait`) while waiting for the healthcheck thread to end. |

### Key Functions (from the referenced source, not exhaustive of the whole subsystem)

- `check_auditd_enabled()` – scans `/proc` for a running `auditd` process.
- `set_auditd_config()` / `configure_audisp()` – ensures the audisp/audit plugin configuration file points Wazuh's socket, restarts audit if configuration changed.
- `init_auditd_socket()` – connects to the Unix domain socket where audit events are forwarded.
- `audit_create_rules_file()` – writes a persistent rules file for **immutable** audit mode and symlinks it into `/etc/audit/rules.d/`.
- `audit_rules_to_realtime()` – for directories whose rule could not be verified (immutable mode), demotes them to `REALTIME_ACTIVE`.
- `audit_init()` – top-level orchestration: validates auditd, configures the socket, runs healthcheck, loads rules, and spawns the audit reading thread.
- `audit_main()` (static) – thread entry point that waits for DB consistency, optionally starts a rule-reload thread, then blocks in `audit_read_events()` until the daemon shuts down or the connection dies; on exit it converts whodata directories back to realtime and cleans regex/rules.
- `audit_read_events()` – the core `select()`-based loop that reads raw audit lines, correlates them by event ID, assembles multi-line records, and pushes completed events to `audit_queue` for the parser thread.
- `audit_parse_thread()` – pops assembled event strings from `audit_queue` and calls `audit_parse()` (defined elsewhere in the whodata parsing logic).
- `audit_health_check()` / `audit_healthcheck_thread()` (in `audit_healthcheck.c`) – creates/deletes a temporary watched file and confirms that the corresponding audit "create" event is received within a timeout window, validating the full audit → Wazuh event pipeline.
- `fim_manipulated_audit_rules()`, `fim_audit_rules_init()`, `fim_rules_initial_load()` (declared in the header, implemented in sibling files) – rule lifecycle management referenced by `audit_init()`.

---

## Architecture

```mermaid
graph TB
    subgraph Syscheckd_Daemon["syscheckd (FIM Daemon)"]
        Core[syscheckd_core<br/>fim_scan / run_check]
        Whodata[syscheckd_whodata_audit<br/>this module]
        EBPF[syscheckd_ebpf<br/>alternative whodata backend]
        FileMod[syscheckd_file]
        RegMod[syscheckd_registry]
        DB[syscheckd_db<br/>FIMDB]
    end

    AuditD[Linux auditd plus audisp plugin]
    Kernel[Linux Kernel Audit subsystem]
    Config[syscheck_config directory_t / whodata struct]
    Queue[Internal audit_queue w_queue_t]
    ParserThread[audit_parse_thread]
    RealtimeMod[syscheckd_core_realtime inotify fallback]

    Kernel -->|raw audit records| AuditD
    AuditD -->|unix socket AUDIT_SOCKET| Whodata
    Config -->|WHODATA_ACTIVE directories| Whodata
    Whodata -->|audit rules add/remove| AuditD
    Whodata -->|push assembled events| Queue
    Queue --> ParserThread
    ParserThread -->|FIM events| DB
    Whodata -->|demote on failure| RealtimeMod
    Core --> Whodata
    Core --> EBPF
    Core --> RealtimeMod
```

### Relationship to Sibling Modules

- **`syscheckd_ebpf`**: an alternative, more modern whodata implementation for Linux based on eBPF probes, avoiding the audit subsystem entirely. Both modules provide equivalent attribution data but via different kernel interfaces; only one is typically active depending on configuration/kernel capabilities.
- **`syscheckd_core_realtime`**: the inotify-based fallback. The audit module actively demotes directories to this mode (`REALTIME_ACTIVE`) whenever audit rules cannot be guaranteed (e.g., immutable audit mode without a matching rule, or persistent audit socket failure).
- **`syscheckd_core`**: owns the global `syscheck_config` (see [Configuration Data Structures](Configuration_Data_Structures_(C_Headers).md) → `Syscheck_Config`), including the `directory_t` list and the `whodata` struct that stores open file descriptors and per-directory state consulted by this module.
- **`syscheckd_db`**: consumes FIM events produced after the parser thread processes assembled audit records, ultimately persisting file state changes.
- Shared low-level utilities used by this module (mutexes, atomic ints, queues) come from [Agent & Manager Native Daemons (C)](Agent_&_Manager_Native_Daemons_(C).md) — specifically `src/headers/atomic.h`, `src/headers/queue_op.h`, and `src/shared/audit_op.c` (`audit_add_rule`, `audit_delete_rule`, `audit_get_rule_list`, `search_audit_rule`, etc.).

---

## Data Structures

```mermaid
classDiagram
    class whodata_directory_t {
        +char* path
        +int pending_removal
    }

    class audit_data_t {
        +int socket
        +audit_mode mode
    }

    class w_audit_rule {
        +char* path
        +int perm
        +char* key
    }

    class directory_t {
        +char* path
        +int options
        +int recursion_level
        +char* tag
        +is_wildcard bit
        +is_expanded bit
    }

    class whodata_config {
        +OSHash* fd
        +OSHash* directories
        +int interval_scan
        +char** device
        +char** drive
    }

    audit_data_t --> whodata_config : references via syscheck global
    directory_t --> w_audit_rule : mapped when WHODATA_ACTIVE
    whodata_directory_t --> directory_t : tracks removal state
```

- **`whodata_directory_t`**: used internally when a directory's whodata monitoring must be torn down (e.g. rule deletion in progress), tracking whether removal is `pending_removal`.
- **`audit_data_t`** (`_audit_data_s`): passed into the audit reading thread (`audit_main`), carrying the live socket descriptor and the detected `audit_mode` (`AUDIT_DISABLED`, `AUDIT_ENABLED`, `AUDIT_IMMUTABLE`) which determines whether rules are added live via netlink or written to a rules file for immutable mode.
- **`w_audit_rule`** (from shared `audit_op.h`, see [Agent & Manager Native Daemons](Agent_&_Manager_Native_Daemons_(C).md)): generic representation of an audit watch rule (path, permission mask, key) used both for adding rules and for querying/comparing existing ones (`search_audit_rule`).
- **`directory_t`** and **`whodata`** (from `src/config/syscheck-config.h`, see [Configuration Data Structures](Configuration_Data_Structures_(C_Headers).md) → `Syscheck_Config`): the configuration-side structures that declare which directories should be monitored in whodata mode (`WHODATA_ACTIVE` bit in `options`) and hold the open file descriptor hash used across FIM.

---

## Process Flows

### 1. Audit Subsystem Initialization (`audit_init`)

```mermaid
flowchart TD
    Start([audit_init]) --> CheckDaemon{auditd process<br/>running?}
    CheckDaemon -- No --> WarnNoRun[Warn: FIM_AUDIT_NORUNNING] --> Fail([Return -1])
    CheckDaemon -- Yes --> CheckConfig[set_auditd_config]
    CheckConfig -- error --> Fail
    CheckConfig -- ok --> OpenSocket[init_auditd_socket]
    OpenSocket -- fail --> Fail
    OpenSocket -- ok --> InitRegex[init_regex]
    InitRegex -- fail --> Fail
    InitRegex -- ok --> RuleListInit[fim_audit_rules_init]
    RuleListInit -- fail --> Fail
    RuleListInit -- ok --> QueueInit[queue_init + start audit_parse_thread]
    QueueInit --> HealthCheckEnabled{audit_healthcheck<br/>enabled?}
    HealthCheckEnabled -- Yes --> HC[audit_health_check]
    HC -- fail --> Fail
    HealthCheckEnabled -- No --> SkipHC[Log: healthcheck disabled]
    HC -- ok --> DetectMode
    SkipHC --> DetectMode[audit_is_enabled: detect mode]
    DetectMode --> ModeSwitch{Audit mode}
    ModeSwitch -- IMMUTABLE --> RulesFile[audit_create_rules_file<br/>+ audit_rules_to_realtime]
    ModeSwitch -- ENABLED --> LoadRules[fim_rules_initial_load<br/>+ atexit clean_rules]
    ModeSwitch -- DISABLED --> Fail
    RulesFile --> StartThread
    LoadRules --> StartThread[Start audit_main thread]
    StartThread --> WaitActive[Wait until thread signals active]
    WaitActive --> Done([Return 1: success])
```

### 2. Audit Health Check

```mermaid
sequenceDiagram
    participant Init as audit_init
    participant HC as audit_health_check
    participant Thread as audit_healthcheck_thread
    participant Audit as auditd
    participant FS as Filesystem

    Init->>HC: audit_health_check(socket)
    HC->>Audit: audit_add_rule(healthcheck dir, wazuh_hc key)
    HC->>Thread: w_create_thread(audit_healthcheck_thread)
    Thread->>HC: signal hc_thread_active = 1
    loop until timer expires or event detected
        HC->>FS: create healthcheck file
        FS-->>Audit: generates audit create event
        Audit-->>Thread: forwards event via audit_read_events
        Thread->>Thread: sets audit_health_check_creation on match
    end
    HC->>FS: unlink healthcheck file
    HC->>Audit: audit_delete_rule(wazuh_hc key)
    HC->>Thread: hc_thread_active = 0 (stop signal)
    Thread-->>HC: signal completion (cond wait, 5s timeout)
    HC-->>Init: return 0 (success) or -1 (failure)
```

### 3. Event Reading and Assembly (`audit_read_events`)

```mermaid
flowchart TD
    Loop([Loop while running]) --> Select[select on audit_sock, 1s timeout]
    Select -- error --> SleepRetry[sleep 1s] --> Loop
    Select -- timeout/no data --> FlushCheck{cache has data?}
    FlushCheck -- Yes --> FlushCache[Push cached event to audit_queue]
    FlushCheck -- No --> Loop
    FlushCache --> Loop
    Select -- data ready --> Recv[recv into buffer]
    Recv -- 0 bytes: closed --> Reconnect[Reconnect loop<br/>up to MAX_CONN_RETRIES]
    Reconnect -- success --> ReloadRules[fim_audit_reload_rules] --> Loop
    Reconnect -- fail --> SendAlert[Send Connection closed alert] --> Exit([Break loop])
    Recv -- data --> FindLine{Complete line<br/>found?}
    FindLine -- No --> Loop
    FindLine -- Yes --> ParseID[audit_get_id per line]
    ParseID --> IDChanged{ID differs from<br/>cached ID?}
    IDChanged -- Yes --> PushCache[Push previous cached event]
    IDChanged -- No --> AppendCache[Append line to cache]
    PushCache --> AppendCache
    AppendCache --> EOECheck{type=EOE<br/>found?}
    EOECheck -- Yes --> PushComplete[Push complete cached event]
    EOECheck -- No --> Loop
    PushComplete --> Loop
```

### 4. Rule Reload & Fallback to Realtime

```mermaid
flowchart LR
    Manager[Directory config WHODATA_ACTIVE] --> RuleCheck{Rule exists<br/>in audit?}
    RuleCheck -- Yes --> KeepWhodata[Keep WHODATA_ACTIVE]
    RuleCheck -- "No, immutable mode" --> Demote[Clear WHODATA_ACTIVE<br/>Set REALTIME_ACTIVE]
    Demote --> RealtimeStart[realtime_start / realtime_adddir]
    ConnLost[Audit socket permanently closed] --> DemoteAll[audit_main: demote all<br/>whodata directories]
    DemoteAll --> RealtimeStart
```

---

## Component Interaction

```mermaid
sequenceDiagram
    participant Syscheck as syscheckd_core (main.c)
    participant AuditInit as audit_init()
    participant Socket as AUDIT_SOCKET (unix)
    participant AuditD as auditd daemon
    participant ReadThread as audit_main / audit_read_events
    participant ParseThread as audit_parse_thread
    participant Queue as audit_queue
    participant FIMDB as syscheckd_db

    Syscheck->>AuditInit: Start whodata (Linux, ENABLE_AUDIT)
    AuditInit->>Socket: init_auditd_socket()
    AuditInit->>AuditD: set_auditd_config() / audit_restart()
    AuditInit->>ReadThread: w_create_thread(audit_main)
    ReadThread->>Socket: select()/recv() loop
    AuditD-->>Socket: forwards kernel audit events
    Socket-->>ReadThread: raw event lines
    ReadThread->>Queue: queue_push_ex(assembled_event)
    Queue-->>ParseThread: queue_pop_ex()
    ParseThread->>ParseThread: audit_parse(event)
    ParseThread->>FIMDB: fim_whodata_event / DB update
```

---

## Configuration Dependencies

The whodata audit module reads and mutates fields on the shared global `syscheck_config` structure (see [Configuration Data Structures (C Headers)](Configuration_Data_Structures_(C_Headers).md) → `Syscheck_Config`):

- `syscheck.directories` — `OSList` of `directory_t`; each entry's `options` bitmask determines `WHODATA_ACTIVE` vs `REALTIME_ACTIVE`.
- `syscheck.wildcards` — expanded wildcard directory entries also eligible for whodata → realtime demotion.
- `syscheck.audit_key` — list of custom audit keys accepted in addition to the default `wazuh_fim` key.
- `syscheck.audit_healthcheck` — toggles whether `audit_health_check()` runs during startup.
- `syscheck.restart_audit` — controls whether misconfiguration triggers an automatic `auditd` restart.
- `syscheck.queue_size` — sizes the internal `audit_queue`.
- `syscheck.directories_lock` / `syscheck.fim_realtime_mutex` — concurrency guards shared with `syscheckd_core_realtime` when demoting directories.

---

## Concurrency Model

| Thread | Responsibility | Synchronization |
|---|---|---|
| Main FIM thread | Calls `audit_init()` once at startup | Blocks on `audit_thread_started` condition until the audit thread signals readiness |
| `audit_main` (audit reading thread) | Waits for DB consistency signal, then runs `audit_read_events()` for the lifetime of the daemon | `audit_mutex` + `audit_db_consistency` condition variable; `audit_thread_active` atomic flag |
| `audit_healthcheck_thread` | Temporary thread used only during startup healthcheck | `audit_hc_mutex` + `audit_hc_cond`; `hc_thread_active` / `audit_health_check_creation` atomics |
| `audit_parse_thread` | Consumes `audit_queue` and parses raw event text into FIM events | Queue's own internal locking (`w_queue_t`); `audit_parse_thread_active` atomic flag |
| Rule reload thread (`audit_reload_thread`, started conditionally) | Periodically verifies/reapplies audit rules | `audit_rules_mutex` |

All flag transitions use `atomic_int_t` (see [Agent & Manager Native Daemons](Agent_&_Manager_Native_Daemons_(C).md) → `src/headers/atomic.h`) to avoid race conditions between the health check, main audit thread, and shutdown sequence.

---

## Error Handling & Resilience

- **auditd not running** → `audit_init()` fails fast (`FIM_AUDIT_NORUNNING`), causing the caller in `syscheckd_core` to fall back to realtime/inotify for all directories.
- **Socket misconfiguration** → `set_auditd_config()` detects SHA1 drift in the audisp plugin config and reconfigures/restarts audit if `syscheck.restart_audit` is enabled; otherwise it warns and continues without whodata.
- **Health check failure** → treated as fatal for whodata; `audit_init()` returns -1 so whodata is disabled for the run, but the FIM daemon itself continues operating with realtime monitoring.
- **Socket disconnect during runtime** → `audit_read_events()` attempts up to `MAX_CONN_RETRIES` reconnects with a short backoff; on success it triggers `fim_audit_reload_rules()`; on permanent failure it sends an internal alert message and lets `audit_main()` clean up, demoting all whodata directories to realtime.
- **Externally deleted rules** → detected via periodic reload logic (`fim_manipulated_audit_rules`, `audit_rules_to_realtime`), automatically demoting the affected directory rather than silently losing coverage.
- **Immutable audit mode** — since live netlink rule changes are disallowed, the module persists rules to a file (`audit_create_rules_file`) and symlinks them for `auditctl -R`/boot-time loading, while any directory not confirmed as covered is demoted to realtime for the current session.

---

## Related Documentation

- [Syscheck / FIM Daemon (C/C++)](Syscheck___FIM_Daemon_(C_C++).md) — parent module; covers `syscheckd_core` (scan engine, realtime), `syscheckd_db` (FIMDB), `syscheckd_ebpf` (alternative Linux whodata backend), `syscheckd_file`, and `syscheckd_registry`.
- [Configuration Data Structures (C Headers)](Configuration_Data_Structures_(C_Headers).md) — defines `syscheck_config`, `directory_t`, and `whodata` used throughout this module.
- [Agent & Manager Native Daemons (C)](Agent_&_Manager_Native_Daemons_(C).md) — provides the shared `audit_op.c`/`audit_op.h` primitives (`audit_add_rule`, `audit_delete_rule`, `search_audit_rule`, `w_audit_rule`), queue/atomic utilities, and OS networking helpers (`os_net.c`) used for the Unix domain socket connection.
