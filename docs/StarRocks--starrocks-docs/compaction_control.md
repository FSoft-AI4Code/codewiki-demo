# Compaction Control Module

## Introduction

The compaction_control module is a critical component of StarRocks' storage management system, responsible for managing and coordinating compaction operations across the database. Compaction is the process of merging multiple smaller data files into larger, more optimized files to improve query performance and reduce storage overhead. This module provides centralized control and scheduling of compaction tasks, ensuring efficient resource utilization while maintaining system stability.

## Overview

The compaction_control module serves as the orchestration layer for all compaction activities in StarRocks. It handles compaction scheduling, resource allocation, conflict resolution, and monitoring of compaction tasks across different storage engines and table types. The module integrates with various storage subsystems including local storage, lake storage, and persistent indexes to provide comprehensive compaction management.

## Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "Compaction Control Layer"
        CH[CompactionHandler]
        MCS[ManualCompactionScheduler]
        ACS[AutomaticCompactionScheduler]
        CM[CompactionManager]
        CQ[CompactionQueue]
    end

    subgraph "Storage Engine Integration"
        SE[StorageEngine]
        LS[LakeStorage]
        PI[PersistentIndex]
        RS[RowsetManager]
    end

    subgraph "Policy & Decision Engine"
        SCP[SizeTieredCompactionPolicy]
        LCP[LevelBasedCompactionPolicy]
        TC[TimeBasedCompactionPolicy]
        RC[ResourceConstraintChecker]
    end

    subgraph "Task Execution"
        TE[TaskExecutor]
        TW[TaskWorkerPool]
        TM[TaskMonitor]
        TR[TaskReporter]
    end

    CH --> MCS
    CH --> ACS
    CH --> CM
    CM --> CQ
    
    CM --> SE
    CM --> LS
    CM --> PI
    CM --> RS
    
    CM --> SCP
    CM --> LCP
    CM --> TC
    CM --> RC
    
    CM --> TE
    TE --> TW
    TE --> TM
    TM --> TR
    TR --> CH
```

### Component Relationships

```mermaid
graph LR
    subgraph "Frontend Components"
        CH[CompactionHandler]
        CCA[CancelCompactionStmtAnalyzer]
        MCA[ManualCompactionTask]
    end

    subgraph "Backend Components"
        MCT[ManualCompactionTask]
        PCT[PrimaryCompactionTask]
        ICT[IncrementalCompactionTask]
        PKCT[PkIndexMajorCompactionTask]
    end

    subgraph "Storage Components"
        TE[TabletEngine]
        TU[TabletUpdates]
        PI[PersistentIndex]
        RS[Rowset]
    end

    CH --> CCA
    CH --> MCA
    MCA --> MCT
    MCT --> TE
    MCT --> TU
    PCT --> PI
    ICT --> RS
    PKCT --> PI
```

## Core Components

### CompactionHandler

The `CompactionHandler` is the central coordinator for all compaction operations in the frontend. It manages compaction requests, validates compaction eligibility, and coordinates with backend nodes to execute compaction tasks.

**Key Responsibilities:**
- Process manual compaction requests from users
- Coordinate automatic compaction scheduling
- Handle compaction cancellation requests
- Monitor compaction progress and status
- Resolve compaction conflicts and resource contention

**Integration Points:**
- Interfaces with the ALTER system for schema change coordination
- Communicates with backend nodes via RPC for task execution
- Integrates with the transaction manager for consistency guarantees
- Works with the metadata system for tablet state management

### Compaction Policies

The module implements multiple compaction strategies to optimize for different workloads and storage patterns:

#### Size-Tiered Compaction Policy
```mermaid
graph LR
    subgraph "Size Tiered Process"
        ST1[SizeTieredCompactionPolicy]
        ST2[LevelComparator]
        ST3[SizeBasedSelector]
        ST4[MergeScheduler]
    end

    ST1 --> ST2
    ST2 --> ST3
    ST3 --> ST4
```

- Groups rowsets by size tiers
- Merges similarly-sized rowsets together
- Optimizes for write-heavy workloads
- Minimizes write amplification

#### Lake Storage Compaction Policy
```mermaid
graph LR
    subgraph "Lake Storage Process"
        LC1[LakeCompactionPolicy]
        LC2[SizeTieredCompactionPolicy]
        LC3[TxnLogApplier]
        LC4[MetaFileManager]
    end

    LC1 --> LC2
    LC1 --> LC3
    LC1 --> LC4
