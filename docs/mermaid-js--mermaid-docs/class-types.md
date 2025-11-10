# Class Types Module Documentation

## Introduction

The class-types module is a core component of the Mermaid class diagram system, providing the fundamental type definitions and parsing logic for representing UML class diagrams. This module defines the data structures that represent classes, their members (methods and attributes), relationships, and other class diagram elements.

## Core Components

### ClassNode
The `ClassNode` interface represents a class in a UML class diagram. It contains all the visual and structural information needed to render a class, including its members, methods, styling, and relationships.

### ClassMember
The `ClassMember` class is a sophisticated parser and data structure that handles both method and attribute definitions in class diagrams. It supports UML visibility modifiers, generic types, static/classifier indicators, and proper text sanitization.

### ClassRelation
The `ClassRelation` interface defines relationships between classes, including association, inheritance, dependency, and other UML relationship types.

## Architecture

```mermaid
graph TB
    subgraph "Class Types Module"
        CN[ClassNode]
        CM[ClassMember]
        CR[ClassRelation]
        CN1[ClassNote]
        IN[Interface]
        NN[NamespaceNode]
        SC[StyleClass]
    end

    subgraph "Class Database Module"
        CDB[ClassDB]
    end

    subgraph "Configuration Module"
        CDC[ClassDiagramConfig]
    end

    subgraph "Common Utilities"
        ST[sanitizeText]
        PGT[parseGenericTypes]
        GC[getConfig]
    end

    CDB --> CN
    CDB --> CR
    CDB --> CN1
    CM --> ST
    CM --> PGT
    CM --> GC
    CN --> CM
    
    style CN fill:#e1f5fe
    style CM fill:#e1f5fe
    style CR fill:#e1f5fe
```

## Data Flow

```mermaid
sequenceDiagram
    participant Parser as "Class Diagram Parser"
    participant CM as "ClassMember"
    participant CN as "ClassNode"
    participant CDB as "ClassDB"
    participant Renderer as "Class Renderer"

    Parser->>CM: new ClassMember(input, type)
    CM->>CM: parseMember(input)
    CM->>CM: sanitizeText(input)
    CM->>CM: apply visibility rules
    CM->>CM: extract parameters/return types
    CM->>CN: add to methods/members array
    CN->>CDB: store in class map
    CDB->>Renderer: provide class data
    Renderer->>Renderer: render class diagram
```

## Component Details

### ClassMember Class

The `ClassMember` class is the most complex component in this module, providing sophisticated parsing capabilities for UML class members.

#### Key Features:
- **Visibility Parsing**: Supports UML visibility modifiers (`+` public, `-` private, `#` protected, `~` package)
- **Method Parsing**: Handles method signatures with parameters and return types
- **Attribute Parsing**: Processes attribute definitions with visibility and classifiers
- **Generic Type Support**: Integrates with `parseGenericTypes` for generic type handling
- **Classifier Support**: Handles static (`$`) and abstract (`*`) classifiers
- **Text Sanitization**: Ensures safe rendering of member text

#### Parsing Logic:

```mermaid
flowchart TD
    Start[Input: member string] --> CheckType{Member Type?}
    CheckType -->|Method| MethodRegex[Apply Method Regex]
    CheckType -->|Attribute| AttributeLogic[Apply Attribute Logic]
    
    MethodRegex --> ExtractVisibility[Extract Visibility]
    MethodRegex --> ExtractName[Extract Method Name]
    MethodRegex --> ExtractParams[Extract Parameters]
    MethodRegex --> ExtractReturn[Extract Return Type]
    MethodRegex --> ExtractClassifier[Extract Classifier]
    
    AttributeLogic --> CheckFirstChar[Check First Char]
    CheckFirstChar -->|Visibility| SetVisibility[Set Visibility]
    CheckFirstChar -->|No Visibility| SkipVisibility[Skip Visibility]
    AttributeLogic --> CheckLastChar[Check Last Char]
    CheckLastChar -->|Classifier| SetClassifier[Set Classifier]
    
    ExtractVisibility --> BuildDisplayText[Build Display Text]
    SetVisibility --> BuildDisplayText
    ExtractName --> BuildDisplayText
    ExtractParams --> BuildDisplayText
    ExtractReturn --> BuildDisplayText
    SetClassifier --> BuildDisplayText
    SkipVisibility --> BuildDisplayText
    
    BuildDisplayText --> ApplySanitization[Apply HTML Sanitization]
    ApplySanitization --> ReturnResult[Return Display Details]
```

