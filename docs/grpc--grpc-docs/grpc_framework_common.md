# gRPC Framework Common Module Documentation

## Introduction

The `grpc_framework_common` module provides fundamental abstractions and enumerations that define the core semantics of gRPC services and methods. This module serves as the foundation for understanding and classifying RPC methods based on their streaming behavior and control flow patterns. It contains essential enums that are used throughout the gRPC framework to categorize and handle different types of RPC operations.

## Module Architecture

### Core Components

The module consists of two primary components:

1. **Cardinality** - Defines the streaming semantics of RPC methods
2. **Service** - Describes the control flow style of RPC method implementations

### Architecture Overview

```mermaid
graph TB
    subgraph "grpc_framework_common"
        C[Cardinality Enum<br/>Streaming Semantics]
        S[Service Enum<br/>Control Flow Style]
    end
    
    subgraph "grpc_framework"
        FI[Framework Interfaces]
        FF[Foundation Components]
        FC[Framework Common]
    end
    
    subgraph "grpc_core"
        CC[Core Components]
        CI[Client Interceptors]
        SI[Server Interceptors]
    end
    
    C -->|Used by| FI
    C -->|Used by| CC
    S -->|Used by| FF
    S -->|Used by| FC
    
    FI -->|Implements| CC
    FF -->|Supports| CI
    FC -->|Supports| SI
```

## Component Details

### Cardinality Enum

The `Cardinality` enum is a fundamental classification system for RPC methods based on their streaming behavior. It defines four distinct patterns that cover all possible combinations of request and response streaming.

#### Definition
```python
@enum.unique
class Cardinality(enum.Enum):
    """Describes the streaming semantics of an RPC method."""
    
    UNARY_UNARY = "request-unary/response-unary"
    UNARY_STREAM = "request-unary/response-streaming"
    STREAM_UNARY = "request-streaming/response-unary"
    STREAM_STREAM = "request-streaming/response-streaming"
```

#### Cardinality Values

| Value | Description | Request Pattern | Response Pattern | Use Case |
|-------|-------------|-----------------|------------------|----------|
| `UNARY_UNARY` | Single request, single response | Unary | Unary | Standard RPC calls, simple function calls |
| `UNARY_STREAM` | Single request, multiple responses | Unary | Streaming | Server-side streaming, data feeds |
| `STREAM_UNARY` | Multiple requests, single response | Streaming | Unary | Client-side streaming, batch operations |
| `STREAM_STREAM` | Multiple requests, multiple responses | Streaming | Streaming | Bidirectional streaming, real-time communication |

#### Usage in gRPC Framework

```mermaid
graph LR
    subgraph "RPC Method Classification"
        UM[User Method]
        C[Cardinality Enum]
        MM[Method Metadata]
        MH[Method Handler]
    end
    
    UM -->|Analyzed by| C
    C -->|Determines| MM
    MM -->|Configures| MH
    
    subgraph "Framework Processing"
        MH -->|Routes to| SC[Server Call Handler]
        MH -->|Routes to| CC[Client Call Handler]
    end
```

### Service Enum

The `Service` enum defines the control flow patterns for implementing RPC methods, determining how the service logic is structured and executed.

#### Definition
```python
@enum.unique
class Service(enum.Enum):
    """Describes the control flow style of RPC method implementation."""
    
    INLINE = "inline"
    EVENT = "event"
```

#### Service Values

| Value | Description | Execution Pattern | Use Case |
|-------|-------------|-------------------|----------|
| `INLINE` | Synchronous execution | Immediate response | Simple, fast operations |
| `EVENT` | Asynchronous execution | Event-driven response | Complex, long-running operations |

## Integration with gRPC Ecosystem

### Relationship with Framework Interfaces

```mermaid
graph TB
    subgraph "grpc_framework_common"
        C[Cardinality]
        S[Service]
    end
    
    subgraph "grpc_framework/interfaces"
        UM[UnaryUnaryMultiCallable]
        US[UnaryStreamMultiCallable]
        SU[StreamUnaryMultiCallable]
        SS[StreamStreamMultiCallable]
        
        MI[MethodImplementation]
        MMI[MultiMethodImplementation]
    end
    
    C -->|Determines| UM
    C -->|Determines| US
    C -->|Determines| SU
    C -->|Determines| SS
    
    S -->|Influences| MI
    S -->|Influences| MMI
    
    MI -->|Uses| C
    MMI -->|Uses| C
```

### Integration with Core gRPC Components

