# Ruby Integration Layer

The Ruby Integration Layer serves as a critical bridge between Logstash's Java-based core infrastructure and its Ruby-based plugin ecosystem. This module provides the essential interfaces and mechanisms that enable seamless interoperability between Java and Ruby components within the IR (Intermediate Representation) compiler framework.

## Architecture Overview

The Ruby Integration Layer operates within the IR compiler subsystem, providing plugin factory interfaces that enable the compilation process to instantiate and manage Ruby-based plugins. It acts as an abstraction layer that allows the Java-based compiler to work with Ruby plugins without direct knowledge of Ruby implementation details.

```mermaid
graph TB
    subgraph "IR Compiler System"
        A[Dataset Compiler] --> B[Ruby Integration Layer]
        C[Event Condition System] --> B
        D[Output Strategy Management] --> B
        E[Plugin Delegation] --> B
    end
    
    subgraph "Ruby Integration Layer"
        B --> F[RubyIntegration.PluginFactory]
        F --> G[Input Plugin Creation]
        F --> H[Output Plugin Creation]
        F --> I[Filter Plugin Creation]
        F --> J[Codec Plugin Creation]
    end
    
    subgraph "Ruby Runtime Environment"
        G --> K[Ruby Input Plugins]
        H --> L[Ruby Output Plugins]
        I --> M[Ruby Filter Plugins]
        J --> N[Ruby Codec Plugins]
    end
    
    subgraph "Core Integration"
        O[RubyJavaIntegration] --> P[Type System Integration]
        Q[RubyUtil] --> R[Ruby Runtime Management]
        S[JrubyEventExtLibrary] --> T[Event Object Bridge]
        U[JrubyTimestampExtLibrary] --> V[Timestamp Object Bridge]
    end
    
    B --> O
    B --> Q
    B --> S
    B --> U
```

## Core Components

### RubyIntegration.PluginFactory

The central interface that defines the contract for creating Ruby-based plugins within the compilation process.

**Key Responsibilities:**
- **Plugin Instantiation**: Creates instances of Ruby plugins (inputs, outputs, filters, codecs)
- **Type Bridge**: Handles conversion between Java and Ruby object representations
- **Source Metadata**: Maintains plugin source information for debugging and error reporting
- **Codec Management**: Provides both default and custom codec creation capabilities

**Interface Methods:**
```java
IRubyObject buildInput(RubyString name, IRubyObject args, SourceWithMetadata source)
AbstractOutputDelegatorExt buildOutput(RubyString name, IRubyObject args, SourceWithMetadata source)
AbstractFilterDelegatorExt buildFilter(RubyString name, IRubyObject args, SourceWithMetadata source)
IRubyObject buildCodec(RubyString name, IRubyObject args, SourceWithMetadata source)
Codec buildDefaultCodec(String codecName)
Codec buildRubyCodecWrapper(RubyObject rubyCodec)
```

## Integration Dependencies

The Ruby Integration Layer relies heavily on several core system components:

### Ruby Runtime Integration
- **[ruby_integration](ruby_integration.md)**: Provides the foundational Ruby-Java bridge
- **[core_data_structures](core_data_structures.md)**: Supplies type conversion and data access utilities

### Plugin System Integration
- **[plugin_delegation](plugin_delegation.md)**: Manages plugin lifecycle and execution
- **[output_strategy_management](output_strategy_management.md)**: Handles output plugin strategies

### Event Processing Integration
- **[event_api](event_api.md)**: Provides event object definitions and interfaces

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant Compiler as IR Compiler
    participant Factory as PluginFactory
    participant Ruby as Ruby Runtime
    participant Plugin as Ruby Plugin
    
    Compiler->>Factory: buildFilter(name, args, source)
    Factory->>Ruby: Instantiate Ruby plugin class
    Ruby->>Plugin: Create plugin instance
    Plugin->>Ruby: Initialize with configuration
    Ruby->>Factory: Return plugin wrapper
    Factory->>Compiler: Return AbstractFilterDelegatorExt
    
    Note over Compiler,Plugin: Plugin is now ready for execution
    
    Compiler->>Factory: buildCodec(name, args, source)
    Factory->>Ruby: Create codec instance
    Ruby->>Factory: Return codec wrapper
    Factory->>Compiler: Return IRubyObject codec
```

## Plugin Creation Process

```mermaid
flowchart TD
    A[Plugin Request] --> B{Plugin Type?}
    
    B -->|Input| C[buildInput]
    B -->|Output| D[buildOutput]
    B -->|Filter| E[buildFilter]
    B -->|Codec| F[buildCodec]
    
    C --> G[Create Ruby Input Instance]
    D --> H[Create Output Delegator]
    E --> I[Create Filter Delegator]
    F --> J[Create Codec Instance]
    
    G --> K[Return IRubyObject]
    H --> L[Return AbstractOutputDelegatorExt]
    I --> M[Return AbstractFilterDelegatorExt]
    J --> N[Return IRubyObject/Codec]
    
    K --> O[Plugin Ready]
    L --> O
    M --> O
    N --> O
