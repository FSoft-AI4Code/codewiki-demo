# classTypes Module Documentation

## Introduction

The `classTypes` module is a core component of Mermaid's class diagram functionality, providing the fundamental type definitions and parsing logic for representing object-oriented structures. This module defines the data structures that model classes, interfaces, relationships, and their members in UML class diagrams.

## Module Purpose

The primary purpose of the classTypes module is to:
- Define TypeScript interfaces and types for class diagram elements
- Provide parsing logic for class members (methods and attributes)
- Handle visibility modifiers and classifiers (static, abstract)
- Support namespace organization and styling capabilities

## Core Components

### ClassNode Interface
The central interface representing a class in the diagram:
```typescript
interface ClassNode {
  id: string;
  type: string;
  label: string;
  shape: string;
  text: string;
  cssClasses: string;
  methods: ClassMember[];
  members: ClassMember[];
  annotations: string[];
  domId: string;
  styles: string[];
  parent?: string;
  link?: string;
  linkTarget?: string;
  haveCallback?: boolean;
  tooltip?: string;
  look?: string;
}
```

### ClassMember Class
A comprehensive parser for class members (methods and attributes):
- **Visibility Support**: Handles UML visibility modifiers (`+` public, `-` private, `#` protected, `~` package)
- **Classifier Support**: Manages static (`$`) and abstract (`*`) modifiers
- **Method Parsing**: Extracts parameters and return types using regex patterns
- **Attribute Parsing**: Processes attribute declarations with proper visibility
- **Generic Type Support**: Integrates with `parseGenericTypes` for template/generic handling

### ClassRelation Interface
Defines relationships between classes:
```typescript
interface ClassRelation {
  id1: string;           // Source class ID
  id2: string;           // Target class ID
  relationTitle1: string;
  relationTitle2: string;
  type: string;
  title: string;
  text: string;
  style: string[];
  relation: {
    type1: number;
    type2: number;
    lineType: number;
  };
}
```

### Supporting Interfaces
- **Interface**: Represents interface implementations
- **ClassNote**: Handles annotations and comments on classes
- **NamespaceNode**: Manages namespace hierarchies
- **StyleClass**: Defines custom styling for diagram elements

## Architecture

```mermaid
graph TB
    subgraph "classTypes Module"
        CN[ClassNode]
        CM[ClassMember]
        CR[ClassRelation]
        INT[Interface]
        CNODE[ClassNote]
        NN[NamespaceNode]
        SC[StyleClass]
        
        CM -->|"parses into"| CN
        CM -->|"parses into"| CN
        CR -->|"connects"| CN
        CR -->|"connects"| CN
        INT -->|"implements"| CN
        CNODE -->|"annotates"| CN
        NN -->|"contains"| CN
        SC -->|"styles"| CN
    end
    
    subgraph "External Dependencies"
        API[diagramAPI]
        COMMON[common]
        CONFIG[getConfig]
        SANITIZE[sanitizeText]
        PARSE[parseGenericTypes]
    end
    
    CM -->|"uses"| CONFIG
    CM -->|"uses"| SANITIZE
    CM -->|"uses"| PARSE
```

## Data Flow

```mermaid
sequenceDiagram
    participant Parser as "Class Diagram Parser"
    participant CM as "ClassMember"
    participant Config as "getConfig()"
    participant Sanitize as "sanitizeText()"
    participant Generic as "parseGenericTypes()"
    
    Parser->>CM: new ClassMember(input, type)
    CM->>Config: getConfig()
    CM->>Sanitize: sanitizeText(input, config)
    CM->>CM: parseMember(sanitizedInput)
    alt Method Parsing
        CM->>CM: methodRegEx.exec(input)
        CM->>Generic: parseGenericTypes(parameters)
        CM->>Generic: parseGenericTypes(returnType)
    else Attribute Parsing
        CM->>CM: Extract visibility & classifier
        CM->>Generic: parseGenericTypes(id)
    end
    CM->>CM: parseClassifier()
    CM->>Parser: Return parsed member
```

## Component Relationships

