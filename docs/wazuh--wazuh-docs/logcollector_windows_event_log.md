# Logcollector Windows Event Log Module

## Introduction

The `logcollector_windows_event_log` module is the Windows-specific subsystem of the Wazuh Agent's **Logcollector** daemon (`src/logcollector`) responsible for collecting security, application, and system events from Windows hosts. It implements **two independent, parallel collection mechanisms** that correspond to the two generations of Windows event logging APIs:

1. **Legacy Event Log API** (`read_win_el.c`) — Uses the classic `OpenEventLog`/`ReadEventLog` Win32 API. This is the fallback mechanism used for older Windows versions or logs that are not exposed via the newer Event Log service, and it is also used to read the *Security* channel with a supplemental "Vista security description" lookup table.
2. **Windows Event Log Channel API** (`read_win_event_channel.c`) — Uses the modern `EvtSubscribe`/`EvtRender` (`winevt.h`) API introduced in Windows Vista. This is an asynchronous, callback-driven, bookmark-based subscription mechanism that is the primary and recommended method for collecting events on all modern Windows Server/Desktop editions.

Both mechanisms ultimately format collected events and forward them to the Wazuh Agent's message queue (`logr_queue`) for delivery to the manager, and both integrate with the shared logcollector file/target state tracking APIs (`w_logcollector_state_*`).

This module is a child of [logcollector_core](logcollector_core.md) and is a sibling of [logcollector_macos](logcollector_macos.md), [logcollector_journald](logcollector_journald.md), and the generic [logcollector_format_readers](logcollector.md) within the broader [Agent & Manager Native Daemons (C)](Agent_Manager_Native_Daemons_C.md) code base.

## Module Purpose & Core Functionality

| Capability | Legacy API (`read_win_el.c`) | EventChannel API (`read_win_event_channel.c`) |
|---|---|---|
| Windows API family | `OpenEventLog`/`ReadEventLog` | `EvtSubscribe`/`EvtRender`/`EvtFormatMessage` |
| Collection model | Polling (`win_readel` called every ~2s) | Asynchronous push via subscription callback |
| Position tracking | In-memory record cursor (`os_el.record`) | Persistent XML **bookmark** file on disk |
| Event enrichment | DLL-based message resolution (`el_getEventDLL`, `el_getMessage`), Vista security description hash | Publisher metadata resolution (`EvtOpenPublisherMetadata`, `EvtFormatMessage`) |
| Output format | Flattened single-line string (`WinEvtLog: ...`) | JSON object with raw XML + resolved message (`EventChannel`) |
| Failure recovery | Detects `ERROR_EVENTLOG_FILE_CHANGED`, `ERROR_INVALID_HANDLE`, RPC unavailability, and reopens the log | Detects subscription failure/service restart and retries in a loop with `reconnect_time` back-off |
| Max channels | 9 (`el[9]` static array) | Unlimited (per-channel heap-allocated `os_channel`) |

### Legacy Event Log API (`read_win_el.c`)

