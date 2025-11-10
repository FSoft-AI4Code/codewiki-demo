# Connector Framework

The Connector Framework is the core abstraction layer in Trino that enables seamless integration with diverse data sources. It provides a standardized interface for connectors to expose their data sources, handle metadata operations, and execute queries while maintaining Trino's distributed query processing capabilities.

## Overview

The Connector Framework serves as the bridge between Trino's query engine and external data sources. It defines the contracts that connectors must implement to participate in query planning, optimization, and execution. This framework enables Trino to treat heterogeneous data sources as unified tables while preserving the unique characteristics and capabilities of each underlying system.

## Core Architecture

### Component Relationships

```mermaid
graph TB
    subgraph "Trino Engine"
        ME[Metadata Engine]
        QE[Query Engine]
        PE[Plan Execution]
    end
    
    subgraph "Connector Framework"
        CM[ColumnMetadata]
        CS[Constraint]
        CMD[ConnectorMaterializedViewDefinition]
        CCM[ConnectorManager]
        CH[ConnectorHandle]
    end
    
    subgraph "Connector Implementations"
        JC[JDBC Connectors]
        HC[Hive Connector]
        IC[Iceberg Connector]
        DLC[Delta Lake Connector]
        KC[Kafka Connector]
    end
    
    subgraph "External Systems"
        DB[(Databases)]
        FS[(File Systems)]
        MS[(Message Systems)]
        DL[(Data Lakes)]
    end
    
    ME --> CM
    ME --> CS
    ME --> CMD
    QE --> CCM
    PE --> CH
    
    CCM --> JC
    CCM --> HC
    CCM --> IC
    CCM --> DLC
    CCM --> KC
    
    JC --> DB
    HC --> FS
    IC --> DL
    DLC --> DL
    KC --> MS
```

### Key Components

#### ColumnMetadata
The `ColumnMetadata` class represents the metadata for a column in a table exposed by a connector. It encapsulates essential column properties including:

- **Name**: Column identifier (automatically normalized to lowercase)
- **Type**: Trino type mapping for the column
- **Nullability**: Whether the column accepts null values
- **Default Value**: Optional default value specification
- **Comment**: Human-readable description
- **Extra Info**: Additional connector-specific metadata
- **Hidden**: Visibility flag for system columns
- **Properties**: Extensible key-value metadata

```mermaid
classDiagram
    class ColumnMetadata {
        -String name
        -Type type
        -Optional~String~ defaultValue
        -boolean nullable
        -String comment
        -String extraInfo
        -boolean hidden
        -Map~String,Object~ properties
        +getName() String
        +getType() Type
        +getDefaultValue() Optional~String~
        +isNullable() boolean
        +getComment() String
        +getExtraInfo() String
        +isHidden() boolean
        +getProperties() Map~String,Object~
        +getColumnSchema() ColumnSchema
    }
    
    class Builder {
        -String name
        -Type type
        -Optional~String~ defaultValue
        -boolean nullable
        -Optional~String~ comment
        -Optional~String~ extraInfo
        -boolean hidden
        -Map~String,Object~ properties
        +setName(String) Builder
        +setType(Type) Builder
        +setDefaultValue(Optional~String~) Builder
        +setNullable(boolean) Builder
        +setComment(Optional~String~) Builder
        +setExtraInfo(Optional~String~) Builder
        +setHidden(boolean) Builder
        +setProperties(Map~String,Object~) Builder
        +build() ColumnMetadata
    }
    
    ColumnMetadata --> Builder : creates
```

#### Constraint
The `Constraint` class represents filtering conditions that connectors can use to optimize data access. It provides multiple levels of constraint expression:

- **Summary**: High-level tuple domain constraints for partition pruning
- **Expression**: Connector-specific expression trees for pushdown
- **Predicate**: Runtime filtering functions for fine-grained control
- **Assignments**: Variable-to-column mappings for expression evaluation

```mermaid
classDiagram
    class Constraint {
        -TupleDomain~ColumnHandle~ summary
        -ConnectorExpression expression
        -Map~String,ColumnHandle~ assignments
        -Optional~Predicate~ predicate
        -Optional~Set~ predicateColumns
        +getSummary() TupleDomain~ColumnHandle~
        +getExpression() ConnectorExpression
        +getAssignments() Map~String,ColumnHandle~
        +predicate() Optional~Predicate~
        +getPredicateColumns() Optional~Set~
    }
    
    class ConstraintType {
        <<enumeration>>
        ALWAYS_TRUE
        ALWAYS_FALSE
        SUMMARY_ONLY
        EXPRESSION_ONLY
        PREDICATE_ONLY
        COMPOUND
    }
    
    Constraint --> ConstraintType : represents
```

#### ConnectorMaterializedViewDefinition
The `ConnectorMaterializedViewDefinition` class defines the structure and properties of materialized views within connectors:

- **Original SQL**: The defining query text
- **Storage Table**: Optional backing table reference
- **Columns**: View column definitions with type information
- **Grace Period**: Staleness tolerance for cached results
- **Metadata**: Owner, comment, and path information

```mermaid
classDiagram
    class ConnectorMaterializedViewDefinition {
        -String originalSql
        -Optional~CatalogSchemaTableName~ storageTable
        -Optional~String~ catalog
        -Optional~String~ schema
        -List~Column~ columns
        -Optional~Duration~ gracePeriod
        -Optional~String~ comment
        -Optional~String~ owner
        -List~CatalogSchemaName~ path
    }
    
    class Column {
        -String name
        -TypeId type
        -Optional~String~ comment
        +getName() String
        +getType() TypeId
        +getComment() Optional~String~
    }
    
    ConnectorMaterializedViewDefinition *-- Column : contains
```

## Integration with Trino Architecture

