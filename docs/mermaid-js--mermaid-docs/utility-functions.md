# Utility Functions Module

## Introduction

The utility-functions module serves as the foundational utility layer within the Mermaid diagram rendering system. It provides a comprehensive set of helper functions, mathematical calculations, text processing utilities, and ID generation capabilities that are essential for diagram rendering, text manipulation, and overall system functionality. This module acts as a shared utility layer that supports all diagram types and rendering operations throughout the Mermaid ecosystem.

## Architecture Overview

The utility-functions module is designed as a centralized utility library that provides cross-cutting concerns for the entire Mermaid system. It sits at the core of the rendering engine and provides essential services to diagram plugins, rendering components, and the main Mermaid API.

```mermaid
graph TB
    subgraph "Mermaid Core API"
        Mermaid[Mermaid Core]
        Config[MermaidConfig]
        Parser[ParseResult]
        Renderer[RenderResult]
    end
    
    subgraph "Utility Functions Module"
        Utils[Utility Functions]
        IDGen[InitIDGenerator]
        TextUtils[Text Utilities]
        MathUtils[Mathematical Utilities]
        D3Utils[D3/Rendering Utilities]
        Security[Security Utilities]
    end
    
    subgraph "Rendering Engine"
        RenderData[RenderData]
        LayoutData[LayoutData]
        BaseNode[BaseNode]
        Edge[Edge]
        Theme[Theme]
    end
    
    subgraph "Diagram Plugins"
        Flowchart[Flowchart]
        Sequence[Sequence]
        Class[Class]
        State[State]
        ER[ER Diagram]
        Git[Git Graph]
    end
    
    Mermaid --> Utils
    Config --> Utils
    Parser --> Utils
    Renderer --> Utils
    
    Utils --> RenderData
    Utils --> LayoutData
    Utils --> BaseNode
    Utils --> Edge
    Utils --> Theme
    
    Utils --> Flowchart
    Utils --> Sequence
    Utils --> Class
    Utils --> State
    Utils --> ER
    Utils --> Git
    
    IDGen --> BaseNode
    TextUtils --> RenderData
    MathUtils --> LayoutData
    D3Utils --> Edge
    Security --> Config
```

## Core Components

### InitIDGenerator Class

The `InitIDGenerator` class provides deterministic and non-deterministic ID generation capabilities essential for creating unique identifiers throughout the diagram rendering process.

```mermaid
classDiagram
    class InitIDGenerator {
        -count: number
        +next: () => number
        +constructor(deterministic: boolean, seed?: string)
    }
    
    class DiagramRenderer {
        <<interface>>
        +render(diagram: Diagram): void
    }
    
    class BaseNode {
        <<interface>>
        +id: string
        +x: number
        +y: number
    }
    
    class Edge {
        <<interface>>
        +id: string
        +from: string
        +to: string
    }
    
    InitIDGenerator --> BaseNode : generates IDs
    InitIDGenerator --> Edge : generates IDs
    DiagramRenderer --> InitIDGenerator : uses for ID generation
```

**Key Features:**
- **Deterministic Mode**: Produces sequential IDs based on an internal counter, ensuring reproducible results
- **Non-deterministic Mode**: Uses timestamp-based IDs for unique generation
- **Seed Support**: Allows initialization with a seed string for predictable ID sequences

## Functional Categories

### 1. Text Processing and Dimension Calculation

The module provides sophisticated text processing capabilities essential for diagram rendering:

```mermaid
graph LR
    subgraph "Text Processing Pipeline"
        A[Input Text] --> B[calculateTextDimensions]
        B --> C[Font Analysis]
        C --> D[SVG Measurement]
        D --> E[Dimension Results]
        
        F[Label Text] --> G[wrapLabel]
        G --> H[Line Breaking]
        H --> I[Width Calculation]
        I --> J[Wrapped Text]
        
        K[HTML Entities] --> L[entityDecode]
        L --> M[HTML Parsing]
        M --> N[Decoded Text]
    end
    
    subgraph "Supporting Functions"
        O[parseFontSize] --> P[Size Parsing]
        P --> Q[Unit Conversion]
        
        R[getTextObj] --> S[Default Config]
        S --> T[Text Object]
    end
```

**Key Functions:**
- `calculateTextDimensions()`: Calculates precise text dimensions using SVG rendering
- `calculateTextWidth()` / `calculateTextHeight()`: Specialized dimension calculations
- `wrapLabel()`: Intelligent text wrapping with hyphenation support
- `entityDecode()`: Safe HTML entity decoding
- `parseFontSize()`: Flexible font size parsing with unit support

