# IRequestClient Module Documentation

## Overview

The `IRequestClient` module is a core component of MassTransit that provides a powerful and flexible way to implement the Request-Response messaging pattern in distributed systems. It enables applications to send requests and receive responses asynchronously, with built-in support for multiple response types, timeouts, and error handling.

## Purpose and Core Functionality

The `IRequestClient` module serves as the primary abstraction for implementing synchronous-style communication patterns over asynchronous messaging infrastructure. It provides:

- **Request-Response Pattern**: Send a request message and receive one or more response messages
- **Multiple Response Types**: Support for handling different response types from a single request
- **Timeout Management**: Configurable timeouts for request completion
- **Cancellation Support**: Full cancellation token support for request cancellation
- **Message Initialization**: Support for object-based message initialization
- **Pipe Configuration**: Extensible pipeline for request customization

## Architecture and Component Relationships

### Core Components

```mermaid
graph TB
    subgraph "IRequestClient Module"
        IRequestClient["IRequestClient&lt;TRequest&gt;"]
        RequestHandle["RequestHandle&lt;TRequest&gt;"]
        Response["Response&lt;T&gt;"]
        RequestTimeout["RequestTimeout"]
        IRequestPipeConfigurator["IRequestPipeConfigurator&lt;TRequest&gt;"]
    end
    
    subgraph "MassTransit Core"
        SendContext["SendContext&lt;T&gt;"]
        ConsumeContext["ConsumeContext"]
        MessageContext["MessageContext"]
        IPipe["IPipe&lt;T&gt;"]
    end
    
    subgraph "Transport Layer"
        ISendEndpoint["ISendEndpoint"]
        IReceiveEndpoint["IReceiveEndpoint"]
    end
    
    IRequestClient --> RequestHandle
    RequestHandle --> Response
    RequestHandle --> IRequestPipeConfigurator
    RequestHandle --> SendContext
    Response --> MessageContext
    IRequestPipeConfigurator --> IPipe
    SendContext --> ISendEndpoint
    
    style IRequestClient fill:#e1f5fe
    style RequestHandle fill:#e1f5fe
    style Response fill:#e1f5fe
```

### Implementation Components

```mermaid
graph TB
    subgraph "Implementation Layer"
        RequestClient["RequestClient&lt;TRequest&gt;"]
        ClientRequestHandle["ClientRequestHandle&lt;TRequest&gt;"]
        ClientFactory["ClientFactory"]
        MessageResponse["MessageResponse"]
    end
    
    subgraph "Request Sending"
        IRequestSendEndpoint["IRequestSendEndpoint&lt;TRequest&gt;"]
        SendRequestEndpoint["SendRequestSendEndpoint"]
        PublishRequestEndpoint["PublishRequestSendEndpoint"]
    end
    
    subgraph "Context & Configuration"
        ClientFactoryContext["ClientFactoryContext"]
        RequestPipeConfiguratorCallback["RequestPipeConfiguratorCallback&lt;T&gt;"]
    end
    
    RequestClient --> ClientRequestHandle
    RequestClient --> ClientFactoryContext
    ClientRequestHandle --> MessageResponse
    ClientFactory --> RequestClient
    RequestClient --> IRequestSendEndpoint
    IRequestSendEndpoint --> SendRequestEndpoint
    IRequestSendEndpoint --> PublishRequestEndpoint
    
    style RequestClient fill:#fff3e0
    style ClientRequestHandle fill:#fff3e0
    style ClientFactory fill:#fff3e0
```

## Data Flow and Request-Response Lifecycle

### Single Response Request Flow

```mermaid
sequenceDiagram
    participant App as Application
    participant RC as RequestClient
    participant RH as RequestHandle
    participant SE as SendEndpoint
    participant Bus as Message Bus
    participant Consumer as Service Consumer
    
    App->>RC: Create(requestMessage)
    RC->>RH: new ClientRequestHandle()
    RC->>App: Return RequestHandle
    
    App->>RH: GetResponse<T>()
    RH->>RH: Setup timeout timer
    RH->>SE: Send request with RequestId
    SE->>Bus: Publish/Send message
    Bus->>Consumer: Deliver request
    
    Consumer->>Consumer: Process request
    Consumer->>Bus: Send response
    Bus->>RH: Deliver response
    RH->>App: Return Response<T>
    
    Note over RH: Timeout or cancellation
    RH->>App: Throw RequestTimeoutException
```

### Multiple Response Request Flow

