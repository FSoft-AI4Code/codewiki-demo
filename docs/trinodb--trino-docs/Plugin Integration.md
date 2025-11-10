# Plugin Integration Module Documentation

## Introduction

The Plugin Integration module serves as the foundation for Trino's extensible architecture, providing the core interfaces and mechanisms that enable third-party developers to create custom connectors, functions, and system components. This module defines the Service Provider Interface (SPI) that all Trino plugins must implement, establishing a standardized contract between the Trino engine and external plugin implementations.

The module's primary purpose is to abstract the complexity of Trino's internal operations while providing a clean, stable API for plugin development. It enables seamless integration of new data sources, custom functions, security providers, and other system extensions without requiring modifications to the core Trino engine.

### Core Example: IcebergPlugin Implementation

The `IcebergPlugin` serves as a prime example of plugin implementation, demonstrating the key integration patterns:

```java
public class IcebergPlugin implements Plugin {
    @Override
    public Iterable<ConnectorFactory> getConnectorFactories() {
        return ImmutableList.of(new IcebergConnectorFactory());
    }
    
    @Override
    public Set<Class<?>> getFunctions() {
        return ImmutableSet.of(IcebergThetaSketchForStats.class);
    }
}
```

This implementation showcases the two primary extension points: connector factories for data source integration and function registration for custom SQL functions.

## Architecture Overview

The Plugin Integration architecture is built around several key design principles:

1. **Service Provider Interface Pattern**: Defines clear contracts between Trino and plugins
2. **Modular Component Design**: Separates concerns into distinct, reusable components
3. **Type Safety**: Provides strong typing throughout the plugin ecosystem
4. **Extensibility**: Allows plugins to extend functionality at multiple integration points

### Core Plugin Architecture

```mermaid
graph TB
    subgraph "Trino Engine Core"
        PM[PluginManager]
        CM[ConnectorManager]
        FM[FunctionManager]
        MM[MetadataManager]
    end
    
    subgraph "Plugin SPI"
        PI[Plugin Interface]
        CF[ConnectorFactory]
        MF[MetadataFactory]
        SF[SplitManager]
        PSP[PageSourceProvider]
        PSP2[PageSinkProvider]
    end
    
    subgraph "Plugin Implementations"
        IP[IcebergPlugin]
        HP[HivePlugin]
        KP[KafkaPlugin]
        TP[TpchPlugin]
    end
    
    subgraph "Connector Instances"
        IC[IcebergConnector]
        HC[HiveConnector]
        KC[KafkaConnector]
        TC[TpchConnector]
    end
    
    PM --> PI
    PI --> CF
    CF --> IP
    CF --> HP
    CF --> KP
    CF --> TP
    
    IP --> IC
    HP --> HC
    KP --> KC
    TP --> TC
    
    CM --> IC
    CM --> HC
    CM --> KC
    CM --> TC
    
    FM --> PI
    MM --> IC
    MM --> HC
    MM --> KC
    MM --> TC
```

### Plugin Lifecycle Management

```mermaid
sequenceDiagram
    participant Server as TrinoServer
    participant PM as PluginManager
    participant Plugin as Plugin Implementation
    participant CM as ConnectorManager
    participant Catalog as Catalog System
    
    Server->>PM: Initialize PluginManager
    PM->>PM: Scan plugin directories
    PM->>Plugin: Load plugin JAR
    Plugin->>Plugin: Create Plugin instance
    Plugin->>PM: Return Plugin object
    PM->>Plugin: getConnectorFactories()
    Plugin->>PM: Return ConnectorFactory list
    PM->>CM: Register ConnectorFactories
    
    Note over Server,Catalog: Runtime Phase
    
    Catalog->>CM: Create catalog with connector
    CM->>Plugin: Create connector instance
    Plugin->>CM: Return connector
    CM->>Catalog: Register connector
    Catalog->>Server: Catalog ready
```

```mermaid
graph TB
    subgraph "Trino Engine"
        TE[Trino Engine Core]
        PM[Plugin Manager]
        CM[Connector Manager]
        FM[Function Manager]
    end
    
    subgraph "Plugin SPI"
        PI[Plugin Interface]
        CF[Connector Factory]
        TP[Type System]
        SF[Security Framework]
        PF[Procedure Framework]
    end
    
    subgraph "Plugin Implementations"
        HP[Hive Plugin]
        IP[Iceberg Plugin]
        KP[Kafka Plugin]
        DJ[Database Connectors]
    end
    
    TE --> PM
    PM --> PI
    PI --> CF
    PI --> TP
    PI --> SF
    PI --> PF
    
    CF --> HP
    CF --> IP
    CF --> KP
    CF --> DJ
    
    CM --> CF
    FM --> PI
```