### 2. Mathematical and Geometric Calculations

Provides essential mathematical operations for diagram layout and positioning:

```mermaid
graph TD
    A[Point Data] --> B[Distance Calculation]
    B --> C[Edge Traversal]
    C --> D[Label Positioning]
    
    E[Curve Points] --> F[calculatePoint]
    F --> G[Interpolation]
    G --> H[Position Results]
    
    I[Edge Points] --> J[calcLabelPosition]
    J --> K[Midpoint Calculation]
    K --> L[Label Placement]
    
    M[Cardinality Points] --> N[calcCardinalityPosition]
    N --> O[Angle Calculation]
    O --> P[Offset Application]
```

**Key Functions:**
- `calculatePoint()`: Interpolates points along curves with distance-based traversal
- `calcLabelPosition()`: Calculates optimal label positions on edges
- `calcCardinalityPosition()`: Positions cardinality indicators with angle calculations
- `distance()`: Euclidean distance calculations between points
- `roundNumber()`: Precision-based number rounding

### 3. D3.js Integration and Curve Management

Integrates with D3.js for advanced curve and rendering operations:

```mermaid
graph LR
    subgraph "D3 Curve System"
        A[Curve Name] --> B[interpolateToCurve]
        B --> C[d3CurveTypes Lookup]
        C --> D[Curve Factory]
        D --> E[Rendering]
        
        F[Curve Types] --> G[curveBasis]
        F --> H[curveCardinal]
        F --> I[curveLinear]
        F --> J[curveMonotone]
        F --> K[curveStep]
    end
    
    subgraph "D3 Utilities"
        L[drawSimpleText] --> M[SVG Text Creation]
        M --> N[Style Application]
        
        O[insertTitle] --> P[Title Positioning]
        P --> Q[SVG Integration]
    end
```

**Key Functions:**
- `interpolateToCurve()`: Maps curve names to D3 curve factories
- `drawSimpleText()`: Creates styled SVG text elements
- `insertTitle()`: Adds titles to SVG diagrams with proper positioning

### 4. Security and Sanitization

Provides security utilities for safe diagram rendering:

```mermaid
graph TD
    A[User Input] --> B[formatUrl]
    B --> C[sanitizeUrl]
    C --> D[Security Check]
    D --> E[Safe URL]
    
    F[Directive Text] --> G[detectDirective]
    G --> H[Directive Parsing]
    H --> I[JSON Extraction]
    I --> J[Configuration]
    
    K[HTML Input] --> L[encodeEntities]
    L --> M[Entity Encoding]
    M --> N[Safe Output]
```

**Key Functions:**
- `formatUrl()`: URL sanitization based on security configuration
- `detectDirective()`: Safe directive parsing with regex validation
- `encodeEntities()` / `decodeEntities()`: Custom entity encoding system
- `sanitizeDirective()`: Directive content sanitization

### 5. Configuration and Utility Functions

Provides general utility functions for system operations:

```mermaid
graph LR
    subgraph "Configuration Utilities"
        A[detectInit] --> B[Init Directive Detection]
        B --> C[Configuration Merge]
        C --> D[MermaidConfig]
        
        E[getStylesFromArray] --> F[Style Parsing]
        F --> G[CSS Generation]
    end
    
    subgraph "General Utilities"
        H[generateId] --> I[Random ID]
        I --> J[Unique Identifier]
        
        K[runFunc] --> L[Function Execution]
        L --> M[Window Context]
        
        N[cleanAndMerge] --> O[Object Merge]
        O --> P[Deep Merge]
    end
```

## Data Flow Integration

The utility-functions module integrates into the Mermaid data flow at multiple points:

```mermaid
sequenceDiagram
    participant User
    participant MermaidAPI
    participant Utils
    participant Parser
    participant Renderer
    participant SVG
    
    User->>MermaidAPI: Diagram Definition
    MermaidAPI->>Utils: detectInit()
    Utils-->>MermaidAPI: Configuration
    
    MermaidAPI->>Parser: Parse Diagram
    Parser->>Utils: calculateTextDimensions()
    Utils-->>Parser: Text Metrics
    
    Parser->>Utils: wrapLabel()
    Utils-->>Parser: Wrapped Text
    
    MermaidAPI->>Renderer: Render Diagram
    Renderer->>Utils: interpolateToCurve()
    Utils-->>Renderer: Curve Factory
    
    Renderer->>Utils: calcLabelPosition()
    Utils-->>Renderer: Label Position
    
    Renderer->>Utils: drawSimpleText()
    Utils-->>SVG: SVG Text Element
    
    Renderer->>Utils: formatUrl()
    Utils-->>Renderer: Safe URL
    
    Renderer-->>User: Rendered Diagram
```