```mermaid
sequenceDiagram
    participant App as Application
    participant RC as RequestClient
    participant RH as RequestHandle
    participant SE as SendEndpoint
    participant Bus as Message Bus
    participant Consumer as Service Consumer
    
    App->>RC: GetResponse<T1, T2>()
    RC->>RH: Create handle for multiple responses
    RH->>SE: Send request
    SE->>Bus: Publish/Send message
    Bus->>Consumer: Deliver request
    
    Consumer->>Consumer: Process request
    alt Response Type 1
        Consumer->>Bus: Send T1 response
        Bus->>RH: Deliver T1 response
    else Response Type 2
        Consumer->>Bus: Send T2 response
        Bus->>RH: Deliver T2 response
    end
    
    RH->>App: Return Response<T1, T2>
    Note over App: Pattern match on response type
```

## Component Interactions

### Request Client Creation and Configuration

```mermaid
graph LR
    subgraph "Client Creation"
        Bus["IBus"]
        ClientFactory["ClientFactory"]
        RequestClient["RequestClient&lt;TRequest&gt;"]
        Context["ClientFactoryContext"]
    end
    
    subgraph "Endpoint Resolution"
        Convention["EndpointConvention"]
        SendEndpoint["IRequestSendEndpoint"]
        Address["Uri destinationAddress"]
    end
    
    Bus --> ClientFactory
    ClientFactory --> Context
    ClientFactory --> RequestClient
    RequestClient --> SendEndpoint
    Convention --> Address
    Address --> SendEndpoint
    
    style Bus fill:#f3e5f5
    style ClientFactory fill:#f3e5f5
    style RequestClient fill:#f3e5f5
```

### Request Handle State Management

```mermaid
stateDiagram-v2
    [*] --> Created: Create RequestHandle
    Created --> Sending: SendRequest() called
    Sending --> Waiting: Request sent
    Waiting --> ResponseReceived: Response received
    Waiting --> Timeout: Timeout expired
    Waiting --> Cancelled: Cancellation requested
    
    ResponseReceived --> [*]: Return response
    Timeout --> [*]: Throw RequestTimeoutException
    Cancelled --> [*]: Throw OperationCanceledException
    
    state Waiting {
        [*] --> SingleResponse: Single response expected
        [*] --> MultipleResponses: Multiple responses expected
        SingleResponse --> ResponseMatched: Response matched
        MultipleResponses --> AnyResponseMatched: Any response matched
    }
```

## Key Features and Capabilities

### 1. Multiple Response Type Support

The `IRequestClient` supports handling multiple response types from a single request:

```csharp
// Single response
Task<Response<OrderResult>> result = client.GetResponse<OrderResult>(request);

// Multiple responses - pattern matching
Task<Response<SuccessResult, ErrorResult>> result = client.GetResponse<SuccessResult, ErrorResult>(request);

// Three response types
Task<Response<SuccessResult, ValidationError, SystemError>> result = 
    client.GetResponse<SuccessResult, ValidationError, SystemError>(request);
```

### 2. Flexible Message Creation

Support for both strongly-typed messages and object initialization:

```csharp
// Strongly-typed message
var response = await client.GetResponse<Result>(new RequestMessage { Id = 123 });

// Object initialization
var response = await client.GetResponse<Result>(new { Id = 123, Name = "Test" });
```

### 3. Timeout and Cancellation

Built-in timeout management with cancellation support:

```csharp
// Default timeout (30 seconds)
var response = await client.GetResponse<Result>(request);

// Custom timeout
var response = await client.GetResponse<Result>(request, timeout: TimeSpan.FromSeconds(60));

// With cancellation token
var response = await client.GetResponse<Result>(request, cancellationToken: cts.Token);
```

### 4. Request Pipeline Configuration

Extensible pipeline for request customization:

```csharp
var response = await client.GetResponse<Result>(request, pipe =>
{
    pipe.UseExecute(context =>
    {
        // Customize send context
        context.Headers.Set("Custom-Header", "value");
    });
});
```

## Integration with MassTransit Ecosystem

### Relationship to Core Abstractions

- **[ConsumeContext](ConsumeContext.md)**: Provides the context for consuming responses
- **[SendContext](SendContext.md)**: Used to configure outgoing request messages
- **[MessageContext](MessageContext.md)**: Base context for all message operations
- **[IPipe](Middleware_Core.md)**: Pipeline abstraction for request/response processing

### Transport Integration

The `IRequestClient` integrates with various transport layers:

