# runtime_utils_observability

## Introduction

`runtime_utils_observability` contains small, runtime-local diagnostics used to make sandbox execution visible and debuggable. It has two deliberately separate responsibilities:

- `LogStreamer` forwards a Docker container's live stdout/stderr stream to a caller-supplied logger.
- `MemoryMonitor` periodically samples the current process and its child processes, forwarding memory-profiler output to the OpenHands logger.

Neither utility controls execution or changes the action protocol. They observe runtime activity asynchronously and report it through logging. The utilities are part of [runtime_utils](runtime_utils.md), which is consumed by the broader [runtime_implementations](runtime_implementations.md) and by the in-sandbox [Action Execution Server](runtime_implementations_action_execution_server.md).

## Position in the system

```mermaid
graph TB
    AC["AgentController<br/>(agent_reasoning_core)"]
    RUNTIME["Runtime implementations<br/>(Docker, local, remote, Kubernetes)"]
    SERVER["ActionExecutor<br/>(action_execution_server)"]

    subgraph OBS["runtime_utils_observability"]
        LS["LogStreamer"]
        MM["MemoryMonitor"]
    end

    DOCKER["Docker daemon / container"]
    LOGGER["OpenHands logger<br/>(core/logger.py)"]
    MP["memory_profiler + psutil backend"]

    AC -->|actions| RUNTIME
    RUNTIME -->|starts and manages| SERVER
    RUNTIME -->|debug container logs| LS
    DOCKER -->|stream=True, follow=True| LS
    SERVER -->|creates / starts| MM
    MM -->|memory_usage samples| MP
    LS -->|logFn(level, message)| LOGGER
    MM -->|LogStream.write| LOGGER

    style OBS fill:#e8f0fe,stroke:#4285f4,stroke-width:2px
```

The utilities sit on opposite sides of the sandbox boundary:

| Utility | Usually owned by | Observes | Output path |
|---|---|---|---|
| `LogStreamer` | `DockerRuntime` | A running Docker container's log generator | Injected `logFn`, commonly the runtime logger |
| `MemoryMonitor` | `ActionExecutor` | The action-server process and child processes | `openhands_logger` through `LogStream` |

See [runtime_implementations_docker](runtime_implementations_docker.md) for container lifecycle and the `DEBUG_RUNTIME` integration, and [runtime_implementations_action_execution_server](runtime_implementations_action_execution_server.md) for action-server startup, environment variables, and shutdown.

## Architecture

```mermaid
classDiagram
    class LogStreamer {
        -Callable log
        -Thread stdout_thread
        -Iterator log_generator
        -Event _stop_event
        +__init__(container, logFn)
        -_stream_logs()
        +close(timeout=5.0)
        +__del__()
    }

    class MemoryMonitor {
        -Thread _monitoring_thread
        -Event _stop_monitoring
        -LogStream log_stream
        -bool enable
        +__init__(enable=False)
        +start_monitoring()
        +stop_monitoring()
    }

    class LogStream {
        +write(message)
        +flush()
    }

    class DockerContainer {
        +logs(stream=True, follow=True)
    }

    class MemoryProfiler {
        +memory_usage(..., stream=log_stream)
    }

    DockerContainer --> LogStreamer : supplies generator
    LogStreamer --> DockerContainer : closes generator
    MemoryMonitor *-- LogStream : owns
    MemoryMonitor --> MemoryProfiler : samples in worker thread
    LogStream --> OpenHandsLogger : logger.info
    LogStreamer --> LogFunction : invokes
```

The module has no common base class. The shared design is operational rather than object-oriented: both components use a daemon thread, catch failures inside the worker, and emit diagnostic messages instead of propagating errors into the main runtime path.

## Component details

### `LogStreamer`

File: `openhands/runtime/utils/log_streamer.py`

`LogStreamer` adapts Docker's blocking log iterator to a background thread:

1. The constructor stores the supplied `logFn`, initializes all state, and calls `container.logs(stream=True, follow=True)`.
2. If Docker returns a generator, a daemon thread starts `_stream_logs()`.
3. Each non-empty byte line is decoded as UTF-8, trailing whitespace is removed, and the callback receives:

   ```python
   logFn('debug', f'[inside container] {decoded_line}')
   ```

4. `close()` sets `_stop_event`, joins the worker for at most `timeout` seconds, and closes the generator to release its file descriptor.

The callback is intentionally typed as `Callable[[str, str], None]`, so the utility does not depend on one particular logger implementation. Initialization and streaming failures are reported through the callback at the `error` level.

