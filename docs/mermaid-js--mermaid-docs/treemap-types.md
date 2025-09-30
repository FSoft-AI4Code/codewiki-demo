# Treemap Types Module Documentation

## Introduction

The `treemap-types` module provides the foundational type definitions for creating treemap diagrams in Mermaid. Treemap diagrams are hierarchical data visualization tools that display nested rectangles to represent data proportions and relationships. This module defines the core data structures, interfaces, and configuration types that enable the creation, styling, and rendering of treemap diagrams.

## Module Architecture

### Core Type Hierarchy

```mermaid
classDiagram
    class TreemapNode {
        +string name
        +TreemapNode[] children
        +number value
        +TreemapNode parent
        +string classSelector
        +string[] cssCompiledStyles
    }
    
    class TreemapItem {
        +string $type
        +string name
        +number value
        +string classSelector
    }
    
    class TreemapRow {
        +string $type
        +string indent
        +TreemapItem item
        +string className
        +string styleText
    }
    
    class TreemapAst {
        +TreemapRow[] TreemapRows
        +string title
        +string description
        +string accDescription
        +string accTitle
        +string diagramTitle
    }
    
    class TreemapData {
        +TreemapNode[] nodes
        +Map~TreemapNode,number~ levels
        +TreemapNode root
        +TreemapNode[] outerNodes
        +Map~string,DiagramStyleClassDef~ classes
    }
    
    class TreemapDB {
        <<interface>>
        +getNodes() TreemapNode[]
        +addNode(TreemapNode, number) void
        +getRoot() TreemapNode
        +getClasses() Map~string,DiagramStyleClassDef~
        +addClass(string, string) void
        +getStylesForClass(string) string[]
    }
    
    class TreemapStyleOptions {
        +string sectionStrokeColor
        +string sectionStrokeWidth
        +string sectionFillColor
        +string leafStrokeColor
        +string leafStrokeWidth
        +string leafFillColor
        +string labelColor
        +string labelFontSize
        +string valueFontSize
        +string valueColor
        +string titleColor
        +string titleFontSize
    }
    
    class TreemapDiagramConfig {
        +number padding
        +number diagramPadding
        +boolean showValues
        +number nodeWidth
        +number nodeHeight
        +number borderWidth
        +number valueFontSize
        +number labelFontSize
        +string valueFormat
    }
    
    TreemapItem --> TreemapRow : contained in
    TreemapRow --> TreemapAst : part of
    TreemapNode --> TreemapData : used in
    TreemapData --> TreemapDB : managed by
    TreemapStyleOptions --> TreemapDiagramConfig : styling options
    TreemapDiagramConfig --> TreemapDB : configuration
```

### Module Dependencies

```mermaid
graph TD
    treemap-types["treemap-types"]
    diagram-api["diagram-api"]
    config["config"]
    
    treemap-types --> diagram-api
    treemap-types --> config
    
    diagram-api -.-> |"imports"| diagram-api/types["DiagramDBBase<br/>DiagramStyleClassDef"]
    config -.-> |"imports"| config/type["BaseDiagramConfig"]
```

## Core Components

### TreemapNode
The fundamental building block representing a single node in the treemap hierarchy.

**Properties:**
- `name`: The display name of the node
- `children`: Optional array of child nodes for hierarchical structure
- `value`: Optional numerical value for size calculation
- `parent`: Reference to parent node for tree navigation
- `classSelector`: CSS class selector for styling
- `cssCompiledStyles`: Array of compiled CSS styles

### TreemapDB
Database interface for managing treemap data and operations.

**Methods:**
- `getNodes()`: Retrieves all nodes in the treemap
- `addNode(node, level)`: Adds a node at specified hierarchy level
- `getRoot()`: Returns the root node of the tree
- `getClasses()`: Retrieves style class definitions
- `addClass(className, style)`: Adds a new style class
- `getStylesForClass(classSelector)`: Gets styles for a specific class

### TreemapData
Container for processed treemap data ready for rendering.

**Properties:**
- `nodes`: Array of all nodes
- `levels`: Map tracking node hierarchy levels
- `root`: Root node reference
- `outerNodes`: Array of outer/leaf nodes
- `classes`: Map of style class definitions

### TreemapStyleOptions
Comprehensive styling options for treemap visualization.

