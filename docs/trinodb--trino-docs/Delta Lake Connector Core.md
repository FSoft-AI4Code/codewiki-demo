# Delta Lake Connector Core Module

## Introduction

The Delta Lake Connector Core module provides Trino's native integration with Delta Lake tables, enabling efficient querying and management of Delta Lake datasets. This module implements the core functionality that allows Trino to read from and write to Delta Lake tables while maintaining ACID transaction guarantees and leveraging Delta Lake's advanced features like time travel, schema evolution, and transaction logs.

The connector bridges Trino's distributed SQL engine with Delta Lake's storage format, providing seamless access to Delta Lake tables through standard SQL operations while preserving the reliability and performance characteristics of both systems.

## Architecture Overview

The Delta Lake Connector Core follows a layered architecture that integrates with Trino's plugin framework and leverages Delta Lake's transaction log protocol:

```mermaid
graph TB
    subgraph "Trino Engine"
        TE[Trino Engine]
        CM[Connector Manager]
        QE[Query Execution]
    end
    
    subgraph "Delta Lake Connector Core"
        DP[DeltaLakePlugin]
        DM[DeltaLakeMetadata]
        SM[DeltaLakeSplitManager]
        PSP[DeltaLakePageSourceProvider]
        PSP2[DeltaLakePageSinkProvider]
        TLA[TransactionLogAccess]
    end
    
    subgraph "Storage Layer"
        FS[FileSystem Abstraction]
        TL[Transaction Log]
        DF[Data Files]
        MS[Metastore]
    end
    
    TE --> CM
    CM --> DP
    DP --> DM
    DM --> SM
    DM --> TLA
    SM --> PSP
    SM --> PSP2
    TLA --> FS
    TLA --> TL
    PSP --> FS
    PSP2 --> FS
    PSP --> DF
    PSP2 --> DF
    DM --> MS
```

## Core Components

### DeltaLakePlugin

The `DeltaLakePlugin` class serves as the entry point for the Delta Lake connector, implementing Trino's `Plugin` interface. It registers the connector factory with Trino's plugin manager, enabling the creation of Delta Lake connector instances.

**Key Responsibilities:**
- Plugin registration and lifecycle management
- Connector factory provisioning
- Integration with Trino's plugin architecture

