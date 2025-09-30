# Storage Factory Module

## Introduction

The storage_factory module provides a centralized factory pattern implementation for creating and managing different types of storage backends in the GraphRAG system. It serves as the primary entry point for instantiating various storage implementations, enabling flexible and extensible storage configuration across the entire system.

## Architecture Overview

The StorageFactory module implements a registry-based factory pattern that allows for dynamic registration and instantiation of storage implementations. This design enables the system to support multiple storage backends while maintaining a consistent interface.

```mermaid
graph TB
    subgraph "Storage Factory Architecture"
        SF[StorageFactory]
        
        subgraph "Registry Management"
            REG[_registry: dict]
            REG_METHODS[Registration Methods]
        end
        
        subgraph "Storage Types"
            BLOB[BlobPipelineStorage]
            COSMOS[CosmosDBPipelineStorage]
            FILE[FilePipelineStorage]
            MEMORY[MemoryPipelineStorage]
        end
        
        subgraph "Factory Interface"
            CREATE[create_storage]
            REGISTER[register]
            GET_TYPES[get_storage_types]
            IS_SUPPORTED[is_supported_type]
        end
        
        SF --> REG
        SF --> REG_METHODS
        REG_METHODS --> REGISTER
        
        CREATE --> REG
        GET_TYPES --> REG
        IS_SUPPORTED --> REG
        
        REGISTER --> BLOB
        REGISTER --> COSMOS
        REGISTER --> FILE
        REGISTER --> MEMORY
    end
```

## Core Components

### StorageFactory Class

The `StorageFactory` class is the central component that manages storage implementation registration and instantiation. It provides a clean interface for creating storage instances while maintaining flexibility for custom implementations.

#### Key Features:
- **Registry-based architecture**: Uses a class-level registry to store storage implementations
- **Dynamic registration**: Allows runtime registration of custom storage types
- **Type safety**: Integrates with the system's StorageType enum for consistent type management
- **Extensibility**: Supports custom storage implementations without modifying core code

#### Class Structure:

```mermaid
classDiagram
    class StorageFactory {
        -_registry: dict[str, Callable[..., PipelineStorage]]
        +register(storage_type: str, creator: Callable) void
        +create_storage(storage_type: str, kwargs: dict) PipelineStorage
        +get_storage_types() list[str]
        +is_supported_type(storage_type: str) bool
    }
    
    class PipelineStorage {
        <<interface>>
        +async methods...
    }
    
    class BlobPipelineStorage {
        +__init__(**kwargs)
    }
    
    class CosmosDBPipelineStorage {
        +__init__(**kwargs)
    }
    
    class FilePipelineStorage {
        +__init__(**kwargs)
    }
    
    class MemoryPipelineStorage {
        +__init__(**kwargs)
    }
    
    StorageFactory ..> PipelineStorage : creates
    PipelineStorage <|-- BlobPipelineStorage
    PipelineStorage <|-- CosmosDBPipelineStorage
    PipelineStorage <|-- FilePipelineStorage
    PipelineStorage <|-- MemoryPipelineStorage
```

## Storage Type Integration

The factory integrates with the system's [configuration](configuration.md) module through the `StorageType` enum, ensuring consistent storage type definitions across the entire system.

```mermaid
graph LR
    subgraph "Configuration Integration"
        CONFIG[GraphRagConfig]
        STORAGE_CONFIG[StorageConfig]
        STORAGE_TYPE[StorageType enum]
    end
    
    subgraph "Factory Registration"
        FACTORY[StorageFactory]
        REGISTRY[_registry]
    end
    
    subgraph "Storage Implementations"
        BLOB[BlobPipelineStorage]
        COSMOS[CosmosDBPipelineStorage]
        FILE[FilePipelineStorage]
        MEMORY[MemoryPipelineStorage]
    end
    
    CONFIG --> STORAGE_CONFIG
    STORAGE_CONFIG --> STORAGE_TYPE
    STORAGE_TYPE --> FACTORY
    FACTORY --> REGISTRY
    REGISTRY --> BLOB
    REGISTRY --> COSMOS
    REGISTRY --> FILE
    REGISTRY --> MEMORY
```

## Data Flow

The storage factory follows a clear data flow pattern for storage instantiation:

```mermaid
sequenceDiagram
    participant Client
    participant StorageFactory
    participant Registry
    participant StorageImpl
    
    Client->>StorageFactory: create_storage(type, kwargs)
    StorageFactory->>Registry: lookup storage_type
    alt storage_type exists
        Registry-->>StorageFactory: creator function
        StorageFactory->>StorageImpl: creator(**kwargs)
        StorageImpl-->>StorageFactory: storage instance
        StorageFactory-->>Client: PipelineStorage
    else storage_type not found
        Registry-->>StorageFactory: None
        StorageFactory-->>Client: ValueError
    end
```

