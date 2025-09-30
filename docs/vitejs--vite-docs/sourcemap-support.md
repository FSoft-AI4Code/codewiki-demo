# Sourcemap Support Module

The sourcemap-support module provides comprehensive source map handling capabilities for Vite's module runner system. It enables accurate error stack traces and debugging information by mapping compiled code positions back to their original source locations.

## Overview

This module is a critical component of Vite's development experience, providing:
- Source map decoding and caching
- Stack trace interception and enhancement
- Original position mapping for compiled code
- Integration with Vite's module evaluation system

## Architecture

### Core Components

```mermaid
graph TB
    subgraph "Sourcemap Support Module"
        decoder["Decoder Components"]
        interceptor["Interceptor Components"]
        
        decoder --> DecodedMap["DecodedMap"]
        decoder --> SourceMapLike["SourceMapLike"]
        decoder --> Stats["Stats"]
        
        interceptor --> InterceptorOptions["InterceptorOptions"]
        interceptor --> CallSite["CallSite"]
        interceptor --> State["State"]
        interceptor --> Handlers["Handler Interfaces"]
        
        Handlers --> RetrieveSourceMapHandler["RetrieveSourceMapHandler"]
        Handlers --> RetrieveFileHandler["RetrieveFileHandler"]
        interceptor --> CachedMapEntry["CachedMapEntry"]
    end
    
    subgraph "External Dependencies"
        traceMapping["@jridgewell/trace-mapping"]
        moduleRunner["ModuleRunner"]
        evaluatedModules["EvaluatedModules"]
    end
    
    DecodedMap --> traceMapping
    interceptor --> moduleRunner
    interceptor --> evaluatedModules
```

### Module Structure

```mermaid
graph LR
    subgraph "sourcemap-support"
        decoder.ts["decoder.ts"]
        interceptor.ts["interceptor.ts"]
    end
    
    subgraph "Dependencies"
        runner["runner-core"]
        evaluated["evaluated-modules"]
        utils["shared/utils"]
    end
    
    decoder.ts --> utils
    interceptor.ts --> decoder.ts
    interceptor.ts --> runner
    interceptor.ts --> evaluated
```

## Component Details

### Decoder Components

#### DecodedMap
The `DecodedMap` class is the core data structure for handling source maps:

```typescript
class DecodedMap {
  _encoded: string              // Encoded mappings string
  _decoded: number[][][]       // Decoded mappings cache
  _decodedMemo: Stats          // Memoization state for performance
  url: string                  // Source map URL
  version: number              // Source map version
  names: string[]              // Symbol names from source map
  resolvedSources: string[]    // Resolved source file paths
}
```

**Key Features:**
- Lazily decodes source map mappings for performance
- Memoizes decoding state to avoid redundant operations
- Resolves source paths relative to the source map location
- Integrates with `@jridgewell/trace-mapping` for accurate position mapping

#### SourceMapLike Interface
Defines the minimal structure required for source map compatibility:

```typescript
interface SourceMapLike {
  version: number
  mappings?: string
  names?: string[]
  sources?: string[]
  sourcesContent?: string[]
}
```

#### Stats Interface
Performance optimization structure for memoization:

```typescript
interface Stats {
  lastKey: number      // Last accessed mapping key
  lastNeedle: number   // Last search position
  lastIndex: number    // Last array index
}
```

### Interceptor Components

#### InterceptorOptions
Configuration interface for stack trace interception:

```typescript
interface InterceptorOptions {
  retrieveFile?: RetrieveFileHandler        // Custom file retrieval
  retrieveSourceMap?: RetrieveSourceMapHandler  // Custom source map retrieval
}
```

#### CallSite Enhancement
Extended CallSite interface that provides additional debugging information:

```typescript
interface CallSite extends NodeJS.CallSite {
  getScriptNameOrSourceURL(): string
}
```

#### State Management
Tracks position mapping state during stack trace processing:

```typescript
interface State {
  nextPosition: null | OriginalMapping  // Next position to process
  curPosition: null | OriginalMapping   // Current mapped position
}
```

#### Handler Interfaces

**RetrieveFileHandler:**
```typescript
interface RetrieveFileHandler {
  (path: string): string | null | undefined | false
}
```

**RetrieveSourceMapHandler:**
```typescript
interface RetrieveSourceMapHandler {
  (path: string): null | { url: string; map: any }
}
```

#### CachedMapEntry
Source map caching structure:

```typescript
interface CachedMapEntry {
  url: string | null      // Source map URL
  map: DecodedMap | null  // Decoded source map
  vite?: boolean         // Vite-specific source map flag
}
```

## Data Flow

### Stack Trace Interception Process

```mermaid
sequenceDiagram
    participant Error
    participant PrepareStackTrace
    participant WrapCallSite
    participant MapSourcePosition
    participant SourceMapCache
    participant DecodedMap
    
    Error->>PrepareStackTrace: Error.prepareStackTrace(error, stack)
    PrepareStackTrace->>WrapCallSite: Process each CallSite
    WrapCallSite->>MapSourcePosition: Map compiled position
    MapSourcePosition->>SourceMapCache: Check for cached map
    alt Cache miss
        SourceMapCache->>DecodedMap: Create new DecodedMap
        DecodedMap->>SourceMapCache: Store in cache
    end
    SourceMapCache->>MapSourcePosition: Return cached map
    MapSourcePosition->>WrapCallSite: Return original position
    WrapCallSite->>PrepareStackTrace: Enhanced CallSite
    PrepareStackTrace->>Error: Formatted stack trace
```