**Dependencies:**
- [Trino SPI Plugin Framework](Trino SPI.md#plugin-architecture)

### DeltaLakeMetadata

The `DeltaLakeMetadata` class is the central component that implements Trino's `ConnectorMetadata` interface. It provides comprehensive metadata operations for Delta Lake tables, including table discovery, schema management, and transaction coordination.

**Key Responsibilities:**
- Table metadata retrieval and caching
- Schema evolution and column management
- Transaction log processing and version management
- Partition pruning and constraint pushdown
- Statistics collection and management
- Time travel query support

**Core Features:**
- **Snapshot Management**: Maintains table snapshots with version tracking
- **Transaction Coordination**: Handles concurrent write operations with conflict detection
- **Schema Evolution**: Supports adding, dropping, and renaming columns
- **Partition Optimization**: Implements partition pruning for efficient queries
- **Statistics Integration**: Collects and utilizes table statistics for query optimization

**Key Methods:**
- `getSnapshot()`: Retrieves table snapshots with caching
- `getTableHandle()`: Creates table handles for query processing
- `applyFilter()`: Applies partition and column constraints
- `createTable()`: Handles table creation with transaction log initialization
- `finishInsert()`: Commits insert operations to transaction log

**Dependencies:**
- [Trino SPI Connector Framework](Trino SPI.md#connector-framework)
- [FileSystem Abstraction Layer](Filesystem Abstraction Layer.md)
- [Hive Support Libraries](Hive Support Libraries.md)

## Data Flow Architecture

### Query Execution Flow

```mermaid
sequenceDiagram
    participant Client
    participant TrinoEngine
    participant DeltaLakeMetadata
    participant TransactionLogAccess
    participant DeltaLakeSplitManager
    participant DeltaLakePageSourceProvider
    participant Storage
    
    Client->>TrinoEngine: Submit Query
    TrinoEngine->>DeltaLakeMetadata: getTableHandle()
    DeltaLakeMetadata->>TransactionLogAccess: loadSnapshot()
    TransactionLogAccess->>Storage: Read Transaction Log
    Storage-->>TransactionLogAccess: Transaction Log Data
    TransactionLogAccess-->>DeltaLakeMetadata: TableSnapshot
    DeltaLakeMetadata-->>TrinoEngine: DeltaLakeTableHandle
    
    TrinoEngine->>DeltaLakeSplitManager: getSplits()
    DeltaLakeSplitManager->>TransactionLogAccess: getActiveFiles()
    TransactionLogAccess->>Storage: List Data Files
    Storage-->>TransactionLogAccess: File Listings
    TransactionLogAccess-->>DeltaLakeSplitManager: AddFileEntry Stream
    DeltaLakeSplitManager-->>TrinoEngine: DeltaLakeSplit
    
    TrinoEngine->>DeltaLakePageSourceProvider: createPageSource()
    DeltaLakePageSourceProvider->>Storage: Read Parquet Files
    Storage-->>DeltaLakePageSourceProvider: Parquet Data
    DeltaLakePageSourceProvider-->>TrinoEngine: Page Data
    TrinoEngine-->>Client: Query Results
```

### Write Operation Flow

```mermaid
sequenceDiagram
    participant Client
    participant TrinoEngine
    participant DeltaLakeMetadata
    participant TransactionLogWriter
    participant Storage
    
    Client->>TrinoEngine: INSERT/UPDATE Statement
    TrinoEngine->>DeltaLakeMetadata: beginInsert()/beginMerge()
    DeltaLakeMetadata-->>TrinoEngine: Insert/Merge Handle
    
    TrinoEngine->>TrinoEngine: Process Data
    TrinoEngine->>DeltaLakeMetadata: finishInsert()/finishMerge()
    DeltaLakeMetadata->>TransactionLogWriter: createWriter()
    
    TransactionLogWriter->>Storage: Read Current Version
    Storage-->>TransactionLogWriter: Current Version
    
    TransactionLogWriter->>TransactionLogWriter: Validate No Conflicts
    TransactionLogWriter->>Storage: Write New Data Files
    Storage-->>TransactionLogWriter: File Locations
    
    TransactionLogWriter->>Storage: Write Transaction Log Entry
    TransactionLogWriter->>Storage: Write Checkpoint (if needed)
    TransactionLogWriter-->>DeltaLakeMetadata: Commit Success
    DeltaLakeMetadata-->>TrinoEngine: Operation Complete
    TrinoEngine-->>Client: Success Response
```

## Component Interactions

### Transaction Log Processing

The connector implements a sophisticated transaction log processing system that ensures ACID properties:

```mermaid
graph LR
    subgraph "Transaction Log Components"
        TLA[TransactionLogAccess]
        TLR[TransactionLogReader]
        TLW[TransactionLogWriter]
        CW[CheckpointWriter]
    end
    
    subgraph "Data Structures"
        TS[TableSnapshot]
        ME[MetadataEntry]
        PE[ProtocolEntry]
        AFE[AddFileEntry]
        RFE[RemoveFileEntry]
    end
    
    subgraph "Storage"
        TL[Transaction Log Files]
        CP[Checkpoint Files]
        DF[Data Files]
    end
    
    TLA --> TLR
    TLA --> TLW
    TLA --> CW
    
    TLR --> TS
    TLR --> ME
    TLR --> PE
    TLR --> AFE
    TLR --> RFE
    
    TLW --> AFE
    TLW --> RFE
    TLW --> ME
    TLW --> PE
    
    CW --> CP
    
    TLR --> TL
    TLW --> TL
    CW --> TL
    
    TLA --> DF
```

### Metadata Caching and Optimization

The connector implements intelligent caching mechanisms to optimize metadata operations:

```mermaid
graph TB
    subgraph "Caching Layer"
        SC[Snapshot Cache]
        LC[Latest Version Cache]
        SAC[Statistics Access Cache]
    end
    
    subgraph "Metadata Operations"
        GS[getSnapshot]
        GLV[latestTableVersions]
        SUA[statisticsAccess]
    end
    
    subgraph "Storage Access"
        TL[Transaction Log]
        MS[Metastore]
        ES[Extended Statistics]
    end
    
    GS --> SC
    GLV --> LC
    SUA --> SAC
    
    SC --> TL
    LC --> TL
    SAC --> ES
    
    GS --> MS
    SUA --> MS
```

## Key Features Implementation

### Time Travel Support

The connector supports Delta Lake's time travel feature, allowing queries to access historical versions of tables:

```mermaid
graph LR
    subgraph "Time Travel Components"
        VQ[Version Query]
        TQ[Temporal Query]
        FV[Find Version]
        SV[Snapshot Version]
    end
    
    subgraph "Version Resolution"
        TV[Target Version]
        TT[Temporal Time]
        LV[Latest Version]
    end
    
    subgraph "Storage"
        TL[Transaction Log]
        TS[Table Snapshots]
    end
    
    VQ --> TV
    TQ --> TT
    FV --> LV
    
    TV --> SV
    TT --> FV
    LV --> SV
    
    SV --> TL
    SV --> TS
```

### Schema Evolution

The connector handles schema changes while maintaining backward compatibility:

```mermaid
stateDiagram-v2
    [*] --> InitialSchema
    InitialSchema --> AddColumn: ADD COLUMN
    AddColumn --> SchemaV2
    SchemaV2 --> RenameColumn: RENAME COLUMN
    RenameColumn --> SchemaV3
    SchemaV3 --> DropColumn: DROP COLUMN
    DropColumn --> SchemaV4
    SchemaV4 --> ModifyColumn: MODIFY COLUMN
    ModifyColumn --> SchemaV5
    
    state "Schema Versions" as schema_versions {
        InitialSchema: Version 0
        SchemaV2: Version 1
        SchemaV3: Version 2
        SchemaV4: Version 3
        SchemaV5: Version 4
    }
```

### Concurrent Write Handling

The connector implements sophisticated conflict detection and resolution for concurrent operations:

```mermaid
sequenceDiagram
    participant Writer1
    participant Writer2
    participant TransactionLog
    participant ConflictDetector
    
    Writer1->>TransactionLog: Read Current Version
    TransactionLog-->>Writer1: Version 10
    Writer2->>TransactionLog: Read Current Version
    TransactionLog-->>Writer2: Version 10
    
    Writer1->>Writer1: Prepare Changes
    Writer2->>Writer2: Prepare Changes
    
    Writer1->>TransactionLog: Attempt Commit Version 11
    TransactionLog->>ConflictDetector: Check Conflicts
    ConflictDetector-->>TransactionLog: No Conflicts
    TransactionLog-->>Writer1: Commit Success
    
    Writer2->>TransactionLog: Attempt Commit Version 11
    TransactionLog->>ConflictDetector: Check Conflicts
    ConflictDetector-->>TransactionLog: Conflict Detected
    TransactionLog-->>Writer2: Retry Required
    
    Writer2->>TransactionLog: Read Current Version
    TransactionLog-->>Writer2: Version 11
    Writer2->>Writer2: Rebase Changes
    Writer2->>TransactionLog: Attempt Commit Version 12
    TransactionLog-->>Writer2: Commit Success
```

## Integration Points

### Trino SPI Integration

The connector integrates with Trino's SPI through well-defined interfaces:

- **Plugin Interface**: `DeltaLakePlugin` implements Trino's `Plugin` interface
- **ConnectorMetadata**: `DeltaLakeMetadata` provides metadata operations
- **ConnectorSplitManager**: Manages data splitting for distributed processing
- **ConnectorPageSource**: Handles data reading from Delta Lake files
- **ConnectorPageSink**: Manages data writing to Delta Lake tables

### Storage Layer Integration

The connector leverages multiple storage abstractions:

- **FileSystem Abstraction**: Unified interface for different storage systems (S3, Azure, GCS, HDFS)
- **Transaction Log Access**: Specialized component for reading/writing Delta transaction logs
- **Metastore Integration**: Connects with Hive metastore for table metadata
- **Parquet Integration**: Utilizes Trino's Parquet reader for columnar data access

### Dependencies

The Delta Lake Connector Core module depends on several key Trino modules:

- **[Trino SPI](Trino SPI.md)**: Core plugin and connector interfaces
- **[FileSystem Abstraction Layer](Filesystem Abstraction Layer.md)**: Unified storage access
- **[ORC & Parquet Libraries](ORC & Parquet Libraries.md)**: Columnar data format support
- **[Hive Support Libraries](Hive Support Libraries.md)**: Metastore integration and utilities
- **[Plugin Toolkit](Plugin Toolkit.md)**: Common plugin utilities and security frameworks

## Performance Optimizations

### Partition Pruning

The connector implements intelligent partition pruning to minimize data scanning:

```mermaid
graph TD
    subgraph "Query Processing"
        QP[Query Parser]
        PC[Partition Columns]
        PF[Partition Filter]
    end
    
    subgraph "Optimization"
        PP[Partition Pruning]
        DC[Domain Compilation]
        FE[File Enumeration]
    end
    
    subgraph "Execution"
        SL[Split List]
        PS[Partitioned Splits]
        DR[Data Reading]
    end
    
    QP --> PC
    PC --> PF
    PF --> PP
    PP --> DC
    DC --> FE
    FE --> SL
    SL --> PS
    PS --> DR
```

### Statistics Collection

The connector supports comprehensive statistics collection for query optimization:

- **Column Statistics**: Min/max values, null counts, distinct value estimates
- **File Statistics**: Row counts, file sizes, modification times
- **Partition Statistics**: Partition-level aggregations and metadata
- **Extended Statistics**: Advanced statistics for complex query optimization

### Caching Strategies

Multiple caching layers optimize performance:

- **Snapshot Caching**: Caches table snapshots to avoid repeated transaction log reads
- **Metadata Caching**: Caches table metadata and schema information
- **Statistics Caching**: Caches collected statistics for query planning
- **File Listing Caching**: Caches data file listings for repeated queries

## Error Handling and Recovery

### Transaction Failure Handling

The connector implements robust error handling for transaction failures:

```mermaid
stateDiagram-v2
    [*] --> BeginTransaction
    BeginTransaction --> WriteData: Success
    BeginTransaction --> HandleFailure: Failure
    
    WriteData --> WriteTransactionLog: Data Written
    WriteData --> CleanupData: Write Failed
    
    WriteTransactionLog --> CommitSuccess: Log Written
    WriteTransactionLog --> CleanupBoth: Log Write Failed
    
    HandleFailure --> RetryTransaction: Retryable
    HandleFailure --> FailOperation: Non-retryable
    
    CleanupData --> [*]
    CleanupBoth --> CleanupData
    CommitSuccess --> [*]
    FailOperation --> [*]
    RetryTransaction --> BeginTransaction
```

### Conflict Resolution

The connector handles various types of conflicts:

- **Concurrent Writes**: Detects and resolves write conflicts using retry mechanisms
- **Schema Conflicts**: Handles schema evolution conflicts during concurrent operations
- **Metadata Conflicts**: Resolves conflicts in table metadata updates
- **Partition Conflicts**: Manages conflicts in partition-specific operations

## Security and Access Control

### Security Integration

The connector integrates with Trino's security framework:

- **Access Control**: Leverages Trino's access control mechanisms
- **Authentication**: Supports Trino's authentication methods
- **Authorization**: Implements table-level and column-level authorization
- **Audit Logging**: Provides comprehensive audit trails for operations

### Data Protection

The connector ensures data protection through:

- **Encryption Support**: Works with encrypted storage systems
- **Secure File Access**: Implements secure file system access patterns
- **Credential Management**: Manages credentials for storage systems
- **Network Security**: Supports secure network protocols

## Monitoring and Observability

### Metrics Collection

The connector provides comprehensive metrics for monitoring:

- **Query Performance**: Execution times, data scanned, partitions pruned
- **Transaction Metrics**: Commit times, conflict rates, retry counts
- **Storage Metrics**: File access patterns, cache hit rates, I/O statistics
- **Error Metrics**: Failure rates, error types, recovery times

### Logging and Debugging

The connector includes extensive logging capabilities:

- **Transaction Logging**: Detailed transaction operation logs
- **Debug Information**: Comprehensive debug information for troubleshooting
- **Performance Logs**: Performance-related logging for optimization
- **Error Logs**: Detailed error information for problem resolution

This comprehensive documentation provides a thorough understanding of the Delta Lake Connector Core module's architecture, functionality, and integration within the Trino ecosystem. The module serves as a critical bridge between Trino's distributed SQL engine and Delta Lake's reliable storage format, enabling powerful analytics capabilities while maintaining data integrity and performance.