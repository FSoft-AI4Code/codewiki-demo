# Partition Builder Module Documentation

## Introduction

The partition_builder module is a critical component of StarRocks' catalog management system, responsible for creating and configuring partition information for tables. This module serves as a centralized builder that converts various partition description types into concrete PartitionInfo objects that can be used throughout the system for data organization and query optimization.

## Module Overview

The partition_builder module provides a unified interface for constructing different types of partition information, including range partitions, list partitions, and expression-based partitions. It acts as a factory pattern implementation that handles the complexity of partition validation, type checking, and configuration setup.

## Core Architecture

### Component Structure

```mermaid
graph TB
    subgraph "Partition Builder Module"
        PB[PartitionInfoBuilder]
        
        PB --> RP[Range Partition Builder]
        PB --> LP[List Partition Builder]
        PB --> EP[Expression Partition Builder]
        
        RP --> RPI[RangePartitionInfo]
        LP --> LPI[ListPartitionInfo]
        EP --> ERPI[ExpressionRangePartitionInfo]
        EP --> ERPIV2[ExpressionRangePartitionInfoV2]
    end
    
    subgraph "Input Types"
        RD[RangePartitionDesc]
        LD[ListPartitionDesc]
        ED[ExpressionPartitionDesc]
    end
    
    subgraph "Dependencies"
        COL[Column]
        PI[PartitionInfo]
        MU[MetaUtils]
    end
    
    RD --> PB
    LD --> PB
    ED --> PB
    
    COL --> PB
    PI --> RPI
    PI --> LPI
    PI --> ERPI
    MU --> PB
```

### Key Components

#### PartitionInfoBuilder
The main builder class that provides static factory methods for creating different types of PartitionInfo objects. It serves as the entry point for all partition creation operations.

**Key Methods:**
- `build()`: Main factory method that dispatches to specific builders
- `buildRangePartitionInfo()`: Creates range partition information
- `buildListPartitionInfo()`: Creates list partition information  
- `buildExpressionPartitionInfo()`: Creates expression-based partition information

## Partition Types Supported

### 1. Range Partitions
Range partitions divide data based on value ranges of partition columns.

```mermaid
graph LR
    subgraph "Range Partition Creation Flow"
        A[RangePartitionDesc] --> B[Validate Columns]
        B --> C[Check Column Types]
        C --> D[Create RangePartitionInfo]
        D --> E[Process Single Range Descriptions]
        E --> F[RangePartitionInfo Object]
    end
```

**Validation Rules:**
- Partition columns must be key columns
- Cannot be aggregated columns
- Must be non-floating point types
- Must be non-complex types

### 2. List Partitions
List partitions divide data based on discrete value lists.

```mermaid
graph LR
    subgraph "List Partition Creation Flow"
        A[ListPartitionDesc] --> B[Find Partition Columns]
        B --> C[Create ListPartitionInfo]
        C --> D[Process Single Item Lists]
        D --> E[Process Multi Item Lists]
        E --> F[Set Partition Properties]
        F --> G[ListPartitionInfo Object]
    end
```

**Features:**
- Supports single-item and multi-item list partitions
- Handles automatic partition detection
- Configures partition properties (data property, memory settings, replication)

### 3. Expression Partitions
Expression partitions use computed expressions to determine partition assignment.

```mermaid
graph LR
    subgraph "Expression Partition Creation Flow"
        A[ExpressionPartitionDesc] --> B{Check Range Desc}
        B -->|Null| C[Create ExpressionRangePartitionInfo]
        B -->|Exists| D[Process Range Partition]
        D --> E{Auto Partition?}
        E -->|Yes| F[ExpressionRangePartitionInfo]
        E -->|No| G[ExpressionRangePartitionInfoV2]
    end
```

