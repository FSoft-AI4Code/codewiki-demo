# ER Database Module Documentation

## Introduction

The ER Database module is a core component of the Mermaid diagram library that provides data management and storage capabilities for Entity-Relationship (ER) diagrams. This module implements the `ErDB` class which serves as the central data repository for ER diagram entities, relationships, and configuration settings.

## Module Overview

The ER Database module is responsible for:
- Storing and managing ER diagram entities with their attributes
- Managing relationships between entities with cardinality and identification specifications
- Handling CSS styling and theming for ER diagram elements
- Providing data access interfaces for rendering engines
- Supporting diagram configuration and accessibility features

## Architecture

### Core Architecture

```mermaid
graph TB
    subgraph "ER Database Module"
        ErDB[ErDB Class]
        Entities[Entity Map]
        Relationships[Relationship Array]
        Classes[CSS Classes Map]
        
        ErDB --> Entities
        ErDB --> Relationships
        ErDB --> Classes
    end
    
    subgraph "External Dependencies"
        DiagramAPI[Diagram API]
        Logger[Logger]
        CommonDB[Common DB]
        Utils[Utils]
        Config[Configuration]
    end
    
    ErDB --> DiagramAPI
    ErDB --> Logger
    ErDB --> CommonDB
    ErDB --> Utils
    ErDB --> Config
```

### Component Relationships

```mermaid
graph LR
    subgraph "ER Database Components"
        ErDB[ErDB]
        EntityNode[EntityNode]
        Relationship[Relationship]
        EntityClass[EntityClass]
        Attribute[Attribute]
    end
    
    subgraph "Related Modules"
        ErTypes[er-types]
        CommonDB[common-db]
        DiagramAPI[diagram-api]
        Rendering[rendering-engine]
    end
    
    ErDB -->|uses| EntityNode
    ErDB -->|manages| Relationship
    ErDB -->|defines| EntityClass
    ErDB -->|contains| Attribute
    
    EntityNode -.->|defined in| ErTypes
    ErDB -.->|extends| CommonDB
    ErDB -.->|implements| DiagramAPI
    ErDB -->|provides data to| Rendering
```

## Core Components

### ErDB Class

The `ErDB` class is the main component that implements the `DiagramDB` interface. It provides comprehensive data management for ER diagrams with the following key features:

#### Data Storage
- **Entities**: Map of entity names to `EntityNode` objects
- **Relationships**: Array of relationship specifications
- **Classes**: Map of CSS class definitions for styling

#### Key Methods

**Entity Management:**
- `addEntity(name, alias)`: Creates or updates entities
- `addAttributes(entityName, attribs)`: Adds attributes to entities
- `getEntity(name)`: Retrieves specific entities
- `getEntities()`: Returns all entities

**Relationship Management:**
- `addRelationship(entA, rolA, entB, rSpec)`: Creates relationships between entities
- `getRelationships()`: Returns all relationships

**Styling and Configuration:**
- `addClass(ids, style)`: Defines CSS classes
- `setClass(ids, classNames)`: Applies classes to entities
- `addCssStyles(ids, styles)`: Adds inline styles
- `setDirection(dir)`: Sets diagram direction

**Data Export:**
- `getData()`: Converts internal data to rendering format
- `clear()`: Resets all data

## Data Flow

```mermaid
sequenceDiagram
    participant Parser
    participant ErDB
    participant Renderer
    participant Config
    
    Parser->>ErDB: addEntity(name, alias)
    ErDB->>ErDB: Create EntityNode
    Parser->>ErDB: addAttributes(entity, attributes)
    ErDB->>ErDB: Update entity.attributes
    Parser->>ErDB: addRelationship(entA, entB, spec)
    ErDB->>ErDB: Create Relationship
    
    Renderer->>ErDB: getData()
    ErDB->>Config: getConfig()
    ErDB->>ErDB: Convert to Node/Edge format
    ErDB->>Renderer: Return {nodes, edges, config}
```

## Entity-Relationship Model

### Entity Structure

```mermaid
classDiagram
    class EntityNode {
        +string id
        +string label
        +Attribute[] attributes
        +string alias
        +string shape
        +string look
        +string cssClasses
        +string[] cssStyles
        +string[] cssCompiledStyles
    }
    
    class Attribute {
        +string name
        +string type
        +string[] keys
        +string comment
    }
    
    class Relationship {
        +string entityA
        +string roleA
        +string entityB
        +RelSpec relSpec
    }
    
    class RelSpec {
        +Cardinality cardA
        +Cardinality cardB
        +Identification relType
    }
    
    EntityNode "1" --> "*" Attribute : contains
    Relationship "*" --> "1" RelSpec : specifies
```

### Cardinality and Identification

The module supports standard ER diagram notations:

**Cardinality Types:**
- `ZERO_OR_ONE`: 0..1
- `ZERO_OR_MORE`: 0..*
- `ONE_OR_MORE`: 1..*
- `ONLY_ONE`: 1
- `MD_PARENT`: Markdown parent relationship

**Identification Types:**
- `NON_IDENTIFYING`: Dashed line relationship
- `IDENTIFYING`: Solid line relationship

## Integration with Other Modules

### Diagram API Integration

The ErDB module integrates with the [diagram-api](diagram_plugin_api.md) module through the `DiagramDB` interface:

```mermaid
graph BT
    subgraph "Diagram API"
        DiagramDB[DiagramDB Interface]
        DiagramDefinition[DiagramDefinition]
    end
    
    subgraph "ER Database"
        ErDB[ErDB Class]
    end
    
    ErDB -.->|implements| DiagramDB
    DiagramDefinition -->|uses| ErDB
```

### Rendering Engine Integration

The module provides data to the [rendering-engine](rendering_engine.md) through the `getData()` method:

```mermaid
graph LR
    subgraph "ER Database"
        ErDB[ErDB]
        EntityData[Entity Data]
        RelationshipData[Relationship Data]
    end
    
    subgraph "Rendering Engine"
        RenderData[RenderData]
        LayoutData[LayoutData]
        Node[BaseNode]
        Edge[Edge]
    end
    
    ErDB --> EntityData
    EntityData --> Node
    RelationshipData --> Edge
    Node --> RenderData
    Edge --> RenderData
```

### Configuration Integration

The module accesses configuration through the [mermaid-core-api](mermaid_core_api.md):

```mermaid
graph TD
    ErDB[ErDB Module]
    Config[Configuration System]
    ErDiagramConfig[ErDiagramConfig]
    
    ErDB --> Config
    Config --> ErDiagramConfig
    ErDiagramConfig --> EntityStyling[Entity Styling]
    ErDiagramConfig --> RelationshipRendering[Relationship Rendering]
```

## Process Flow

### Entity Addition Process

```mermaid
flowchart TD
    Start([Start])
    AddEntity[addEntity called]
    CheckExists{Entity exists?}
    CreateEntity[Create new EntityNode]
    UpdateAlias[Update alias if provided]
    ReturnEntity[Return EntityNode]
    
    Start --> AddEntity
    AddEntity --> CheckExists
    CheckExists -->|No| CreateEntity
    CheckExists -->|Yes| UpdateAlias
    CreateEntity --> ReturnEntity
    UpdateAlias --> ReturnEntity
```

### Relationship Addition Process

```mermaid
flowchart TD
    Start([Start])
    AddRel[addRelationship called]
    GetEntities[Get entityA and entityB]
    CheckExists{Both entities exist?}
    CreateRel[Create Relationship object]
    AddToArray[Add to relationships array]
    Return[Return]
    
    Start --> AddRel
    AddRel --> GetEntities
    GetEntities --> CheckExists
    CheckExists -->|Yes| CreateRel
    CheckExists -->|No| Return
    CreateRel --> AddToArray
    AddToArray --> Return
```

### Data Export Process

```mermaid
flowchart TD
    Start([Start])
    GetData[getData called]
    InitArrays[Initialize nodes/edges arrays]
    ProcessEntities[Process each entity]
    CompileStyles[Compile CSS styles]
    ConvertToNodes[Convert to Node format]
    ProcessRelationships[Process relationships]
    ConvertToEdges[Convert to Edge format]
    ReturnData[Return Result]
    
    Start --> GetData
    GetData --> InitArrays
    InitArrays --> ProcessEntities
    ProcessEntities --> CompileStyles
    CompileStyles --> ConvertToNodes
    ConvertToNodes --> ProcessRelationships
    ProcessRelationships --> ConvertToEdges
    ConvertToEdges --> ReturnData
```

## Key Features

### 1. Entity Management
- Dynamic entity creation with unique ID generation
- Support for entity aliases
- Attribute management with type and key specifications
- CSS class and style application

### 2. Relationship Management
- Support for all standard ER cardinality types
- Identifying and non-identifying relationship types
- Role-based relationship labeling
- Automatic edge generation for rendering

### 3. Styling System
- CSS class definition and application
- Inline style support
- Compiled style caching
- Integration with Mermaid theme system

### 4. Accessibility Support
- Title and description management
- Screen reader compatibility
- Semantic HTML generation

## Usage Patterns

### Basic Entity Creation
```typescript
const erDb = new ErDB();
erDb.addEntity('Customer', 'cust');
erDb.addAttributes('Customer', [
  { name: 'id', type: 'int', keys: ['PK'] },
  { name: 'name', type: 'varchar(255)' }
]);
```

### Relationship Definition
```typescript
erDb.addRelationship('Customer', 'places', 'Order', {
  cardA: 'ONLY_ONE',
  cardB: 'ZERO_OR_MORE',
  relType: 'NON_IDENTIFYING'
});
```

### Styling Application
```typescript
erDb.addClass(['Customer'], ['fill:#f9f', 'stroke:#333']);
erDb.setClass(['Customer'], ['highlight']);
```

## Error Handling

The module implements defensive programming practices:
- Entity existence validation before relationship creation
- Graceful handling of missing entities
- Safe attribute processing with default value assignment
- CSS style validation and sanitization

## Performance Considerations

- **Map-based entity storage**: O(1) lookup performance
- **Lazy entity creation**: Entities created on-demand
- **Compiled style caching**: Reduces repeated CSS processing
- **Efficient relationship indexing**: Direct entity reference storage

## Related Documentation

- [ER Types](er-types.md) - Entity and relationship type definitions
- [ER Configuration](er-configuration.md) - Diagram-specific configuration options
- [Diagram API](diagram_plugin_api.md) - General diagram API interface
- [Rendering Engine](rendering_engine.md) - Data rendering and visualization
- [Mermaid Core API](mermaid_core_api.md) - Core configuration and utilities