# Blob Storage Module

## Introduction

The blob_storage module provides Azure Blob Storage integration for the GraphRAG pipeline system. It implements the `PipelineStorage` protocol to enable cloud-based storage of graph data, documents, and intermediate processing results. This module serves as a scalable, distributed storage backend that can handle large-scale graph data processing workflows.

## Architecture

### Core Component

The module centers around the `BlobPipelineStorage` class, which implements the `PipelineStorage` protocol to provide Azure Blob Storage capabilities.

```mermaid
classDiagram
    class PipelineStorage {
        <<interface>>
        +get(key, as_bytes, encoding)
        +set(key, value, encoding)
        +has(key)
        +delete(key)
        +clear()
        +child(name)
        +keys()
        +find(file_pattern, base_dir, file_filter, max_count)
        +get_creation_date(key)
    }
    
    class BlobPipelineStorage {
        -_connection_string: str
        -_container_name: str
        -_path_prefix: str
        -_encoding: str
        -_storage_account_blob_url: str
        -_blob_service_client: BlobServiceClient
        +__init__(**kwargs)
        +_create_container()
        +_delete_container()
        +_container_exists()
        +find(file_pattern, base_dir, file_filter, max_count)
        +get(key, as_bytes, encoding)
        +set(key, value, encoding)
        +_set_df_json(key, dataframe)
        +_set_df_parquet(key, dataframe)
        +has(key)
        +delete(key)
        +clear()
        +child(name)
        +keys()
        +_keyname(key)
        +_abfs_url(key)
        +get_creation_date(key)
    }
    
    class BlobServiceClient {
        +from_connection_string(conn_str)
        +get_container_client(container_name)
        +list_containers()
        +create_container(container_name)
        +delete_container(container_name)
    }
    
    class DefaultAzureCredential {
        +get_token()
    }
    
    PipelineStorage <|-- BlobPipelineStorage
    BlobPipelineStorage --> BlobServiceClient
    BlobPipelineStorage ..> DefaultAzureCredential
```

### Module Dependencies

```mermaid
graph TD
    BS[Blob Storage Module]
    PS[Pipeline Storage Protocol]
    AZ[Azure SDK]
    
    BS --> PS
    BS --> AZ
    
    PS --> |implements| BS
    AZ --> |uses| BS
    
    style BS fill:#f9f,stroke:#333,stroke-width:4px
```

## Component Details

### BlobPipelineStorage

The `BlobPipelineStorage` class is the primary implementation that provides Azure Blob Storage functionality for the GraphRAG pipeline. It handles:

- **Authentication**: Supports both connection string and Azure AD authentication via `DefaultAzureCredential`
- **Container Management**: Automatic container creation and lifecycle management
- **Data Operations**: Read/write operations for text and binary data
- **Pattern Matching**: Advanced file pattern matching and filtering capabilities
- **DataFrame Integration**: Direct integration with pandas DataFrames for JSON and Parquet formats

#### Key Features

1. **Flexible Authentication**
   - Connection string authentication for development scenarios
   - Azure AD authentication via `DefaultAzureCredential` for production

2. **Container Management**
   - Automatic container creation if it doesn't exist
   - Container existence validation
   - Container deletion capabilities

3. **Advanced File Operations**
   - Pattern-based file discovery with regex support
   - Custom filtering based on metadata
   - Batch processing with configurable limits

4. **Data Format Support**
   - Text data with configurable encoding (default UTF-8)
   - Binary data handling
   - Direct DataFrame operations for JSON and Parquet formats

## Data Flow

```mermaid
sequenceDiagram
    participant Client
    participant BlobPipelineStorage
    participant BlobServiceClient
    participant AzureStorage
    
    Client->>BlobPipelineStorage: Initialize with config
    BlobPipelineStorage->>BlobServiceClient: Create client
    BlobPipelineStorage->>AzureStorage: Check container exists
    alt Container doesn't exist
        BlobPipelineStorage->>AzureStorage: Create container
    end
    
    Client->>BlobPipelineStorage: set(key, value)
    BlobPipelineStorage->>AzureStorage: Upload blob
    AzureStorage-->>BlobPipelineStorage: Upload complete
    BlobPipelineStorage-->>Client: Success
    
    Client->>BlobPipelineStorage: get(key)
    BlobPipelineStorage->>AzureStorage: Download blob
    AzureStorage-->>BlobPipelineStorage: Blob data
    BlobPipelineStorage-->>Client: Return data
```