* **`os_el`** — Per-channel state structure holding the log handle (`HANDLE h`), the last read record number, and the channel name.
* **`startEL`** — Opens an event log channel via `OpenEventLog`, seeks to the oldest record, and returns the number of available records.
* **`win_startel`** — Public entry point invoked once per configured legacy channel at startup. It registers the channel with the shared logcollector state (`w_logcollector_state_add_file`/`_add_target`), opens it, and fast-forwards to the last available record without emitting historical events (`readel(&el[el_last], 0)`), so only new events are reported going forward.
* **`win_readel`** — Called periodically (every ~2 seconds, via `Sleep(2000)`) from the logcollector main loop. It iterates over every registered channel and invokes `readel(..., 1)` to actually read and forward new records.
* **`readel`** — The core reading routine. It calls `ReadEventLog` in a loop, and for each retrieved record:
  - Determines category (`el_getCategory`) and extracts source/computer name from the raw event buffer.
  - Resolves a human-readable description either via the Vista security hash (`el_vista_getMessage`, only for the `Security` channel on Vista+ hosts) or via DLL-based message formatting (`el_getMessage`, which loads the provider's message-resource DLL through `LoadLibraryEx`/`FormatMessage`).
  - Resolves the user/domain name via `LookupAccountSid`, with a special-cased fallback for well-known Security event IDs (4624, 4634, 4647, 4769) when no SID is present.
  - Builds a flattened log line (`WinEvtLog: <channel>: <category>(<id>): <source>: <user>: <domain>: <computer>: <message>`) and sends it via `SendMSG` to the local queue.
  - Updates file/target statistics via `w_logcollector_state_update_file`/`_update_target`.
  - Handles error conditions: `ERROR_HANDLE_EOF` (no more records, normal), `ERROR_EVENTLOG_FILE_CHANGED` (log cleared — closes/reopens and alerts), `ERROR_INVALID_HANDLE` (EventLog service restarted — reconnects), and `RPC_S_SERVER_UNAVAILABLE`/`RPC_S_UNKNOWN_IF` (service down — throttled warning).
* **`win_read_vista_sec`** — Loads `vista_sec.txt` at startup into an `OSHash` (`vista_sec_id_hash`), mapping numeric Security event IDs to human-readable message templates used by `el_vista_getMessage`, avoiding brittle DLL message-table lookups for that channel.
* **`el_getEventDLL`** — Looks up (and caches in `dll_hash`) the `EventMessageFile` registry value for a given event source, used to locate the DLL(s) containing the message-format strings.

### Windows Event Log Channel API (`read_win_event_channel.c`)

* **`os_channel`** — Per-channel state structure holding the channel/query strings, the bookmark file path, the `reconnect_time`, and the live `EVT_HANDLE subscription`.
* **`os_event`** — Structure representing a parsed event's fields (conceptual data model; the primary code path builds a JSON payload directly rather than fully populating this struct).
* **`win_start_event_channel`** — Public entry point that:
  1. Converts channel/query strings to wide-character (`convert_unix_string`) and sanitizes the query (`filter_special_chars`).
  2. Optionally loads a previously persisted bookmark (`read_bookmark`) to resume from the last processed position, or subscribes to future events only (`EvtSubscribeToFutureEvents`) if bookmarking is disabled or no bookmark exists.
  3. Calls `EvtSubscribe` with `event_channel_callback` as the asynchronous notification callback. If subscribing from a bookmark fails, it falls back to future-events-only subscription.
  4. Registers the channel with the shared logcollector state.
* **`event_channel_callback`** — The Windows-invoked callback for the subscription. On `EvtSubscribeActionDeliver` it calls `send_channel_event` to process and forward the new event. On any other action (typically indicating the EventLog service went down), it enters a **retry loop**, repeatedly calling `win_start_event_channel` after sleeping `reconnect_time` seconds until the subscription is successfully re-established, then destroys the stale channel object.
* **`send_channel_event`** — Renders the raw event to XML (`EvtRender` with `EvtRenderEventXml`), extracts the `Provider Name` attribute from the XML, resolves a human-friendly message via `get_message` (`EvtFormatMessage` against the provider's metadata), and builds a JSON payload (`{"Message": ..., "Event": <raw-xml>}`) which is sent to the queue via `SendMSG` using the `WIN_EVT_MQ` message type. It also triggers a bookmark update (`update_bookmark`) after each processed event when bookmarking is enabled, and updates file/target read statistics.
* **`get_message`** — Wraps `EvtOpenPublisherMetadata` + `EvtFormatMessage` to resolve the descriptive message text for an event from its provider's message resources, handling the two-call buffer-sizing convention used by the Windows Event API.
* **`read_bookmark` / `update_bookmark`** — Persist and restore subscription position as serialized bookmark XML in a file under the `bookmarks/` directory, keyed by a sanitized version of the channel name (`/` replaced with `_`).
* **`os_channel_destroy`** — Cleans up an `os_channel`, closing the live subscription handle and freeing associated memory — invoked both on setup failure and after a successful reconnect replaces the old subscription.

## Relationship to the Logcollector Daemon

`logcollector_windows_event_log` is one of several **platform/format specific readers** that plug into the generic Logcollector engine. It sits alongside:

- [logcollector_core](logcollector_core.md) — daemon lifecycle, file/socket handling, and threading model that invokes `win_startel`/`win_start_event_channel` at startup and `win_readel` in the periodic polling loop.
- [logcollector_config_state](logcollector_config_state.md) — configuration parsing (`config.c`) and the global/per-target status persistence (`state.c`, `state.h`) that this module relies on via `w_logcollector_state_add_file`/`_add_target`/`_update_file`/`_update_target`.
- [logcollector_macos](logcollector_macos.md) — the analogous module for Apple's Unified Logging System, following a similar "spawn/subscribe, parse output, persist state" pattern.
- [logcollector_journald](logcollector_journald.md) — the analogous module for Linux's `systemd-journald`.
- [logcollector_remote_control](logcollector_remote_control.md) — exposes current Logcollector state (including Windows channel status) via the `lccom` control socket.

The configuration data types consumed by both readers (`logreader`, `logreader_config`, etc., including the `<log_format>eventlog</log_format>` / `<log_format>eventchannel</log_format>` and `<query>` elements) are defined in [Localfile_Config_core](Localfile_Config_core.md), part of the broader [Configuration_Data_Structures_(C_Headers)](Configuration_Data_Structures_(C_Headers).md) area.

## Architecture Overview

```mermaid
graph TB
    subgraph Wazuh_Agent["Wazuh Agent Process"]
        subgraph Logcollector["Logcollector Daemon (src/logcollector)"]
            Core["logcollector_core<br/>(logcollector.c/h, main.c)<br/>Read loop, threading"]
            ConfigState["logcollector_config_state<br/>(config.c, state.c/h)<br/>Config parsing & JSON status"]
            WinEvt["logcollector_windows_event_log (this module)"]
            MacOS["logcollector_macos"]
            Journald["logcollector_journald"]
        end
    end

    subgraph WinEvtModule["Internal structure of this module"]
        direction TB
        subgraph Legacy["Legacy EventLog API (read_win_el.c)"]
            STARTEL["win_startel()"]
            READEL["win_readel() / readel()"]
            VISTASEC["win_read_vista_sec()"]
            ELHASH["dll_hash / vista_sec_id_hash<br/>(OSHash)"]
        end
        subgraph Channel["EventChannel API (read_win_event_channel.c)"]
            STARTCH["win_start_event_channel()"]
            CALLBACK["event_channel_callback()"]
            SENDEVT["send_channel_event()"]
            BOOKMARK["read_bookmark() / update_bookmark()"]
        end
    end

    subgraph WinAPI["Windows OS APIs"]
        LEGACYAPI["OpenEventLog / ReadEventLog<br/>LookupAccountSid / FormatMessage"]
        EVTAPI["EvtSubscribe / EvtRender<br/>EvtFormatMessage"]
        REGISTRY["Registry: EventMessageFile"]
        FS["Filesystem:<br/>vista_sec.txt, bookmarks/"]
    end

    subgraph Queue["Agent Messaging"]
        MQ["logr_queue<br/>SendMSG()"]
    end

    Core -->|configures channels| ConfigState
    ConfigState -->|legacy log_format=eventlog| STARTEL
    ConfigState -->|log_format=eventchannel| STARTCH
    Core -->|periodic polling loop| READEL
    WinEvt -.contains.- Legacy
    WinEvt -.contains.- Channel

    STARTEL --> LEGACYAPI
    READEL --> LEGACYAPI
    VISTASEC --> FS
    ELHASH -.cache.-> READEL
    READEL --> ELHASH
    READEL --> MQ
    READEL --> ConfigState

    STARTCH --> EVTAPI
    STARTCH --> BOOKMARK
    BOOKMARK --> FS
    EVTAPI -->|async callback| CALLBACK
    CALLBACK --> SENDEVT
    CALLBACK -->|on failure, retry| STARTCH
    SENDEVT --> EVTAPI
    SENDEVT --> MQ
    SENDEVT --> ConfigState
    LEGACYAPI --> REGISTRY

    MacOS -.sibling reader.- WinEvt
    Journald -.sibling reader.- WinEvt

    style Legacy fill:#e8f0fe
    style Channel fill:#fdf3e0
```

### Component Relationships

```mermaid
classDiagram
    class os_el {
        +int time_of_last
        +char* name
        +EVENTLOGRECORD* er
        +HANDLE h
        +DWORD record
    }

    class os_channel {
        +char* evt_log
        +char* bookmark_name
        +char bookmark_enabled
        +char bookmark_filename
        +char* query
        +int reconnect_time
        +EVT_HANDLE subscription
    }

    class os_event {
        +char* name
        +unsigned int id
        +char* source
        +SID* uid
        +char* user
        +char* domain
        +char* computer
        +char* message
        +ULONGLONG time_created
        +char* timestamp
        +int64 keywords
        +int64 level
        +char* category
    }

    class win_el_functions {
        +startEL(app, el) int
        +win_startel(evt_log) void
        +win_readel() void
        +readel(el, printit) void
        +win_read_vista_sec() void
        +el_getEventDLL(evt_name, source, event) char*
        +el_getMessage(er, name, source, sstring) char*
        +el_vista_getMessage(evt_id, sstring) char*
    }

    class win_event_channel_functions {
        +win_start_event_channel(evt_log, future, query, reconnect_time) int
        +event_channel_callback(action, channel, evt) DWORD
        +send_channel_event(evt, channel) void
        +get_message(evt, provider_name, flags) char*
        +read_bookmark(channel) EVT_HANDLE
        +update_bookmark(evt, channel) int
        +os_channel_destroy(channel) void
    }

    win_el_functions --> os_el : manages array el[9]
    win_event_channel_functions --> os_channel : allocates/destroys
    win_event_channel_functions --> os_event : conceptual model
    win_el_functions ..> OSHash : dll_hash, vista_sec_id_hash
    win_event_channel_functions ..> EVT_HANDLE : subscription
```

## Data Flow

### Legacy Event Log Polling Flow

```mermaid
sequenceDiagram
    participant Main as logcollector main loop
    participant Start as win_startel()
    participant Read as win_readel()/readel()
    participant WinAPI as Win32 EventLog API
    participant Hash as dll_hash / vista_sec_id_hash
    participant Queue as logr_queue (SendMSG)
    participant State as w_logcollector_state_*

    Main->>Start: initialize configured "eventlog" channels
    Start->>WinAPI: OpenEventLog(app)
    Start->>WinAPI: GetOldestEventLogRecord / GetNumberOfEventLogRecords
    Start->>Read: readel(el, printit=0) - fast-forward, no emit
    State->>State: w_logcollector_state_add_file/target

    loop every ~2 seconds (Sleep(2000))
        Main->>Read: win_readel()
        Read->>WinAPI: ReadEventLog(FORWARDS_READ | SEQUENTIAL_READ)
        alt records available
            Read->>Hash: el_getEventDLL() / el_vista_getMessage() lookup
            Read->>WinAPI: LoadLibraryEx + FormatMessage (if not cached path)
            Read->>WinAPI: LookupAccountSid (resolve user/domain)
            Read->>Queue: SendMSG(final_msg, "WinEvtLog", LOCALFILE_MQ)
            Read->>State: w_logcollector_state_update_file/target
        else ERROR_HANDLE_EOF
            Read-->>Main: stop reading, wait next cycle
        else ERROR_EVENTLOG_FILE_CHANGED
            Read->>Queue: alert "Event log cleared"
            Read->>WinAPI: CloseEventLog + startEL (reopen)
        else ERROR_INVALID_HANDLE
            Read->>WinAPI: CloseEventLog + startEL (reconnect)
        else RPC_S_SERVER_UNAVAILABLE/UNKNOWN_IF
            Read-->>Main: throttled warning, skip cycle
        end
    end
```

### EventChannel Subscription Flow

```mermaid
sequenceDiagram
    participant Config as Logcollector config
    participant Start as win_start_event_channel()
    participant Bookmark as read_bookmark()/update_bookmark()
    participant WinEvt as Windows Event Log (winevt.h)
    participant Callback as event_channel_callback()
    participant Send as send_channel_event()
    participant Queue as logr_queue (SendMSG)
    participant State as w_logcollector_state_*

    Config->>Start: win_start_event_channel(evt_log, future, query, reconnect_time)
    Start->>Bookmark: read_bookmark(channel)
    alt bookmark exists
        Start->>WinEvt: EvtSubscribe(..., flags=StartAfterBookmark)
    else no bookmark / future-only
        Start->>WinEvt: EvtSubscribe(..., flags=ToFutureEvents)
    end
    Start->>State: w_logcollector_state_add_file/target

    Note over WinEvt,Callback: Asynchronous notification (push model)
    WinEvt-->>Callback: EvtSubscribeActionDeliver(evt)
    Callback->>Send: send_channel_event(evt, channel)
    Send->>WinEvt: EvtRender(EvtRenderEventXml)
    Send->>WinEvt: EvtOpenPublisherMetadata + EvtFormatMessage
    Send->>Queue: SendMSG(JSON payload, "EventChannel", WIN_EVT_MQ)
    Send->>State: w_logcollector_state_update_file/target
    Send->>Bookmark: update_bookmark(evt, channel)

    WinEvt-->>Callback: action != Deliver (service error)
    loop until reconnected
        Callback->>Start: win_start_event_channel() retry
        Callback->>Callback: sleep(reconnect_time)
    end
    Callback->>Callback: os_channel_destroy(old channel)
```

## Error Handling & Resilience

Both readers implement dedicated recovery logic to cope with the instability of the Windows EventLog service:

```mermaid
flowchart TD
    A[Read/Deliver Event] --> B{Error?}
    B -- No --> C[Format & Forward Event]
    B -- Yes --> D{Error Type}
    D -- "ERROR_HANDLE_EOF (legacy)" --> E[Normal: no more records, wait next cycle]
    D -- "ERROR_EVENTLOG_FILE_CHANGED (legacy)" --> F["Alert 'log cleared' + Close/Reopen log"]
    D -- "ERROR_INVALID_HANDLE (legacy)" --> G[EventLog service restarted: Close/Reopen]
    D -- "RPC_S_SERVER_UNAVAILABLE/UNKNOWN_IF (legacy)" --> H[Service down: throttled warning]
    D -- "Subscription action != Deliver (EventChannel)" --> I["Retry loop: win_start_event_channel + sleep(reconnect_time)"]
    I --> J[Reconnected: destroy stale os_channel, resume]
```

## Integration with the Broader System

* **Configuration** — Channels are declared in `ossec.conf` via `<localfile>` blocks with `<log_format>eventlog</log_format>` (legacy) or `<log_format>eventchannel</log_format>` (modern). Parsing of these entries is handled by [Localfile_Config_core](Localfile_Config_core.md), which is consumed by `logcollector.c` in [logcollector_core](logcollector_core.md) to dispatch to `win_startel`/`win_start_event_channel` at startup.
* **State reporting** — Both readers call into the shared file/target statistics API defined in [logcollector_config_state](logcollector_config_state.md) (`state.c`/`state.h`), enabling the `wazuh-logcollector -x`/`lccom` runtime status queries (see [logcollector_remote_control](logcollector_remote_control.md)) and metrics such as bytes/events read per file and target.
* **Message delivery** — Both readers use the shared `SendMSG` primitive from the [Wazuh_Modules_Daemon shared library](Agent_Manager_Native_Daemons_C.md) (`mq_op.c`) to enqueue formatted events onto `logr_queue`, the same local socket used by all other logcollector readers, before being forwarded to `client-agent`/`remoted` for delivery to the manager.
* **Sibling readers** — This module is one of several platform/format-specific readers under `logcollector_core`, alongside [logcollector_macos](logcollector_macos.md) (Unified Logging on macOS) and [logcollector_journald](logcollector_journald.md) (systemd journal on Linux). All readers are orchestrated by the generic input/output threading model implemented in `logcollector_core`.
* **Downstream processing** — Forwarded events (whether the legacy flattened string or the EventChannel JSON payload) are ultimately parsed and decoded by the Wazuh Engine Core (see [engine_hlp](engine_hlp.md) for JSON/XML high-level parsers) / classic analysisd rule and decoder pipeline on the manager side.

## Key Design Notes

* **Two generations, two data models.** The legacy path optimizes for compatibility with very old Windows Event Log semantics (fixed-size binary `EVENTLOGRECORD` buffers, DLL-resource message tables) and emits a single flattened text line preserving the historical Wazuh `WinEvtLog:` format for backward-compatible rule matching. The EventChannel path instead surfaces the full event as XML plus a best-effort resolved message, embedded in JSON, allowing downstream engine decoders to extract structured fields directly.
* **Position persistence differs fundamentally.** The legacy API keeps only an in-process record cursor (`os_el.record`), meaning a channel restarts from the last available record on agent restart (no cross-restart resume). The EventChannel API persists an actual Windows-native bookmark blob to disk (`bookmarks/<sanitized-channel-name>`), enabling reliable at-least-once delivery across agent restarts.
* **Bounded legacy channel count.** The legacy implementation uses a fixed-size static array `os_el el[9]`, capping the number of simultaneously monitored legacy `eventlog` channels to 9 — a legacy limitation not present in the dynamically-allocated EventChannel implementation.
* **Self-healing subscriptions.** The `event_channel_callback`'s retry loop makes the EventChannel reader resilient to transient EventLog service restarts without requiring the whole `logcollector` process to restart, which is important on Windows systems where the EventLog service is occasionally recycled by the OS.
* **Security channel special-casing.** Both readers give special treatment to the Windows `Security` channel: the legacy reader uses the `vista_sec_id_hash` lookup table and event-ID-based user/domain extraction heuristics (for event IDs 4624, 4634, 4647, 4769) instead of relying on `UserSidLength`, since Security events frequently omit an explicit SID in the record.
