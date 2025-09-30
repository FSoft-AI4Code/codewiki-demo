# StructType Module Documentation

## Overview

The `struct_type` module provides the core implementation for STRUCT types in StarRocks, a complex data type that represents structured data with named fields. This module enables the database to handle nested, hierarchical data structures commonly found in modern data formats like Parquet, ORC, and JSON.

## Purpose and Core Functionality

The StructType module serves as the foundation for:
- **Complex Type Support**: Enabling StarRocks to handle structured data with multiple named fields
- **Schema Evolution**: Supporting dynamic schema changes and field pruning for optimization
- **Type Compatibility**: Ensuring type safety and compatibility across different data sources
- **Serialization/Deserialization**: Handling JSON serialization for metadata persistence

## Architecture

### Core Components

```mermaid
graph TB
    subgraph "StructType Core"
        ST[StructType]
        SF[StructField]
        STD[StructTypeDeserializer]
    end
    
    subgraph "Type System"
        T[Type]
        CT[ColumnType]
    end
    
    subgraph "Serialization"
        GU[GsonUtils]
        JE[JsonElement]
    end
    
    ST -->|extends| T
    ST -->|contains| SF
    ST -->|uses| STD
    STD -->|implements| JsonDeserializer
    STD -->|uses| GU
    GU -->|processes| JE
    
    SF -->|has| CT
    SF -->|has| T
```

### Component Relationships

```mermaid
graph LR
    subgraph "Frontend Layer"
        ST[StructType]
        CT[ColumnType]
        T[Type System]
    end
    
    subgraph "Storage Layer"
        BE[Backend Types]
        SM[ScalarFieldTypeToLogicalTypeMapping]
    end
    
    subgraph "Serialization"
        GS[Gson Serialization]
        JD[JSON Deserialization]
    end
    
    ST -->|field types| CT
    ST -->|inherits from| T
    ST -->|serializes via| GS
    BE -->|maps to| SM
    GS -->|creates| JD
```

## Data Flow

### Type Creation and Validation

```mermaid
sequenceDiagram
    participant Client
    participant Parser
    participant StructType
    participant TypeSystem
    participant Storage
    
    Client->>Parser: Define struct type
    Parser->>StructType: Create with fields
    StructType->>StructType: Validate field names
    StructType->>TypeSystem: Check type compatibility
    StructType->>Storage: Generate type descriptor
    Storage-->>Client: Type created
```

### Field Access and Pruning

```mermaid
sequenceDiagram
    participant Query
    participant StructType
    participant FieldMap
    participant Pruner
    
    Query->>StructType: Access field "name"
    StructType->>FieldMap: Lookup "name" (case-insensitive)
    FieldMap-->>StructType: Return field position
    StructType->>Pruner: Mark field as selected
    Query->>Pruner: Prune unused fields
    Pruner->>StructType: Remove unselected fields
```

## Key Features

### 1. Field Management
- **Named Fields**: Support for named struct fields with case-insensitive lookup
- **Field Validation**: Duplicate field name detection and validation
- **Position Tracking**: Maintains field positions for efficient access
- **Field Pruning**: Optimizes storage by removing unused fields

### 2. Type Compatibility
- **Structural Matching**: Compares struct types based on field names and types
- **Full Compatibility**: Supports compatibility checking for schema evolution
- **Nested Support**: Handles complex nested structures with depth limits

### 3. Serialization Support
- **JSON Serialization**: Custom deserializer for Gson-based persistence
- **Thrift Integration**: Converts to Thrift type descriptors for BE communication
- **MySQL Compatibility**: Provides MySQL-compatible type strings

## Integration with System Components

### Frontend Integration

```mermaid
graph TB
    subgraph "SQL Layer"
        SA[SQL Analyzer]
        EP[Expression Parser]
        CT[Column Type System]
    end
    
    subgraph "Catalog"
        ST[StructType]
        SF[StructField]
        T[Type Hierarchy]
    end
    
    subgraph "Storage Engine"
        BE[Backend Types]
        CD[Column Deserializer]
        CS[Column Serializer]
    end
    
    SA -->|creates| ST
    EP -->|validates| T
    CT -->|extends| ST
    ST -->|serializes| CD
    ST -->|deserializes| CS
    CD -->|maps to| BE
```

### Backend Type System Integration

