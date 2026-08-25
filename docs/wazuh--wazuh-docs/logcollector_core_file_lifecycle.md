# Logcollector Core – File Discovery & Lifecycle Management

## Introduction

The **`logcollector_core_file_lifecycle`** module implements the logic that keeps the Wazuh
**Logcollector** daemon's view of "which files must be monitored right now" in sync with the state
of the filesystem. It lives inside `src/logcollector/logcollector.c` /
`src/logcollector/logcollector.h` and is a sibling of
[logcollector_core_daemon_lifecycle](logcollector_core_daemon_lifecycle.md) (process bootstrap) and
[logcollector_core_threading](logcollector_core_threading.md) (input/output thread orchestration)
inside the parent [logcollector_core](logcollector_core.md) module.

Concretely, this module is responsible for:

- **Wildcard/glob expansion** of `<location>` patterns configured with wildcards (`check_pattern_expand`),
  discovering new matching files as they appear on disk.
- **Exclusion handling** — removing files that match an `<exclude>` glob pattern from the monitored
  set (`check_pattern_expand_excluded`).
- **Binary vs. text detection** — automatically dropping files that are not ASCII/UTF-8 text from the
  monitored set when `filter_binary` is enabled (`check_text_only`).
- **Duplicate-entry elimination** — ensuring that the same physical file is not monitored twice, whether
  configured explicitly twice or discovered redundantly through glob expansion
  (`remove_duplicates`, `find_duplicate_inode`).
- **Concurrency primitives setup** — initializing the reader/writer locks that protect the shared file
  list and the "can read" gate consumed by every input thread (`files_lock_init`).
- **Persisted read-position tracking** — the `os_file_status_t` structure and the `file_status.json`
  load/save routines that allow Logcollector to resume reading exactly where it left off after a
  restart, rotation, or crash (`w_initialize_file_status`, `w_save_file_status`,
  `w_load_files_status`, `w_update_hash_node`, `w_set_to_last_line_read`).

This module does **not** implement daemon startup (see
[logcollector_core_daemon_lifecycle](logcollector_core_daemon_lifecycle.md)) nor the pool of reader/writer
threads that consume this file list (see [logcollector_core_threading](logcollector_core_threading.md)).
Instead, it is the **stateful bookkeeping layer** that both of those modules depend on: the daemon
lifecycle module calls into it once at startup (`files_lock_init`, `check_pattern_expand`), and the
threading module's input threads continuously rely on the `files_update_rwlock` and `file_status`
hash table it manages while reading files concurrently.

## Purpose and Core Functionality

### Core components covered by this document

| Component | Type | File | Responsibility |
|---|---|---|---|
| `check_pattern_expand` | function | `logcollector.c` | Expands `<location>` glob patterns, discovering new files that match and were not previously known; registers them into `globs[j].gfiles[]`. |
| `check_pattern_expand_excluded` | function | `logcollector.c` | Expands `<exclude>` glob patterns and removes any currently-monitored file whose path matches, moving it into the `excluded_files` hash. |
| `check_text_only` | function | `logcollector.c` | Iterates all monitored files with `filter_binary` set and removes (and remembers in `excluded_binaries`) any file that is not ASCII/UTF-8 text. |
| `remove_duplicates` | function | `logcollector.c` | Scans the full file list for two `logreader`/`logreader_glob` entries pointing at the same path and removes the duplicate. |
| `files_lock_init` | function | `logcollector.c` | Initializes the two `rwlock_t` objects — `files_update_rwlock` (file-list mutation) and `can_read_rwlock` (reader gate) — used throughout the file lifecycle and threading subsystems. |
| `file_status` / `os_file_status_t` | struct | `logcollector.h` | Persisted per-file record: last-read byte offset (`int64_t offset`), a live `EVP_MD_CTX *context` (streaming SHA1 state), and a snapshot `os_sha1 hash` used to validate content on resume. |

### Closely related (same-file) helper functions

These are declared/implemented alongside the core components above and are described here because
they form one cohesive subsystem (file-status persistence); they belong to the same logical unit even
though they were not separately called out as "core" components:

- `w_initialize_file_status` — creates the `files_status` `OSHash`, sets its size, registers the
  free-data callback, and loads `file_status.json` from disk if present.
