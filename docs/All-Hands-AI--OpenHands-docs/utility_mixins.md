# Utility Mixins Module

The utility_mixins module provides essential mixin classes that enhance LLM functionality with retry logic and debugging capabilities. These mixins are fundamental components of the [llm_integration](llm_integration.md) system, providing cross-cutting concerns that are shared across all LLM implementations.

## Overview

This module contains two core mixin classes:
- **RetryMixin**: Implements configurable retry logic for handling transient LLM failures
- **DebugMixin**: Provides comprehensive logging and debugging capabilities for LLM interactions

These mixins are designed to be composed with LLM classes to provide robust error handling and observability without duplicating code across different LLM implementations.

## Architecture

```mermaid
classDiagram
    class RetryMixin {
        +retry_decorator(**kwargs) Callable
        +log_retry_attempt(retry_state) None
        -_handle_temperature_adjustment(retry_state)
    }
    
    class DebugMixin {
        +log_prompt(messages) None
        +log_response(resp) None
        +vision_is_active() bool
        -_format_message_content(message) str
        -_format_content_element(element) str
    }
    
    class LLM {
        <<inherits RetryMixin, DebugMixin>>
        +completion() Callable
        +get_token_count() int
        +vision_is_active() bool
    }
    
    class AsyncLLM {
        <<inherits LLM>>
        +async_completion() Callable
    }
    
    RetryMixin <|-- LLM
    DebugMixin <|-- LLM
    LLM <|-- AsyncLLM
    
    RetryMixin --> "uses" TenacityLibrary
    RetryMixin --> "handles" LLMNoResponseError
    DebugMixin --> "uses" LoggingSystem
```

## Component Dependencies

```mermaid
graph TD
    A[utility_mixins] --> B[tenacity]
    A --> C[openhands.core.exceptions]
    A --> D[openhands.core.logger]
    A --> E[openhands.utils.tenacity_stop]
    
    F[core_llm_implementation] --> A
    G[router_system] --> A
    
    A --> H[LLMNoResponseError]
    A --> I[llm_prompt_logger]
    A --> J[llm_response_logger]
    A --> K[stop_if_should_exit]
    
    style A fill:#e1f5fe
    style F fill:#f3e5f5
    style G fill:#f3e5f5
```

## Core Components

### RetryMixin

The RetryMixin class provides configurable retry logic for LLM operations, handling transient failures and implementing intelligent retry strategies.

#### Key Features

- **Configurable Retry Parameters**: Supports customizable retry counts, wait times, and multipliers
- **Exception-Specific Handling**: Targets specific exception types for retry logic
- **Temperature Adjustment**: Automatically adjusts temperature for `LLMNoResponseError` cases
- **Exponential Backoff**: Implements exponential backoff with jitter for optimal retry timing
- **Graceful Exit Handling**: Integrates with system shutdown signals

#### Retry Strategy

```mermaid
flowchart TD
    A[LLM Request] --> B{Request Successful?}
    B -->|Yes| C[Return Response]
    B -->|No| D{Retryable Exception?}
    D -->|No| E[Raise Exception]
    D -->|Yes| F{Max Retries Reached?}
    F -->|Yes| E
    F -->|No| G[Log Retry Attempt]
    G --> H{LLMNoResponseError?}
    H -->|Yes| I[Adjust Temperature to 1.0]
    H -->|No| J[Keep Original Parameters]
    I --> K[Wait with Exponential Backoff]
    J --> K
    K --> L{Should Exit?}
    L -->|Yes| E
    L -->|No| A
```

#### Configuration Parameters

| Parameter | Description | Default Behavior |
|-----------|-------------|------------------|
| `num_retries` | Maximum number of retry attempts | Configurable per LLM |
| `retry_exceptions` | Tuple of exception types to retry | LLM-specific exceptions |
| `retry_min_wait` | Minimum wait time between retries | Exponential backoff minimum |
| `retry_max_wait` | Maximum wait time between retries | Exponential backoff maximum |
| `retry_multiplier` | Backoff multiplier | Exponential growth factor |
| `retry_listener` | Callback for retry events | Optional notification handler |

### DebugMixin

The DebugMixin class provides comprehensive logging and debugging capabilities for LLM interactions, enabling detailed observability of LLM operations.

#### Key Features

- **Prompt Logging**: Detailed logging of input messages and prompts
- **Response Logging**: Comprehensive logging of LLM responses including tool calls
- **Multi-format Support**: Handles various message formats (text, images, tool calls)
- **Vision Content Handling**: Special handling for vision-enabled models
- **Performance Optimization**: Conditional logging based on debug level

#### Logging Flow

```mermaid
sequenceDiagram
    participant Client
    participant LLM
    participant DebugMixin
    participant Logger
    
    Client->>LLM: completion(messages)
    LLM->>DebugMixin: log_prompt(messages)
    DebugMixin->>DebugMixin: _format_message_content()
    DebugMixin->>Logger: llm_prompt_logger.debug()
    
    LLM->>LLM: call_llm_api()
    LLM->>DebugMixin: log_response(response)
    DebugMixin->>DebugMixin: extract_tool_calls()
    DebugMixin->>Logger: llm_response_logger.debug()
    
    LLM->>Client: return response
```

## Integration with LLM System

### Mixin Composition

The utility mixins are composed with LLM classes using multiple inheritance:

