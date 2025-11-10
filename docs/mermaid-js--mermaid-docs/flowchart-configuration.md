# Flowchart Configuration Module

## Introduction

The flowchart-configuration module defines the configuration interface for flowchart diagrams in Mermaid. It provides a comprehensive set of options that control the appearance, layout, and rendering behavior of flowchart diagrams, from node spacing and curve styles to rendering engine selection and label formatting.

## Architecture Overview

The flowchart configuration system is built around the `FlowchartDiagramConfig` interface, which extends the base diagram configuration and provides flowchart-specific settings. This configuration is integrated into the main Mermaid configuration system and used by the flowchart rendering engine to control diagram appearance and behavior.

```mermaid
graph TB
    subgraph "Configuration System"
        A[MermaidConfig] --> B[FlowchartDiagramConfig]
        B --> C[BaseDiagramConfig]
        B --> D[Flowchart-specific Options]
    end
    
    subgraph "Configuration Usage"
        D --> E[Flowchart Parser]
        D --> F[Flowchart Renderer]
        D --> G[Layout Engine]
        D --> H[Theme System]
    end
    
    subgraph "Rendering Engines"
        I[defaultRenderer] --> J[dagre-d3]
        I --> K[dagre-wrapper]
        I --> L[elk]
    end
    
    style A fill:#e1f5fe
    style B fill:#fff3e0
    style D fill:#f3e5f5
```

## Core Components

### FlowchartDiagramConfig Interface

The `FlowchartDiagramConfig` interface is the central configuration object for flowchart diagrams. It extends `BaseDiagramConfig` and provides flowchart-specific configuration options.

**Key Properties:**

- **Layout Control**: `nodeSpacing`, `rankSpacing`, `diagramPadding`
- **Rendering Control**: `defaultRenderer`, `curve`, `htmlLabels`
- **Text Formatting**: `wrappingWidth`, `padding`, `titleTopMargin`
- **Subgraph Management**: `subGraphTitleMargin`, `inheritDir`

```mermaid
classDiagram
    class FlowchartDiagramConfig {
        +number titleTopMargin
        +object subGraphTitleMargin
        +boolean arrowMarkerAbsolute
        +number diagramPadding
        +boolean htmlLabels
        +number nodeSpacing
        +number rankSpacing
        +string curve
        +number padding
        +string defaultRenderer
        +number wrappingWidth
        +boolean inheritDir
    }
    
    class BaseDiagramConfig {
        +number useWidth
        +boolean useMaxWidth
    }
    
    FlowchartDiagramConfig --|> BaseDiagramConfig
```

## Configuration Categories

### 1. Layout and Spacing Configuration

Controls the spatial arrangement of flowchart elements:

```mermaid
graph LR
    A[Layout Config] --> B[nodeSpacing]
    A --> C[rankSpacing]
    A --> D[diagramPadding]
    A --> E[titleTopMargin]
    A --> F[subGraphTitleMargin]
    
    B --> G[Horizontal/Vertical spacing between nodes]
    C --> H[Spacing between different levels]
    D --> I[Overall diagram margins]
    E --> J[Space above diagram title]
    F --> K[Subgraph title positioning]
```

### 2. Rendering Engine Configuration

Determines which rendering engine is used:

- **`defaultRenderer`**: Selects between 'dagre-d3', 'dagre-wrapper', or 'elk'
- **`curve`**: Controls curve interpolation for connections
- **`htmlLabels`**: Enables/disables HTML label rendering

### 3. Text and Label Configuration

Manages text rendering and formatting:

- **`wrappingWidth`**: Maximum width for text before wrapping
- **`padding`**: Space between labels and shapes
- **`htmlLabels`**: HTML vs plain text rendering

### 4. Subgraph Configuration

Controls subgraph (cluster) behavior:

- **`subGraphTitleMargin`**: Top/bottom margins for subgraph titles
- **`inheritDir`**: Whether subgraphs inherit global direction

