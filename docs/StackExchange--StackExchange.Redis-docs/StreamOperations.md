# StreamOperations Module Documentation

## Overview

The StreamOperations module provides comprehensive Redis Stream functionality for the StackExchange.Redis client library. It implements Redis Streams commands for event sourcing, message queuing, and real-time data processing scenarios. The module handles both single-stream and multi-stream operations, consumer group management, and stream trimming capabilities.

## Purpose and Core Functionality

StreamOperations enables developers to:
- Implement event-driven architectures using Redis Streams
- Create producer-consumer patterns with reliable message delivery
- Manage consumer groups for scalable stream processing
- Perform stream trimming and maintenance operations
- Handle both synchronous and asynchronous stream operations

## Architecture

### Component Structure

```mermaid
graph TB
    subgraph "StreamOperations Module"
        A[SingleStreamReadCommandMessage]
        B[SingleStreamReadGroupCommandMessage]
        C[MultiStreamReadCommandMessage]
        D[MultiStreamReadGroupCommandMessage]
    end
    
    subgraph "Message System"
        E[Message Base]
        F[CommandMessage]
        G[PhysicalConnection]
    end
    
    subgraph "Result Processing"
        H[SingleStreamProcessor]
        I[MultiStreamProcessor]
        J[StreamInfoProcessor]
    end
    
    subgraph "Database Operations"
        K[RedisDatabase]
        L[RedisBase]
        M[ExecuteSync/Async]
    end
    
    A --> E
    B --> E
    C --> E
    D --> E
    
    E --> F
    F --> G
    
    A --> H
    B --> H
    C --> I
    D --> I
    
    K --> A
    K --> B
    K --> C
    K --> D
    
    K --> L
    L --> M
```

### Core Components

#### 1. Stream Command Messages

The module implements specialized message classes for different stream operations:

**SingleStreamReadCommandMessage**
- Handles `XREAD` operations for single streams
- Manages stream positioning and count parameters
- Supports both blocking and non-blocking reads

**SingleStreamReadGroupCommandMessage**
- Implements `XREADGROUP` for consumer group operations
- Manages consumer group names and consumer identities
- Handles message acknowledgment tracking

**MultiStreamReadCommandMessage**
- Processes multiple streams in a single `XREAD` operation
- Coordinates stream positions across multiple keys
- Optimizes network round-trips for bulk operations

**MultiStreamReadGroupCommandMessage**
- Extends consumer group functionality to multiple streams
- Manages complex consumer group scenarios
- Handles cross-stream message ordering

#### 2. Stream Position Management

```mermaid
sequenceDiagram
    participant Client
    participant StreamOps
    participant Redis
    
    Client->>StreamOps: StreamRead(key, position)
    StreamOps->>StreamOps: ResolvePosition(position)
    StreamOps->>Redis: XREAD STREAMS key position
    Redis-->>StreamOps: Stream entries
    StreamOps-->>Client: StreamEntry[]
    
    Client->>StreamOps: StreamReadGroup(key, group, consumer)
    StreamOps->>StreamOps: ResolveGroupPosition(group)
    StreamOps->>Redis: XREADGROUP GROUP group consumer STREAMS key position
    Redis-->>StreamOps: Stream entries for consumer
    StreamOps-->>Client: StreamEntry[]
```

## Data Flow Architecture

### Stream Read Operations

```mermaid
flowchart LR
    A[Client Request] --> B{Operation Type}
    B -->|Single Stream| C[SingleStreamReadCommandMessage]
    B -->|Multi Stream| D[MultiStreamReadCommandMessage]
    B -->|Consumer Group| E[SingleStreamReadGroupCommandMessage]
    B -->|Multi Group| F[MultiStreamReadGroupCommandMessage]
    
    C --> G[Message Creation]
    D --> G
    E --> G
    F --> G
    
    G --> H[PhysicalConnection.Write]
    H --> I[Redis Server]
    I --> J[RawResult]
    J --> K[ResultProcessor]
    K --> L[StreamEntry Array]
    L --> M[Client Response]
```

### Stream Write Operations

```mermaid
flowchart TD
    A[StreamAdd Request] --> B[Parameter Validation]
    B --> C{Message Type}
    C -->|Single Field| D[XADD with field/value]
    C -->|Multiple Fields| E[XADD with NameValueEntry Array]
    C -->|With Trimming| F[XADD with MAXLEN/MINID]
    
    D --> G[Message Creation]
    E --> G
    F --> G
    
    G --> H[Stream Trimming Logic]
    H --> I[PhysicalConnection.Write]
    I --> J[Redis Server]
    J --> K[Message ID]
    K --> L[Client Response]
```

## Key Features

### 1. Consumer Group Management

The module provides comprehensive consumer group functionality:

```mermaid
graph TB
    A[StreamCreateConsumerGroup] --> B[XGROUP CREATE]
    C[StreamConsumerGroupSetPosition] --> D[XGROUP SETID]
    E[StreamDeleteConsumerGroup] --> F[XGROUP DESTROY]
    G[StreamDeleteConsumer] --> H[XGROUP DELCONSUMER]
    
    I[StreamReadGroup] --> J[XREADGROUP]
    K[StreamAcknowledge] --> L[XACK]
    M[StreamPending] --> N[XPENDING]
    O[StreamAutoClaim] --> P[XAUTOCLAIM]
```

