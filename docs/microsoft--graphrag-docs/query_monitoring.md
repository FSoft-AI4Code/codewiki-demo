# Query Monitoring Module

## Introduction

The query_monitoring module provides a callback-based monitoring system for tracking and observing query execution within the GraphRAG system. It serves as the primary mechanism for monitoring query operations, context building, and language model interactions during the search and retrieval process.

## Architecture Overview

The query_monitoring module implements the `QueryCallbacks` class, which extends `BaseLLMCallback` to provide comprehensive monitoring capabilities for query execution workflows. This module acts as a bridge between the query system and the broader callback infrastructure, enabling real-time observation and logging of query operations.

```mermaid
graph TB
    subgraph "Query Monitoring Module"
        QC[QueryCallbacks]
    end
    
    subgraph "LLM Integration"
        BLC[BaseLLMCallback]
    end
    
    subgraph "Query System"
        BS[BaseSearch]
        LS[LocalSearch]
        GS[GlobalSearch]
        BS2[BasicSearch]
        DS[DRIFTSearch]
    end
    
    subgraph "Context Builder"
        LCB[LocalContextBuilder]
        GCB[GlobalContextBuilder]
    end
    
    BLC --> QC
    QC --> BS
    QC --> LS
    QC --> GS
    QC --> BS2
    QC --> DS
    QC --> LCB
    QC --> GCB
```

## Core Components

### QueryCallbacks

The `QueryCallbacks` class is the central component of the query monitoring module. It provides a comprehensive set of callback methods that allow external observers to track the progress and results of query operations.

**Key Features:**
- **Context Monitoring**: Track when context data is constructed during query execution
- **Map-Reduce Operation Tracking**: Monitor the start and end of map and reduce operations
- **LLM Token Streaming**: Handle real-time token generation events
- **Search Result Processing**: Capture and process search results from various search operations

**Inheritance Hierarchy:**
```
BaseLLMCallback (from [llm_integration](llm_integration.md))
    └── QueryCallbacks
```

## Component Interactions

```mermaid
sequenceDiagram
    participant QS as Query System
    participant QC as QueryCallbacks
    participant LLM as Language Model
    participant CB as Context Builder
    
    QS->>QC: on_context(context)
    Note over QC: Context construction started
    
    CB->>QC: on_context(context_data)
    Note over QC: Context data received
    
    QS->>QC: on_map_response_start(contexts)
    Note over QC: Map operation initiated
    
    QS->>LLM: Process map requests
    LLM->>QC: on_llm_new_token(token)
    Note over QC: Token streaming
    
    LLM-->>QS: Map results
    QS->>QC: on_map_response_end(results)
    Note over QC: Map operation completed
    
    QS->>QC: on_reduce_response_start(context)
    Note over QC: Reduce operation initiated
    
    QS->>LLM: Process reduce request
    LLM->>QC: on_llm_new_token(token)
    Note over QC: Token streaming
    
    LLM-->>QS: Final result
    QS->>QC: on_reduce_response_end(result)
    Note over QC: Reduce operation completed
```

## Data Flow

```mermaid
graph LR
    subgraph "Input Sources"
        C[Context Data]
        MRC[Map Response Contexts]
        RRC[Reduce Response Context]
        T[LLM Tokens]
    end
    
    subgraph "QueryCallbacks"
        on_context[on_context]
        on_map_start[on_map_response_start]
        on_map_end[on_map_response_end]
        on_reduce_start[on_reduce_response_start]
        on_reduce_end[on_reduce_response_end]
        on_token[on_llm_new_token]
    end
    
    subgraph "Output Types"
        SR[SearchResult Array]
        STR[String]
        VOID[None]
    end
    
    C --> on_context
    MRC --> on_map_start
    SR --> on_map_end
    RRC --> on_reduce_start
    STR --> on_reduce_end
    T --> on_token
    
    on_context --> VOID
    on_map_start --> VOID
    on_map_end --> VOID
    on_reduce_start --> VOID
    on_reduce_end --> VOID
    on_token --> VOID
```

## Integration Points

### Query System Integration
The QueryCallbacks class integrates with all search types in the [query_system](query_system.md) module:
- **LocalSearch**: Monitors local graph-based search operations
- **GlobalSearch**: Tracks global community-based search operations  
- **BasicSearch**: Observes basic retrieval operations
- **DRIFTSearch**: Monitors DRIFT (Dynamic Reasoning over Information Flow and Topology) search operations

### Context Builder Integration
Works closely with context builders from the [query_system](query_system.md) module:
- **LocalContextBuilder**: Monitors local context construction
- **GlobalContextBuilder**: Tracks global context building processes

### LLM Integration
Extends the [llm_integration](llm_integration.md) module's BaseLLMCallback to inherit token streaming capabilities, ensuring consistent LLM monitoring across the system.

## Process Flow

```mermaid
graph TD
    Start([Query Initiated]) --> Context{Context Building}
    Context -->|Context Ready| MapStart[Map Operation Start]
    MapStart --> MapProcess[Process Map Requests]
    MapProcess --> TokenStream1[Token Streaming]
    TokenStream1 --> MapEnd[Map Operation End]
    MapEnd --> ReduceStart[Reduce Operation Start]
    ReduceStart --> ReduceProcess[Process Reduce Request]
    ReduceProcess --> TokenStream2[Token Streaming]
    TokenStream2 --> ReduceEnd[Reduce Operation End]
    ReduceEnd --> Final[Final Result]
    
    Context -->|Monitor| on_context[on_context callback]
    MapStart -->|Monitor| on_map_start[on_map_response_start callback]
    MapEnd -->|Monitor| on_map_end[on_map_response_end callback]
    ReduceStart -->|Monitor| on_reduce_start[on_reduce_response_start callback]
    ReduceEnd -->|Monitor| on_reduce_end[on_reduce_response_end callback]
    TokenStream1 -->|Monitor| on_token[on_llm_new_token callback]
    TokenStream2 -->|Monitor| on_token
```

## Usage Patterns

### Basic Monitoring
The QueryCallbacks class provides a base implementation that can be extended to create custom monitoring solutions. Each callback method is designed to be overridden based on specific monitoring requirements.

### Integration with Workflow Management
While QueryCallbacks focuses on query-specific monitoring, it integrates with the broader [workflow_management](workflow_management.md) system through the shared callback infrastructure, enabling comprehensive system-wide observability.

### Real-time Monitoring
The token streaming capabilities (`on_llm_new_token`) enable real-time monitoring of LLM interactions, which is crucial for user experience optimization and performance analysis.

## Dependencies

- **[llm_integration](llm_integration.md)**: Provides BaseLLMCallback for LLM monitoring capabilities
- **[query_system](query_system.md)**: Supplies SearchResult type and search operation context
- **[workflow_management](workflow_management.md)**: Integrates with broader callback management system

## Extension Points

The QueryCallbacks class is designed for extension, allowing developers to:
- Override specific callback methods for custom monitoring logic
- Add new callback methods for additional monitoring points
- Integrate with external monitoring systems and logging frameworks
- Implement performance metrics collection and analysis

## Best Practices

1. **Minimal Overhead**: Callback implementations should be lightweight to avoid impacting query performance
2. **Error Handling**: Callback methods should handle errors gracefully to prevent query failures
3. **State Management**: Maintain minimal state within callback implementations to ensure thread safety
4. **Logging Integration**: Use appropriate logging levels and structured logging for monitoring data
5. **Metrics Collection**: Consider implementing metrics collection for performance analysis and optimization