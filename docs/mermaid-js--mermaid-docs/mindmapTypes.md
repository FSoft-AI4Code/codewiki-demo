# mindmapTypes Module Documentation

## Overview

The `mindmapTypes` module defines the core type system for mindmap diagrams in Mermaid. It provides the fundamental data structures that represent mindmap nodes and their hierarchical relationships, forming the foundation for mindmap diagram parsing, rendering, and interaction.

## Purpose and Core Functionality

This module serves as the type definition layer for the mindmap diagram type, offering:

- **Node Representation**: Defines the structure of individual mindmap nodes
- **Hierarchical Relationships**: Establishes parent-child relationships between nodes
- **Layout Properties**: Specifies positioning and sizing information for rendering
- **Visual Attributes**: Includes styling and icon support for enhanced visualization
- **Type Safety**: Provides TypeScript interfaces for compile-time type checking

## Core Components

### MindmapNode Interface

The primary interface that defines the structure of a mindmap node:

```typescript
interface MindmapNode {
  id: number;                    // Unique numeric identifier
  nodeId: string;               // String identifier for the node
  level: number;                // Depth level in the hierarchy (0 = root)
  descr: string;                // Node description/text content
  type: number;                 // Node type identifier
  children: MindmapNode[];      // Array of child nodes
  width: number;                // Node width for layout
  padding: number;              // Internal padding
  section?: number;             // Optional section identifier
  height?: number;              // Optional node height
  class?: string;               // Optional CSS class for styling
  icon?: string;                // Optional icon identifier
  x?: number;                   // Optional x-coordinate for positioning
  y?: number;                   // Optional y-coordinate for positioning
}
```

### FilledMindMapNode Type

A utility type that makes all properties of MindmapNode required:

```typescript
type FilledMindMapNode = RequiredDeep<MindmapNode>;
```

## Architecture and Component Relationships

### Module Dependencies

```mermaid
graph TD
    mindmapTypes[mindmapTypes<br/><small>MindmapNode, FilledMindMapNode</small>]
    
    mindmapDb[mindmapDb<br/><small>MindmapDB</small>]
    mindmapRenderer[mindmapRenderer<br/><small>EdgeSingular</small>]
    
    mindmapTypes --> mindmapDb
    mindmapTypes --> mindmapRenderer
    
    style mindmapTypes fill:#e1f5fe
    style mindmapDb fill:#fff3e0
    style mindmapRenderer fill:#fff3e0
```

### Data Flow Architecture

```mermaid
graph LR
    A[Mindmap Parser] -->|creates| B["MindmapNode[]"]
    B -->|stored in| C["MindmapDB"]
    C -->|processed by| D["Layout Engine"]
    D -->|adds coords| E["MindmapNode[] with x,y"]
    E -->|rendered by| F["Mindmap Renderer"]
    
    style B fill:#e1f5fe
    style E fill:#e1f5fe
```

## Component Interactions

### Node Hierarchy Structure

```mermaid
graph TD
    Root[Root Node<br/>level: 0] --> Child1[Child Node 1<br/>level: 1]
    Root --> Child2[Child Node 2<br/>level: 1]
    Root --> Child3[Child Node 3<br/>level: 1]
    
    Child1 --> GrandChild1[GrandChild 1<br/>level: 2]
    Child1 --> GrandChild2[GrandChild 2<br/>level: 2]
    
    Child2 --> GrandChild3[GrandChild 3<br/>level: 2]
    
    style Root fill:#e3f2fd
    style Child1 fill:#e8f5e9
    style Child2 fill:#e8f5e9
    style Child3 fill:#e8f5e9
    style GrandChild1 fill:#fff3e0
    style GrandChild2 fill:#fff3e0
    style GrandChild3 fill:#fff3e0
```

### Rendering Process Flow

```mermaid
sequenceDiagram
    participant Parser
    participant MindmapDB
    participant LayoutEngine
    participant Renderer
    
    Parser->>MindmapDB: Create MindmapNode objects
    MindmapDB->>MindmapDB: Build hierarchical structure
    MindmapDB->>LayoutEngine: Provide node tree
    LayoutEngine->>LayoutEngine: Calculate positions (x,y)
    LayoutEngine->>Renderer: Nodes with layout data
    Renderer->>Renderer: Draw nodes and edges
    Renderer->>UI: Rendered mindmap
```

## Integration with Mermaid System

### Position in Module Hierarchy

```mermaid
graph TD
    mermaid[mermaid core]
    
    mermaid --> diagramAPI[diagram-api]
    diagramAPI --> mindmap[mindmap diagram]
    
    mindmap --> mindmapTypes[mindmapTypes]
    mindmap --> mindmapDb[mindmapDb]
    mindmap --> mindmapRenderer[mindmapRenderer]
    
    config[config] --> mindmap
    themes[themes] --> mindmap
    
    style mindmapTypes fill:#e1f5fe
    style mindmap fill:#fff3e0
```

### Configuration Integration

The `MindmapNode` interface works with the [config](config.md) module through:

- `MindmapDiagramConfig` for diagram-level settings
- `class` property for applying custom styles
- `icon` property for visual enhancements

### Rendering Pipeline Integration

```mermaid
graph LR
    A[Parse Mindmap Text] --> B[Create MindmapNode Tree]
    B --> C[Apply Configuration]
    C --> D[Calculate Layout]
    D --> E[Apply Theme]
    E --> F[Render SVG]
    
    B -.->|uses| mindmapTypes
    C -.->|uses| config
    E -.->|uses| themes
    
    style B fill:#e1f5fe
```

## Usage Patterns

### Node Creation

```typescript
// Typical node structure
const rootNode: MindmapNode = {
  id: 0,
  nodeId: 'root',
  level: 0,
  descr: 'Main Topic',
  type: 0,
  children: [],
  width: 100,
  padding: 10
};
```

### Hierarchical Building

```typescript
// Building parent-child relationships
parentNode.children.push(childNode);
childNode.level = parentNode.level + 1;
```

### Layout Processing

```typescript
// Adding positioning data
node.x = calculatedX;
node.y = calculatedY;
node.width = calculatedWidth;
node.height = calculatedHeight;
```

## Related Modules

- **[mindmapDb](mindmapDb.md)**: Database layer that stores and manages MindmapNode instances
- **[mindmapRenderer](mindmapRenderer.md)**: Rendering engine that converts MindmapNode data to visual representation
- **[config](config.md)**: Configuration system including MindmapDiagramConfig
- **[rendering-util](rendering-util.md)**: Utility functions for layout calculations and rendering

## Type Safety and Extensibility

The module leverages TypeScript's type system to ensure:

- **Compile-time validation**: All required properties must be present
- **IDE support**: Autocomplete and type checking during development
- **Refactoring safety**: Type-safe changes across the codebase
- **Documentation**: Self-documenting interface definitions

The `RequiredDeep` utility from `type-fest` ensures that the `FilledMindMapNode` type has all properties marked as required, providing additional type safety for scenarios where complete node data is required.