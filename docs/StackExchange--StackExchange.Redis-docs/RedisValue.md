# RedisValue Module Documentation

## Introduction

The RedisValue module is a fundamental component of the StackExchange.Redis library that provides a unified representation of values that can be stored in and retrieved from Redis. It serves as the primary data type for all Redis operations, offering seamless conversion between .NET types and Redis-compatible formats while maintaining optimal performance and memory efficiency.

## Overview

RedisValue is a readonly struct that encapsulates the complexity of Redis data types, providing a type-safe wrapper around Redis's string-based protocol. It supports implicit conversions from and to various .NET primitive types, collections, and binary data, making it the central abstraction for data exchange between .NET applications and Redis servers.

## Architecture

### Core Components

```mermaid
classDiagram
    class RedisValue {
        -object? _objectOrSentinel
        -ReadOnlyMemory<byte> _memory
        -long _overlappedBits64
        +RedisValue(string value)
        +RedisValue(long value)
        +RedisValue(double value)
        +RedisValue(byte[] value)
        +bool IsNull
        +bool IsNullOrEmpty
        +bool HasValue
        +long Length()
        +int GetByteCount()
        +int CopyTo(Span<byte> destination)
        +bool TryParse(out long val)
        +bool TryParse(out int val)
        +bool TryParse(out double val)
        +RedisValue Simplify()
        +bool StartsWith(RedisValue value)
        +object? Box()
        +static RedisValue Unbox(object? value)
    }

    class StorageType {
        <<enumeration>>
        Null
        Int64
        UInt64
        Double
        Raw
        String
    }

    RedisValue --> StorageType : uses
```

### Internal Storage Strategy

```mermaid
graph TD
    A[RedisValue Creation] --> B{Input Type}
    B -->|string| C[Store as String Object]
    B -->|int/long| D[Store in overlappedBits64]
    B -->|uint/ulong| E[Store in overlappedBits64 + Sentinel_UnsignedInteger]
    B -->|double| F[Store in overlappedBits64 + Sentinel_Double]
    B -->|binary data| G[Store in memory + Sentinel_Raw]
    B -->|null| H[Null Value]
    
    C --> I[objectOrSentinel = string value]
    D --> J[objectOrSentinel = Sentinel_SignedInteger]
    E --> K[objectOrSentinel = Sentinel_UnsignedInteger]
    F --> L[objectOrSentinel = Sentinel_Double]
    G --> M[memory = ReadOnlyMemory<byte>]
    H --> N[objectOrSentinel = null]
```

## Data Flow and Processing

### Value Conversion Pipeline

```mermaid
sequenceDiagram
    participant App as .NET Application
    participant RedisValue as RedisValue
    participant Storage as Internal Storage
    participant Redis as Redis Server
    
    App->>RedisValue: Create from .NET type
    RedisValue->>Storage: Determine optimal storage
    Storage-->>RedisValue: Store in appropriate format
    RedisValue-->>App: Return RedisValue instance
    
    App->>RedisValue: Send to Redis
    RedisValue->>Storage: Serialize to bytes
    Storage-->>Redis: Transmit to server
    Redis-->>Storage: Receive response
    Storage-->>RedisValue: Parse response
    RedisValue-->>App: Return converted value
```

### Type Conversion Matrix

```mermaid
graph LR
    subgraph "Implicit Conversions TO RedisValue"
        A1[string] -->|implicit| RV[RedisValue]
        A2[int] -->|implicit| RV
        A3[long] -->|implicit| RV
        A4[double] -->|implicit| RV
        A5[bool] -->|implicit| RV
        A6[binary data] -->|implicit| RV
        A7[Memory] -->|implicit| RV
        A8[ReadOnlyMemory] -->|implicit| RV
    end
    
    subgraph "Explicit Conversions FROM RedisValue"
        RV -->|explicit| B1[string]
        RV -->|explicit| B2[int]
        RV -->|explicit| B3[long]
        RV -->|explicit| B4[double]
        RV -->|explicit| B5[bool]
        RV -->|explicit| B6[binary data]
        RV -->|explicit| B7[Memory]
        RV -->|explicit| B8[ReadOnlyMemory]
    end
```

## Key Features and Capabilities

### 1. Multi-Type Support
RedisValue seamlessly handles multiple data types through a unified interface:

- **Primitive Types**: int, long, uint, ulong, double, float, bool
- **String Types**: string, char
- **Binary Types**: byte[], Memory<byte>, ReadOnlyMemory<byte>
- **Nullable Types**: All primitive nullable types are supported

### 2. Memory Efficiency
The implementation uses several optimization strategies:

```mermaid
graph TD
    A[Memory Optimization] --> B[Sentinel Objects]
    A --> C[Overlapped Storage]
    A --> D[Array Pooling]
    A --> E[String Interning]
    
    B --> F[Common integers -1 to 20]
    B --> G[Special double values]
    B --> H[Empty string singleton]
    
    C --> I[64-bit values in overlapped field]
    C --> J[Avoid heap allocation for primitives]
    
    D --> K[Rent arrays for temporary operations]
    D --> L[Return to pool after use]
    
    E --> M[Cache common string representations]
    E --> N[Reduce string allocations]
```

### 3. Performance Optimizations