## Built-in Storage Types

The factory comes pre-configured with four built-in storage implementations:

### 1. File Storage ([file_storage](file_storage.md))
- **Type**: `StorageType.file`
- **Implementation**: `FilePipelineStorage`
- **Use Case**: Local file system storage for development and small deployments

### 2. Blob Storage ([blob_storage](blob_storage.md))
- **Type**: `StorageType.blob`
- **Implementation**: `BlobPipelineStorage`
- **Use Case**: Cloud blob storage for scalable deployments

### 3. Memory Storage ([memory_storage](memory_storage.md))
- **Type**: `StorageType.memory`
- **Implementation**: `MemoryPipelineStorage`
- **Use Case**: In-memory storage for testing and temporary operations

### 4. CosmosDB Storage ([cosmosdb_storage](cosmosdb_storage.md))
- **Type**: `StorageType.cosmosdb`
- **Implementation**: `CosmosDBPipelineStorage`
- **Use Case**: Distributed NoSQL storage for enterprise deployments

## Custom Storage Implementation

The factory pattern allows for easy extension with custom storage implementations:

```mermaid
graph TB
    subgraph "Custom Storage Registration Process"
        CUSTOM[Custom Storage Class]
        REGISTER[StorageFactory.register]
        REGISTRY[Factory Registry]
        CREATE[create_storage call]
        INSTANCE[Custom Instance]
        
        CUSTOM -->|implements| PIPELINE[PipelineStorage Protocol]
        CUSTOM -->|register| REGISTER
        REGISTER -->|adds to| REGISTRY
        CREATE -->|looks up| REGISTRY
        REGISTRY -->|creates| INSTANCE
    end
```

## Integration with Pipeline System

The storage factory integrates seamlessly with the [pipeline_infrastructure](pipeline_infrastructure.md) module, providing storage instances for various pipeline operations:

```mermaid
graph LR
    subgraph "Pipeline Integration"
        PIPELINE[Pipeline]
        CONTEXT[PipelineRunContext]
        STORAGE_CONFIG[StorageConfig]
    end
    
    subgraph "Storage Factory"
        FACTORY[StorageFactory]
        STORAGE[PipelineStorage Instance]
    end
    
    subgraph "Pipeline Operations"
        EXTRACT[GraphExtractor]
        EMBED[TextEmbedStrategy]
        SUMMARIZE[CommunityReportsExtractor]
    end
    
    PIPELINE --> CONTEXT
    CONTEXT --> STORAGE_CONFIG
    STORAGE_CONFIG --> FACTORY
    FACTORY --> STORAGE
    STORAGE --> EXTRACT
    STORAGE --> EMBED
    STORAGE --> SUMMARIZE
```

## Error Handling

The factory implements robust error handling for unknown storage types:

- **Validation**: Checks if storage type is registered before instantiation
- **Error Reporting**: Provides clear error messages for unsupported types
- **Type Safety**: Integrates with configuration enums to prevent invalid types

## Usage Examples

### Basic Storage Creation
```python
from graphrag.storage.factory import StorageFactory
from graphrag.config.enums import StorageType

# Create file storage
storage = StorageFactory.create_storage(
    StorageType.file.value,
    {"base_dir": "/path/to/storage"}
)
```

### Custom Storage Registration
```python
# Register custom storage implementation
StorageFactory.register("custom", CustomPipelineStorage)

# Use custom storage
custom_storage = StorageFactory.create_storage(
    "custom",
    {"custom_param": "value"}
)
```

## Dependencies

The storage_factory module has the following key dependencies:

- **[configuration](configuration.md)**: Uses `StorageType` enum for consistent type definitions
- **[pipeline_storage](pipeline_storage.md)**: Creates instances implementing the `PipelineStorage` protocol
- **Individual storage implementations**: Delegates to specific storage classes for instantiation

## Best Practices

1. **Type Consistency**: Always use the `StorageType` enum values when creating storage instances
2. **Error Handling**: Handle `ValueError` exceptions when creating storage with potentially unknown types
3. **Custom Extensions**: Register custom storage implementations during application initialization
4. **Configuration Integration**: Use storage configuration from the main system configuration for consistency

## Future Considerations

The factory pattern provides a solid foundation for future enhancements:

- **Async Factory Methods**: Potential addition of async creation methods
- **Storage Health Checks**: Integration with system health monitoring
- **Performance Metrics**: Collection of storage instantiation metrics
- **Auto-discovery**: Potential automatic discovery of storage implementations