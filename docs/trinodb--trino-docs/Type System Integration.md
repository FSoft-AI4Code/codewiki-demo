# Type System Integration Module

## Introduction

The Type System Integration module serves as the central hub for type management and language function handling in Trino. It provides the foundational infrastructure for registering, managing, and resolving data types, as well as handling SQL language functions. This module acts as the bridge between the core type system defined in the Trino SPI and the metadata management layer, ensuring type consistency across the entire query execution pipeline.

## Architecture Overview

The Type System Integration module consists of two primary components that work together to provide comprehensive type and function management capabilities:

### Core Components

1. **TypeRegistry.InternalTypeManager** - Central type registry and manager
2. **LanguageFunctionManager.LanguageFunctionLoader** - SQL language function management

```mermaid
graph TB
    subgraph "Type System Integration Module"
        TR[TypeRegistry.InternalTypeManager]
        LFM[LanguageFunctionManager.LanguageFunctionLoader]
        
        TR --> |"provides types to"| LFM
        LFM --> |"uses types from"| TR
    end
    
    subgraph "External Dependencies"
        SPI[Trino SPI Type System]
        MM[Metadata Manager]
        QE[Query Execution]
        SP[SQL Parser]
    end
    
    SPI --> |"defines base types"| TR
    TR --> |"provides type resolution"| MM
    TR --> |"provides type resolution"| QE
    SP --> |"parses type signatures"| TR
    LFM --> |"registers functions"| MM
    LFM --> |"provides function implementations"| QE
```

## TypeRegistry.InternalTypeManager

### Purpose and Responsibilities

The `InternalTypeManager` is the core type registry that manages all data types in Trino. It provides:

- **Type Registration**: Centralized registration of built-in and parametric types
- **Type Resolution**: Lookup and instantiation of types from signatures
- **Type Validation**: Verification of type operators and consistency
- **SQL Type Parsing**: Conversion from SQL type strings to Type objects
- **Parametric Type Support**: Dynamic instantiation of parameterized types

### Architecture

```mermaid
graph TB
    subgraph "TypeRegistry Architecture"
        TR[TypeRegistry]
        ITM[InternalTypeManager]
        TC[Type Cache]
        STC[SQL Type Cache]
        PT[Parametric Types]
        BT[Built-in Types]
        TO[Type Operators]
        
        TR --> |"implements"| ITM
        TR --> TC
        TR --> STC
        TR --> PT
        TR --> BT
        TR --> TO
        
        TC --> |"caches instantiated"| PT
        STC --> |"caches parsed"| BT
    end
```

### Type Management Process

```mermaid
sequenceDiagram
    participant Client
    participant TypeRegistry
    participant TypeCache
    participant ParametricType
    participant Type
    
    Client->>TypeRegistry: getType(signature)
    TypeRegistry->>TypeRegistry: check built-in types
    alt Type found
        TypeRegistry-->>Client: return Type
    else Parametric type
        TypeRegistry->>TypeCache: lookup cached instance
        alt Cache hit
            TypeCache-->>TypeRegistry: return cached Type
        else Cache miss
            TypeRegistry->>ParametricType: createType(parameters)
            ParametricType->>Type: instantiate
            ParametricType-->>TypeRegistry: return new Type
            TypeRegistry->>TypeCache: cache instance
        end
        TypeRegistry-->>Client: return Type
    end
```

### Built-in Types

The TypeRegistry automatically registers essential built-in types during initialization:

**Primitive Types**: BOOLEAN, BIGINT, INTEGER, SMALLINT, TINYINT, DOUBLE, REAL, VARBINARY, DATE
**Complex Types**: INTERVAL_YEAR_MONTH, INTERVAL_DAY_TIME, HYPER_LOG_LOG, P4_HYPER_LOG_LOG
**Specialized Types**: JSON, JSON_2016, JSON_PATH, COLOR, IPADDRESS, UUID, TDIGEST, SET_DIGEST
**Parametric Types**: VARCHAR, CHAR, DECIMAL, ROW, ARRAY, MAP, FUNCTION, QDIGEST, TIMESTAMP, TIME

### Type Validation

The registry performs comprehensive validation to ensure type consistency:

```mermaid
graph LR
    subgraph "Type Validation Process"
        TV[verifyTypes]
        MO[Missing Operators Check]
        CO[Comparable Types Check]
        OO[Orderable Types Check]
        
        TV --> MO
        TV --> CO
        TV --> OO
        
        MO --> |"checks for"| EQUAL
        MO --> |"checks for"| HASH_CODE
        MO --> |"checks for"| XX_HASH_64
        
        CO --> |"validates"| COMPARISON
        CO --> |"validates"| LESS_THAN
        
        OO --> |"ensures"| ORDERING
    end
```

## LanguageFunctionManager.LanguageFunctionLoader

### Purpose and Responsibilities

The `LanguageFunctionLoader` manages SQL language functions, providing:

- **Function Registration**: Dynamic registration of SQL functions
- **Function Analysis**: Semantic analysis and validation of function definitions
- **Function Compilation**: Compilation of SQL functions to executable form
- **Security Integration**: Access control and permission management for functions
- **Query Isolation**: Per-query function namespace management

### Architecture

```mermaid
graph TB
    subgraph "LanguageFunctionManager Architecture"
        LFM[LanguageFunctionManager]
        QF[QueryFunctions]
        FL[FunctionListing]
        LFI[LanguageFunctionImplementation]
        LFD[LanguageFunctionData]
        SRA[SqlRoutineAnalyzer]
        SRP[SqlRoutinePlanner]
        SRC[SqlRoutineCompiler]
        
        LFM --> |"manages"| QF
        QF --> |"contains"| FL
        FL --> |"manages"| LFI
        LFI --> |"produces"| LFD
        LFM --> |"uses"| SRA
        LFM --> |"uses"| SRP
        LFM --> |"uses"| SRC
    end
```

### Function Lifecycle

```mermaid
stateDiagram-v2
    [*] --> FunctionSpecification
    FunctionSpecification --> Analysis: analyze()
    Analysis --> Planning: plan()
    Planning --> Compilation: compile()
    Compilation --> Executable: generate()
    Executable --> [*]
    
    state Analysis {
        [*] --> SemanticValidation
        SemanticValidation --> TypeChecking
        TypeChecking --> DependencyResolution
        DependencyResolution --> [*]
    }
    
    state Planning {
        [*] --> IRGeneration
        IRGeneration --> Optimization
        Optimization --> [*]
    }
```

### Function Types Support

The manager supports different function categories:

**SQL Functions**: Pure SQL functions compiled to Trino's internal representation
**Engine Functions**: Functions implemented in external languages (via LanguageFunctionEngine)
**Inline Functions**: Temporary functions scoped to a specific query
**Stored Functions**: Persistent functions stored in catalogs

### Security and Access Control

```mermaid
graph TB
    subgraph "Function Security Flow"
        FA[Function Access]
        AC[AccessControl]
        VAC[ViewAccessControl]
        IL[IdentityLoader]
        RAI[RunAsIdentity]
        
        FA --> |"checks"| AC
        AC --> |"may wrap"| VAC
        IL --> |"provides"| RAI
        RAI --> |"used for"| FunctionExecution
        
        VAC --> |"restricts access"| FunctionDependencies
    end
```

## Integration with Other Modules

### Trino SPI Integration

The Type System Integration module serves as the bridge between the Trino SPI type system and the internal metadata management:

```mermaid
graph LR
    subgraph "SPI Integration"
        SPI[Trino SPI Type.Type]
        TR[TypeRegistry]
        ITM[InternalTypeManager]
        
        SPI --> |"base types"| TR
        TR --> |"implements"| ITM
        ITM --> |"provides"| SPI
    end
```

### Metadata Manager Integration

```mermaid
graph TB
    subgraph "Metadata Integration"
        MM[MetadataManager]
        TR[TypeRegistry]
        LFM[LanguageFunctionManager]
        FM[FunctionManager]
        
        MM --> |"uses"| TR
        MM --> |"manages"| FM
        FM --> |"delegates to"| LFM
        LFM --> |"registers with"| FM
    end
```

### Query Execution Integration

```mermaid
graph LR
    subgraph "Query Execution Integration"
        QE[QueryExecution]
        TR[TypeRegistry]
        LFM[LanguageFunctionManager]
        SC[StatementClient]
        
        QE --> |"resolves types"| TR
        QE --> |"executes functions"| LFM
        SC --> |"provides context"| LFM
    end
```