## Core Components

### Plugin Interface

The `Plugin` interface is the entry point for all Trino plugins. It serves as the primary contract that plugin implementations must fulfill to be recognized by the Trino system.

**Key Responsibilities:**
- Provide connector factories for creating connector instances
- Register custom functions and procedures
- Define plugin-specific types and security providers
- Manage plugin lifecycle and resources

**Implementation Example - IcebergPlugin (from core code):**

```java
public class IcebergPlugin implements Plugin {
    @Override
    public Iterable<ConnectorFactory> getConnectorFactories() {
        return ImmutableList.of(new IcebergConnectorFactory());
    }
    
    @Override
    public Set<Class<?>> getFunctions() {
        return ImmutableSet.of(IcebergThetaSketchForStats.class);
    }
}
```

This implementation demonstrates the two primary extension points: connector factories for data source integration and function registration for custom SQL functions.

### Connector Framework

The Connector Framework provides the infrastructure for building data source connectors, abstracting the complexity of data access patterns and query execution.

**Key Interfaces:**
- `ConnectorFactory`: Creates connector instances
- `ConnectorMetadata`: Handles metadata operations (tables, schemas, columns)
- `ConnectorSplitManager`: Manages data partitioning and split generation
- `ConnectorPageSourceProvider`: Provides data reading capabilities
- `ConnectorPageSinkProvider`: Handles data writing operations

### Type System

The Type System defines how data types are represented and handled across the Trino ecosystem, ensuring consistency between the engine and plugins.

**Core Type Components:**
- `Type`: Base interface for all data types
- `Block`: Columnar data storage format
- `Page`: Collection of blocks representing a set of rows
- `ColumnMetadata`: Schema information for columns

### Security Framework

The Security Framework enables plugins to implement custom authentication and authorization mechanisms.

**Security Components:**
- `ConnectorIdentity`: Represents user identity within connectors
- Access control interfaces for fine-grained permission management
- Authentication providers for custom credential validation

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant Client
    participant TrinoEngine
    participant PluginManager
    participant ConnectorFactory
    participant Connector
    participant DataSource

    Client->>TrinoEngine: Submit Query
    TrinoEngine->>PluginManager: Load Plugin
    PluginManager->>ConnectorFactory: Create Connector
    ConnectorFactory->>Connector: Initialize
    TrinoEngine->>Connector: Request Metadata
    Connector->>DataSource: Fetch Metadata
    DataSource-->>Connector: Return Metadata
    Connector-->>TrinoEngine: Provide Metadata
    TrinoEngine->>Connector: Execute Query
    Connector->>DataSource: Access Data
    DataSource-->>Connector: Return Data
    Connector-->>TrinoEngine: Process Results
    TrinoEngine-->>Client: Return Results
```

## Component Interactions

### Plugin Discovery and Loading

```mermaid
graph LR
    subgraph "Plugin Discovery"
        JAR[Plugin JAR]
        SPI[ServiceLoader]
        PI[Plugin Interface]
    end
    
    subgraph "Plugin Registration"
        PM[Plugin Manager]
        CF[Connector Factory]
        FM[Function Manager]
        TM[Type Manager]
    end
    
    subgraph "Runtime Usage"
        CM[Connector Manager]
        QE[Query Execution]
        MD[Metadata Operations]
    end
    
    JAR --> SPI
    SPI --> PI
    PI --> PM
    PM --> CF
    PM --> FM
    PM --> TM
    CF --> CM
    CM --> QE
    CM --> MD
```

### Query Execution Flow with Plugins

```mermaid
graph TD
    subgraph "Query Planning"
        QP[Query Parser]
        QA[Query Analyzer]
        QO[Query Optimizer]
    end
    
    subgraph "Plugin Integration"
        CM[Connector Metadata]
        SM[Split Manager]
        PE[Plan Execution]
    end
    
    subgraph "Data Access"
        PSP[Page Source Provider]
        PS[Page Sink]
        DA[Data Access]
    end
    
    QP --> QA
    QA --> CM
    CM --> QA
    QA --> QO
    QO --> SM
    SM --> PE
    PE --> PSP
    PSP --> DA
    PE --> PS
    PS --> DA
