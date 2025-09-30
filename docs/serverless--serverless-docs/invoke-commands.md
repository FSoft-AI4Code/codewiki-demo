# Invoke Commands Module Documentation

## Overview

The invoke-commands module provides the core functionality for invoking serverless functions both locally and remotely. It serves as the primary interface for function execution within the serverless framework, handling environment setup, command routing, and execution tracking.

## Purpose and Core Functionality

The invoke-commands module is responsible for:

- **Function Invocation**: Executing serverless functions both locally and in cloud environments
- **Environment Management**: Setting up provider-independent environment variables for local development
- **Command Structure**: Defining the CLI command hierarchy for invoke operations
- **Execution Tracking**: Providing hooks for monitoring and analytics of function invocations
- **Local Development Support**: Enabling local function testing with proper environment simulation

## Architecture

### Component Structure

```mermaid
graph TB
    subgraph "Invoke Commands Module"
        INVOKER[lib.plugins.invoke.Invoke]
        
        subgraph "Command Definitions"
            INVOKE_CMD[invoke command]
            INVOKE_LOCAL_CMD[invoke local command]
        end
        
        subgraph "Hook System"
            INIT_HOOK[initialize hook]
            LOAD_ENV_HOOK[loadEnvVarsForLocal hook]
            TRACK_INVOKE_HOOK[trackInvoke hook]
            TRACK_LOCAL_HOOK[trackInvokeLocal hook]
        end
        
        subgraph "Environment Management"
            ENV_VARS[Environment Variables]
            PROVIDER_ENV[Provider Environment]
            PROCESS_ENV[Process Environment]
        end
    end
    
    subgraph "External Dependencies"
        CLI_SCHEMA[cliCommandsSchema]
        SERVERLESS[Serverless Framework]
        LODASH[Lodash Utils]
    end
    
    INVOKER --> INVOKE_CMD
    INVOKER --> INVOKE_LOCAL_CMD
    INVOKER --> INIT_HOOK
    INVOKER --> LOAD_ENV_HOOK
    INVOKER --> TRACK_INVOKE_HOOK
    INVOKER --> TRACK_LOCAL_HOOK
    
    LOAD_ENV_HOOK --> ENV_VARS
    LOAD_ENV_HOOK --> PROVIDER_ENV
    LOAD_ENV_HOOK --> PROCESS_ENV
    
    CLI_SCHEMA --> INVOKE_CMD
    CLI_SCHEMA --> INVOKE_LOCAL_CMD
    SERVERLESS --> INVOKER
    LODASH --> INVOKER
```

### Data Flow Architecture

```mermaid
sequenceDiagram
    participant CLI as CLI Command
    participant INVOKER as Invoke Plugin
    participant HOOKS as Hook System
    participant ENV as Environment Manager
    participant TRACKER as Tracker
    
    CLI->>INVOKER: Execute invoke command
    INVOKER->>HOOKS: Trigger initialize hook
    HOOKS->>INVOKER: Process options
    
    alt Local Invocation
        INVOKER->>HOOKS: Trigger loadEnvVarsForLocal
        HOOKS->>ENV: Set IS_LOCAL=true
        ENV->>ENV: Process --env options
        ENV->>PROCESS: Update process.env
        ENV->>PROVIDER: Update provider environment
    end
    
    INVOKER->>INVOKER: Execute function
    
    alt Remote Invocation
        INVOKER->>TRACKER: Trigger trackInvoke
    else Local Invocation
        INVOKER->>TRACKER: Trigger trackInvokeLocal
    end
    
    TRACKER-->>CLI: Return result
```

## Core Components

### lib.plugins.invoke.Invoke

The main class that orchestrates function invocation functionality. It extends the serverless plugin architecture and provides:

- **Command Registration**: Defines the `invoke` and `invoke local` CLI commands
- **Hook Management**: Implements lifecycle hooks for initialization and tracking
- **Environment Setup**: Configures environment variables for local execution
- **Option Processing**: Handles command-line options and parameters

#### Key Methods

- `constructor(serverless, options)`: Initializes the plugin with serverless instance and options
- `loadEnvVarsForLocal()`: Sets up provider-independent environment variables for local execution
- `trackInvoke()`: Hook for tracking remote function invocations (currently no-op)
- `trackInvokeLocal()`: Hook for tracking local function invocations (currently no-op)

## Command Structure

```mermaid
graph TD
    INVOKE[invoke]
    LOCAL[local]
    
    INVOKE --> LOCAL
    
    subgraph "invoke options"
        FUNCTION[--function]
        DATA[--data]
        PATH[--path]
        TYPE[--type]
    end
    
    subgraph "invoke local options"
        LOCAL_FUNCTION[--function]
        LOCAL_DATA[--data]
        LOCAL_PATH[--path]
        LOCAL_ENV[--env]
        LOCAL_DOCKER[--docker]
    end
    
    INVOKE --> FUNCTION
    INVOKE --> DATA
    INVOKE --> PATH
    INVOKE --> TYPE
    
    LOCAL --> LOCAL_FUNCTION
    LOCAL --> LOCAL_DATA
    LOCAL --> LOCAL_PATH
    LOCAL --> LOCAL_ENV
    LOCAL --> LOCAL_DOCKER
```

