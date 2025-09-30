# Kudu Connector Module Documentation

## Introduction

The Kudu Connector module provides StarRocks with the capability to integrate with Apache Kudu, a distributed columnar storage engine designed for fast analytics on fast data. This module enables StarRocks to query and analyze data stored in Kudu tables, extending the system's data lakehouse capabilities to include Kudu as a first-class data source.

The connector implements predicate pushdown, type conversion, and schema mapping to ensure efficient query execution and seamless integration with StarRocks' query optimization engine.

## Architecture Overview

```mermaid
graph TB
    subgraph "StarRocks Query Engine"
        QE[Query Engine]
        OP[Optimizer]
        SC[Scanner]
    end
    
    subgraph "Kudu Connector"
        KC[KuduConnector]
        KPC[KuduPredicateConverter]
        KTC[KuduTypeConverter]
        KSC[KuduScanner]
    end
    
    subgraph "Apache Kudu"
        KM[Kudu Master]
        KT[Kudu Tablet Servers]
        KDS[Kudu Data Storage]
    end
    
    QE --> OP
    OP --> KPC
    OP --> SC
    SC --> KSC
    KSC --> KM
    KM --> KT
    KT --> KDS
    
    KPC -.->|Predicate Pushdown| KT
    KTC -.->|Type Mapping| KSC
```

## Core Components

### KuduPredicateConverter

The `KuduPredicateConverter` is the primary component responsible for converting StarRocks' internal predicate representations into Kudu-native predicates. This enables efficient predicate pushdown, reducing data transfer and improving query performance.

#### Key Features:
- **Scalar Operator Visitor Pattern**: Implements `ScalarOperatorVisitor` to traverse and convert various predicate types
- **Type-Aware Conversion**: Handles type conversion between StarRocks and Kudu data types
- **Compound Predicate Support**: Supports AND, OR, and NOT logical operations
- **Comparison Operations**: Maps StarRocks binary predicates to Kudu comparison operations
- **NULL Handling**: Converts IS NULL and IS NOT NULL predicates
- **IN Clause Support**: Handles IN and NOT IN predicates with multiple values

#### Predicate Conversion Flow

```mermaid
sequenceDiagram
    participant QE as Query Engine
    participant KPC as KuduPredicateConverter
    participant Kudu as Kudu Client
    
    QE->>KPC: ScalarOperator (WHERE clause)
    KPC->>KPC: visitCompoundPredicate()
    KPC->>KPC: visitBinaryPredicate()
    KPC->>KPC: visitIsNullPredicate()
    KPC->>KPC: visitInPredicate()
    KPC->>Kudu: List<KuduPredicate>
    Kudu->>Kudu: Apply predicates to scan
```

#### Supported Predicate Types

| StarRocks Predicate | Kudu Predicate | Notes |
|-------------------|---------------|--------|
| Binary (=, <, >, <=, >=) | ComparisonPredicate | Full support with type conversion |
| IS NULL | IsNullPredicate | Direct mapping |
| IS NOT NULL | IsNotNullPredicate | Direct mapping |
| IN | InListPredicate | Multi-value support |
| NOT IN | Not supported | Returns empty result |
| LIKE | Not supported | Returns empty result |
| OR | Compound logic | Limited support |
| AND | Compound logic | Full support |
| NOT | Compound logic | Limited support |

#### Type Conversion Matrix

The converter handles various data type mappings between StarRocks and Kudu:

```mermaid
graph LR
    subgraph "StarRocks Types"
        SR_BOOL[BOOLEAN]
        SR_INT[INT]
        SR_BIGINT[BIGINT]
        SR_FLOAT[FLOAT]
        SR_DOUBLE[DOUBLE]
        SR_DECIMAL[DECIMAL]
        SR_VARCHAR[VARCHAR]
        SR_DATE[DATE]
        SR_DATETIME[DATETIME]
    end
    
    subgraph "Kudu Types"
        K_BOOL[BOOL]
        K_INT32[INT32]
        K_INT64[INT64]
        K_FLOAT[FLOAT]
        K_DOUBLE[DOUBLE]
        K_DECIMAL[DECIMAL]
        K_STRING[STRING]
        K_DATE[DATE]
        K_TIMESTAMP[TIMESTAMP]
    end
    
    SR_BOOL --> K_BOOL
    SR_INT --> K_INT32
    SR_BIGINT --> K_INT64
    SR_FLOAT --> K_FLOAT
    SR_DOUBLE --> K_DOUBLE
    SR_DECIMAL --> K_DECIMAL
    SR_VARCHAR --> K_STRING
    SR_DATE --> K_DATE
    SR_DATETIME --> K_TIMESTAMP
```

#### ExtractColumnName Inner Class

The `ExtractColumnName` class is a specialized visitor that extracts column names from scalar operators:

- **ColumnRefOperator**: Direct name extraction from variable references
- **CastOperator**: Recursive extraction through cast operations
- **Other operators**: Returns null (unsupported)

