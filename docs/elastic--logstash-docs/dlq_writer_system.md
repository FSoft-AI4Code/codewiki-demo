# Dead Letter Queue Writer System

## Overview

The Dead Letter Queue (DLQ) Writer System is a critical component of Logstash's error handling infrastructure that manages the persistent storage of events that cannot be processed successfully. This system provides reliable, thread-safe writing capabilities with advanced features including segment management, retention policies, storage quotas, and automatic cleanup mechanisms.

The system operates on a segment-based architecture where events are written to temporary files that are atomically moved to permanent segments when size or time thresholds are reached. This design ensures data integrity and enables concurrent access patterns between writers and readers.

## Architecture Overview

```mermaid
graph TB
    subgraph "DLQ Writer System"
        DLQFactory[DeadLetterQueueFactory]
        DLQWriter[DeadLetterQueueWriter]
        Builder[DeadLetterQueueWriter.Builder]
        
        subgraph "Core Components"
            RecordWriter[RecordIOWriter]
            SegmentMgr[Segment Manager]
            PolicyEngine[Policy Engine]
            Scheduler[Scheduler Service]
        end
        
        subgraph "Storage Management"
            TempFiles[Temporary Files]
            SealedSegments[Sealed Segments]
            FileLock[File Lock]
        end
        
        subgraph "Policy Systems"
            AgePolicy[Age Retention Policy]
            SizePolicy[Storage Size Policy]
            FlushPolicy[Flush Policy]
        end
    end
    
    subgraph "External Dependencies"
        EventAPI[Event API]
        FileSystem[File System]
        Monitoring[Monitoring System]
        Settings[Settings Management]
    end
    
    DLQFactory --> DLQWriter
    Builder --> DLQWriter
    DLQWriter --> RecordWriter
    DLQWriter --> SegmentMgr
    DLQWriter --> PolicyEngine
    DLQWriter --> Scheduler
    
    SegmentMgr --> TempFiles
    SegmentMgr --> SealedSegments
    SegmentMgr --> FileLock
    
    PolicyEngine --> AgePolicy
    PolicyEngine --> SizePolicy
    PolicyEngine --> FlushPolicy
    
    DLQWriter --> EventAPI
    DLQWriter --> FileSystem
    DLQWriter --> Monitoring
    DLQWriter --> Settings
```

## Component Architecture

### DeadLetterQueueFactory

The factory class manages a static registry of DLQ writers, providing centralized access and lifecycle management:

```mermaid
classDiagram
    class DeadLetterQueueFactory {
        -ConcurrentHashMap~String,DeadLetterQueueWriter~ REGISTRY
        -long MAX_SEGMENT_SIZE_BYTES
        +getWriter(id, dlqPath, maxQueueSize, flushInterval, storageType) DeadLetterQueueWriter
        +getWriter(id, dlqPath, maxQueueSize, flushInterval, storageType, age) DeadLetterQueueWriter
        +release(id) DeadLetterQueueWriter
        -newWriter(...) DeadLetterQueueWriter
    }
    
    class DeadLetterQueueWriter {
        -Path queuePath
        -long maxSegmentSize
        -long maxQueueSize
        -QueueStorageType storageType
        -AtomicLong currentQueueSize
        -RecordIOWriter currentWriter
        -ReentrantLock lock
        +writeEntry(event, pluginName, pluginId, reason)
        +close()
        +getCurrentQueueSize() long
        +getDroppedEvents() long
        +getExpiredEvents() long
    }
    
    DeadLetterQueueFactory --> DeadLetterQueueWriter : creates/manages
```

### DeadLetterQueueWriter

The core writer component handles all DLQ operations with sophisticated segment and policy management:

**Key Responsibilities:**
- Thread-safe event writing with ReentrantLock synchronization
- Segment lifecycle management (creation, sealing, cleanup)
- Policy enforcement (age retention, storage limits, flush intervals)
- Concurrent access coordination with readers
- Metrics tracking and error reporting

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant Plugin as Plugin/Filter
    participant Factory as DLQFactory
    participant Writer as DLQWriter
    participant RecordIO as RecordIOWriter
    participant FileSystem as File System
    participant Scheduler as Scheduler
    
    Plugin->>Factory: getWriter(id, config)
    Factory->>Writer: create/retrieve writer
    Factory-->>Plugin: return writer
    
    Plugin->>Writer: writeEntry(event, plugin, reason)
    Writer->>Writer: acquire lock
    Writer->>Writer: check policies
    
    alt Storage policy violation
        Writer->>Writer: drop event or clean segments
    else Age policy violation
        Writer->>Writer: delete expired segments
    else Normal write
        Writer->>RecordIO: writeEvent(serialized)
        RecordIO->>FileSystem: write to temp file
        
        alt Segment full
            Writer->>Writer: finalizeSegment()
            Writer->>FileSystem: atomic move temp to sealed
            Writer->>RecordIO: create new writer
        end
    end
    
    Writer->>Writer: release lock
    
    par Background Operations
        Scheduler->>Writer: scheduledFlushCheck()
        Writer->>Writer: check stale segments
        Writer->>Writer: apply retention policies
    and
        Writer->>Writer: watchForDeletedNotification()
        Writer->>Writer: update queue metrics
    end
```

## Segment Management

The system uses a sophisticated segment-based storage model:

```mermaid
stateDiagram-v2
    [*] --> Creating : nextWriter()
    Creating --> Writing : first event
    Writing --> Writing : subsequent events
    Writing --> Sealing : size limit OR time limit OR close
    Sealing --> Sealed : atomic move
    Sealed --> [*] : normal lifecycle
    
    Writing --> Cleanup : age policy
    Sealed --> Cleanup : age/size policy
    Cleanup --> [*] : file deleted
    
    state Writing {
        [*] --> TempFile
        TempFile --> RecordIO : write operations
    }
    
    state Sealing {
        [*] --> AtomicMove
        AtomicMove --> UpdateMetrics
        UpdateMetrics --> NotifyScheduler
    }
```

### Segment Lifecycle

1. **Creation**: New segments start as temporary files (`.log.tmp`)
2. **Writing**: Events are written using RecordIOWriter with proper serialization
3. **Sealing**: When limits are reached, segments are atomically moved to permanent files (`.log`)
4. **Monitoring**: Background processes monitor for cleanup and policy enforcement
5. **Cleanup**: Expired or oversized segments are removed based on configured policies

## Policy Management

### Storage Policies

```mermaid
flowchart TD
    WriteRequest[Write Request] --> CheckSize{Size Check}
    CheckSize -->|Under Limit| WriteEvent[Write Event]
    CheckSize -->|Over Limit| CheckPolicy{Storage Policy}
    
    CheckPolicy -->|DROP_NEWER| DropEvent[Drop Event & Increment Counter]
    CheckPolicy -->|DROP_OLDER| CleanOld[Remove Oldest Segments]
    
    CleanOld --> ReCheck{Still Over Limit?}
    ReCheck -->|Yes| CleanOld
    ReCheck -->|No| WriteEvent
    
    WriteEvent --> UpdateMetrics[Update Queue Size]
    DropEvent --> LogError[Log Error & Update Metrics]
```

### Age Retention Policy

```mermaid
flowchart TD
    ScheduledCheck[Scheduled Check] --> GetOldest[Get Oldest Segment]
    GetOldest --> CheckAge{Age > Retention?}
    CheckAge -->|No| Continue[Continue Normal Operation]
    CheckAge -->|Yes| DeleteSegment[Delete Expired Segment]
    DeleteSegment --> UpdateRef[Update Oldest Reference]
    UpdateRef --> CheckAge
