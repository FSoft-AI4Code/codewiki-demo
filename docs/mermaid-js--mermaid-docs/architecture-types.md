# Architecture Types Module

The architecture-types module defines the core type system for architecture diagrams in Mermaid, providing the foundational data structures and type definitions for creating system architecture visualizations. This module establishes the type safety and structure for representing services, groups, junctions, and their relationships in architectural diagrams.

## Overview

The architecture-types module serves as the type foundation for the architecture diagram implementation in Mermaid. It defines comprehensive TypeScript interfaces and type definitions that enable the creation of system architecture diagrams showing services, their connections, and organizational groupings. The module provides type-safe representations of architectural elements including services, junctions, groups, and edges with directional relationships.

## Architecture

### Module Structure

```mermaid
graph TB
    subgraph "architecture-types Module"
        AT[architectureTypes.ts]
        
        subgraph "Core Type Definitions"
            AD[ArchitectureDirection]
            ADB[ArchitectureDB]
            AS[ArchitectureService]
            AG[ArchitectureGroup]
            AJ[ArchitectureJunction]
            AE[ArchitectureEdge]
            NS[NodeSingular]
            ES[EdgeSingular]
            ESD[EdgeSingularData]
            ASO[ArchitectureStyleOptions]
            ADS[ArchitectureDataStructures]
            AST[ArchitectureState]
        end
        
        subgraph "Direction System"
            ADX[ArchitectureDirectionX]
            ADY[ArchitectureDirectionY]
            ADP[ArchitectureDirectionPair]
            ADPM[ArchitectureDirectionPairMap]
            AA[ArchitectureAlignment]
        end
        
        subgraph "Utility Functions"
            GAD[getArchitectureDirectionPair]
            SPBADP[shiftPositionByArchitectureDirectionPair]
            GADXY[getArchitectureDirectionXYFactors]
            GADA[getArchitectureDirectionAlignment]
            IAD[isArchitectureDirection]
            IADX[isArchitectureDirectionX]
            IADY[isArchitectureDirectionY]
            IADXY[isArchitectureDirectionXY]
            IVADP[isValidArchitectureDirectionPair]
        end
    end
    
    subgraph "Dependencies"
        DBB[DiagramDBBase]
        ADC[ArchitectureDiagramConfig]
        DE[D3Element]
        CS[cytoscape]
    end
    
    AT --> DBB
    AT --> ADC
    AT --> DE
    AT --> CS
    
    ADB -.->|extends| DBB
    ASO -.->|used by| ADB
    ADS -.->|used by| ADB
    AST -.->|contains| ADB
    
    NS -.->|extends| CS
    ES -.->|extends| CS
    ESD -.->|used by| ES
```

### Type Hierarchy

```mermaid
graph TD
    subgraph "Base Types"
        DBB[DiagramDBBase]
        DE[D3Element]
        CS[cytoscape types]
    end
    
    subgraph "Architecture Types"
        ADB[ArchitectureDB<br/>extends DiagramDBBase]
        AS[ArchitectureService]
        AJ[ArchitectureJunction]
        AG[ArchitectureGroup]
        AE[ArchitectureEdge]
        AN[ArchitectureNode<br/>AS or AJ]
        ADS[ArchitectureDataStructures]
        AST[ArchitectureState]
    end
    
    subgraph "Cytoscape Extensions"
        NS[NodeSingular<br/>extends cytoscape.NodeSingular]
        ES[EdgeSingular<br/>extends cytoscape.EdgeSingular]
        ESD[EdgeSingularData]
        NSD[NodeSingularData]
    end
    
    subgraph "Direction System"
        AD[ArchitectureDirection<br/>L R T B]
        ADX[ArchitectureDirectionX<br/>L R]
        ADY[ArchitectureDirectionY<br/>T B]
        ADP[ArchitectureDirectionPair]
        AA[ArchitectureAlignment<br/>vertical horizontal bend]
    end
    
    DBB --> ADB
    DE --> AST
    CS --> NS
    CS --> ES
    
    AS --> AN
    AJ --> AN
    AE -->|references| AN
    AST -->|contains| ADB
    AST -->|contains| ADS
    
    NS --> NSD
    ES --> ESD
    
    AD --> ADX
    AD --> ADY
    ADP -->|composed of| AD
```

## Core Components

### ArchitectureDB

The `ArchitectureDB` interface extends `DiagramDBBase` and serves as the primary database interface for architecture diagrams. It provides methods for managing services, junctions, groups, and edges within the diagram.

**Key Methods:**
- `addService()`: Adds a new service node to the diagram
- `addJunction()`: Adds a junction node for connecting edges
- `addGroup()`: Creates organizational groups for services
- `addEdge()`: Establishes connections between nodes
- `getServices()`, `getJunctions()`, `getGroups()`, `getEdges()`: Retrieval methods
- `setElementForId()`, `getElementById()`: D3 element management

