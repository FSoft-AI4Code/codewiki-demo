# Plugin System Module

## Introduction

The plugin system module is the core extensibility framework of Vite, providing a powerful and flexible plugin architecture that extends Rollup's plugin interface with Vite-specific functionality. It enables developers to customize and extend Vite's behavior across development, build, and preview environments through a comprehensive hook system.

## Architecture Overview

```mermaid
graph TB
    subgraph "Plugin System Core"
        P[Plugin Interface]
        PC[Plugin Context]
        MPC[Minimal Plugin Context]
        CPC[Config Plugin Context]
        PCM[Plugin Context Meta]
    end

    subgraph "Plugin Types"
        AP[App Plugins]
        EP[Environment Plugins]
        SP[Shared Plugins]
    end

    subgraph "Hook System"
        CH[Config Hooks]
        DH[Dev Hooks]
        BH[Build Hooks]
        HH[HMR Hooks]
    end

    subgraph "Plugin Container"
        PCO[Plugin Container]
        EPC[Environment Plugin Container]
        TPC[Transform Plugin Context]
        LPC[Load Plugin Context]
    end

    P --> PC
    P --> MPC
    P --> PCM
    
    AP --> CH
    EP --> DH
    SP --> BH
    
    PC --> PCO
    PCO --> EPC
    EPC --> TPC
    EPC --> LPC
    
    DH --> HH
```

## Core Components

### Plugin Interface

The `Plugin` interface is the central abstraction that extends Rollup's plugin system with Vite-specific enhancements:

```mermaid
classDiagram
    class Plugin {
        <<interface>>
        +name: string
        +enforce?: 'pre' | 'post'
        +apply?: 'serve' | 'build' | function
        +config?: ObjectHook
        +configEnvironment?: ObjectHook
        +configResolved?: ObjectHook
        +configureServer?: ObjectHook
        +configurePreviewServer?: ObjectHook
        +transformIndexHtml?: IndexHtmlTransform
        +handleHotUpdate?: ObjectHook
        +hotUpdate?: ObjectHook
        +sharedDuringBuild?: boolean
        +perEnvironmentStartEndDuringDev?: boolean
        +applyToEnvironment?: function
    }
```

### Plugin Context System

The plugin context system provides different levels of context access depending on the plugin's scope:

```mermaid
graph LR
    subgraph "Context Hierarchy"
        MPC[MinimalPluginContext] --> PC[PluginContext]
        PC --> TPC[TransformPluginContext]
        MPC --> CPC[ConfigPluginContext]
        MPC --> MPCE[MinimalPluginContextWithoutEnvironment]
    end

    subgraph "Extensions"
        PCE[PluginContextExtension] --> MPC
        PCME[PluginContextMetaExtension] --> PCM[PluginContextMeta]
    end
```

## Plugin Types and Lifecycle

### App Plugins vs Environment Plugins

```mermaid
stateDiagram-v2
    [*] --> PluginRegistration
    
    state PluginRegistration {
        [*] --> AppPlugin
        [*] --> EnvironmentPlugin
        
        AppPlugin --> ConfigHook: config
        AppPlugin --> ConfigResolvedHook: configResolved
        AppPlugin --> ConfigureServerHook: configureServer
        AppPlugin --> ConfigurePreviewHook: configurePreviewServer
        
        EnvironmentPlugin --> EnvironmentSpecific: applyToEnvironment
        EnvironmentPlugin --> PerEnvironmentHooks: per-environment
    }
    
    ConfigHook --> ServerStart: if serve
    ConfigHook --> BuildStart: if build
    
    ConfigureServerHook --> HMRReady
    ConfigurePreviewHook --> PreviewReady
    
    ServerStart --> RuntimeHooks: resolveId, load, transform
    BuildStart --> BuildHooks: resolveId, load, transform, generateBundle
```

### Plugin Application Logic

```mermaid
flowchart TD
    Start[Plugin Registration] --> CheckApply{apply condition?}
    CheckApply -->|true| CheckApplyToEnv{applyToEnvironment?}
    CheckApply -->|false| Skip[Skip Plugin]
    
    CheckApplyToEnv -->|function| EvaluateEnv[Evaluate Environment]
    CheckApplyToEnv -->|boolean| CheckBoolean{true?}
    CheckApplyToEnv -->|PluginOption| FlattenOptions[Flatten Options]
    
    EvaluateEnv -->|true| AddToEnv[Add to Environment]
    EvaluateEnv -->|false| Skip
    
    CheckBoolean -->|true| AddToEnv
    CheckBoolean -->|false| Skip
    
    FlattenOptions --> ProcessOptions[Process Plugin Options]
    ProcessOptions --> AddToEnv
    
    AddToEnv --> RegisterHooks[Register Hooks]
    RegisterHooks --> End[Plugin Active]
    Skip --> End
```