```

## Type System Integration

The Ruby Integration Layer works closely with the core type conversion system to ensure seamless data exchange:

### Ruby-Java Object Mapping
- **Event Objects**: Bridges between Java Event instances and Ruby Event objects
- **Timestamp Objects**: Handles temporal data conversion between Java and Ruby representations
- **Configuration Objects**: Converts plugin configuration from Ruby hashes to Java maps
- **Metadata Objects**: Preserves source metadata across language boundaries

### Conversion Flow
```mermaid
graph LR
    A[Java Objects] --> B[Valuefier]
    B --> C[Ruby Objects]
    C --> D[Rubyfier]
    D --> A
    
    E[Plugin Args] --> F[Type Conversion]
    F --> G[Ruby Plugin Config]
    
    H[Ruby Plugin Output] --> I[Type Conversion]
    I --> J[Java Event Objects]
```

## Error Handling and Debugging

The Ruby Integration Layer provides comprehensive error handling mechanisms:

### Source Metadata Tracking
- **File Information**: Tracks the source file where plugins are defined
- **Line Numbers**: Maintains line number information for error reporting
- **Configuration Context**: Preserves configuration context for debugging

### Exception Translation
- **Ruby Exceptions**: Translates Ruby exceptions to Java exceptions
- **Type Errors**: Provides clear error messages for type mismatches
- **Configuration Errors**: Reports configuration validation failures

## Performance Considerations

### Plugin Instantiation Optimization
- **Factory Caching**: Reuses factory instances where possible
- **Lazy Loading**: Defers plugin creation until actually needed
- **Memory Management**: Properly manages Ruby object lifecycle

### Runtime Efficiency
- **Minimal Overhead**: Reduces conversion overhead between Java and Ruby
- **Direct Delegation**: Uses direct method calls where possible
- **Resource Pooling**: Manages Ruby runtime resources efficiently

## Configuration and Lifecycle

### Plugin Factory Configuration
The PluginFactory interface is implemented by Ruby classes that handle the actual plugin instantiation logic. The factory is responsible for:

1. **Plugin Discovery**: Locating Ruby plugin classes
2. **Configuration Validation**: Ensuring plugin configurations are valid
3. **Dependency Injection**: Providing required dependencies to plugins
4. **Lifecycle Management**: Managing plugin initialization and cleanup

### Integration Points
- **Compilation Phase**: Plugins are instantiated during pipeline compilation
- **Runtime Phase**: Plugin instances are executed within the pipeline
- **Shutdown Phase**: Proper cleanup of Ruby resources

## Security Considerations

### Ruby Code Execution
- **Sandboxing**: Ruby plugin execution is contained within the JRuby runtime
- **Resource Limits**: Memory and CPU usage is monitored and limited
- **Permission Management**: Ruby plugins operate with restricted permissions

### Configuration Security
- **Input Validation**: All plugin configurations are validated before use
- **Sanitization**: User inputs are sanitized to prevent injection attacks
- **Access Control**: Plugin access to system resources is controlled

## Monitoring and Observability

### Plugin Metrics
- **Creation Time**: Tracks time taken to instantiate plugins
- **Memory Usage**: Monitors memory consumption of Ruby plugins
- **Error Rates**: Tracks plugin creation and execution errors

### Debugging Support
- **Stack Traces**: Provides detailed stack traces across Java-Ruby boundaries
- **Configuration Dumps**: Supports dumping plugin configurations for debugging
- **Runtime Inspection**: Allows inspection of Ruby plugin state

## Future Considerations

### Performance Enhancements
- **Native Compilation**: Potential for compiling Ruby plugins to native code
- **Caching Improvements**: Enhanced caching strategies for plugin instances
- **Memory Optimization**: Reduced memory footprint for Ruby objects

### Feature Extensions
- **Plugin Versioning**: Support for multiple versions of the same plugin
- **Hot Reloading**: Dynamic reloading of Ruby plugins without restart
- **Enhanced Debugging**: Improved debugging tools for Ruby-Java integration

## Related Documentation

- **[ir_compiler](ir_compiler.md)**: Parent module containing the Ruby Integration Layer
- **[dataset_compilation](dataset_compilation.md)**: Dataset compilation that uses Ruby plugins
- **[plugin_delegation](plugin_delegation.md)**: Plugin delegation mechanisms
- **[ruby_integration](ruby_integration.md)**: Core Ruby-Java integration utilities
- **[event_api](event_api.md)**: Event object definitions and interfaces
- **[core_data_structures](core_data_structures.md)**: Type conversion and data access utilities