This ensures that only valid column references are processed for predicate conversion.

## Integration with StarRocks Ecosystem

### Query Optimization Integration

```mermaid
graph TB
    subgraph "Query Processing Pipeline"
        SQL[SQL Parser]
        AN[Analyzer]
        OP[Optimizer]
        EX[Execution]
    end
    
    subgraph "Kudu Integration Points"
        PC[PredicateConverter]
        TC[TypeConverter]
        SC[Scanner]
    end
    
    subgraph "Storage Layer"
        KC[Kudu Client]
        KT[Kudu Tablets]
    end
    
    SQL --> AN
    AN --> OP
    OP --> PC
    PC --> TC
    TC --> SC
    SC --> KC
    KC --> KT
```

### Connector Framework Integration

The Kudu connector integrates with StarRocks' connector framework through:

1. **ConnectorFactory**: Creates Kudu-specific connector instances
2. **MetadataTable**: Provides schema information for Kudu tables
3. **PartitionTraits**: Handles partition-aware query planning
4. **RemoteFileInfo**: Manages data location and access information

## Performance Optimizations

### Predicate Pushdown Strategy

The converter implements intelligent predicate pushdown:

- **Early Filtering**: Pushes filters as close to data as possible
- **Predicate Combination**: Combines multiple predicates for optimal performance
- **Fallback Handling**: Gracefully handles unsupported predicates
- **Type Coercion**: Ensures type compatibility during conversion

### Scan Optimization

```mermaid
graph LR
    subgraph "Scan Optimization Process"
        QP[Query Plan]
        PC[Predicate Conversion]
        PS[Predicate Selection]
        KS[Kudu Scan]
        DR[Data Return]
    end
    
    QP --> PC
    PC --> PS
    PS --> KS
    KS --> DR
    
    PS -.->|Rejected| QP
    PC -.->|Failed| QP
```

## Error Handling and Limitations

### Supported Operations
- Basic comparison predicates (=, <, >, <=, >=)
- NULL checks (IS NULL, IS NOT NULL)
- IN clauses with multiple values
- AND logical operations
- Simple column references

### Limitations
- **NOT IN predicates**: Not supported by Kudu, returns empty results
- **LIKE predicates**: Not supported, returns empty results
- **Complex expressions**: Limited support for nested expressions
- **OR operations**: Restricted support based on predicate compatibility

### Error Recovery
- **Type Cast Failures**: Gracefully skips predicate pushdown
- **Schema Mismatches**: Falls back to post-scan filtering
- **Unsupported Operations**: Returns empty predicate lists

## Dependencies

The Kudu connector module depends on several StarRocks components:

### Internal Dependencies
- [ColumnTypeConverter](column_type_converter.md): Type conversion utilities
- [ScalarOperatorVisitor](scalar_operator_visitor.md): Query expression traversal
- [ConnectorFramework](connector_framework.md): Base connector infrastructure

### External Dependencies
- Apache Kudu Client Library: Native Kudu connectivity
- Google Guava: Collection utilities
- Apache Logging: Log4j for debugging and monitoring

## Configuration and Usage

### Connector Configuration

The Kudu connector requires minimal configuration:

```sql
CREATE EXTERNAL CATALOG kudu_catalog 
PROPERTIES (
    "type" = "kudu",
    "kudu.master_addresses" = "host1:7051,host2:7051,host3:7051"
);
```

### Query Examples

```sql
-- Basic query with predicate pushdown
SELECT * FROM kudu_catalog.default.table1 
WHERE column1 > 100 AND column2 IS NOT NULL;

-- Query with IN clause
SELECT * FROM kudu_catalog.default.table1 
WHERE status IN ('active', 'pending');

-- Query with compound predicates
SELECT * FROM kudu_catalog.default.table1 
WHERE column1 > 100 AND (column2 = 'value' OR column3 IS NULL);
```

## Monitoring and Debugging

### Logging

The converter provides detailed logging through Log4j:
- Predicate conversion success/failure
- Type conversion issues
- Schema resolution problems
- Performance metrics

### Performance Metrics

Key performance indicators:
- Predicate pushdown ratio
- Scan efficiency improvement
- Data transfer reduction
- Query latency improvement

## Future Enhancements

### Planned Features
- Enhanced OR predicate support
- LIKE predicate implementation
- Complex expression handling
- Partition pruning optimization
- Statistics integration

### Performance Improvements
- Batch predicate processing
- Caching mechanisms
- Parallel scan optimization
- Adaptive predicate selection

## Related Documentation

- [Connector Framework](connector_framework.md) - General connector architecture
- [Predicate Evaluation](predicate_evaluation.md) - Query predicate processing
- [Type System](type_system.md) - Data type handling
- [Query Optimization](query_optimization.md) - Query planning and execution
- [Storage Engine](storage_engine.md) - Underlying storage integration