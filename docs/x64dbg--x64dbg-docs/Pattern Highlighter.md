# Pattern Highlighter Module

## Introduction

The Pattern Highlighter module provides syntax highlighting capabilities for the Pattern Language used in the Hex Viewer component. It extends Qt's QSyntaxHighlighter to deliver real-time syntax coloring and formatting for pattern definition files, making code more readable and helping users identify syntax elements quickly.

## Architecture Overview

<use_mermaid>
graph TD
    subgraph "Pattern Highlighter Architecture"
        PH[PatternHighlighter]
        F[Format Helper Class]
        
        PH --> |"inherits from"| QSH[QSyntaxHighlighter]
        PH --> |"uses"| CE[CodeEditor Style]
        PH --> |"processes"| TD[QTextDocument]
        
        F --> |"configures"| TCF[QTextCharFormat]
        
        PH --> |"applies rules to"| HB[highlightBlock]
        HB --> |"matches"| RE[Regular Expressions]
        RE --> |"formats with"| TCF
    end
    
    subgraph "Highlighting Categories"
        K[Keywords]
        I[Instructions]
        O[Operators]
        C[Constants]
        FN[Functions]
        S[Strings]
        T[Types]
        CM[Comments]
    end
    
    PH --> K
    PH --> I
    PH --> O
    PH --> C
    PH --> FN
    PH --> S
    PH --> T
    PH --> CM
</use_mermaid>

## Core Components

### PatternHighlighter Class

The main class responsible for syntax highlighting implementation. It processes text blocks and applies formatting rules based on regular expression patterns.

**Key Features:**
- Real-time syntax highlighting during text editing
- Support for 23 language keywords
- Multiple syntax element categories with distinct styling
- Configurable color schemes through CodeEditor integration
- Multi-line comment support

**Constructor:**
```cpp
PatternHighlighter(const CodeEditor* style, QTextDocument* parent)
```

**Key Methods:**
- `refreshColors(const CodeEditor* style)` - Updates highlighting rules based on current color scheme
- `highlightBlock(const QString & text)` - Processes individual text blocks for syntax highlighting

### Format Helper Class

A fluent interface utility class that simplifies QTextCharFormat configuration:

```cpp
struct Format {
    Format && italic()
    Format && bold()
    Format && color(const QColor & color)
}
```

This helper enables method chaining for format configuration, making the highlighting rule setup more readable and maintainable.

## Syntax Categories and Rules

### 1. Keywords (23 total)
**Elements:** `struct`, `union`, `enum`, `bitfield`, `float`, `double`, `char`, `char16`, `bool`, `str`, `auto`, `namespace`, `using`, `fn`, `if`, `else`, `match`, `break`, `continue`, `try`, `catch`, `return`, `in`, `out`, `static`

**Styling:** Colored with keyword color, with special bracket formatting for `[[` and `]]`

### 2. Instructions (3 total)
**Elements:** `addressof`, `sizeof`, `import`

**Styling:** Bold text with instruction color

### 3. Operators
**Pattern:** `[+\-=^|&%*/<>]+` and `[\$\?:@~!]`

**Styling:** Operator color with special characters in bold

### 4. Constants
**Patterns:**
- Decimal numbers: `\b\d+\b`
- Hexadecimal numbers: `\b0x[0-9A-Fa-f]+\b`
- Boolean values: `\b(true|false)\b`

**Styling:** Constant color

### 5. Functions
**Pattern:** `\b[-a-zA-Z$._:][-a-zA-Z$._:0-9]*\w*(?=\()`

**Styling:** Bold text with function color

### 6. Strings
**Pattern:** `"(?:\\.|[^"\\])*"`

**Styling:** String color

### 7. Integer Types
**Pattern:** `\b[us]\d+\b`

**Styling:** Integer type color

### 8. Comments
**Line Comments:** `//.*$`
**Block Comments:** `\/\*[\s\S]*?\*\/`

**Styling:** Comment color

## Data Flow

<use_mermaid>
sequenceDiagram
    participant User
    participant QTextDocument
    participant PatternHighlighter
    participant CodeEditor
    participant HighlightingRules
    
    User->>QTextDocument: Edit text
    QTextDocument->>PatternHighlighter: Trigger highlightBlock()
    PatternHighlighter->>CodeEditor: Get style colors
    PatternHighlighter->>HighlightingRules: Apply regex patterns
    loop For each rule
        HighlightingRules->>PatternHighlighter: Return matches
        PatternHighlighter->>QTextDocument: Apply formatting
    end
    PatternHighlighter->>QTextDocument: Return formatted text
</use_mermaid>

## Integration with Pattern Language

The Pattern Highlighter works closely with the [Pattern Language](Pattern Language.md) module to provide syntax highlighting for pattern definition files. The highlighting rules are designed to match the syntax elements defined in the Pattern Language grammar.

### Relationship with PatternLanguage.ApiPatternVisitor

While the Pattern Highlighter focuses on syntax presentation, the ApiPatternVisitor in the Pattern Language module handles the semantic analysis and execution of pattern definitions. Both modules work together to provide a complete development experience:

- **Pattern Highlighter**: Visual feedback during code editing
- **ApiPatternVisitor**: Runtime pattern processing and data extraction

## Configuration and Styling

The module integrates with the CodeEditor's styling system, allowing users to customize colors for different syntax elements:

- `operatorColor` - Mathematical and logical operators
- `constantColor` - Numeric and boolean literals
- `keywordColor` - Language keywords
- `instructionColor` - Built-in instructions
- `functionColor` - Function names
- `stringColor` - String literals
- `integerTypeColor` - Integer type specifications
- `commentColor` - Comments

## Error Handling

The module includes validation for regular expressions:
```cpp
if(!highlightingRules.back().pattern.isValid())
{
    qFatal("Invalid regular expression");
}
```

This ensures that any invalid regex patterns are caught during development rather than causing runtime issues.

## Usage Context

The Pattern Highlighter is primarily used within the Hex Viewer component to provide syntax highlighting for pattern definition files. It's designed to work with the Pattern Language syntax, making it easier for users to write and debug complex data structure patterns used in binary analysis.

## Dependencies

- **Qt Framework**: QSyntaxHighlighter, QTextDocument, QRegularExpression
- **CodeEditor**: Provides styling and color configuration
- **Pattern Language**: Defines the syntax being highlighted

## Performance Considerations

The highlighting system processes text in blocks, which provides good performance for large files. Rules are applied in order, allowing later rules to override earlier ones, which enables fine-grained control over syntax presentation without significant performance overhead.