## Dependencies and Integration

The utility-functions module has strategic dependencies that enable its functionality:

```mermaid
graph TD
    subgraph "External Dependencies"
        D3[D3.js Library]
        Sanitize[sanitize-url]
        Lodash[lodash-es]
    end
    
    subgraph "Internal Dependencies"
        Logger[Logger Module]
        Common[Common Module]
        Types[Types Module]
        Config[Config Module]
    end
    
    subgraph "Utility Functions"
        Utils[Utility Functions]
        IDGen[InitIDGenerator]
    end
    
    D3 --> Utils
    Sanitize --> Utils
    Lodash --> Utils
    
    Logger --> Utils
    Common --> Utils
    Types --> Utils
    Config --> Utils
    
    Utils --> IDGen
```

**External Dependencies:**
- **D3.js**: Provides curve factories, SVG manipulation, and mathematical operations
- **sanitize-url**: URL sanitization for security
- **lodash-es**: Utility functions for memoization and object merging

**Internal Dependencies:**
- **Logger Module**: Logging and error reporting
- **Common Module**: Shared constants and regex patterns
- **Types Module**: TypeScript type definitions
- **Config Module**: Configuration type definitions

## Error Handling and Validation

The module implements comprehensive error handling and validation:

```mermaid
graph TD
    A[Function Input] --> B{Validation Check}
    B -->|Valid| C[Process Input]
    B -->|Invalid| D[Error Handling]
    
    C --> E[Try Block]
    E --> F{Success?}
    F -->|Yes| G[Return Result]
    F -->|No| H[Catch Error]
    
    D --> I[Default Values]
    I --> G
    
    H --> J[Log Error]
    J --> K[Return Safe Value]
    
    subgraph "Error Types"
        L[Parse Errors]
        M[Type Errors]
        N[Range Errors]
        O[Security Errors]
    end
    
    L --> H
    M --> H
    N --> H
    O --> H
```

## Performance Optimizations

The module implements several performance optimizations:

1. **Memoization**: Text dimension calculations and label wrapping are memoized using lodash
2. **Lazy Loading**: D3 elements are created only when needed
3. **Caching**: Font dimension calculations are cached across multiple font families
4. **Batch Operations**: Multiple text operations are batched where possible

## Security Considerations

The utility-functions module implements several security measures:

1. **URL Sanitization**: All URLs are sanitized based on security configuration
2. **HTML Entity Encoding**: Custom entity encoding prevents XSS attacks
3. **Input Validation**: All user inputs are validated before processing
4. **Safe Defaults**: Functions return safe default values when inputs are invalid

## Usage Examples

### Text Dimension Calculation
```typescript
const dimensions = calculateTextDimensions('Sample Text', {
  fontSize: 14,
  fontFamily: 'Arial',
  fontWeight: 400
});
// Returns: { width: 85, height: 18, lineHeight: 18 }
```

### ID Generation
```typescript
const idGen = new InitIDGenerator(true, 'seed');
const id1 = idGen.next(); // Returns: 0
const id2 = idGen.next(); // Returns: 1
```

### Label Positioning
```typescript
const points = [{ x: 0, y: 0 }, { x: 100, y: 100 }];
const labelPos = calcLabelPosition(points);
// Returns: { x: 50, y: 50 }
```

## Integration with Other Modules

The utility-functions module serves as a foundation for other modules in the Mermaid ecosystem:

- **[Rendering Engine](rendering-engine.md)**: Uses text utilities and mathematical functions
- **[Diagram Plugins](diagram-plugin-api.md)**: Leverage ID generation and text processing
- **[Theme System](theme-system.md)**: Utilizes style parsing and configuration utilities
- **[Parser Engine](parser_engine.md)**: Depends on text validation and entity decoding

## Conclusion

The utility-functions module is a critical component that provides essential services to the entire Mermaid diagram rendering system. Its comprehensive set of utilities enables consistent text processing, secure operations, mathematical calculations, and efficient rendering across all diagram types. The module's design emphasizes reusability, performance, and security, making it an indispensable foundation for the Mermaid ecosystem.