- `w_save_file_status` / `w_save_files_status_to_cJSON` — serializes the current `files_status` hash
  (plus macOS/journald specific extensions) into `file_status.json`; registered via `atexit()` in
  [logcollector_core_daemon_lifecycle](logcollector_core_daemon_lifecycle.md).
- `w_load_files_status` — parses the previously saved JSON, recomputing a fresh SHA1 up to the saved
  offset to validate that the file has not changed unexpectedly since last shutdown.
- `w_set_to_last_line_read` / `w_set_to_pos` — decide, for a freshly opened file, whether to resume at
  the last saved offset, rewind to the beginning (content changed), or jump to the end (large diff).
- `w_update_hash_node` / `w_update_file_status` — update (or insert) the `files_status` entry for a
  given path after a read operation advances the offset.
- `w_get_hash_context` — lazily builds or clones the `EVP_MD_CTX` SHA1 context needed by the input
  threads (see [logcollector_core_threading](logcollector_core_threading.md)) when computing checksums
  incrementally as new lines are read.
- `find_duplicate_inode` — inode/device-based duplicate detection used by `handle_file()` to catch
  hard-linked or symlinked duplicates that `remove_duplicates` (path-string based) cannot detect.

## Architecture Overview

### Component Diagram

```mermaid
graph TB
    subgraph "logcollector_core (parent)"
        LIFECYCLE["logcollector_core_daemon_lifecycle<br/>main()"]
        THIS["logcollector_core_file_lifecycle (this module)"]
        THREADING["logcollector_core_threading<br/>input/output threads"]
    end

    subgraph "This module's internal areas"
        DISCOVERY["Glob Expansion<br/>check_pattern_expand"]
        EXCLUSION["Exclusion Handling<br/>check_pattern_expand_excluded"]
        TEXTCHECK["Binary/Text Filtering<br/>check_text_only"]
        DEDUPE["Duplicate Removal<br/>remove_duplicates,<br/>find_duplicate_inode"]
        LOCKS["Concurrency Primitives<br/>files_lock_init<br/>(files_update_rwlock,<br/>can_read_rwlock)"]
        STATUS["File Status Persistence<br/>os_file_status_t / file_status<br/>w_initialize_file_status,<br/>w_save_file_status,<br/>w_load_files_status"]
    end

    subgraph "Data Stores"
        GLOBS["globs[] / logff[]<br/>(in-memory logreader arrays)"]
        EXHASH["excluded_files / excluded_binaries<br/>(OSHash)"]
        FSHASH["files_status<br/>(OSHash: path -> os_file_status_t)"]
        JSONFILE["file_status.json<br/>(on-disk persistence)"]
    end

    LIFECYCLE -->|"calls at startup"| LOCKS
    LIFECYCLE -->|"calls at startup"| DISCOVERY
    LIFECYCLE -->|"calls at startup"| STATUS

    DISCOVERY --> GLOBS
    DISCOVERY --> EXHASH
    EXCLUSION --> GLOBS
    EXCLUSION --> EXHASH
    TEXTCHECK --> GLOBS
    TEXTCHECK --> EXHASH
    DEDUPE --> GLOBS

    STATUS --> FSHASH
    STATUS --> JSONFILE

    THREADING -->|"read-locks files_update_rwlock,<br/>checks can_read_rwlock"| LOCKS
    THREADING -->|"updates offset/hash after reads"| STATUS
    THIS --> DISCOVERY
    THIS --> EXCLUSION
    THIS --> TEXTCHECK
    THIS --> DEDUPE
    THIS --> LOCKS
    THIS --> STATUS
```

### Dependency Diagram

```mermaid
flowchart LR
    ThisModule["logcollector_core_file_lifecycle"]

    ThisModule --> Headers["headers<br/>(hash_op.h: OSHash,<br/>rwlock_op.h: rwlock_t)"]
    ThisModule --> SharedLib["shared_lib<br/>(OSHash_*, rwlock_*, file_op.c,<br/>debug_op.c merror/mdebug)"]
    ThisModule --> LocalfileCfg["Localfile_Config_core<br/>(logreader, logreader_glob,<br/>logreader_config structs)"]
    ThisModule --> OSCrypto["os_crypto/sha1<br/>(OS_SHA1_File_Nbytes,<br/>OS_SHA1_Stream) via OpenSSL EVP"]
    ThisModule --> CJSON["cJSON<br/>(file_status.json parsing/serialization)"]

    Lifecycle["logcollector_core_daemon_lifecycle"] --> ThisModule
    ThisModule --> Threading["logcollector_core_threading"]
    ThisModule --> ConfigState["logcollector_config_state<br/>(w_logcollector_state_delete_file)"]
    ThisModule -.optional platform hooks.-> MacOS["logcollector_macos<br/>(w_macos_set_status_from_JSON)"]
    ThisModule -.optional platform hooks.-> Journald["logcollector_journald<br/>(w_journald_set_status_from_JSON)"]

    classDef ext fill:#eef,stroke:#88a;
    class Headers,SharedLib,LocalfileCfg,OSCrypto,CJSON ext;
```

