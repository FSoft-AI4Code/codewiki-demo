# Storage Layer Module

## Introduction

The storage layer module provides the persistence infrastructure for Rasa's graph-based architecture. It serves as the backbone for model storage, resource management, and model packaging, enabling the Rasa engine to persist and retrieve trained components, models, and their metadata throughout the ML lifecycle.

This module is critical for:
- **Model Persistence**: Storing trained graph components and their states
- **Resource Management**: Managing the lifecycle of persisted resources
- **Model Packaging**: Creating deployable model archives
- **Version Compatibility**: Ensuring model compatibility across Rasa versions
- **Caching Support**: Enabling efficient resource caching and retrieval

## Architecture

### Core Components

```mermaid
graph TB
    subgraph "Storage Layer Architecture"
        MS[ModelStorage<br/><i>Abstract Base Class</i>]
        MM[ModelMetadata<br/><i>Data Class</i>]
        R[Resource<br/><i>Value Object</i>]
        
        MS --> |"manages"| R
        MS --> |"creates"| MM
        MM --> |"describes"| MS
        
        subgraph "ModelStorage Implementations"
            MSI1[FileSystemModelStorage]
            MSI2[MemoryModelStorage]
            MSI3[CloudModelStorage]
        end
        
        MS -.->|"implemented by"| MSI1
        MS -.->|"implemented by"| MSI2
        MS -.->|"implemented by"| MSI3
    end
    
    subgraph "External Dependencies"
        GS[GraphSchema]
        GMC[GraphModelConfiguration]
        D[Domain]
        TS[TrainingType]
    end
    
    MM --> |"contains"| GS
    MM --> |"references"| GMC
    MM --> |"includes"| D
    MM --> |"specifies"| TS
```

### Component Relationships

```mermaid
graph LR
    subgraph "Storage Layer Components"
        MS[ModelStorage]
        MM[ModelMetadata]
        R[Resource]
    end
    
    subgraph "Graph Engine Components"
        GC[GraphComponent]
        GN[GraphNode]
        GS[GraphSchema]
        GMC[GraphModelConfiguration]
    end
    
    subgraph "Core Components"
        D[Domain]
        TS[TrainingType]
    end
    
    MS --> |"persists data for"| GC
    MS --> |"manages resources for"| GN
    MS --> |"creates packages with"| GMC
    
    MM --> |"describes model with"| GS
    MM --> |"includes"| D
    MM --> |"specifies training type"| TS
    
    R --> |"identified by"| GC
    R --> |"fingerprinted by"| GN
```

## Data Flow

### Model Storage Lifecycle

```mermaid
sequenceDiagram
    participant GE as GraphEngine
    participant MS as ModelStorage
    participant R as Resource
    participant MM as ModelMetadata
    participant FS as FileSystem
    
    GE->>MS: create(storage_path)
    MS->>FS: initialize storage directory
    MS-->>GE: ModelStorage instance
    
    GE->>MS: write_to(resource)
    MS->>R: validate resource
    MS->>FS: create resource directory
    MS-->>GE: Path for writing
    GE->>MS: write data to path
    MS-->>GE: resource persisted
    
    GE->>MS: read_from(resource)
    MS->>R: locate resource
    MS->>FS: access resource directory
    MS-->>GE: Path for reading
    
    GE->>MS: create_model_package(config, domain)
    MS->>MM: create metadata
    MS->>FS: package all resources
    MS-->>GE: ModelMetadata
```

### Resource Management Flow

```mermaid
graph TD
    A[Graph Component Execution] --> B{Need Persistence?}
    B -->|Yes| C[Create Resource]
    B -->|No| Z[Continue Execution]
    
    C --> D[Generate Fingerprint]
    D --> E[Write to ModelStorage]
    E --> F[Persist Data to Disk]
    F --> G[Resource Available]
    
    H[Dependent Component] --> I[Request Resource]
    I --> J[Read from ModelStorage]
    J --> K[Access Persisted Data]
    K --> L[Load Component State]
    L --> M[Continue Execution]
```

## Core Components

### ModelStorage

The `ModelStorage` abstract base class defines the contract for all storage implementations. It provides a unified interface for persisting and retrieving graph component data throughout the Rasa engine lifecycle.

**Key Responsibilities:**
- **Resource Persistence**: Provides context managers for reading and writing component data
- **Model Packaging**: Creates deployable model archives with all necessary resources
- **Version Management**: Handles model version compatibility checks
- **Storage Initialization**: Creates storage instances from scratch or model archives

**Core Methods:**
- `create()`: Initializes a new storage instance
- `from_model_archive()`: Loads storage from an existing model package
- `write_to()`: Provides write access for persisting resources
- `read_from()`: Provides read access to persisted resources
- `create_model_package()`: Creates a complete model archive

### ModelMetadata

The `ModelMetadata` data class encapsulates all metadata about a trained model, providing essential information for model loading, validation, and deployment.

**Key Attributes:**
- **Model Identification**: `model_id`, `assistant_id`, `trained_at`
- **Version Information**: `rasa_open_source_version` for compatibility checking
- **Configuration**: `train_schema`, `predict_schema` for graph execution
- **Domain**: Complete domain specification used for training
- **Training Context**: `language`, `training_type`, `project_fingerprint`

**Validation Features:**
- Automatic version compatibility checking
- Serialization/deserialization support
- Integration with Rasa's version management system

### Resource

