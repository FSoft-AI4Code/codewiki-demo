# Dev Environment Module

The dev-environment module is a core component of Vite's development server infrastructure, providing isolated execution environments for different build targets during development. It serves as the foundation for Vite's multi-environment support, enabling developers to work with different JavaScript environments (browser, SSR, worker, etc.) simultaneously within a single development session.

## Overview

The DevEnvironment class extends BaseEnvironment and represents a specific execution environment within Vite's development server. Each environment maintains its own module graph, plugin container, dependency optimizer, and hot module replacement (HMR) channel, allowing for isolated processing and transformation of modules based on the target environment's requirements.

## Architecture

```mermaid
graph TB
    subgraph "Dev Environment Architecture"
        DE[DevEnvironment]
        BC[BaseEnvironment]
        MG[EnvironmentModuleGraph]
        PC[EnvironmentPluginContainer]
        DO[DepsOptimizer]
        HC[NormalizedHotChannel]
        
        DE --> BC
        DE --> MG
        DE --> PC
        DE --> DO
        DE --> HC
    end
    
    subgraph "External Dependencies"
        VS[ViteDevServer]
        RC[ResolvedConfig]
        FM[fetchModule]
        TR[transformRequest]
        
        VS --> DE
        RC --> DE
        DE --> FM
        DE --> TR
    end
```

## Core Components

### DevEnvironment Class

The main class that encapsulates all development environment functionality:

```mermaid
classDiagram
    class DevEnvironment {
        -mode: 'dev'
        -moduleGraph: EnvironmentModuleGraph
        -depsOptimizer: DepsOptimizer
        -_pluginContainer: EnvironmentPluginContainer
        -_pendingRequests: Map
        -_crawlEndFinder: CrawlEndFinder
        -hot: NormalizedHotChannel
        -_closing: boolean
        +init(options): Promise<void>
        +listen(server): Promise<void>
        +fetchModule(id, importer, options): Promise<FetchResult>
        +transformRequest(url, options): Promise<TransformResult>
        +warmupRequest(url): Promise<void>
        +close(): Promise<void>
        +waitForRequestsIdle(ignoredId): Promise<void>
    }
```

### DevEnvironmentContext Interface

Configuration context for creating a DevEnvironment instance:

```typescript
interface DevEnvironmentContext {
  hot: boolean                    // Enable HMR
  transport?: HotChannel | WebSocketServer  // HMR transport
  options?: EnvironmentOptions    // Environment-specific options
  remoteRunner?: {
    inlineSourceMap?: boolean     // Source map configuration for remote runners
  }
  depsOptimizer?: DepsOptimizer   // Optional dependency optimizer
}
```

## Key Features

### 1. Module Graph Management

Each DevEnvironment maintains its own module graph through the `EnvironmentModuleGraph` class, which tracks module dependencies, imports, and transformations specific to that environment.

```mermaid
graph LR
    subgraph "Module Graph Flow"
        URL[URL Request] --> MG[EnvironmentModuleGraph]
        MG --> PC[PluginContainer.resolveId]
        PC --> MN[ModuleNode]
        MN --> TR[TransformRequest]
        TR --> TM[Transformed Module]
    end
```

### 2. Dependency Optimization

The environment integrates with Vite's dependency optimizer to handle pre-bundling of dependencies:

```mermaid
graph TD
    subgraph "Dependency Optimization Flow"
        DE[DevEnvironment] --> OD{optimizeDeps.enabled?}
        OD -->|Yes| DO[DepsOptimizer]
        OD -->|No| ND[No Optimization]
        DO --> ND
        
        DO --> ND1[createDepsOptimizer]
        DO --> ND2[createExplicitDepsOptimizer]
        
        ND1 --> |discovery| DO1[Full Optimization]
        ND2 --> |noDiscovery| DO2[Explicit Only]
    end
```

### 3. Hot Module Replacement (HMR)

Each environment has its own HMR channel for managing hot updates:

```mermaid
sequenceDiagram
    participant Client
    participant HotChannel
    participant DevEnvironment
    participant ModuleGraph
    
    Client->>HotChannel: Request Update
    HotChannel->>DevEnvironment: fetchModule
    DevEnvironment->>ModuleGraph: Check Dependencies
    DevEnvironment->>DevEnvironment: transformRequest
    DevEnvironment->>HotChannel: Send Update
    HotChannel->>Client: Apply Update
```

### 4. Request Management

The environment implements sophisticated request tracking and caching:

```mermaid
graph TB
    subgraph "Request Processing"
        RQ[Request] --> PC{Pending Check}
        PC -->|Exists| CR[Cached Request]
        PC -->|New| NR[New Request]
        
        NR --> TR[TransformRequest]
        TR --> CC[Cache Result]
        CC --> RP[Return Promise]
        
        CR --> RP
    end
```

## Lifecycle Management

### Environment Initialization

```mermaid
sequenceDiagram
    participant Config
    participant DevEnvironment
    participant PluginContainer
    participant ModuleGraph
    
    Config->>DevEnvironment: new DevEnvironment()
    DevEnvironment->>DevEnvironment: Initialize Properties
    DevEnvironment->>ModuleGraph: Create Module Graph
    DevEnvironment->>DevEnvironment: Setup HMR
    DevEnvironment->>DevEnvironment: Configure DepsOptimizer
    
    Note over DevEnvironment: Environment Created
    
    Config->>DevEnvironment: init()
    DevEnvironment->>PluginContainer: createEnvironmentPluginContainer()
    PluginContainer-->>DevEnvironment: PluginContainer Ready
    DevEnvironment-->>Config: Initialization Complete
```

