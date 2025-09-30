# Transaction Log Applier Module

## Overview

The `txn_log_applier` module is a critical component of StarRocks' lake storage architecture, responsible for applying transaction logs to tablet metadata. It serves as the bridge between transaction logs and the actual data storage, ensuring ACID properties and data consistency in the lake storage format.

## Purpose and Core Functionality

The primary purpose of this module is to:
- Apply transaction logs to tablet metadata in a consistent and atomic manner
- Handle different types of operations (write, compaction, schema change, replication, metadata alteration)
- Support both primary key and non-primary key tables with specialized logic for each
- Ensure data consistency and recoverability in case of failures
- Manage the complex state transitions during transaction application

## Architecture

### Core Components

```mermaid
classDiagram
    class TxnLogApplier {
        <<interface>>
        +apply(log: TxnLogPB): Status
        +apply(logs: TxnLogVector): Status
        +finish(): Status
        +init(): Status
    }
    
    class PrimaryKeyTxnLogApplier {
        -_tablet: Tablet
        -_metadata: MutableTabletMetadataPtr
        -_base_version: int64_t
        -_new_version: int64_t
        -_max_txn_id: int64_t
        -_builder: MetaFileBuilder
        -_index_entry: LakePrimaryIndex*
        -_guard: lock_guard*
        -_has_finalized: bool
        -_rebuild_pindex: bool
        +apply(log: TxnLogPB): Status
        +apply(logs: TxnLogVector): Status
        +finish(): Status
        +init(): Status
    }
    
    class NonPrimaryKeyTxnLogApplier {
        -_tablet: Tablet
        -_metadata: MutableTabletMetadataPtr
        -_new_version: int64_t
        -_skip_write_tablet_metadata: bool
        +apply(log: TxnLogPB): Status
        +apply(logs: TxnLogVector): Status
        +finish(): Status
    }
    
    TxnLogApplier <|-- PrimaryKeyTxnLogApplier
    TxnLogApplier <|-- NonPrimaryKeyTxnLogApplier
```

### Module Dependencies

```mermaid
graph TD
    txn_log_applier[txn_log_applier] --> lake_primary_index[lake_primary_index]
    txn_log_applier --> lake_primary_key_recover[lake_primary_key_recover]
    txn_log_applier --> meta_file[meta_file]
    txn_log_applier --> tablet[tablet]
    txn_log_applier --> tablet_metadata[tablet_metadata]
    txn_log_applier --> update_manager[update_manager]
    txn_log_applier --> lake_tablet_manager[lake_tablet_manager]
    
    lake_primary_index -.-> persistent_index[persistent_index]
    update_manager -.-> persistent_index
    meta_file -.-> protobuf_file[protobuf_file]
    tablet -.-> lake_storage[lake_storage]
```

## Data Flow

### Transaction Log Application Process

```mermaid
sequenceDiagram
    participant Client
    participant TxnLogApplier
    participant Tablet
    participant UpdateManager
    participant MetaFileBuilder
    participant Storage
    
    Client->>TxnLogApplier: new_txn_log_applier()
    TxnLogApplier->>TxnLogApplier: Initialize applier
    Client->>TxnLogApplier: apply(log)
    
    alt Primary Key Table
        TxnLogApplier->>UpdateManager: prepare_primary_index()
        TxnLogApplier->>UpdateManager: lock_shard_pk_index_shard()
        TxnLogApplier->>UpdateManager: publish_primary_key_tablet()
        TxnLogApplier->>UpdateManager: unlock_shard_pk_index_shard()
    else Non-Primary Key Table
        TxnLogApplier->>MetaFileBuilder: Direct metadata update
    end
    
    TxnLogApplier->>MetaFileBuilder: Update metadata
    Client->>TxnLogApplier: finish()
    TxnLogApplier->>MetaFileBuilder: finalize()
    MetaFileBuilder->>Storage: Persist metadata
    TxnLogApplier-->>Client: Status
```

## Operation Types

### 1. Write Operations (op_write)

**Primary Key Tables:**
- Apply rowset data with delete vectors
- Update primary index for upserts and deletes
- Handle column-mode partial updates
- Maintain delete vector consistency

**Non-Primary Key Tables:**
- Simple rowset addition to metadata
- No index updates required
- Support for delete predicates

### 2. Compaction Operations (op_compaction)

**Primary Key Tables:**
- Apply compaction to primary index
- Handle SSTable compaction in cloud-native format
- Maintain index consistency during compaction

**Non-Primary Key Tables:**
- Replace input rowsets with output rowset
- Update cumulative compaction point
- Handle schema evolution during compaction

### 3. Schema Change Operations (op_schema_change)

```mermaid
flowchart LR
    A[Schema Change Start] --> B{Base Version = 1?}
    B -->|Yes| C[Clear Existing Rowsets]
    B -->|No| D[Apply Schema Change]
    C --> D
    D --> E[Add New Rowsets]
    E --> F[Update Delete Vector Meta]
    F --> G[Save Base Metadata]
```