```mermaid
sequenceDiagram
    participant DR as DockerRuntime
    participant LS as LogStreamer
    participant D as Docker container
    participant T as daemon worker
    participant L as runtime logFn

    DR->>LS: LogStreamer(container, logFn)
    LS->>D: logs(stream=True, follow=True)
    D-->>LS: log generator
    LS->>T: start(_stream_logs)
    loop while generator yields
        D-->>T: bytes log line
        T->>T: decode UTF-8 and rstrip()
        T->>L: debug("[inside container] ...")
    end
    DR->>LS: close(timeout)
    LS->>T: set stop event
    LS->>T: join(timeout)
    LS->>D: generator.close()
```

In the Docker runtime, creation is conditional on `DEBUG_RUNTIME`; therefore normal container execution does not necessarily incur a log-streaming thread. The stream is diagnostic and does not feed observations back to the agent.

### `MemoryMonitor` and `LogStream`

Files: `openhands/runtime/utils/memory_monitor.py`

`MemoryMonitor` is opt-in. With `enable=False`, both lifecycle methods return without starting work. When enabled, `start_monitoring()` is idempotent while `_monitoring_thread` is non-`None`.

The worker calls `memory_profiler.memory_usage` with the following policy:

| Setting | Value | Meaning |
|---|---:|---|
| Target | `-1` | Current process |
| Interval | `0.1` seconds | Sample every 100 ms |
| Timeout | `3600` seconds | Maximum one-hour monitoring call |
| `max_usage` | `False` | Collect a time series rather than one maximum |
| `include_children` | `True` | Include child processes |
| `multiprocess` | `True` | Monitor process tree |
| Backend | `psutil_pss` | Proportional set size measurements |
| Stream | `self.log_stream` | Redirect profiler text to logging |

`LogStream.write()` ignores empty/whitespace-only messages and sends all other text to `logger.info` with a `[Memory usage]` prefix. `flush()` is a no-op to satisfy stream-like interfaces.

```mermaid
flowchart TD
    START["ActionExecutor constructs<br/>MemoryMonitor(enable=...)" ] --> ENABLE{enabled?}
    ENABLE -->|no| IDLE["No thread; no samples"]
    ENABLE -->|yes| GUARD{worker already exists?}
    GUARD -->|yes| IDLE2["Return; preserve current worker"]
    GUARD -->|no| THREAD["Start daemon monitor thread"]
    THREAD --> SAMPLE["memory_usage(-1, interval=0.1,<br/>include_children=True, multiprocess=True)"]
    SAMPLE --> WRITE["LogStream.write(message)"]
    WRITE -->|nonblank| INFO["openhands_logger.info(...) "]
    WRITE --> SAMPLE
    SAMPLE -->|exception| ERROR["openhands_logger.error(...) "]
    STOP["stop_monitoring()"] --> EVENT["Set _stop_monitoring event"]
    EVENT --> CLEAR["Clear thread reference"]
```

The monitor logs the final returned `mem_usage` list after `memory_usage` exits. Its purpose is diagnosis—especially investigating memory pressure or OOM behaviour—not enforcing a memory limit. Actual shell limits are configured separately through `RUNTIME_MAX_MEMORY_GB`; see [runtime_implementations_action_execution_server](runtime_implementations_action_execution_server.md).

## Dependencies

```mermaid
graph LR
    LS["LogStreamer"] --> TH["threading"]
    LS --> DOCKER["docker.models.containers.Container"]
    LS --> CB["Caller logFn"]

    MM["MemoryMonitor"] --> TH2["threading"]
    MM --> PROF["memory_profiler.memory_usage"]
    PROF --> PSUTIL["psutil_pss backend"]
    MM --> OHLOG["openhands.core.logger.openhands_logger"]
    MM --> STREAM["LogStream"]
    STREAM --> OHLOG

    RUNTIME["DockerRuntime"] --> LS
    EXEC["ActionExecutor"] --> MM
```

There is no dependency from either utility to the agent, LLM, event stream, or storage layers. They are therefore safe to reuse from runtime backends without coupling observability to agent reasoning.

## Runtime integration and data flow

### Docker log flow

```mermaid
flowchart LR
    C["Container stdout/stderr"] --> API["Docker Container.logs()"]
    API --> GEN["blocking byte generator"]
    GEN --> WORKER["LogStreamer daemon thread"]
    WORKER --> DECODE["UTF-8 decode + rstrip"]
    DECODE --> CALLBACK["logFn('debug', message)"]
    CALLBACK --> RLOG["DockerRuntime / OpenHands logger"]
```

