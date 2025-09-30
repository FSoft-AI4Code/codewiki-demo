# Partition Core Module Documentation

## Overview

The partition_core module is a fundamental component of StarRocks' storage engine that manages partition metadata and lifecycle operations. It provides the core data structures and operations for handling table partitions, which are essential for data organization, query optimization, and distributed storage management.

## Purpose and Core Functionality

The partition_core module serves as the central hub for partition management in StarRocks, offering:

- **Partition Metadata Management**: Maintains comprehensive metadata for table partitions including version tracking, state management, and distribution information
- **Physical Partition Abstraction**: Manages the relationship between logical partitions and their physical storage representations
- **Version Control**: Implements sophisticated version management for partition data, supporting both shared-nothing and shared-data storage modes
- **Lifecycle Operations**: Handles partition creation, modification, and deletion operations
- **Data Organization**: Provides mechanisms for organizing data across multiple physical partitions within a logical partition

## Architecture

### Core Components

```mermaid
graph TB
    subgraph "Partition Core Module"
        P[Partition]
        PP[PhysicalPartition]
        DI[DistributionInfo]
        MI[MaterializedIndex]
        
        P -->|contains| PP
        P -->|has| DI
        PP -->|has| MI
    end
    
    subgraph "Related Modules"
        PI[partition_info.md]
        PB[partition_builder.md]
        PK[partition_key.md]
        CM[column_management.md]
    end
    
    P -.->|references| PI
    P -.->|uses| PB
    P -.->|manages| PK
    PP -.->|contains| CM
```

### Component Relationships

```mermaid
graph LR
    subgraph "Partition Structure"
        LP[Logical Partition]
        PP1[Physical Partition 1]
        PP2[Physical Partition 2]
        PPn[Physical Partition N]
        
        LP -->|1:N| PP1
        LP -->|1:N| PP2
        LP -->|1:N| PPn
    end
    
    subgraph "Version Management"
        VV[Visible Version]
        NV[Next Version]
        DV[Data Version]
        VE[Version Epoch]
        
        VV -->|triggers| NV
        DV -->|separate| VV
        VE -->|coordinates| VV
    end
```

## Key Data Structures

### Partition Class

The `Partition` class is the central entity that represents a logical partition in StarRocks. It encapsulates:

- **Identity**: Unique ID and name for the partition
- **State Management**: Current partition state (NORMAL, ROLLUP, SCHEMA_CHANGE)
- **Physical Partitions**: Mapping of physical partitions that store the actual data
- **Version Information**: Comprehensive version tracking for data consistency
- **Distribution Info**: How data is distributed across nodes

### Physical Partition Management

Each logical partition can contain multiple physical partitions:

```mermaid
graph TD
    LP[Logical Partition]
    
    subgraph "Physical Partitions"
        PP1[Physical Partition 1<br/>ID: 1001]
        PP2[Physical Partition 2<br/>ID: 1002]
        PPT[Temp Partition<br/>ID: 1003]
    end
    
    subgraph "Storage Elements"
        BI[Base Index]
        VRI[Visible Rollup Indexes]
        SI[Shadow Indexes]
    end
    
    LP -->|manages| PP1
    LP -->|manages| PP2
    LP -->|manages| PPT
    
    PP1 -->|contains| BI
    PP1 -->|contains| VRI
    PP1 -->|contains| SI
```

## Version Management System

### Version Types

The partition_core module implements a sophisticated version management system:

1. **Visible Version**: The current version visible to users
2. **Next Version**: The version that will be committed next
3. **Data Version**: Version tracking for data changes (separate from visible version in shared-data mode)
4. **Version Epoch**: Global transaction identifier for consistency

### Version Flow

```mermaid
sequenceDiagram
    participant T as Transaction
    participant P as Partition
    participant V as Version System
    
    T->>P: Begin Transaction
    P->>V: Get Next Version
    V-->>P: nextVersion + 1
    
    T->>P: Commit Data
    P->>V: Update Committed Version
    
    T->>P: Publish Transaction
    P->>V: Update Visible Version
    V-->>P: visibleVersion = committedVersion
```

## Data Flow and Operations

### Partition Creation Flow

```mermaid
flowchart TD
    Start[Create Partition Request]
    Validate[Validate Parameters]
    CreatePP[Create Physical Partition]
    SetDist[Set Distribution Info]
    AddMaps[Add to ID/Name Maps]
    InitVersion[Initialize Versions]
    End[Partition Created]
    
    Start --> Validate
    Validate --> CreatePP
    CreatePP --> SetDist
    SetDist --> AddMaps
    AddMaps --> InitVersion
    InitVersion --> End
```

