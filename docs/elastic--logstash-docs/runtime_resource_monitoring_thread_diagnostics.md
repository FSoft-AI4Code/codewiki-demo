# Runtime Resource Monitoring: Thread Diagnostics

Thread diagnostics are an on-demand view of JVM thread contention and stack traces. `ThreadsReport` converts `HotThreadsMonitor` results into maps, and `LogStash::Util::ThreadDump` filters and limits those results for callers such as operational APIs.

## Detection flow

```mermaid
flowchart TD
    Caller[API or diagnostic caller] --> Dump[ThreadDump]
    Dump --> Report[ThreadsReport.generate(options)]
    Report --> Monitor[HotThreadsMonitor.detect]
    Monitor --> MX[ThreadMXBean]
    MX --> Sample[CPU time, wait/block counters, stack traces]
    Sample --> Sort[sort by cpu, wait, or block]
    Sort --> Report
    Report --> Dump
    Dump --> Filter[skip idle/internal threads]
    Filter --> Limit[return top N useful threads]
```

## `HotThreadsMonitor`

The monitor excludes its calling thread, enables CPU-time measurement when supported, obtains up to a configurable stack depth (50 by default), and returns `ThreadReport` objects. Valid ordering options are `cpu`, `wait`, and `block`; invalid values raise `IllegalArgumentException`. Reports include thread identity/state, stack trace, CPU time, blocked count/time, and waited count/time.

## `ThreadsReport` and `ThreadDump`

`ThreadsReport.generate` maps each Java report to a Ruby/JSON-friendly map. Its no-argument path intends CPU ordering and the option path accepts `ordered_by` and `stacktrace_size`.

`ThreadDump` defaults to ten results and ignores idle threads. It excludes JVM service threads (`Finalizer`, `Reference Handler`, and `Signal Dispatcher`), JRuby JIT/dispatch pool threads, and threads whose stack contains `ThreadPoolExecutor.getTask`. Filtering occurs while iterating the already sorted report, so the returned set is the first non-idle entries rather than a second ranking pass.

## Operational relationship

This is distinct from the recurring `jvm/threads` gauges collected by the `JVM` periodic poller: the poller reports counts, while this path provides actionable per-thread evidence. The metric layer that stores related operational data is described in [metrics_and_instrumentation.md](metrics_and_instrumentation.md).