### ClassNode Interface

The `ClassNode` interface represents a complete class with all its visual and structural properties:

- **Identity**: `id`, `label`, `domId` for unique identification
- **Content**: `methods`, `members`, `annotations` for class content
- **Styling**: `cssClasses`, `styles`, `shape`, `look` for visual appearance
- **Navigation**: `link`, `linkTarget`, `tooltip` for interactive features
- **Hierarchy**: `parent` for namespace containment

### ClassRelation Interface

Defines relationships between classes with:
- **Endpoints**: `id1`, `id2` for connected classes
- **Titles**: `relationTitle1`, `relationTitle2` for relationship labels
- **Type Information**: `type`, `relation` for UML relationship semantics
- **Styling**: `style`, `text` for visual representation

## Dependencies

The class-types module has several key dependencies:

- **[class-database.md](class-database.md)**: Uses `ClassNode` and `ClassRelation` for storing class diagram data
- **[class-configuration.md](class-configuration.md)**: Provides configuration options that affect parsing and rendering
- **[common-utilities.md](common-utilities.md)**: Uses `sanitizeText` and `parseGenericTypes` functions
- **[diagram-api.md](diagram-api.md)**: Integrates with the main diagram API for configuration access

## Usage Patterns

### Creating Class Members

```typescript
// Method example
const method = new ClassMember("+getName() : string", "method");
const methodDetails = method.getDisplayDetails();
// Result: displayText: "+getName() : string", cssStyle: ""

// Attribute example  
const attribute = new ClassMember("-age : int", "attribute");
const attributeDetails = attribute.getDisplayDetails();
// Result: displayText: "-age : int", cssStyle: ""

// Static method example
const staticMethod = new ClassMember("+createInstance()$ : MyClass", "method");
const staticDetails = staticMethod.getDisplayDetails();
// Result: displayText: "+createInstance()", cssStyle: "text-decoration:underline;"
```

### Building Class Relationships

```typescript
const relation: ClassRelation = {
  id1: "ClassA",
  id2: "ClassB", 
  relationTitle1: "",
  relationTitle2: "",
  type: "inheritance",
  title: "",
  text: "",
  style: [],
  relation: {
    type1: 1, // inheritance arrow
    type2: 0,
    lineType: 1 // solid line
  }
};
```

## Integration with Rendering System

The class-types module integrates with the rendering system through:

1. **Data Provision**: `ClassNode` and `ClassRelation` objects are passed to renderers
2. **Style Information**: CSS classes and styles are applied during rendering
3. **Layout Data**: Position and size information is added during layout phase
4. **Shape Definitions**: Visual representation is handled by the shape system

```mermaid
graph LR
    subgraph "Class Types"
        CN[ClassNode]
        CM[ClassMember]
        CR[ClassRelation]
    end
    
    subgraph "Rendering System"
        RD[RenderData]
        LD[LayoutData]
        SD[ShapeDefinition]
        TH[Theme]
    end
    
    CN --> RD
    CN --> LD
    CM --> SD
    CR --> RD
    TH --> SD
```

## Extension Points

The module provides several extension points:

- **Custom Visibility**: The `Visibility` type can be extended with new visibility modifiers
- **Classifier Support**: Additional classifiers can be added to the parsing logic
- **Style Classes**: New CSS styles can be defined for different member types
- **Relationship Types**: New relationship types can be defined in `ClassRelation`

## Best Practices

1. **Text Sanitization**: Always use `sanitizeText` for user input to prevent XSS attacks
2. **Generic Type Handling**: Use `parseGenericTypes` for consistent generic type rendering
3. **Visibility Validation**: Use the `visibilityValues` array for validating visibility modifiers
4. **Classifier Consistency**: Maintain consistent classifier usage across the application
5. **ID Generation**: Use proper ID generation for DOM elements to avoid conflicts

## Related Documentation

- [Class Database](class-database.md) - Data storage and management for class diagrams
- [Class Configuration](class-configuration.md) - Configuration options for class diagrams
- [Rendering Types](rendering-types.md) - Core rendering data structures
- [Shape System](shape-system.md) - Visual representation of diagram elements
- [Theme System](theme-system.md) - Styling and theming capabilities