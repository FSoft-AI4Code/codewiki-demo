# Runner Core Module Documentation

## Introduction

The runner-core module is the central execution engine of Vite's module system, responsible for dynamically loading, evaluating, and managing JavaScript modules in both development and production environments. It provides the foundation for Vite's hot module replacement (HMR) system and serves as the bridge between Vite's build system and runtime execution.

## Architecture Overview

The runner-core module implements a sophisticated module execution system that handles:

- **Dynamic Module Loading**: Runtime module resolution and loading
- **Module Caching**: Intelligent caching with invalidation strategies
- **Hot Module Replacement**: Live module updates without page refresh
- **Source Map Support**: Debugging support for transformed code
- **Circular Dependency Detection**: Prevention of infinite loops
- **External Module Handling**: Integration with Node.js and browser modules

```mermaid
graph TB
    subgraph "Runner Core Architecture"
        MR[ModuleRunner]
        MD[ModuleRunnerDebugger]
        EM[EvaluatedModules]
        EMN[EvaluatedModuleNode]
        ESE[ESModulesEvaluator]
        HMR[HMRClient]
        SMS[SourceMapSupport]
        
        MR --> EM
        MR --> HMR
        MR --> SMS
        MR --> ESE
        EM --> EMN
        MR -.-> MD
    end
    
    subgraph "External Dependencies"
        TT[Transport Layer]
        DT[Dev Server]
        BT[Build System]
        PS[Plugin System]
    end
    
    MR --> TT
    MR -.-> DT
    MR -.-> BT
    MR -.-> PS
```

## Core Components

### ModuleRunner

The `ModuleRunner` class is the primary orchestrator that manages the entire module execution lifecycle. It coordinates between different subsystems including the evaluator, transport layer, HMR system, and source map support.

**Key Responsibilities:**
- Module import and execution coordination
- Cache management and invalidation
- HMR integration and handling
- Transport layer communication
- Error handling and debugging support

**Core Methods:**
- `import<T>(url: string): Promise<T>` - Main entry point for module loading
- `clearCache(): void` - Clears all module caches and HMR listeners
- `close(): Promise<void>` - Graceful shutdown with cleanup
- `isClosed(): boolean` - Runtime state checking

### ModuleRunnerDebugger

A debugging interface that provides runtime insights into module loading performance and execution flow. It helps identify bottlenecks and circular dependencies during development.

## Module Execution Flow

```mermaid
sequenceDiagram
    participant App as Application
    participant MR as ModuleRunner
    participant CM as CachedModule
    participant TL as Transport Layer
    participant EV as Evaluator
    participant EM as EvaluatedModules
    
    App->>MR: import(url)
    MR->>CM: cachedModule(url)
    alt Module not cached
        CM->>TL: fetchModule(url)
        TL-->>CM: module info
        CM->>EM: ensureModule(id, url)
    end
    CM-->>MR: EvaluatedModuleNode
    MR->>MR: cachedRequest(url, mod)
    alt Module not evaluated
        MR->>EV: runInlinedModule(context, code)
        EV-->>MR: exports
    end
    MR-->>App: module exports
```

## Dependency Management

The runner-core module maintains complex relationships with other Vite subsystems:

```mermaid
graph LR
    subgraph "Runner Core Dependencies"
        RC[runner-core]
        EM[esm-evaluator]
        EV[evaluated-modules]
        SS[sourcemap-support]
        TI[types-and-interfaces]
        HMR[hmr-shared]
    end
    
    subgraph "External Systems"
        DS[dev-server]
        PS[plugin-system]
        MG[module-graph]
        CT[core-types]
    end
    
    RC --> EM
    RC --> EV
    RC --> SS
    RC --> TI
    RC --> HMR
    
    RC -.-> DS
    RC -.-> PS
    RC -.-> MG
    RC -.-> CT
```

## Module Caching Strategy

The runner-core implements a multi-layered caching system:

```mermaid
graph TB
    subgraph "Caching Layers"
        CM[Concurrent Module Promises]
        EM[Evaluated Modules Cache]
        TC[Transport Cache]
    end
    
    subgraph "Cache Operations"
        GET[getModuleByUrl]
        ENS[ensureModule]
        INV[invalidateModule]
        CLR[clearCache]
    end
    
    CM --> EM
    EM --> TC
    
    GET --> CM
    ENS --> EM
    INV --> EM
    CLR --> CM
    CLR --> EM
```

## Hot Module Replacement Integration

