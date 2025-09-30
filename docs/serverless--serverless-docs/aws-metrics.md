# AWS Metrics Module

## Introduction

The AWS Metrics module provides comprehensive monitoring and observability capabilities for AWS Lambda functions within the Serverless Framework. It enables developers to retrieve, analyze, and display key performance metrics from AWS CloudWatch, offering insights into function invocations, errors, throttles, and execution duration. This module is essential for monitoring application health, troubleshooting performance issues, and optimizing serverless applications.

## Architecture Overview

```mermaid
graph TB
    subgraph "AWS Metrics Module"
        AM[AwsMetrics Class]
        VAL[validate.js]
        UTIL[utils]
        DAY[dayjs]
    end
    
    subgraph "External Dependencies"
        CW[AWS CloudWatch]
        SF[Serverless Framework]
        PM[Plugin Manager]
    end
    
    subgraph "Core Framework"
        PROVIDER[AWS Provider]
        SERVICE[Service Model]
        CONFIG[Configuration]
    end
    
    AM --> VAL
    AM --> UTIL
    AM --> DAY
    AM --> CW
    AM --> SF
    AM --> PM
    SF --> PROVIDER
    SF --> SERVICE
    SF --> CONFIG
    
    style AM fill:#e1f5fe
    style CW fill:#fff3e0
    style SF fill:#f3e5f5
```

## Component Architecture

```mermaid
graph LR
    subgraph "AwsMetrics Class Components"
        CONSTRUCTOR[Constructor]
        HOOKS[Hooks Setup]
        VALIDATE[extendedValidate]
        GETMETRICS[getMetrics]
        SHOWMETRICS[showMetrics]
    end
    
    subgraph "AWS CloudWatch Integration"
        INVOCATIONS[Invocations Metric]
        THROTTLES[Throttles Metric]
        ERRORS[Errors Metric]
        DURATION[Duration Metric]
    end
    
    subgraph "Data Processing"
        TIMECALC[Time Calculation]
        PERIODCALC[Period Calculation]
        DATAPARSE[Data Parsing]
        AGGREGATION[Data Aggregation]
    end
    
    CONSTRUCTOR --> HOOKS
    HOOKS --> VALIDATE
    VALIDATE --> GETMETRICS
    GETMETRICS --> SHOWMETRICS
    
    GETMETRICS --> INVOCATIONS
    GETMETRICS --> THROTTLES
    GETMETRICS --> ERRORS
    GETMETRICS --> DURATION
    
    GETMETRICS --> TIMECALC
    GETMETRICS --> PERIODCALC
    SHOWMETRICS --> DATAPARSE
    SHOWMETRICS --> AGGREGATION
    
    style CONSTRUCTOR fill:#c8e6c9
    style GETMETRICS fill:#ffcdd2
    style SHOWMETRICS fill:#bbdefb
```

## Data Flow

```mermaid
sequenceDiagram
    participant CLI as Serverless CLI
    participant AM as AwsMetrics
    participant VAL as Validation
    participant CW as CloudWatch API
    participant DP as Data Processing
    participant LOG as Logger
    
    CLI->>AM: Execute metrics command
    AM->>VAL: extendedValidate()
    VAL->>VAL: Parse time options
    VAL->>VAL: Set default time range
    VAL-->>AM: Validation complete
    
    AM->>AM: getMetrics()
    AM->>CW: Request Invocations metric
    AM->>CW: Request Throttles metric
    AM->>CW: Request Errors metric
    AM->>CW: Request Duration metric
    CW-->>AM: Return metric data
    
    AM->>DP: Process and aggregate data
    DP-->>AM: Aggregated metrics
    
    AM->>LOG: showMetrics()
    LOG-->>CLI: Display formatted results
```

## Core Components

### AwsMetrics Class

The `AwsMetrics` class is the main component that orchestrates the metrics retrieval and display process. It integrates with the Serverless Framework plugin system and AWS CloudWatch to provide comprehensive metrics functionality.

#### Key Properties:
- `serverless`: Reference to the Serverless Framework instance
- `options`: Command-line options and configuration
- `provider`: AWS provider instance for API calls
- `logger`: Logging utility for output
- `progress`: Progress indicator for user feedback

#### Core Methods:

**Constructor**
```javascript
constructor(serverless, options, pluginUtils)
```
Initializes the metrics plugin with necessary dependencies and sets up command hooks.

**extendedValidate()**
```javascript
extendedValidate()
```
Validates input parameters and processes time range options. Supports relative time expressions (e.g., "1d", "2h", "30m") and sets appropriate default values.