The `Resource` class represents individual persisted components within the storage system, providing unique identification and fingerprinting capabilities.

**Key Features:**
- **Unique Identification**: Each resource has a unique name and fingerprint
- **Caching Support**: Integration with caching mechanisms for performance
- **Fingerprinting**: Automatic generation of unique identifiers for resource versions
- **Cache Operations**: `from_cache()` and `to_cache()` methods for cache management

## Integration with Graph Engine

### Storage in Graph Execution

```mermaid
graph TB
    subgraph "Graph Execution Context"
        GN[GraphNode]
        GC[GraphComponent]
        MS[ModelStorage]
        R[Resource]
    end
    
    subgraph "Execution Flow"
        GN --> |"provides context"| GC
        GC --> |"requests persistence"| MS
        MS --> |"manages"| R
        R --> |"identifies"| GC
    end
    
    subgraph "Dependency Injection"
        MS --> |"injected into"| GC
        R --> |"created by"| GC
        MS --> |"stores"| R
    end
```

### Model Packaging Process

```mermaid
graph LR
    subgraph "Model Creation"
        GMC[GraphModelConfiguration]
        D[Domain]
        MS[ModelStorage]
        MM[ModelMetadata]
        MAP[Model Archive]
    end
    
    GMC --> |"provides configuration"| MS
    D --> |"provides domain"| MS
    MS --> |"creates"| MM
    MS --> |"packages into"| MAP
    MM --> |"describes"| MAP
```

## Dependencies

### Internal Dependencies

The storage layer depends on several core Rasa components:

- **[`rasa.engine.graph`](graph_core.md)**: Graph schema and model configuration
- **[`rasa.shared.core.domain`](shared_core.md)**: Domain specification and validation
- **[`rasa.constants`](shared_core.md)**: Version compatibility constants
- **[`rasa.exceptions`](shared_core.md)**: Exception handling for version errors

### External Dependencies

- **`packaging.version`**: Version parsing and comparison
- **`pathlib.Path`**: File system operations
- **`dataclasses`**: Data class functionality for metadata
- **`contextlib`**: Context manager support for resource operations

## Usage Patterns

### Basic Resource Persistence

```python
# Component persisting data
with model_storage.write_to(resource) as resource_directory:
    # Save model files, configurations, etc.
    save_model_files(resource_directory)

# Component reading persisted data
with model_storage.read_from(resource) as resource_directory:
    # Load model files, configurations, etc.
    load_model_files(resource_directory)
```

### Model Package Creation

```python
# Create a complete model package
metadata = model_storage.create_model_package(
    model_archive_path="path/to/model.tar.gz",
    model_configuration=graph_model_configuration,
    domain=domain
)
```

### Model Loading from Archive

```python
# Load storage from existing model
model_storage, metadata = ModelStorage.from_model_archive(
    storage_path="path/to/storage",
    model_archive_path="path/to/model.tar.gz"
)
```

## Error Handling

### Version Compatibility

The storage layer implements strict version checking to ensure model compatibility:

```mermaid
graph TD
    A[Load Model] --> B{Check Version}
    B -->|Compatible| C[Proceed with Loading]
    B -->|Incompatible| D[Raise UnsupportedModelVersionError]
    D --> E[Log Error Details]
    E --> F[Fail Gracefully]
```

### Resource Validation

Resources are validated during read/write operations:

- **Missing Resources**: `ValueError` when accessing non-existent resources
- **Invalid Paths**: Path validation for storage operations
- **Permission Errors**: File system permission handling

## Performance Considerations

### Caching Integration

The storage layer is designed to work seamlessly with caching mechanisms:

- **Resource Fingerprinting**: Unique identifiers prevent unnecessary operations
- **Cache-aware Operations**: `from_cache()` and `to_cache()` methods
- **Directory Comparison**: Efficient cache validation using directory comparison

### Storage Optimization

- **Context Managers**: Efficient resource lifecycle management
- **Lazy Loading**: Resources loaded only when needed
- **Fingerprint-based Invalidation**: Smart cache invalidation strategies

## Extension Points

### Custom Storage Implementations

The abstract `ModelStorage` base class allows for custom implementations:

- **Cloud Storage**: AWS S3, Google Cloud Storage, Azure Blob Storage
- **Database Storage**: SQL-based storage for metadata and small resources
- **Hybrid Storage**: Combination of local and remote storage

### Metadata Extensions

The `ModelMetadata` data class can be extended to include additional fields:

- **Custom Training Metrics**: Performance indicators, validation scores
- **Deployment Information**: Target environments, deployment configurations
- **Audit Trail**: Training history, model lineage information

## Best Practices

### Resource Management

1. **Always use context managers** for resource operations
2. **Validate resource existence** before accessing
3. **Handle version compatibility** gracefully
4. **Implement proper cleanup** in error scenarios

### Model Packaging

1. **Include all necessary resources** in model packages
2. **Validate model metadata** before packaging
3. **Test model loading** from created packages
4. **Document model dependencies** in metadata

### Error Handling

1. **Provide meaningful error messages** for debugging
2. **Log storage operations** for audit trails
3. **Implement retry logic** for transient failures
4. **Validate inputs** before storage operations

## Related Documentation

- **[Graph Core](graph_core.md)**: Graph schema and component execution
- **[Shared Core](shared_core.md)**: Domain and event system
- **[Training Framework](training_framework.md)**: Model training process
- **[Execution Engine](execution_engine.md)**: Graph execution runtime