```

## Plugin Types and Categories

### Data Source Connectors

Data source connectors enable Trino to query external data systems. Each connector is implemented as a plugin that provides the necessary components for data access, metadata management, and query execution.

| Connector Type | Plugin Implementation | Data Source | Key Features |
|----------------|----------------------|-------------|--------------|
| **Iceberg** | IcebergPlugin | Apache Iceberg tables | ACID transactions, time travel, schema evolution, partition evolution |
| **Hive** | HivePlugin | Hive/HDFS ecosystem | Partition pruning, bucket optimization, ORC/Parquet optimization |
| **Delta Lake** | DeltaLakePlugin | Delta Lake tables | ACID transactions, unified batch/streaming, time travel |
| **Kafka** | KafkaPlugin | Apache Kafka | Real-time streaming, schema registry integration, exactly-once semantics |
| **Base JDBC** | BaseJdbcPlugin | JDBC-compatible databases | Standardized SQL access, connection pooling, type mapping |

**Example: IcebergPlugin Integration**

The IcebergPlugin demonstrates advanced connector patterns:

```mermaid
graph TB
    subgraph "IcebergPlugin Components"
        IP[IcebergPlugin]
        ICF[IcebergConnectorFactory]
        IC[IcebergConnector]
        IM[IcebergMetadata]
        ISM[IcebergSplitManager]
        IPP[IcebergPageSourceProvider]
        IPSP[IcebergPageSinkProvider]
    end
    
    subgraph "Iceberg Catalog Integration"
        TC[TrinoCatalog]
        HCF[HiveCatalogFactory]
        GCF[GlueCatalogFactory]
        ICAT[IcebergCatalog]
    end
    
    subgraph "External Systems"
        S3[S3 Storage]
        GLUE[Glue Metastore]
        HMS[Hive Metastore]
    end
    
    IP --> ICF
    ICF --> IC
    IC --> IM
    IC --> ISM
    IC --> IPP
    IC --> IPSP
    
    IM --> TC
    TC --> HCF
    TC --> GCF
    HCF --> HMS
    GCF --> GLUE
    
    IPP --> S3
    IPSP --> S3
```

### Testing and Development Connectors

| Connector | Plugin | Purpose | Characteristics |
|-----------|--------|---------|-----------------|
| **TPC-H** | TpchPlugin | Benchmarking | Standardized test data, performance testing |
| **TPC-DS** | TpcdsPlugin | Decision support testing | Complex queries, analytical workloads |

### Base Infrastructure

| Component | Plugin | Function | Integration Level |
|-----------|--------|----------|-------------------|
| **Base JDBC** | BaseJdbcPlugin | JDBC database abstraction | Foundation for database connectors |

## Integration Points

### 1. Connector Integration

Plugins integrate with Trino through the Connector API, which provides standardized interfaces for:

- **Metadata Management**: Table discovery, schema operations, column information
- **Data Access**: Reading and writing data in the connector's native format
- **Transaction Management**: Supporting ACID properties where applicable
- **Optimization**: Providing statistics and pushdown capabilities

**Example: IcebergPlugin Metadata Integration**

```mermaid
graph TB
    subgraph "Trino Metadata Layer"
        TM[Trino Metadata]
        CM[CatalogManager]
        MM[MetadataManager]
    end
    
    subgraph "IcebergPlugin Metadata"
        IM[IcebergMetadata]
        TC[TrinoCatalog]
        SM[SchemaManagement]
    end
    
    subgraph "External Iceberg Systems"
        IC[Iceberg Catalog]
        HMS[Hive Metastore]
        GLUE[Glue Catalog]
    end
    
    TM --> CM
    CM --> MM
    MM --> IM
    IM --> TC
    TC --> IC
    TC --> HMS
    TC --> GLUE
