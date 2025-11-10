# Parser Engine Module Documentation

## Introduction

The parser_engine module is a critical component of the Mermaid diagramming system that handles the parsing and validation of diagram syntax. Built on top of the Langium framework, it provides the foundation for converting textual diagram definitions into structured Abstract Syntax Trees (AST) that can be processed by other parts of the system. The module specializes in tokenization, value conversion, and diagram-specific validation rules.

## Architecture Overview

The parser_engine module serves as the linguistic foundation of the Mermaid system, positioned between the core API and individual diagram implementations. It provides abstract base classes and validation mechanisms that diagram-specific parsers extend and customize.

```mermaid
graph TB
    subgraph "Mermaid Core System"
        MC[mermaid_core_api]
        DP[diagram_plugin_api]
        RE[rendering_engine]
        PE[parser_engine]
        LE[layout_engine_elk]
    end
    
    subgraph "Diagram Implementations"
        DF[diagram_flowchart]
        DS[diagram_sequence]
        DC[diagram_class]
        DST[diagram_state]
        DER[diagram_er]
        DG[diagram_git]
        DPie[diagram_pie]
        DXY[diagram_xy_chart]
        DR[diagram_requirement]
        DM[diagram_mindmap]
        DA[diagram_architecture]
        DSan[diagram_sankey]
        DQ[diagram_quadrant_chart]
        DT[diagram_treemap]
    end
    
    MC --> PE
    PE --> DP
    DP --> DF
    DP --> DS
    DP --> DC
    DP --> DST
    DP --> DER
    DP --> DG
    DP --> DPie
    DP --> DXY
    DP --> DR
    DP --> DM
    DP --> DA
    DP --> DSan
    DP --> DQ
    DP --> DT
    
    PE -.-> RE
    RE -.-> LE
```

## Core Components

### AbstractMermaidTokenBuilder

**Location**: `packages.parser.src.language.common.tokenBuilder.AbstractMermaidTokenBuilder`

The AbstractMermaidTokenBuilder extends Langium's DefaultTokenBuilder to provide Mermaid-specific tokenization logic. It handles the creation of token types from grammar rules with special handling for keywords to ensure proper parsing constraints.

**Key Features:**
- Keyword restriction enforcement
- Custom regex pattern modification
- Integration with Langium's tokenization system

**Architecture:**
```mermaid
classDiagram
    class AbstractMermaidTokenBuilder {
        -keywords: Set<string>
        +constructor(keywords: string[])
        #buildKeywordTokens(rules, terminalTokens, options): TokenType[]
    }
    
    class DefaultTokenBuilder {
        <<Langium>>
        +buildKeywordTokens(rules, terminalTokens, options): TokenType[]
    }
    
    class CommonTokenBuilder {
        +CommonTokenBuilder()
    }
    
    DefaultTokenBuilder <|-- AbstractMermaidTokenBuilder
    AbstractMermaidTokenBuilder <|-- CommonTokenBuilder
```

**Process Flow:**
```mermaid
sequenceDiagram
    participant G as Grammar Rules
    participant A as AbstractMermaidTokenBuilder
    participant D as DefaultTokenBuilder
    participant T as TokenType Array
    
    G->>A: Stream of AbstractRule
    A->>D: super.buildKeywordTokens()
    D-->>A: Base TokenType[]
    A->>A: Apply keyword restrictions
    A->>T: Modified TokenType[]
    Note over A: Adds regex patterns to prevent<br/>non-whitespace after keywords
```

### AbstractMermaidValueConverter

**Location**: `packages.parser.src.language.common.valueConverter.AbstractMermaidValueConverter`

The AbstractMermaidValueConverter extends Langium's DefaultValueConverter to provide Mermaid-specific value conversion logic. It handles the conversion of parsed text values into appropriate JavaScript types, with special handling for titles and accessibility features.

**Key Features:**
- Title extraction and formatting
- Accessibility description handling
- Multi-line text processing
- Custom converter extensibility

**Architecture:**
```mermaid
classDiagram
    class AbstractMermaidValueConverter {
        #runCustomConverter(rule, input, cstNode): ValueType|undefined
        #runConverter(rule, input, cstNode): ValueType
        -runCommonConverter(rule, input, cstNode): ValueType|undefined
    }
    
    class DefaultValueConverter {
        <<Langium>>
        +runConverter(rule, input, cstNode): ValueType
    }
    
    class CommonValueConverter {
        #runCustomConverter(rule, input, cstNode): ValueType|undefined
    }
    
    DefaultValueConverter <|-- AbstractMermaidValueConverter
    AbstractMermaidValueConverter <|-- CommonValueConverter
```

