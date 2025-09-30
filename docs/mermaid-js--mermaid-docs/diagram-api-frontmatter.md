# diagram-api-frontmatter Module Documentation

## Introduction

The `diagram-api-frontmatter` module is a specialized component within the Mermaid diagramming library that handles YAML frontmatter parsing and extraction from diagram definitions. This module provides the functionality to parse metadata embedded at the beginning of Mermaid diagrams, allowing users to specify configuration options, titles, and display modes that affect how diagrams are rendered.

Frontmatter is a common pattern in markup languages where metadata is placed at the beginning of a document, typically separated from the main content by delimiters. In Mermaid, this allows users to configure diagram behavior and appearance without modifying the core diagram syntax.

## Architecture Overview

### Module Position in System Architecture

The `diagram-api-frontmatter` module sits at the intersection of diagram parsing and configuration management within the Mermaid ecosystem. It acts as a preprocessing layer that extracts metadata before the main diagram content is parsed and rendered.

```mermaid
graph TB
    subgraph "Mermaid Core System"
        A["Diagram Input Text"] --> B["diagram-api-frontmatter"]
        B --> C["Extracted Content"]
        B --> D["FrontMatter Metadata"]
        C --> E["Diagram Parser"]
        D --> F["Configuration Manager"]
        F --> G["Diagram Renderer"]
        E --> G
        
        subgraph "diagram-api-frontmatter Components"
            B1["extractFrontMatter Function"]
            B2["FrontMatterMetadata Interface"]
            B3["FrontMatterResult Interface"]
            B4["YAML Parser Integration"]
        end
        
        B --> B1
        B1 --> B2
        B1 --> B3
        B1 --> B4
    end
```

### Component Relationships

```mermaid
graph LR
    subgraph "External Dependencies"
        A["js-yaml Library"]
        B["config.type Module"]
        C["regexes Module"]
    end
    
    subgraph "diagram-api-frontmatter"
        D["FrontMatterMetadata"]
        E["FrontMatterResult"]
        F["extractFrontMatter"]
    end
    
    subgraph "Dependent Modules"
        G["diagram-api Module"]
        H["Core Mermaid Engine"]
    end
    
    A --> F
    B --> D
    C --> F
    F --> D
    F --> E
    D --> E
    E --> G
    G --> H
```

## Core Components

### FrontMatterMetadata Interface

The `FrontMatterMetadata` interface defines the structure of metadata that can be extracted from YAML frontmatter in Mermaid diagrams.

```typescript
interface FrontMatterMetadata {
  title?: string;
  displayMode?: GanttDiagramConfig['displayMode'];
  config?: MermaidConfig;
}
```

**Properties:**
- `title` (optional): A string that specifies the diagram title
- `displayMode` (optional): Controls display modes, currently used for compact mode in Gantt charts
- `config` (optional): Contains [MermaidConfig](config.md) settings that override default configuration

### FrontMatterResult Interface

The `FrontMatterResult` interface represents the output of the frontmatter extraction process.

```typescript
interface FrontMatterResult {
  text: string;
  metadata: FrontMatterMetadata;
}
```

**Properties:**
- `text`: The diagram content with frontmatter removed
- `metadata`: Parsed frontmatter data following the `FrontMatterMetadata` structure

### extractFrontMatter Function

The core function that processes diagram text to extract and parse YAML frontmatter.

```typescript
export function extractFrontMatter(text: string): FrontMatterResult
```

**Parameters:**
- `text`: The complete diagram text that may contain YAML frontmatter

**Returns:**
- `FrontMatterResult`: Object containing the cleaned text and parsed metadata

**Process Flow:**

```mermaid
sequenceDiagram
    participant User
    participant extractFrontMatter
    participant RegexMatcher
    participant YAMLParser
    participant Validator
    
    User->>extractFrontMatter: Input diagram text
    extractFrontMatter->>RegexMatcher: Match frontmatter pattern
    alt Frontmatter found
        RegexMatcher->>YAMLParser: Extract YAML content
        YAMLParser->>Validator: Parse with JSON schema
        Validator->>extractFrontMatter: Return parsed object
        extractFrontMatter->>extractFrontMatter: Filter supported properties
        extractFrontMatter->>User: Return result with metadata
    else No frontmatter
        RegexMatcher->>extractFrontMatter: Return null
        extractFrontMatter->>User: Return text with empty metadata
    end
```

## Data Flow

### Frontmatter Processing Pipeline

```mermaid
flowchart TD
    A["Raw Diagram Text"] --> B{"Contains Frontmatter?"}
    B -->|Yes| C["Extract YAML Block"]
    B -->|No| D["Return Original Text"]
    
    C --> E["Parse YAML with js-yaml"]
    E --> F["Validate Object Structure"]
    F --> G["Filter Supported Properties"]
    G --> H["Create FrontMatterResult"]
    
    D --> I["Create Result with Empty Metadata"]
    
    H --> J["Return Processed Result"]
    I --> J
    
    J --> K["Diagram Parser"]
    K --> L["Configuration Application"]
    L --> M["Diagram Rendering"]
```