### Memory flow

```mermaid
flowchart LR
    PROC["Action-server process"] --> PROF["memory_profiler"]
    CHILD["Child processes"] --> PROF
    PROF --> PSS["psutil PSS samples"]
    PSS --> STREAM["LogStream.write"]
    STREAM --> LOG["openhands_logger.info"]
    PROF --> SERIES["mem_usage time series"]
    SERIES --> LOG2["final summary log"]
```

The two streams converge only at logging. Container output is labelled `[inside container]` and emitted through a caller-selected callback; memory output is labelled `[Memory usage]` and uses the module-level OpenHands logger.

## Lifecycle, shutdown, and failure semantics

| Condition | `LogStreamer` behaviour | `MemoryMonitor` behaviour |
|---|---|---|
| Disabled / not requested | Not normally constructed by Docker runtime | `start_monitoring()` and `stop_monitoring()` return immediately |
| Startup failure | Calls `log('error', ...)`; constructor does not re-raise | Worker catches and logs `Memory monitoring failed: ...` |
| Worker failure | Catches and logs `Error streaming docker logs...` | Catches and logs `Memory monitoring failed...` |
| Normal stop | Event, bounded join, generator close | Event set and thread reference cleared |
| Runtime shutdown | `DockerRuntime.close()` should close the streamer; `__del__` is a fallback | `ActionExecutor.close()` calls `stop_monitoring()` |

```mermaid
sequenceDiagram
    participant Owner as Runtime owner
    participant U as Observability utility
    participant W as Worker thread
    participant Source as Docker / memory profiler

    Owner->>U: start or construct
    U->>W: start daemon thread
    W->>Source: blocking observation loop
    Owner->>U: close / stop_monitoring
    U->>W: request stop
    alt LogStreamer
        U->>W: join(timeout)
        U->>Source: close log generator
    else MemoryMonitor
        U->>U: set event and clear reference
    end
```

### Important implementation caveats

- `LogStreamer` decodes every line strictly as UTF-8. A non-UTF-8 Docker log line is handled by the outer exception path and terminates the worker.
- `LogStreamer.close()` bounds the join but closes the generator after the join. If the Docker iterator does not unblock promptly, the thread may remain alive beyond the timeout until the generator is closed.
- `LogStreamer.__del__()` is only a fallback. Deterministic owners should call `close()` explicitly because destructor timing is not guaranteed.
- `MemoryMonitor._stop_monitoring` is set by `stop_monitoring()`, but the supplied implementation does not pass that event into `memory_usage` or otherwise poll it. Consequently, the profiler call may continue until it returns or raises; clearing `_monitoring_thread` permits a subsequent start and can result in overlapping monitor calls.
- `MemoryMonitor.start_monitoring()` records a thread before the worker has completed. If the worker fails, the reference remains non-`None` until `stop_monitoring()` is called.
- The `memory_usage` interval is `0.1` seconds even though the source comment says “every second”; the code value is authoritative.

## Operational guidance

Use `LogStreamer` when diagnosing container startup, action-server boot, or sandbox-side failures. Enable the Docker runtime's debug logging path (`DEBUG_RUNTIME`) and ensure the supplied callback routes `debug` messages to a visible sink.

Use `MemoryMonitor` when investigating memory growth, child-process leaks, or OOM-related failures. Enable it with `RUNTIME_MEMORY_MONITOR=true` (also accepted: `1` and `yes`). Pair it with `RUNTIME_MAX_MEMORY_GB` only when a hard shell memory cap is also desired; monitoring itself does not impose that cap.

For the surrounding runtime lifecycle, see [runtime_implementations_docker](runtime_implementations_docker.md), [runtime_implementations_action_execution_server](runtime_implementations_action_execution_server.md), and [sandboxed_execution_layer](sandboxed_execution_layer.md). For shared logging types and filtering, see [logging](logging.md) if that module documentation is available.

## Summary

`runtime_utils_observability` is a passive diagnostics layer. `LogStreamer` bridges a Docker byte stream into runtime logging, while `MemoryMonitor` bridges process-tree memory samples into the OpenHands logger. Both isolate blocking observation work on daemon threads and report failures as logs, preserving the main runtime and action-execution paths. Explicit shutdown remains important, and the current memory-stop implementation should be treated as best-effort rather than a synchronous cancellation mechanism.
