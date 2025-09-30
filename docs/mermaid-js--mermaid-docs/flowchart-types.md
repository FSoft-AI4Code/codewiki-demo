# Flowchart Types Module Documentation

## Introduction

The `flowchart-types` module defines the core type definitions for flowchart diagrams in the Mermaid.js library. This module provides the fundamental data structures and interfaces that represent flowchart elements such as vertices (nodes), edges (connections), subgraphs, and styling classes. These types form the foundation for parsing, rendering, and interacting with flowchart diagrams throughout the Mermaid ecosystem.

## Architecture Overview

The flowchart-types module serves as the type foundation for the flowchart diagram implementation, providing TypeScript interfaces that define the structure of flowchart components and their relationships.

```mermaid
flowchart TB
    subgraph "flowchart-types Module"
        FlowVertex["FlowVertex"]
        FlowEdge["FlowEdge"]
        FlowLink["FlowLink"]
        FlowSubGraph["FlowSubGraph"]
        FlowText["FlowText"]
        FlowClass["FlowClass"]
        FlowVertexTypeParam["FlowVertexTypeParam"]
    end

    subgraph "Dependencies"
        ShapeID["ShapeID<br/>from rendering-util-shapes"]
    end

    subgraph "Consumer Modules"
        flowchartMod["flowchart Module"]
        flowchartDb["flowchart.flowDb"]
        renderingUtil["rendering-util"]
        configMod["config"]
    end

    FlowVertex -->|"uses"| ShapeID
    FlowVertex -->|"defines type"| FlowVertexTypeParam
    
    flowchartMod -->|"consumes"| FlowVertex
    flowchartMod -->|"consumes"| FlowEdge
    flowchartMod -->|"consumes"| FlowLink
    flowchartMod -->|"consumes"| FlowSubGraph
    flowchartMod -->|"consumes"| FlowText
    flowchartMod -->|"consumes"| FlowClass
    
    flowchartDb -->|"uses"| FlowVertex
    flowchartDb -->|"uses"| FlowEdge
    
    renderingUtil -->|"references"| FlowVertex
    configMod -->|"references"| FlowVertex
```

## Core Components

### FlowVertex

The `FlowVertex` interface represents a node or vertex in a flowchart diagram. It defines all the properties that a flowchart node can have, including its visual appearance, behavior, and metadata.

```mermaid
classDiagram
    class FlowVertex {
        +string id
        +string domId
        +string[] classes
        +string[] styles
        +string labelType
        +string? text
        +ShapeID? type
        +string? dir
        +boolean? haveCallback
        +string? link
        +string? linkTarget
        +any? props
        +string? icon
        +string? form
        +string? pos
        +string? img
        +number? assetWidth
        +number? assetHeight
        +number? defaultWidth
        +number? imageAspectRatio
        +string? constraint
    }
```

**Key Properties:**
- `id`: Unique identifier for the vertex
- `domId`: DOM element identifier for rendering
- `classes`: CSS classes applied to the vertex
- `styles`: Inline styles for the vertex
- `type`: Shape type (references [rendering-util-shapes](rendering-util-shapes.md))
- `text`: Display text content
- `link`: Hyperlink URL
- `icon`: Icon identifier
- `img`: Image URL for custom node images

### FlowEdge

The `FlowEdge` interface defines the structure of connections between vertices in a flowchart.

```mermaid
classDiagram
    class FlowEdge {
        +boolean isUserDefinedId
        +string start
        +string end
        +string text
        +string labelType
        +string[] classes
        +string? id
        +string? interpolate
        +string? type
        +string? stroke
        +string[]? style
        +number? length
        +string? animation
        +boolean? animate
    }
```

**Key Properties:**
- `start`: ID of the source vertex
- `end`: ID of the target vertex
- `text`: Label text for the edge
- `stroke`: Line style ('normal', 'thick', 'invisible', 'dotted')
- `animation`: Animation speed ('fast', 'slow')
- `animate`: Whether to enable animation

### FlowSubGraph

Represents a container or grouping of vertices within a flowchart.

```mermaid
classDiagram
    class FlowSubGraph {
        +string id
        +string title
        +string[] nodes
        +string[] classes
        +string labelType
        +string? dir
    }
```

**Key Properties:**
- `id`: Unique identifier for the subgraph
- `title`: Display title of the subgraph
- `nodes`: Array of vertex IDs contained in this subgraph
- `classes`: CSS classes for styling

