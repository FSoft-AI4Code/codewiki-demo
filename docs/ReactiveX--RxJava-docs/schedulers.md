# Schedulers Module Documentation

## Introduction

The Schedulers module is a core component of RxJava that provides thread management and execution context control for reactive streams. It offers a collection of pre-configured schedulers optimized for different types of work, enabling developers to control where and how their reactive operations execute.

## Overview

Schedulers in RxJava are responsible for:
- Managing thread pools and execution contexts
- Providing different scheduling strategies for various workload types
- Enabling time-based operations like delays and timeouts
- Supporting custom executor integration
- Offering thread-safe task execution

## Architecture

### Core Components

```mermaid
graph TB
    subgraph "Schedulers Module"
        S[Schedulers<br/>Static Factory]
        SPF[SchedulerPoolFactory<br/>Pool Management]
    end
    
    subgraph "Scheduler Types"
        COMP[ComputationScheduler<br/>CPU-bound work]
        IO[IoScheduler<br/>IO-bound work]
        SINGLE[SingleScheduler<br/>Sequential execution]
        NT[NewThreadScheduler<br/>New thread per task]
        TRAMP[TrampolineScheduler<br/>Current thread queue]
    end
    
    subgraph "External Dependencies"
        RP[RxJavaPlugins<br/>Plugin System]
        CORE[Core Reactive Types]
    end
    
    S --> COMP
    S --> IO
    S --> SINGLE
    S --> NT
    S --> TRAMP
    S --> RP
    SPF --> COMP
    SPF --> IO
    SPF --> SINGLE
    SPF --> NT
    RP --> CORE
```

### Scheduler Hierarchy

```mermaid
graph TD
    A[Scheduler<br/>Abstract Base] --> B[ComputationScheduler]
    A --> C[IoScheduler]
    A --> D[SingleScheduler]
    A --> E[NewThreadScheduler]
    A --> F[TrampolineScheduler]
    A --> G[ExecutorScheduler]
    
    H[Schedulers<br/>Static Factory] --> B
    H --> C
    H --> D
    H --> E
    H --> F
    H --> G
```

## Component Details

### Schedulers Class

The `Schedulers` class serves as the main entry point and static factory for obtaining standard scheduler instances. It provides five pre-configured schedulers, each optimized for specific use cases:

#### Available Schedulers

1. **Computation Scheduler** (`computation()`)
   - Optimized for CPU-intensive work
   - Thread pool size equals available processors
   - Suitable for event loops and processing callbacks
   - Less sensitive to worker leaks

2. **IO Scheduler** (`io()`)
   - Designed for IO-bound operations
   - Cached thread pool with unbounded growth
   - Supports worker reuse and release modes
   - Configurable keep-alive time and priority

3. **Single Scheduler** (`single()`)
   - Single-threaded sequential execution
   - Suitable for event loops and strongly-sequential work
   - Less sensitive to worker leaks
   - Background thread execution

4. **New Thread Scheduler** (`newThread()`)
   - Creates new thread for each task
   - Suitable for isolated long-running operations
   - Requires careful worker disposal
   - Can lead to resource exhaustion if misused

5. **Trampoline Scheduler** (`trampoline()`)
   - Executes on current thread with FIFO queueing
   - No thread switching
   - Suitable for testing and specific synchronization scenarios

#### Custom Scheduler Creation

The `Schedulers` class also provides factory methods for wrapping custom `Executor` instances:

```mermaid
sequenceDiagram
    participant App as Application
    participant Sched as Schedulers
    participant Exec as Executor
    participant Plugin as RxJavaPlugins
    
    App->>Sched: from(executor)
    Sched->>Plugin: createExecutorScheduler()
    Plugin->>Exec: wrap with Scheduler interface
    Plugin-->>Sched: return ExecutorScheduler
    Sched-->>App: return Scheduler instance
```

### SchedulerPoolFactory

The `SchedulerPoolFactory` manages the creation of `ScheduledExecutorService` instances and configures purging behavior:

- **Thread Pool Creation**: Creates `ScheduledThreadPoolExecutor` instances with custom thread factories
- **Purge Management**: Configures automatic task removal on cancellation
- **System Property Support**: Handles `rx3.purge-enabled` property

## Configuration and Customization

### System Properties

The schedulers module supports extensive configuration through system properties:

```mermaid
graph LR
    subgraph "System Properties"
        P1[rx3.computation-threads]
        P2[rx3.computation-priority]
        P3[rx3.io-keep-alive-time]
        P4[rx3.io-priority]
        P5[rx3.io-scheduled-release]
        P6[rx3.newthread-priority]
        P7[rx3.single-priority]
        P8[rx3.purge-enabled]
        P9[rx3.scheduler.use-nanotime]
    end
    
    subgraph "Schedulers"
        COMP[Computation]
        IO[IO]
        NT[NewThread]
        SINGLE[Single]
        ALL[All Schedulers]
    end
    
    P1 --> COMP
    P2 --> COMP
    P3 --> IO
    P4 --> IO
    P5 --> IO
    P6 --> NT
    P7 --> SINGLE
    P8 --> ALL
    P9 --> ALL
```

