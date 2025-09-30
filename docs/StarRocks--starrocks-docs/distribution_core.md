# Distribution Core Module Documentation

## Introduction

The distribution_core module is a fundamental component of StarRocks' catalog system that manages data distribution strategies across the cluster. It provides the abstract foundation and concrete implementations for how data is distributed across tablets and nodes, directly impacting query performance, data locality, and load balancing.

This module sits at the intersection of the catalog management system and the storage engine, defining how table data is physically organized and distributed across the cluster infrastructure.

## Architecture Overview

```mermaid
graph TB
    subgraph "Distribution Core Module"
        DI[DistributionInfo<br/><i>Abstract Base Class</i>]
        HD[HashDistributionInfo<br/><i>Hash-based Distribution</i>]
        RD[RandomDistributionInfo<br/><i>Random Distribution</i>]
        DB[DistributionInfoBuilder<br/><i>Builder Pattern</i>]
    end
    
    subgraph "Catalog System Dependencies"
        CM[Column Management]
        PM[Partition Management]
        TM[Table Management]
    end
    
    subgraph "Storage Engine Dependencies"
        SE[Storage Engine]
        TI[Tablet Management]
        RI[Replica Management]
    end
    
    subgraph "Query Engine Dependencies"
        QP[Query Planner]
        JE[Join Execution]
        AG[Aggregation Engine]
    end
    
    DI -->|implements| HD
    DI -->|implements| RD
    DB -->|builds| DI
    
    CM -->|uses| DI
    PM -->|uses| DI
    TM -->|uses| DI
    
    DI -->|informs| SE
    DI -->|informs| TI
    DI -->|informs| RI
    
    QP -->|queries| DI
    JE -->|uses| DI
    AG -->|uses| DI
```

## Core Components

### DistributionInfo (Abstract Base Class)

The `DistributionInfo` abstract class serves as the foundation for all distribution strategies in StarRocks. It defines the contract that concrete distribution implementations must follow and provides common functionality for distribution management.

**Key Responsibilities:**
- Define distribution type enumeration (HASH, RANDOM)
- Provide serialization/deserialization support
- Establish the interface for distribution column management
- Support colocation requirements for distributed computing

**Core Interface:**
```java
public abstract class DistributionInfo implements Writable {
    // Distribution type management
    public enum DistributionInfoType { HASH, RANDOM }
    
    // Core distribution properties
    protected DistributionInfoType type;
    protected String typeStr;
    
    // Abstract methods for concrete implementations
    public abstract int getBucketNum();
    public abstract boolean supportColocate();
    public abstract List<ColumnId> getDistributionColumns();
    public abstract DistributionInfo copy();
}
```

### Distribution Strategies

#### Hash Distribution
Hash distribution is the primary strategy for ensuring data locality and efficient query processing. It distributes data based on hash values of specified columns, ensuring that rows with the same distribution key values are colocated.

**Use Cases:**
- Join operations on distribution keys
- Aggregation operations
- Colocated analytics workloads

#### Random Distribution  
Random distribution provides uniform data distribution across tablets without considering specific column values. This strategy is useful when no natural distribution key exists or when uniform distribution is desired.

**Use Cases:**
- Tables without clear distribution patterns
- Uniform load distribution requirements
- Initial data loading scenarios

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant Client
    participant FE as Frontend
    participant DI as DistributionInfo
    participant BE as Backend
    participant Storage as Storage Engine
    
    Client->>FE: CREATE TABLE with distribution
    FE->>DI: Create DistributionInfo
    DI->>DI: Validate distribution strategy
    DI->>FE: Return distribution metadata
    FE->>Storage: Persist distribution info
    
    Client->>FE: INSERT data
    FE->>DI: Calculate distribution
    DI->>DI: Hash/Random distribution logic
    DI->>FE: Return target tablets
    FE->>BE: Route to appropriate backends
    BE->>Storage: Store data with distribution
    
    Client->>FE: SELECT query
    FE->>DI: Analyze distribution for optimization
    DI->>FE: Provide distribution metadata
    FE->>BE: Optimize query execution plan
    BE->>Storage: Execute with distribution awareness
```

## Component Interactions

### Catalog Integration

```mermaid
graph LR
    subgraph "Distribution Core"
        DI[DistributionInfo]
        DB[DistributionInfoBuilder]
    end
    
    subgraph "Column Management"
        COL[Column]
        CID[ColumnId]
        CS[ColumnStats]
    end
    
    subgraph "Partition Management"
        PART[Partition]
        PI[PartitionInfo]
        PK[PartitionKey]
    end
    
    subgraph "Table Management"
        TBL[Table]
        TM[TableMetadata]
    end
    
    DI -->|references| COL
    DI -->|uses| CID
    DB -->|builds with| CS
    
    PART -->|contains| DI
    PI -->|manages| DI
    PK -->|influences| DI
    
    TBL -->|defines| DI
    TM -->|stores| DI
```

### Query Optimization Integration

```mermaid
graph TD
    subgraph "Distribution Core"
        DI[DistributionInfo]
        DC[DistributionColumns]
    end
    
    subgraph "Query Engine"
        QP[QueryPlanner]
        JH[JoinHashMap]
        AG[Aggregator]
        SC[ScanOperator]
    end
    
    subgraph "Optimization"
        CO[ColocationOptimizer]
        BPO[BucketPruningOptimizer]
        DRO[DistributionRewriter]
    end
    
    DI -->|enables| CO
    DC -->|drives| BPO
    
    CO -->|optimizes| QP
    BPO -->|optimizes| SC
    DRO -->|rewrites| JH
    
    QP -->|uses| AG
    JH -->|uses| DI
    SC -->|queries| DI