## Data Model

```mermaid
classDiagram
    class os_file_status_t {
        +int64_t offset
        +EVP_MD_CTX* context
        +os_sha1 hash
    }

    class logreader {
        +char* file
        +char* ffile
        +int64_t fd
        +int64_t size
        +int dev
        +int ign
        +int exists
        +FILE* fp
        +fpos_t position
    }

    class logreader_glob {
        +char* gpath
        +char* exclude_path
        +logreader* gfiles
        +int num_files
    }

    class OSHash_files_status {
        <<OSHash>>
        +key: path (char*)
        +value: os_file_status_t*
    }

    class OSHash_excluded_files {
        <<OSHash>>
        +key: path (char*)
        +value: sentinel (1)
    }

    OSHash_files_status "1" --> "*" os_file_status_t : stores
    logreader_glob "1" --> "*" logreader : gfiles[]
    os_file_status_t ..> logreader : keyed by logreader.file
```

**Key fields of `os_file_status_t`** (`logcollector.h`):

| Field | Type | Purpose |
|---|---|---|
| `offset` | `int64_t` | Byte offset of the last successfully processed position in the file. Persisted so reading can resume exactly there after a restart. |
| `context` | `EVP_MD_CTX *` | Live OpenSSL EVP digest context holding the incremental SHA1 state computed over the bytes read so far — reused by input threads to avoid re-hashing the whole file on every update. |
| `hash` | `os_sha1` | A snapshot SHA1 digest (as of `offset`) written to `file_status.json`; used at startup to verify the file's leading content hasn't changed before trusting the saved `offset`. |

## Process Flows

### 1. Startup: Locks, Discovery, and Status Load

```mermaid
sequenceDiagram
    participant Lifecycle as logcollector_core_daemon_lifecycle
    participant This as file_lifecycle
    participant Hash as files_status (OSHash)
    participant JSON as file_status.json
    participant FS as Filesystem

    Lifecycle->>This: w_initialize_file_status()
    This->>Hash: OSHash_Create() + OSHash_setSize()
    This->>JSON: wfopen(LOCALFILE_STATUS, "r")
    alt file exists
        JSON-->>This: JSON content
        This->>This: w_load_files_status(global_json)
        loop for each saved file entry
            This->>FS: w_stat(path) - verify file still exists
            This->>This: OS_SHA1_File_Nbytes(path, offset) - verify prefix hash
            This->>Hash: OSHash_Add_ex/Update_ex(path, os_file_status_t)
        end
    else no file / ENOENT
        This-->>Lifecycle: proceed with empty files_status
    end
    Lifecycle->>This: files_lock_init()
    This->>This: rwlock_init(files_update_rwlock)
    This->>This: rwlock_init(can_read_rwlock)
    Lifecycle->>This: check_pattern_expand(1)
    This->>FS: glob(gpath)
    This->>This: register newly matched files into globs[j].gfiles[]
    Lifecycle->>This: check_pattern_expand_excluded()
    This->>FS: glob(exclude_path)
    This->>This: remove matching files from globs[j].gfiles[]
    Lifecycle->>This: check_text_only()
    This->>FS: is_ascii_utf8(file)
    This->>This: remove non-text files, populate excluded_binaries
```

### 2. Periodic Re-check Loop (inside `LogCollectorStart`)