### Plugin Integration

The schedulers module integrates with the [plugins system](plugins_system.md) for customization:

- **Initialization Hooks**: Override default scheduler instances at startup
- **Runtime Replacement**: Replace scheduler instances after initialization
- **Custom Factory Methods**: Create scheduler instances with custom thread factories

## Usage Patterns

### Basic Usage

```java
// CPU-intensive operations
Observable.range(1, 1000000)
    .map(expensiveComputation)
    .subscribeOn(Schedulers.computation())
    .subscribe();

// IO operations
Observable.fromCallable(this::fetchFromDatabase)
    .subscribeOn(Schedulers.io())
    .subscribe();

// Sequential processing
Observable.fromArray(items)
    .observeOn(Schedulers.single())
    .subscribe(this::processSequentially);
```

### Custom Executor Integration

```mermaid
graph TD
    A[Application] --> B[Create ExecutorService]
    B --> C[Schedulers from executor]
    C --> D[Use in Observable chain]
    D --> E[Shutdown executor]
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style E fill:#f96,stroke:#333,stroke-width:2px
```

## Thread Safety and Resource Management

### Worker Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Created: createWorker()
    Created --> Active: schedule()
    Active --> Disposed: dispose()
    Active --> Active: schedule more tasks
    Disposed --> [*]: garbage collected
    
    note right of Active
        Worker can schedule
        multiple tasks
    end note
    
    note right of Disposed
        Resources released
        No new tasks accepted
    end note
```

### Resource Leak Prevention

- **Worker Disposal**: Always dispose workers to prevent resource leaks
- **Scheduler Shutdown**: Call `Schedulers.shutdown()` for cleanup
- **Executor Management**: Manage external executor lifecycle when using `from()`

## Performance Considerations

### Scheduler Selection Guide

| Scheduler | Use Case | Thread Pool | Overhead | Leak Sensitivity |
|-----------|----------|-------------|----------|------------------|
| Computation | CPU work | Fixed (CPU count) | Low | Low |
| IO | Blocking IO | Cached/Unbounded | Medium | High |
| Single | Sequential | Single thread | Low | Low |
| NewThread | Isolated tasks | New per task | High | High |
| Trampoline | Current thread | None | Minimal | N/A |

### Best Practices

1. **Choose the right scheduler** for your workload type
2. **Dispose workers** when done to prevent leaks
3. **Avoid blocking operations** on computation scheduler
4. **Limit newThread() usage** to prevent thread exhaustion
5. **Configure system properties** before accessing Schedulers class

## Integration with Other Modules

### Core Reactive Types

The schedulers module integrates with [core reactive types](core_reactive_types.md) through:

- **Scheduler Support Annotations**: Mark operators that use specific schedulers
- **Transformer Integration**: Allow scheduler specification in custom transformers
- **Emitter Scheduling**: Support for scheduling emissions in custom operators

### Test Utilities

Integration with [test utilities](test_utilities.md) provides:

- **TestScheduler**: Virtual time scheduler for testing
- **Scheduler Overrides**: Replace schedulers in test environments
- **Deterministic Execution**: Control timing in unit tests

## Error Handling

### Uncaught Exception Handling

- **Thread-level handlers**: Each scheduler thread has an `UncaughtExceptionHandler`
- **Global error routing**: Unhandled errors go through `RxJavaPlugins.onError()`
- **Worker disposal**: Errors don't automatically dispose workers

### RejectedExecutionException

When using custom executors:
- **Proper executor lifecycle**: Avoid premature shutdown
- **Bounded queue management**: Use backpressure to limit work
- **Error routing**: Rejected tasks go to global error handler

## System Architecture Integration

```mermaid
graph TB
    subgraph "Application Layer"
        APP[Application Code]
        OP[Reactive Operators]
    end
    
    subgraph "Schedulers Module"
        SF[Schedulers Factory]
        SP[SchedulerPoolFactory]
        CS[Custom Schedulers]
    end
    
    subgraph "JVM Layer"
        TE[Thread Executors]
        TP[Thread Pools]
        STP[ScheduledThreadPoolExecutor]
    end
    
    subgraph "System Layer"
        SYS[System Properties]
        TM[Thread Management]
    end
    
    APP --> OP
    OP --> SF
    SF --> SP
    SF --> CS
    SP --> TE
    CS --> TE
    TE --> TP
    TE --> STP
    SYS --> SF
    SYS --> SP
    TM --> TP
```

This architecture provides a clean separation between reactive operations and thread management, allowing for flexible configuration and optimization based on workload characteristics.