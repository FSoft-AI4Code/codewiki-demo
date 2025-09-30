# Utility Operations Module

The utility_operations module provides essential utility functions and string interpolation capabilities that support various operations throughout the Logstash system. This module is part of the broader [core_data_structures](core_data_structures.md) module and serves as a foundational layer for data manipulation and formatting operations.

## Overview

The utility_operations module consists of two core components:
- **StringInterpolation**: Advanced string templating and field interpolation system
- **Util**: Collection of utility methods for data structure manipulation

These components provide critical functionality for event processing, configuration templating, and data merging operations across the Logstash pipeline.

## Architecture

```mermaid
graph TB
    subgraph "Utility Operations Module"
        SI[StringInterpolation]
        UT[Util]
    end
    
    subgraph "Dependencies"
        OM[ObjectMappers]
        EV[Event]
        AC[Accessors]
        TS[Timestamp]
    end
    
    subgraph "Consumers"
        PE[Pipeline Execution]
        CF[Config System]
        PL[Plugin System]
        LG[Logging System]
    end
    
    SI --> OM
    SI --> EV
    SI --> TS
    UT --> AC
    
    PE --> SI
    PE --> UT
    CF --> SI
    PL --> SI
    LG --> SI
    
    classDef module fill:#e1f5fe
    classDef dependency fill:#f3e5f5
    classDef consumer fill:#e8f5e8
    
    class SI,UT module
    class OM,EV,AC,TS dependency
    class PE,CF,PL,LG consumer
```

## Core Components

### StringInterpolation

The StringInterpolation class provides sophisticated string templating capabilities with support for field references, timestamp formatting, and dynamic value substitution.

#### Key Features

- **Field Reference Interpolation**: Supports `%{field_name}` syntax for dynamic field substitution
- **Timestamp Formatting**: Multiple timestamp format patterns including UNIX, JODA, and Java time formats
- **Special Patterns**: Support for current time generation and complex nested field access
- **Thread-Safe Operations**: Uses ThreadLocal StringBuilder for efficient string building

#### Interpolation Patterns

```mermaid
graph LR
    subgraph "Interpolation Types"
        FR["Field Reference<br/>%{field}"]
        UF["UNIX Format<br/>%{+%s}"]
        JF["Java Format<br/>%{{pattern}}"]
        JD["JODA Format<br/>%{+pattern}"]
        TN["Time Now<br/>%{{TIME_NOW}}"]
    end
    
    subgraph "Processing Flow"
        TP[Template Parsing]
        FE[Field Extraction]
        TS[Timestamp Processing]
        VS[Value Substitution]
        SB[String Building]
    end
    
    FR --> TP
    UF --> TP
    JF --> TP
    JD --> TP
    TN --> TP
    
    TP --> FE
    FE --> TS
    TS --> VS
    VS --> SB
    
    classDef pattern fill:#fff3e0
    classDef process fill:#e3f2fd
    
    class FR,UF,JF,JD,TN pattern
    class TP,FE,TS,VS,SB process
```

#### Usage Examples

```java
// Field interpolation
String template = "Host: %{host}, Message: %{message}";
String result = StringInterpolation.evaluate(event, template);

// Timestamp formatting
String timeTemplate = "Date: %{+YYYY-MM-dd}, Epoch: %{+%s}";
String timeResult = StringInterpolation.evaluate(event, timeTemplate);

// Java time patterns
String javaTemplate = "ISO Date: %{{yyyy-MM-dd'T'HH:mm:ss.SSSZ}}";
String javaResult = StringInterpolation.evaluate(event, javaTemplate);
```

### Util

The Util class provides essential utility methods for data structure manipulation, particularly focused on merging operations for Maps and Lists.

#### Key Features

- **Deep Map Merging**: Recursive merging of nested Map structures
- **List Deduplication**: Intelligent merging of List values with duplicate removal
- **Type-Safe Operations**: Handles mixed data types during merge operations
- **Memory Efficient**: Uses buffer reuse for list operations

#### Merge Behavior

