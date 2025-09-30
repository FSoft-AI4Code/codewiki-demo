# Core Mermaid Module Documentation

## Introduction

The core-mermaid module serves as the main entry point and orchestration layer for the Mermaid diagramming library. It provides the primary API surface for users to render diagrams, manage configurations, and handle the complete diagram lifecycle from text parsing to SVG rendering. This module acts as the facade that coordinates between various specialized subsystems including diagram detection, parsing, rendering, and configuration management.

## Architecture Overview

The core-mermaid module follows a layered architecture pattern with clear separation of concerns:

```mermaid
graph TB
    subgraph "Core Mermaid Layer"
        Mermaid[Mermaid API]
        RunOptions[RunOptions]
    end
    
    subgraph "API Layer"
        mermaidAPI[mermaidAPI]
        parse[parse]
        render[render]
    end
    
    subgraph "Orchestration Layer"
        diagramAPI[Diagram API]
        detectType[detectType]
        loadDiagram[loadDiagram]
    end
    
    subgraph "Configuration Layer"
        MermaidConfig[MermaidConfig]
        diagramConfig[Diagram-specific Configs]
    end
    
    subgraph "Rendering Layer"
        renderUtil[Rendering Utils]
        themes[Themes]
        layout[Layout Algorithms]
    end
    
    Mermaid --> mermaidAPI
    Mermaid --> parse
    Mermaid --> render
    parse --> diagramAPI
    render --> mermaidAPI
    mermaidAPI --> detectType
    mermaidAPI --> diagramAPI
    diagramAPI --> loadDiagram
    mermaidAPI --> MermaidConfig
    MermaidConfig --> diagramConfig
    mermaidAPI --> renderUtil
    renderUtil --> themes
    renderUtil --> layout
```

## Core Components

### Mermaid Class

The `Mermaid` class is the primary interface exposed to users, providing a comprehensive set of methods for diagram processing:

```mermaid
classDiagram
    class Mermaid {
        +boolean startOnLoad
        +ParseErrorFunction parseError
        +mermaidAPI mermaidAPI
        +parse(text, parseOptions)
        +render(id, text, container)
        +init(config, nodes, callback)
        +run(options)
        +registerLayoutLoaders(loaders)
        +registerExternalDiagrams(diagrams, opts)
        +initialize(config)
        +contentLoaded()
        +setParseErrorHandler(handler)
        +detectType(text)
        +registerIconPacks()
        +getRegisteredDiagramsMetadata()
    }
```

### RunOptions Interface

The `RunOptions` interface defines configuration options for the diagram rendering process:

```mermaid
classDiagram
    class RunOptions {
        +string querySelector
        +ArrayLike~HTMLElement~ nodes
        +Function postRenderCallback
        +boolean suppressErrors
    }
```

## Data Flow Architecture

### Diagram Processing Pipeline

The core processing pipeline follows a sequential flow from text input to rendered SVG:

```mermaid
sequenceDiagram
    participant User
    participant Mermaid
    participant mermaidAPI
    participant DiagramAPI
    participant Parser
    participant Renderer
    participant DOM
    
    User->>Mermaid: render(id, text, container)
    Mermaid->>Mermaid: Queue execution
    Mermaid->>mermaidAPI: render(id, text, container)
    mermaidAPI->>DiagramAPI: detectType(text)
    DiagramAPI-->>mermaidAPI: diagramType
    mermaidAPI->>Parser: parse(text, options)
    Parser-->>mermaidAPI: ParseResult
    mermaidAPI->>Renderer: render(diagram, config)
    Renderer-->>mermaidAPI: {svg, bindFunctions}
    mermaidAPI-->>Mermaid: {svg, bindFunctions}
    Mermaid-->>User: {svg, bindFunctions}
    User->>DOM: element.innerHTML = svg
    User->>DOM: bindFunctions(element)
```

### Configuration Flow

Configuration management follows a hierarchical approach:

```mermaid
graph TD
    A[User Configuration] --> B[initialize]
    B --> C[mermaidAPI.updateSiteConfig]
    C --> D[Global Configuration]
    D --> E[Diagram-specific Config]
    E --> F[Render Options]
    F --> G[SVG Output]
    
    H[Default Configs] --> D
    I[Theme Configs] --> D
    J[Layout Configs] --> D
```

## Component Interactions

### Execution Queue Management

The core module implements a sophisticated execution queue to handle concurrent rendering requests:

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Queued: render()/parse() called
    Queued --> Processing: executeQueue()
    Processing --> Completed: Promise resolved
    Processing --> Error: Promise rejected
    Error --> Idle: Error handled
    Completed --> Idle: Queue empty
    
    state Processing {
        [*] --> Executing
        Executing --> Next: Function completed
        Next --> Executing: More functions
        Next --> [*]: Queue empty
    }