**Types:**
- **Automatic Partition**: For time-based automatic partitioning
- **Expression Range**: For custom expression-based ranges

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant Client
    participant PartitionInfoBuilder
    participant ColumnValidator
    participant PartitionInfo
    participant MetaUtils
    
    Client->>PartitionInfoBuilder: build(partitionDesc, schema, nameToId, isTemp)
    PartitionInfoBuilder->>PartitionInfoBuilder: Determine partition type
    
    alt Range Partition
        PartitionInfoBuilder->>ColumnValidator: Validate range columns
        ColumnValidator-->>PartitionInfoBuilder: Validation result
        PartitionInfoBuilder->>PartitionInfoBuilder: Create RangePartitionInfo
        PartitionInfoBuilder->>MetaUtils: buildIdToColumn(schema)
        PartitionInfoBuilder->>PartitionInfo: handleNewSinglePartitionDesc()
    else List Partition
        PartitionInfoBuilder->>PartitionInfoBuilder: Find partition columns
        PartitionInfoBuilder->>PartitionInfo: Create ListPartitionInfo
        PartitionInfoBuilder->>PartitionInfo: setValues()/setMultiValues()
        PartitionInfoBuilder->>PartitionInfo: setPartitionProperties()
    else Expression Partition
        PartitionInfoBuilder->>PartitionInfoBuilder: Check expression type
        PartitionInfoBuilder->>PartitionInfo: Create ExpressionRangePartitionInfo
        PartitionInfoBuilder->>PartitionInfo: Create ExpressionRangePartitionInfoV2
    end
    
    PartitionInfoBuilder-->>Client: PartitionInfo object
```

## Integration with Catalog System

### Dependencies

```mermaid
graph TB
    subgraph "Partition Builder Dependencies"
        PB[PartitionInfoBuilder]
        
        PB --> COL[Column Management]
        PB --> PI[PartitionInfo Types]
        PB --> MU[MetaUtils]
        PB --> AD[AST Descriptions]
        
        COL --> CC[column_core]
        COL --> CT[type_system]
        
        PI --> PM[partition_management]
        
        AD --> RD[RangePartitionDesc]
        AD --> LD[ListPartitionDesc]
        AD --> ED[ExpressionPartitionDesc]
    end
```

### Related Modules

- **[column_management](column_management.md)**: Provides column validation and type checking
- **[partition_management](partition_management.md)**: Contains partition information classes
- **[type_system](type_system.md)**: Handles data type validation and conversion
- **[sql_parser_optimizer](sql_parser_optimizer.md)**: Provides AST description classes

## Error Handling

The module implements comprehensive error handling for various scenarios:

```mermaid
graph TD
    A[Partition Creation] --> B{Validation}
    B -->|Invalid Column| C[DdlException: Invalid partition column]
    B -->|Wrong Type| D[DdlException: Invalid data type]
    B -->|Missing Column| E[DdlException: Column not found]
    B -->|Analysis Error| F[DdlException: AnalysisException]
    B -->|Success| G[PartitionInfo Created]
```

**Exception Types:**
- `DdlException`: Primary exception for DDL operations
- `AnalysisException`: Wrapped for analysis-related errors
- Custom messages for specific validation failures

## Configuration and Properties

### Partition Properties
Each partition can be configured with:
- **Data Property**: Storage and compression settings
- **Memory Settings**: In-memory storage configuration
- **Replication**: Number of replicas
- **Tablet Type**: Type of tablet storage
- **Data Cache**: Cache configuration for the partition
- **Temporary Flag**: Whether partition is temporary

### Validation Rules
- Partition columns must exist in the table schema
- Column names are case-insensitive
- Partition columns cannot be aggregated (except NONE)
- Floating point and complex types are prohibited
- Expression partitions support only single partition column

## Usage Examples

### Basic Usage Pattern
```java
// Create partition info from description
PartitionInfo partitionInfo = PartitionInfoBuilder.build(
    partitionDesc,      // Range/List/Expression partition description
    tableSchema,        // List of Column objects
    partitionNameToId,  // Map of partition names to IDs
    isTemporary         // Whether partitions are temporary
);
```

### Integration Points
The module integrates with:
- **Table Creation**: During CREATE TABLE operations
- **Schema Changes**: When modifying partition schemes
- **Query Planning**: For partition pruning optimization
- **Data Loading**: To determine target partitions

## Performance Considerations

- **Column Lookup**: Optimized column finding with early termination
- **Validation**: Type checking performed once during creation
- **Memory Usage**: Minimal temporary object creation
- **Error Handling**: Early validation to prevent costly operations

## Future Enhancements

Potential areas for improvement:
- Support for additional partition types
- Enhanced validation with better error messages
- Performance optimizations for large partition counts
- Integration with partition statistics
- Support for custom partition functions

## Conclusion

The partition_builder module serves as a critical foundation for StarRocks' partitioning capabilities, providing a robust and extensible framework for managing table partitions. Its design enables support for multiple partition strategies while maintaining consistency and validation across the system.