## Data Flow

### Type Resolution Flow

```mermaid
sequenceDiagram
    participant QueryEngine
    participant TypeRegistry
    participant InternalTypeManager
    participant TypeCache
    participant Type
    
    QueryEngine->>InternalTypeManager: getType(signature)
    InternalTypeManager->>TypeRegistry: getType(signature)
    TypeRegistry->>TypeCache: lookup type
    alt Cache hit
        TypeCache-->>TypeRegistry: return cached type
    else Cache miss
        TypeRegistry->>TypeRegistry: instantiate parametric type
        TypeRegistry->>TypeCache: cache new type
    end
    TypeRegistry-->>InternalTypeManager: return type
    InternalTypeManager-->>QueryEngine: return type
```

### Function Resolution Flow

```mermaid
sequenceDiagram
    participant QueryEngine
    participant FunctionManager
    participant LanguageFunctionManager
    participant QueryFunctions
    participant FunctionImplementation
    
    QueryEngine->>FunctionManager: resolve function
    FunctionManager->>LanguageFunctionManager: get functions
    LanguageFunctionManager->>QueryFunctions: get function listing
    QueryFunctions->>FunctionImplementation: analyze and plan
    FunctionImplementation-->>QueryFunctions: return metadata
    QueryFunctions-->>LanguageFunctionManager: return function list
    LanguageFunctionManager-->>FunctionManager: return functions
    FunctionManager-->>QueryEngine: return resolved function
```

## Key Features

### Type System Features

- **Comprehensive Type Support**: All standard SQL types plus Trino-specific extensions
- **Parametric Type Instantiation**: Dynamic creation of parameterized types (VARCHAR(n), DECIMAL(p,s))
- **Type Caching**: Efficient caching of instantiated types to avoid repeated creation
- **Type Validation**: Comprehensive validation of type operators and consistency
- **SQL Type Parsing**: Direct parsing of SQL type strings to Type objects

### Language Function Features

- **Multi-Language Support**: SQL and external language function engines
- **Query Isolation**: Per-query function namespaces prevent conflicts
- **Security Integration**: Full integration with Trino's access control system
- **Function Compilation**: Compilation to efficient executable form
- **Dependency Management**: Automatic resolution and validation of function dependencies

## Performance Considerations

### Type Registry Performance

- **Caching Strategy**: Two-level caching (built-in types + parametric type cache)
- **Concurrent Access**: Thread-safe implementation using ConcurrentHashMap
- **Lazy Instantiation**: Parametric types instantiated only when needed
- **Memory Efficiency**: Shared type instances across the system

### Language Function Performance

- **Compilation Caching**: Compiled functions cached for repeated use
- **Query-Level Isolation**: Functions scoped to queries to avoid global locks
- **Efficient Resolution**: Function metadata cached after first resolution
- **Parallel Processing**: Support for concurrent function analysis and compilation

## Error Handling

### Type System Errors

- **TypeNotFoundException**: Raised when requested type cannot be found or instantiated
- **IllegalStateException**: Raised for type registration conflicts or validation failures
- **ParsingException**: Raised for invalid SQL type strings

### Language Function Errors

- **LanguageFunctionAnalysisException**: Raised during function analysis phase
- **TrinoException**: General function-related errors with specific error codes
- **IllegalStateException**: Raised for invalid function states or configurations

## Configuration and Extension

### Type Registration

Types can be registered through:
- **Built-in Registration**: Automatic during TypeRegistry initialization
- **Plugin Registration**: Via Plugin interface for connector-specific types
- **Dynamic Registration**: Runtime registration of new types

### Function Engine Extension

New language function engines can be added by:
- **Implementing LanguageFunctionEngine**: Interface for external language support
- **Registering with LanguageFunctionEngineManager**: Engine discovery and management
- **Providing Function Properties**: Configuration support for function properties

## References

- [Trino SPI Type System](Trino%20SPI.md#type-system)
- [Metadata & Connector Abstraction](Metadata%20&%20Connector%20Abstraction.md)
- [SQL Parser & AST](SQL%20Parser%20&%20AST.md)
- [Query Execution Engine](Query%20Execution%20Engine.md)