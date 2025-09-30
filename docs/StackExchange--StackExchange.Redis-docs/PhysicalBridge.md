# PhysicalBridge Module Documentation

## Introduction

The PhysicalBridge module serves as a critical intermediary layer in the StackExchange.Redis connection management system, managing the communication bridge between the logical connection layer and the actual physical TCP connections to Redis servers. It handles connection state management, message queuing, write coordination, and connection health monitoring.

## Core Purpose

PhysicalBridge acts as a sophisticated traffic controller that:
- Manages the lifecycle of physical TCP connections to Redis servers
- Coordinates message writing through a single-writer mutex to prevent message reordering
- Implements intelligent message queuing and backlog processing
- Provides connection health monitoring and automatic reconnection capabilities
- Handles different connection types (Interactive and Subscription) with specialized behaviors

## Architecture Overview

```mermaid
graph TB
    subgraph "PhysicalBridge Architecture"
        PB[PhysicalBridge]
        PC[PhysicalConnection]
        SEP[ServerEndPoint]
        CM[ConnectionMultiplexer]
        MSG[Message]
        
        CM -->|manages| PB
        PB -->|wraps| PC
        PB -->|belongs to| SEP
        PB -->|processes| MSG
        
        subgraph "Connection States"
            CS1[Connecting]
            CS2[ConnectedEstablishing]
            CS3[ConnectedEstablished]
            CS4[Disconnected]
        end
        
        PB -.->|manages| CS1
        PB -.->|manages| CS2
        PB -.->|manages| CS3
        PB -.->|manages| CS4
    end
```

## Component Relationships

```mermaid
graph LR
    subgraph "Connection Management Ecosystem"
        CM[ConnectionMultiplexer]
        PB[PhysicalBridge]
        PC[PhysicalConnection]
        SEP[ServerEndPoint]
        MSG[Message Queue]
        
        CM -->|creates| PB
        CM -->|coordinates| PB
        PB -->|owns| PC
        PB -->|reports to| SEP
        PB -->|manages| MSG
        
        subgraph "Message Flow"
            direction TB
            APP[Application]
            CM
            PB
            PC
            REDIS[Redis Server]
            
            APP -->|sends| CM
            CM -->|routes| PB
            PB -->|writes| PC
            PC -->|sends| REDIS
        end
    end
```

## Core Components

### PhysicalBridge Class

The main bridge implementation that coordinates all connection activities:

```mermaid
classDiagram
    class PhysicalBridge {
        -string Name
        -PhysicalConnection physical
        -ConcurrentQueue~Message~ _backlog
        -int state
        -SemaphoreSlim _singleWriterMutex
        -long operationCount
        -DateTime? ConnectedAt
        +TryWriteSync(Message, bool)
        +TryWriteAsync(Message, bool, bool)
        +OnConnectedAsync(PhysicalConnection, ILogger)
        +OnDisconnected(ConnectionFailureType, PhysicalConnection, bool, State)
        +OnHeartbeat(bool)
        +TryConnect(ILogger)
        -ProcessBacklog()
        -WriteMessageInsideLock(PhysicalConnection, Message)
    }
```

### BridgeStatus Structure

Provides comprehensive status information about the bridge state:

```mermaid
classDiagram
    class BridgeStatus {
        +int MessagesSinceLastHeartbeat
        +DateTime? ConnectedAt
        +bool IsWriterActive
        +BacklogStatus BacklogStatus
        +int BacklogMessagesPending
        +int BacklogMessagesPendingCounter
        +long TotalBacklogMessagesQueued
        +PhysicalConnection.ConnectionStatus Connection
        +ToString() string
    }
```

## Connection State Management

The PhysicalBridge implements a sophisticated state machine with the following states:

```mermaid
stateDiagram-v2
    [*] --> Disconnected: Initialize
    Disconnected --> Connecting: TryConnect()
    Connecting --> ConnectedEstablishing: TCP Connected
    ConnectedEstablishing --> ConnectedEstablished: Handshake Complete
    ConnectedEstablishing --> Disconnected: Connection Failed
    ConnectedEstablished --> Disconnected: Connection Lost
    Connecting --> Disconnected: Timeout/Failure
    Disconnected --> [*]: Dispose
    
    note right of ConnectedEstablished : Normal operational state
    note right of Connecting : Attempting TCP connection
    note right of ConnectedEstablishing : TCP connected, completing Redis handshake
```

## Message Flow Architecture

