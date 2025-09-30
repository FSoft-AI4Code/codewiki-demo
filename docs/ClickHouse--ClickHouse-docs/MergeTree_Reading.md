# MergeTree_Reading Module Documentation

## Introduction

The MergeTree_Reading module is a critical component of the ClickHouse query execution engine, responsible for reading data from MergeTree tables. It implements sophisticated algorithms for efficient data retrieval, including parallel reading, index utilization, and various optimization strategies. This module serves as the bridge between the query planning phase and actual data access, orchestrating how data is read from disk and processed through the query pipeline.

## Core Architecture

### Primary Components

The module centers around the `ReadFromMergeTree` class, which implements the `IQueryPlanStep` interface. This class coordinates the entire reading process, from analyzing which parts and ranges to read, to creating the actual data processing pipeline.

```mermaid
classDiagram
    class ReadFromMergeTree {
        -prepared_parts: RangesInDataParts
        -mutations_snapshot: MergeTreeData::MutationsSnapshotPtr
        -all_column_names: Names
        -data: MergeTreeData
        -query_info: SelectQueryInfo
        -storage_snapshot: StorageSnapshotPtr
        -context: ContextPtr
        -reader_settings: MergeTreeReaderSettings
        -indexes: std::optional<Indexes>
        -analyzed_result_ptr: AnalysisResultPtr
        +read(): Pipe
        +selectRangesToRead(): AnalysisResultPtr
        +spreadMarkRanges(): Pipe
        +initializePipeline(): void
    }

    class PartRangesReadInfo {
        -sum_marks_in_parts: std::vector<size_t>
        -sum_marks: size_t
        -total_rows: size_t
        -adaptive_parts: size_t
        -min_marks_for_concurrent_read: size_t
        -use_uncompressed_cache: bool
        +PartRangesReadInfo()
    }

    class AnalysisResult {
        -parts_with_ranges: RangesInDataParts
        -column_names_to_read: Names
        -selected_parts: size_t
        -selected_marks: size_t
        -selected_rows: size_t
        -read_type: ReadType
        -index_stats: std::vector<IndexStat>
        -sampling: Sampling
    }

    ReadFromMergeTree --> PartRangesReadInfo : uses
    ReadFromMergeTree --> AnalysisResult : produces
```

### Reading Strategies

The module implements multiple reading strategies optimized for different scenarios:

```mermaid
graph TD
    A[ReadFromMergeTree] --> B{Reading Strategy}
    B --> C[Default Reading]
    B --> D[In-Order Reading]
    B --> E[Reverse Order Reading]
    B --> F[Parallel Replicas Reading]
    B --> G[Final Reading]
    
    C --> C1[spreadMarkRangesAmongStreams]
    D --> D1[readInOrder]
    E --> E1[readInOrder with Reverse]
    F --> F1[readFromPoolParallelReplicas]
    G --> G1[spreadMarkRangesAmongStreamsFinal]
    
    C1 --> H[MergeTreeReadPool]
    D1 --> I[MergeTreeReadPoolInOrder]
    F1 --> J[MergeTreeReadPoolParallelReplicas]
```

## Data Flow Architecture

### Query Processing Pipeline

```mermaid
flowchart LR
    A[Query Plan] --> B[ReadFromMergeTree::selectRangesToRead]
    B --> C[Index Analysis]
    C --> D[Partition Pruning]
    D --> E[Primary Key Filtering]
    E --> F[Skip Index Application]
    F --> G[Range Selection]
    G --> H[Pipeline Creation]
    H --> I[Data Reading]
    I --> J[Result Processing]
    
    C --> C1[Primary Key Condition]
    C --> C2[MinMax Index]
    C --> C3[Partition Pruner]
    C --> C4[Skip Indexes]
    
    H --> H1[Thread Pool Selection]
    H --> H2[Reading Strategy]
    H --> H3[Stream Creation]
```

### Index Utilization Flow