## Configuration

The blob storage module integrates with the [configuration module](configuration.md) through the `StorageConfig` model. Key configuration parameters include:

- `connection_string`: Azure Storage connection string (optional)
- `storage_account_blob_url`: Storage account URL (optional)
- `container_name`: Target container name (required)
- `base_dir`: Base directory/prefix for blob paths (optional)
- `encoding`: Text encoding for string operations (default: utf-8)

## Usage Patterns

### Basic Operations

```python
# Initialize storage
storage = BlobPipelineStorage(
    container_name="graphrag-data",
    storage_account_blob_url="https://mystorageaccount.blob.core.windows.net"
)

# Store data
await storage.set("documents/doc1.txt", "Document content")

# Retrieve data
content = await storage.get("documents/doc1.txt")

# Check existence
exists = await storage.has("documents/doc1.txt")
```

### Pattern-based Discovery

```python
# Find all JSON files
pattern = re.compile(r".*\.json$")
async for blob_name, metadata in storage.find(pattern):
    print(f"Found: {blob_name}")

# Find with filtering
pattern = re.compile(r"(?P<type>\w+)_(?P<date>\d{8})\.json$")
filter_dict = {"type": "entity"}
async for blob_name, metadata in storage.find(pattern, file_filter=filter_dict):
    print(f"Entity file: {blob_name}, Date: {metadata['date']}")
```

### DataFrame Operations

```python
# Store DataFrame as JSON
storage._set_df_json("output/entities.json", df_entities)

# Store DataFrame as Parquet
storage._set_df_parquet("output/relationships.parquet", df_relationships)
```

## Integration with Pipeline System

```mermaid
graph LR
    subgraph "GraphRAG Pipeline"
        P[Pipeline]
        PSC[PipelineStorage]
    end
    
    subgraph "Storage Factory"
        SF[StorageFactory]
    end
    
    subgraph "Blob Storage"
        BS[BlobPipelineStorage]
        AZ[Azure Blob Service]
    end
    
    P --> |uses| PSC
    PSC --> |implemented by| BS
    SF --> |creates| BS
    BS --> |stores in| AZ
    
    style BS fill:#f9f,stroke:#333,stroke-width:4px
```

The blob storage module integrates with the [storage factory](storage_factory.md) to provide seamless storage backend selection based on configuration. It works alongside other storage implementations:

- [File Storage](file_storage.md): Local file system storage
- [Memory Storage](memory_storage.md): In-memory storage for testing
- [CosmosDB Storage](cosmosdb_storage.md): NoSQL database storage

## Error Handling

The module implements comprehensive error handling:

- **Validation**: Container name validation according to Azure naming rules
- **Graceful Degradation**: Returns `None` for missing keys instead of raising exceptions
- **Logging**: Detailed logging for debugging and monitoring
- **Exception Handling**: Catches and logs Azure SDK exceptions

## Performance Considerations

1. **Batch Operations**: The `find` method supports batch processing with `max_count` parameter
2. **Lazy Loading**: Iterator-based file discovery to handle large datasets efficiently
3. **Connection Pooling**: Reuses `BlobServiceClient` for optimal performance
4. **Direct DataFrame Operations**: Bypasses intermediate serialization for better performance

## Security

- **Authentication**: Supports Azure AD authentication for production environments
- **Credential Management**: Uses `DefaultAzureCredential` for secure credential handling
- **Network Security**: Leverages Azure Storage's built-in network security features

## Container Naming Validation

The module includes a `validate_blob_container_name` function that enforces Azure container naming rules:

- 3-63 characters in length
- Starts with letter or number
- Lowercase letters only
- Letters, numbers, and hyphens only
- No consecutive hyphens
- Cannot end with hyphen

This ensures compatibility with Azure Blob Storage naming conventions and prevents runtime errors.