### 2. Stream Trimming and Maintenance

```mermaid
flowchart LR
    A[StreamTrim] --> B[XTRIM MAXLEN]
    C[StreamTrimByMinId] --> D[XTRIM MINID]
    E[StreamDelete] --> F[XDEL]
    G[StreamLength] --> H[XLEN]
    
    I[StreamInfo] --> J[XINFO STREAM]
    K[StreamGroupInfo] --> L[XINFO GROUPS]
    M[StreamConsumerInfo] --> N[XINFO CONSUMERS]
```

### 3. Advanced Stream Operations

- **Stream Range Queries**: `XRANGE` and `XREVRANGE` for historical data access
- **Pending Message Management**: `XPENDING` for monitoring unacknowledged messages
- **Message Claiming**: `XCLAIM` and `XAUTOCLAIM` for handling consumer failures
- **Stream Acknowledgment**: `XACK` for confirming message processing

## Integration with System Architecture

### Connection to DatabaseOperations

```mermaid
graph LR
    A[StreamOperations] --> B[RedisDatabase]
    C[RedisDatabase] --> D[ConnectionMultiplexer]
    D --> E[PhysicalBridge]
    E --> F[PhysicalConnection]
    
    G[Message Creation] --> H[Command Processing]
    H --> I[Server Selection]
    I --> J[Connection Pool]
    J --> K[Redis Server]
```

### Result Processing Pipeline

```mermaid
sequenceDiagram
    participant StreamOps
    participant Message
    participant PhysicalConnection
    participant Redis
    participant ResultProcessor
    
    StreamOps->>Message: Create Command Message
    Message->>PhysicalConnection: Write to Connection
    PhysicalConnection->>Redis: Send Command
    Redis-->>PhysicalConnection: Return RawResult
    PhysicalConnection-->>Message: Process Response
    Message-->>ResultProcessor: Parse Result
    ResultProcessor-->>StreamOps: Return Typed Result
```

## Dependencies

### Internal Dependencies

- **[ConnectionManagement](ConnectionManagement.md)**: Provides connection pooling and server selection
- **[MessageSystem](MessageSystem.md)**: Base message infrastructure and protocol handling
- **[ResultProcessing](ResultProcessing.md)**: Specialized processors for stream data types
- **[ValueTypes](ValueTypes.md)**: Stream-specific data types (StreamEntry, StreamPosition, etc.)

### External Dependencies

- **Redis Server**: Requires Redis 5.0+ for full stream functionality
- **PhysicalConnection**: Low-level network communication layer
- **ServerSelectionStrategy**: Intelligent server routing for cluster scenarios

## Usage Patterns

### Basic Stream Operations

```csharp
// Add messages to stream
var messageId = db.StreamAdd("mystream", "field1", "value1");

// Read from stream
var entries = db.StreamRead("mystream", StreamPosition.Beginning);

// Create consumer group
db.StreamCreateConsumerGroup("mystream", "mygroup", StreamPosition.NewMessages);

// Read as consumer
var groupEntries = db.StreamReadGroup("mystream", "mygroup", "consumer1");

// Acknowledge messages
db.StreamAcknowledge("mystream", "mygroup", messageId);
```

### Advanced Stream Processing

```csharp
// Multi-stream reading
var streams = db.StreamRead(new[] {
    new StreamPosition("stream1", position1),
    new StreamPosition("stream2", position2)
});

// Consumer group with multiple streams
var groupStreams = db.StreamReadGroup(
    new[] {
        new StreamPosition("stream1", StreamPosition.NewMessages),
        new StreamPosition("stream2", StreamPosition.NewMessages)
    },
    "mygroup", "consumer1"
);

// Stream trimming with limits
db.StreamTrim("mystream", 1000, useApproximateMaxLength: true, limit: 100);
```

## Performance Considerations

### Message Batching
- Multi-stream operations reduce network round-trips
- Batch acknowledgment improves throughput
- Stream trimming with limits prevents blocking operations

### Memory Management
- Stream entry parsing uses array pooling
- Large stream reads support pagination via count parameters
- Automatic connection management prevents resource leaks

### Cluster Support
- Stream operations respect Redis Cluster slot allocation
- Multi-stream operations require same-slot keys
- Consumer groups work across cluster nodes

## Error Handling

### Common Exceptions
- `RedisServerException`: Stream doesn't exist, invalid message IDs
- `ArgumentException`: Invalid parameters, wrong operation sequence
- `TimeoutException`: Blocking operations exceeding timeout

### Recovery Patterns
- Consumer group recreation on `BUSYGROUP` errors
- Stream creation with `MkStream` flag
- Position validation before read operations

## Best Practices

1. **Consumer Group Design**: Use meaningful group names and consumer identifiers
2. **Message Acknowledgment**: Always acknowledge processed messages to prevent redelivery
3. **Stream Trimming**: Implement appropriate retention policies to manage memory
4. **Error Handling**: Handle consumer failures with auto-claim mechanisms
5. **Monitoring**: Use `XPENDING` and stream info commands for operational visibility

## Related Documentation

- [DatabaseOperations](DatabaseOperations.md) - General database operation patterns
- [ConnectionManagement](ConnectionManagement.md) - Connection and server management
- [ResultProcessing](ResultProcessing.md) - Stream-specific result processors
- [APIValueTypes](APIValueTypes.md) - Stream data structures and types