```mermaid
graph TD
    subgraph "Map Merge Logic"
        MM[mapMerge]
        TC[Type Check]
        
        subgraph "Merge Strategies"
            NM[Nested Map<br/>Recursive Merge]
            LM[List Merge<br/>Deduplicated Union]
            SM[Scalar Merge<br/>List Creation]
            OM[Object Merge<br/>Replacement]
        end
    end
    
    MM --> TC
    TC --> NM
    TC --> LM
    TC --> SM
    TC --> OM
    
    subgraph "List Operations"
        ML[mergeLists]
        LH[LinkedHashSet<br/>Buffer]
        DD[Deduplication]
        OR[Order Preservation]
    end
    
    LM --> ML
    ML --> LH
    LH --> DD
    DD --> OR
    
    classDef operation fill:#e8f5e8
    classDef strategy fill:#fff3e0
    classDef listop fill:#f3e5f5
    
    class MM,TC,ML operation
    class NM,LM,SM,OM strategy
    class LH,DD,OR listop
```

## Integration Points

### Event System Integration

The utility_operations module integrates closely with the [event_api](event_api.md) module:

```mermaid
sequenceDiagram
    participant E as Event
    participant SI as StringInterpolation
    participant A as Accessors
    participant OM as ObjectMappers
    
    E->>SI: evaluate(event, template)
    SI->>E: getField(fieldName)
    E->>A: get(data, fieldRef)
    A-->>E: field value
    E-->>SI: field value
    
    alt Complex Object
        SI->>OM: writeValueAsString(value)
        OM-->>SI: JSON string
    end
    
    SI-->>E: interpolated string
```

### Pipeline Processing Integration

Integration with [pipeline_execution](pipeline_execution.md) for configuration and logging:

```mermaid
graph LR
    subgraph "Pipeline Components"
        WL[WorkerLoop]
        ED[EventDispatcher]
        PF[PeriodicFlush]
    end
    
    subgraph "Utility Operations"
        SI[StringInterpolation]
        UT[Util]
    end
    
    subgraph "Operations"
        CF[Config Templates]
        LF[Log Formatting]
        DM[Data Merging]
    end
    
    WL --> SI
    ED --> UT
    PF --> SI
    
    SI --> CF
    SI --> LF
    UT --> DM
    
    classDef pipeline fill:#e3f2fd
    classDef utility fill:#e1f5fe
    classDef operation fill:#e8f5e8
    
    class WL,ED,PF pipeline
    class SI,UT utility
    class CF,LF,DM operation
```

## Data Flow

### String Interpolation Flow

```mermaid
flowchart TD
    subgraph "Input Processing"
        IT[Input Template]
        TP[Template Parsing]
        PR[Pattern Recognition]
    end
    
    subgraph "Field Resolution"
        FE[Field Extraction]
        EL[Event Lookup]
        VR[Value Retrieval]
    end
    
    subgraph "Value Processing"
        TC[Type Checking]
        TF[Timestamp Formatting]
        JS[JSON Serialization]
        SC[Scalar Conversion]
    end
    
    subgraph "Output Generation"
        SB[String Building]
        CO[Concatenation]
        OR[Output Result]
    end
    
    IT --> TP
    TP --> PR
    PR --> FE
    FE --> EL
    EL --> VR
    VR --> TC
    
    TC --> TF
    TC --> JS
    TC --> SC
    
    TF --> SB
    JS --> SB
    SC --> SB
    SB --> CO
    CO --> OR
    
    classDef input fill:#fff3e0
    classDef field fill:#e8f5e8
    classDef value fill:#f3e5f5
    classDef output fill:#e3f2fd
    
    class IT,TP,PR input
    class FE,EL,VR field
    class TC,TF,JS,SC value
    class SB,CO,OR output
```

### Map Merge Flow

