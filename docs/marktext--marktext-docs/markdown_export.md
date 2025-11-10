# Markdown Export Module Documentation

## Introduction

The Markdown Export module is a core component of the Muya Editor I/O system, responsible for converting the editor's internal block-based document structure into valid Markdown syntax. This module ensures that exported Markdown complies with multiple industry standards including CommonMark, GitHub Flavored Markdown (GFM), and Pandoc Markdown specifications.

## Overview

The `ExportMarkdown` class serves as the primary export engine that transforms rich text content from the Muya editor's internal representation into properly formatted Markdown text. It handles complex formatting scenarios including nested lists, tables, code blocks, mathematical expressions, and various container elements while maintaining compatibility with different Markdown flavors.

## Architecture

### Core Component Structure

```mermaid
classDiagram
    class ExportMarkdown {
        -blocks: Array
        -listType: Array
        -isLooseParentList: boolean
        -isGitlabCompatibilityEnabled: boolean
        -listIndentation: string
        -listIndentationCount: number
        +constructor(blocks, listIndentation, isGitlabCompatibilityEnabled)
        +generate()
        +translateBlocks2Markdown(blocks, indent, listIndent)
        +normalizeParagraphText(block, indent)
        +normalizeHeaderText(block, indent)
        +normalizeTable(table, indent)
        +normalizeListItem(block, indent)
        +normalizeCodeBlock(block, indent)
        +normalizeContainer(block, indent)
        +normalizeFootnote(block, indent)
        +insertLineBreak(result, indent)
    }
```

### Module Dependencies

```mermaid
graph TD
    A[ExportMarkdown] --> B[ContentState]
    A --> C[StateRender]
    A --> D[Block Structure]
    
    B -.-> E[Muya Editor Core]
    C -.-> E
    D -.-> E
    
    style A fill:#f9f,stroke:#333,stroke-width:4px
    style E fill:#bbf,stroke:#333,stroke-width:2px
```

## Component Details

### ExportMarkdown Class

The `ExportMarkdown` class is the main export engine that orchestrates the conversion process. It maintains state information about the current export context, including list types, indentation settings, and compatibility flags.

#### Key Properties

- **blocks**: The document structure represented as an array of block objects
- **listType**: Stack tracking nested list contexts (unordered/ordered)
- **isLooseParentList**: Flag indicating if the parent list is loose (has blank lines between items)
- **isGitlabCompatibilityEnabled**: Flag for GitLab-specific math block formatting
- **listIndentation**: Configuration for list indentation style ('dfm', 'number', or default)
- **listIndentationCount**: Numeric value for indentation spaces (1-4)

#### Constructor Parameters

```javascript
constructor(blocks, listIndentation = 1, isGitlabCompatibilityEnabled = false)
```

- **blocks**: Array of document block objects from the editor
- **listIndentation**: Indentation style configuration
- **isGitlabCompatibilityEnabled**: Enable GitLab math block compatibility

## Data Flow

### Export Process Flow

```mermaid
sequenceDiagram
    participant Editor as Muya Editor
    participant Export as ExportMarkdown
    participant Output as Markdown Output
    
    Editor->>Export: Initialize with blocks
    Export->>Export: translateBlocks2Markdown()
    loop For each block
        Export->>Export: Determine block type
        alt Paragraph
            Export->>Export: normalizeParagraphText()
        else Header
            Export->>Export: normalizeHeaderText()
        else List
            Export->>Export: normalizeListItem()
        else Table
            Export->>Export: normalizeTable()
        else Code Block
            Export->>Export: normalizeCodeBlock()
        else Container
            Export->>Export: normalizeContainer()
        end
        Export->>Export: Apply indentation
    end
    Export->>Output: Return formatted markdown
```

### Block Type Processing

```mermaid
flowchart TD
    A[Block Input] --> B{Block Type}
    B -->|p/span| C[Paragraph Processing]
    B -->|h1-h6| D[Header Processing]
    B -->|ul/ol| E[List Processing]
    B -->|li| F[List Item Processing]
    B -->|figure| G{Function Type}
    G -->|table| H[Table Processing]
    G -->|html| I[HTML Processing]
    G -->|code| J[Code Block Processing]
    G -->|math| K[Math Block Processing]
    G -->|container| L[Container Processing]
    B -->|pre| M[Frontmatter/Code Block]
    B -->|blockquote| N[Blockquote Processing]
    
    C --> O[Apply Indentation]
    D --> O
    E --> O
    F --> O
    H --> O
    I --> O
    J --> O
    K --> O
    L --> O
    M --> O
    N --> O
    
    O --> P[Output Markdown]
```