**Value Conversion Process:**
```mermaid
flowchart TD
    Start([Input String]) --> RuleCheck{Rule Name Check}
    RuleCheck -->|Title/Acc Rules| RegexMatch[Apply Regex Matching]
    RuleCheck -->|Other Rules| CustomConverter[Run Custom Converter]
    RegexMatch --> SingleLine{Single Line?}
    SingleLine -->|Yes| TrimSingle[Trim & Normalize Spaces]
    SingleLine -->|No| ProcessMulti[Process Multi-line]
    ProcessMulti --> CleanMulti[Clean Indentation & Spacing]
    CustomConverter --> HasCustom{Custom Result?}
    HasCustom -->|No| DefaultConvert[Use Default Converter]
    HasCustom -->|Yes| UseCustom[Use Custom Result]
    TrimSingle --> ReturnValue([Return Value])
    CleanMulti --> ReturnValue
    DefaultConvert --> ReturnValue
    UseCustom --> ReturnValue
```

### TreemapValidator

**Location**: `packages.parser.src.language.treemap.treemap-validator.TreemapValidator`

The TreemapValidator provides diagram-specific validation for treemap diagrams, ensuring structural correctness. It validates that treemap diagrams contain only one root node, which is essential for proper hierarchical rendering.

**Key Features:**
- Single root node validation
- Indentation-based hierarchy checking
- Error reporting with precise location information

**Validation Process:**
```mermaid
flowchart TD
    Start([Treemap Document]) --> IterateRows[Iterate TreemapRows]
    IterateRows --> CheckItem{Has Item?}
    CheckItem -->|No| NextRow[Continue to Next Row]
    CheckItem -->|Yes| CheckIndent{Has Indentation?}
    CheckIndent -->|No| CheckRoot{Root Already Found?}
    CheckRoot -->|No| SetRoot[Set as Root Node]
    CheckRoot -->|Yes| ErrorMultiRoot[Error: Multiple Roots]
    CheckIndent -->|Yes| CheckIndentLevel{Valid Indent Level?}
    CheckIndentLevel -->|No| ErrorInvalid[Error: Invalid Hierarchy]
    CheckIndentLevel -->|Yes| ValidNode[Valid Node]
    SetRoot --> NextRow
    ValidNode --> NextRow
    ErrorMultiRoot --> NextRow
    ErrorInvalid --> NextRow
    NextRow --> MoreRows{More Rows?}
    MoreRows -->|Yes| CheckItem
    MoreRows -->|No| End([Validation Complete])
```

## Module Dependencies

The parser_engine module has specific dependencies and relationships with other system components:

```mermaid
graph LR
    subgraph "External Dependencies"
        L[Langium Framework]
        C[Chevrotain]
    end
    
    subgraph "Internal Dependencies"
        MC[mermaid_core_api]
        DP[diagram_plugin_api]
    end
    
    subgraph "parser_engine Components"
        ATB[AbstractMermaidTokenBuilder]
        AVC[AbstractMermaidValueConverter]
        TV[TreemapValidator]
    end
    
    L --> ATB
    L --> AVC
    C --> ATB
    
    ATB -.-> DP
    AVC -.-> DP
    TV -.-> MC
```

## Integration with Diagram Types

The parser_engine provides the foundation for all diagram-specific parsers. Each diagram type extends the abstract base classes to implement custom parsing logic:

```mermaid
graph TD
    subgraph "Parser Engine Foundation"
        ATB[AbstractMermaidTokenBuilder]
        AVC[AbstractMermaidValueConverter]
    end
    
    subgraph "Diagram-Specific Extensions"
        FBP[Flowchart Parser]
        SP[Sequence Parser]
        CP[Class Parser]
        STP[State Parser]
        EPP[ER Parser]
        GGP[Git Parser]
        PPP[Pie Parser]
        XYP[XYChart Parser]
        RP[Requirement Parser]
        MP[Mindmap Parser]
        AP[Architecture Parser]
        SAP[Sankey Parser]
        QCP[Quadrant Parser]
        TMP[Treemap Parser]
    end
    
    ATB -.-> FBP
    ATB -.-> SP
    ATB -.-> CP
    ATB -.-> STP
    ATB -.-> EPP
    ATB -.-> GGP
    ATB -.-> PPP
    ATB -.-> XYP
    ATB -.-> RP
    ATB -.-> MP
    ATB -.-> AP
    ATB -.-> SAP
    ATB -.-> QCP
    ATB -.-> TMP
    
    AVC -.-> FBP
    AVC -.-> SP
    AVC -.-> CP
    AVC -.-> STP
    AVC -.-> EPP
    AVC -.-> GGP
    AVC -.-> PPP
    AVC -.-> XYP
    AVC -.-> RP
    AVC -.-> MP
    AVC -.-> AP
    AVC -.-> SAP
    AVC -.-> QCP
    AVC -.-> TMP
```

