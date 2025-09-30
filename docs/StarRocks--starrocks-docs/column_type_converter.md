# Column Type Converter Module

## Introduction

The Column Type Converter module is a critical component of StarRocks' connector framework that handles type conversion between external data sources and StarRocks' internal type system. This module enables seamless data integration by providing bidirectional type mapping capabilities across multiple data formats and storage systems.

## Architecture Overview

```mermaid
graph TB
    subgraph "External Data Sources"
        HIVE["Hive"]
        HUDI["Hudi"]
        ICEBERG["Iceberg"]
        DELTA["Delta Lake"]
        PAIMON["Paimon"]
        KUDU["Kudu"]
    end
    
    subgraph "Column Type Converter"
        CTC["ColumnTypeConverter"]
        HV["Hive Type Visitor"]
        PV["Paimon Type Visitor"]
        PARSER["Type String Parser"]
        VALIDATOR["Type Validator"]
    end
    
    subgraph "StarRocks Type System"
        ST["Scalar Types"]
        AT["Array Types"]
        MT["Map Types"]
        STT["Struct Types"]
        DT["Decimal Types"]
    end
    
    HIVE --> CTC
    HUDI --> CTC
    ICEBERG --> CTC
    DELTA --> CTC
    PAIMON --> CTC
    KUDU --> CTC
    
    CTC --> HV
    CTC --> PV
    CTC --> PARSER
    CTC --> VALIDATOR
    
    HV --> ST
    PV --> ST
    PARSER --> AT
    PARSER --> MT
    PARSER --> STT
    VALIDATOR --> DT
    
    CTC --> ST
    CTC --> AT
    CTC --> MT
    CTC --> STT
    CTC --> DT
```

## Core Components

### ColumnTypeConverter Class

The `ColumnTypeConverter` class serves as the central hub for all type conversion operations. It provides static methods for converting between external data source types and StarRocks internal types.

#### Key Responsibilities:
- **Bidirectional Type Mapping**: Convert from external types to StarRocks types and vice versa
- **Complex Type Support**: Handle nested structures like arrays, maps, and structs
- **Type Validation**: Ensure type compatibility between different systems
- **Format-Specific Logic**: Implement specialized conversion logic for each data source

## Type Conversion Matrix

```mermaid
graph LR
    subgraph "Source Types"
        HT["Hive Types"]
        HUT["Hudi Types"]
        IT["Iceberg Types"]
        DT["Delta Types"]
        PT["Paimon Types"]
        KT["Kudu Types"]
    end
    
    subgraph "StarRocks Types"
        ST["Scalar Types"]
        AT["Array Types"]
        MT["Map Types"]
        STT["Struct Types"]
        DT2["Decimal Types"]
    end
    
    HT -->|fromHiveType| ST
    HUT -->|fromHudiType| ST
    IT -->|fromIcebergType| ST
    DT -->|fromDeltaLakeType| ST
    PT -->|fromPaimonType| ST
    KT -->|fromKuduType| ST
    
    HT -->|fromHiveTypeToArrayType| AT
    HT -->|fromHiveTypeToMapType| MT
    HT -->|fromHiveTypeToStructType| STT
    
    ST -->|toHiveType| HT
    ST -->|toTypeInfo| HT
```

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant DS as Data Source
    participant CTC as ColumnTypeConverter
    participant TS as Type System
    participant SR as StarRocks
    
    DS->>CTC: External Type String
    CTC->>CTC: Parse Type String
    CTC->>CTC: Validate Type
    CTC->>TS: Convert to Internal Type
    TS->>CTC: Internal Type Object
    CTC->>SR: Return StarRocks Type
    
    Note over CTC: Bidirectional conversion
    SR->>CTC: Internal Type
    CTC->>CTC: Map to External Type
    CTC->>DS: Return External Type String
