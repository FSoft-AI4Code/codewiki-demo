# Transform Request Module

## Introduction

The transform-request module is a core component of Vite's development server that handles the transformation of modules during the development process. It serves as the central processing unit that takes raw source files, applies various transformations through the plugin system, and produces optimized code ready for browser consumption or server-side rendering.

This module sits at the heart of Vite's development workflow, orchestrating the load-transform pipeline that enables features like hot module replacement (HMR), source map generation, and plugin-based code transformations. It bridges the gap between the raw source code and the processed modules that are served to the browser.

## Architecture Overview

```mermaid
graph TB
    subgraph "Transform Request Module"
        TR[transformRequest Function]
        DT[doTransform Function]
        LNT[loadAndTransform Function]
        GCTR[getCachedTransformResult Function]
        HMSI[handleModuleSoftInvalidation Function]
    end
    
    subgraph "External Dependencies"
        DC[DevEnvironment]
        PC[PluginContainer]
        MG[ModuleGraph]
        DO[DepsOptimizer]
    end
    
    subgraph "Core Types"
        TO[TransformOptions]
        TRS[TransformResult]
        TOI[TransformOptionsInternal]
    end
    
    TR --> DT
    DT --> LNT
    DT --> GCTR
    GCTR --> HMSI
    
    TR --> DC
    DT --> PC
    DT --> MG
    LNT --> PC
    LNT --> MG
    
    TR -.-> TO
    TR -.-> TRS
    TR -.-> TOI
```

## Core Components

### TransformOptions

The `TransformOptions` interface defines the public configuration options for the transformation process. Currently, it primarily handles SSR (Server-Side Rendering) configuration, though this is deprecated in favor of environment-based inference.

```typescript
export interface TransformOptions {
  /**
   * @deprecated inferred from environment
   */
  ssr?: boolean
}
```

### TransformResult

The `TransformResult` interface represents the output of the transformation process, containing the transformed code, source maps, and metadata about dependencies.

```typescript
export interface TransformResult {
  code: string
  map: SourceMap | { mappings: '' } | null
  ssr?: boolean
  etag?: string
  deps?: string[]
  dynamicDeps?: string[]
}
```

### TransformOptionsInternal

Internal options used within the transform request pipeline, providing additional control over the transformation process.

```typescript
export interface TransformOptionsInternal {
  /**
   * @internal
   */
  allowId?: (id: string) => boolean
}
```

## Data Flow

```mermaid
sequenceDiagram
    participant Client
    participant TR as transformRequest
    participant DT as doTransform
    participant GCTR as getCachedTransformResult
    participant LNT as loadAndTransform
    participant PC as PluginContainer
    participant FS as FileSystem
    
    Client->>TR: Request URL transformation
    TR->>TR: Check for pending requests
    TR->>DT: Initiate transformation
    DT->>GCTR: Check cache
    alt Cache Hit
        GCTR-->>DT: Return cached result
        DT-->>TR: Return result
    else Cache Miss
        DT->>LNT: Load and transform
        LNT->>PC: Load via plugins
        alt Plugin Load Success
            PC-->>LNT: Return code/map
        else Plugin Load Fail
            LNT->>FS: Read file directly
            FS-->>LNT: Return file content
        end
        LNT->>PC: Transform code
        PC-->>LNT: Return transformed code
        LNT->>LNT: Process source maps
        LNT-->>DT: Return result
        DT-->>TR: Return result
    end
    TR-->>Client: Return TransformResult
```

## Process Flow

### Main Transformation Pipeline

```mermaid
flowchart TD
    Start([transformRequest called])
    CheckClosing{Server closing?}
    CheckPending[Check pending requests]
    CheckCache{Cache valid?}
    DoTransform[Call doTransform]
    ReturnResult[Return TransformResult]
    HandleError[Handle errors]
    
    Start --> CheckClosing
    CheckClosing -->|Yes| HandleError
    CheckClosing -->|No| CheckPending
    CheckPending -->|Has pending| CheckCache
    CheckPending -->|No pending| DoTransform
    CheckCache -->|Valid| ReturnResult
    CheckCache -->|Invalid| DoTransform
    DoTransform --> ReturnResult
    HandleError --> End([End])
    ReturnResult --> End
```

### Load and Transform Process