### Write Coordination

The PhysicalBridge implements a sophisticated single-writer pattern to prevent message reordering:

```mermaid
sequenceDiagram
    participant App as Application
    participant CM as ConnectionMultiplexer
    participant PB as PhysicalBridge
    participant PC as PhysicalConnection
    participant Redis as Redis Server
    
    App->>CM: Send Message
    CM->>PB: TryWriteAsync()
    
    alt Connection Available
        PB->>PB: Try Single Writer Lock
        alt Lock Acquired
            PB->>PC: WriteMessageInsideLock()
            PC->>Redis: Send Data
            PB->>PB: Release Lock
            PB->>App: Success
        else Lock Not Available
            PB->>PB: Queue to Backlog
            PB->>App: Queued
            PB->>PB: StartBacklogProcessor()
        end
    else Connection Not Available
        PB->>PB: Queue to Backlog
        PB->>App: Queued
    end
```

### Backlog Processing

The backlog system ensures message delivery during connection issues:

```mermaid
flowchart TD
    Start([Message Received]) --> CheckConnection{Connection Available?}
    CheckConnection -->|Yes| TryLock{Try Single Writer Lock}
    CheckConnection -->|No| QueueBacklog[Queue to Backlog]
    
    TryLock -->|Success| WriteDirect[Write Directly]
    TryLock -->|Failure| QueueBacklog
    
    QueueBacklog --> StartProcessor{Backlog Processor Running?}
    StartProcessor -->|No| StartBacklogProcessor[Start Backlog Processor]
    StartProcessor -->|Yes| ReturnQueued[Return Queued Status]
    StartBacklogProcessor --> ReturnQueued
    
    WriteDirect --> ReturnSuccess[Return Success]
    ReturnQueued --> End([End])
    ReturnSuccess --> End
```

## Connection Health Monitoring

### Heartbeat System

The PhysicalBridge implements comprehensive health monitoring:

```mermaid
flowchart LR
    Heartbeat[OnHeartbeat Triggered] --> CheckState{Check Connection State}
    
    CheckState -->|Connecting| CheckTimeout{Connection Timeout?}
    CheckState -->|Connected| CheckIdle{Connection Idle?}
    CheckState -->|Disconnected| TryReconnect{Retry Due?}
    
    CheckTimeout -->|Yes| AbortConnect[Abort & Retry]
    CheckTimeout -->|No| EndHeartbeat[End Heartbeat]
    
    CheckIdle -->|Yes| SendKeepAlive[Send Keep-Alive]
    CheckIdle -->|No| CheckConfig{Config Check Due?}
    
    SendKeepAlive --> EndHeartbeat
    CheckConfig -->|Yes| CheckReplication[Check Replication]
    CheckConfig -->|No| EndHeartbeat
    
    TryReconnect -->|Yes| AttemptReconnect[Attempt Reconnect]
    TryReconnect -->|No| EndHeartbeat
    
    AbortConnect --> EndHeartbeat
    CheckReplication --> EndHeartbeat
    AttemptReconnect --> EndHeartbeat
```

### Keep-Alive Mechanisms

Different connection types use different keep-alive strategies:

- **Interactive Connections**: Use tracer messages (ECHO with unique ID)
- **Subscription Connections**: Use PING commands or UNSUBSCRIBE on unique channels

## Error Handling and Recovery

### Connection Failure Handling

```mermaid
flowchart TD
    Failure[Connection Failure Detected] --> DetermineType{Determine Failure Type}
    
    DetermineType -->|UnableToConnect| HandleConnectFail[Handle Connect Failure]
    DetermineType -->|SocketFailure| HandleSocketFail[Handle Socket Failure]
    DetermineType -->|ProtocolFailure| HandleProtocolFail[Handle Protocol Failure]
    
    HandleConnectFail --> IncrementRetry[Increment Retry Count]
    HandleSocketFail --> CleanupSocket[Cleanup Socket]
    HandleProtocolFail --> ResetState[Reset Connection State]
    
    IncrementRetry --> CheckRetryPolicy{Retry Policy Met?}
    CleanupSocket --> TryImmediateReconnect[Try Immediate Reconnect]
    ResetState --> TryImmediateReconnect
    
    CheckRetryPolicy -->|Yes| ScheduleReconnect[Schedule Reconnect]
    CheckRetryPolicy -->|No| WaitNextHeartbeat[Wait for Next Heartbeat]
    
    ScheduleReconnect --> WaitNextHeartbeat
    TryImmediateReconnect --> WaitNextHeartbeat
```

