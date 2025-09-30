# MindmapDB Module Documentation

## Introduction

The MindmapDB module is a core component of the Mermaid.js library that provides data management and storage capabilities for mindmap diagrams. It serves as the central database for mindmap nodes, handling node creation, hierarchical relationships, and node decorations. This module implements the `DiagramDB` interface and works in conjunction with the mindmap parser and renderer to create interactive hierarchical mindmap visualizations.

## Architecture Overview

The MindmapDB module follows a hierarchical data structure pattern where nodes are organized in a tree-like structure with parent-child relationships. Each node can have multiple children but only one parent, forming a directed acyclic graph that represents the mindmap structure.

```mermaid
graph TB
    subgraph "MindmapDB Architecture"
        A[MindmapDB Class] --> B[Node Management]
        A --> C[Hierarchical Structure]
        A --> D[Node Types]
        A --> E[Element Storage]
        A --> F[Configuration Integration]
        
        B --> B1[addNode Method]
        B --> B2[getParent Method]
        B --> B3[clear Method]
        
        C --> C1[Tree Traversal]
        C --> C2[Level-based Hierarchy]
        C --> C3[Root Node Validation]
        
        D --> D1[Shape Type Detection]
        D --> D2[Node Type Constants]
        D --> D3[Type-to-String Conversion]
        
        E --> E1[D3Element Storage]
        E --> E2[Element Retrieval]
        
        F --> F1[Configuration Access]
        F --> F2[Padding Calculation]
        F --> F3[Text Sanitization]
    end
```

## Core Components

### MindmapDB Class

The `MindmapDB` class is the primary component that implements the database functionality for mindmap diagrams. It manages the complete lifecycle of mindmap nodes and provides methods for node manipulation and retrieval.

```mermaid
classDiagram
    class MindmapDB {
        -nodes: MindmapNode[]
        -count: number
        -elements: Record<number, D3Element>
        -nodeType: typeof nodeType
        +constructor()
        +clear(): void
        +getParent(level: number): MindmapNode|null
        +getMindmap(): MindmapNode|null
        +addNode(level: number, id: string, descr: string, type: number): void
        +getType(startStr: string, endStr: string): number
        +setElementForId(id: number, element: D3Element): void
        +getElementById(id: number): D3Element
        +decorateNode(decoration?: object): void
        +type2Str(type: number): string
        +getLogger(): Logger
    }
```

## Data Flow

The following diagram illustrates the data flow within the MindmapDB module:

```mermaid
sequenceDiagram
    participant Parser
    participant MindmapDB
    participant Config
    participant Logger
    
    Parser->>MindmapDB: addNode(level, id, descr, type)
    MindmapDB->>Config: getConfig()
    MindmapDB->>MindmapDB: getParent(level)
    MindmapDB->>MindmapDB: sanitizeText()
    MindmapDB->>Logger: log.info()
    MindmapDB->>MindmapDB: Create MindmapNode
    MindmapDB->>MindmapDB: Add to parent.children
    MindmapDB-->>Parser: Node added
    
    Parser->>MindmapDB: getType(startStr, endStr)
    MindmapDB->>Logger: log.debug()
    MindmapDB-->>Parser: Node type
    
    Renderer->>MindmapDB: getMindmap()
    MindmapDB-->>Renderer: Root node
    
    Renderer->>MindmapDB: setElementForId(id, element)
    MindmapDB-->>Renderer: Element stored
```

## Node Types and Shapes

The MindmapDB module supports various node shapes that are determined by parsing the syntax tokens:

```mermaid
graph LR
    A[Syntax Token] --> B{Shape Detection}
    B -->|"["| C[Rectangle]
    B -->|"()"| D[Rounded Rectangle]
    B -->|"(("| E[Circle]
    B -->|")"| F[Cloud]
    B -->|"))"| G[Bang]
    B -->|"{{"| H[Hexagon]
    B -->|Default| I[No Border]
    
    C --> J[Padding * 2]
    D --> J
    H --> J
    E --> K[Default Padding]
    F --> K
    G --> K
    I --> K
```

## Hierarchical Structure Management

The module implements a level-based hierarchical system where each node's position in the tree is determined by its level:

```mermaid
graph TD
    A[Root Node - Level 0] --> B[Child 1 - Level 1]
    A --> C[Child 2 - Level 1]
    B --> D[Grandchild 1.1 - Level 2]
    B --> E[Grandchild 1.2 - Level 2]
    C --> F[Grandchild 2.1 - Level 2]
    
    G[getParent Logic] --> H{Find node with level < current}
    H -->|Found| I[Return parent]
    H -->|Not found| J[Return null]
    
    K[Root Validation] --> L{nodes.length === 0}
    L -->|True| M[Allow root]
    L -->|False| N[Throw error]
```

## Integration with Other Modules

The MindmapDB module integrates with several other modules in the Mermaid ecosystem:

```mermaid
graph TB
    subgraph "External Dependencies"
        A[MindmapDB]
        B[Diagram API]
        C[Configuration System]
        D[Common Utilities]
        E[Logger]
        F[Mindmap Types]
        G[Default Config]
    end
    
    A --> B
    A --> D
    A --> E
    A --> F
    A --> G
    
    B --> H[diagram-api.md]
    C --> I[config.md]
    D --> J[utils.md]
    E --> K[core-mermaid.md]
    F --> L[mindmapTypes.md]
```

## Configuration Integration

The module integrates with Mermaid's configuration system to apply styling and layout options:

```mermaid
graph LR
    A[addNode Method] --> B{Get Config}
    B --> C[mindmap.padding]
    B --> D[mindmap.maxNodeWidth]
    B --> E[Global Config]
    
    C --> F{Adjust by Type}
    F -->|RECT, ROUNDED_RECT, HEXAGON| G[padding * 2]
    F -->|Other types| H[Default padding]
    
    D --> I[Node width]
    E --> J[sanitizeText]
```

## Error Handling

The module implements specific error handling for mindmap structure validation:

```mermaid
graph TD
    A[addNode Request] --> B{Root exists?}
    B -->|Yes| C{Parent found?}
    B -->|No| D[Create root]
    C -->|Yes| E[Add as child]
    C -->|No| F[Throw error]
    
    F --> G["Error: There can be only one root. No parent could be found"]
    G --> H[Include node description in error]
```

## Node Decoration System

The module supports node decoration through CSS classes and icons:

```mermaid
sequenceDiagram
    participant Parser
    participant MindmapDB
    participant Config
    
    Parser->>MindmapDB: decorateNode({class: "highlight", icon: "fa-home"})
    MindmapDB->>Config: getConfig()
    MindmapDB->>MindmapDB: Get last node
    MindmapDB->>MindmapDB: sanitizeText(class)
    MindmapDB->>MindmapDB: sanitizeText(icon)
    MindmapDB->>MindmapDB: Apply to node
    MindmapDB-->>Parser: Decoration applied
```

## Element Storage and Retrieval

The module provides a mechanism for storing and retrieving D3 elements associated with nodes:

```mermaid
graph LR
    A[setElementForId] --> B[Store in elements map]
    C[getElementById] --> D{Element exists?}
    D -->|Yes| E[Return element]
    D -->|No| F[Return undefined]
    
    B --> G[elements stored]
    E --> H[D3Element returned]
```

## Type Conversion and String Representation

The module provides methods for converting between numeric types and string representations:

```mermaid
graph TD
    A[getType Method] --> B{Parse tokens}
    B --> C[Return numeric type]
    
    D[type2Str Method] --> E{Switch on type}
    E --> F[Return string representation]
    
    G[Numeric Types] --> H[0: no-border]
    G --> I[1: rounded-rect]
    G --> J[2: rect]
    G --> K[3: circle]
    G --> L[4: cloud]
    G --> M[5: bang]
    G --> N[6: hexagon]
```

## Performance Considerations

The MindmapDB module is designed with performance in mind:

1. **Efficient Parent Lookup**: The `getParent` method iterates backwards through the nodes array, ensuring the most recently added nodes are checked first.

2. **Memory Management**: The `clear` method resets all internal data structures, preventing memory leaks in long-running applications.

3. **Lazy Initialization**: Node decorations are only applied when explicitly requested, reducing unnecessary processing.

4. **Type Safety**: The use of TypeScript ensures type safety and reduces runtime errors.

## Usage Examples

The MindmapDB module is typically used in conjunction with the mindmap parser and renderer:

```typescript
// Example usage pattern (not actual implementation)
const mindmapDB = new MindmapDB();

// Add nodes
mindmapDB.addNode(0, "root", "Root Node", mindmapDB.nodeType.DEFAULT);
mindmapDB.addNode(1, "child1", "Child 1", mindmapDB.nodeType.RECT);
mindmapDB.addNode(1, "child2", "Child 2", mindmapDB.nodeType.CIRCLE);

// Get the mindmap structure
const root = mindmapDB.getMindmap();

// Decorate nodes
mindmapDB.decorateNode({ class: "highlight", icon: "fa-star" });
```

## Related Documentation

- [mindmapTypes.md](mindmapTypes.md) - Mindmap node type definitions
- [mindmapRenderer.md](mindmapRenderer.md) - Mindmap rendering components
- [diagram-api.md](diagram-api.md) - General diagram API documentation
- [config.md](config.md) - Configuration system documentation
- [core-mermaid.md](core-mermaid.md) - Core Mermaid functionality

## Summary

The MindmapDB module serves as the central data management system for mindmap diagrams in Mermaid.js. It provides a robust, hierarchical data structure that supports various node shapes, decorations, and configuration options. The module's design ensures efficient node management while maintaining integration with the broader Mermaid ecosystem through configuration, logging, and utility systems.