### Data Access Patterns

```mermaid
graph LR
    subgraph "Query Operations"
        Q1[Point Query]
        Q2[Range Query]
        Q3[Full Scan]
    end
    
    subgraph "Partition Operations"
        PO1[getSubPartition by ID]
        PO2[getSubPartition by Name]
        PO3[getDefaultPhysicalPartition]
    end
    
    Q1 -->|uses| PO1
    Q2 -->|uses| PO2
    Q3 -->|uses| PO3
```

## Integration with Other Modules

### Storage Engine Integration

The partition_core module integrates with various storage engine components:

- **[storage_engine](storage_engine.md)**: Provides physical storage management
- **[rowset_management](rowset_management.md)**: Manages rowset lifecycle within partitions
- **[data_compaction](data_compaction.md)**: Handles partition-level compaction operations

### Query Engine Integration

```mermaid
graph TB
    subgraph "Query Processing"
        QP[Query Planner]
        PS[Partition Pruner]
        SE[Scan Executor]
    end
    
    subgraph "Partition Core"
        PC[Partition Core]
        PI[Partition Info]
        PK[Partition Key]
    end
    
    QP -->|requests| PC
    PS -->|filters| PI
    SE -->|scans| PK
```

## State Management

### Partition States

The module supports different partition states:

- **NORMAL**: Standard operational state
- **ROLLUP**: Deprecated state for rollup operations
- **SCHEMA_CHANGE**: Deprecated state for schema modifications

### State Transitions

```mermaid
stateDiagram-v2
    [*] --> NORMAL: Create Partition
    NORMAL --> [*]: Drop Partition
    
    note right of NORMAL
        Most operations occur
        in this state
    end note
```

## Performance Considerations

### Memory Management

- **Lazy Initialization**: Physical partitions are created on-demand
- **Map-based Lookups**: Efficient O(1) access to sub-partitions by ID
- **TreeMap for Names**: Case-insensitive name lookups with ordering

### Concurrency Control

- **Atomic Operations**: Version updates use atomic variables
- **Immutable Flags**: Partition immutability controlled via AtomicBoolean
- **Concurrent Collections**: Thread-safe maps for partition storage

## Error Handling and Recovery

### Version Consistency

The module implements several mechanisms to ensure version consistency:

- **Gson Post-processing**: Handles version migration during deserialization
- **Default Value Assignment**: Provides sensible defaults for missing version fields
- **Validation Checks**: Ensures version coherence during operations

### Recovery Mechanisms

```mermaid
flowchart TD
    Failure[System Failure]
    Detect[Detect Inconsistency]
    Validate[Validate Versions]
    Repair[Apply Defaults]
    Resume[Resume Operations]
    
    Failure --> Detect
    Detect --> Validate
    Validate --> Repair
    Repair --> Resume
```

## Configuration and Tuning

### Key Parameters

- **PARTITION_INIT_VERSION**: Initial version for new partitions (default: 1L)
- **Version Epoch Generation**: Uses global GTID generator for consistency

### Best Practices

1. **Partition Size**: Keep partitions reasonably sized for optimal performance
2. **Version Management**: Monitor version gaps in shared-data mode
3. **Physical Partition Count**: Limit number of physical partitions per logical partition

## Monitoring and Observability

### Key Metrics

- **Partition Count**: Number of active partitions
- **Version Lag**: Difference between next and visible versions
- **Data Size**: Total data size across all physical partitions
- **Row Count**: Total row count for the partition

### Logging

The module provides comprehensive logging for:
- Partition creation and deletion
- Version changes and state transitions
- Error conditions and recovery operations

## Future Enhancements

### Planned Improvements

1. **Enhanced State Management**: More granular partition states
2. **Improved Version Tracking**: Better support for time-travel queries
3. **Dynamic Partitioning**: Automatic partition management based on data patterns
4. **Cross-Partition Operations**: Optimized operations spanning multiple partitions

## References

- [partition_info](partition_info.md) - Detailed partition information management
- [partition_builder](partition_builder.md) - Partition construction utilities
- [partition_key](partition_key.md) - Partition key handling
- [storage_engine](storage_engine.md) - Storage engine integration
- [rowset_management](rowset_management.md) - Rowset lifecycle management