The enums defined in this module are extensively used throughout the gRPC core system:

1. **Method Registration**: When services are registered, their methods are classified using `Cardinality`
2. **Call Handling**: The framework uses cardinality to determine appropriate call handlers
3. **Interceptor Chains**: Interceptors use cardinality information to process requests correctly
4. **Service Implementation**: The `Service` enum guides how service methods should be implemented

### Data Flow Architecture

```mermaid
sequenceDiagram
    participant Client
    participant Framework
    participant Cardinality
    participant Service
    participant Server
    
    Client->>Framework: RPC Call
    Framework->>Cardinality: Determine Method Type
    Cardinality-->>Framework: UNARY_UNARY/etc
    Framework->>Service: Check Implementation Style
    Service-->>Framework: INLINE/EVENT
    Framework->>Server: Route to Appropriate Handler
    Server-->>Client: Response
```

## Dependencies and Relationships

### Upstream Dependencies

The `grpc_framework_common` module is a foundational component with no internal dependencies on other gRPC modules. It provides pure abstractions that are used by:

- [grpc_framework.md](grpc_framework.md) - Framework interfaces and foundation
- [grpc_core.md](grpc_core.md) - Core gRPC functionality
- [grpc_aio.md](grpc_aio.md) - Async I/O support

### Downstream Usage

```mermaid
graph BT
    subgraph "Dependent Modules"
        GC[grpc_core]
        GF[grpc_framework]
        GA[grpc_aio]
        GO[grpc_observability]
        GT[grpc_testing]
    end
    
    subgraph "grpc_framework_common"
        C[Cardinality]
        S[Service]
    end
    
    GC -->|uses| C
    GC -->|uses| S
    GF -->|uses| C
    GF -->|uses| S
    GA -->|uses| C
    GA -->|uses| S
    GO -->|uses| C
    GT -->|uses| C
```

## Process Flow

### Method Classification Process

```mermaid
flowchart TD
    Start[Service Definition] --> Parse[Parse Proto File]
    Parse --> Extract[Extract Method Signatures]
    Extract --> Analyze[Analyze Streaming Pattern]
    
    Analyze -->|Unary Request| CheckResponse1{Response Type}
    Analyze -->|Stream Request| CheckResponse2{Response Type}
    
    CheckResponse1 -->|Unary| SetUU[Set Cardinality:<br/>UNARY_UNARY]
    CheckResponse1 -->|Stream| SetUS[Set Cardinality:<br/>UNARY_STREAM]
    
    CheckResponse2 -->|Unary| SetSU[Set Cardinality:<br/>STREAM_UNARY]
    CheckResponse2 -->|Stream| SetSS[Set Cardinality:<br/>STREAM_STREAM]
    
    SetUU --> Register[Register Method Handler]
    SetUS --> Register
    SetSU --> Register
    SetSS --> Register
    
    Register --> DetermineStyle{Implementation Style}
    DetermineStyle -->|Simple| SetInline[Set Service:<br/>INLINE]
    DetermineStyle -->|Complex| SetEvent[Set Service:<br/>EVENT]
    
    SetInline --> End[Method Ready]
    SetEvent --> End
```

## Best Practices

### Using Cardinality

1. **Method Design**: Choose the appropriate cardinality based on your use case:
   - Use `UNARY_UNARY` for simple request-response operations
   - Use `UNARY_STREAM` for server-to-client data streaming
   - Use `STREAM_UNARY` for client-to-server data streaming
   - Use `STREAM_STREAM` for bidirectional real-time communication

2. **Performance Considerations**:
   - Streaming methods (`*_STREAM`) are more memory-efficient for large data transfers
   - Unary methods (`UNARY_*`) are simpler to implement and debug

### Using Service

1. **Implementation Style**:
   - Use `INLINE` for fast, synchronous operations
   - Use `EVENT` for operations that may take time or require asynchronous processing

2. **Error Handling**:
   - Inline services should handle errors immediately
   - Event services can implement complex error recovery mechanisms

## Summary

The `grpc_framework_common` module provides the essential building blocks for understanding and implementing gRPC services. By defining clear enumerations for streaming semantics and control flow patterns, it enables the framework to handle diverse RPC scenarios consistently and efficiently. These abstractions are fundamental to the entire gRPC ecosystem, influencing how services are defined, implemented, and executed across all supported programming languages and platforms.

The module's simplicity belies its importance - every gRPC method, from the simplest unary call to the most complex bidirectional streaming scenario, is classified and handled according to the patterns defined in this foundational module.