### Configuration Integration

The extracted frontmatter metadata integrates with the broader configuration system:

```mermaid
graph TD
    A["FrontMatterMetadata.config"] --> B["Configuration Merger"]
    C["Default MermaidConfig"] --> B
    D["User-defined Config"] --> B
    
    B --> E["Merged Configuration"]
    E --> F["Diagram Renderer"]
    
    G["FrontMatterMetadata.title"] --> H["Title Display"]
    I["FrontMatterMetadata.displayMode"] --> J["Display Mode Selector"]
    
    F --> K["Final Diagram Output"]
    H --> K
    J --> K
```

## Integration Points

### Relationship with diagram-api Module

The `diagram-api-frontmatter` module is tightly integrated with the [diagram-api](diagram-api.md) module, which uses the frontmatter extraction as a preprocessing step before diagram parsing.

```mermaid
graph LR
    subgraph "diagram-api Processing Chain"
        A["Diagram Text Input"] --> B["diagram-api-frontmatter"]
        B --> C["Clean Text + Metadata"]
        C --> D["Diagram Parser"]
        D --> E["AST Generation"]
        E --> F["Renderer"]
    end
    
    subgraph "Metadata Flow"
        G["FrontMatterResult.metadata"] --> H["Configuration System"]
        H --> I["Renderer Settings"]
        I --> F
    end
```

### Configuration System Integration

The module interfaces with the [config](config.md) module to provide type-safe configuration options:

- `MermaidConfig`: Base configuration interface for all Mermaid settings
- `GanttDiagramConfig`: Specific configuration for Gantt chart display modes
- Type safety ensures only valid configuration options are accepted

## Usage Patterns

### Basic Frontmatter Structure

```yaml
---
title: My Diagram Title
config:
  theme: dark
  fontFamily: Arial
displayMode: compact
---
graph TD
    A[Start] --> B[End]
```

### Processing Example

```mermaid
sequenceDiagram
    participant Developer
    participant Mermaid
    participant FrontmatterModule
    
    Developer->>Mermaid: Provide diagram with frontmatter
    Mermaid->>FrontmatterModule: Call extractFrontMatter
    FrontmatterModule->>FrontmatterModule: Parse YAML metadata
    FrontmatterModule->>Mermaid: Return cleaned text + config
    Mermaid->>Mermaid: Apply configuration
    Mermaid->>Developer: Render diagram with settings
```

## Error Handling and Validation

### YAML Parsing Safety

The module implements several safety measures:

1. **Schema Validation**: Uses JSON_SCHEMA to ensure predictable parsing
2. **Type Checking**: Validates that parsed data is an object (not array or primitive)
3. **Property Filtering**: Only extracts explicitly supported properties
4. **Graceful Degradation**: Returns empty metadata if parsing fails

### Runtime Type Safety

```typescript
// Ensure parsed data is a valid object
parsed = typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};

// Only add properties that are explicitly supported
if (parsed.displayMode) {
  metadata.displayMode = parsed.displayMode.toString() as GanttDiagramConfig['displayMode'];
}
```

## Dependencies

### External Libraries

- **js-yaml**: YAML parsing library for extracting metadata from frontmatter blocks
- Uses JSON_SCHEMA for predictable parsing behavior

### Internal Dependencies

- **config.type**: Provides type definitions for configuration objects
- **regexes**: Contains the `frontMatterRegex` pattern for identifying frontmatter blocks

### Dependent Modules

- **diagram-api**: Uses frontmatter extraction for preprocessing diagram text
- **Core Mermaid Engine**: Integrates frontmatter metadata into the rendering pipeline

## Extension Points

### Adding New Metadata Properties

To extend the frontmatter capabilities:

1. Update the `FrontMatterMetadata` interface with new optional properties
2. Add validation logic in the `extractFrontMatter` function
3. Ensure new properties integrate with relevant configuration systems

### Custom YAML Schemas

The module can be extended to support custom YAML schemas beyond JSON_SCHEMA for specialized use cases.

## Best Practices

### For Developers

1. **Always validate** frontmatter structure before using metadata
2. **Use type guards** when accessing optional properties
3. **Document supported** frontmatter options for your diagrams
4. **Handle gracefully** when frontmatter is missing or invalid

### For Users

1. **Keep frontmatter minimal** - only include necessary configuration
2. **Use consistent formatting** for better maintainability
3. **Test configurations** across different diagram types
4. **Document custom settings** for team collaboration

## Performance Considerations

The frontmatter extraction process is designed to be lightweight:

- **Regex matching** is fast and only processes the beginning of the text
- **YAML parsing** only occurs when frontmatter is detected
- **Property filtering** prevents unnecessary data processing
- **Early returns** minimize processing for diagrams without frontmatter

This ensures minimal impact on diagram rendering performance, especially for large diagrams or batch processing scenarios.