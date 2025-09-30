# Requirement Types Module Documentation

## Introduction

The requirement-types module defines the core type definitions for requirement diagrams in Mermaid. This module provides the fundamental data structures and type definitions that enable the creation, validation, and rendering of requirement diagrams, which are used to model system requirements, their relationships, and verification methods in software engineering and systems analysis.

## Core Components

### 1. Requirement Interface

The `Requirement` interface represents individual requirements within a requirement diagram. It encapsulates all essential properties of a requirement including its type, verification method, risk level, and styling information.

**Properties:**
- `name`: Human-readable name of the requirement
- `type`: Categorization of the requirement (RequirementType)
- `requirementId`: Unique identifier for the requirement
- `text`: Detailed description of the requirement
- `risk`: Risk level assessment (Low, Medium, High)
- `verifyMethod`: Verification approach (Analysis, Demonstration, Inspection, Test)
- `cssStyles`: Array of CSS style classes for visual customization
- `classes`: Array of additional CSS classes

### 2. Relation Interface

The `Relation` interface defines relationships between different requirements and elements within the diagram. It supports various relationship types that represent different semantic connections in requirement engineering.

**Properties:**
- `type`: Type of relationship (contains, copies, derives, satisfies, verifies, refines, traces)
- `src`: Source element identifier
- `dst`: Destination element identifier

### 3. Element Interface

The `Element` interface represents general elements within requirement diagrams that may not be formal requirements but are related to the requirement ecosystem.

**Properties:**
- `name`: Element name
- `type`: Element type classification
- `docRef`: Documentation reference
- `cssStyles`: Array of CSS style classes
- `classes`: Array of additional CSS classes

### 4. RequirementClass Interface

The `RequirementClass` interface defines styling classes that can be applied to requirements for consistent visual representation across the diagram.

**Properties:**
- `id`: Unique identifier for the class
- `styles`: Array of CSS styles
- `textStyles`: Array of text-specific styling properties

## Type Definitions

### RequirementType
Enumerates the different types of requirements supported:
- `Requirement`: General requirement
- `Functional Requirement`: Functionality-specific requirement
- `Interface Requirement`: Interface-related requirement
- `Performance Requirement`: Performance-related requirement
- `Physical Requirement`: Physical constraint requirement
- `Design Constraint`: Design limitation requirement

### RiskLevel
Defines the risk assessment levels:
- `Low`: Low risk requirement
- `Medium`: Medium risk requirement
- `High`: High risk requirement

### VerifyType
Specifies verification methods:
- `Analysis`: Analytical verification
- `Demonstration`: Demonstration-based verification
- `Inspection`: Inspection-based verification
- `Test`: Testing-based verification

### RelationshipType
Defines the types of relationships between elements:
- `contains`: Container relationship
- `copies`: Copying relationship
- `derives`: Derivation relationship
- `satisfies`: Satisfaction relationship
- `verifies`: Verification relationship
- `refines`: Refinement relationship
- `traces`: Traceability relationship

## Architecture

```mermaid
graph TB
    subgraph "Requirement Types Module"
        Requirement[Requirement Interface]
        Relation[Relation Interface]
        Element[Element Interface]
        RequirementClass[RequirementClass Interface]
        
        RequirementType[RequirementType Enum]
        RiskLevel[RiskLevel Enum]
        VerifyType[VerifyType Enum]
        RelationshipType[RelationshipType Enum]
    end
    
    subgraph "Requirement Database Module"
        RequirementDB[RequirementDB Class]
    end
    
    subgraph "Configuration Module"
        RequirementDiagramConfig[RequirementDiagramConfig]
    end
    
    Requirement --> RequirementType
    Requirement --> RiskLevel
    Requirement --> VerifyType
    
    Relation --> RelationshipType
    
    RequirementDB --> Requirement
    RequirementDB --> Relation
    RequirementDB --> Element
    RequirementDB --> RequirementClass
    
    RequirementDiagramConfig --> RequirementClass
```

## Data Flow

```mermaid
sequenceDiagram
    participant Parser
    participant RequirementDB
    participant Types
    participant Renderer
    
    Parser->>Types: Create Requirement objects
    Types-->>Parser: Return typed requirements
    Parser->>RequirementDB: Store requirements
    Parser->>Types: Create Relation objects
    Types-->>Parser: Return typed relations
    Parser->>RequirementDB: Store relations
    
    Renderer->>RequirementDB: Retrieve requirements
    RequirementDB-->>Renderer: Return Requirement[]
    Renderer->>RequirementDB: Retrieve relations
    RequirementDB-->>Renderer: Return Relation[]
    Renderer->>Types: Apply styling classes
    Types-->>Renderer: Return styled elements
```