### Request Processing Flow

```mermaid
graph TD
    subgraph "Transform Request Flow"
        RQ[transformRequest] --> PC{PluginContainer Ready?}
        PC -->|No| ER[Throw Error]
        PC -->|Yes| CC{Cache Check}
        
        CC -->|Hit| CR[Return Cached]
        CC -->|Miss| TR[Transform Module]
        
        TR --> PI[Plugin Processing]
        PI --> LM[Load Module]
        LM --> TRA[Transform]
        TRA --> SR[Store Result]
        SR --> RP[Return Result]
        
        CR --> RP
    end
```

## Integration with Other Modules

### Module Runner Integration

The DevEnvironment works closely with the [module-runner](module-runner.md) system:

```mermaid
graph LR
    subgraph "Module Runner Integration"
        DE[DevEnvironment] --> FM[fetchModule]
        FM --> MR[ModuleRunner]
        MR --> EM[ESModulesEvaluator]
        EM --> EMN[EvaluatedModuleNode]
    end
```

### Plugin System Integration

Integration with the [plugin-system](plugin-system.md) and [plugin-container](plugin-container.md):

```mermaid
graph TB
    subgraph "Plugin System Integration"
        DE[DevEnvironment] --> PC[EnvironmentPluginContainer]
        PC --> PS[Plugin System]
        PS --> PL[Plugins]
        PL --> TR[Transform Hooks]
        PL --> LR[Load Hooks]
        PL --> RS[Resolve Hooks]
    end
```

### HMR System Integration

Integration with the [hmr](hmr.md) system:

```mermaid
graph LR
    subgraph "HMR Integration"
        DE[DevEnvironment] --> HC[HotChannel]
        HC --> HU[Hot Update]
        HU --> UM[Update Modules]
        UM --> MG[Module Graph]
    end
```

## Configuration

The DevEnvironment is configured through the `DevEnvironmentContext` and the main Vite configuration:

```typescript
// Environment context configuration
const context: DevEnvironmentContext = {
  hot: true,                    // Enable HMR
  transport: hotChannel,       // HMR transport mechanism
  options: environmentOptions, // Environment-specific options
  remoteRunner: {
    inlineSourceMap: true      // Source map configuration
  },
  depsOptimizer: optimizer     // Optional custom optimizer
}

// Create environment
const environment = new DevEnvironment('client', config, context)
```

## Error Handling

The environment implements comprehensive error handling for various scenarios:

```mermaid
graph TD
    subgraph "Error Handling"
        OP[Operation] --> TE{Transform Error}
        TE -->|Outdated Dep| OD[ERR_OUTDATED_OPTIMIZED_DEP]
        TE -->|Closed Server| CS[ERR_CLOSED_SERVER]
        TE -->|Other| OE[Log Error]
        
        OD --> IG[Ignore]
        CS --> IG
        OE --> LG[Log and Continue]
    end
```

## Performance Optimizations

### Request Caching

The environment maintains a pending requests cache to avoid duplicate transformations:

```typescript
_pendingRequests: Map<string, {
  request: Promise<TransformResult | null>
  timestamp: number
  abort: () => void
}>
```

### Crawl End Detection

Implements intelligent crawl end detection to optimize module graph processing:

```mermaid
graph LR
    subgraph "Crawl End Detection"
        RP[Register Processing] --> WD[Wait Done]
        WD --> CC{Check Complete}
        CC -->|Pending| WT[Wait Timeout]
        CC -->|Complete| RE[Resolve]
        WT --> CC
    end
```

## Usage Examples

### Basic Environment Creation

```typescript
import { DevEnvironment } from 'vite'

const environment = new DevEnvironment('client', config, {
  hot: true,
  transport: webSocketServer
})

await environment.init()
await environment.listen(devServer)
```

### Module Fetching

```typescript
// Fetch a module for transformation
const result = await environment.fetchModule('./src/main.js')

// Transform a request
const transformed = await environment.transformRequest('/src/App.vue')
```

### HMR Usage

```typescript
// Send HMR update
environment.hot.send({
  type: 'update',
  updates: [{
    type: 'js-update',
    path: '/src/App.vue',
    acceptedPath: '/src/App.vue'
  }]
})
```

## API Reference

### Constructor

```typescript
new DevEnvironment(name: string, config: ResolvedConfig, context: DevEnvironmentContext)
```

### Methods

- `init(options?)`: Initialize the environment
- `listen(server)`: Start listening for requests
- `fetchModule(id, importer?, options?)`: Fetch and transform a module
- `transformRequest(url, options?)`: Transform a request
- `warmupRequest(url)`: Pre-transform a request
- `close()`: Close the environment
- `waitForRequestsIdle(ignoredId?)`: Wait for pending requests to complete

### Properties

- `mode`: Always 'dev'
- `moduleGraph`: Environment-specific module graph
- `depsOptimizer`: Dependency optimizer instance
- `hot`: HMR channel
- `pluginContainer`: Plugin container for this environment

## Related Documentation

- [Module Runner](module-runner.md) - For module evaluation and execution
- [Plugin System](plugin-system.md) - For plugin development and integration
- [Plugin Container](plugin-container.md) - For plugin context management
- [HMR](hmr.md) - For hot module replacement system
- [Dev Server](dev-server.md) - For overall development server architecture