```

## Key Features

### 1. Distribution Strategy Flexibility
The module supports multiple distribution strategies through a plugin architecture, allowing different distribution algorithms to be implemented and deployed based on workload requirements.

### 2. Colocation Support
Built-in support for data colocation ensures that related data is stored together, enabling efficient distributed joins and aggregations without data shuffling.

### 3. Dynamic Distribution Management
Supports dynamic modification of distribution strategies through the catalog system, allowing tables to adapt to changing workload patterns.

### 4. Query Optimization Integration
Deep integration with the query optimizer enables distribution-aware query planning, including bucket pruning, colocation optimization, and join order optimization.

### 5. Serialization and Persistence
Robust serialization support ensures distribution metadata is consistently persisted across the cluster and can be recovered during system restarts.

## Process Flows

### Table Creation with Distribution

```mermaid
flowchart TD
    Start[Client CREATE TABLE]
    Parse[Parse Distribution Clause]
    Validate[Validate Distribution Columns]
    CreateDist[Create DistributionInfo]
    CalcBuckets[Calculate Bucket Count]
    AssignTablets[Assign Tablets to Backends]
    Persist[Persist Distribution Metadata]
    Complete[Table Creation Complete]
    
    Start --> Parse
    Parse --> Validate
    Validate --> CreateDist
    CreateDist --> CalcBuckets
    CalcBuckets --> AssignTablets
    AssignTablets --> Persist
    Persist --> Complete
    
    Validate -.->|invalid| Error[Error: Invalid Distribution]
    Error --> End[End]
    Complete --> End
```

### Query Execution with Distribution Optimization

```mermaid
flowchart TD
    Start[Query Received]
    Parse[Parse Query]
    AnalyzeDist[Analyze Distribution]
    CheckColocate[Check Colocation]
    OptimizeJoin[Optimize Join Order]
    PruneBuckets[Prune Buckets]
    GeneratePlan[Generate Execution Plan]
    Execute[Execute Query]
    
    Start --> Parse
    Parse --> AnalyzeDist
    AnalyzeDist --> CheckColocate
    CheckColocate --> OptimizeJoin
    OptimizeJoin --> PruneBuckets
    PruneBuckets --> GeneratePlan
    GeneratePlan --> Execute
    
    CheckColocate -.->|colocated| SkipShuffle[Skip Data Shuffle]
    SkipShuffle --> GeneratePlan
```

## Dependencies and Integration Points

### Upstream Dependencies
- **Column Management Module**: Provides column metadata and statistics used for distribution decisions
- **Type System Module**: Ensures distribution columns have compatible types
- **Catalog Persistence Layer**: Stores and retrieves distribution metadata

### Downstream Dependencies
- **Storage Engine**: Uses distribution information for data placement and retrieval
- **Query Execution Engine**: Leverages distribution for query optimization and execution
- **Tablet Management System**: Creates and manages tablets based on distribution strategy

### Related Modules
- [column_management](column_management.md): Column metadata and statistics
- [partition_management](partition_management.md): Partition-level distribution coordination
- [table_management](table_management.md): Table-level distribution configuration
- [query_execution](query_execution.md): Distribution-aware query processing
- [storage_engine](storage_engine.md): Physical data storage based on distribution

## Configuration and Management

### Distribution Configuration
Distribution strategies are configured during table creation through SQL DDL statements:

```sql
-- Hash Distribution Example
CREATE TABLE users (
    user_id BIGINT,
    name VARCHAR(100),
    email VARCHAR(200)
)
DISTRIBUTED BY HASH(user_id) BUCKETS 32;

-- Random Distribution Example  
CREATE TABLE logs (
    log_id BIGINT,
    timestamp DATETIME,
    message TEXT
)
DISTRIBUTED BY RANDOM BUCKETS 64;
```

### Runtime Management
The distribution core module provides runtime APIs for:
- Distribution metadata inspection
- Distribution strategy validation
- Bucket count optimization
- Colocation analysis

## Performance Considerations

### Distribution Key Selection
Choosing appropriate distribution keys is critical for performance:
- High cardinality columns for even distribution
- Frequently joined columns for colocation benefits
- Query filter columns for bucket pruning

### Bucket Count Tuning
Optimal bucket counts depend on:
- Cluster size and capacity
- Data volume and growth projections
- Query concurrency requirements
- Storage engine characteristics

### Colocation Optimization
Colocation strategies should consider:
- Join frequency and patterns
- Data skew potential
- Load balancing requirements
- Schema evolution implications

## Future Enhancements

### Planned Features
1. **Adaptive Distribution**: Automatic distribution strategy adjustment based on workload analysis
2. **Multi-dimensional Distribution**: Support for composite distribution keys
3. **Distribution Hints**: Query-level distribution hints for optimization override
4. **Distribution Analytics**: Comprehensive distribution performance analytics and recommendations

### Scalability Improvements
- Distributed distribution metadata management
- Incremental distribution strategy changes
- Support for extremely large bucket counts
- Cross-cluster distribution coordination

This documentation provides a comprehensive overview of the distribution_core module, its architecture, and its role within the StarRocks system. The module's flexible design enables efficient data distribution strategies that adapt to diverse workload requirements while maintaining system performance and scalability.