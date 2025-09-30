# Memory Storage Module Documentation

## Introduction

The memory storage module provides an in-memory implementation of the pipeline storage interface for the GraphRAG system. This module offers a lightweight, high-performance storage solution that keeps all data in RAM during pipeline execution, making it ideal for testing, development, and scenarios where data persistence is not required.

## Architecture Overview

The memory storage module implements a hierarchical storage pattern where `MemoryPipelineStorage` extends `FilePipelineStorage` to provide in-memory storage capabilities while maintaining compatibility with the broader storage interface.

```mermaid
graph TB
    subgraph "Storage Hierarchy"
        PS[PipelineStorage<br/><i>Abstract Interface</i>]
        FPS[FilePipelineStorage<br/><i>Base Implementation</i>]
        MPS[MemoryPipelineStorage<br/><i>In-Memory Implementation</i>]
        
        PS --> FPS
        FPS --> MPS
    end
    
    subgraph "Memory Storage Components"
        MPS --> Dict["Dict[str, Any]<br/><i>Internal Storage</i>"]
        MPS --> Ops["Storage Operations<br/><i>get, set, has, delete</i>"]
        MPS --> Child["Child Storage<br/><i>Hierarchical Creation</i>"]
    end
    
    style PS fill:#e1f5fe
    style MPS fill:#c8e6c9
    style Dict fill:#fff3e0
```

## Core Components

### MemoryPipelineStorage

The `MemoryPipelineStorage` class is the primary component of this module, providing a complete in-memory implementation of the pipeline storage interface.

**Key Characteristics:**
- **Storage Type**: In-memory dictionary-based storage
- **Persistence**: Non-persistent (data lost on process termination)
- **Performance**: High-speed read/write operations
- **Use Case**: Development, testing, and temporary data processing

**Core Methods:**
- `get(key, as_bytes=None, encoding=None)`: Retrieve values from memory
- `set(key, value, encoding=None)`: Store values in memory
- `has(key)`: Check key existence
- `delete(key)`: Remove specific keys
- `clear()`: Clear all stored data
- `child(name)`: Create hierarchical storage instances
- `keys()`: List all stored keys

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant Client as Storage Client
    participant MPS as MemoryPipelineStorage
    participant Memory as Internal Dict
    
    Client->>MPS: set(key, value)
    MPS->>Memory: _storage[key] = value
    MPS-->>Client: None
    
    Client->>MPS: get(key)
    MPS->>Memory: _storage.get(key)
    Memory-->>MPS: value
    MPS-->>Client: value
    
    Client->>MPS: has(key)
    MPS->>Memory: key in _storage
    Memory-->>MPS: boolean
    MPS-->>Client: boolean
    
    Client->>MPS: delete(key)
    MPS->>Memory: del _storage[key]
    MPS-->>Client: None
```

## Component Interactions

The memory storage module integrates with the broader GraphRAG storage system through the following relationships:

```mermaid
graph LR
    subgraph "Storage Factory System"
        SF[StorageFactory]
        ST[StorageType.MEMORY]
    end
    
    subgraph "Pipeline Execution"
        Pipeline[Pipeline]
        Context[PipelineRunContext]
    end
    
    subgraph "Memory Storage Module"
        MPS[MemoryPipelineStorage]
        Storage[Dict Storage]
    end
    
    SF -->|creates| MPS
    ST -->|configures| MPS
    Pipeline -->|uses| MPS
    Context -->|manages| MPS
    MPS -->|utilizes| Storage
    
    style MPS fill:#c8e6c9
    style SF fill:#e1f5fe
    style Pipeline fill:#f3e5f5
```

## Storage Configuration

The memory storage module is configured through the [storage configuration system](storage_config.md), which defines storage types and their parameters. Memory storage is typically configured with:

- **Storage Type**: `StorageType.MEMORY`
- **Base Path**: Not applicable (in-memory)
- **Connection String**: Not required
- **Container Name**: Not applicable

## Usage Patterns

### 1. Development and Testing
```python
# Ideal for unit tests and development
storage = MemoryPipelineStorage()
await storage.set("test_key", test_data)
result = await storage.get("test_key")
```

### 2. Temporary Data Processing
```python
# Use for intermediate processing steps
temp_storage = MemoryPipelineStorage()
# Process data without disk I/O overhead
```

### 3. Hierarchical Storage
```python
# Create child storage instances
child_storage = parent_storage.child("subdirectory")
# Maintains isolation while sharing memory space
```

## Performance Characteristics

- **Read Operations**: O(1) average case
- **Write Operations**: O(1) average case
- **Memory Usage**: Proportional to stored data size
- **Scalability**: Limited by available system memory
- **Concurrency**: Thread-safe for individual operations

## Integration with Pipeline System

The memory storage module integrates seamlessly with the [pipeline infrastructure](pipeline_infrastructure.md) and [caching system](caching.md):

```mermaid
graph TD
    subgraph "Pipeline Execution Flow"
        Start[Pipeline Start]
        Config[Storage Configuration]
        Factory[StorageFactory]
        Memory[MemoryPipelineStorage]
        Process[Data Processing]
        Cache[PipelineCache]
        End[Pipeline End]
    end
    
    Start --> Config
    Config --> Factory
    Factory --> Memory
    Memory --> Process
    Process --> Cache
    Cache --> End
    
    style Memory fill:#c8e6c9
    style Factory fill:#e1f5fe
    style Cache fill:#fff3e0
```

## Error Handling

The memory storage module handles errors gracefully:

- **Key Not Found**: Returns `None` for `get()` operations
- **Key Existence**: `has()` method provides safe key checking
- **Memory Constraints**: Subject to system memory limitations
- **Type Safety**: Maintains type information for stored values

## Best Practices

1. **Use Cases**: Ideal for development, testing, and temporary data processing
2. **Memory Management**: Monitor memory usage for large datasets
3. **Data Persistence**: Not suitable for production data requiring persistence
4. **Performance**: Leverage for high-speed operations without I/O overhead
5. **Cleanup**: Use `clear()` method to free memory when storage is no longer needed

## Related Modules

- [Storage Configuration](storage_config.md) - Configuration models for storage systems
- [Storage Factory](storage_factory.md) - Factory pattern for storage creation
- [Pipeline Infrastructure](pipeline_infrastructure.md) - Pipeline execution framework
- [File Storage](file_storage.md) - File-based storage implementation
- [Blob Storage](blob_storage.md) - Cloud blob storage implementation

## Dependencies

The memory storage module depends on:
- `graphrag.storage.file_pipeline_storage.FilePipelineStorage` - Base implementation
- `graphrag.storage.pipeline_storage.PipelineStorage` - Interface definition
- Standard Python typing and dictionary operations