```

- Specialized compaction for lake storage format
- Handles transactional consistency
- Manages metadata updates during compaction
- Supports cloud-native storage patterns

### Task Management System

```mermaid
graph TB
    subgraph "Task Lifecycle"
        TR[TaskRequest]
        TV[TaskValidation]
        TS[TaskScheduling]
        TE[TaskExecution]
        TC[TaskCompletion]
        TT[TaskTracking]
    end

    TR --> TV
    TV --> TS
    TS --> TE
    TE --> TC
    TC --> TT
    TT --> TR
```

**Task Types:**
- **ManualCompactionTask**: User-initiated compaction operations
- **PrimaryCompactionTask**: Compaction for primary key tables
- **IncrementalCompactionTask**: Incremental compaction for append-only data
- **PkIndexMajorCompactionTask**: Major compaction for persistent indexes

## Data Flow

### Compaction Request Flow

```mermaid
sequenceDiagram
    participant User
    participant FE
    participant CH as CompactionHandler
    participant CM as CompactionManager
    participant BE as Backend
    participant Storage

    User->>FE: Submit compaction request
    FE->>CH: Validate and process request
    CH->>CM: Create compaction task
    CM->>CM: Check resource availability
    CM->>BE: Send compaction task
    BE->>Storage: Execute compaction
    Storage->>BE: Return result
    BE->>CM: Report completion
    CM->>CH: Update status
    CH->>FE: Return response
    FE->>User: Notify completion
```

### Compaction Decision Flow

```mermaid
graph TD
    Start([Compaction Trigger])
    Check1{Manual Request?}
    Check2{Auto-triggered?}
    Check3{Resource Available?}
    Check4{Tablet Healthy?}
    Check5{Policy Allows?}
    Execute[Execute Compaction]
    Queue[Queue for Later]
    Reject[Reject Request]
    End([End])

    Start --> Check1
    Check1 -->|Yes| Check3
    Check1 -->|No| Check2
    Check2 -->|Yes| Check3
    Check2 -->|No| Reject
    Check3 -->|Yes| Check4
    Check3 -->|No| Queue
    Check4 -->|Yes| Check5
    Check4 -->|No| Reject
    Check5 -->|Yes| Execute
    Check5 -->|No| Queue
    Execute --> End
    Queue --> End
    Reject --> End
```

## Integration with Storage Engine

### Tablet-Level Compaction

```mermaid
graph LR
    subgraph "Tablet Components"
        T[Tablet]
        TU[TabletUpdates]
        RS[Rowsets]
        PI[PersistentIndex]
    end

    subgraph "Compaction Integration"
        CE[CompactionEntry]
        MCT[ManualCompactionTask]
        PCT[PrimaryCompactionTask]
    end

    T --> TU
    TU --> RS
    TU --> PI
    TU --> CE
    CE --> MCT
    CE --> PCT
```

The compaction_control module integrates deeply with the tablet management system:

- **TabletUpdates**: Manages versioned data updates and compaction state
- **Rowset Management**: Handles rowset lifecycle during compaction
- **Persistent Index**: Coordinates index compaction with data compaction
- **Version Graph**: Maintains consistency across compaction operations

### Resource Management

```mermaid
graph TB
    subgraph "Resource Controllers"
        RC[ResourceController]
        DC[DiskController]
        MC[MemoryController]
        CC[CPUController]
    end

    subgraph "Compaction Resources"
        DSK[Disk Space]
        MEM[Memory]
        CPU[CPU Cores]
        NET[Network]
    end

    RC --> DC
    RC --> MC
    RC --> CC
    
    DC --> DSK
    MC --> MEM
    CC --> CPU
    RC --> NET
```

## Configuration and Monitoring

### Key Configuration Parameters

- `compaction_max_memory`: Maximum memory allocation for compaction operations
- `compaction_task_queue_size`: Size of the compaction task queue
- `compaction_check_interval_seconds`: Interval for checking compaction eligibility
- `max_compaction_concurrency`: Maximum concurrent compaction tasks
- `compaction_trace_threshold`: Threshold for tracing slow compactions

### Monitoring and Metrics

```mermaid
graph LR
    subgraph "Metrics Collection"
        MC[MetricsCollector]
        CD[CompactionDuration]
        CC[CompactionCount]
        CS[CompactionSize]
        CE[CompactionErrors]
    end

    subgraph "Monitoring Systems"
        PM[PrometheusMetrics]
        FM[FrontendMetrics]
        BM[BackendMetrics]
    end

    MC --> CD
    MC --> CC
    MC --> CS
    MC --> CE
    
    CD --> PM
    CC --> FM
    CS --> BM
    CE --> PM