## Component Interactions

```mermaid
graph LR
    subgraph "Type System"
        Req[Requirement]
        Rel[Relation]
        Elem[Element]
        ReqClass[RequirementClass]
    end
    
    subgraph "Enumeration Types"
        ReqType[RequirementType]
        Risk[RiskLevel]
        Verify[VerifyType]
        RelType[RelationshipType]
    end
    
    subgraph "Usage Context"
        Parser[Parser]
        DB[RequirementDB]
        Renderer[Renderer]
        Config[Configuration]
    end
    
    Parser --> Req
    Parser --> Rel
    Parser --> Elem
    
    Req --> ReqType
    Req --> Risk
    Req --> Verify
    
    Rel --> RelType
    
    DB --> Req
    DB --> Rel
    DB --> Elem
    DB --> ReqClass
    
    Renderer --> Req
    Renderer --> Rel
    Renderer --> Elem
    Renderer --> ReqClass
    
    Config --> ReqClass
```

## Process Flow

```mermaid
flowchart TD
    A[Requirement Diagram Input] --> B{Parse Requirement}
    B --> C[Create Requirement Object]
    C --> D[Validate RequirementType]
    D --> E[Set RiskLevel]
    E --> F[Set VerifyType]
    F --> G[Apply CSS Classes]
    
    H[Relationship Input] --> I{Parse Relation}
    I --> J[Create Relation Object]
    J --> K[Validate RelationshipType]
    K --> L[Set Source/Destination]
    
    M[Element Input] --> N{Parse Element}
    N --> O[Create Element Object]
    O --> P[Apply Styling]
    
    Q[Style Definition] --> R{Parse Style}
    R --> S[Create RequirementClass]
    S --> T[Define Styles]
    T --> U[Define TextStyles]
    
    G --> V[Store in RequirementDB]
    L --> V
    P --> V
    U --> V
    
    V --> W[Render Diagram]
    W --> X[Display Requirement Diagram]
```

## Integration with Other Modules

### Requirement Database Module
The requirement-types module is tightly integrated with the [requirement-database](requirement-database.md) module. The database module uses these type definitions to store and manage requirement diagram data structures.

### Configuration Module
The [config](config.md) module's `RequirementDiagramConfig` utilizes the `RequirementClass` interface to define styling configurations for requirement diagrams.

### Rendering System
The rendering system uses these type definitions to properly display requirement diagrams with appropriate styling, relationships, and visual representations.

## Usage Examples

### Creating a Requirement
```typescript
const requirement: Requirement = {
    name: "User Authentication",
    type: "Functional Requirement",
    requirementId: "REQ-001",
    text: "The system shall provide secure user authentication",
    risk: "High",
    verifyMethod: "Test",
    cssStyles: ["requirement-box"],
    classes: ["high-priority"]
};
```

### Defining a Relationship
```typescript
const relation: Relation = {
    type: "satisfies",
    src: "REQ-001",
    dst: "REQ-002"
};
```

### Creating a Style Class
```typescript
const requirementClass: RequirementClass = {
    id: "high-priority",
    styles: ["fill: #ff0000", "stroke: #000000"],
    textStyles: ["font-weight: bold", "font-size: 14px"]
};
```

## Best Practices

1. **Type Safety**: Always use the defined enum types instead of string literals to ensure type safety
2. **Consistent Styling**: Use `RequirementClass` for consistent styling across multiple requirements
3. **Relationship Validation**: Ensure source and destination IDs exist before creating relationships
4. **Risk Assessment**: Properly assess and set risk levels for effective requirement management
5. **Verification Planning**: Choose appropriate verification methods based on requirement type

## Dependencies

- **Internal**: Works closely with [requirement-database](requirement-database.md) for data persistence
- **Configuration**: Integrates with [config](config.md) module for diagram styling
- **Rendering**: Used by rendering utilities for visual representation
- **Parser**: Consumed by the requirement diagram parser for syntax validation

## Extension Points

The module provides a solid foundation for extending requirement diagram functionality:
- New requirement types can be added to the `RequirementType` enum
- Additional relationship types can be included in `RelationshipType`
- New verification methods can be added to `VerifyType`
- Custom styling properties can be extended in the interfaces

This modular design ensures that the requirement diagram system remains flexible and maintainable while providing a robust type-safe foundation for requirement engineering visualization.