### 4. Metadata Alteration (op_alter_metadata)

Supports:
- **Persistent Index Configuration**: Enable/disable persistent index, change index type
- **Schema Updates**: Handle tablet schema changes with historical schema tracking
- **Compaction Strategy**: Update compaction strategy for the tablet

### 5. Replication Operations (op_replication)

**Incremental Replication:**
- Apply write operations from source
- Maintain version consistency

**Full Replication:**
- Replace all existing rowsets
- Clear delete vector metadata
- Update source schema information

## Error Handling and Recovery

### Primary Key Recovery Mechanism

```mermaid
flowchart TD
    A[Operation Failed] --> B{Need Recovery?}
    B -->|Yes| C{Recovery Type?}
    B -->|No| Z[Return Error]
    
    C -->|RECOVER_WITH_PUBLISH| D[Rebuild Index]
    C -->|Other| E[Rebuild DelVec]
    
    D --> F[Re-publish Operation]
    E --> G[Skip Re-publish]
    
    F --> H[Return Status]
    G --> H
```

### Recovery Process:
1. **Index Rebuilding**: Rebuild primary index from scratch
2. **Delete Vector Recovery**: Rebuild delete vectors from transaction logs
3. **Re-publication**: Re-apply operations after recovery
4. **Resource Cleanup**: Remove failed index entries from cache

## Memory Management

### Primary Key Index Cache Management
- **Cache Entry Management**: Dynamic cache for primary indexes
- **Memory Tracking**: Strict memory limit checking for PK operations
- **Resource Cleanup**: Automatic cleanup of failed operations
- **Shard-level Locking**: Prevent GC during critical operations

### Memory Safety Features:
- Scoped memory limit checking
- Thread-local memory trackers
- Automatic resource cleanup on failure
- Guard-based locking mechanisms

## Batch Operations

### Batch Transaction Log Application

**Primary Key Tables:**
- Support only op_write operations in batch mode
- Lock shard for entire batch duration
- Prepare primary index once for the batch
- Apply operations sequentially with consistency checks

**Non-Primary Key Tables:**
- Merge multiple rowsets into single rowset
- Accumulate segment information across logs
- Support encryption metadata preservation
- Handle schema mapping for historical schemas

## Version Management

### Version Consistency
- **Base Version**: Starting version for the transaction
- **New Version**: Target version after application
- **Transaction ID Tracking**: Maximum transaction ID for file naming
- **Version Validation**: Ensure version compatibility across operations

### Schema Versioning
- **Historical Schema Tracking**: Maintain schema evolution history
- **Rowset-to-Schema Mapping**: Track which schema each rowset uses
- **Schema ID Management**: Unique identifiers for schema versions

## Integration Points

### Related Modules
- **[lake_storage](lake_storage.md)**: Core lake storage functionality
- **[persistent_index](persistent_index.md)**: Primary index management
- **[update_manager](update_manager.md)**: Update operation coordination
- **[meta_file](meta_file.md)**: Metadata file operations
- **[tablet_manager](tablet_manager.md)**: Tablet lifecycle management

### External Dependencies
- **Protobuf**: Transaction log serialization
- **Google Libraries**: String utilities and containers
- **Threading**: Memory tracking and synchronization
- **File System**: Metadata persistence

## Performance Considerations

### Optimization Strategies
1. **Index Caching**: Reuse primary index entries across operations
2. **Batch Processing**: Minimize lock contention with batch operations
3. **Memory Pooling**: Reduce allocation overhead with object pools
4. **Early Validation**: Check versions and metadata before expensive operations

### Monitoring and Metrics
- Operation latency tracking
- Memory usage monitoring
- Recovery frequency metrics
- Cache hit/miss ratios

## Configuration

### Key Configuration Parameters
- `enable_pk_strict_memcheck`: Enable strict memory checking for PK operations
- `enable_primary_key_recover`: Enable automatic recovery for PK failures
- `lake_enable_alter_struct`: Enable struct column alteration (testing feature)
- `enable_size_tiered_compaction_strategy`: Use size-tiered compaction

## Best Practices

### Usage Guidelines
1. **Error Handling**: Always check return status from apply operations
2. **Resource Management**: Use RAII patterns for automatic cleanup
3. **Version Validation**: Validate version compatibility before operations
4. **Memory Monitoring**: Monitor memory usage during large operations
5. **Recovery Planning**: Plan for recovery scenarios in production

### Common Pitfalls
- Forgetting to call `finish()` after apply operations
- Not handling recovery scenarios properly
- Ignoring memory limits during large transactions
- Inadequate error handling for batch operations

## Future Enhancements

### Planned Improvements
- Enhanced recovery mechanisms for complex failure scenarios
- Improved batch operation performance
- Better memory management for large transactions
- Extended support for new operation types
- Enhanced monitoring and observability features