### ArchitectureService

Represents a service component in the architecture diagram with properties for identification, visualization, and connection management.

**Properties:**
- `id`: Unique identifier
- `type`: Always 'service' for type discrimination
- `edges`: Array of connected edges
- `icon`, `iconText`: Visual representation options
- `title`: Display name
- `in`: Group membership identifier
- `width`, `height`: Dimension specifications

### ArchitectureJunction

Special node type used as connection points for edges, enabling complex routing and multiple connections.

**Properties:**
- `id`: Unique identifier
- `type`: Always 'junction' for type discrimination
- `edges`: Array of connected edges
- `in`: Group membership identifier
- `width`, `height`: Dimension specifications

### ArchitectureGroup

Organizational container for grouping related services and junctions in the diagram.

**Properties:**
- `id`: Unique identifier
- `icon`: Optional group icon
- `title`: Group display name
- `in`: Parent group identifier for nested groups

### ArchitectureEdge

Defines connections between nodes with directional information and styling options.

**Properties:**
- `lhsId`, `rhsId`: Source and target node identifiers
- `lhsDir`, `rhsDir`: Connection directions (L, R, T, B)
- `lhsInto`, `rhsInto`: Boolean flags for inward connections
- `lhsGroup`, `rhsGroup`: Boolean flags for group connections
- `title`: Edge label text

### Direction System

The module implements a comprehensive direction system for precise edge routing:

```mermaid
graph LR
    subgraph "Direction Types"
        L[L - Left]
        R[R - Right]
        T[T - Top]
        B[B - Bottom]
    end
    
    subgraph "Valid Pairs"
        LR[LR - Left to Right]
        RL[RL - Right to Left]
        TB[TB - Top to Bottom]
        BT[BT - Bottom to Top]
        LT[LT - Left to Top]
        LB[LB - Left to Bottom]
        RT[RT - Right to Top]
        RB[RB - Right to Bottom]
        TL[TL - Top to Left]
        TR[TR - Top to Right]
        BL[BL - Bottom to Left]
        BR[BR - Bottom to Right]
    end
    
    subgraph "Invalid Pairs"
        LL[LL - Left to Left]
        RR[RR - Right to Right]
        TT[TT - Top to Top]
        BB[BB - Bottom to Bottom]
    end
    
    L --> LR
    L --> LT
    L --> LB
    R --> RL
    R --> RT
    R --> RB
    T --> TB
    T --> TL
    T --> TR
    B --> BT
    B --> BL
    B --> BR
    
    L -.-> LL
    R -.-> RR
    T -.-> TT
    B -.-> BB
```

### Cytoscape Integration

The module extends Cytoscape.js types for rendering architecture diagrams:

```mermaid
graph TD
    subgraph "Cytoscape Extensions"
        NS[NodeSingular]
        ES[EdgeSingular]
        ESD[EdgeSingularData]
        NSD[NodeSingularData]
    end
    
    subgraph "Node Types"
        NSS[Service Node Data]
        NSJ[Junction Node Data]
        NSG[Group Node Data]
    end
    
    subgraph "Edge Data"
        EDID[ID]
        EDLABEL[Label]
        EDSRC[Source Info]
        EDTGT[Target Info]
    end
    
    NS --> NSD
    NSD --> NSS
    NSD --> NSJ
    NSD --> NSG
    
    ES --> ESD
    ESD --> EDID
    ESD --> EDLABEL
    ESD --> EDSRC
    ESD --> EDTGT
```

## Data Flow

### Architecture Diagram Processing Pipeline

```mermaid
sequenceDiagram
    participant Parser
    participant DB as ArchitectureDB
    participant Types as Architecture Types
    participant Renderer
    participant Cytoscape
    
    Parser->>DB: Parse architecture syntax
    DB->>Types: Create service objects
    DB->>Types: Create junction objects
    DB->>Types: Create group objects
    DB->>Types: Create edge objects
    
    DB->>DB: Build adjacency lists
    DB->>DB: Calculate spatial maps
    DB->>DB: Determine group alignments
    
    Renderer->>DB: Request data structures
    DB->>Renderer: Return ArchitectureDataStructures
    
    Renderer->>Cytoscape: Create NodeSingular objects
    Renderer->>Cytoscape: Create EdgeSingular objects
    Renderer->>Cytoscape: Apply layout algorithms
    Cytoscape->>Renderer: Return positioned elements
    Renderer->>Renderer: Render SVG output
```

### State Management

