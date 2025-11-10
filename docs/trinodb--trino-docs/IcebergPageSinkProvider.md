# IcebergPageSinkProvider Module Documentation

## Introduction

The IcebergPageSinkProvider module is a critical component of the Trino Iceberg connector that handles the creation of page sinks for writing data to Iceberg tables. It implements the `ConnectorPageSinkProvider` interface and serves as the factory for creating different types of page sinks used in INSERT, CREATE TABLE AS SELECT (CTAS), MERGE, and table optimization operations.

This module bridges the gap between Trino's execution engine and Iceberg's data writing capabilities, providing a unified interface for various write operations while handling the complexities of Iceberg's table format, partitioning, and file organization.

## Architecture Overview

The IcebergPageSinkProvider acts as a central factory that creates specialized page sinks based on the type of operation being performed. It integrates with multiple Trino and Iceberg components to provide a comprehensive data writing solution.

```mermaid
graph TB
    subgraph "Trino Execution Engine"
        CE[Connector Engine]
        CS[Connector Session]
        CTH[Connector Transaction Handle]
    end
    
    subgraph "IcebergPageSinkProvider"
        IPSP[IcebergPageSinkProvider]
        IPS[IcebergPageSink]
        IMS[IcebergMergeSink]
    end
    
    subgraph "Supporting Components"
        IFSF[IcebergFileSystemFactory]
        IFWF[IcebergFileWriterFactory]
        PIF[PageIndexerFactory]
        PS[PageSorter]
        TM[TypeManager]
    end
    
    subgraph "Iceberg Integration"
        Schema[Iceberg Schema]
        PSPEC[PartitionSpec]
        LP[LocationProvider]
        FF[FileFormat]
    end
    
    CE -->|creates| IPSP
    IPSP -->|creates| IPS
    IPSP -->|creates| IMS
    
    IPSP -.->|uses| IFSF
    IPSP -.->|uses| IFWF
    IPSP -.->|uses| PIF
    IPSP -.->|uses| PS
    IPSP -.->|uses| TM
    
    IPS -.->|configures| Schema
    IPS -.->|configures| PSPEC
    IPS -.->|configures| LP
    IPS -.->|configures| FF
```

## Core Components

### IcebergPageSinkProvider

The main class that implements `ConnectorPageSinkProvider` interface. It serves as the entry point for creating page sinks and handles different types of write operations:

- **INSERT operations**: Creates page sinks for inserting data into existing tables
- **CREATE TABLE AS SELECT (CTAS)**: Creates page sinks for writing data during table creation
- **MERGE operations**: Creates specialized merge sinks for handling UPDATE/INSERT/DELETE operations
- **Table optimization**: Creates page sinks for table optimization procedures like OPTIMIZE

#### Key Dependencies

```mermaid
graph LR
    IPSP[IcebergPageSinkProvider]
    
    subgraph "External Dependencies"
        IFSF[IcebergFileSystemFactory]
        IFWF[IcebergFileWriterFactory]
        PIF[PageIndexerFactory]
        PS[PageSorter]
        TM[TypeManager]
        JC[JsonCodec<CommitTaskData>]
        SFWC[SortingFileWriterConfig]
    end
    
    IPSP -->|depends on| IFSF
    IPSP -->|depends on| IFWF
    IPSP -->|depends on| PIF
    IPSP -->|depends on| PS
    IPSP -->|depends on| TM
    IPSP -->|depends on| JC
    IPSP -->|depends on| SFWC
```

## Data Flow Architecture

The data flow through IcebergPageSinkProvider varies based on the operation type:

```mermaid
sequenceDiagram
    participant QE as Query Execution
    participant IPSP as IcebergPageSinkProvider
    participant IPS as IcebergPageSink
    participant IFWF as IcebergFileWriterFactory
    participant IFS as IcebergFileSystem
    participant IC as Iceberg Catalog
    
    QE->>IPSP: createPageSink(handle, session)
    IPSP->>IPSP: parse schema & partition spec
    IPSP->>IPSP: create location provider
    IPSP->>IPSP: create file system
    IPSP->>IPS: create page sink
    IPS->>IFWF: create file writers
    IPS->>IFS: write data files
    IPS->>IC: commit metadata
    IPS-->>QE: return completion
```

## Component Interactions

### Page Sink Creation Process

The provider creates different types of page sinks based on the handle type:

```mermaid
graph TD
    Start[Handle Received]
    HandleType{Handle Type?}
    
    CTAS[CREATE TABLE AS SELECT]
    Insert[INSERT]
    Merge[MERGE]
    Optimize[OPTIMIZE Procedure]
    
    IPS[IcebergPageSink]
    IMS[IcebergMergeSink]
    
    Start --> HandleType
    HandleType -->|OutputTableHandle| CTAS
    HandleType -->|InsertTableHandle| Insert
    HandleType -->|MergeTableHandle| Merge
    HandleType -->|TableExecuteHandle| Optimize
    
    CTAS --> IPS
    Insert --> IPS
    Merge --> IMS
    Optimize --> IPS
```

### Configuration and Setup

Each page sink creation involves several configuration steps:

```mermaid
graph LR
    subgraph "Configuration Sources"
        Session[ConnectorSession]
        Handle[WritableTableHandle]
        Config[Session Properties]
    end
    
    subgraph "Setup Process"
        ParseSchema[Parse Iceberg Schema]
        ParsePartition[Parse Partition Spec]
        CreateLP[Create Location Provider]
        CreateFS[Create FileSystem]
        Configure[Configure PageSink]
    end
    
    Session -->|provides| Config
    Handle -->|contains| ParseSchema
    Handle -->|contains| ParsePartition
    Handle -->|provides| CreateLP
    Session -->|identity| CreateFS
    
    ParseSchema --> Configure
    ParsePartition --> Configure
    CreateLP --> Configure
    CreateFS --> Configure
```

