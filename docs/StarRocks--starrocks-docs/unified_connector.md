# Unified Connector Module Documentation

## Introduction

The Unified Connector module provides a unified interface for accessing multiple data lake formats through a single connector. It acts as a facade that delegates operations to specific connectors for different table formats like Hive, Iceberg, Hudi, Delta Lake, Kudu, and Paimon. This design simplifies data access by providing a consistent API while supporting multiple storage formats through a unified metastore configuration.

## Architecture Overview

The Unified Connector follows a delegation pattern where it creates and manages multiple specialized connectors internally. Each specialized connector handles operations for its specific table format, while the Unified Connector provides a single point of access for all operations.

```mermaid
graph TB
    subgraph "Unified Connector Architecture"
        UC[UnifiedConnector]
        
        subgraph "Internal Connector Map"
            HC[HiveConnector]
            IC[IcebergConnector]
            HUC[HudiConnector]
            DLC[DeltaLakeConnector]
            KC[KuduConnector]
            PC[PaimonConnector]
        end
        
        subgraph "Metadata Delegation"
            UM[UnifiedMetadata]
            HCM[HiveMetadata]
            ICM[IcebergMetadata]
            HUM[HudiMetadata]
            DLCM[DeltaLakeMetadata]
            KCM[KuduMetadata]
            PCM[PaimonMetadata]
        end
        
        UC -->|creates| HC
        UC -->|creates| IC
        UC -->|creates| HUC
        UC -->|creates| DLC
        UC -->|creates| KC
        UC -->|creates| PC
        
        UC -->|delegates to| UM
        UM -->|delegates to| HCM
        UM -->|delegates to| ICM
        UM -->|delegates to| HUM
        UM -->|delegates to| DLCM
        UM -->|delegates to| KCM
        UM -->|delegates to| PCM
    end
```

## Core Components

### UnifiedConnector

The main entry point that implements the `Connector` interface. It:
- Validates the metastore type configuration (supports "hive" and "glue")
- Creates derived properties for all underlying connectors
- Initializes and manages a map of table type to specific connectors
- Delegates metadata operations to `UnifiedMetadata`
- Handles shutdown and configuration binding for all connectors

#### Key Configuration

- `unified.metastore.type`: Specifies the metastore type ("hive" or "glue")
- Automatically derives catalog type properties for all underlying connectors

#### Supported Table Types

- **HIVE**: Hive tables
- **ICEBERG**: Iceberg tables
- **HUDI**: Hudi tables
- **DELTALAKE**: Delta Lake tables
- **KUDU**: Kudu tables
- **PAIMON**: Paimon tables (optional, enabled when warehouse is configured)

## Data Flow

```mermaid
sequenceDiagram
    participant Client
    participant UnifiedConnector
    participant ConnectorMap
    participant SpecificConnector
    participant UnifiedMetadata
    participant SpecificMetadata
    
    Client->>UnifiedConnector: getMetadata()
    UnifiedConnector->>ConnectorMap: get all connectors
    loop For each connector
        UnifiedConnector->>SpecificConnector: getMetadata()
        SpecificConnector->>SpecificConnector: create metadata
        SpecificConnector-->>UnifiedConnector: return metadata
    end
    UnifiedConnector->>UnifiedMetadata: create with metadata map
    UnifiedConnector-->>Client: return UnifiedMetadata
    
    Client->>UnifiedMetadata: metadata operation
    UnifiedMetadata->>SpecificMetadata: delegate based on table type
    SpecificMetadata-->>UnifiedMetadata: return result
    UnifiedMetadata-->>Client: return result
```

## Component Relationships

```mermaid
classDiagram
    class UnifiedConnector {
        -Map~TableType,Connector~ connectorMap
        +UnifiedConnector(ConnectorContext context)
        +getMetadata() ConnectorMetadata
        +shutdown() void
        +bindConfig(ConnectorConfig config) void
    }
    
    class Connector {
        <<interface>>
        +getMetadata() ConnectorMetadata
        +shutdown() void
        +bindConfig(ConnectorConfig config) void
    }
    
    class ConnectorContext {
        -String catalogName
        -String type
        -Map~String,String~ properties
    }
    
    class ConnectorMetadata {
        <<interface>>
    }
    
    class HiveConnector {
    }
    
    class IcebergConnector {
    }
    
    class HudiConnector {
    }
    
    class DeltaLakeConnector {
    }
    
    class KuduConnector {
    }
    
    class PaimonConnector {
    }
    
    class UnifiedMetadata {
        -Map~TableType,ConnectorMetadata~ metadataMap
    }
    
    UnifiedConnector ..|> Connector
    UnifiedConnector --> ConnectorContext : uses
    UnifiedConnector --> HiveConnector : creates
    UnifiedConnector --> IcebergConnector : creates
    UnifiedConnector --> HudiConnector : creates
    UnifiedConnector --> DeltaLakeConnector : creates
    UnifiedConnector --> KuduConnector : creates
    UnifiedConnector --> PaimonConnector : creates
    UnifiedConnector --> UnifiedMetadata : creates
    UnifiedMetadata --> ConnectorMetadata : delegates to
    HiveConnector ..|> Connector
    IcebergConnector ..|> Connector
    HudiConnector ..|> Connector
    DeltaLakeConnector ..|> Connector
    KuduConnector ..|> Connector
    PaimonConnector ..|> Connector
```