#### Value Comparison
- Type-aware comparison with fast-path for same-type comparisons
- Optimized byte array comparison using unsafe pointer operations
- String comparison using ordinal comparison for performance

#### Parsing and Conversion
- Lazy parsing with `Simplify()` method
- Fast-path for integer parsing when possible
- Avoids unnecessary string allocations

#### Hash Code Generation
- Type-specific hash code generation
- Efficient byte array hashing using span operations

## Integration with Other Modules

### Relationship to Database Operations

```mermaid
graph TD
    A[RedisDatabase] -->|uses| B[RedisValue]
    A -->|uses| C[RedisKey]
    A -->|uses| D[RedisResult]
    
    B -->|converts to| E[Message System]
    C -->|converts to| E
    D -->|converts from| E
    
    E -->|sends to| F[PhysicalConnection]
    F -->|receives from| G[Redis Server]
```

### Connection to Result Processing

```mermaid
graph LR
    A[RedisValue] -->|parsed by| B[ResultProcessor.RedisValueProcessor]
    A -->|parsed by| C[ResultProcessor.RedisValueArrayProcessor]
    A -->|parsed by| D[ResultProcessor.RedisValueGeoPositionProcessor]
    
    E[RedisResult] -->|contains| A
    F[RedisValueWithExpiry] -->|contains| A
```

## Usage Patterns

### 1. Basic Value Creation
```csharp
// From primitives
RedisValue value1 = 42;
RedisValue value2 = "hello";
RedisValue value3 = 3.14;
RedisValue value4 = true;

// From binary data
byte[] data = { 1, 2, 3, 4 };
RedisValue value5 = data;

// Null values
RedisValue value6 = RedisValue.Null;
```

### 2. Value Conversion
```csharp
RedisValue value = "123";

// Safe conversion with TryParse
if (value.TryParse(out int intValue))
{
    Console.WriteLine($"Integer: {intValue}");
}

// Explicit conversion
string stringValue = (string)value;
long longValue = (long)value;
```

### 3. Comparison Operations
```csharp
RedisValue a = "hello";
RedisValue b = "hello";
RedisValue c = "world";

bool areEqual = a == b; // true
int comparison = a.CompareTo(c); // negative value
bool startsWith = a.StartsWith("hel"); // true
```

## Performance Characteristics

### Memory Allocation
- **Primitive values**: Zero heap allocation (stored in overlapped field)
- **String values**: Single string reference allocation
- **Binary data**: Single ReadOnlyMemory<byte> allocation
- **Large values**: May use array pooling for temporary operations

### Conversion Performance
- **Implicit conversions**: O(1) for primitives, O(n) for strings/byte arrays
- **Explicit conversions**: Optimized with type-specific fast paths
- **Parsing operations**: Lazy evaluation with caching

### Comparison Performance
- **Same type**: O(1) for primitives, O(n) for strings/byte arrays
- **Different types**: O(n) due to normalization requirements
- **Hash code**: O(n) for strings/byte arrays, O(1) for primitives

## Error Handling

### Conversion Errors
- Invalid cast exceptions for incompatible type conversions
- Overflow exceptions for numeric conversions that exceed target type ranges
- Format exceptions for string parsing failures

### Null Handling
- Null values are explicitly supported and handled consistently
- Null coalescing behavior follows Redis conventions (null ≈ 0 for numeric operations)
- IsNull and IsNullOrEmpty properties for null checking

## Thread Safety

RedisValue is immutable and thread-safe:
- All fields are readonly
- No mutable state after construction
- Safe for concurrent access across multiple threads
- Comparison operations are atomic

## Best Practices

### 1. Use Implicit Conversions
Prefer implicit conversions when creating RedisValue instances:
```csharp
// Good
RedisValue value = 42;

// Avoid
RedisValue value = new RedisValue(42, default, Sentinel_SignedInteger);
```

### 2. Check for Null Values
Always check for null values before operations:
```csharp
if (!value.IsNullOrEmpty)
{
    // Process value
}
```

### 3. Use TryParse for Safe Conversion
Use TryParse methods instead of explicit casts when conversion might fail:
```csharp
// Safe
if (value.TryParse(out int intValue))
{
    // Use intValue
}

// May throw
int intValue = (int)value; // Throws if not convertible
```

### 4. Leverage Type Information
Use the Type property for type-specific optimizations:
```csharp
switch (value.Type)
{
    case StorageType.Int64:
        // Fast integer processing
        break;
    case StorageType.String:
        // String-specific processing
        break;
}
```

## Related Documentation

- [RedisKey Module](RedisKey.md) - Key representation and operations
- [RedisResult Module](RedisResult.md) - Result processing and type conversion
- [RedisDatabase Module](RedisDatabase.md) - Database operations using RedisValue
- [MessageSystem Module](MessageSystem.md) - Message serialization and protocol handling
- [ResultProcessing Module](ResultProcessing.md) - Result parsing and conversion utilities

## Conclusion

The RedisValue module provides a robust, efficient, and type-safe foundation for all Redis data operations in the StackExchange.Redis library. Its unified interface abstracts the complexity of Redis's string-based protocol while maintaining excellent performance through careful memory management and optimization strategies. Understanding RedisValue is essential for effectively working with any other module in the library, as it serves as the primary data exchange format between .NET applications and Redis servers.