## Hook System Architecture

### Hook Types and Execution Order

```mermaid
graph TD
    subgraph "Hook Categories"
        Config[Config Hooks]
        Server[Server Hooks]
        Transform[Transform Hooks]
        HMR[HMR Hooks]
        Build[Build Hooks]
    end

    subgraph "Execution Order"
        Pre[enforce: 'pre']
        Normal[normal]
        Post[enforce: 'post']
    end

    subgraph "Hook Examples"
        config[config hook]
        configResolved[configResolved hook]
        configureServer[configureServer hook]
        resolveId[resolveId hook]
        load[load hook]
        transform[transform hook]
        handleHotUpdate[handleHotUpdate hook]
        hotUpdate[hotUpdate hook]
    end

    Config --> config
    Config --> configResolved
    Server --> configureServer
    Transform --> resolveId
    Transform --> load
    Transform --> transform
    HMR --> handleHotUpdate
    HMR --> hotUpdate

    Pre --> Normal
    Normal --> Post
```

### Transform Pipeline Integration

```mermaid
sequenceDiagram
    participant Request as Module Request
    participant PluginContainer as Plugin Container
    participant ResolveHook as resolveId Hook
    participant LoadHook as load Hook
    participant TransformHook as transform Hook
    participant ModuleGraph as Module Graph

    Request->>PluginContainer: Request module
    PluginContainer->>ResolveHook: resolveId(id, importer)
    ResolveHook-->>PluginContainer: Resolved ID
    PluginContainer->>LoadHook: load(id)
    LoadHook-->>PluginContainer: Module content
    PluginContainer->>TransformHook: transform(code, id)
    TransformHook-->>PluginContainer: Transformed code
    PluginContainer->>ModuleGraph: Update module info
    ModuleGraph-->>Request: Return processed module
```

## Environment-Specific Plugin Behavior

### Plugin Environment Resolution

```mermaid
flowchart LR
    subgraph "Environment Types"
        Dev[Dev Environment]
        Build[Build Environment]
        Scan[Scan Environment]
    end

    subgraph "Plugin Application"
        Shared[Shared Plugins]
        DevSpecific[Dev-Specific]
        BuildSpecific[Build-Specific]
        PerEnv[Per-Environment]
    end

    Dev --> DevSpecific
    Build --> BuildSpecific
    Dev --> Shared
    Build --> Shared
    
    PerEnv -.-> Dev
    PerEnv -.-> Build
    PerEnv -.-> Scan
```

### Hot Module Replacement (HMR) Integration

```mermaid
graph TB
    subgraph "HMR Plugin Hooks"
        HHU[handleHotUpdate]
        HU[hotUpdate]
    end

    subgraph "HMR Context"
        HC[HmrContext]
        HUO[HotUpdateOptions]
        EMN[EnvironmentModuleNode]
    end

    subgraph "HMR Flow"
        FileChange[File Change Detected]
        ModuleUpdate[Module Update]
        CustomUpdate[Custom Update]
        FullReload[Full Reload]
    end

    FileChange --> HHU
    HHU -->|returns modules| ModuleUpdate
    HHU -->|returns empty| CustomUpdate
    HHU -->|returns void| FullReload
    
    HU -->|environment-specific| EMN
    HC -->|provides context| HHU
    HUO -->|options| HU
```

## Plugin Container Integration

The plugin system works closely with the [plugin-container](plugin-container.md) module to manage plugin execution:

```mermaid
graph LR
    subgraph "Plugin System"
        PI[Plugin Interface]
        PH[Plugin Hooks]
        PC[Plugin Context]
    end

    subgraph "Plugin Container"
        PCO[PluginContainer]
        EPC[EnvironmentPluginContainer]
        TPC[TransformPluginContext]
    end

    subgraph "Execution"
        MH[Module Resolution]
        TH[Transform Handling]
        HH[HMR Handling]
    end

    PI --> PCO
    PH --> EPC
    PC --> TPC
    
    PCO --> MH
    EPC --> TH
    TPC --> HH
```