```

### 2. Function Integration

Custom functions extend Trino's built-in function library through:

- **Scalar Functions**: Single-row, single-value operations
- **Aggregate Functions**: Multi-row aggregation operations
- **Window Functions**: Partition-based analytical operations
- **Table Functions**: Functions that return entire tables

**Example: IcebergPlugin Function Registration**

The IcebergPlugin registers the `IcebergThetaSketchForStats` function, which provides specialized statistical capabilities for Iceberg tables:

```mermaid
graph LR
    subgraph "Function Registration"
        IP[IcebergPlugin]
        GF[Get Functions]
        FM[FunctionManager]
        FR[Function Registry]
    end
    
    subgraph "Custom Functions"
        ITS[IcebergThetaSketchForStats]
        CF[Custom Functions]
    end
    
    IP --> GF
    GF --> FM
    FM --> FR
    FR --> ITS
    ITS --> CF
```

### 3. Type System Integration

Plugins can introduce custom data types by implementing:

- **Type Interfaces**: Defining type behavior and properties
- **Serialization**: Converting between internal and external representations
- **Operators**: Defining operations on custom types
- **Comparisons**: Implementing ordering and equality logic

## Plugin Development Process

### Development Framework

The Plugin Development Framework provides comprehensive tools and utilities for building Trino plugins:

```mermaid
graph TB
    subgraph "Plugin Development Components"
        BCT[BaseConnectorTest]
        QR[QueryRunner]
        DQR[DistributedQueryRunner]
        SQR[StandaloneQueryRunner]
    end
    
    subgraph "Development Tools"
        PT[Plugin Toolkit]
        CS[ClassLoader Safety]
        SP[Session Properties]
        AFR[Aggregate Function Rules]
    end
    
    subgraph "Testing Framework"
        UT[Unit Tests]
        IT[Integration Tests]
        PT2[Performance Tests]
        ST[Security Tests]
    end
    
    BCT --> UT
    QR --> IT
    DQR --> PT2
    SQR --> ST
    
    PT --> CS
    PT --> SP
    PT --> AFR
```

### Plugin Toolkit Integration

The Plugin Toolkit provides base implementations and utilities for plugin development:

```mermaid
graph TB
    subgraph "Plugin Toolkit Components"
        CS[ClassLoaderSafeConnectorMetadata]
        FBSAC[FileBasedSystemAccessControl]
        AASAC[AllowAllSystemAccessControl]
        SPP[SessionPropertiesProvider]
        AFR[AggregateFunctionRule]
        CER[ConnectorExpressionRule]
    end
    
    subgraph "Plugin Implementations"
        IM[IcebergMetadata]
        HM[HiveMetadata]
        KM[KafkaMetadata]
    end
    
    subgraph "Security Implementations"
        IS[IcebergSecurity]
        HS[HiveSecurity]
        KS[KafkaSecurity]
    end
    
    CS --> IM
    CS --> HM
    CS --> KM
    
    FBSAC --> IS
    AASAC --> HS
    SPP --> IM
    AFR --> IM
    CER --> IM
```

## Integration with Other Modules

### SQL Parser Integration

The Plugin Integration module works closely with the [SQL Parser & AST](SQL%20Parser%20&%20AST.md) module to handle plugin-specific SQL extensions:

- **Custom Functions**: Plugins register functions that integrate with the parser's function resolution
- **Connector-specific Syntax**: Special handling for connector-specific SQL extensions
- **Procedure Calls**: Integration with the parser for stored procedure execution

**Example: IcebergPlugin Function Integration**

The `IcebergThetaSketchForStats` function registered by IcebergPlugin integrates with the SQL parser to provide specialized statistical functions:

```mermaid
graph LR
    subgraph "SQL Parser Integration"
        SP[SQL Parser]
        FE[Function Expression]
        FR[Function Resolution]
    end
    
    subgraph "IcebergPlugin Functions"
        IP[IcebergPlugin]
        ITS[IcebergThetaSketchForStats]
        GF[Get Functions]
    end
    
    subgraph "Query Execution"
        QE[Query Execution]
        FO[Function Operator]
    end
    
    IP --> GF
    GF --> ITS
    ITS --> FR
    SP --> FE
    FE --> FR
    FR --> FO
    FO --> QE
