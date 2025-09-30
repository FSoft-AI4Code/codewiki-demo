# Configuration System Module

## Introduction

The configuration system module is the central configuration management system for Chart.js. It provides a hierarchical configuration structure that handles chart defaults, overrides, and dynamic option resolution. This module ensures consistent behavior across all chart types while allowing flexible customization at multiple levels.

## Core Components

### Config Class (`src.core.core.config.Config`)
The main configuration manager that handles chart configuration initialization, option resolution, and caching mechanisms.

### Defaults Class (`src.core.core.defaults.Defaults`)
The global defaults manager that provides default values for all chart properties and manages the defaults hierarchy.

## Architecture

```mermaid
graph TB
    subgraph "Configuration System"
        Config[Config Class]
        Defaults[Defaults Class]
        Overrides[overrides object]
        Descriptors[descriptors object]
    end
    
    subgraph "External Dependencies"
        Helpers[Helpers]
        Animations[Animation System]
        Scales[Scale System]
        Layouts[Layout System]
    end
    
    Config -->|uses| Defaults
    Config -->|uses| Overrides
    Config -->|uses| Descriptors
    Defaults -->|creates| Overrides
    Defaults -->|creates| Descriptors
    Defaults -->|applies| Animations
    Defaults -->|applies| Scales
    Defaults -->|applies| Layouts
    Config -->|uses| Helpers
```

## Configuration Hierarchy

```mermaid
graph TD
    A[Chart Instance Options] -->|highest priority| B[Option Resolution]
    C[Chart Type Overrides] --> B
    D[Dataset Defaults] --> B
    E[Global Defaults] --> B
    F[Descriptors] -->|lowest priority| B
    
    B --> G[Final Configuration]
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style G fill:#9f9,stroke:#333,stroke-width:2px
```

## Data Flow

```mermaid
sequenceDiagram
    participant Chart
    participant Config
    participant Defaults
    participant Resolver
    
    Chart->>Config: new Config(config)
    Config->>Config: initConfig(config)
    Config->>Config: initData(data)
    Config->>Config: initOptions(options)
    Config->>Defaults: mergeScaleConfig()
    
    Chart->>Config: getOptionScopes()
    Config->>Config: _cachedScopes()
    Config->>Resolver: getResolver()
    Resolver-->>Config: resolver instance
    Config-->>Chart: option scopes array
    
    Chart->>Config: resolveNamedOptions()
    Config->>Resolver: resolve options
    Resolver-->>Config: resolved values
    Config-->>Chart: final options
```

## Component Interactions

```mermaid
graph LR
    subgraph "Option Resolution Process"
        A[Chart Request] --> B[Config.getOptionScopes]
        B --> C[Scope Cache Check]
        C -->|Cache Hit| D[Return Cached Scopes]
        C -->|Cache Miss| E[Build Scopes]
        E --> F[Add Main Scope]
        F --> G[Add Options]
        G --> H[Add Overrides]
        I[Add Defaults] --> J[Add Descriptors]
        J --> K[Cache Result]
        K --> D
    end
```

## Key Features

### 1. Hierarchical Configuration
The system supports multiple levels of configuration with clear precedence:
- Chart instance options (highest priority)
- Chart type-specific overrides
- Dataset-level defaults
- Global defaults
- Descriptor defaults (lowest priority)

### 2. Dynamic Option Resolution
Options are resolved dynamically using a sophisticated caching mechanism that considers:
- Scriptable options (functions that receive context)
- Indexable options (arrays that map to data indices)
- Nested option structures

### 3. Scale Configuration Management
Specialized handling for scale configurations including:
- Automatic axis detection from position and ID
- Dataset-specific scale overrides
- Default scale option merging
- Index axis determination

### 4. Caching System
Multiple levels of caching for performance:
- Scope cache for option resolution contexts
- Resolver cache for option resolvers
- Key cache for scope key generation

## Configuration Process Flow

```mermaid
flowchart TD
    Start[Chart Creation] --> InitConfig[Initialize Config]
    InitConfig --> InitData[Initialize Data]
    InitData --> InitOptions[Initialize Options]
    InitOptions --> MergeScales[Merge Scale Configs]
    
    MergeScales --> ProcessDatasets[Process Dataset Defaults]
    ProcessDatasets --> ApplyOverrides[Apply Chart Overrides]
    ApplyOverrides --> ApplyDefaults[Apply Global Defaults]
    ApplyDefaults --> FinalConfig[Final Configuration]
    
    style Start fill:#ff9
    style FinalConfig fill:#9f9
```

## Integration with Other Systems

### Animation System
The configuration system provides animation defaults and handles animation-specific option resolution. See [animation-system.md](animation-system.md) for details.

### Scale System
Manages scale configurations and provides scale-specific defaults. Scale options are merged from multiple sources including dataset defaults and chart type overrides.

### Plugin System
Handles plugin option resolution through dedicated scope keys and supports plugin-specific option routing.

## API Reference

### Config Class Methods

#### `getOptionScopes(mainScope, keyLists, resetCache)`
Returns an array of option scopes for resolution based on the provided key lists.

#### `resolveNamedOptions(scopes, names, context, prefixes)`
Resolves named options from the provided scopes, handling scriptable and indexable options.

#### `createResolver(scopes, context, prefixes, descriptorDefaults)`
Creates a resolver for the given scopes and context.

#### `datasetScopeKeys(datasetType)`
Returns scope keys for resolving dataset options.

#### `datasetAnimationScopeKeys(datasetType, transition)`
Returns scope keys for resolving dataset animation options.

### Defaults Class Methods

#### `set(scope, values)`
Sets default values for the specified scope.

#### `get(scope)`
Gets default values for the specified scope.

#### `describe(scope, values)`
Sets descriptor defaults for the specified scope.

#### `override(scope, values)`
Sets override values for the specified scope.

#### `route(scope, name, targetScope, targetName)`
Routes a property to fallback to another scope when not defined locally.

## Usage Examples

### Basic Configuration
```javascript
const config = new Config({
  type: 'line',
  data: {
    datasets: [{
      data: [1, 2, 3]
    }]
  },
  options: {
    responsive: true
  }
});
```

### Option Resolution
```javascript
const scopes = config.getOptionScopes(dataset, [
  ['datasets.line', ''],
  ['elements.point', '']
]);
const options = config.resolveNamedOptions(scopes, ['backgroundColor', 'borderColor'], context);
```

### Default Configuration
```javascript
defaults.set('scales.linear', {
  ticks: {
    maxTicksLimit: 11
  }
});
```

## Performance Considerations

1. **Caching Strategy**: The system uses aggressive caching to avoid repeated option resolution
2. **Lazy Resolution**: Options are resolved only when needed
3. **Scope Optimization**: Scope keys are cached to minimize lookup overhead
4. **Memory Management**: Cache clearing mechanisms prevent memory leaks

## Error Handling

The configuration system includes several validation mechanisms:
- Invalid scale configurations are logged as errors
- Proxy warnings prevent resolver conflicts
- Axis determination throws descriptive errors for invalid configurations

## Extension Points

The system is designed for extensibility through:
- Custom option scopes
- Plugin-specific configuration
- Dynamic defaults application
- Custom descriptor definitions