## Configuration and Lifecycle

### Plugin Configuration Flow

```mermaid
sequenceDiagram
    participant Vite as Vite Core
    participant Plugin as Plugin System
    participant Config as Config System
    participant Server as Dev Server
    participant Build as Build System

    Vite->>Plugin: Register plugins
    Plugin->>Config: Execute config hooks
    Config-->>Plugin: Modified config
    Plugin->>Config: Execute configResolved hooks
    
    alt Development Mode
        Vite->>Server: Create dev server
        Plugin->>Server: Execute configureServer hooks
        Server-->>Plugin: Server instance
        Plugin->>Server: Set up HMR handlers
    else Build Mode
        Vite->>Build: Create build environment
        Plugin->>Build: Execute build hooks
    end
```

### Plugin Hook Execution Context

```mermaid
graph TB
    subgraph "Hook Context Types"
        ConfigCtx[ConfigPluginContext]
        MinimalCtx[MinimalPluginContext]
        TransformCtx[TransformPluginContext]
        DevCtx[Dev Environment Context]
    end

    subgraph "Available Data"
        ConfigData[Config Data]
        EnvData[Environment Data]
        ModuleData[Module Data]
        ServerData[Server Data]
    end

    subgraph "Hook Types"
        ConfigHooks[config, configResolved]
        TransformHooks[resolveId, load, transform]
        ServerHooks[configureServer, configurePreviewServer]
        HMRHooks[handleHotUpdate, hotUpdate]
    end

    ConfigCtx --> ConfigData
    MinimalCtx --> EnvData
    TransformCtx --> ModuleData
    DevCtx --> ServerData
    
    ConfigHooks --> ConfigCtx
    TransformHooks --> TransformCtx
    ServerHooks --> MinimalCtx
    HMRHooks --> DevCtx
```

## Integration with Other Modules

### Module Dependencies

```mermaid
graph LR
    subgraph "Plugin System Dependencies"
        PS[Plugin System]
        CS[Config System]
        DSS[Dev Server]
        BS[Build System]
        HMR[HMR System]
        PC[Plugin Container]
    end

    subgraph "External Dependencies"
        Rollup[Rollup Plugin API]
        ViteTypes[Vite Type Definitions]
    end

    PS --> CS
    PS --> DSS
    PS --> BS
    PS --> HMR
    PS --> PC
    
    PS -.-> Rollup
    PS -.-> ViteTypes
```

### Related Documentation

- [plugin-container](plugin-container.md) - Plugin execution and context management
- [config](config.md) - Configuration system that plugins can modify
- [dev-server](dev-server.md) - Development server that plugins can configure
- [build](build.md) - Build system that plugins integrate with
- [hmr](hmr.md) - Hot module replacement system with plugin hooks

## Best Practices and Guidelines

### Plugin Development

1. **Hook Selection**: Choose appropriate hooks based on your plugin's purpose
2. **Context Usage**: Use the correct context type for each hook
3. **Error Handling**: Implement proper error handling in async hooks
4. **Performance**: Consider the performance impact of transform hooks
5. **Compatibility**: Ensure compatibility with both dev and build modes

### Plugin Application

1. **Conditional Application**: Use `apply` property for environment-specific plugins
2. **Environment Filtering**: Use `applyToEnvironment` for fine-grained control
3. **Hook Ordering**: Use `enforce` property to control hook execution order
4. **Shared Plugins**: Consider `sharedDuringBuild` for build optimization
5. **Per-Environment Hooks**: Use `perEnvironmentStartEndDuringDev` for dev-specific behavior

## API Reference

### Core Interfaces

- `Plugin<A = any>` - Main plugin interface extending RollupPlugin
- `PluginContextExtension` - Vite-specific environment extension
- `PluginContextMetaExtension` - Vite version metadata
- `ConfigPluginContext` - Context for config hooks
- `MinimalPluginContextWithoutEnvironment` - Minimal context without environment access

### Utility Functions

- `resolveEnvironmentPlugins(environment)` - Resolves plugins for a specific environment
- `perEnvironmentPlugin(name, applyToEnvironment)` - Creates environment-specific plugins

### Hook Types

- `ObjectHook<T, O>` - Type for hooks with options
- `PluginOption` - Union type for plugin configuration
- `FalsyPlugin` - Type for falsy plugin values
- `PluginWithRequiredHook<K>` - Type for plugins with required hooks