**getMetrics()**
```javascript
async getMetrics()
```
Retrieves metrics from AWS CloudWatch for specified Lambda functions. Fetches four key metrics:
- **Invocations**: Total number of function invocations
- **Throttles**: Number of throttled requests
- **Errors**: Number of failed executions
- **Duration**: Average execution time in milliseconds

**showMetrics()**
```javascript
showMetrics(metrics)
```
Processes and displays the retrieved metrics in a user-friendly format, including aggregation and formatting.

## Dependencies

### Internal Dependencies
- **[core-framework](core-framework.md)**: Provides the base Serverless Framework functionality
  - Service model for function management
  - Configuration handling
  - Plugin system integration

### External Dependencies
- **dayjs**: Date manipulation and formatting library
- **lodash**: Utility library for data manipulation
- **@serverlessinc/sf-core**: Core Serverless Framework utilities

### AWS Services
- **CloudWatch**: Primary service for metrics retrieval
- **Lambda**: Target service for which metrics are collected

## Configuration and Usage

### Command Line Options

The module supports various command-line options for customizing metrics retrieval:

- `--function`: Specify a specific function (retrieves metrics for all functions if omitted)
- `--startTime`: Start time for metrics (supports relative expressions like "1d", "2h")
- `--endTime`: End time for metrics (defaults to current time)

### Time Range Calculation

```mermaid
graph TD
    A[User Input] --> B{Relative Time?}
    B -->|Yes| C[Parse Expression]
    C --> D[Calculate from Now]
    B -->|No| E[Use Absolute Time]
    D --> F[Set Start Time]
    E --> F
    F --> G[Determine Period]
    G --> H[Period = 3600s if <24h]
    G --> I[Period = 86400s if >24h]
```

### Metrics Period Calculation

The module automatically determines the appropriate CloudWatch metrics period based on the time range:
- **Less than 24 hours**: 1-hour periods (3600 seconds)
- **More than 24 hours**: 1-day periods (86400 seconds)

## Integration Points

### Plugin System Integration

```mermaid
graph LR
    subgraph "Serverless Plugin System"
        PM[Plugin Manager]
        HOOK[Hook System]
        CMD[Command Registry]
    end
    
    subgraph "AwsMetrics Plugin"
        METRICS[metrics:metrics Hook]
        VALIDATE[Validation]
        EXEC[Execution Logic]
    end
    
    PM --> HOOK
    HOOK --> METRICS
    METRICS --> VALIDATE
    VALIDATE --> EXEC
    CMD --> PM
```

### AWS Provider Integration

The module integrates with the [aws-provider](aws-provider.md) to:
- Access AWS credentials and configuration
- Make authenticated CloudWatch API calls
- Retrieve function configuration and names

## Error Handling

The module implements robust error handling for:
- **Invalid time ranges**: Graceful fallback to default values
- **API failures**: Proper error propagation and user feedback
- **Missing metrics**: Handles cases where no metrics are available
- **Function not found**: Validates function existence before metrics retrieval

## Performance Considerations

### Batch Processing
- Retrieves metrics for multiple functions in parallel using `Promise.all()`
- Efficiently aggregates data across function boundaries

### Time Range Optimization
- Automatically selects optimal CloudWatch periods to minimize API calls
- Caches time calculations to avoid redundant processing

### Data Aggregation
- Uses lodash utilities for efficient data processing
- Minimizes memory footprint during large dataset processing

## Extension Points

The module can be extended to:
- Support additional CloudWatch metrics
- Implement custom aggregation functions
- Add new output formats (JSON, CSV, etc.)
- Integrate with third-party monitoring systems

## Related Modules

- **[aws-logs](aws-logs.md)**: Complementary logging functionality
- **[aws-invoke](aws-invoke.md)**: Function invocation capabilities
- **[aws-info](aws-info.md)**: Service information retrieval
- **[core-framework](core-framework.md)**: Base framework functionality

## Best Practices

1. **Time Range Selection**: Use appropriate time ranges for meaningful metrics
2. **Function-Specific Metrics**: Target specific functions for detailed analysis
3. **Regular Monitoring**: Implement automated metrics collection for proactive monitoring
4. **Performance Analysis**: Use duration metrics to identify performance bottlenecks
5. **Error Tracking**: Monitor error rates to ensure application reliability

## Troubleshooting

### Common Issues
- **No metrics found**: Ensure functions have been invoked within the specified time range
- **Permission errors**: Verify AWS credentials have CloudWatch read permissions
- **Time zone issues**: All times are handled in UTC by default
- **Large time ranges**: Consider using longer periods for better performance

### Debug Information
The module provides detailed logging when verbose mode is enabled, including:
- API request parameters
- Response data structure
- Processing time information
- Error details and stack traces