### FlowText

Simple text container used for labels and text content within flowcharts.

```mermaid
classDiagram
    class FlowText {
        +string text
        +string type
    }
```

### FlowClass

Defines CSS class styling information for flowchart elements.

```mermaid
classDiagram
    class FlowClass {
        +string id
        +string[] styles
        +string[] textStyles
    }
```

### FlowLink

Represents a link or connection with basic properties.

```mermaid
classDiagram
    class FlowLink {
        +string stroke
        +string type
        +number? length
        +string? text
    }
```

## Data Flow

The flowchart types participate in the following data flow within the Mermaid system:

```mermaid
flowchart LR
    subgraph "Data Flow Process"
        Parser["Parser"]
        flowchartDb["flowchartDb"]
        Types["Types"]
        Renderer["Renderer"]
        Rendering["Rendering Engine"]
    end
    
    Parser -->|"Create FlowVertex objects"| Types
    Parser -->|"Create FlowEdge objects"| Types
    Parser -->|"Create FlowSubGraph objects"| Types
    
    Parser -->|"Store typed objects"| flowchartDb
    
    Renderer -->|"Retrieve typed objects"| flowchartDb
    Renderer -->|"Reference type definitions"| Types
    Renderer -->|"Generate SVG/Canvas output"| Rendering
```

## Component Relationships

The flowchart-types module integrates with the broader Mermaid ecosystem through well-defined relationships:

```mermaid
flowchart LR
    subgraph "Type Definition Layer"
        FT["flowchart-types"]
    end
    
    subgraph "Database Layer"
        FD["flowchart.flowDb"]
    end
    
    subgraph "Rendering Layer"
        RU["rendering-util"]
        RS["rendering-util-shapes"]
    end
    
    subgraph "Configuration Layer"
        FC["FlowchartDiagramConfig"]
    end
    
    subgraph "Parser Layer"
        FP["flowchart parser"]
    end
    
    FT -->|"defines structure"| FD
    FT -->|"references shapes"| RS
    FT -->|"used by"| RU
    FT -->|"configures"| FC
    FT -->|"consumed by"| FP
    
    FD -->|"implements"| FT
    RU -->|"renders"| FT
    FC -->|"styles"| FT
```

## Integration with Other Modules

### Flowchart Module Integration

The flowchart-types module is consumed by the main [flowchart](flowchart.md) module, which provides the implementation for parsing and rendering flowchart diagrams.

### Configuration Integration

Flowchart types work with the [config](config.md) module's `FlowchartDiagramConfig` to apply styling and behavior configurations to flowchart elements.

### Rendering Integration

The types integrate with [rendering-util](rendering-util.md) and [rendering-util-shapes](rendering-util-shapes.md) modules to enable proper visual representation of flowchart elements.

## Usage Examples

### Vertex Creation

```typescript
const vertex: FlowVertex = {
  id: 'node1',
  domId: 'flowchart-node1',
  classes: ['default', 'important'],
  styles: ['fill:#f9f', 'stroke:#333'],
  labelType: 'text',
  text: 'Start Process',
  type: 'round',
  link: '/process/start',
  constraint: 'on'
};
```

### Edge Creation

```typescript
const edge: FlowEdge = {
  isUserDefinedId: false,
  start: 'node1',
  end: 'node2',
  text: 'Process Data',
  labelType: 'text',
  classes: ['flow-link'],
  stroke: 'normal',
  animate: true,
  animation: 'slow'
};
```

### SubGraph Creation

```typescript
const subGraph: FlowSubGraph = {
  id: 'cluster_1',
  title: 'Processing Stage',
  nodes: ['node1', 'node2', 'node3'],
  classes: ['subgraph'],
  labelType: 'text'
};
```

## Type Safety and Extensibility

The flowchart-types module provides strong TypeScript typing throughout the flowchart implementation, ensuring:

- **Type Safety**: All flowchart elements have well-defined structures
- **IntelliSense**: IDE support for property names and types
- **Compile-time Validation**: Catch type errors during development
- **Extensibility**: Easy to extend with new properties while maintaining backward compatibility

## Summary

The flowchart-types module is a foundational component that defines the data structures for flowchart diagrams in Mermaid.js. It provides the type definitions that enable consistent parsing, storage, and rendering of flowchart elements across the entire Mermaid ecosystem. By maintaining clear separation between type definitions and implementation, this module ensures type safety and promotes code maintainability throughout the flowchart diagram implementation.