```

## Supported Data Sources

### 1. Hive Type Conversion

The module provides comprehensive support for Hive data types through `fromHiveType()` and `toHiveType()` methods.

**Supported Hive Types:**
- Primitive: TINYINT, SMALLINT, INT, BIGINT, FLOAT, DOUBLE, DECIMAL, BOOLEAN, STRING, VARCHAR, CHAR, DATE, TIMESTAMP, BINARY
- Complex: ARRAY, MAP, STRUCT

**Key Features:**
- Pattern-based type string parsing using regex
- Support for parameterized types (DECIMAL, VARCHAR, CHAR)
- Complex type decomposition and reconstruction

### 2. Hudi Type Conversion

Specialized conversion for Hudi's Avro-based type system through `fromHudiType()` and `fromHudiTypeToHiveTypeString()`.

**Key Features:**
- Avro schema processing with logical type support
- Union type handling with nullability
- Custom timestamp and date logical types
- MOR (Merge On Read) specific optimizations

### 3. Iceberg Type Conversion

Handles Apache Iceberg's type system through `fromIcebergType()` method.

**Supported Features:**
- Nested complex types (List, Map, Struct)
- UUID and Binary type support
- Timestamp with timezone handling
- Decimal precision scaling

### 4. Delta Lake Type Conversion

Converts Delta Lake kernel types via `fromDeltaLakeType()` method.

**Special Features:**
- Column mapping mode support (ID, NAME)
- Delta-specific data types
- Metadata preservation for struct fields

### 5. Paimon Type Conversion

Implements visitor pattern for Paimon type conversion through `PaimonToHiveTypeVisitor`.

**Capabilities:**
- Row type to Struct conversion
- Local timestamp handling
- Binary and varbinary support

### 6. Kudu Type Conversion

Handles Kudu column schema types through `fromKuduType()` method.

**Features:**
- UNIXTIME_MICROS to DATETIME conversion
- Type attributes handling (precision, scale)
- VARCHAR length preservation

## Type Validation System

```mermaid
graph TD
    subgraph "Validation Process"
        START["Start Validation"]
        NULL_CHECK["Null Check"]
        UNKNOWN_CHECK["Unknown Type Check"]
        COMPLEX_CHECK["Complex Type Check"]
        PRIMITIVE_CHECK["Primitive Type Check"]
        END["Validation Result"]
    end
    
    START --> NULL_CHECK
    NULL_CHECK -->|Pass| UNKNOWN_CHECK
    NULL_CHECK -->|Fail| END
    UNKNOWN_CHECK -->|Pass| COMPLEX_CHECK
    UNKNOWN_CHECK -->|Fail| END
    COMPLEX_CHECK -->|Array| ARRAY_VALID["Array Type Validation"]
    COMPLEX_CHECK -->|Map| MAP_VALID["Map Type Validation"]
    COMPLEX_CHECK -->|Struct| STRUCT_VALID["Struct Type Validation"]
    COMPLEX_CHECK -->|Primitive| PRIMITIVE_CHECK
    ARRAY_VALID --> END
    MAP_VALID --> END
    STRUCT_VALID --> END
    PRIMITIVE_CHECK --> END