- **[ISendTransport](Transports_Core.md)**: For direct send operations
- **[IReceiveTransport](Transports_Core.md)**: For response reception
- **[PublishEndpoint](Transports_Core.md)**: For publish-based requests

### Error Handling Integration

- **[RequestException](Exceptions.md)**: Base exception for request failures
- **[RequestTimeoutException](Exceptions.md)**: Specific timeout handling
- **[Fault](Contracts.md)**: Standard fault message handling

## Configuration and Usage Patterns

### Basic Configuration

```csharp
services.AddMassTransit(cfg =>
{
    cfg.AddRequestClient<SubmitOrderRequest>();
});
```

### Custom Timeout Configuration

```csharp
services.AddMassTransit(cfg =>
{
    cfg.AddRequestClient<SubmitOrderRequest>(new RequestTimeout(TimeSpan.FromSeconds(45)));
});
```

### Destination Address Configuration

```csharp
services.AddMassTransit(cfg =>
{
    cfg.AddRequestClient<SubmitOrderRequest>(
        new Uri("queue:order-service"),
        RequestTimeout.Default);
});
```

## Process Flows

### Request-Response with Error Handling

```mermaid
flowchart TD
    Start([Application Start]) --> CreateClient[Create RequestClient]
    CreateClient --> SendRequest[Send Request]
    SendRequest --> WaitResponse{Wait for Response}
    
    WaitResponse -->|Success| ProcessResponse[Process Response]
    WaitResponse -->|Timeout| HandleTimeout[Handle Timeout]
    WaitResponse -->|Fault| HandleFault[Handle Fault]
    WaitResponse -->|Cancel| HandleCancel[Handle Cancellation]
    
    ProcessResponse --> Complete([Complete])
    HandleTimeout --> LogError[Log Timeout Error]
    HandleFault --> LogFault[Log Fault Error]
    HandleCancel --> LogCancel[Log Cancellation]
    
    LogError --> Retry{Retry?}
    LogFault --> Retry
    LogCancel --> Retry
    
    Retry -->|Yes| SendRequest
    Retry -->|No| Failed([Failed])
    
    style Start fill:#e8f5e8
    style Complete fill:#e8f5e8
    style Failed fill:#ffe8e8
```

### Advanced Request Pattern with Multiple Services

```mermaid
flowchart LR
    subgraph "Client Application"
        RC[RequestClient]
        FH[RequestHandle]
    end
    
    subgraph "Service Discovery"
        EC[EndpointConvention]
        SD[Service Discovery]
    end
    
    subgraph "Backend Services"
        S1[Order Service]
        S2[Inventory Service]
        S3[Payment Service]
    end
    
    RC --> EC
    EC --> SD
    SD --> S1
    SD --> S2
    SD --> S3
    
    FH -->|Request| S1
    S1 -->|Response| FH
    
    style RC fill:#e3f2fd
    style FH fill:#e3f2fd
```

## Best Practices

### 1. Request Design

- Keep request messages focused and cohesive
- Use meaningful message names that describe the intent
- Include all necessary data in the request to avoid chatty interactions

### 2. Response Design

- Design responses to be self-descriptive
- Use multiple response types for different success/error scenarios
- Include correlation IDs for tracking

### 3. Timeout Configuration

- Set appropriate timeouts based on expected processing time
- Use shorter timeouts for user-facing operations
- Consider circuit breaker patterns for cascading failures

### 4. Error Handling

- Always handle `RequestTimeoutException`
- Implement retry policies for transient failures
- Use structured logging for request tracking

## Testing Considerations

The `IRequestClient` module integrates with MassTransit's testing framework:

- **[InMemoryTestHarness](Testing_Core.md)**: For unit testing request-response scenarios
- **[IConsumerTestHarness](Testing_Core.md)**: For testing consumer responses
- **[IBusTestHarness](Testing_Core.md)**: For integration testing

## Performance Characteristics

- **Async/Await**: Fully asynchronous implementation
- **Memory Efficient**: Uses struct-based response types for multiple responses
- **Timeout Management**: Efficient timer-based timeout handling
- **Connection Pooling**: Integrates with transport connection pooling

## Summary

The `IRequestClient` module provides a robust foundation for implementing request-response patterns in distributed systems. Its flexible design supports various messaging scenarios while maintaining strong type safety and excellent performance characteristics. The module's integration with MassTransit's broader ecosystem makes it an essential component for building reliable, scalable distributed applications.