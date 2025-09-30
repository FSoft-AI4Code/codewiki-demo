# Type Conversion System

The Type Conversion System is a critical component of Logstash's core data processing infrastructure, responsible for seamless conversion between Java and Ruby object types. This system enables Logstash to efficiently handle data transformation across the JRuby runtime boundary while maintaining type safety and performance.

## Overview

The Type Conversion System provides bidirectional type conversion capabilities that allow Logstash to:
- Convert Java objects to Ruby objects for JRuby runtime compatibility
- Convert Ruby objects back to Java objects for efficient processing
- Maintain type fidelity during conversions
- Handle complex nested data structures (maps, lists, arrays)
- Support specialized Logstash types like Timestamps

## Architecture

```mermaid
graph TB
    subgraph "Type Conversion System"
        V[Valuefier]
        J[Javafier]
        R[Rubyfier]
        
        subgraph "Conversion Flow"
            Input[Input Object] --> V
            V --> |"Java → Ruby"| ConvertedData[Converted Data]
            ConvertedData --> R
            R --> |"Ruby Objects"| RubyRuntime[Ruby Runtime]
            ConvertedData --> J
            J --> |"Java Objects"| JavaRuntime[Java Runtime]
        end
        
        subgraph "Converter Maps"
            VM[Valuefier Converters]
            JM[Javafier Converters]
            RM[Rubyfier Converters]
        end
        
        V -.-> VM
        J -.-> JM
        R -.-> RM
    end
    
    subgraph "Dependencies"
        CDS[core_data_structures]
        RI[ruby_integration]
    end
    
    V --> CDS
    J --> CDS
    R --> RI
```

## Core Components

### Valuefier
The entry point for type conversion that normalizes input objects into Logstash's internal representation.

**Key Responsibilities:**
- Primary conversion interface for all input data
- Handles Java primitives, Ruby objects, and complex collections
- Creates ConvertedMap and ConvertedList wrappers for collections
- Manages timestamp conversions from various date/time formats

**Conversion Strategy:**
```mermaid
flowchart TD
    A[Input Object] --> B{Null Check}
    B -->|null| C[Return RubyNil]
    B -->|not null| D[Get Object Class]
    D --> E{Converter Exists?}
    E -->|Yes| F[Apply Converter]
    E -->|No| G[Fallback Convert]
    G --> H[Search Superclass Converters]
    H --> I{Found?}
    I -->|Yes| J[Cache & Apply Converter]
    I -->|No| K[Throw MissingConverterException]
    F --> L[Return Converted Object]
    J --> L
```

### Javafier
Converts objects from Logstash's internal representation back to pure Java objects.

**Key Responsibilities:**
- Extracts Java values from BiValue objects
- Converts ConvertedMap/ConvertedList back to HashMap/ArrayList
- Handles Ruby object to Java primitive conversions
- Used primarily by getField operations

**Supported Conversions:**
- Ruby strings/symbols → Java String
- Ruby numerics → Java primitives (Long, Double, BigInteger, etc.)
- Ruby collections → Java collections
- Ruby timestamps → Logstash Timestamp objects

### Rubyfier
Converts Java objects and Logstash internal objects to Ruby objects for JRuby runtime compatibility.

**Key Responsibilities:**
- Deep conversion of nested structures to Ruby objects
- Creates RubyHash and RubyArray from Java collections
- Maintains Ruby object identity where appropriate
- Handles specialized conversions for Logstash types

**Deep Conversion Process:**
```mermaid
sequenceDiagram
    participant Client
    participant Rubyfier
    participant ConverterMap
    participant RubyRuntime
    
    Client->>Rubyfier: deep(runtime, object)
    Rubyfier->>Rubyfier: Check null
    Rubyfier->>ConverterMap: Get converter for class
    alt Converter found
        ConverterMap-->>Rubyfier: Return converter
        Rubyfier->>Converter: convert(runtime, object)
        Converter-->>RubyRuntime: Create Ruby object
        RubyRuntime-->>Rubyfier: Ruby object
    else No converter
        Rubyfier->>Rubyfier: fallbackConvert()
        Rubyfier->>ConverterMap: Search assignable classes
        ConverterMap-->>Rubyfier: Found converter
        Rubyfier->>ConverterMap: Cache converter
    end
    Rubyfier-->>Client: IRubyObject
```

## Data Flow

```mermaid
graph LR
    subgraph "Input Sources"
        A[Java Objects]
        B[Ruby Objects]
        C[Mixed Collections]
    end
    
    subgraph "Type Conversion System"
        D[Valuefier.convert]
        E[ConvertedMap/ConvertedList]
        F[Javafier.deep]
        G[Rubyfier.deep]
    end
    
    subgraph "Output Targets"
        H[Java Runtime]
        I[Ruby Runtime]
        J[Event Fields]
    end
    
    A --> D
    B --> D
    C --> D
    D --> E
    E --> F
    E --> G
    F --> H
    F --> J
    G --> I
```