### Backlog Timeout Management

Messages in the backlog are automatically timed out based on configured timeouts:

```mermaid
flowchart LR
    ProcessBacklog[Process Backlog] --> CheckTimeouts[Check for Timeouts]
    CheckTimeouts --> PeekMessage[Peek at Head Message]
    PeekMessage --> HasTimeout{Message Timed Out?}
    
    HasTimeout -->|Yes| RemoveMessage[Remove from Queue]
    HasTimeout -->|No| ProcessRemaining[Process Remaining]
    
    RemoveMessage --> CompleteWithTimeout[Complete with Timeout Exception]
    CompleteWithTimeout --> PeekMessage
    ProcessRemaining --> TryWrite[Try Write Messages]
```

## Integration with Other Modules

### ConnectionMultiplexer Integration

The PhysicalBridge works closely with the [ConnectionMultiplexer](ConnectionMultiplexer.md) for:
- Connection lifecycle management
- Message routing and load balancing
- Error reporting and event handling
- Configuration management

### ServerEndPoint Integration

Each PhysicalBridge is associated with a [ServerEndPoint](ServerEndPoint.md) that provides:
- Server-specific configuration
- Feature detection and capability management
- Replication and topology information
- Health status and statistics

### PhysicalConnection Integration

The bridge manages the underlying [PhysicalConnection](PhysicalConnection.md) which handles:
- Raw TCP socket communication
- Protocol encoding and decoding
- SSL/TLS encryption
- Low-level connection health monitoring

## Performance Characteristics

### Single-Writer Coordination

The PhysicalBridge uses a single-writer mutex to prevent message reordering while maintaining high throughput:

- **Instantaneous Lock Acquisition**: Messages write directly when possible
- **Backlog Queuing**: Messages queue when lock is contested
- **Dedicated Backlog Processor**: Background thread processes queued messages
- **Timeout Management**: Automatic timeout of stale messages

### Memory Management

- **ConcurrentQueue**: Lock-free message queuing
- **Interlocked Operations**: Thread-safe counters without locks
- **Message Reuse**: Efficient message lifecycle management
- **Backlog Limiter**: Prevents unbounded memory growth

## Configuration Options

The PhysicalBridge behavior is controlled through several configuration options:

- **TimeoutMilliseconds**: Write operation timeout
- **BacklogPolicy**: Message queuing behavior when disconnected
- **HeartbeatConsistencyChecks**: Enable aggressive keep-alive checks
- **HighIntegrity**: Enable message integrity tracking

## Thread Safety

The PhysicalBridge is designed for high-concurrency scenarios:

- **Single Writer Guarantee**: Prevents message reordering
- **Lock-Free Operations**: Uses interlocked operations where possible
- **Thread-Safe State Changes**: Atomic state transitions
- **Concurrent Backlog Processing**: Safe message queuing and processing

## Monitoring and Diagnostics

### Status Reporting

The BridgeStatus structure provides comprehensive diagnostics:

- Connection state and timing information
- Backlog queue statistics
- Writer activity status
- Underlying connection health

### Performance Counters

The PhysicalBridge tracks various performance metrics:

- Operation count and rate
- Socket connection count
- Active writer count
- Non-preferred endpoint usage

### Storm Logging

Comprehensive logging for connection issues including:
- Connection failure details
- Message backlog status
- Performance snapshots
- Error context information

## Best Practices

### Connection Management

1. **Allow Automatic Reconnection**: Let the bridge handle connection failures
2. **Configure Appropriate Timeouts**: Balance between responsiveness and reliability
3. **Monitor Backlog Status**: Watch for queue growth indicating connection issues
4. **Use Connection Types Appropriately**: Interactive vs Subscription connections

### Error Handling

1. **Handle WriteResult Values**: Check return values from write operations
2. **Monitor Connection Events**: Subscribe to connection failure events
3. **Configure Retry Policies**: Set appropriate reconnection retry behavior
4. **Use Backlog Policies**: Configure message queuing behavior during disconnections

### Performance Optimization

1. **Batch Operations**: Use batching to reduce lock contention
2. **Monitor Queue Depths**: Watch backlog queue sizes
3. **Tune Timeouts**: Set appropriate timeouts for your network conditions
4. **Use Fire-and-Forget Judiciously**: Balance performance vs reliability needs