```python
class LLM(RetryMixin, DebugMixin):
    def __init__(self, config, service_id, metrics=None, retry_listener=None):
        # Initialize LLM-specific functionality
        self.retry_listener = retry_listener
        
        # Apply retry decorator to completion function
        @self.retry_decorator(
            num_retries=self.config.num_retries,
            retry_exceptions=LLM_RETRY_EXCEPTIONS,
            retry_min_wait=self.config.retry_min_wait,
            retry_max_wait=self.config.retry_max_wait,
            retry_multiplier=self.config.retry_multiplier,
            retry_listener=self.retry_listener,
        )
        def wrapper(*args, **kwargs):
            # Log prompt
            self.log_prompt(messages)
            
            # Make LLM call
            resp = self._completion_unwrapped(*args, **kwargs)
            
            # Log response
            self.log_response(resp)
            
            return resp
        
        self._completion = wrapper
```

### Error Handling Integration

```mermaid
graph TD
    A[LLM Request] --> B[RetryMixin.retry_decorator]
    B --> C[DebugMixin.log_prompt]
    C --> D[LLM API Call]
    D --> E{Exception Occurred?}
    E -->|No| F[DebugMixin.log_response]
    E -->|Yes| G[RetryMixin.log_retry_attempt]
    G --> H{Retryable?}
    H -->|Yes| I[Apply Backoff]
    H -->|No| J[Raise Exception]
    I --> K{LLMNoResponseError?}
    K -->|Yes| L[Adjust Temperature]
    K -->|No| M[Retry Request]
    L --> M
    M --> D
    F --> N[Return Response]
    J --> O[Propagate Error]
```

## Error Handling Strategies

### Exception Types

The retry system handles specific exception types:

- **Rate Limiting (429)**: Exponential backoff with jitter
- **Service Unavailable (503)**: Retry with increasing delays
- **Connection Errors**: Network-level retry logic
- **LLMNoResponseError**: Special handling with temperature adjustment

### Temperature Adjustment Logic

For `LLMNoResponseError` (primarily seen in Gemini models):

1. **Detection**: Identify LLMNoResponseError during retry
2. **Temperature Check**: Verify current temperature setting
3. **Adjustment**: Set temperature to 1.0 if currently 0
4. **Logging**: Log the temperature adjustment
5. **Retry**: Attempt request with adjusted parameters

## Logging and Observability

### Log Levels and Destinations

```mermaid
graph LR
    A[Debug Messages] --> B[llm_prompt_logger]
    A --> C[llm_response_logger]
    A --> D[openhands_logger]
    
    B --> E[Prompt Content]
    C --> F[Response Content]
    C --> G[Tool Calls]
    D --> H[Retry Attempts]
    D --> I[Error Messages]
    
    style B fill:#e8f5e8
    style C fill:#e8f5e8
    style D fill:#fff3e0
```

### Message Formatting

The debug system handles various content types:

- **Text Messages**: Direct string logging
- **Image Content**: URL logging for vision models
- **Tool Calls**: Function name and arguments
- **Multi-part Content**: Structured formatting

## Performance Considerations

### Conditional Logging

```python
def log_prompt(self, messages):
    if not logger.isEnabledFor(DEBUG):
        # Skip expensive string operations if not debugging
        return
    
    # Proceed with detailed logging
    debug_message = MESSAGE_SEPARATOR.join(
        self._format_message_content(msg) for msg in messages
    )
```

### Memory Optimization

- **Lazy Evaluation**: String formatting only when needed
- **Conditional Processing**: Skip operations when debug disabled
- **Efficient Serialization**: Optimized message formatting

## Configuration Integration

### Retry Configuration

The mixins integrate with the broader configuration system:

```python
# From LLMConfig
num_retries: int = 8
retry_min_wait: int = 15
retry_max_wait: int = 120
retry_multiplier: float = 2
```

### Debug Configuration

```python
# From LLMConfig
log_completions: bool = False
log_completions_folder: Optional[str] = None
```

## Usage Patterns

### Basic Usage

```python
# Mixins are automatically applied to all LLM instances
llm = LLM(config=llm_config, service_id="main")

# Retry and debug functionality is transparent
response = llm.completion(messages=[{"role": "user", "content": "Hello"}])
```

### Custom Retry Listeners

```python
def retry_callback(attempt: int, max_retries: int):
    print(f"Retry attempt {attempt}/{max_retries}")

llm = LLM(config=llm_config, service_id="main", retry_listener=retry_callback)
```

## Related Documentation

- [llm_integration](llm_integration.md) - Overall LLM system architecture
- [core_llm_implementation](core_llm_implementation.md) - Base LLM classes
- [router_system](router_system.md) - LLM routing and load balancing
- [events_and_actions](events_and_actions.md) - Event system integration

## Future Enhancements

### Planned Improvements

1. **Adaptive Retry Strategies**: Dynamic adjustment based on error patterns
2. **Circuit Breaker Pattern**: Prevent cascading failures
3. **Metrics Integration**: Enhanced observability with custom metrics
4. **Structured Logging**: JSON-formatted logs for better parsing
5. **Retry Budget Management**: Global retry limits across requests

### Extension Points

- **Custom Retry Strategies**: Pluggable retry algorithms
- **Enhanced Debug Formatters**: Custom message formatting
- **Telemetry Integration**: OpenTelemetry support
- **Performance Profiling**: Request timing and resource usage