```mermaid
flowchart TD
    Start["Every vcheck_files seconds"] --> Lock["set_can_read(0)\nrwlock_lock_write(files_update_rwlock)"]
    Lock --> Reload{"force_reload &&\nf_reload >= reload_interval?"}
    Reload -->|yes| CloseAll["Close all open files"]
    CloseAll --> Delay["Optional reload_delay sleep\n(mutex released)"]
    Delay --> ReAcquire["Re-acquire write lock"]
    ReAcquire --> ReopenAll["Reopen files, restore fsetpos"]
    Reload -->|no| RotCheck
    ReopenAll --> RotCheck["Check each monitored file for:\n- deletion (ENOENT)\n- inode/device change (rotation)\n- size shrink (truncation)"]
    RotCheck -->|rotated/truncated| Cleanup["OSHash_Delete_ex(files_status, path)\nw_logcollector_state_delete_file()\nhandle_file() reopen"]
    RotCheck -->|deleted, expanded entry| RemoveGlob["Remove_Localfile() from globs[j]"]
    Cleanup --> Expand["check_pattern_expand(1)"]
    RemoveGlob --> Expand
    RotCheck -->|no change| Expand
    Expand --> Dedup["remove_duplicates() for any newly added entries"]
    Dedup --> ExclCheck["check_pattern_expand_excluded()"]
    ExclCheck --> TextCheck["check_text_only()"]
    TextCheck --> Unlock["rwlock_unlock(files_update_rwlock)"]
    Unlock --> Persist["w_save_file_status()"]
    Persist --> Sleep["sleep(1); f_check++"]
```

### 3. Resuming a File on (Re)open

```mermaid
flowchart TD
    Open["handle_file() opens fp"] --> Check{"lf->future == 0?"}
    Check -->|"yes (default)"| LastLine["w_set_to_last_line_read(lf)"]
    Check -->|"no (only future events)"| ToEnd["w_set_to_pos(lf, 0, SEEK_END)"]
    LastLine --> Lookup["OSHash_Get_ex(files_status, lf->file)"]
    Lookup -->|"no saved entry"| SeekEnd["Seek to EOF, record new offset"]
    Lookup -->|"entry found"| Verify["OS_SHA1_File_Nbytes up to saved offset"]
    Verify -->|"hash mismatch"| Rewind["Seek to SEEK_SET (0) - re-read from start"]
    Verify -->|"hash matches, size-offset > diff_max_size"| SeekEndBig["Seek to EOF - too much backlog"]
    Verify -->|"hash matches, small backlog"| ResumeOffset["Seek to saved offset - resume exactly"]
    SeekEnd --> Update["w_update_hash_node(path, new_offset)"]
    Rewind --> Update
    SeekEndBig --> Update
    ResumeOffset --> Done["Read loop continues from here"]
    Update --> Done
    ToEnd --> Update
```

## Component Interaction Diagram

```mermaid
graph LR
    subgraph "Producers of file-list changes"
        CFG["logcollector_config_state<br/>(initial <localfile>/<location> parsing)"]
        DISC["check_pattern_expand /<br/>check_pattern_expand_excluded<br/>(this module)"]
    end

    subgraph "Consumers of file-list state"
        INPUT["logcollector_core_threading<br/>w_input_thread (read loop)"]
        REMOTE["logcollector_remote_control<br/>lccom (state/config queries)"]
    end

    subgraph "Shared guarded state (this module)"
        RWLOCK["files_update_rwlock<br/>can_read_rwlock"]
        FSTATUS["files_status OSHash<br/>(os_file_status_t)"]
        EXHASH["excluded_files /<br/>excluded_binaries"]
    end

    CFG --> DISC
    DISC -->|"write lock"| RWLOCK
    DISC --> EXHASH
    INPUT -->|"read lock"| RWLOCK
    INPUT -->|"update offset/hash"| FSTATUS
    REMOTE -->|"read-only queries"| FSTATUS
    DISC -->|"cleanup on rotation/delete"| FSTATUS
```

## Key Behavioral Notes

- **Two exclusion hashes, two purposes.** `excluded_files` remembers *any* file that has been
  intentionally removed from monitoring (either via `<exclude>` glob match or the periodic
  "free excluded files" cache-refresh cycle in `LogCollectorStart`), while `excluded_binaries` is a
  finer-grained sub-set specifically tracking files removed because `check_text_only` classified them
  as non-text. This distinction lets `check_pattern_expand` differentiate between "never re-add" and
  "re-add if it was only excluded for being binary but a new glob-matched file with a different content
  profile appears," used when handling `file_excluded_binary` in `check_pattern_expand`.