## Process Flow

### Initialization Process

```mermaid
flowchart TD
    Start[Start UnifiedConnector Initialization]
    Validate[Validate metastore type]
    CreateProps[Create derived properties]
    CreateContext[Create derived context]
    InitializeConnectors[Initialize connector map]
    
    Start --> Validate
    Validate -->|Valid| CreateProps
    Validate -->|Invalid| Error[Throw SemanticException]
    
    CreateProps --> CreateContext
    CreateContext --> InitializeConnectors
    InitializeConnectors --> End[Initialization Complete]
    Error --> End
    
    subgraph "Connector Initialization"
        Hive[Create HiveConnector]
        Iceberg[Create IcebergConnector]
        Hudi[Create HudiConnector]
        Delta[Create DeltaLakeConnector]
        Kudu[Create KuduConnector]
        Paimon[Create PaimonConnector - optional]
    end
    
    InitializeConnectors --> Hive
    InitializeConnectors --> Iceberg
    InitializeConnectors --> Hudi
    InitializeConnectors --> Delta
    InitializeConnectors --> Kudu
    InitializeConnectors --> Paimon
```

### Metadata Operation Flow

```mermaid
flowchart LR
    Request[Client Request] --> UnifiedConnector
    UnifiedConnector --> UnifiedMetadata
    
    subgraph "Table Type Routing"
        direction TB
        CheckType{Determine Table Type}
        HiveOp[Route to Hive Metadata]
        IcebergOp[Route to Iceberg Metadata]
        HudiOp[Route to Hudi Metadata]
        DeltaOp[Route to Delta Lake Metadata]
        KuduOp[Route to Kudu Metadata]
        PaimonOp[Route to Paimon Metadata]
        
        CheckType --> HiveOp
        CheckType --> IcebergOp
        CheckType --> HudiOp
        CheckType --> DeltaOp
        CheckType --> KuduOp
        CheckType --> PaimonOp
    end
    
    UnifiedMetadata --> CheckType
    HiveOp --> Result[Return Result]
    IcebergOp --> Result
    HudiOp --> Result
    DeltaOp --> Result
    KuduOp --> Result
    PaimonOp --> Result
```

## Integration with Other Modules

### Dependencies

The Unified Connector depends on several other modules:

- **[Connector Framework](connector_framework.md)**: Provides the base `Connector` interface and `ConnectorContext`
- **[Hive Connector](hive_connector.md)**: Handles Hive table operations
- **[Iceberg Connector](iceberg_connector.md)**: Handles Iceberg table operations
- **[Hudi Connector](hudi_connector.md)**: Handles Hudi table operations
- **[Delta Lake Connector](delta_lake_connector.md)**: Handles Delta Lake table operations
- **[Kudu Connector](kudu_connector.md)**: Handles Kudu table operations
- **[Paimon Connector](paimon_connector.md)**: Handles Paimon table operations

### Configuration Integration

The module integrates with the configuration system by:
- Validating metastore type configuration
- Deriving properties for all underlying connectors
- Supporting dynamic configuration binding through `bindConfig()`

## Error Handling

The Unified Connector implements several error handling mechanisms:

1. **Configuration Validation**: Throws `SemanticException` for invalid metastore types
2. **Connector Initialization**: Each connector handles its own initialization errors
3. **Metadata Delegation**: Errors from specific connectors are propagated through the unified interface

## Performance Considerations

- **Lazy Initialization**: Connectors are created during UnifiedConnector initialization
- **Metadata Caching**: Each connector manages its own metadata caching
- **Resource Management**: Proper shutdown sequence ensures all resources are released

## Extension Points

The module can be extended by:
- Adding new table type support in the connector map
- Implementing new specialized connectors
- Extending the UnifiedMetadata to support new operations

## Usage Examples

### Basic Configuration

```properties
# Catalog configuration
catalog.name = unified_catalog
catalog.type = unified
unified.metastore.type = hive
```

### Supported Operations

The Unified Connector supports all operations provided by the underlying connectors:
- Table metadata operations
- Partition management
- Data scanning
- Predicate pushdown
- Statistics collection

## Future Enhancements

Potential improvements include:
- Support for additional metastore types
- Dynamic connector loading
- Enhanced error reporting with connector-specific details
- Performance optimizations for multi-format queries