```mermaid
flowchart TD
    subgraph "Input Maps"
        TM[Target Map]
        AM[Add Map]
    end
    
    subgraph "Entry Processing"
        EI[Entry Iteration]
        KC[Key Comparison]
        VC[Value Check]
    end
    
    subgraph "Merge Decision"
        NV[Null Value?]
        MM[Map-Map?]
        LL[List-List?]
        LO[List-Object?]
        OL[Object-List?]
        EQ[Equal Values?]
    end
    
    subgraph "Merge Actions"
        DI[Direct Insert]
        RM[Recursive Merge]
        LM[List Merge]
        LC[List Creation]
        LA[List Append]
        SK[Skip/Keep]
    end
    
    TM --> EI
    AM --> EI
    EI --> KC
    KC --> VC
    VC --> NV
    
    NV -->|Yes| DI
    NV -->|No| MM
    MM -->|Yes| RM
    MM -->|No| LL
    LL -->|Yes| LM
    LL -->|No| LO
    LO -->|Yes| LC
    LO -->|No| OL
    OL -->|Yes| LA
    OL -->|No| EQ
    EQ -->|Yes| SK
    EQ -->|No| LC
    
    classDef input fill:#fff3e0
    classDef process fill:#e8f5e8
    classDef decision fill:#f3e5f5
    classDef action fill:#e3f2fd
    
    class TM,AM input
    class EI,KC,VC process
    class NV,MM,LL,LO,OL,EQ decision
    class DI,RM,LM,LC,LA,SK action
```

## Performance Considerations

### String Interpolation Optimization

- **ThreadLocal StringBuilder**: Reuses StringBuilder instances to minimize object allocation
- **Pattern Caching**: Efficient pattern recognition and parsing
- **Lazy Evaluation**: Only processes interpolation patterns when found
- **Memory Management**: Clears StringBuilder buffer after each use

### Map Merge Optimization

- **Buffer Reuse**: LinkedHashSet buffer for list merge operations
- **Type Checking**: Early type detection to choose optimal merge strategy
- **Shallow vs Deep**: Intelligent decision on merge depth requirements
- **Memory Efficiency**: Minimizes temporary object creation

## Error Handling

### StringInterpolation Errors

```java
// JSON processing errors
try {
    String result = StringInterpolation.evaluate(event, template);
} catch (JsonProcessingException e) {
    // Handle JSON serialization errors for complex objects
}

// Invalid event type
try {
    StringInterpolation.evaluate(unknownEvent, template);
} catch (IllegalStateException e) {
    // Handle unknown event concrete class
}
```

### Util Errors

The Util class is designed to be robust and handles various edge cases:
- Null value handling in merge operations
- Type safety during map and list operations
- Graceful handling of mixed data types

## Testing and Validation

### Unit Test Coverage

- **Pattern Recognition**: Tests for all interpolation pattern types
- **Field Resolution**: Validation of field access and retrieval
- **Timestamp Formatting**: Coverage of all supported time formats
- **Merge Operations**: Comprehensive testing of merge scenarios
- **Edge Cases**: Null handling, empty collections, type mismatches

### Integration Testing

- **Event Integration**: Testing with real Event objects
- **Pipeline Integration**: Validation within pipeline context
- **Performance Testing**: Benchmarking of interpolation and merge operations

## Related Documentation

- [core_data_structures](core_data_structures.md) - Parent module overview
- [data_access_layer](data_access_layer.md) - Field access mechanisms
- [serialization_framework](serialization_framework.md) - JSON/CBOR serialization
- [type_conversion_system](type_conversion_system.md) - Type conversion utilities
- [event_api](event_api.md) - Event system integration
- [pipeline_execution](pipeline_execution.md) - Pipeline processing integration
- [logging_system](logging_system.md) - Logging and formatting integration

## Future Enhancements

### Planned Improvements

- **Performance Optimization**: Further optimization of string building operations
- **Pattern Extensions**: Additional interpolation pattern support
- **Caching Mechanisms**: Template compilation and caching for frequently used patterns
- **Async Operations**: Support for asynchronous interpolation operations
- **Memory Profiling**: Enhanced memory usage monitoring and optimization

### API Evolution

- **Streaming Support**: Support for streaming interpolation operations
- **Custom Formatters**: Pluggable formatter system for specialized use cases
- **Validation Framework**: Built-in template validation and error reporting
- **Metrics Integration**: Performance metrics collection and reporting