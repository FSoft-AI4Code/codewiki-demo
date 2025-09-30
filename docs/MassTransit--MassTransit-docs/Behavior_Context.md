# Behavior Context Module

## Overview

The Behavior Context module is a core component of MassTransit's Saga State Machine implementation, providing the execution context for state machine behaviors and activities. It serves as the bridge between the state machine engine and the business logic that processes events within saga instances.

## Purpose and Core Functionality

The Behavior Context module provides:

- **Execution Context**: Encapsulates the runtime environment for state machine behaviors, including the saga instance, current event, and state machine reference
- **Event Processing**: Enables raising new events and creating contextual proxies for event handling
- **Message Initialization**: Provides message initialization capabilities for creating new messages within behaviors
- **Exception Handling**: Supports exceptional contexts for error scenarios and compensation activities
- **State Management**: Integrates with saga lifecycle management, including completion tracking

## Architecture and Component Relationships

### Core Components

```mermaid
graph TB
    subgraph "Behavior Context Module"
        BC["BehaviorContext<TSaga>"]
        BCM["BehaviorContext<TSaga, TMessage>"]
        BEC["BehaviorExceptionContext<TSaga, TException>"]
        BECM["BehaviorExceptionContext<TSaga, TMessage, TException>"]
        UEC["UnhandledEventContext<TSaga>"]
        
        BC --> BCM
        BC --> BEC
        BCM --> BECM
        BC --> UEC
    end
    
    SCC["SagaConsumeContext<TSaga>"] --> BC
    SM["StateMachine<TSaga>"] --> BC
    EV["Event"] --> BC
    
    style BC fill:#e1f5fe
    style BCM fill:#e1f5fe
    style BEC fill:#fff3e0
    style BECM fill:#fff3e0
    style UEC fill:#fce4ec
```

### Implementation Hierarchy

```mermaid
graph TB
    subgraph "Implementation Layer"
        BCP["BehaviorContextProxy"]
        BCPM["BehaviorContextProxy<TMessage>"]
        BEP["BehaviorExceptionContextProxy<TException>"]
        BEPM["BehaviorExceptionContextProxy<TData, TException>"]
        UEBC["UnhandledEventBehaviorContext"]
    end
    
    subgraph "Interface Layer"
        BC["BehaviorContext<TSaga>"]
        BCM["BehaviorContext<TSaga, TMessage>"]
        BEC["BehaviorExceptionContext<TSaga, TException>"]
        BECM["BehaviorExceptionContext<TSaga, TMessage, TException>"]
        UEC["UnhandledEventContext<TSaga>"]
    end
    
    BCP -.->|implements| BC
    BCPM -.->|implements| BCM
    BEP -.->|implements| BEC
    BEPM -.->|implements| BECM
    UEBC -.->|implements| UEC
    
    BCP --> BCPM
    BCP --> BEP
    BCPM --> BEPM
    BCP --> UEBC
```

## Key Interfaces and Their Roles

### BehaviorContext<TSaga>
The primary interface that provides:
- Access to the state machine instance
- Current event information
- Event raising capabilities
- Message initialization
- Context proxy creation

### BehaviorContext<TSaga, TMessage>
Extends the base behavior context with:
- Typed message access
- Strongly-typed event handling
- Message-specific operations

### BehaviorExceptionContext<TSaga, TException>
Handles exceptional scenarios by providing:
- Exception information within the behavior context
- Maintains state machine context during error handling
- Enables compensation activities

### UnhandledEventContext<TSaga>
Manages unhandled events with:
- Current state information
- Options to ignore or throw on unhandled events
- Graceful degradation capabilities

## Data Flow and Process Flows

### Event Processing Flow

```mermaid
sequenceDiagram
    participant SM as StateMachine
    participant BC as BehaviorContext
    participant S as SagaInstance
    participant B as Behavior
    
    SM->>BC: Create context with event
    BC->>S: Access saga data
    BC->>B: Execute behavior
    B->>BC: Process event
    alt Raise new event
        B->>BC: Raise(event)
        BC->>SM: RaiseEvent(context)
        SM->>BC: Create new context
    end
    BC->>SM: Return result
```