- **Path-based vs inode-based duplicate detection.** `remove_duplicates` compares `current->file`
  strings across all `logreader`/`logreader_glob` entries — it catches configuration mistakes (the same
  path listed twice) and duplicate glob matches. `find_duplicate_inode`, by contrast, is invoked from
  `handle_file()` after a file is actually opened and compares `(fd, dev)` pairs — catching cases where
  two different configured paths (e.g., a symlink and its target, or two hard links) resolve to the
  same physical file, which the string-based check cannot detect.
- **Windows vs POSIX implementations.** Both `check_pattern_expand` and `check_pattern_expand_excluded`
  have separate implementations guarded by `#ifdef WIN32`: the POSIX version uses `glob(3)`, while the
  Windows version uses `expand_win32_wildcards()` and a hand-rolled directory-scan + regex match against
  `exclude_path`'s trailing wildcard component, since native Windows APIs lack POSIX glob semantics.
- **`files_lock_init` is intentionally minimal.** It exists as a tiny, dedicated function (rather than
  being inlined at the `LogCollectorStart` call site) specifically so that unit tests
  (`test_logcollector.c`) can invoke it in isolation to set up the locking subsystem without pulling in
  the rest of the daemon's startup sequence.
- **`file_status.json` schema extensibility.** `w_save_files_status_to_cJSON` / `w_load_files_status`
  compose the base `files` array (one entry per `os_file_status_t`) with optional top-level keys
  (`OS_LOGCOLLECTOR_JSON_MACOS`, `JOURNALD_LOG`) populated by
  [logcollector_macos](logcollector_macos.md) and [logcollector_journald](logcollector_journald.md)
  respectively, allowing those platform-specific sub-modules to persist their own resume state
  (e.g., last timestamp read) inside the very same file without this module needing any knowledge of
  their internal formats.

## Related Modules

- [logcollector_core.md](logcollector_core.md) — parent module overview and where this sub-module fits
  among its siblings.
- [logcollector_core_daemon_lifecycle.md](logcollector_core_daemon_lifecycle.md) — calls
  `files_lock_init()`, `check_pattern_expand()`, `check_pattern_expand_excluded()`, and
  `w_initialize_file_status()` once during `LogCollectorStart()` setup, before the input/output thread
  pools are created.
- [logcollector_core_threading.md](logcollector_core_threading.md) — the input threads that acquire
  `files_update_rwlock` in read mode and consult `can_read()` (backed by `can_read_rwlock`) before
  reading; also the primary caller of `w_update_file_status()`/`w_get_hash_context()` after each read.
- [logcollector_config_state.md](logcollector_config_state.md) — supplies the initial `logreader`
  entries (parsed from `<localfile>`/`<location>` XML) that this module expands, deduplicates, and
  tracks; also owns `w_logcollector_state_delete_file()`, invoked here whenever a file is forgotten.
- [logcollector_remote_control.md](logcollector_remote_control.md) — the `lccom` socket handler exposes
  read-only introspection into the same `files_status` state for `wazuh-control`/API consumers.
- [logcollector_macos.md](logcollector_macos.md) and [logcollector_journald.md](logcollector_journald.md)
  — platform-specific readers that extend the `file_status.json` schema via
  `w_macos_set_status_from_JSON` / `w_journald_set_status_from_JSON` hooks called from
  `w_load_files_status`.
- [Localfile_Config_core.md](Localfile_Config_core.md) — defines the `logreader`, `logreader_glob`, and
  `logreader_config` structures manipulated throughout this module (`gfiles[]`, `gpath`,
  `exclude_path`, etc.).
- [headers.md](headers.md) — declares the underlying `OSHash` (`hash_op.h`) and `rwlock_t`
  (`rwlock_op.h`) primitives this module builds upon.

## Summary

The `logcollector_core_file_lifecycle` module is the stateful glue between static configuration
(`<localfile>` entries) and the dynamic, ever-changing set of files that actually need to be read on a
running system. By combining glob expansion, exclusion filtering, binary detection, duplicate removal,
and a crash-safe persisted offset/hash cache, it allows Logcollector to safely and efficiently discover
new log sources at runtime while guaranteeing — via `file_status.json` — that no log data is
duplicated or silently skipped across restarts, rotations, or reconfigurations.
