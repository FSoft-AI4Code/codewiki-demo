# Function Factory Module Documentation

## Introduction

The Function Factory module is a critical component of the ClickHouse database system that serves as the central registry and instantiation mechanism for aggregate functions. This module provides a factory pattern implementation for creating aggregate function instances, managing function registration, and handling function combinators that extend base aggregate functions with additional behaviors.

The module plays a pivotal role in query execution by dynamically resolving aggregate function names to their implementations, applying appropriate type transformations, and managing the complex ecosystem of function combinators that enhance base functionality.

## Architecture Overview

The Function Factory module implements a sophisticated factory pattern with support for function combinators, case-insensitive name resolution, and null-handling transformations. The architecture is built around the `AggregateFunctionFactory` singleton class that maintains registries of function creators and their properties.

```mermaid
graph TB
    subgraph "Function Factory Core"
        AFF["AggregateFunctionFactory<br/>Singleton"]
        AFREG["Function Registry<br/>aggregate_functions"]
        CIREG["Case-Insensitive Registry<br/>case_insensitive_aggregate_functions"]
        NULLMAP["Null Handling Maps<br/>respect_nulls/ignore_nulls"]
        COMBFAC["Combinator Factory<br/>AggregateFunctionCombinatorFactory"]
    end
    
    subgraph "Function Creation Flow"
        FC["Function Creator<br/>Value.creator"]
        PROP["Function Properties<br/>AggregateFunctionProperties"]
        TYPES["Type Conversion<br/>convertLowCardinalityTypesToNested"]
        NULLCHECK["Null Argument Check"]
    end
    
    subgraph "External Dependencies"
        CONTEXT["Query Context<br/>ContextPtr"]
        SETTINGS["System Settings<br/>Settings"]
        TYPESYS["DataType System"]
        AST["AST Functions<br/>ASTFunction"]
    end
    
    AFF --> AFREG
    AFF --> CIREG
    AFF --> NULLMAP
    AFF --> COMBFAC
    AFF --> FC
    FC --> PROP
    FC --> TYPES
    TYPES --> NULLCHECK
    AFF --> CONTEXT
    AFF --> SETTINGS
    AFF --> TYPESYS
    AFF --> AST
```

## Core Components

### AggregateFunctionFactory

The `AggregateFunctionFactory` class serves as the central registry and factory for all aggregate functions in the system. It implements the singleton pattern to ensure a single point of access for function resolution and instantiation.

**Key Responsibilities:**
- Function registration and name resolution
- Case-insensitive function name handling
- Null-handling transformations (RESPECT_NULLS/IGNORE_NULLS)
- Combinator application and validation
- Type conversion for LowCardinality types
- Query logging integration

**Core Methods:**
- `registerFunction()`: Registers new aggregate functions with the factory
- `get()`: Main factory method for creating aggregate function instances
- `getImpl()`: Internal implementation for function resolution
- `tryGetProperties()`: Retrieves function properties without instantiation
- `isAggregateFunctionName()`: Validates if a name corresponds to an aggregate function

### Function Registration System

The factory maintains multiple registries to support different naming conventions and access patterns:

```mermaid
graph LR
    subgraph "Registration Mechanisms"
        EXACT["Exact Name Registry<br/>aggregate_functions"]
        CASEINS["Case-Insensitive Registry<br/>case_insensitive_aggregate_functions"]
        ALIAS["Alias Mapping<br/>case_insensitive_name_mapping"]
        NULLTRANS["Null Transformation Maps<br/>respect_nulls/ignore_nulls"]
    end
    
    subgraph "Registration Process"
        REGCALL["registerFunction()"]
        VALIDATE["Validation Checks"]
        INSERT["Registry Insertion"]
        ALIASMAP["Alias Mapping Update"]
    end
    
    REGCALL --> VALIDATE
    VALIDATE --> INSERT
    INSERT --> EXACT
    INSERT --> CASEINS
    VALIDATE --> ALIASMAP
    ALIASMAP --> ALIAS
```

### Function Resolution Process

The function resolution follows a multi-step process to handle the complexity of aggregate function ecosystem:

```mermaid
sequenceDiagram
    participant Client
    participant Factory as AggregateFunctionFactory
    participant Registry as Function Registry
    participant Combinator as Combinator Factory
    participant Creator as Function Creator
    
    Client->>Factory: get(name, action, types, parameters)
    Factory->>Factory: convertLowCardinalityTypesToNested()
    Factory->>Factory: Check for null arguments
    alt Has Nullable Arguments
        Factory->>Combinator: tryFindSuffix("Null")
        Combinator-->>Factory: Null combinator
        Factory->>Factory: Transform arguments for nested function
    end
    
    Factory->>Registry: Find function by name
    alt Function Found
        Registry-->>Factory: Function creator and properties
    else Function Not Found
        Factory->>Combinator: tryFindSuffix(name)
        Combinator-->>Factory: Combinator found
        Factory->>Factory: Extract nested name
        Factory->>Factory: Recursive get() call
    end
    
    Factory->>Creator: Execute creator function
    Creator-->>Factory: AggregateFunction instance
    Factory-->>Client: Return aggregate function
```

## Data Flow Architecture

### Type Conversion and Null Handling

The module implements sophisticated type conversion logic to handle LowCardinality types and null values:

```mermaid
graph TD
    subgraph "Input Processing"
        INPUT["Input DataTypes<br/>argument_types"]
        LC_CHECK["LowCardinality Check"]
        CONVERT["convertLowCardinalityTypesToNested()"]
        NULL_CHECK["Nullable Type Detection"]
    end
    
    subgraph "Null Handling Logic"
        NULL_ARG["Has Null Arguments?"]
        NULL_COMB["Apply Null Combinator"]
        NESTED_GET["Recursive get() Call"]
        TRANSFORM["Transform Result"]
    end
    
    subgraph "Function Selection"
        FUNC_GET["getImpl() Call"]
        PROP_CHECK["Property Validation"]
        CREATE["Function Creation"]
    end
    
    INPUT --> LC_CHECK
    LC_CHECK --> CONVERT
    CONVERT --> NULL_CHECK
    NULL_CHECK --> NULL_ARG
    NULL_ARG -->|Yes| NULL_COMB
    NULL_ARG -->|No| FUNC_GET
    NULL_COMB --> NESTED_GET
    NESTED_GET --> TRANSFORM
    TRANSFORM --> CREATE
    FUNC_GET --> PROP_CHECK
    PROP_CHECK --> CREATE
```

### Combinator Processing

Function combinators extend base aggregate functions with additional behaviors:

```mermaid
graph LR
    subgraph "Combinator Resolution"
        NAME["Function Name"]
        SUFFIX["Suffix Analysis"]
        COMB_FIND["tryFindSuffix()"]
        COMB_VALID["Validation Checks"]
    end
    
    subgraph "Combinator Application"
        NESTED["Extract Nested Name"]
        RECURSIVE["Recursive Resolution"]
        TRANSFORM_ARGS["Transform Arguments"]
        TRANSFORM_PARAMS["Transform Parameters"]
        APPLY["Apply Combinator"]
    end
    
    NAME --> SUFFIX
    SUFFIX --> COMB_FIND
    COMB_FIND --> COMB_VALID
    COMB_VALID --> NESTED
    NESTED --> RECURSIVE
    RECURSIVE --> TRANSFORM_ARGS
    RECURSIVE --> TRANSFORM_PARAMS
    TRANSFORM_ARGS --> APPLY
    TRANSFORM_PARAMS --> APPLY
```

## Integration with System Components

### Context and Settings Integration

The Function Factory integrates with the query execution context to access system settings and logging capabilities:

```mermaid
graph TB
    subgraph "Context Integration"
        CTHREAD["CurrentThread"]
        QCONTEXT["Query Context"]
        SETTINGS["Settings Reference"]
        LOGGING["Query Logging"]
    end
    
    subgraph "Settings Usage"
        LOG_SETTING["log_queries Setting"]
        SETTINGS_PTR["Settings Pointer"]
        CREATOR_CALL["Creator Function Call"]
    end
    
    CTHREAD --> QCONTEXT
    QCONTEXT --> SETTINGS
    SETTINGS --> LOG_SETTING
    SETTINGS --> SETTINGS_PTR
    LOG_SETTING --> LOGGING
    SETTINGS_PTR --> CREATOR_CALL
```

### Error Handling and Validation

The module implements comprehensive error handling for various failure scenarios:

