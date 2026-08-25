# E2B Runtime

## Introduction

`E2BRuntime` is the OpenHands runtime that runs agent work inside an [E2B](https://e2b.dev) cloud sandbox. E2B gives you a fresh Linux micro-VM on demand, with a shell, a Python code interpreter, and a filesystem — all reachable through the `e2b_code_interpreter` Python SDK.

This module holds one class: `E2BRuntime` (in `third_party/runtime/impl/e2b/e2b_runtime.py`). It is the *translation layer*. Its job is to take OpenHands `Action` objects, turn them into E2B SDK calls, and turn the results back into OpenHands `Observation` objects.

It leans on two sibling modules to do the low-level work:

| Module | What it gives `E2BRuntime` |
| --- | --- |
| [E2B Sandbox](third_party_runtimes_e2b_sandbox.md) | `E2BBox` / `E2BSandbox` — creating, connecting to, running commands in, and killing the sandbox |
| [E2B File Store](third_party_runtimes_e2b_filestore.md) | `E2BFileStore` — read / write / list / delete files inside the sandbox |

Both siblings, plus this runtime, are grouped under [E2B Runtime Family](third_party_runtimes_e2b.md) and the wider [Third-Party Runtimes](third_party_runtimes.md) tree.

### The one thing to understand first

Nearly every other OpenHands runtime works by starting an HTTP server *inside* the sandbox — the [Action Execution Server](runtime_implementations_action_execution_server.md) — and POSTing actions to it. `E2BRuntime` **does not do this.** It extends `ActionExecutionClient` for the class contract and constructor plumbing, but then overrides every action method to call the E2B SDK directly from the host process.

The giveaway is in `connect()`:

```python
# E2B doesn't use action execution server - set dummy URL
self.api_url = "direct://e2b-sandbox"
```

That URL is a placeholder, not a real endpoint. Keeping this in mind explains most of the design — and most of the caveats listed near the end of this document.

---

## Where this module sits

```mermaid
graph TB
    subgraph host["Host process (OpenHands)"]
        AC["AgentController<br/><i>agent_controller.md</i>"]
        ES["EventStream<br/><i>event_system.md</i>"]
        CFG["OpenHandsConfig<br/><i>core_configuration.md</i>"]
        LLMR["LLMRegistry<br/><i>llm_layer_registry.md</i>"]
    end

    subgraph base["Runtime base classes"]
        RT["Runtime<br/>(abstract)"]
        AEC["ActionExecutionClient<br/>(HTTP client base)"]
    end

    subgraph e2bmod["E2B modules"]
        E2BR["<b>E2BRuntime</b><br/>this module"]
        BOX["E2BBox / E2BSandbox<br/><i>..._e2b_sandbox.md</i>"]
        FS["E2BFileStore<br/><i>..._e2b_filestore.md</i>"]
    end

    subgraph cloud["E2B cloud"]
        SDK["e2b_code_interpreter.Sandbox"]
        VM["Linux micro-VM<br/>shell + Jupyter kernel + FS"]
    end

    AC -->|"actions"| ES
    ES -->|"on_event"| E2BR
    E2BR -->|"observations"| ES
    CFG --> E2BR
    LLMR --> E2BR

    RT --> AEC
    AEC --> E2BR

    E2BR -->|"execute / run_code"| BOX
    E2BR -->|"read / write / list"| FS
    BOX --> SDK
    FS -->|"sandbox.files"| SDK
    SDK -.->|"HTTPS"| VM

    style E2BR fill:#2563eb,color:#fff
    style BOX fill:#7c3aed,color:#fff
    style FS fill:#7c3aed,color:#fff
```

The runtime is a *subscriber* on the [EventStream](event_system.md). It never polls; `Runtime.on_event` hands it each `Action` the agent emits, and it pushes the resulting `Observation` back onto the stream. See [Agent Controller](agent_controller.md) for the loop that drives this.

---

## Class anatomy

```mermaid
classDiagram
    class Runtime {
        <<abstract>>
        +sid: str
        +config: OpenHandsConfig
        +setup_initial_env()
        +run_action(action) Observation
        +set_runtime_status(status)
        #_runtime_initialized: bool
    }

    class ActionExecutionClient {
        +session: HttpSession
        +action_semaphore: Semaphore
        +action_execution_server_url
        +send_action_for_execution(action)
        +copy_from(path)
        +call_tool_mcp(action)
    }

    class E2BRuntime {
        +_sandbox_id_cache: dict$
        +sandbox: E2BSandbox|None
        +file_store: E2BFileStore|None
        +api_url: str|None
        +connect() async
        +close() async
        +run(CmdRunAction)
        +run_ipython(IPythonRunCellAction)
        +read(FileReadAction)
        +write(FileWriteAction)
        +edit(FileEditAction)
        +browse(BrowseURLAction)
        +browse_interactive(...) ErrorObs
        +list_files(path)
        +add_env_vars(vars)
        +copy_to(src, dest, recursive)
        +get_working_directory()
        +get_mcp_config(...)
        +check_if_alive()
        +get_vscode_token() ""
        +setup(config)$
        +teardown(config)$
    }

    class E2BBox {
        +sandbox: Sandbox
        +filesystem
        +execute(cmd, timeout) tuple
        +copy_to(src, dest, recursive)
        +close()
    }

    class E2BFileStore {
        +read(path) str
        +write(path, contents)
        +list(path) list
        +delete(path)
    }

    Runtime <|-- ActionExecutionClient
    ActionExecutionClient <|-- E2BRuntime
    E2BRuntime --> E2BBox : owns
    E2BRuntime --> E2BFileStore : owns
    E2BFileStore ..> E2BBox : wraps .filesystem
```

### Instance state

| Attribute | Set in | Meaning |
| --- | --- | --- |
| `_sandbox_id_cache` | class body | **Class-level** `dict[sid, sandbox_id]`. Lets a later `connect()` re-attach to a sandbox from an earlier session in the same process. |
| `sandbox` | `__init__` / `connect` | The `E2BBox` handle. May be injected by the caller (useful for tests). |
| `file_store` | `connect` | `E2BFileStore` wrapping `sandbox.filesystem`. `None` until `connect()` runs. |
| `api_url` | `connect` | Sentinel string `"direct://e2b-sandbox"`. Its only real job is to be non-`None` so `action_execution_server_url` stops raising. |
| `_action_server_port` | `__init__` | Set to `8000` but never read — vestigial. |
| `_runtime_initialized` | `connect` | Flips to `True` on success; read by the base `runtime_initialized` property. |

### Constructor notes

`__init__` warns and ignores `config.workspace_base`, because an E2B sandbox has its own isolated filesystem and there is nothing on the host to bind-mount into it. Everything else is forwarded straight to `ActionExecutionClient.__init__`, which builds the `HttpSession`, the action semaphore, and the base `Runtime` wiring (event-stream subscription, `GitHandler`, provider tokens, security analyzer).

---

## Lifecycle

### `connect()` — bring the sandbox up

```mermaid
flowchart TD
    START([connect]) --> ST["set_runtime_status(STARTING_RUNTIME)"]
    ST --> Q1{"attach_to_existing<br/>and sandbox is None?"}

    Q1 -->|yes| CACHE{"sid in<br/>_sandbox_id_cache?"}
    Q1 -->|no| Q2

    CACHE -->|yes| CONN["E2BBox(config.sandbox,<br/>sandbox_id=cached_id)"]
    CACHE -->|no| Q2
    CONN -->|success| Q2
    CONN -->|"exception"| EVICT["log warning,<br/>drop cache entry,<br/>sandbox = None"]
    EVICT --> Q2

    Q2{"sandbox is None?"} -->|yes| CREATE["E2BSandbox(config.sandbox)<br/>= new micro-VM"]
    Q2 -->|no| CHECK
    CREATE -->|success| STORE["_sandbox_id_cache[sid] = sandbox_id"]
    CREATE -->|"exception"| FAIL
    STORE --> CHECK

    CHECK{"isinstance<br/>E2BSandbox/E2BBox?"} -->|no| FAIL
    CHECK -->|yes| MKFS["file_store =<br/>E2BFileStore(sandbox.filesystem)"]
    MKFS --> URL["api_url = 'direct://e2b-sandbox'"]
    URL --> WS{"workspace_mount_path_<br/>in_sandbox set?"}

    WS -->|yes| MKDIR["sudo mkdir -p DIR<br/>then sudo chmod 777 DIR<br/><i>failures only warn</i>"]
    WS -->|no| ENV
    MKDIR --> ENV

    ENV["await call_sync_from_async(<br/>setup_initial_env)"] --> OK["_runtime_initialized = True<br/>status = READY"]
    OK --> DONE([connected])

    FAIL["log error<br/>status = FAILED<br/>re-raise"] --> ERR([raises])

    style DONE fill:#059669,color:#fff
    style ERR fill:#dc2626,color:#fff
    style FAIL fill:#dc2626,color:#fff
```

Three things worth calling out:

1. **Attach is best-effort.** If the cached sandbox is gone, the failure is downgraded to a warning, the stale entry is evicted, and a brand-new sandbox is created. The agent never sees the hiccup.
2. **Workspace setup is best-effort too.** A failed `mkdir` only logs a warning; `connect()` still reports `READY`. Later file operations against that path will then fail one at a time.
3. **`setup_initial_env()` is inherited** from `Runtime`. It short-circuits when `attach_to_existing` is `True`; otherwise it calls this class's `add_env_vars()` and then `_setup_git_config()` (which shells out via `run()`).

> Note: the status set on the failure path is written as `RuntimeStatus.FAILED`. The [`RuntimeStatus`](runtime_utils.md) enum defines `ERROR`, `STOPPED`, and friends — not `FAILED` — so this line raises `AttributeError` inside the `except` block rather than reporting a clean failure status. Worth fixing to `RuntimeStatus.ERROR`.

### `close()` — tear down (or don't)

```mermaid
flowchart LR
    C([close]) --> G{"_runtime_closed?"}
    G -->|yes| RET([return])
    G -->|no| MARK["_runtime_closed = True"]
    MARK --> S{"sandbox set?"}
    S -->|no| SUPER
    S -->|yes| A{"attach_to_existing?"}
    A -->|"False"| KILL["sandbox.close()<br/>evict from _sandbox_id_cache"]
    A -->|"True"| KEEP["leave sandbox running<br/>for reuse"]
    KILL --> SUPER
    KEEP --> SUPER
    SUPER["super().close()<br/>closes HttpSession"] --> END([closed])

    style KILL fill:#dc2626,color:#fff
    style KEEP fill:#0891b2,color:#fff
```

The `attach_to_existing` flag is the switch between *ephemeral* and *reusable* sandboxes. When it is `True`, `close()` deliberately leaves the E2B micro-VM alive so the next session can re-attach — which also means **you are still paying for it** until E2B's own idle timeout kills it.

`close()` is declared `async` here, but `ActionExecutionClient.close()` is synchronous. The code handles this by awaiting the parent's return value only when it is not `None`:

```python
parent_close = super().close()
if parent_close is not None:
    await parent_close
```

Note that the base `Runtime.__init__` registers `close` with `atexit`. Since this override is a coroutine function, the `atexit` hook creates an un-awaited coroutine at interpreter shutdown rather than actually closing anything — so rely on the conversation manager calling `close()`, not on process exit.

---

## Action dispatch

`Runtime.run_action()` dispatches by looking up `getattr(self, action.action)`. So the method names below *are* the routing table.

```mermaid
graph LR
    subgraph acts["Action"]
        A1[CmdRunAction]
        A2[IPythonRunCellAction]
        A3[FileReadAction]
        A4[FileWriteAction]
        A5[FileEditAction]
        A6[BrowseURLAction]
        A7[BrowseInteractiveAction]
    end

    subgraph meth["E2BRuntime method"]
        M1["run()"]
        M2["run_ipython()"]
        M3["read()"]
        M4["write()"]
        M5["edit()"]
        M6["browse()"]
        M7["browse_interactive()"]
    end

    subgraph backend["Backend call"]
        B1["sandbox.execute(cmd)"]
        B2["sandbox.sandbox.run_code(code)"]
        B3["file_store.read/write/list"]
        B4["sandbox.execute(curl / wget)"]
        B5["always ErrorObservation"]
    end

    subgraph obs["Observation"]
        O1[CmdOutputObservation]
        O2[IPythonRunCellObservation]
        O3[FileReadObservation]
        O4[FileWriteObservation]
        O5[FileEditObservation]
        O6[BrowserOutputObservation]
        O7[ErrorObservation]
    end

    A1 --> M1 --> B1 --> O1
    A2 --> M2 --> B2 --> O2
    A3 --> M3 --> B3 --> O3
    A4 --> M4 --> B3 --> O4
    A5 --> M5 --> B3 --> O5
    A6 --> M6 --> B4 --> O6
    A7 --> M7 --> B5 --> O7

    B1 -.->|"on exception"| O7
    B2 -.->|"on exception"| O7
    B3 -.->|"on exception"| O7
    B4 -.->|"on exception"| O7

    style B5 fill:#dc2626,color:#fff
    style O7 fill:#f59e0b,color:#000
```

**Uniform error policy.** Every handler follows the same shape:

```python
if self.sandbox is None:          # or self.file_store is None
    return ErrorObservation("E2B sandbox not initialized")
try:
    ...
except Exception as e:
    return ErrorObservation(f"Failed to ...: {e}")
```

Nothing propagates upward. The agent always gets a readable observation and can decide what to do next, instead of the whole conversation dying on a transient sandbox error. See [Event System](event_system.md) for how observations flow back.

### Command execution — `run()`

Resolves the timeout as `action.timeout or config.sandbox.timeout`, then calls `E2BBox.execute()`, which returns a `(exit_code, output)` tuple with stdout and stderr concatenated. That becomes a `CmdOutputObservation`.

Because `E2BBox.execute()` calls `sandbox.commands.run(cmd)` fresh each time, **each command runs in its own shell**. There is no persistent bash session, so `cd`, `export`, and shell functions do not carry over between actions. This is the biggest behavioural difference from runtimes built on the stateful [`BashSession`](runtime_utils.md).

### Notebook execution — `run_ipython()`

Reaches past the wrapper (`self.sandbox.sandbox`) to call the E2B SDK's `run_code()` directly, using the sandbox's built-in Jupyter kernel — no [Jupyter plugin](runtime_plugins.md) needs installing.

Result extraction walks `result.results` and takes the first available representation per entry, in priority order:

```mermaid
flowchart LR
    R["result.results[i]"] --> T{"has .text?"}
    T -->|yes| TX["append r.text"]
    T -->|no| H{"has .html?"}
    H -->|yes| HT["append r.html"]
    H -->|no| P{"has .png?"}
    P -->|yes| PN["append '[Image data: N bytes]'"]
    P -->|no| SKIP["skipped"]
    style SKIP fill:#9ca3af,color:#fff
```

Images are reduced to a byte-count placeholder — the actual image data is discarded, so multimodal agents get no picture here. If `result.error` is set, the whole cell returns an `ErrorObservation` instead.

### File operations

All three file handlers go through `E2BFileStore`, never through the shell.

`read()` fetches the whole file, then trims to the requested window with the shared [`read_lines`](runtime_utils.md) helper.

`write()` has three branches:

```mermaid
flowchart TD
    W([write]) --> F{"start == 0<br/>and end == -1?"}
    F -->|yes| FULL["file_store.write(path, content)<br/><i>whole-file overwrite</i>"]
    F -->|no| EX{"path in<br/>file_store.list(path)?"}
    EX -->|yes| SPLICE["read all lines →<br/>insert_lines(...) →<br/>write back"]
    EX -->|no| NEW["file_store.write(path, content)<br/><i>create new file</i>"]
    FULL --> OBS([FileWriteObservation])
    SPLICE --> OBS
    NEW --> OBS
```

`edit()` replaces the half-open line range `[start, end)` with new content and returns a `FileEditObservation` carrying `old_content` so the UI can render a diff. It validates the range (`start < 0` or `end > len(lines)` is rejected) but **only handles the OSS/range-based edit path** — it does not check `action.impl_source`, so an LLM-based edit request is not routed to `llm_based_edit()` the way `ActionExecutionClient.send_action_for_execution()` would route it.

Both `write()` and `edit()` test existence with `action.path in self.file_store.list(action.path)` — listing the file's *own* path and looking for itself in the results. Whether that succeeds depends entirely on how the E2B SDK's `files.list()` behaves when handed a file rather than a directory; treat this check as fragile.

### Browsing — deliberately shallow

`browse()` does not use a real browser. It shells out to `curl -s -L`, and on non-zero exit retries with `wget -qO-`, then wraps the raw response body in a `BrowserOutputObservation` with `screenshot=None`.

`browse_interactive()` always returns an `ErrorObservation`. There is no [BrowserEnv](browser_environment.md) / BrowserGym instance in an E2B sandbox, so clicking, typing, and screenshots are simply unavailable. Agents that depend on interactive browsing — see [Browsing Agents](agents_browsing.md) — will not work on this runtime.

> The URL is interpolated straight into a shell string (`f"curl -s -L '{action.url}'"`) with only single quotes around it. A URL containing a single quote can break out of the quoting and inject shell commands. Since URLs can originate from model output or fetched page content, this is worth hardening with `shlex.quote`.

---

## Supporting operations

| Method | Behaviour |
| --- | --- |
| `list_files(path)` | Runs `find {path} -maxdepth 1 -type f -o -type d`, then strips the `path/` prefix from each result. Defaults to `workspace_mount_path_in_sandbox` or `/workspace`. Returns `[]` (never raises) on any problem. |
| `add_env_vars(vars)` | Records vars in `self._env_vars`, then runs one `export KEY='value'` per var, with `'` escaped as `'"'"'`. |
| `get_working_directory()` | Runs `pwd`; falls back to the configured workspace path or `/workspace`. |
| `copy_to(src, dest, recursive)` | Delegates to `E2BBox.copy_to`, which tars locally, uploads, and untars in the sandbox. Overrides the base class's HTTP upload. |
| `check_if_alive()` | Only asserts `sandbox is not None` — it does **not** ping the sandbox. Overrides the base `GET /alive`. |
| `get_vscode_token()` | Returns `""`; E2B has no [VSCode plugin](runtime_plugins.md) support. |
| `get_mcp_config(...)` | Returns a plain `dict` with just `stdio_servers` — effectively disabling MCP. |
| `setup()` / `teardown()` | Class methods that only log. Unlike Docker, there is no image to build; provisioning is E2B's job. See [Runtime Image Builders](runtime_image_builders.md) for the contrast. |

### Environment variables: an important caveat

`add_env_vars()` issues `export KEY=value` as its own `sandbox.execute()` call. Because every `execute()` starts a new shell, that export dies with the shell and is **not** visible to the next command. Nothing is written to `~/.bashrc` either (the base `Runtime.add_env_vars` does write to `.bashrc`; this override does not).

The `self._env_vars` dict is populated but never consumed, so it does not compensate. Practically: git tokens and other secrets injected during `setup_initial_env()` are unlikely to be present when the agent later runs a command. This is the most likely source of confusing "why is my token missing" behaviour on this runtime.

```mermaid
sequenceDiagram
    participant R as E2BRuntime
    participant B as E2BBox
    participant S1 as shell #1
    participant S2 as shell #2

    R->>B: execute("export TOKEN='abc'")
    B->>S1: commands.run(...)
    S1-->>B: exit 0
    Note over S1: shell exits,<br/>TOKEN lost

    R->>B: execute("git push")
    B->>S2: commands.run(...)
    Note over S2: fresh shell —<br/>TOKEN not set
    S2-->>B: auth failure
```

---

## End-to-end request flow

```mermaid
sequenceDiagram
    actor U as User
    participant AC as AgentController
    participant ES as EventStream
    participant RT as E2BRuntime
    participant SBX as E2BBox
    participant FS as E2BFileStore
    participant E2B as E2B cloud VM

    U->>AC: task
    AC->>RT: connect()
    RT->>SBX: E2BSandbox(config.sandbox)
    SBX->>E2B: Sandbox.create()
    E2B-->>SBX: sandbox_id
    SBX-->>RT: handle
    RT->>RT: cache sandbox_id under sid
    RT->>FS: E2BFileStore(sandbox.filesystem)
    RT->>SBX: sudo mkdir -p /workspace
    RT->>RT: setup_initial_env()
    RT-->>AC: status = READY

    loop agent step
        AC->>ES: add_event(Action)
        ES->>RT: on_event(action)
        RT->>RT: run_action → dispatch by action type

        alt CmdRunAction
            RT->>SBX: execute(cmd, timeout)
            SBX->>E2B: commands.run(cmd)
            E2B-->>SBX: stdout+stderr, exit_code
            SBX-->>RT: (exit_code, output)
        else IPythonRunCellAction
            RT->>E2B: sandbox.run_code(code)
            E2B-->>RT: results / error
        else File action
            RT->>FS: read / write / list
            FS->>E2B: files API
            E2B-->>FS: contents
            FS-->>RT: str / list
        end

        RT->>ES: add_event(Observation)
        ES->>AC: observation
    end

    AC->>RT: close()
    alt attach_to_existing = False
        RT->>SBX: close() → sandbox.kill()
        SBX->>E2B: kill
        RT->>RT: evict cache entry
    else attach_to_existing = True
        RT->>RT: keep sandbox alive for reuse
    end
```

---

## Sandbox reuse across sessions

```mermaid
stateDiagram-v2
    [*] --> NoSandbox

    NoSandbox --> Attaching: connect() with<br/>attach_to_existing=True<br/>and cache hit
    NoSandbox --> Creating: no cache entry,<br/>or attach_to_existing=False

    Attaching --> Ready: Sandbox.connect(id) OK
    Attaching --> Creating: connect failed<br/>(evict stale id)

    Creating --> Ready: Sandbox.create() OK<br/>(store id under sid)
    Creating --> Failed: create raised

    Ready --> Ready: run / read / write / browse
    Ready --> Preserved: close() with<br/>attach_to_existing=True
    Ready --> Killed: close() with<br/>attach_to_existing=False

    Preserved --> Attaching: next connect() in<br/>the same process
    Killed --> [*]
    Failed --> [*]
```

`_sandbox_id_cache` is a plain class attribute — an in-memory dict on the Python class. That has real consequences:

- **Process-local.** Restart the server and every mapping is gone. The E2B sandboxes may still be running and billable, but OpenHands can no longer find them. Durable reuse would need a real store — see [Storage Backends](storage_backends.md).
- **Shared across instances.** Every `E2BRuntime` in the process reads and writes the same dict, keyed by `sid`. Two conversations with the same `sid` would collide.
- **Unsynchronised.** Reads, writes, and `del` happen without a lock, so concurrent `connect()` / `close()` calls on the same `sid` can race.

---

## Capability comparison

How E2B stacks up against the first-party runtimes:

| Capability | E2B | [Docker](runtime_implementations_docker.md) | [Remote](runtime_implementations_orchestrated_remote_runtime.md) | [CLI](runtime_implementations_local_execution_cli_runtime.md) |
| --- | --- | --- | --- | --- |
| Action execution server | ✗ direct SDK | ✓ HTTP | ✓ HTTP | ✗ direct |
| Persistent shell session | ✗ per-command shell | ✓ `BashSession` | ✓ | ✓ |
| IPython / notebook | ✓ native E2B kernel | ✓ Jupyter plugin | ✓ | limited |
| Simple URL fetch | ✓ curl / wget | ✓ | ✓ | ✓ |
| Interactive browsing | ✗ | ✓ BrowserGym | ✓ | ✗ |
| VSCode | ✗ | ✓ | ✓ | ✗ |
| MCP tools | ✗ | ✓ | ✓ | partial |
| Custom runtime image | ✗ E2B-managed | ✓ | ✓ | n/a |
| `copy_from` (download) | ✗ not implemented | ✓ | ✓ | ✓ |
| Workspace bind-mount | ✗ isolated FS | ✓ | ✗ | ✓ host FS |

---

## Known constraints and caveats

Collected here so maintainers do not have to rediscover them. Items marked **bug** look like genuine defects rather than deliberate trade-offs.

### Inherited HTTP methods that cannot work

`E2BRuntime` overrides most action methods but not all of the base class's HTTP-backed helpers. The ones left inherited still point at `action_execution_server_url`, which is the sentinel `"direct://e2b-sandbox"`:

```mermaid
graph TB
    subgraph over["Overridden — work correctly"]
        O1["run / run_ipython"]
        O2["read / write / edit"]
        O3["browse / browse_interactive"]
        O4["list_files / copy_to"]
        O5["check_if_alive"]
        O6["get_vscode_token / get_mcp_config"]
    end

    subgraph inh["Inherited — hit the fake URL"]
        I1["copy_from()"]
        I2["call_tool_mcp()"]
        I3["send_action_for_execution()"]
    end

    I1 -.->|"breaks"| B1["microagent loading<br/>(Runtime._load_microagents_<br/>from_directory)"]
    I2 -.->|"breaks"| B2["any MCPAction"]

    style inh fill:#dc2626,color:#fff
    style B1 fill:#f59e0b,color:#000
    style B2 fill:#f59e0b,color:#000
```

- **bug — `copy_from()` is not overridden.** The inherited version streams `GET {url}/download_files`. Against `direct://e2b-sandbox` this fails, which in turn breaks `get_microagents_from_selected_repo()`, since [microagent](microagents.md) loading zips the microagents directory out of the sandbox. Repo- and org-level microagents therefore will not load on E2B.
- **bug — `call_tool_mcp()` is not overridden.** It calls `get_mcp_config()` and expects an `MCPConfig`, but this class returns a plain `dict`, so attribute access on the result fails. Any `MCPAction` errors out.

### Type-contract deviations

- **`get_mcp_config()` returns `dict`, not `MCPConfig`.** The abstract signature on `Runtime` promises `MCPConfig`. Callers that touch `.sse_servers` / `.stdio_servers` will raise.
- **`close()` is `async`, the base is sync.** Handled defensively for the `super()` call, but it makes the inherited `atexit` registration a no-op (see Lifecycle above).

### Behavioural gaps

- **bug — `RuntimeStatus.FAILED` does not exist.** The `except` branch of `connect()` raises `AttributeError` instead of setting an error status. Should be `RuntimeStatus.ERROR`.
- **`timeout` is accepted but ignored.** `run()` computes a timeout and passes it to `E2BBox.execute()`, which does not forward it to `sandbox.commands.run()`. Long commands are bounded only by E2B's own defaults.
- **No shell state between actions.** `cd`, `export`, and shell functions do not persist (see above).
- **Environment variables do not stick** (see the dedicated section above).
- **No plugin support.** `plugins` is accepted and stored by the base class, but nothing installs [AgentSkills, Jupyter, or VSCode](runtime_plugins.md) in the sandbox. IPython works only because E2B ships its own kernel.
- **Images are dropped** from IPython results, replaced by a byte-count string.
- **Shell injection** risk in `browse()` and, more mildly, in the `mkdir`/`chmod`/`find` command construction, since paths come from config.
- **`E2BSandbox` is just an alias.** `sandbox.py` ends with `E2BSandbox = E2BBox`, so the `isinstance(self.sandbox, (E2BSandbox, E2BBox))` check tests the same class twice.

---

## Configuration

| Source | Key | Used for |
| --- | --- | --- |
| Env var | `E2B_API_KEY` | **Required.** `E2BBox.__init__` raises `ValueError` without it. |
| Env var | `E2B_DOMAIN` | Optional self-hosted E2B endpoint; sets `E2B_API_URL`. |
| [`SandboxConfig`](core_configuration.md) | `timeout` | Default command timeout (currently not enforced end-to-end). |
| `SandboxConfig` | `initialize_plugins` | Read by `E2BBox` but not acted on. |
| [`OpenHandsConfig`](core_configuration.md) | `workspace_mount_path_in_sandbox` | Directory created and `chmod 777`ed during `connect()`; default working dir. |
| `OpenHandsConfig` | `workspace_base` | **Ignored** — warns if set. |
| `OpenHandsConfig` | `git_user_name` / `git_user_email` | Applied by the inherited `_setup_git_config()`. |

Selecting this runtime happens through the usual `get_runtime_cls()` lookup described in [Sandboxed Execution Layer](sandboxed_execution_layer.md).

---

## Related documentation

- [E2B Sandbox](third_party_runtimes_e2b_sandbox.md) — `E2BBox`, command execution, tar-based upload
- [E2B File Store](third_party_runtimes_e2b_filestore.md) — `E2BFileStore`, `SupportsFilesystemOperations`
- [E2B Runtime Family](third_party_runtimes_e2b.md) — the three E2B modules together
- [Third-Party Runtimes](third_party_runtimes.md) — E2B alongside Daytona, Modal, Runloop
- [Managed Sandboxes](third_party_runtimes_managed_sandboxes.md) — the other hosted-sandbox providers
- [Sandboxed Execution Layer](sandboxed_execution_layer.md) — the runtime abstraction as a whole
- [Action Execution Server](runtime_implementations_action_execution_server.md) — the HTTP protocol E2B bypasses
- [Runtime Utils](runtime_utils.md) — `BashSession`, `GitHandler`, `read_lines` / `insert_lines`
- [Runtime Plugins](runtime_plugins.md) — AgentSkills, Jupyter, VSCode (unsupported here)
- [Event System](event_system.md) — actions, observations, and the `EventStream`
- [Agent Controller](agent_controller.md) — the loop that drives the runtime
- [Core Configuration](core_configuration.md) — `OpenHandsConfig`, `SandboxConfig`