```

## Error Handling and Recovery

### Compaction Failure Scenarios

1. **Resource Exhaustion**: Automatic backoff and retry with reduced resource allocation
2. **Disk Space Issues**: Pre-compaction space validation and cleanup procedures
3. **Version Conflicts**: Conflict resolution through version graph analysis
4. **Network Failures**: Retry mechanisms with exponential backoff
5. **Data Corruption**: Validation checks and rollback capabilities

### Recovery Mechanisms

```mermaid
graph TD
    Failure[Compaction Failure]
    Detect{Failure Type}
    Retry[Retry Operation]
    Rollback[Rollback Changes]
    Cleanup[Cleanup Resources]
    Alert[Send Alert]
    Log[Log Error]
    
    Failure --> Detect
    Detect -->|Transient| Retry
    Detect -->|Persistent| Rollback
    Retry --> Cleanup
    Rollback --> Cleanup
    Cleanup --> Alert
    Cleanup --> Log
```

## Performance Optimization

### Compaction Scheduling Strategies

1. **Time-based Scheduling**: Off-peak hours for large compactions
2. **Size-based Scheduling**: Priority to larger compactions for better ROI
3. **Query-pattern Scheduling**: Optimize based on query access patterns
4. **Resource-aware Scheduling**: Balance with other system workloads

### Optimization Techniques

- **Incremental Compaction**: Process only changed data segments
- **Parallel Compaction**: Utilize multiple cores for large compactions
- **Smart Filtering**: Skip unnecessary data during compaction
- **Compression Optimization**: Choose optimal compression algorithms

## Security and Access Control

### Permission Model

```mermaid
graph LR
    subgraph "Access Control"
        AC[AccessController]
        CP[CompactionPrivilege]
        AP[AdminPrivilege]
        UP[UserPrivilege]
    end

    subgraph "Operations"
        MC[Manual Compaction]
        CC[Cancel Compaction]
        VC[View Status]
        MC2[Modify Config]
    end

    AC --> CP
    AC --> AP
    AC --> UP
    
    CP --> MC
    AP --> CC
    UP --> VC
    AP --> MC2
```

## Dependencies

### Internal Dependencies

- **[storage_engine](storage_engine.md)**: Core storage management and tablet operations
- **[alter](alter.md)**: Schema change coordination and resource management
- **[transaction](transaction.md)**: Transaction consistency during compaction
- **[query_scheduler](query_scheduler.md)**: Resource allocation and task scheduling

### External Dependencies

- **RPC Framework**: Communication with backend nodes
- **Metadata Service**: Tablet and partition metadata management
- **Metrics System**: Performance monitoring and alerting
- **Configuration Service**: Dynamic configuration management

## Best Practices

### Operational Guidelines

1. **Monitor Compaction Metrics**: Regular monitoring of compaction duration, frequency, and success rates
2. **Resource Planning**: Ensure adequate disk space and memory for compaction operations
3. **Schedule Management**: Balance automatic and manual compaction to avoid resource conflicts
4. **Error Response**: Implement proper alerting and response procedures for compaction failures

### Performance Tuning

1. **Policy Selection**: Choose appropriate compaction policy based on workload characteristics
2. **Concurrency Control**: Adjust compaction concurrency based on system resources
3. **Threshold Tuning**: Optimize compaction triggers for your specific use case
4. **Monitoring Setup**: Implement comprehensive monitoring for proactive issue detection

## Future Enhancements

### Planned Improvements

1. **Machine Learning Integration**: Predictive compaction scheduling based on access patterns
2. **Cloud-Native Optimization**: Enhanced support for cloud storage patterns
3. **Real-time Compaction**: Support for continuous compaction in streaming scenarios
4. **Cross-Table Compaction**: Optimization opportunities across related tables

### Scalability Enhancements

- **Distributed Coordination**: Improved coordination across large clusters
- **Hierarchical Management**: Multi-level compaction management for better scalability
- **Adaptive Policies**: Self-tuning compaction policies based on system feedback
- **Resource Isolation**: Better isolation between compaction and query workloads