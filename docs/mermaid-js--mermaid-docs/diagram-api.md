# Diagram API Module

## Overview

The diagram-api module serves as the central orchestration layer for Mermaid's diagram processing system. It provides the core infrastructure for diagram registration, parsing, rendering, and lifecycle management. This module acts as the bridge between the main Mermaid engine and individual diagram types, handling the dynamic loading and initialization of diagram processors.

## Architecture

```mermaid
graph TB
    subgraph "Diagram API Module"
        DA[Diagram API]
        DD[Diagram Definition]
        DIA[Diagram Class]
        TYPES[Type Definitions]
        FM[Frontmatter Handler]
    end
    
    subgraph "Core Mermaid"
        MER[Main Mermaid Engine]
        CONFIG[Config System]
    end
    
    subgraph "Diagram Types"
        FC[Flowchart]
        SEQ[Sequence]
        CL[Class]
        ST[State]
        ER[ER Diagram]
        GIT[Git Graph]
        PIE[Pie Chart]
        MM[Mindmap]
        QC[Quadrant Chart]
        RD[Radar]
        SK[Sankey]
        TL[Timeline]
        TM[Treemap]
        XY[XY Chart]
        ARCH[Architecture]
        BLK[Block]
        C4[C4 Diagram]
        REQ[Requirement]
        PKT[Packet]
    end
    
    subgraph "Rendering System"
        RU[Rendering Utils]
        TH[Themes]
    end
    
    MER --> DA
    DA --> DD
    DA --> DIA
    DA --> TYPES
    DA --> FM
    DD --> FC
    DD --> SEQ
    DD --> CL
    DD --> ST
    DD --> ER
    DD --> GIT
    DD --> PIE
    DD --> MM
    DD --> QC
    DD --> RD
    DD --> SK
    DD --> TL
    DD --> TM
    DD --> XY
    DD --> ARCH
    DD --> BLK
    DD --> C4
    DD --> REQ
    DD --> PKT
    DIA --> RU
    DIA --> TH
    CONFIG --> DA
```

## Core Components

### Diagram Class (`packages.mermaid.src.Diagram.Diagram`)

The main Diagram class serves as the primary interface for diagram processing. It handles:

- **Text Parsing**: Converts diagram text into structured data
- **Type Detection**: Automatically identifies diagram types from text content
- **Dynamic Loading**: Loads diagram processors on-demand
- **Rendering Coordination**: Manages the rendering pipeline

Key methods:
- `fromText()`: Static factory method for creating diagram instances
- `render()`: Renders the diagram to a DOM element
- `getParser()`: Returns the parser for the diagram
- `getType()`: Returns the diagram type

### Type Definitions (`packages.mermaid.src.diagram-api.types.*`)

Comprehensive type system defining:

- **DiagramDefinition**: Core interface for diagram implementations
- **DiagramDB**: Database interface for diagram data storage
- **DiagramRenderer**: Rendering interface for diagram visualization
- **DiagramMetadata**: Metadata container for diagram properties
- **ExternalDiagramDefinition**: Interface for external diagram types
- **ParserDefinition**: Parser interface for text processing
- **InjectUtils**: Utility injection interface

### Frontmatter Handler (`packages.mermaid.src.diagram-api.frontmatter.*`)

Handles YAML frontmatter processing:

- **FrontMatterMetadata**: Metadata extraction and validation
- **FrontMatterResult**: Structured result container
- **extractFrontMatter()**: Main extraction function

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant Mermaid
    participant DiagramAPI
    participant DiagramType
    participant Renderer
    
    User->>Mermaid: Diagram Text
    Mermaid->>DiagramAPI: fromText(text)
    DiagramAPI->>DiagramAPI: detectType()
    DiagramAPI->>DiagramType: Load if needed
    DiagramType->>DiagramAPI: DiagramDefinition
    DiagramAPI->>DiagramType: parse(text)
    DiagramType->>DiagramType: Process to DB
    DiagramAPI->>Renderer: render(id, version)
    Renderer->>User: SVG/Canvas Output
```

## Integration Points

### With Core Mermaid Engine
- Receives diagram text and configuration
- Returns processed diagram objects
- Handles error propagation and validation

### With Configuration System
- Retrieves diagram-specific configurations
- Applies theme and styling options
- Manages display modes and accessibility settings

### With Rendering System
- Coordinates with rendering utilities
- Applies theme configurations
- Manages layout and positioning

### With Individual Diagram Types
- Provides standardized interfaces
- Handles lifecycle management
- Enables dynamic loading and registration

## Sub-modules

### [Types System](diagram-api-types.md)
Comprehensive type definitions and interfaces for the diagram API ecosystem, including core interfaces like `DiagramDefinition`, `DiagramDB`, `DiagramRenderer`, and related type definitions that form the foundation of the diagram processing system.

### [Frontmatter Processing](diagram-api-frontmatter.md)
YAML frontmatter extraction and processing for diagram metadata, providing functionality to parse and extract configuration, titles, and display modes from diagram text with YAML frontmatter blocks.

## Key Features

1. **Dynamic Diagram Loading**: Supports on-demand loading of diagram processors
2. **Type Safety**: Comprehensive TypeScript definitions for all interfaces
3. **Extensibility**: Plugin architecture for custom diagram types
4. **Error Handling**: Robust error detection and reporting
5. **Accessibility**: Built-in support for accessibility features
6. **Performance**: Efficient parsing and rendering pipeline

## Usage Patterns

### Basic Diagram Processing
```typescript
const diagram = await Diagram.fromText(diagramText);
await diagram.render('diagram-id', '1.0.0');
```

### Custom Diagram Registration
```typescript
registerDiagram('custom', {
  db: customDB,
  renderer: customRenderer,
  parser: customParser
});
```

### Metadata Handling
```typescript
const diagram = await Diagram.fromText(text, {
  title: 'My Diagram',
  config: customConfig
});
```

## Related Documentation

- [Core Mermaid Module](core-mermaid.md) - Main Mermaid engine integration
- [Configuration System](config.md) - Configuration and settings management
- [Rendering Utilities](rendering-util.md) - Rendering and layout utilities
- [Themes System](themes.md) - Theme and styling system