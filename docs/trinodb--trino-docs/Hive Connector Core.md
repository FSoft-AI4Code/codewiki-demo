# Hive Connector Core Module

## Purpose

The Hive Connector Core module is the foundational component of Trino's Hive connector that provides comprehensive integration with Apache Hive data warehouses. It enables Trino to query and manipulate data stored in Hive tables across various storage formats (ORC, Parquet, Avro, TextFile, etc.) and distributed file systems (HDFS, S3, Azure, GCS). The module handles the complete lifecycle of Hive table operations including metadata management, data access, transaction coordination, and integration with different Hive metastore implementations.

## Architecture

```mermaid
graph TB
    subgraph "Trino Query Engine"
        QE[Query Engine]
        CM[Connector Manager]
    end
    
    subgraph "Hive Connector Core"
        subgraph "Lifecycle & Metadata"
            HP[HivePlugin]
            HTM[HiveTransactionManager]
            HM[HiveMetadata]
        end
        
        subgraph "Data Access"
            HSM[HiveSplitManager]
            HPSP[HivePageSourceProvider]
            HPSP2[HivePageSinkProvider]
        end
        
        subgraph "Metastore Clients"
            THM[ThriftHiveMetastore]
            GHM[GlueHiveMetastore]
        end
        
        subgraph "Utilities"
            HB[HiveBucketing]
        end
    end
    
    subgraph "External Systems"
        HMS[Hive Metastore]
        FS[File System]
        SD[Storage Drivers]
    end
    
    QE --> CM
    CM --> HP
    HP --> HTM
    HTM --> HM
    HM --> HSM
    HSM --> HPSP
    HM --> HPSP2
    
    HSM --> FS
    HPSP --> SD
    HPSP2 --> SD
    
    THM --> HMS
    GHM --> HMS
    HSM --> HB
```

## Core Components

### Hive Connector Lifecycle & Metadata
- **HivePlugin**: Entry point that registers the connector with Trino and provides connector factories
- **HiveTransactionManager**: Manages transaction lifecycle and provides per-transaction metadata instances
- **HiveMetadata**: Central component handling all metadata operations including table creation, alteration, statistics management, and partition operations

### Hive Data Access
- **HiveSplitManager**: Generates splits for Hive tables by querying metastore and applying dynamic filtering
- **HivePageSourceProvider**: Creates page sources for reading Hive data with support for column mapping and type coercion
- **HivePageSinkProvider**: Handles data writing operations for INSERT, CREATE TABLE, and MERGE operations

### Hive Metastore Clients
- **ThriftHiveMetastore**: Traditional Hive metastore client using Thrift protocol
- **GlueHiveMetastore**: AWS Glue Data Catalog integration for cloud-native deployments

## Key Features

- **Multi-format Support**: Native support for ORC, Parquet, Avro, TextFile, RCFile, and SequenceFile formats
- **Transaction Management**: Full ACID table support with INSERT, UPDATE, DELETE operations
- **Partition Management**: Dynamic partition pruning, projection, and bulk operations
- **Schema Evolution**: Automatic type coercion and column mapping for evolving schemas
- **Bucketing Support**: Optimized queries on bucketed tables with bucket pruning
- **Statistics Integration**: Automatic statistics collection for cost-based optimization
- **Security Integration**: Role-based access control and privilege management
- **Cloud Storage**: Seamless integration with S3, Azure, and GCS through unified filesystem abstraction

## References to Core Components

- [Hive Connector Lifecycle & Metadata](Hive Connector Core/Hive Connector Lifecycle & Metadata.md) - Detailed documentation of plugin integration, transaction management, and metadata operations
- [Hive Data Access](Hive Connector Core/Hive Data Access.md) - Comprehensive guide to split management, data reading, and writing operations
- [Hive Metastore Clients](Hive Connector Core/Hive Metastore Clients.md) - Documentation for Thrift and Glue metastore implementations
- [Trino SPI](Trino SPI.md) - Service Provider Interface that Hive connector implements
- [Metadata & Connector Abstraction](Metadata & Connector Abstraction.md) - General metadata management framework
- [Filesystem Abstraction Layer](Filesystem Abstraction Layer.md) - Unified filesystem interface for storage access
- [ORC & Parquet Libraries](ORC & Parquet Libraries.md) - Columnar format support libraries
- [Hive Support Libraries](Hive Support Libraries.md) - Metastore and format libraries for Hive-specific operations