```mermaid
stateDiagram-v2
    [*] --> EmptyState
    
    EmptyState --> ServiceAdded: addService()
    EmptyState --> JunctionAdded: addJunction()
    EmptyState --> GroupAdded: addGroup()
    
    ServiceAdded --> EdgeAdded: addEdge()
    JunctionAdded --> EdgeAdded: addEdge()
    GroupAdded --> ServiceAdded: addService() with group
    GroupAdded --> JunctionAdded: addJunction() with group
    
    EdgeAdded --> EdgeAdded: addEdge()
    EdgeAdded --> ServiceAdded: addService()
    EdgeAdded --> JunctionAdded: addJunction()
    
    ServiceAdded --> ElementRegistered: setElementForId()
    JunctionAdded --> ElementRegistered: setElementForId()
    GroupAdded --> ElementRegistered: setElementForId()
    
    ElementRegistered --> ReadyState: All elements positioned
    ReadyState --> [*]: clear()
```

## Component Relationships

### Type Dependencies

```mermaid
graph TB
    subgraph "External Dependencies"
        DBB[DiagramDBBase]
        ADC[ArchitectureDiagramConfig]
        DE[D3Element]
        CS[cytoscape]
    end
    
    subgraph "Core Types"
        ADB[ArchitectureDB]
        AS[ArchitectureService]
        AJ[ArchitectureJunction]
        AG[ArchitectureGroup]
        AE[ArchitectureEdge]
        AN[ArchitectureNode]
        ADS[ArchitectureDataStructures]
        AST[ArchitectureState]
    end
    
    subgraph "Cytoscape Extensions"
        NS[NodeSingular]
        ES[EdgeSingular]
        ESD[EdgeSingularData]
    end
    
    subgraph "Direction System"
        AD[ArchitectureDirection]
        ADX[ArchitectureDirectionX]
        ADY[ArchitectureDirectionY]
        ADP[ArchitectureDirectionPair]
        AA[ArchitectureAlignment]
    end
    
    subgraph "Style & Configuration"
        ASO[ArchitectureStyleOptions]
    end
    
    DBB --> ADB
    ADC --> ADB
    ADC --> AST
    DE --> ADB
    DE --> AST
    
    CS --> NS
    CS --> ES
    
    ADB --> AS
    ADB --> AJ
    ADB --> AG
    ADB --> AE
    ADB --> ADS
    ADB --> AST
    
    AS --> AN
    AJ --> AN
    AE --> AN
    
    NS --> ESD
    ES --> ESD
    
    AD --> AE
    AD --> ADX
    AD --> ADY
    ADP --> AD
    AA --> ADP
    
    ASO --> ADB
```

### Integration Points

The architecture-types module integrates with several other Mermaid modules:

- **[config](config.md)**: Uses `ArchitectureDiagramConfig` for configuration management
- **[diagram-api](diagram-api.md)**: Extends `DiagramDBBase` and integrates with diagram API types
- **[types](types.md)**: Utilizes `D3Element` and other core type definitions
- **[architecture-database](architecture-database.md)**: Implements the `ArchitectureDB` interface

## Key Features

### Type Safety

The module provides comprehensive type safety through:
- Discriminated unions for node types (Service vs Junction)
- Direction validation with compile-time checking
- Cytoscape integration with proper type extensions
- Configuration type integration

### Direction System

Advanced direction handling includes:
- Cardinal directions (L, R, T, B)
- Direction pair validation
- XY direction detection for bend routing
- Position shifting algorithms
- Arrow rendering helpers

### Data Structure Management

Efficient data organization through:
- Adjacency lists for connection tracking
- Spatial maps for layout calculations
- Group alignment matrices
- State management for rendering pipeline

## Usage Patterns

### Creating Architecture Elements

```typescript
// Service creation
const service: ArchitectureService = {
  id: 'web-server',
  type: 'service',
  edges: [],
  title: 'Web Server',
  icon: 'server',
  width: 120,
  height: 60
};

// Junction creation
const junction: ArchitectureJunction = {
  id: 'junction-1',
  type: 'junction',
  edges: [],
  width: 20,
  height: 20
};

// Edge creation
const edge: ArchitectureEdge = {
  lhsId: 'web-server',
  lhsDir: 'R',
  rhsId: 'database',
  rhsDir: 'L',
  title: 'HTTP Request'
};
```

### Direction Validation

```typescript
// Validate direction pairs
const pair = getArchitectureDirectionPair('L', 'R'); // Returns 'LR'
const invalidPair = getArchitectureDirectionPair('L', 'L'); // Returns undefined

// Check direction types
if (isArchitectureDirectionX('L')) {
  // Handle horizontal direction
}

if (isArchitectureDirectionXY('L', 'T')) {
  // Handle bend routing
}
```

This comprehensive type system enables the creation of complex, well-structured architecture diagrams while maintaining type safety and providing robust validation mechanisms.