```mermaid
classDiagram
    class ClassNode {
        +string id
        +string label
        +ClassMember[] methods
        +ClassMember[] members
        +string[] annotations
        +string cssClasses
        +string[] styles
    }
    
    class ClassMember {
        +string id
        +Visibility visibility
        +string memberType
        +string classifier
        +string parameters
        +string returnType
        +parseMember(input)
        +getDisplayDetails()
        +parseClassifier()
    }
    
    class ClassRelation {
        +string id1
        +string id2
        +string type
        +string title
        +string text
        +string[] style
    }
    
    class NamespaceNode {
        +string id
        +ClassMap classes
        +NamespaceMap children
    }
    
    class Interface {
        +string id
        +string label
        +string classId
    }
    
    ClassNode "1" --> "*" ClassMember : contains
    ClassNode "*" <-- "*" ClassRelation : connects
    NamespaceNode "1" --> "*" ClassNode : contains
    Interface "*" --> "1" ClassNode : implements
```

## Process Flow

### Member Parsing Process
```mermaid
flowchart TD
    Start([Input Member String])
    Sanitize{sanitizeText}
    TypeCheck{Member Type?}
    MethodPath[Method Parsing]
    AttributePath[Attribute Parsing]
    
    MethodRegex[Apply methodRegEx]
    ExtractVis[Extract Visibility]
    ExtractParams[Extract Parameters]
    ExtractReturn[Extract Return Type]
    ExtractClassifier[Extract Classifier]
    
    AttrVis[Check First Char for Visibility]
    AttrClassifier[Check Last Char for Classifier]
    ExtractId[Extract ID]
    
    ParseGeneric[parseGenericTypes]
    BuildText[Build Display Text]
    ParseCSS[parseClassifier for CSS]
    
    Start --> Sanitize
    Sanitize --> TypeCheck
    TypeCheck -->|Method| MethodPath
    TypeCheck -->|Attribute| AttributePath
    
    MethodPath --> MethodRegex
    MethodRegex --> ExtractVis
    ExtractVis --> ExtractParams
    ExtractParams --> ExtractReturn
    ExtractReturn --> ExtractClassifier
    ExtractClassifier --> ParseGeneric
    
    AttributePath --> AttrVis
    AttrVis --> AttrClassifier
    AttrClassifier --> ExtractId
    ExtractId --> ParseGeneric
    
    ParseGeneric --> BuildText
    BuildText --> ParseCSS
    ParseCSS --> End([Return Parsed Member])
```

## Dependencies

The classTypes module has the following key dependencies:

- **[diagramAPI](../diagram-api.md)**: Provides configuration access via `getConfig()`
- **[common](../common-types.md)**: Supplies text sanitization and generic type parsing utilities
- **[config](../config.md)**: Configuration types for diagram styling and behavior

## Integration with Class Diagram System

```mermaid
graph LR
    subgraph "Class Diagram Processing Pipeline"
        Parser[Class Parser]
        DB[ClassDB]
        Types[classTypes]
        Renderer[Class Renderer]
    end
    
    Parser -->|"creates instances"| Types
    Types -->|"stored in"| DB
    DB -->|"provides data to"| Renderer
    
    subgraph "classTypes Components"
        CM[ClassMember]
        CN[ClassNode]
        CR[ClassRelation]
        NN[NamespaceNode]
    end
    
    Types -.-> CM
    Types -.-> CN
    Types -.-> CR
    Types -.-> NN
```

## Key Features

### 1. UML Compliance
- Supports standard UML visibility modifiers
- Handles method signatures with parameters and return types
- Manages classifiers for static and abstract members

### 2. Flexible Parsing
- Regex-based parsing for method signatures
- Character-based parsing for attributes
- Generic type support through `parseGenericTypes`

### 3. Styling Support
- CSS class assignment based on classifiers
- Custom style properties for individual elements
- Integration with theme system

### 4. Namespace Organization
- Hierarchical namespace support
- Class grouping and organization
- Parent-child relationships

## Usage Examples

The classTypes module is primarily used internally by the class diagram parser and renderer. The `ClassMember` class automatically handles parsing when instantiated:

```typescript
// Method parsing
const method = new ClassMember('+getName() : string', 'method');
// Results in: visibility='+', id='getName', parameters='', returnType='string'

// Attribute parsing  
const attribute = new ClassMember('-age : int', 'attribute');
// Results in: visibility='-', id='age', classifier=''

// Static method
const staticMethod = new ClassMethod('$getInstance() : ClassName', 'method');
// Results in: classifier='$', cssStyle='text-decoration:underline;'
```

## Related Documentation

- [classDb Module](classDb.md) - Database operations for class diagrams
- [classRenderer Module](classRenderer.md) - Rendering logic for class diagrams
- [config Module](config.md) - Configuration management
- [diagram-api Module](diagram-api.md) - Core diagram API functionality