## Integration with Trino Ecosystem

### Connector Framework Integration

The IcebergPageSinkProvider integrates with Trino's connector framework through several interfaces:

```mermaid
graph TB
    subgraph "Trino SPI Interfaces"
        CPSP[ConnectorPageSinkProvider]
        CPS[ConnectorPageSink]
        CMS[ConnectorMergeSink]
        CTH[ConnectorTransactionHandle]
        CSH[ConnectorSession]
    end
    
    subgraph "Iceberg Implementation"
        IPSP[IcebergPageSinkProvider]
        IPS[IcebergPageSink]
        IMS[IcebergMergeSink]
    end
    
    IPSP -.->|implements| CPSP
    IPS -.->|implements| CPS
    IMS -.->|implements| CMS
    
    CPSP -->|uses| CTH
    CPSP -->|uses| CSH
```

### File System Abstraction

The provider leverages Trino's file system abstraction layer for flexible storage support:

```mermaid
graph LR
    IPSP[IcebergPageSinkProvider]
    IFSF[IcebergFileSystemFactory]
    TFS[TrinoFileSystem]
    
    subgraph "Storage Backends"
        S3[S3FileSystem]
        Azure[AzureFileSystem]
        GCS[GcsFileSystem]
        HDFS[HdfsFileSystem]
        Local[LocalFileSystem]
    end
    
    IPSP -->|creates via| IFSF
    IFSF -->|creates| TFS
    TFS -->|can be| S3
    TFS -->|can be| Azure
    TFS -->|can be| GCS
    TFS -->|can be| HDFS
    TFS -->|can be| Local
```

## Supported Operations

### Standard Write Operations

1. **INSERT INTO**: Writes data to existing Iceberg tables
2. **CREATE TABLE AS SELECT**: Creates new tables with query results
3. **MERGE**: Handles complex UPDATE/INSERT/DELETE operations

### Table Maintenance Operations

1. **OPTIMIZE**: Rewrites data files for better performance
2. **OPTIMIZE_MANIFESTS**: Manages manifest file organization
3. **Other procedures**: Handled through metadata operations

## Error Handling and Validation

The provider includes several validation mechanisms:

- **Schema validation**: Ensures Iceberg schema compatibility
- **Partition spec validation**: Validates partition specifications
- **File format validation**: Confirms supported file formats
- **Location validation**: Verifies output paths and permissions

## Performance Considerations

### Memory Management

- Configurable buffer sizes for sorting operations
- Maximum open file limits for concurrent writes
- Partition-aware memory allocation

### Parallel Processing

- Support for parallel writer instances
- Partition-based data distribution
- Concurrent file writing capabilities

## Dependencies

### Internal Dependencies

- **IcebergFileSystemFactory**: Creates file system instances
- **IcebergFileWriterFactory**: Creates file writers for different formats
- **IcebergPageSink**: Handles actual data writing
- **IcebergMergeSink**: Handles merge operations

### External Dependencies

- **Trino SPI**: Core interfaces and types
- **Iceberg Library**: Table format and metadata handling
- **File System Libraries**: Storage backend support

## Configuration

### Session Properties

- `max_partitions_per_writer`: Controls partition parallelism
- Sorting buffer sizes and file limits

### Table Properties

- File format selection (PARQUET, ORC, AVRO)
- Storage properties for location configuration
- Partition specifications

## Related Documentation

- [Iceberg Connector](IcebergConnector.md) - Overall Iceberg connector architecture
- [IcebergMetadata](IcebergMetadata.md) - Metadata management operations
- [IcebergPageSourceProvider](IcebergPageSourceProvider.md) - Data reading operations
- [IcebergFileSystemFactory](IcebergFileSystemFactory.md) - File system abstraction
- [TrinoFileSystem](TrinoFileSystem.md) - File system interface

## Process Flows

### INSERT Operation Flow

```mermaid
graph TD
    Start[INSERT Query]
    Parse[Parse Query & Plan]
    CreateHandle[Create InsertTableHandle]
    CreateSink[Call createPageSink]
    Configure[Configure IcebergPageSink]
    WriteData[Write Data Pages]
    Commit[Commit Files]
    UpdateMeta[Update Metadata]
    End[Complete]
    
    Start --> Parse
    Parse --> CreateHandle
    CreateHandle --> CreateSink
    CreateSink --> Configure
    Configure --> WriteData
    WriteData --> Commit
    Commit --> UpdateMeta
    UpdateMeta --> End
```

### MERGE Operation Flow

```mermaid
graph TD
    Start[MERGE Query]
    Parse[Parse & Analyze]
    CreateMerge[Create MergeTableHandle]
    CreateSink[Call createMergeSink]
    CreateIPS[Create IcebergPageSink]
    CreateIMS[Create IcebergMergeSink]
    Process[Process Merge Operations]
    Write[Write Changes]
    Commit[Commit Transaction]
    End[Complete]
    
    Start --> Parse
    Parse --> CreateMerge
    CreateMerge --> CreateSink
    CreateSink --> CreateIPS
    CreateSink --> CreateIMS
    CreateIPS --> Process
    CreateIMS --> Process
    Process --> Write
    Write --> Commit
    Commit --> End
```

This comprehensive documentation provides a complete understanding of the IcebergPageSinkProvider module's role, architecture, and integration within the Trino ecosystem.