## Integration with Mermaid System

The flowchart configuration integrates with the broader Mermaid ecosystem:

```mermaid
graph TB
    subgraph "Mermaid Core"
        A[MermaidConfig]
        B[Configuration Parser]
        C[Theme System]
    end
    
    subgraph "Flowchart Module"
        D[FlowchartDiagramConfig]
        E[FlowDB]
        F[FlowVertex]
        G[FlowEdge]
        H[FlowSubGraph]
    end
    
    subgraph "Rendering Pipeline"
        I[Parser]
        J[Layout Engine]
        K[Renderer]
        L[SVG Output]
    end
    
    A --> D
    D --> E
    D --> F
    D --> G
    D --> H
    
    D --> I
    D --> J
    D --> K
    
    I --> J
    J --> K
    K --> L
    
    C --> D
    B --> D
```

## Configuration Flow

The configuration flows through the system as follows:

```mermaid
sequenceDiagram
    participant User
    participant Mermaid
    participant ConfigParser
    participant FlowchartConfig
    participant Renderer
    participant Output
    
    User->>Mermaid: Initialize with config
    Mermaid->>ConfigParser: Parse configuration
    ConfigParser->>FlowchartConfig: Create FlowchartDiagramConfig
    User->>Mermaid: Render flowchart
    Mermaid->>Renderer: Pass config to renderer
    Renderer->>FlowchartConfig: Apply settings
    Renderer->>Output: Generate SVG with config
```

## Related Modules

The flowchart configuration module interacts with several other modules:

- **[diagram-flowchart](diagram-flowchart.md)**: Main flowchart diagram implementation
- **[mermaid-core-api](mermaid-core-api.md)**: Core configuration system
- **[rendering-engine](rendering-engine.md)**: Rendering infrastructure
- **[theme-system](theme-system.md)**: Theme and styling system

## Usage Examples

### Basic Configuration

```javascript
mermaid.initialize({
  flowchart: {
    nodeSpacing: 50,
    rankSpacing: 80,
    curve: 'basis',
    defaultRenderer: 'dagre-wrapper'
  }
});
```

### Advanced Configuration

```javascript
mermaid.initialize({
  flowchart: {
    titleTopMargin: 25,
    subGraphTitleMargin: { top: 10, bottom: 5 },
    diagramPadding: 20,
    htmlLabels: true,
    nodeSpacing: 60,
    rankSpacing: 100,
    curve: 'cardinal',
    padding: 15,
    defaultRenderer: 'elk',
    wrappingWidth: 200,
    inheritDir: true
  }
});
```

## Configuration Validation

The configuration system validates settings and provides defaults:

```mermaid
graph TD
    A[User Config] --> B{Validation}
    B -->|Valid| C[Apply Config]
    B -->|Invalid| D[Use Default]
    C --> E[Render Diagram]
    D --> E
    
    F[Default Values] --> D
    G[Schema Validation] --> B
```

## Performance Considerations

Different configuration options can impact rendering performance:

- **`defaultRenderer`**: 'elk' may be slower for large diagrams but produces better layouts
- **`curve`**: Complex curves (catmullRom, cardinal) require more computation
- **`htmlLabels`**: HTML rendering is slower than plain text
- **`nodeSpacing`/`rankSpacing`**: Larger values increase diagram size and rendering time

## Best Practices

1. **Choose appropriate renderer**: Use 'dagre-wrapper' for most cases, 'elk' for complex layouts
2. **Optimize spacing**: Balance between readability and diagram size
3. **Use consistent curves**: Stick to one curve type for visual consistency
4. **Consider HTML labels**: Enable only when formatting is needed
5. **Test with inheritDir**: Useful for maintaining consistent subgraph directions

## Migration and Compatibility

The configuration system maintains backward compatibility while allowing for new features:

- Legacy configurations are automatically converted
- New options have sensible defaults
- Deprecation warnings guide users to new options
- Version-specific configuration validation ensures compatibility