## Component Interactions

```mermaid
classDiagram
    class Valuefier {
        +convert(Object) Object
        -fallbackConvert(Object, Class) Object
        -initConverters() Map
        +IDENTITY Converter
    }
    
    class Javafier {
        +deep(Object) Object
        -fallbackConvert(Object, Class) Object
        -initConverters() Map
    }
    
    class Rubyfier {
        +deep(Ruby, Object) IRubyObject
        -deepList(Ruby, Collection) RubyArray
        -deepMap(Ruby, Map) RubyHash
        -fallbackConvert(Ruby, Object, Class) IRubyObject
    }
    
    class ValuefierConverter {
        <<interface>>
        +convert(Object) Object
    }
    
    class RubyfierConverter {
        <<interface>>
        +convert(Ruby, Object) IRubyObject
    }
    
    Valuefier --> ValuefierConverter
    Rubyfier --> RubyfierConverter
    Valuefier ..> ConvertedMap
    Valuefier ..> ConvertedList
    Javafier ..> ConvertedMap
    Javafier ..> ConvertedList
```

## Performance Optimizations

### Converter Caching
All three components use `ConcurrentHashMap` for thread-safe converter caching:
- **Initial Capacity**: 50 converters
- **Load Factor**: 0.2 for minimal collision
- **Concurrency Level**: 1 for single-threaded optimization

### Fallback Strategy
When a direct converter isn't found:
1. Search through registered converters for assignable classes
2. Cache the found converter for the specific class
3. Throw `MissingConverterException` if no converter is found

### Identity Conversions
Objects that don't require conversion use `IDENTITY` converters to avoid unnecessary processing overhead.

## Type Support Matrix

| Java Type | Valuefier | Javafier | Rubyfier | Notes |
|-----------|-----------|----------|----------|-------|
| String | ✓ | ✓ | ✓ | Direct conversion |
| Primitives (int, long, float, double) | ✓ | ✓ | ✓ | Numeric conversions |
| Boolean | ✓ | ✓ | ✓ | Boolean handling |
| BigInteger/BigDecimal | ✓ | ✓ | ✓ | Large number support |
| Collections (List, Map) | ✓ | ✓ | ✓ | Deep conversion |
| Ruby Objects | ✓ | ✓ | ✓ | JRuby integration |
| Timestamp | ✓ | ✓ | ✓ | Logstash timestamp |
| Date/Time variants | ✓ | - | - | Multiple date formats |

## Integration Points

### With Core Data Structures
- Uses `ConvertedMap` and `ConvertedList` from [core_data_structures](core_data_structures.md)
- Integrates with `Timestamp` objects for time handling
- Leverages `RubyUtil` for Ruby runtime access

### With Ruby Integration
- Depends on [ruby_integration](ruby_integration.md) for JRuby types
- Uses `JrubyTimestampExtLibrary` for timestamp conversions
- Integrates with Ruby runtime for object creation

### With Event Processing
- Supports [event_api](event_api.md) field access operations
- Enables data transformation in [pipeline_execution](pipeline_execution.md)
- Facilitates plugin data handling in [plugin_system](plugin_system.md)

## Error Handling

### MissingConverterException
Thrown when no suitable converter is found for a given type:
```java
throw new MissingConverterException(cls);
```

### Fallback Mechanisms
- Searches parent classes and interfaces for compatible converters
- Caches successful fallback discoveries for future use
- Provides detailed error messages for debugging

## Thread Safety

All converter maps use `ConcurrentHashMap` with optimized parameters:
- Thread-safe read/write operations
- Minimal lock contention
- Efficient caching strategy

## Usage Patterns

### Event Field Access
```java
// Getting field value (uses Javafier)
Object value = Javafier.deep(event.getField("fieldName"));

// Setting field value (uses Valuefier)
event.setField("fieldName", Valuefier.convert(inputValue));
```

### Ruby Integration
```java
// Converting for Ruby runtime (uses Rubyfier)
IRubyObject rubyValue = Rubyfier.deep(runtime, javaObject);
```

## Best Practices

1. **Type Consistency**: Ensure all data passes through Valuefier.convert when entering the system
2. **Performance**: Leverage cached converters by using consistent object types
3. **Error Handling**: Handle MissingConverterException for unsupported types
4. **Memory Management**: Be aware of object creation overhead in deep conversions

## Future Considerations

- Support for additional Java 8+ time types
- Performance optimizations for large collection conversions
- Enhanced error reporting and debugging capabilities
- Integration with new Ruby runtime versions