**Style Categories:**
- **Section Styles**: `sectionStrokeColor`, `sectionStrokeWidth`, `sectionFillColor`
- **Leaf Styles**: `leafStrokeColor`, `leafStrokeWidth`, `leafFillColor`
- **Text Styles**: `labelColor`, `labelFontSize`, `valueFontSize`, `valueColor`
- **Title Styles**: `titleColor`, `titleFontSize`

### TreemapDiagramConfig
Configuration interface extending base diagram configuration.

**Layout Options:**
- `padding`: Internal padding between nodes
- `diagramPadding`: External padding for entire diagram
- `nodeWidth/Height`: Fixed dimensions for nodes
- `borderWidth`: Border thickness

**Display Options:**
- `showValues`: Toggle value display
- `valueFormat`: Format string for value display
- `valueFontSize/labelFontSize`: Text sizing

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant Parser
    participant TreemapAst
    participant TreemapDB
    participant TreemapData
    participant Renderer
    
    Parser->>TreemapAst: Parse input text
    TreemapAst->>TreemapDB: Create database instance
    TreemapDB->>TreemapDB: Process TreemapRows
    TreemapDB->>TreemapDB: Build node hierarchy
    TreemapDB->>TreemapData: Generate render data
    TreemapData->>Renderer: Provide structured data
    Renderer->>Renderer: Apply styles & layout
    Renderer->>Renderer: Generate SVG output
```

## AST Processing Flow

```mermaid
flowchart TD
    A[TreemapAst Input] --> B{Parse TreemapRows}
    B --> C[Extract TreemapItems]
    C --> D[Build Node Hierarchy]
    D --> E[Apply Class Styles]
    E --> F[Calculate Values]
    F --> G[Generate TreemapData]
    G --> H[Ready for Rendering]
    
    I[TreemapStyleOptions] --> E
    J[TreemapDiagramConfig] --> F
```

## Integration with Mermaid Ecosystem

### Relationship to Core Modules

```mermaid
graph LR
    treemap-types --> |extends| diagram-api/types
    treemap-types --> |extends| config/type
    
    treemap-database --> |implements| treemap-types
    treemap-renderer --> |consumes| treemap-types
    
    diagram-api/types -.-> |DiagramDBBase| treemap-types
    config/type -.-> |BaseDiagramConfig| treemap-types
```

### Configuration Inheritance

The `TreemapDiagramConfig` extends `BaseDiagramConfig` from the config module, inheriting common diagram properties while adding treemap-specific options:

```typescript
interface TreemapDiagramConfig extends BaseDiagramConfig {
  // Treemap-specific properties
  padding?: number;
  showValues?: boolean;
  // ... additional properties
}
```

## Usage Patterns

### Node Hierarchy Construction

```mermaid
graph TD
    Root[Root Node] --> Child1[Child Node 1]
    Root --> Child2[Child Node 2]
    Child1 --> GrandChild1[Grandchild 1]
    Child1 --> GrandChild2[Grandchild 2]
    Child2 --> GrandChild3[Grandchild 3]
    
    style Root fill:#f9f,stroke:#333
    style Child1 fill:#bbf,stroke:#333
    style Child2 fill:#bbf,stroke:#333
    style GrandChild1 fill:#bfb,stroke:#333
    style GrandChild2 fill:#bfb,stroke:#333
    style GrandChild3 fill:#bfb,stroke:#333
```

### Style Application

The module supports CSS-like styling through class selectors:

1. Define style classes in `TreemapStyleOptions`
2. Apply classes to nodes via `classSelector` property
3. Styles are compiled and applied during rendering
4. Hierarchical style inheritance is supported

## Key Features

### Hierarchical Data Support
- Unlimited nesting depth
- Parent-child relationships
- Value aggregation for parent nodes
- Level-based styling

### Flexible Styling
- Section and leaf-specific styles
- CSS class-based styling
- Dynamic style compilation
- Theme integration support

### Configuration Options
- Layout customization
- Value display control
- Font and color theming
- Border and padding settings

## Related Documentation

- [diagram-api](diagram-api.md) - Core diagram API and base types
- [config](config.md) - Configuration system and base diagram config
- [treemap-database](treemap-database.md) - Database implementation for treemap data
- [rendering-util](rendering-util.md) - Rendering utilities and common types

## Summary

The `treemap-types` module provides a comprehensive type system for treemap diagram creation in Mermaid. It defines the essential data structures for representing hierarchical data, managing styles, and configuring diagram behavior. The module's design emphasizes flexibility, extensibility, and integration with Mermaid's broader architecture while maintaining clear separation of concerns between data representation, styling, and configuration.