```

### Error Handling Flow

Comprehensive error handling ensures graceful degradation:

```mermaid
graph TD
    A[Error Occurred] --> B{Error Type}
    B -->|DetailedError| C[Extract str, hash]
    B -->|Regular Error| D[Create DetailedError]
    B -->|String| E[Wrap in DetailedError]
    
    C --> F[Call parseError callback]
    D --> F
    E --> F
    
    F --> G{suppressErrors?}
    G -->|true| H[Log error, continue]
    G -->|false| I[Throw error]
    
    F --> J[Add to errors array]
    J --> K{errors.length > 0?}
    K -->|true| I
    K -->|false| L[Continue processing]
```

## Integration Points

### External Diagram Registration

The module supports dynamic registration of external diagram types:

```mermaid
graph LR
    A[External Diagram] --> B[registerExternalDiagrams]
    B --> C{lazyLoad?}
    C -->|true| D[Register for lazy loading]
    C -->|false| E[Load immediately]
    D --> F[Detectors updated]
    E --> G[Diagrams loaded]
    G --> F
```

### DOM Integration

Automatic DOM processing on page load:

```mermaid
graph TD
    A[Page Load] --> B[contentLoaded event]
    B --> C{startOnLoad enabled?}
    C -->|true| D[mermaid.run]
    C -->|false| E[Wait for manual trigger]
    D --> F[Query DOM for .mermaid]
    F --> G[Process each element]
    G --> H[Set data-processed attribute]
    H --> I[Render diagram]
```

## Configuration Management

### Hierarchical Configuration System

The configuration system supports multiple levels of customization:

```mermaid
graph TD
    subgraph "Configuration Levels"
        A1[Global Site Config]
        A2[Diagram Type Config]
        A3[Instance Config]
        A4[Render Options]
    end
    
    B[User Input] --> C[initialize]
    C --> D[updateSiteConfig]
    D --> A1
    A1 --> A2
    A2 --> A3
    A3 --> A4
    A4 --> E[Final Render]
```

## Key Features

### 1. Multi-Diagram Support
Supports 20+ diagram types through a unified API:
- Flowcharts, Sequence diagrams, Class diagrams
- State diagrams, ER diagrams, Git graphs
- Pie charts, Mind maps, Quadrant charts
- Radar charts, Sankey diagrams, Timeline diagrams
- And many more specialized diagram types

### 2. Theme System
Comprehensive theming with built-in themes:
- Default, Dark, Forest, Neutral themes
- Customizable color schemes and styling
- Per-diagram theme overrides

### 3. Layout Algorithms
Flexible layout system supporting:
- Multiple layout algorithms (dagre, elk, etc.)
- Custom layout loaders
- Automatic layout selection based on diagram type

### 4. Error Handling
Robust error management:
- Detailed error reporting with context
- Graceful degradation options
- Custom error handlers
- Parse error callbacks

## Dependencies

The core-mermaid module orchestrates multiple specialized modules:

- **[config](config.md)**: Configuration management and type definitions
- **[diagram-api](diagram-api.md)**: Diagram detection and API abstraction
- **[rendering-util](rendering-util.md)**: Rendering utilities and layout management
- **[themes](themes.md)**: Theme system and styling
- **[types](types.md)**: Common type definitions
- **[utils](utils.md)**: Utility functions and helpers

## Usage Patterns

### Basic Usage
```javascript
// Initialize with configuration
mermaid.initialize({
  startOnLoad: true,
  theme: 'dark'
});

// Render specific diagram
const { svg } = await mermaid.render('diagram-id', 'graph TD; A-->B;');
```

### Advanced Usage
```javascript
// Register custom diagrams
await mermaid.registerExternalDiagrams([customDiagram]);

// Custom error handling
mermaid.setParseErrorHandler((err, hash) => {
  console.error('Parse error:', err);
});

// Batch processing
await mermaid.run({
  querySelector: '.my-diagrams',
  postRenderCallback: (id) => console.log(`Rendered: ${id}`)
});
```

## Performance Considerations

### Execution Queue
- Serializes concurrent render requests
- Prevents race conditions
- Maintains consistent state

### Lazy Loading
- Diagrams loaded on-demand
- Reduces initial bundle size
- Improves startup performance

### Caching
- Processed elements marked with data-processed
- Prevents duplicate processing
- Efficient DOM querying

## Security Considerations

### Content Sanitization
- HTML entity decoding
- XSS prevention measures
- Safe DOM manipulation

### Configuration Validation
- Type-safe configuration
- Runtime validation
- Secure defaults

This documentation provides a comprehensive overview of the core-mermaid module's architecture, functionality, and integration points. For detailed information about specific diagram types, configuration options, or rendering utilities, refer to the respective module documentation.