```

## Concurrency and Thread Safety

The system handles multiple concurrent scenarios:

```mermaid
graph TB
    subgraph "Writer Thread Safety"
        WriteLock[ReentrantLock]
        AtomicOps[Atomic Operations]
        ThreadSafe[Thread-Safe Collections]
    end
    
    subgraph "Background Threads"
        FlushScheduler[Flush Scheduler]
        FSWatcher[File System Watcher]
        PolicyEnforcer[Policy Enforcer]
    end
    
    subgraph "Reader Coordination"
        FileLocks[File Locks]
        AtomicMoves[Atomic File Operations]
        Notifications[Cleanup Notifications]
    end
    
    WriteLock --> AtomicOps
    AtomicOps --> ThreadSafe
    
    FlushScheduler --> WriteLock
    FSWatcher --> AtomicOps
    PolicyEnforcer --> WriteLock
    
    FileLocks --> AtomicMoves
    AtomicMoves --> Notifications
```

## Integration Points

### Event API Integration
- Integrates with [event_api](event_api.md) for event processing and metadata management
- Uses Event serialization and DLQEntry structures
- Implements duplicate detection through metadata inspection

### Plugin System Integration
- Works with [plugin_system](plugin_system.md) for plugin identification and error context
- Receives plugin name, ID, and failure reason for comprehensive error tracking
- Supports plugin-specific DLQ writers through factory pattern

### Monitoring Integration
- Provides metrics through [metrics_system](metrics_system.md) integration
- Tracks dropped events, expired events, queue size, and error states
- Supports real-time monitoring of DLQ health and performance

### Settings Management
- Configured through [settings_management](settings_management.md) system
- Supports dynamic configuration of retention policies, size limits, and flush intervals
- Validates configuration parameters and provides sensible defaults

## Configuration and Usage

### Builder Pattern Configuration

```java
DeadLetterQueueWriter writer = DeadLetterQueueWriter
    .newBuilder(queuePath, maxSegmentSize, maxQueueSize, flushInterval)
    .storageType(QueueStorageType.DROP_OLDER)
    .retentionTime(Duration.ofDays(7))
    .build();
```

### Factory-based Access

```java
DeadLetterQueueWriter writer = DeadLetterQueueFactory.getWriter(
    "pipeline-id", 
    "/var/log/logstash/dlq", 
    1024 * 1024 * 100, // 100MB
    Duration.ofSeconds(30),
    QueueStorageType.DROP_NEWER,
    Duration.ofDays(3)
);
```

## Error Handling and Recovery

The system implements comprehensive error handling:

1. **File System Errors**: Graceful handling of I/O exceptions with proper cleanup
2. **Corruption Recovery**: Automatic detection and handling of corrupted segments
3. **Lock Conflicts**: Proper file locking to prevent concurrent access issues
4. **Resource Management**: Automatic cleanup of resources and temporary files
5. **Graceful Shutdown**: Proper segment finalization during system shutdown

## Performance Characteristics

- **Write Performance**: Optimized for high-throughput sequential writes
- **Memory Usage**: Minimal memory footprint with streaming operations
- **Disk Usage**: Efficient segment-based storage with automatic cleanup
- **Concurrency**: Thread-safe operations with minimal lock contention
- **Scalability**: Supports multiple concurrent writers per pipeline

## Dependencies

### Internal Dependencies
- [core_data_structures](core_data_structures.md): Event serialization and data access
- [common_utilities](common_utilities.md): File system utilities and buffer management
- [logging_system](logging_system.md): Comprehensive logging and error reporting

### External Dependencies
- Java NIO for efficient file operations
- Apache Log4j for logging
- Google Guava for utility functions
- Java concurrent utilities for thread safety

## Related Components

- [dlq_reader_system](dlq_reader_system.md): Companion reader system for DLQ consumption
- [plugin_integration_layer](plugin_integration_layer.md): Plugin-specific DLQ integration
- [queue_management](queue_management.md): General queue management infrastructure
- [pipeline_execution](pipeline_execution.md): Pipeline integration and event flow

The DLQ Writer System serves as a critical reliability component in Logstash's architecture, ensuring that no events are lost during processing failures while maintaining system performance and resource constraints.