### Source Map Retrieval Flow

```mermaid
flowchart TD
    Start["Retrieve Source Map"]
    CheckHandlers{"Custom handlers defined?"}
    TryCustom["Try custom retrieveSourceMap handler"]
    ExtractURL["Extract sourceMappingURL from file"]
    CheckDataURL{"Is data URL?"}
    ProcessData["Process base64 data URL"]
    ResolveRelative["Resolve relative URL"]
    RetrieveFile["Retrieve source map file"]
    ParseJSON["Parse JSON source map"]
    CreateDecodedMap["Create DecodedMap instance"]
    CacheResult["Cache result"]
    ReturnResult["Return source map"]
    ReturnNull["Return null"]
    
    Start --> CheckHandlers
    CheckHandlers -->|Yes| TryCustom
    CheckHandlers -->|No| ExtractURL
    TryCustom -->|Success| ReturnResult
    TryCustom -->|Failure| ExtractURL
    ExtractURL --> CheckDataURL
    CheckDataURL -->|Yes| ProcessData
    CheckDataURL -->|No| ResolveRelative
    ProcessData --> ParseJSON
    ResolveRelative --> RetrieveFile
    RetrieveFile -->|Success| ParseJSON
    RetrieveFile -->|Failure| ReturnNull
    ParseJSON --> CreateDecodedMap
    CreateDecodedMap --> CacheResult
    CacheResult --> ReturnResult
```

## Integration with Module Runner

The sourcemap-support module integrates closely with the [runner-core](runner-core.md) module:

```mermaid
graph LR
    subgraph "Module Runner Integration"
        runner["ModuleRunner"]
        evaluated["EvaluatedModules"]
        interceptor["interceptStackTrace"]
        reset["Reset Function"]
    end
    
    runner --> |"provides"| evaluated
    interceptor --> |"registers"| evaluated
    interceptor --> |"returns"| reset
    reset --> |"cleans up"| interceptor
```

### Key Integration Points:

1. **Module Registration**: The interceptor registers with the ModuleRunner's EvaluatedModules instance
2. **Source Map Lookup**: Uses EvaluatedModules to find Vite-specific source maps
3. **Lifecycle Management**: Returns a cleanup function for proper resource management
4. **Error Handling**: Overrides Error.prepareStackTrace for enhanced debugging

## Performance Optimizations

### Caching Strategy

```mermaid
graph TB
    subgraph "Caching Layers"
        fileCache["fileContentsCache"]
        sourceMapCache["sourceMapCache"]
        evaluatedCache["evaluatedModulesCache"]
        memoizedStats["_decodedMemo"]
    end
    
    subgraph "Cache Keys"
        filePath["File Path"]
        sourcePath["Source Path"]
        moduleGraph["Module Graph Instance"]
        mappingKey["Mapping Key"]
    end
    
    filePath --> fileCache
    sourcePath --> sourceMapCache
    moduleGraph --> evaluatedCache
    mappingKey --> memoizedStats
```

### Optimization Techniques:

1. **Lazy Decoding**: Source map mappings are only decoded when needed
2. **Memoization**: Decoding state is cached to avoid redundant operations
3. **Multi-level Caching**: File contents, source maps, and module graphs are cached separately
4. **Handler Chaining**: Custom handlers are tried in sequence until one succeeds

## Error Handling

### Stack Trace Enhancement

The module enhances error stack traces by:

1. **Position Mapping**: Maps compiled positions to original source positions
2. **Function Name Resolution**: Preserves original function names from source maps
3. **Eval Origin Mapping**: Handles nested eval() calls correctly
4. **Vite-specific Handling**: Identifies and marks Vite-processed source maps

### Fallback Behavior

When source mapping fails:
- Returns original compiled position for accuracy
- Preserves all available debugging information
- Continues processing remaining stack frames
- Logs no errors to avoid disrupting the debugging experience

## Usage Patterns

### Basic Integration

```typescript
// Register stack trace interceptor
const cleanup = interceptStackTrace(moduleRunner, {
  retrieveFile: (path) => {
    // Custom file retrieval logic
    return customFileSystem.readFile(path)
  },
  retrieveSourceMap: (path) => {
    // Custom source map retrieval logic
    return customSourceMapProvider.getMap(path)
  }
})

// Later, cleanup when done
cleanup()
```

### Custom Handler Implementation

Handlers should follow these patterns:
- Return `null` or `undefined` to indicate "not handled, try next"
- Return `false` to indicate "not found, stop trying"
- Return valid data to indicate success
- Handle errors gracefully without throwing

## Related Modules

- [runner-core](runner-core.md) - Module runner core functionality
- [evaluated-modules](evaluated-modules.md) - Module evaluation and caching
- [dev-server](dev-server.md) - Development server with source map support

## Dependencies

### External Dependencies
- `@jridgewell/trace-mapping` - Source map position mapping
- Node.js `Error.prepareStackTrace` - Stack trace customization

### Internal Dependencies
- `../utils` - Path resolution utilities
- `../../shared/utils` - Shared utility functions
- `../evaluatedModules` - Module evaluation tracking
- `../runner` - Module runner integration

## Future Considerations

1. **Performance**: Consider implementing async source map loading for large applications
2. **Memory**: Implement cache size limits to prevent memory growth in long-running processes
3. **Source Map v4**: Prepare for upcoming source map specification changes
4. **WebAssembly**: Consider WASM implementation for performance-critical decoding operations