### Query Planning Integration

```mermaid
sequenceDiagram
    participant Client
    participant Parser
    participant Analyzer
    participant Planner
    participant Connector
    participant DataSource
    
    Client->>Parser: Submit Query
    Parser->>Analyzer: Parse Tree
    Analyzer->>Connector: Request Metadata
    Connector->>DataSource: Fetch Schema
    DataSource-->>Connector: Schema Info
    Connector-->>Analyzer: ColumnMetadata[]
    Analyzer->>Planner: Analyzed Query
    Planner->>Connector: Push Constraint
    Connector->>Connector: Optimize Access
    Connector-->>Planner: Optimized Plan
    Planner-->>Client: Execution Plan
```

### Data Flow Architecture

```mermaid
graph LR
    subgraph "Query Processing"
        QP[Query Parser]
        QA[Query Analyzer]
        QP[Query Planner]
        QE[Query Executor]
    end
    
    subgraph "Connector Framework"
        CM[ColumnMetadata]
        CS[Constraint System]
        MV[Materialized Views]
        CH[Connector Handles]
    end
    
    subgraph "Connector SPI"
        CCM[ConnectorMetadata]
        CSR[ConnectorSplitManager]
        CSP[ConnectorPageSource]
        CSK[ConnectorPageSink]
    end
    
    QA --> CM
    QP --> CS
    QE --> MV
    CCM --> CSR
    CSR --> CSP
    CSP --> CSK
```

## Connector Development Patterns

### Basic Connector Structure

```mermaid
graph TD
    subgraph "Connector Implementation"
        MP[Main Plugin Class]
        MD[Metadata Implementation]
        SM[Split Manager]
        PS[Page Source Provider]
        PK[Page Sink Provider]
    end
    
    subgraph "Framework Integration"
        PI[Plugin Interface]
        CM[ColumnMetadata Usage]
        CT[Constraint Handling]
        MV[Materialized View Support]
    end
    
    MP --> PI
    MD --> CM
    SM --> CT
    PS --> CM
    PK --> MV
```

### Metadata Resolution Flow

```mermaid
sequenceDiagram
    participant QE as Query Engine
    participant MF as Metadata Framework
    participant CM as ColumnMetadata
    participant CI as Connector Implementation
    participant DS as Data Source
    
    QE->>MF: Request Table Schema
    MF->>CI: getTableMetadata()
    CI->>DS: Query Schema
    DS-->>CI: Raw Schema
    CI->>CI: Map to Trino Types
    CI->>CM: Create ColumnMetadata
    CM-->>MF: Return Metadata
    MF-->>QE: Provide Schema
```

## Advanced Features

### Constraint Pushdown Optimization

The Constraint system enables sophisticated query optimization through multiple pushdown mechanisms:

1. **Partition Pruning**: TupleDomain constraints eliminate unnecessary partitions
2. **Filter Pushdown**: Connector expressions are translated to native query languages
3. **Runtime Filtering**: Dynamic predicates refine results during execution
4. **Index Utilization**: Predicate information enables index-based access paths

### Materialized View Integration

Connectors can expose materialized views with:
- **Automatic Refresh**: Grace period-based staleness management
- **Storage Optimization**: Optional backing table references
- **Query Rewrite**: Transparent substitution with materialized data
- **Incremental Updates**: Efficient delta processing

## Performance Considerations

### Metadata Caching
- ColumnMetadata objects are cached at the connector level
- Schema information is refreshed based on configuration
- Type mapping is pre-computed for common scenarios

### Constraint Evaluation
- Predicate evaluation is optimized for short-circuiting
- Expression trees are minimized before pushdown
- Column references are resolved efficiently through assignments

### Memory Management
- ColumnMetadata uses immutable collections
- Constraint objects are designed for efficient serialization
- Materialized view definitions support lazy evaluation

## Error Handling

The framework provides comprehensive error handling for:
- **Type Mapping Failures**: Graceful degradation for unsupported types
- **Constraint Pushdown Rejection**: Fallback to Trino-side filtering
- **Metadata Resolution Issues**: Clear error messages with context
- **Permission Denials**: Proper security exception propagation

## Testing and Validation

### Connector Validation Framework
- ColumnMetadata consistency checks
- Constraint pushdown verification
- Materialized view refresh testing
- Performance regression detection

### Integration Testing Patterns
- End-to-end query execution validation
- Metadata round-trip verification
- Constraint optimization effectiveness
- Cross-connector compatibility testing

## Best Practices

### ColumnMetadata Design
- Use appropriate Trino type mappings
- Provide meaningful comments and extra info
- Consider nullability carefully
- Leverage properties for connector-specific metadata

### Constraint Implementation
- Implement comprehensive TupleDomain support
- Provide accurate predicate column information
- Handle expression pushdown gracefully
- Consider performance implications of complex predicates

### Materialized View Support
- Define appropriate grace periods
- Handle storage table lifecycle properly
- Provide clear ownership information
- Support incremental refresh when possible

## Related Documentation

- [Trino SPI Overview](Trino%20SPI.md) - Core service provider interface concepts
- [Plugin Architecture](Plugin%20Architecture.md) - Plugin lifecycle and registration
- [Type System](Type%20System.md) - Type mapping and conversion
- [Query Planning](SQL%20Analyzer%2C%20Planner%20%26%20Optimizer.md) - Query optimization integration
- [Metadata Management](Metadata%20%26%20Connector%20Abstraction.md) - Centralized metadata coordination

## References

- [Trino Connector SPI Documentation](https://trino.io/docs/current/develop/connectors.html)
- [Connector Development Guide](https://trino.io/docs/current/develop/spi-overview.html)
- [Built-in Connector Examples](https://github.com/trinodb/trino/tree/master/plugin)