## Environment Variable Management

The module implements a sophisticated environment variable management system for local development:

### Default Environment Variables

- `IS_LOCAL`: Set to `'true'` to indicate local execution context
- Provider-specific variables are handled by respective provider plugins

### Environment Variable Propagation

```mermaid
graph LR
    subgraph "Source"
        DEFAULT[Default Variables]
        CLI[CLI --env options]
        PROVIDER[Provider Config]
    end
    
    subgraph "Processing"
        MERGE[_.merge]
        SPLIT[String Split]
    end
    
    subgraph "Targets"
        PROCESS_ENV[process.env]
        SERVICE_ENV[service.provider.environment]
    end
    
    DEFAULT --> MERGE
    CLI --> SPLIT
    SPLIT --> MERGE
    MERGE --> PROCESS_ENV
    MERGE --> SERVICE_ENV
    PROVIDER --> SERVICE_ENV
```

## Integration with Serverless Framework

### Plugin Registration

The invoke-commands module integrates with the serverless framework through:

1. **Plugin System**: Registered as a core plugin in the serverless plugin manager
2. **Command Schema**: Uses `cliCommandsSchema` for command definition and validation
3. **Hook System**: Leverages serverless lifecycle hooks for execution flow
4. **Service Integration**: Accesses service configuration and provider settings

### Dependencies

- **Core Framework**: Depends on [core-framework](core-framework.md) for base functionality
- **CLI Interface**: Integrates with [cli-interface](cli-interface.md) for command processing
- **Configuration Management**: Uses [configuration-management](configuration-management.md) for service configuration
- **Provider Plugins**: Works with provider-specific invoke implementations (e.g., [aws-invoke-local](aws-invoke-local.md))

## Hook System

The module implements a comprehensive hook system for extensibility:

### Lifecycle Hooks

1. **initialize**: Processes input options and prepares the plugin
2. **invoke:local:loadEnvVars**: Sets up environment variables for local execution
3. **after:invoke:invoke**: Post-execution hook for remote invocations
4. **after:invoke:local:invoke**: Post-execution hook for local invocations

### Hook Execution Flow

```mermaid
stateDiagram-v2
    [*] --> Initialize
    Initialize --> CommandSelection
    
    CommandSelection --> LocalInvoke: invoke local
    CommandSelection --> RemoteInvoke: invoke
    
    LocalInvoke --> LoadEnvVars
    LoadEnvVars --> ExecuteLocal
    ExecuteLocal --> TrackLocal
    TrackLocal --> [*]
    
    RemoteInvoke --> ExecuteRemote
    ExecuteRemote --> TrackRemote
    TrackRemote --> [*]
```

## Error Handling and Validation

The module includes built-in validation and error handling:

- **Command Validation**: Uses CLI schema for option validation
- **Environment Validation**: Ensures proper environment variable setup
- **Provider Integration**: Delegates provider-specific validation to respective plugins

## Extension Points

The invoke-commands module provides several extension points:

1. **Custom Hooks**: Other plugins can hook into the invoke lifecycle
2. **Provider Overrides**: Provider plugins can override default behavior
3. **Custom Trackers**: Analytics and monitoring plugins can extend tracking functionality
4. **Environment Customization**: Plugins can modify environment variable handling

## Usage Examples

### Local Function Invocation

```bash
# Invoke function locally with data
serverless invoke local --function myFunction --data '{"key": "value"}'

# Invoke with environment variables
serverless invoke local --function myFunction --env VAR1=value1 --env VAR2=value2

# Invoke with data file
serverless invoke local --function myFunction --path ./data.json
```

### Remote Function Invocation

```bash
# Invoke function remotely
serverless invoke --function myFunction --data '{"key": "value"}'

# Invoke with specific type
serverless invoke --function myFunction --type RequestResponse
```

## Best Practices

1. **Environment Isolation**: Use `--env` options to isolate local development environments
2. **Data Management**: Use `--path` for complex data payloads instead of inline `--data`
3. **Local Testing**: Always test functions locally before deployment using `invoke local`
4. **Hook Utilization**: Leverage hooks for custom pre/post-processing logic
5. **Provider Integration**: Understand provider-specific invoke implementations for optimal usage

## Related Documentation

- [Core Framework](core-framework.md) - Base serverless framework functionality
- [CLI Interface](cli-interface.md) - Command-line interface components
- [Configuration Management](configuration-management.md) - Service configuration handling
- [AWS Invoke Local](aws-invoke-local.md) - AWS-specific local invocation implementation
- [AWS Commands](aws-commands.md) - AWS provider command implementations