## Supported Markdown Elements

### Text Formatting

- **Paragraphs**: Basic text blocks with proper line breaks
- **Headers**: ATX style (#) and Setext style (underline) support
- **Blockquotes**: Nested blockquote support with proper indentation

### Lists

- **Unordered Lists**: Bullet marker customization (-, *, +)
- **Ordered Lists**: Numbered lists with custom delimiters
- **Task Lists**: Checkbox support for task items
- **Nested Lists**: Multi-level list support with configurable indentation
- **Loose/Tight Lists**: Proper spacing based on list item content

### Code Elements

- **Fenced Code Blocks**: Language-specific syntax highlighting
- **Indented Code Blocks**: Four-space indentation support
- **Frontmatter**: YAML, TOML, and JSON frontmatter support

### Tables

- **GitHub Flavored Tables**: Pipe-delimited table format
- **Column Alignment**: Left, center, right alignment support
- **Text Escaping**: Proper pipe character escaping

### Special Containers

- **Mathematical Expressions**: LaTeX math block support with GitLab compatibility
- **Diagrams**: Mermaid, Flowchart, Sequence, PlantUML, Vega-Lite support
- **HTML Blocks**: Raw HTML content preservation
- **Footnotes**: Reference-style footnote support

## Configuration Options

### List Indentation Styles

1. **Default**: Single space indentation
2. **Number**: Configurable 1-4 spaces
3. **DFM (Daring Fireball Markdown)**: 4-space indentation

### Compatibility Modes

- **GitLab Math**: Enables GitLab-style math block formatting (```math)
- **CommonMark**: Standard CommonMark compliance
- **GitHub Flavored Markdown**: GFM specification compliance

## Integration with Muya Editor

The ExportMarkdown module integrates with the broader Muya editor ecosystem:

```mermaid
graph LR
    A[ContentState] -->|provides blocks| B[ExportMarkdown]
    C[StateRender] -->|rendering context| B
    D[Selection] -->|cursor position| A
    E[History] -->|document state| A
    
    B -->|exports| F[Markdown File]
    B -->|feeds| G[Preview System]
    B -->|supports| H[Copy/Paste]
    
    style B fill:#f9f,stroke:#333,stroke-width:4px
```

## Usage Examples

### Basic Export

```javascript
const blocks = contentState.getBlocks()
const exporter = new ExportMarkdown(blocks, 2, false)
const markdown = exporter.generate()
```

### GitLab Compatibility

```javascript
const exporter = new ExportMarkdown(blocks, 'dfm', true)
const markdown = exporter.generate()
```

## Error Handling

The module includes basic error handling for unknown block types:

```javascript
default: {
  console.warn('translateBlocks2Markdown: Unknown block type:', block.type)
  break
}
```

## Standards Compliance

The module adheres to multiple Markdown specifications:

- **CommonMark Spec 0.29**: Base Markdown standard
- **GitHub Flavored Markdown**: Extended syntax support
- **Pandoc Markdown**: Additional formatting options

## Related Documentation

- [Muya Editor Core](muya_editor_core.md) - Core editor functionality
- [ContentState Management](contentstate_management.md) - Document state handling
- [StateRender System](staterender_system.md) - Rendering engine
- [HTML Export](html_export.md) - HTML export functionality

## Performance Considerations

The export process is optimized for:

- **Memory Efficiency**: Streaming block processing
- **Indentation Management**: Minimal string operations
- **List State Tracking**: Efficient stack-based list context management
- **Text Escaping**: Targeted escaping only when necessary

## Future Enhancements

Potential areas for improvement:

- **Plugin Architecture**: Extensible block type support
- **Custom Renderers**: User-defined formatting rules
- **Performance Metrics**: Export timing and optimization
- **Validation**: Output validation against Markdown specifications