```

## Utility Functions

### String Parsing Utilities

The module includes sophisticated string parsing capabilities:

- **`getTypeKeyword()`**: Extract base type from complex type strings
- **`getPrecisionAndScale()`**: Parse decimal type parameters
- **`splitByFirstLevel()`**: Handle nested type structures
- **Regex Patterns**: Pre-compiled patterns for type string matching

### Type Information Conversion

- **`toTypeInfo()`**: Convert StarRocks types to Hive TypeInfo objects
- **Format-specific utilities**: Handle length constraints and type parameters

## Error Handling

The module implements comprehensive error handling:

- **`StarRocksConnectorException`**: Custom exception for type conversion failures
- **Validation failures**: Detailed error messages for unsupported type combinations
- **Pattern matching errors**: Specific error reporting for malformed type strings

## Integration Points

### Connector Framework Integration

The Column Type Converter integrates with the broader connector framework:

- **Metadata Discovery**: Used during table schema discovery
- **Query Planning**: Type compatibility checking during query optimization
- **Data Loading**: Type conversion during data ingestion
- **Schema Evolution**: Handling schema changes in external tables

### Dependencies

```mermaid
graph BT
    subgraph "External Dependencies"
        HIVE_LIB["Hive SerDe Library"]
        ICEBERG_LIB["Iceberg API"]
        DELTA_LIB["Delta Lake Kernel"]
        PAIMON_LIB["Paimon Types"]
        KUDU_LIB["Kudu Client"]
        AVRO_LIB["Avro Schema"]
    end
    
    subgraph "StarRocks Dependencies"
        CATALOG["Catalog System"]
        TYPE_SYS["Type System"]
        EXCEPTION["Exception Framework"]
    end
    
    CTC["ColumnTypeConverter"]
    
    HIVE_LIB --> CTC
    ICEBERG_LIB --> CTC
    DELTA_LIB --> CTC
    PAIMON_LIB --> CTC
    KUDU_LIB --> CTC
    AVRO_LIB --> CTC
    CATALOG --> CTC
    TYPE_SYS --> CTC
    EXCEPTION --> CTC
```

## Performance Considerations

### Optimization Strategies

1. **Static Method Design**: All conversion methods are static for minimal overhead
2. **Pattern Compilation**: Regex patterns are pre-compiled as static constants
3. **Visitor Pattern**: Used for complex type hierarchies (Paimon)
4. **Early Validation**: Type validation occurs before conversion attempts
5. **Immutable Collections**: Uses Guava's ImmutableList for thread safety

### Memory Management

- **String Interning**: Type strings are processed efficiently
- **Object Reuse**: Visitor pattern instances are singletons
- **Stream Processing**: Uses Java streams for collection processing

## Usage Examples

### Basic Type Conversion

```java
// Convert Hive type to StarRocks type
Type starrocksType = ColumnTypeConverter.fromHiveType("array<struct<a:int,b:string>>");

// Convert StarRocks type to Hive type
String hiveType = ColumnTypeConverter.toHiveType(ScalarType.createType(PrimitiveType.BIGINT));
```

### Complex Type Handling

```java
// Convert Hudi Avro schema
Schema avroSchema = // ... get Avro schema
Type convertedType = ColumnTypeConverter.fromHudiType(avroSchema);

// Convert Iceberg type
org.apache.iceberg.types.Type icebergType = // ... get Iceberg type
Type starrocksType = ColumnTypeConverter.fromIcebergType(icebergType);
```

### Type Validation

```java
// Validate type compatibility
boolean isCompatible = ColumnTypeConverter.validateColumnType(type1, type2);

// Check column equality
boolean columnsEqual = ColumnTypeConverter.columnEquals(column1, column2);
```

## Future Enhancements

### Planned Features

1. **Additional Data Sources**: Support for more external systems
2. **Enhanced Validation**: More sophisticated type compatibility checking
3. **Performance Optimization**: Caching mechanisms for frequent conversions
4. **Schema Evolution**: Better handling of schema changes over time

### Extensibility

The module is designed for easy extension:

- **Visitor Pattern**: Easy to add new data source support
- **Static Methods**: Simple to add new conversion functions
- **Modular Design**: Clear separation of concerns

## Related Documentation

- [Connector Framework Documentation](connector_framework.md)
- [Type System Documentation](type_system.md)
- [Catalog System Documentation](catalog.md)
- [Query Execution Documentation](query_execution.md)

## Conclusion

The Column Type Converter module is a foundational component that enables StarRocks to seamlessly integrate with various external data sources. Its comprehensive type mapping capabilities, robust error handling, and extensible design make it essential for the connector framework's success in providing unified data access across heterogeneous storage systems.