The HMR system is deeply integrated into the module runner:

```mermaid
graph LR
    subgraph "HMR Components"
        HC[HMRClient]
        HH[HMRHandler]
        HL[HMRLogger]
        HU[HMRContext]
    end
    
    subgraph "Runner Integration"
        MR[ModuleRunner]
        EM[EvaluatedModules]
        IM[import method]
    end
    
    MR --> HC
    MR --> HH
    HC --> HL
    HC --> HU
    IM -.-> HC
    HC -.-> EM
```

## Circular Dependency Detection

The runner-core implements sophisticated circular dependency detection to prevent infinite loops:

```mermaid
graph TD
    A[Module A] -->|imports| B[Module B]
    B -->|imports| C[Module C]
    C -->|imports| A
    
    subgraph "Detection Methods"
        CS[Callstack Check]
        CM[Circular Module Check]
        CI[Circular Import Check]
    end
    
    CS -->|tracks import chain| CS
    CM -->|checks module imports| CM
    CI -->|traverses importers| CI
```

## Source Map Support

Source map integration provides debugging capabilities for transformed code:

```mermaid
graph LR
    subgraph "Source Map Components"
        SMS[SourceMapSupport]
        SD[SourceMapDecoder]
        SI[SourceMapInterceptor]
        RM[Reset Method]
    end
    
    subgraph "Runner Integration"
        MR[ModuleRunner]
        EV[Evaluator]
        ER[Error Handling]
    end
    
    MR --> SMS
    SMS --> SD
    SMS --> SI
    MR --> RM
    ER -.-> SI
```

## Transport Layer Integration

The runner-core communicates with the build system through a transport layer:

```mermaid
sequenceDiagram
    participant MR as ModuleRunner
    participant NT as NormalizedTransport
    participant TL as Transport Layer
    participant BS as Build System
    
    MR->>NT: normalizeModuleRunnerTransport
    NT->>TL: establish connection
    TL->>BS: fetchModule request
    BS-->>TL: module data
    TL-->>NT: resolved result
    NT-->>MR: processed module
```

## Error Handling and Debugging

The runner-core provides comprehensive error handling and debugging capabilities:

- **Module Loading Errors**: Detailed error messages with import chain information
- **Circular Dependency Warnings**: Early detection and reporting
- **Performance Monitoring**: Debug timers for slow-loading modules
- **Source Map Integration**: Accurate error stack traces
- **HMR Error Recovery**: Graceful handling of module update failures

## Configuration Options

The runner-core accepts various configuration options through `ModuleRunnerOptions`:

- **Transport**: Communication layer with build system
- **HMR**: Hot module replacement configuration
- **Source Maps**: Source map support settings
- **Evaluator**: Custom module evaluator implementation
- **Debug**: Debug logging and performance monitoring

## Performance Considerations

The runner-core is designed for optimal performance:

- **Concurrent Module Loading**: Parallel fetching of module information
- **Intelligent Caching**: Multi-layered cache with invalidation strategies
- **Lazy Evaluation**: Modules evaluated only when needed
- **Circular Dependency Optimization**: Early detection to prevent redundant work
- **Memory Management**: Proper cleanup and garbage collection

## Integration with Vite Ecosystem

The runner-core serves as the foundation for Vite's module system and integrates with:

- **[Dev Server](dev-server.md)**: Provides runtime module execution
- **[Build System](build.md)**: Consumes build artifacts and source maps
- **[Plugin System](plugin-system.md)**: Executes plugin-transformed modules
- **[HMR System](hmr-shared.md)**: Enables live module updates
- **[Module Graph](module-graph.md)**: Tracks module dependencies

## Best Practices

1. **Module Organization**: Structure modules to minimize circular dependencies
2. **Error Handling**: Implement proper error boundaries for dynamic imports
3. **Performance Monitoring**: Use debug mode to identify slow-loading modules
4. **Cache Management**: Understand cache invalidation patterns for optimal performance
5. **HMR Integration**: Design modules with HMR compatibility in mind

## Troubleshooting

Common issues and solutions:

- **Circular Dependencies**: Use the debug mode to identify and refactor
- **Module Loading Timeouts**: Check transport layer connectivity
- **HMR Failures**: Verify HMR configuration and transport support
- **Source Map Issues**: Ensure proper source map generation in build configuration
- **Memory Leaks**: Properly close the runner when finished

## API Reference

See [types-and-interfaces.md](types-and-interfaces.md) for detailed type definitions and interfaces used by the runner-core module.