```mermaid
sequenceDiagram
    participant Q as Query
    participant R as ReadFromMergeTree
    participant I as IndexBuilder
    participant P as PrimaryKey
    participant M as MinMaxIndex
    participant S as SkipIndex
    participant D as DataParts
    
    Q->>R: Initialize with query info
    R->>I: buildIndexes()
    I->>P: Create KeyCondition
    I->>M: Create MinMaxCondition
    I->>S: Create SkipIndexConditions
    R->>D: filterPartsByPartition()
    R->>D: filterPartsByPrimaryKey()
    R->>D: Apply skip indexes
    D-->>R: Filtered parts with ranges
    R-->>Q: AnalysisResult
```

## Key Components and Dependencies

### External Dependencies

The MergeTree_Reading module integrates with several other system modules:

```mermaid
graph TD
    A[MergeTree_Reading] --> B[Storage_Engine]
    A --> C[Query_Planning]
    A --> D[Interpreters]
    A --> E[Core_Engine]
    A --> F[IO_System]
    
    B --> B1[MergeTreeData]
    B --> B2[MergeTreeSettings]
    B --> B3[MergeTreeReadPool]
    
    C --> C1[QueryPlan]
    C --> C2[PartsSplitter]
    
    D --> D1[Context]
    D --> D2[ExpressionActions]
    D --> D3[ActionsDAG]
    
    E --> E1[Settings]
    E --> E2[SortDescription]
    
    F --> F1[ReadBuffer]
    F --> F2[SeekableReadBuffer]
```

### Internal Component Relationships

```mermaid
graph LR
    A[ReadFromMergeTree] --> B[PartRangesReadInfo]
    A --> C[AnalysisResult]
    A --> D[Indexes]
    A --> E[ReadingAlgorithms]
    
    B --> B1[Mark Counting]
    B --> B2[Concurrency Calculation]
    B --> B3[Cache Decision]
    
    C --> C1[Part Statistics]
    C --> C2[Index Statistics]
    C --> C3[Sampling Info]
    
    D --> D1[Primary Key]
    D --> D2[MinMax Index]
    D --> D3[Skip Indexes]
    D --> D4[Partition Pruner]
    
    E --> E1[ThreadSelectAlgorithm]
    E --> E2[InOrderAlgorithm]
    E --> E3[ReverseOrderAlgorithm]
```

## Reading Process Flow

### Main Reading Algorithm

```mermaid
flowchart TD
    A[initializePipeline] --> B[getAnalysisResult]
    B --> C{Analysis Complete?}
    C -->|No| D[selectRangesToRead]
    D --> E[Build Indexes]
    E --> F[Apply Filters]
    F --> G[Select Parts/Ranges]
    
    C -->|Yes| H{Output Strategy}
    H --> I[Partition Grouping]
    H --> J[Mark Range Spreading]
    
    I --> K[groupStreamsByPartition]
    J --> L[spreadMarkRanges]
    
    K --> M[Create Pipes]
    L --> M
    
    M --> N[Apply Sampling]
    N --> O[Apply Projections]
    O --> P[Initialize Pipeline]
```

### Range Selection Process

```mermaid
sequenceDiagram
    participant RT as ReadFromMergeTree
    participant SE as SelectExecutor
    participant PK as PrimaryKey
    participant PP as PartitionPruner
    participant SI as SkipIndexes
    
    RT->>SE: filterPartsByPartition()
    SE->>PP: Apply partition conditions
    PP-->>SE: Filtered parts
    
    RT->>SE: getSampling()
    SE-->>RT: Sampling info
    
    RT->>SE: filterPartsByPrimaryKeyAndSkipIndexes()
    SE->>PK: Apply primary key condition
    PK-->>SE: PK-filtered ranges
    
    SE->>SI: Apply skip indexes
    SI-->>SE: Index-filtered ranges
    
    SE-->>RT: Final parts with ranges
```

## Optimization Strategies

### Parallel Reading Optimization

The module implements several parallel reading strategies based on data characteristics:

```mermaid
graph TD
    A[Parallel Reading Decision] --> B{Data Location}
    B -->|Remote| C[Remote Reading Strategy]
    B -->|Local| D[Local Reading Strategy]
    
    C --> C1[Prefetched Read Pool]
    C --> C2[Parallel Replicas]
    
    D --> D1[Standard Read Pool]
    D --> D2[In-Order Reading]
    
    A --> E{Query Type}
    E -->|Final| F[Final Reading Strategy]
    E -->|InOrder| G[Ordered Reading Strategy]
    E -->|Default| H[Default Reading Strategy]
```

