# Thrift Metastore Client

The Thrift Metastore Client module provides the primary interface for Trino's Hive connector to interact with Hive Metastore services using the Apache Thrift protocol. This module implements a robust, retry-aware client that handles all metadata operations required for Hive table management, including schema operations, table lifecycle management, partition handling, statistics management, and transactional support.

## Overview

The Thrift Metastore Client serves as the bridge between Trino's Hive connector and external Hive Metastore services. It implements comprehensive error handling, automatic retry logic with exponential backoff, and connection pooling to ensure reliable metadata operations across distributed Hive deployments. The client supports both traditional Hive tables and ACID transactional tables, providing full compatibility with Hive's evolving metadata requirements.

## Architecture

### Core Components

```mermaid
graph TB
    subgraph "Thrift Metastore Client"
        THM[ThriftHiveMetastore]
        TMCF[IdentityAwareMetastoreClientFactory]
        TMC[ThriftMetastoreClient]
        TMS[ThriftMetastoreStats]
        TMU[ThriftMetastoreUtil]
    end
    
    subgraph "External Dependencies"
        HM[Hive Metastore Service]
        TFS[TrinoFileSystem]
        SPI[Trino SPI]
    end
    
    THM --> TMCF
    THM --> TMC
    THM --> TMS
    THM --> TMU
    TMCF --> HM
    TMC --> HM
    THM --> TFS
    THM --> SPI
```

### Component Relationships

```mermaid
graph LR
    subgraph "Client Factory Layer"
        IMCF[IdentityAwareMetastoreClientFactory]
        TMCF[ThriftMetastoreClientFactory]
    end
    
    subgraph "Core Client Implementation"
        THM[ThriftHiveMetastore]
        Retry[RetryDriver]
        Stats[ThriftMetastoreStats]
    end
    
    subgraph "Protocol Layer"
        TMC[ThriftMetastoreClient]
        HM[Hive Metastore Thrift API]
    end
    
    IMCF --> TMCF
    TMCF --> TMC
    THM --> IMCF
    THM --> Retry
    THM --> Stats
    TMC --> HM
```

## Key Features

### Comprehensive Metadata Operations

The Thrift Metastore Client provides complete coverage of Hive Metastore operations:

- **Database Management**: Create, drop, alter databases with full schema lifecycle support
- **Table Operations**: Create, drop, alter tables with comprehensive validation and error handling
- **Partition Management**: Add, drop, alter partitions with batch operation support
- **Statistics Management**: Table and partition-level column statistics with concurrent update support
- **Privilege Management**: Role-based access control with grant/revoke operations
- **Transaction Support**: Full ACID transaction support with locking mechanisms

### Robust Error Handling and Retry Logic

```mermaid
graph TD
    A[Metastore Operation] --> B{Exception Type}
    B -->|TException| C[Retry with Exponential Backoff]
    B -->|NoSuchObjectException| D[Return Empty Result]
    B -->|AlreadyExistsException| E[Throw AlreadyExists Error]
    B -->|InvalidOperationException| F[Throw InvalidOperation Error]
    B -->|Other Exception| G[Propagate Error]
    
    C --> H{Retry Attempts < Max?}
    H -->|Yes| I[Wait with Backoff]
    I --> A
    H -->|No| J[Throw TrinoException]
```

### Connection Management and Performance

The client implements sophisticated connection management:

- **Connection Pooling**: Reuses metastore connections to minimize overhead
- **Identity-Aware Connections**: Supports different authentication contexts
- **Concurrent Statistics Updates**: Parallel processing of partition statistics
- **Configurable Timeouts**: Flexible timeout and retry configuration
- **Performance Metrics**: Comprehensive statistics collection for monitoring

## Data Flow

### Metadata Retrieval Flow

```mermaid
sequenceDiagram
    participant Trino
    participant ThriftHiveMetastore
    participant RetryDriver
    participant ThriftMetastoreClient
    participant HiveMetastore
    
    Trino->>ThriftHiveMetastore: getTable(database, table)
    ThriftHiveMetastore->>RetryDriver: retry().run()
    RetryDriver->>ThriftMetastoreClient: createMetastoreClient()
    ThriftMetastoreClient->>HiveMetastore: getTable()
    HiveMetastore-->>ThriftMetastoreClient: Table object
    ThriftMetastoreClient-->>RetryDriver: Return result
    RetryDriver-->>ThriftHiveMetastore: Return result
    ThriftHiveMetastore-->>Trino: Optional<Table>
```

### Statistics Update Flow

```mermaid
sequenceDiagram
    participant Trino
    participant ThriftHiveMetastore
    participant WriteStatisticsExecutor
    participant ThriftMetastoreClient
    participant HiveMetastore
    
    Trino->>ThriftHiveMetastore: updateTableStatistics()
    ThriftHiveMetastore->>ThriftHiveMetastore: getCurrentTableStatistics()
    ThriftHiveMetastore->>ThriftHiveMetastore: calculateUpdatedStatistics()
    ThriftHiveMetastore->>ThriftMetastoreClient: alterTable()
    ThriftHiveMetastore->>WriteStatisticsExecutor: submit(updateColumnStatistics)
    WriteStatisticsExecutor->>ThriftMetastoreClient: setTableColumnStatistics()
    ThriftMetastoreClient->>HiveMetastore: update statistics
    HiveMetastore-->>ThriftMetastoreClient: success
    WriteStatisticsExecutor-->>ThriftHiveMetastore: complete
    ThriftHiveMetastore-->>Trino: success
```

## Transaction and Lock Management

### ACID Transaction Support

The client provides comprehensive support for Hive's ACID transactional tables:

```mermaid
graph TD
    A[Begin Transaction] --> B["openTransaction()"]
    B --> C[Acquire Table Locks]
    C --> D[Perform Operations]
    D --> E{Commit or Abort}
    E -->|Commit| F["commitTransaction()"]
    E -->|Abort| G["abortTransaction()"]
    F --> H[Release Locks]
    G --> H
    
    I[Concurrent Operations] --> J[Lock Manager]
    J --> K[Shared Read Locks]
    J --> L[Exclusive Write Locks]
    J --> M[Partition-level Locks]
```

### Lock Acquisition Process

```mermaid
graph LR
    A[Acquire Lock Request] --> B[Create LockRequest]
    B --> C[Set Lock Components]
    C --> D["Call acquireLock()"]
    D --> E{Lock State}
    E -->|ACQUIRED| F[Return Lock ID]
    E -->|WAITING| G["checkLock() with Retry"]
    G --> E
    E -->|Timeout| H[Throw Lock Exception]
    
    I[Lock Types] --> J[SHARED_READ]
    I --> K[EXCLUSIVE]
    I --> L[TABLE_LEVEL]
    I --> M[PARTITION_LEVEL]
```

## Integration with Trino Ecosystem

### Hive Connector Integration

```mermaid
graph TB
    subgraph "Trino Hive Connector"
        HM[HiveMetadata]
        HSM[HiveSplitManager]
        HPSP[HivePageSourceProvider]
        HPSIP[HivePageSinkProvider]
    end
    
    subgraph "Thrift Metastore Client"
        THM[ThriftHiveMetastore]
        TMS[ThriftMetastoreStats]
    end
    
    subgraph "Metastore Abstraction"
        HMS[HiveMetastore Interface]
        MSM[MetastoreUtil]
    end
    
    HM --> THM
    HSM --> THM
    HPSP --> THM
    HPSIP --> THM
    THM --> HMS
    THM --> TMS
    THM --> MSM
```

### Configuration and Dependencies

The Thrift Metastore Client integrates with several Trino subsystems:

- **FileSystem Integration**: Uses [TrinoFileSystem](Filesystem Abstraction Layer.md) for data file operations
- **Security Framework**: Integrates with [Trino Security](Trino Server & API.md#security-framework) for authentication
- **Statistics Framework**: Works with [Trino Statistics](SQL Analyzer, Planner & Optimizer.md#cost--statistics) for query optimization
- **Error Handling**: Leverages [Trino SPI](Trino SPI.md) exception types for consistent error reporting

## Configuration Options

### Connection and Retry Configuration

- **Backoff Parameters**: Configurable exponential backoff for retries
- **Timeout Settings**: Connection timeouts and maximum wait times
- **Retry Limits**: Maximum retry attempts and time limits
- **Connection Pooling**: Client factory configuration for connection reuse

### Feature Flags

- **deleteFilesOnDrop**: Automatic cleanup of data files on table/partition drop
- **assumeCanonicalPartitionKeys**: Optimization for partition key handling
- **useSparkTableStatisticsFallback**: Compatibility with Spark-generated statistics

## Performance Characteristics

### Statistics Collection

The client provides comprehensive performance metrics through `ThriftMetastoreStats`:

- Operation-level timing and success rates
- Connection pool utilization metrics
- Retry frequency and failure analysis
- Lock acquisition timing and contention

### Optimization Features

- **Batch Operations**: Efficient bulk operations for partitions and statistics
- **Concurrent Updates**: Parallel processing of independent statistics updates
- **Connection Reuse**: Minimizes connection overhead through pooling
- **Smart Retries**: Exponential backoff with jitter to avoid thundering herd

## Error Handling and Reliability

### Exception Classification

The client implements sophisticated exception handling:

- **Retryable Exceptions**: Network issues, temporary metastore unavailability
- **Non-retryable Exceptions**: Invalid objects, permission errors, schema conflicts
- **Special Cases**: Handling of Hive version-specific exception types

### Reliability Features

- **Circuit Breaker Pattern**: Prevents cascading failures
- **Graceful Degradation**: Continues operation when statistics updates fail
- **Resource Cleanup**: Automatic cleanup of locks and connections
- **Transaction Safety**: Ensures transaction consistency even on failure

## Security and Authentication

### Identity Management

The client supports multiple authentication modes:

- **User Impersonation**: Operations performed on behalf of query users
- **Service Authentication**: Dedicated service account for metastore access
- **Principal Mapping**: Translation between Trino and Hive principal types

### Access Control Integration

- **Privilege Validation**: Validates user privileges before operations
- **Role Management**: Supports Hive's role-based access control
- **Audit Trail**: Comprehensive logging for security auditing

## Monitoring and Observability

### Metrics and Logging

The client provides extensive observability features:

- **Operation Metrics**: Detailed timing and success rates per operation type
- **Connection Metrics**: Pool utilization and connection lifecycle tracking
- **Error Metrics**: Categorized error rates and retry statistics
- **Performance Logging**: Structured logging for troubleshooting

### Health Checks

- **Connection Health**: Regular validation of metastore connectivity
- **Operation Health**: Success rate monitoring for critical operations
- **Resource Health**: Connection pool and thread pool monitoring

## Future Enhancements

### Planned Improvements

- **Async Operations**: Non-blocking variants of long-running operations
- **Caching Layer**: Intelligent caching of frequently accessed metadata
- **Multi-Metastore Support**: Federation across multiple metastore instances
- **Enhanced Metrics**: More granular performance and reliability metrics

### Compatibility Considerations

- **Hive Version Support**: Maintaining compatibility across Hive versions
- **Protocol Evolution**: Support for new Thrift protocol features
- **Cloud Integration**: Enhanced support for cloud-based metastore services