## Data Flow

The parser_engine module processes diagram text through a structured pipeline:

```mermaid
sequenceDiagram
    participant Input as Diagram Text
    participant TB as TokenBuilder
    participant VC as ValueConverter
    participant V as Validator
    participant AST as Abstract Syntax Tree
    
    Input->>TB: Raw Text
    TB->>TB: Tokenize with Keywords
    TB->>TB: Apply Restrictions
    TB->>VC: Token Stream
    VC->>VC: Convert Values
    VC->>VC: Extract Titles
    VC->>VC: Process Accessibility
    VC->>V: Converted AST
    V->>V: Validate Structure
    V->>V: Check Constraints
    V->>AST: Validated AST
    AST-->>Input: Structured Representation
```

## Configuration and Extensibility

The parser_engine module is designed for extensibility, allowing diagram types to customize parsing behavior:

### Token Builder Extension
```typescript
class CustomDiagramTokenBuilder extends AbstractMermaidTokenBuilder {
  constructor() {
    super(['customKeyword1', 'customKeyword2']);
  }
}
```

### Value Converter Extension
```typescript
class CustomDiagramValueConverter extends AbstractMermaidValueConverter {
  protected runCustomConverter(
    rule: GrammarAST.AbstractRule,
    input: string,
    cstNode: CstNode
  ): ValueType | undefined {
    // Custom conversion logic
    return undefined;
  }
}
```

### Validator Registration
```typescript
function registerCustomValidationChecks(services: CustomServices) {
  const validator = services.validation.CustomValidator;
  const registry = services.validation.ValidationRegistry;
  const checks: ValidationChecks<CustomAstType> = {
    CustomNode: validator.validateCustomNode.bind(validator),
  };
  registry.register(checks, validator);
}
```

## Error Handling

The parser_engine module implements comprehensive error handling at multiple levels:

```mermaid
flowchart TD
    Start([Parsing Start]) --> TokenError{Tokenization Error}
    TokenError -->|Keyword Issue| KeywordError[Report Keyword Error]
    TokenError -->|Pattern Issue| PatternError[Report Pattern Error]
    TokenError -->|None| ConvertError{Conversion Error}
    
    ConvertError -->|Value Converting| ValueError[Report Value Error]
    ConvertError -->|None| ValidateError{Validation Error}
    
    ValidateError -->|Structural| StructureError[Report Structure Error]
    ValidateError -->|Semantic| SemanticError[Report Semantic Error]
    ValidateError -->|None| Success([Parsing Success])
    
    KeywordError --> ErrorContext[Add Error Context]
    PatternError --> ErrorContext
    ValueError --> ErrorContext
    StructureError --> ErrorContext
    SemanticError --> ErrorContext
    
    ErrorContext --> UserFeedback[Provide User Feedback]
```

## Performance Considerations

The parser_engine module is optimized for performance through several mechanisms:

1. **Keyword Set Optimization**: Uses Set data structure for O(1) keyword lookup
2. **Regex Caching**: Pre-compiled regex patterns for common conversions
3. **Stream Processing**: Leverages Langium's stream-based processing for memory efficiency
4. **Validation Short-circuiting**: Early termination on critical validation failures

## Testing Strategy

The parser_engine module follows a comprehensive testing approach:

- **Unit Tests**: Individual component testing for token builders and value converters
- **Integration Tests**: Cross-component interaction validation
- **Grammar Tests**: End-to-end parsing validation with sample diagrams
- **Performance Tests**: Parsing speed and memory usage benchmarks
- **Regression Tests**: Prevention of parsing behavior changes

## Related Documentation

For more information about related modules, see:

- [mermaid_core_api](mermaid_core_api.md) - Core API and diagram lifecycle management
- [diagram_plugin_api](diagram_plugin_api.md) - Diagram definition and plugin architecture
- [rendering_engine](rendering_engine.md) - Diagram rendering and visualization
- Individual diagram type documentations for specific parsing implementations

## Summary

The parser_engine module provides the linguistic foundation for the Mermaid diagramming system. Through its abstract base classes and validation framework, it enables consistent and reliable parsing across all diagram types while allowing for diagram-specific customization. The module's design emphasizes extensibility, performance, and maintainability, making it a robust foundation for the entire Mermaid ecosystem.