```mermaid
flowchart TD
    Start([loadAndTransform called])
    ResolveId[Resolve module ID]
    LoadModule[Load module code]
    CheckLoadResult{Load successful?}
    TryFileSystem[Try file system read]
    TransformCode[Transform via plugins]
    ProcessSourceMap[Process source maps]
    ApplySSRTransform{SSR transform?}
    CacheResult[Cache result]
    ReturnResult[Return TransformResult]
    
    Start --> ResolveId
    ResolveId --> LoadModule
    LoadModule --> CheckLoadResult
    CheckLoadResult -->|No| TryFileSystem
    CheckLoadResult -->|Yes| TransformCode
    TryFileSystem --> TransformCode
    TransformCode --> ProcessSourceMap
    ProcessSourceMap --> ApplySSRTransform
    ApplySSRTransform -->|Yes| SSRTransform
    ApplySSRTransform -->|No| CacheResult
    SSRTransform[Apply SSR transformation] --> CacheResult
    CacheResult --> ReturnResult
```

## Key Features

### Request Deduplication

The module implements sophisticated request deduplication to prevent redundant transformations:

- **Pending Request Tracking**: Maintains a map of ongoing transformations to avoid duplicate processing
- **Timestamp-based Invalidation**: Uses timestamps to determine if cached results are still valid
- **Abort Mechanism**: Provides ability to abort stale requests when modules are invalidated

### Caching Strategy

```mermaid
graph LR
    subgraph "Cache Layers"
        Memory[Memory Cache]
        Soft[Soft Invalidation]
        Hard[Hard Invalidation]
    end
    
    subgraph "Cache Keys"
        URL[URL-based]
        ID[ID-based]
        Timestamp[Timestamp-based]
    end
    
    Memory --> URL
    Memory --> ID
    Soft --> Timestamp
    Hard --> Timestamp
```

### Source Map Processing

The module handles source map generation and processing:

- **Extraction**: Extracts source maps from loaded files
- **Injection**: Injects source content into source maps
- **Normalization**: Normalizes source map formats
- **Path Resolution**: Rewrites absolute paths to relative paths for better debugger support

### Error Handling

Comprehensive error handling for various scenarios:

- **File Not Found**: Graceful handling of missing files
- **Permission Denied**: Proper error reporting for restricted files
- **Public File Access**: Special handling for files in public directory
- **Server Closure**: Proper cleanup when server is shutting down

## Integration Points

### DevEnvironment Integration

The module integrates closely with the [dev-environment](dev-environment.md) system:

- Uses `DevEnvironment` for configuration and state management
- Leverages the module graph for dependency tracking
- Integrates with the plugin container for transformations
- Coordinates with the dependency optimizer

### Plugin System Integration

Works with the [plugin-container](plugin-container.md) to:

- Resolve module IDs through plugins
- Load module content via plugins
- Apply transformations through the plugin pipeline
- Handle plugin-specific configurations

### Module Graph Integration

Integrates with the [module-graph](module-graph.md) to:

- Track module dependencies
- Manage module invalidation states
- Update module transformation results
- Handle HMR-related transformations

## Performance Considerations

### Optimization Strategies

1. **Caching**: Multi-layered caching prevents redundant transformations
2. **Request Deduplication**: Avoids duplicate processing of the same module
3. **Lazy Loading**: Defers expensive operations until necessary
4. **Incremental Processing**: Only reprocesses changed modules

### Memory Management

- **Cache Invalidation**: Proper cleanup of stale cache entries
- **Request Cleanup**: Automatic cleanup of completed requests
- **Resource Management**: Efficient handling of file system resources

## Error Codes

The module defines specific error codes for different failure scenarios:

- `ERR_LOAD_URL`: Failed to load a URL
- `ERR_LOAD_PUBLIC_URL`: Attempted to import from public directory
- `ERR_DENIED_ID`: ID was denied by the allowId function

## Dependencies

### Internal Dependencies

- [dev-environment](dev-environment.md): Core development environment
- [plugin-container](plugin-container.md): Plugin system integration
- [module-graph](module-graph.md): Module dependency tracking
- [ssr](ssr.md): Server-side rendering transformations

### External Dependencies

- `es-module-lexer`: ES module parsing
- `magic-string`: String manipulation for transformations
- `etag`: ETag generation for caching
- Node.js file system and path utilities

## Usage Examples

### Basic Transformation

```typescript
const result = await transformRequest(environment, '/src/main.js')
console.log(result.code) // Transformed code
console.log(result.map)  // Source map
```

### With Internal Options

```typescript
const result = await transformRequest(environment, '/src/app.js', {
  allowId: (id) => !id.includes('node_modules')
})
```

### Error Handling

```typescript
try {
  const result = await transformRequest(environment, '/src/missing.js')
} catch (error) {
  if (error.code === 'ERR_LOAD_URL') {
    console.error('Failed to load module')
  }
}
```

## Future Considerations

The module is designed with extensibility in mind:

- **Environment-based Processing**: Moving towards environment-specific transformation logic
- **Plugin Integration**: Enhanced plugin system integration
- **Performance Optimization**: Continued optimization of transformation pipeline
- **Source Map Enhancement**: Improved source map handling and debugging support