The StructType module integrates with the backend type system through:
- **Type Mapping**: Maps to backend logical types via `ScalarFieldTypeToLogicalTypeMapping`
- **Serialization**: Converts to Thrift descriptors for BE processing
- **Field Access**: Provides field position information for columnar access

## Process Flows

### Struct Type Creation

```mermaid
flowchart TD
    Start([Start])
    ValidateFields{Validate Fields}
    CheckDuplicates{Check Duplicates}
    CreateFieldMap[Create Field Map]
    SetPositions[Set Positions]
    InitializeSelected[Initialize Selected Fields]
    End([End])
    
    Start --> ValidateFields
    ValidateFields -->|Valid| CheckDuplicates
    ValidateFields -->|Invalid| Error[Throw Exception]
    CheckDuplicates -->|No Duplicates| CreateFieldMap
    CheckDuplicates -->|Duplicates| Error
    CreateFieldMap --> SetPositions
    SetPositions --> InitializeSelected
    InitializeSelected --> End
```

### Field Access Pattern

```mermaid
flowchart TD
    Start([Field Access Request])
    NormalizeName[Normalize Field Name]
    LookupField[Lookup in FieldMap]
    FieldFound{Field Found?}
    ReturnPosition[Return Position]
    ThrowError[Throw Exception]
    End([End])
    
    Start --> NormalizeName
    NormalizeName --> LookupField
    LookupField --> FieldFound
    FieldFound -->|Yes| ReturnPosition
    FieldFound -->|No| ThrowError
    ReturnPosition --> End
    ThrowError --> End
```

## Dependencies

### Internal Dependencies
- **[type_system](type_system.md)**: Base Type class and type hierarchy
- **[column_management](column_management.md)**: Column type definitions and field management
- **[gson_utils](gson_utils.md)**: JSON serialization utilities

### External Dependencies
- **Thrift**: For backend communication type descriptors
- **Gson**: For JSON serialization and deserialization
- **Apache Commons**: For string utilities and validation

## Usage Examples

### Creating a Struct Type

```java
// Create struct fields
ArrayList<StructField> fields = new ArrayList<>();
fields.add(new StructField("id", Type.INT));
fields.add(new StructField("name", Type.VARCHAR));
fields.add(new StructField("address", Type.VARCHAR));

// Create struct type
StructType structType = new StructType(fields);
```

### Accessing Fields

```java
// Get field by name
StructField nameField = structType.getField("name");

// Check if field exists
boolean hasField = structType.containsField("email");

// Get field position
int position = structType.getFieldPos("id");
```

### Type Compatibility Check

```java
// Check if two struct types are compatible
boolean compatible = structType1.matchesType(structType2);

// Check full compatibility for schema evolution
boolean fullyCompatible = structType1.isFullyCompatible(structType2);
```

## Performance Considerations

### Memory Optimization
- **Field Pruning**: Automatically removes unused fields to reduce memory footprint
- **Lazy Initialization**: Selected fields array is initialized on demand
- **Case-Insensitive Lookup**: Uses lowercase field names for efficient HashMap access

### Serialization Efficiency
- **Custom Deserializer**: Optimized JSON deserialization for struct types
- **Thrift Conversion**: Efficient conversion to backend-compatible format
- **Field Position Caching**: Pre-computes field positions for fast access

## Error Handling

### Validation Errors
- **Duplicate Fields**: Throws `SemanticException` for duplicate field names
- **Invalid Fields**: Validates field types and names during construction
- **Access Errors**: Throws exceptions for non-existent field access

### Type Compatibility Errors
- **Structural Mismatch**: Returns false for incompatible struct types
- **Field Count Mismatch**: Handles different numbers of fields gracefully
- **Type Incompatibility**: Detects incompatible field types

## Future Enhancements

### Planned Features
- **Schema Evolution**: Enhanced support for backward/forward compatibility
- **Performance Optimization**: Improved field access patterns and caching
- **Extended Validation**: More comprehensive type validation rules

### Integration Improvements
- **Connector Support**: Enhanced integration with external data sources
- **Query Optimization**: Better predicate pushdown for struct fields
- **Storage Optimization**: Improved columnar storage for nested types

## Related Documentation

- [Type System](type_system.md) - Core type hierarchy and base classes
- [Column Management](column_management.md) - Column type definitions and utilities
- [Complex Types](complex_types.md) - Overview of complex type support
- [Backend Type System](be_type_system.md) - Backend type mapping and serialization