```mermaid
graph TD
    subgraph "Validation Points"
        NAME_LEN["Name Length Check"]
        FUNC_EXIST["Function Existence"]
        COMB_NEST["Combinator Nesting"]
        NULL_SUPPORT["Null Support Validation"]
    end
    
    subgraph "Error Types"
        TOO_LONG["TOO_LARGE_STRING_SIZE"]
        UNKNOWN_FUNC["UNKNOWN_AGGREGATE_FUNCTION"]
        ILLEGAL_AGG["ILLEGAL_AGGREGATION"]
        NOT_IMPL["NOT_IMPLEMENTED"]
        LOGICAL_ERR["LOGICAL_ERROR"]
    end
    
    NAME_LEN -->|Exceeds limit| TOO_LONG
    FUNC_EXIST -->|Not found| UNKNOWN_FUNC
    COMB_NEST -->|Invalid nesting| ILLEGAL_AGG
    NULL_SUPPORT -->|Not supported| NOT_IMPL
    FUNC_EXIST -->|Registry conflict| LOGICAL_ERR
```

## Dependencies and Interactions

### External Module Dependencies

The Function Factory module has significant dependencies on other system modules:

- **[Core_Engine](Core_Engine.md)**: Utilizes Settings system for configuration management
- **[Interpreters](Interpreters.md)**: Integrates with Context system for query execution state
- **[Data_Types](Data_Types.md)**: Leverages DataType system for type conversion and validation
- **[Parsers](Parsers.md)**: Processes ASTFunction nodes for function identification
- **[IO_System](IO_System.md)**: Uses WriteHelpers for error message formatting

### Internal Component Relationships

```mermaid
graph LR
    subgraph "Function Factory Components"
        FACTORY["AggregateFunctionFactory"]
        SETTINGS["Settings Integration"]
        REGISTRY["Function Registries"]
        COMBINATOR["Combinator Support"]
    end
    
    subgraph "Dependent Systems"
        CONTEXT["Context System"]
        DTYPES["DataType System"]
        AST["AST Processing"]
        THREAD["Thread Management"]
    end
    
    FACTORY --> SETTINGS
    FACTORY --> REGISTRY
    FACTORY --> COMBINATOR
    FACTORY --> CONTEXT
    FACTORY --> DTYPES
    FACTORY --> AST
    FACTORY --> THREAD
```

## Key Features and Capabilities

### Function Combinator Support

The module supports a rich ecosystem of function combinators that extend base aggregate functions:

- **Null Combinator**: Automatically applies null-handling behavior
- **Suffix-based Combinators**: Supports arbitrary suffix-based function extensions
- **Nested Combinator Support**: Handles complex combinator chains (with validation)
- **Internal Combinators**: Supports system-internal combinator types

### Case-Insensitive Function Resolution

The factory provides case-insensitive function name resolution while maintaining exact case mappings for display and logging purposes.

### Null Handling Transformations

Advanced null-handling capabilities including:
- **RESPECT_NULLS**: Functions that explicitly handle null values
- **IGNORE_NULLS**: Functions that ignore null values (default behavior)
- **Automatic Transformation**: Dynamic function selection based on null handling requirements

### Type System Integration

Seamless integration with the DataType system including:
- **LowCardinality Type Handling**: Automatic conversion to nested types
- **Nullable Type Processing**: Intelligent null combinator application
- **Type Validation**: Comprehensive type checking and validation

## Performance Considerations

### Caching and Registry Optimization

The factory implements efficient registry mechanisms with O(1) lookup performance for function resolution:

- **Hash-based Registries**: Standard unordered_map for exact name lookups
- **Case-insensitive Registry**: Separate registry for case-insensitive resolution
- **Alias Mapping**: Efficient alias resolution without full registry scans

### Memory Management

- **Singleton Pattern**: Single factory instance reduces memory overhead
- **Creator Function Storage**: Function pointers minimize per-instance memory usage
- **Property Caching**: Function properties cached at registration time

### Query Performance Impact

The factory design minimizes query execution overhead through:
- **Early Validation**: Function validation during parsing phase
- **Efficient Resolution**: Optimized lookup algorithms
- **Type Caching**: Reuse of type conversion results
- **Context Integration**: Minimal context switching overhead

## Extension Points

### Custom Function Registration

The module provides clear extension points for adding new aggregate functions:

```cpp
// Example registration pattern
AggregateFunctionFactory::instance().registerFunction(
    "custom_function",
    {creator_function, properties},
    Case::Sensitive
);
```

### Combinator Development

New combinators can be integrated through the AggregateFunctionCombinatorFactory system, following the established suffix-based naming convention.

### Null Handling Extensions

The null transformation system supports registration of custom null-handling relationships between functions.

This comprehensive documentation provides the foundation for understanding the Function Factory module's role in the ClickHouse system architecture, its internal workings, and its integration with other system components.