### Index Optimization

```mermaid
graph LR
    A[Index Optimization] --> B[Primary Key]
    A --> C[MinMax Index]
    A --> D[Skip Indexes]
    A --> E[Partition Pruning]
    
    B --> B1[Range Pruning]
    B --> B2[Mark Selection]
    
    C --> C1[Partition Filtering]
    C --> C2[Min/Max Bounds]
    
    D --> D1[Granule Skipping]
    D --> D2[Index Merging]
    
    E --> E1[Partition Elimination]
    E --> E2[Max Block Filtering]
```

## Configuration and Settings

### Key Settings Integration

The module integrates with multiple setting categories from the Core_Engine module:

- **Reading Settings**: `max_streams_for_merge_tree_reading`, `merge_tree_min_rows_for_concurrent_read`
- **Cache Settings**: `use_uncompressed_cache`, `merge_tree_max_rows_to_use_cache`
- **Index Settings**: `use_skip_indexes`, `force_primary_key`
- **Parallel Settings**: `max_parallel_replicas`, `parallel_replicas_local_plan`

### Performance Tuning

```mermaid
graph TD
    A[Performance Tuning] --> B[Concurrency Control]
    A --> C[Memory Management]
    A --> D[IO Optimization]
    A --> E[Index Selection]
    
    B --> B1[Thread Pool Sizing]
    B --> B2[Mark Range Distribution]
    
    C --> C1[Block Size Optimization]
    C --> C2[Cache Utilization]
    
    D --> D1[Prefetch Strategy]
    D --> D2[Remote vs Local]
    
    E --> E1[Index Priority]
    E --> E2[Condition Pushdown]
```

## Error Handling and Monitoring

### Statistics Collection

The module provides comprehensive statistics for monitoring and debugging:

- **Part Selection**: Number of parts selected at each filtering stage
- **Index Usage**: Which indexes were applied and their effectiveness
- **Performance Metrics**: Marks read, rows selected, cache hit rates
- **Resource Usage**: Memory consumption, thread utilization

### Error Scenarios

```mermaid
graph TD
    A[Error Handling] --> B[Index Errors]
    A --> C[Resource Limits]
    A --> D[Data Consistency]
    
    B --> B1[Primary Key Not Used]
    B --> B2[Index Corruption]
    
    C --> C1[Memory Limits]
    C --> C2[Thread Limits]
    C --> C3[Timeout Handling]
    
    D --> D1[Part Validation]
    D --> D2[Mutation Consistency]
```

## Integration Points

### Query Plan Integration

The module integrates with the Query_Planning module through:

- **Step Interface**: Implements `IQueryPlanStep` for pipeline integration
- **Cost Estimation**: Provides cardinality and cost estimates
- **Parallel Execution**: Coordinates with parallel query execution

### Storage Layer Integration

Integration with the Storage_Engine module includes:

- **Data Part Access**: Through `MergeTreeData` interface
- **Metadata Management**: Using `StorageMetadataPtr`
- **Mutation Handling**: Via `MutationsSnapshotPtr`

## Performance Characteristics

### Scalability Patterns

```mermaid
graph LR
    A[Scalability] --> B[Data Volume]
    A --> C[Concurrency]
    A --> D[Index Efficiency]
    
    B --> B1[Linear with Parts]
    B --> B2[Sublinear with Indexes]
    
    C --> C1[Thread Scaling]
    C --> C2[Replica Scaling]
    
    D --> D1[Selectivity Impact]
    D --> D2[Index Coverage]
```

### Optimization Triggers

The module automatically applies optimizations based on:

- **Query Characteristics**: FINAL, ORDER BY, WHERE conditions
- **Data Distribution**: Part sizes, partition distribution
- **System Resources**: Available memory, CPU cores
- **Storage Type**: Local vs remote filesystem characteristics

## References

- [Storage_Engine Module](Storage_Engine.md) - For MergeTree data storage details
- [Query_Planning Module](Query_Planning.md) - For query plan integration
- [Core_Engine Module](Core_Engine.md) - For settings and configuration
- [Interpreters Module](Interpreters.md) - For context and expression handling