```

### Query Planning Integration

Integration with the [SQL Analyzer, Planner & Optimizer](SQL%20Analyzer%2C%20Planner%20&%20Optimizer.md) module:

- **Metadata Resolution**: Plugin metadata feeds into the analyzer's scope resolution
- **Cost-based Optimization**: Plugin-provided statistics influence plan optimization
- **Pushdown Optimization**: Connector-specific pushdown rules integrate with the optimizer

### Execution Engine Integration

The Plugin Integration module provides the data access layer for the [Query Execution Engine](Query%20Execution%20Engine.md):

- **Split Generation**: Connectors provide splits that drive task execution
- **Data Reading**: PageSource implementations feed data to operators
- **Data Writing**: PageSink implementations handle result persistence

### Security Framework Integration

Integration with the [Trino Server & API](Trino%20Server%20&%20API.md) security components:

- **Access Control**: Plugin-specific access control integrates with the server's security manager
- **Authentication**: Connector-specific authentication mechanisms
- **Authorization**: Integration with external authorization systems

## Error Handling and Resilience

The Plugin Integration module implements several mechanisms to ensure system stability:

### 1. Plugin Isolation
- ClassLoader isolation prevents plugin conflicts
- Resource management prevents memory leaks
- Graceful degradation when plugins fail

### 2. Error Propagation
- Standardized error reporting through TrinoException
- Contextual error information for debugging
- Fallback mechanisms for critical operations

### 3. Recovery Mechanisms
- Plugin restart capabilities
- Connection pooling and retry logic
- Circuit breaker patterns for failing plugins

## Performance Considerations

### 1. Plugin Loading
- Lazy loading of plugin components
- Caching of frequently used metadata
- Connection pooling for data sources

### 2. Query Optimization
- Pushdown of operations to connectors
- Statistics-based optimization
- Parallel execution support

### 3. Memory Management
- Streaming data processing
- Configurable memory limits
- Spilling to disk for large operations

## Security Model

### 1. Authentication Integration
- Pluggable authentication providers
- Support for various authentication mechanisms
- Credential management and rotation

### 2. Authorization Framework
- Fine-grained access control
- Role-based permissions
- Row and column-level security

### 3. Data Protection
- Encryption in transit and at rest
- Data masking and anonymization
- Audit logging for compliance

## Configuration Management

### 1. Plugin Configuration
- Property-based configuration
- Environment variable support
- Dynamic configuration updates

### 2. Connector-Specific Settings
- Catalog configuration files
- Connection string parameters
- Performance tuning options

### 3. Runtime Configuration
- Session-level overrides
- Query-level hints
- Dynamic resource allocation

## Monitoring and Observability

### 1. Metrics Collection
- Plugin performance metrics
- Connector-specific statistics
- Resource utilization tracking

### 2. Health Checks
- Plugin availability monitoring
- Connection health validation
- Automatic failure detection

### 3. Logging and Tracing
- Structured logging support
- Distributed tracing integration
- Debug and diagnostic capabilities

## Best Practices

### 1. Plugin Design
- Follow interface segregation principles
- Implement proper resource cleanup
- Provide comprehensive error handling
- Document configuration options

### 2. Performance Optimization
- Implement pushdown capabilities
- Use appropriate data types
- Leverage parallel processing
- Cache frequently accessed data

### 3. Security Implementation
- Validate all inputs
- Implement proper authentication
- Follow principle of least privilege
- Secure sensitive configuration

## Related Documentation

- [Trino SPI](Trino%20SPI.md) - Core Service Provider Interface definitions
- [Connector Framework](Connector%20Framework.md) - Detailed connector implementation guide
- [Type System](Type%20System.md) - Type system architecture and implementation
- [Security Framework](Security%20Framework.md) - Security integration patterns
- [Function System](Function%20System.md) - Custom function development
- [Metadata & Connector Abstraction](Metadata%20&%20Connector%20Abstraction.md) - Metadata management patterns
- [SQL Parser & AST](SQL%20Parser%20&%20AST.md) - SQL parsing and function resolution
- [SQL Analyzer, Planner & Optimizer](SQL%20Analyzer%2C%20Planner%20&%20Optimizer.md) - Query planning and optimization integration
- [Query Execution Engine](Query%20Execution%20Engine.md) - Execution engine integration points
- [Trino Server & API](Trino%20Server%20&%20API.md) - Server infrastructure and REST API integration
- [Plugin Toolkit](Plugin%20Toolkit.md) - Development utilities and base implementations

## Conclusion

The Plugin Integration module is fundamental to Trino's extensibility and flexibility. By providing well-defined interfaces and comprehensive support for custom implementations, it enables the Trino ecosystem to grow and adapt to diverse data processing needs. Understanding this module is essential for developers who want to extend Trino's capabilities through custom plugins or connectors.