### Exception Handling Flow

```mermaid
sequenceDiagram
    participant BC as BehaviorContext
    participant BEC as BehaviorExceptionContext
    participant EH as ExceptionHandler
    participant SM as StateMachine
    
    BC->>BC: Exception occurs
    BC->>BEC: Create exception context
    BEC->>EH: Handle exception
    alt Compensation needed
        EH->>BEC: Create compensation context
        BEC->>SM: Execute compensation
    end
    EH->>BC: Return result
```

## Integration with Other Modules

### Dependencies on Core Modules

```mermaid
graph LR
    BC["Behavior_Context"]
    CA["Core_Abstractions"]
    SSM["Saga_StateMachine_Core"]
    MC["Middleware_Core"]
    
    BC -->|uses| CA
    BC -->|extends| SSM
    BC -->|integrates| MC
    
    CA -->|provides| SCC["SagaConsumeContext"]
    CA -->|provides| EV["Event"]
    SSM -->|provides| SM["StateMachine"]
    SSM -->|provides| SI["SagaStateMachineInstance"]
```

### Key Dependencies

- **[Core_Abstractions](Core_Abstractions.md)**: Provides foundational interfaces like `SagaConsumeContext`, `ConsumeContext`, and `Event`
- **[Saga_StateMachine_Core](Saga_StateMachine_Core.md)**: Supplies the `StateMachine` interface and saga instance abstractions
- **[Middleware_Core](Middleware_Core.md)**: Integrates with the middleware pipeline for message processing

## Usage Patterns and Best Practices

### Basic Behavior Implementation
```csharp
public class MyBehavior : IBehavior<MySaga, MyMessage>
{
    public async Task Execute(BehaviorContext<MySaga, MyMessage> context)
    {
        // Access saga instance
        var saga = context.Saga;
        
        // Access message data
        var message = context.Message;
        
        // Raise new events
        await context.Raise(new MyEvent());
        
        // Initialize new messages
        var sendTuple = await context.Init<OtherMessage>(new { Property = value });
    }
}
```

### Exception Handling
```csharp
public async Task Faulted<TException>(BehaviorExceptionContext<MySaga, MyMessage, TException> context)
    where TException : Exception
{
    // Access exception
    var exception = context.Exception;
    
    // Handle compensation
    await context.Raise(new CompensationEvent());
}
```

### Unhandled Event Management
```csharp
public async Task Unhandled(UnhandledEventContext<MySaga> context)
{
    // Check current state
    var currentState = context.CurrentState;
    
    // Choose to ignore or throw
    if (ShouldIgnore(context.Event))
        await context.Ignore();
    else
        await context.Throw();
}
```

## Advanced Features

### Context Proxy Creation
The module supports creating proxy contexts for:
- Event forwarding and transformation
- Nested event processing
- Message enrichment before processing

### Message Initialization
Provides type-safe message initialization with:
- Object mapping capabilities
- Header preservation
- Correlation ID management

### State Machine Integration
Tight integration with the state machine engine enables:
- Event raising within behaviors
- State transition management
- Saga lifecycle control

## Performance Considerations

- **Context Pooling**: Proxy contexts are designed for efficient creation and disposal
- **Memory Efficiency**: Minimal overhead in context creation and proxy operations
- **Async Operations**: All operations support async/await patterns for scalability

## Error Handling and Resilience

The module provides comprehensive error handling through:
- Exception context propagation
- Compensation activity support
- Unhandled event management
- Graceful degradation options

## Testing and Debugging

Behavior contexts support testing through:
- Mock context creation
- Event simulation
- Exception scenario testing
- State verification

## References

- [Core_Abstractions](Core_Abstractions.md) - Foundation interfaces and base contracts
- [Saga_StateMachine_Core](Saga_StateMachine_Core.md) - State machine engine and saga management
- [Middleware_Core](Middleware_Core.md) - Message processing pipeline integration