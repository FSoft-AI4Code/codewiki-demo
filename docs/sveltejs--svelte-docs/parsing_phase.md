# Parsing Phase Module

The parsing phase is the first critical stage in the Svelte compilation pipeline, responsible for transforming raw Svelte template strings into structured Abstract Syntax Trees (AST). This module provides the foundational parsing capabilities that enable all subsequent compilation phases.

## Overview

The parsing phase takes Svelte component source code and converts it into a structured AST representation that can be analyzed and transformed by later compilation phases. It handles the complex task of parsing mixed HTML, JavaScript, CSS, and Svelte-specific syntax into a unified tree structure.

## Architecture

```mermaid
graph TB
    subgraph "Parsing Phase"
        Parser[Parser Class]
        ParseFunc[parse Function]
        States[Parser States]
        Utils[Parsing Utils]
    end
    
    subgraph "Input"
        Template[Template String]
        Options[Parse Options]
    end
    
    subgraph "Output"
        Root[AST Root Node]
        Fragment[Fragment Nodes]
        Metadata[Parse Metadata]
    end
    
    subgraph "Dependencies"
        Acorn[Acorn Parser]
        Errors[Error System]
        Patterns[Regex Patterns]
    end
    
    Template --> Parser
    Options --> Parser
    Parser --> Root
    Parser --> Fragment
    Parser --> Metadata
    
    Parser -.-> Acorn
    Parser -.-> Errors
    Parser -.-> Patterns
    
    Root --> AnalysisPhase[Analysis Phase]
    
    classDef primary fill:#e1f5fe
    classDef secondary fill:#f3e5f5
    classDef output fill:#e8f5e8
    
    class Parser,ParseFunc primary
    class States,Utils secondary
    class Root,Fragment,Metadata output
```

## Core Components

### Parser Class

The `Parser` class is the central component that orchestrates the parsing process:

```mermaid
classDiagram
    class Parser {
        +string template
        +boolean loose
        +number index
        +boolean ts
        +AST.TemplateNode[] stack
        +AST.Fragment[] fragments
        +AST.Root root
        +Record~string,boolean~ meta_tags
        +LastAutoClosedTag last_auto_closed_tag
        
        +constructor(template, loose)
        +current() AST.TemplateNode
        +acorn_error(err) never
        +eat(str, required, required_in_loose) boolean
        +match(str) boolean
        +match_regex(pattern) string|null
        +allow_whitespace() void
        +read(pattern) string|null
        +read_identifier(allow_reserved) string|null
        +read_until(pattern) string
        +require_whitespace() void
        +pop() AST.TemplateNode
        +append(node) T
    }
    
    class AST_Root {
        +type: 'Root'
        +SvelteOptions|null options
        +Fragment fragment
        +CSS.StyleSheet|null css
        +Script|null instance
        +Script|null module
        +JSComment[] comments
        +metadata: object
    }
    
    class Fragment {
        +type: 'Fragment'
        +Array~TemplateNode~ nodes
        +metadata: FragmentMetadata
    }
    
    Parser --> AST_Root : creates
    AST_Root --> Fragment : contains
```

#### Key Properties

- **`template`**: The raw Svelte component source code
- **`loose`**: Enables loose parsing mode for error recovery
- **`index`**: Current parsing position in the template
- **`ts`**: TypeScript mode detection flag
- **`stack`**: Parsing context stack for nested elements
- **`fragments`**: Fragment stack for managing nested scopes
- **`root`**: The resulting AST root node

#### Core Methods

- **`eat(str, required, required_in_loose)`**: Consumes expected tokens
- **`match(str)`**: Tests for token presence without consuming
- **`read_identifier(allow_reserved)`**: Parses JavaScript identifiers
- **`read_until(pattern)`**: Reads content until pattern match
- **`append(node)`**: Adds nodes to current fragment

## Parsing Process Flow

```mermaid
flowchart TD
    Start([Start Parsing]) --> Init[Initialize Parser]
    Init --> DetectTS{Detect TypeScript?}
    DetectTS -->|Yes| SetTS[Set ts = true]
    DetectTS -->|No| SetJS[Set ts = false]
    SetTS --> CreateRoot[Create Root AST Node]
    SetJS --> CreateRoot
    
    CreateRoot --> InitStack[Initialize Stack & Fragments]
    InitStack --> ParseLoop{Parse Template Loop}
    
    ParseLoop --> CheckIndex{index < template.length?}
    CheckIndex -->|No| Finalize[Finalize Parsing]
    CheckIndex -->|Yes| GetState[Get Current Parser State]
    
    GetState --> ExecuteState[Execute Parser State]
    ExecuteState --> UpdateState[Update Parser State]
    UpdateState --> ParseLoop
    
    Finalize --> CheckStack{Stack Length > 1?}
    CheckStack -->|Yes| HandleUnclosed[Handle Unclosed Elements]
    CheckStack -->|No| ProcessOptions[Process Svelte Options]
    
    HandleUnclosed --> LooseMode{Loose Mode?}
    LooseMode -->|Yes| SetEnd[Set End Position]
    LooseMode -->|No| ThrowError[Throw Parse Error]
    SetEnd --> ProcessOptions
    ThrowError --> End([End with Error])
    
    ProcessOptions --> SetBounds[Set Root Start/End]
    SetBounds --> ReturnAST[Return AST Root]
    ReturnAST --> End([End Successfully])
    
    classDef process fill:#e3f2fd
    classDef decision fill:#fff3e0
    classDef error fill:#ffebee
    classDef success fill:#e8f5e8
    
    class Init,CreateRoot,InitStack,ExecuteState,UpdateState,HandleUnclosed,SetEnd,ProcessOptions,SetBounds,ReturnAST process
    class DetectTS,CheckIndex,CheckStack,LooseMode decision
    class ThrowError error
    class End success
```

## Parser States

The parser uses a state machine approach where different parsing states handle different contexts:

```mermaid
stateDiagram-v2
    [*] --> Fragment
    Fragment --> Element : tag_start
    Fragment --> Text : text content
    Fragment --> Expression : expression_start
    Fragment --> Comment : comment_start
    Fragment --> Block : block_start
    Fragment --> Script : script_tag
    Fragment --> StyleTag : style_tag
    Fragment --> Options : options_tag
    
    Element --> Attributes : parse attributes
    Element --> Children : parse children
    Children --> Fragment : nested content
    
    Expression --> JavaScript : parse JS expression
    JavaScript --> Fragment : return to template
    
    Block --> BlockContent : parse block body
    BlockContent --> Fragment : nested template
    
    Script --> JavaScript : parse script content
    StyleTag --> CSS : parse style content
    Options --> OptionsContent : parse options
    
    Attributes --> Fragment : complete element
    CSS --> Fragment : complete style
    OptionsContent --> Fragment : complete options
```

## TypeScript Detection

The parser automatically detects TypeScript mode by scanning for `<script lang="ts">` tags:

```mermaid
flowchart LR
    Template[Template String] --> Regex[Lang Attribute Regex]
    Regex --> Match{Match Found?}
    Match -->|No| JSMode[JavaScript Mode]
    Match -->|Yes| CheckLang{Check Language}
    CheckLang -->|No| JSMode
    CheckLang -->|Yes| TSMode[TypeScript Mode]
    
    JSMode --> SetFlag1[ts = false]
    TSMode --> SetFlag2[ts = true]
    
    SetFlag1 --> Continue[Continue Parsing]
    SetFlag2 --> Continue
    
    classDef mode fill:#e1f5fe
    classDef decision fill:#fff3e0
    
    class JSMode,TSMode mode
    class Match,CheckLang decision
```

## Error Handling

The parser provides comprehensive error handling with two modes:

### Strict Mode (default)
- Throws errors immediately on syntax violations
- Provides precise error locations and messages
- Ensures complete syntax compliance

### Loose Mode
- Attempts to continue parsing after errors
- Useful for IDE integration and partial parsing
- Provides best-effort AST construction

```mermaid
flowchart TD
    Error[Parse Error Detected] --> CheckMode{Loose Mode?}
    CheckMode -->|No| ThrowError[Throw Immediate Error]
    CheckMode -->|Yes| RecoverError[Attempt Error Recovery]
    
    RecoverError --> SetDefaults[Set Default Values]
    SetDefaults --> ContinueParsing[Continue Parsing]
    ContinueParsing --> MarkIncomplete[Mark AST as Incomplete]
    
    ThrowError --> StopParsing[Stop Parsing]
    MarkIncomplete --> PartialAST[Return Partial AST]
    StopParsing --> NoAST[No AST Returned]
    
    classDef error fill:#ffebee
    classDef recovery fill:#fff3e0
    classDef result fill:#e8f5e8
    
    class Error,ThrowError,StopParsing error
    class RecoverError,SetDefaults,ContinueParsing recovery
    class PartialAST,NoAST result
```

## Integration with Compilation Pipeline

The parsing phase serves as the foundation for the entire Svelte compilation process:

```mermaid
graph LR
    subgraph "Parsing Phase"
        Parser[Parser]
        AST[AST Root]
    end
    
    subgraph "Analysis Phase"
        Analyzer[Component Analyzer]
        Scope[Scope Analysis]
    end
    
    subgraph "Transform Phase"
        ClientTransform[Client Transform]
        ServerTransform[Server Transform]
    end
    
    Template[Template String] --> Parser
    Parser --> AST
    AST --> Analyzer
    AST --> Scope
    
    Analyzer --> ClientTransform
    Analyzer --> ServerTransform
    Scope --> ClientTransform
    Scope --> ServerTransform
    
    ClientTransform --> ClientCode[Client Code]
    ServerTransform --> ServerCode[Server Code]
    
    classDef phase fill:#e1f5fe
    classDef output fill:#e8f5e8
    
    class Parser,Analyzer,ClientTransform,ServerTransform phase
    class AST,ClientCode,ServerCode output
```

## AST Structure

The parser generates a hierarchical AST with the following key node types:

```mermaid
graph TD
    Root[Root Node] --> Fragment[Fragment]
    Root --> Options[Svelte Options]
    Root --> CSS[CSS StyleSheet]
    Root --> Instance[Instance Script]
    Root --> Module[Module Script]
    Root --> Comments[Comments]
    Root --> Metadata[Metadata]
    
    Fragment --> Elements[HTML Elements]
    Fragment --> Text[Text Nodes]
    Fragment --> Expressions[Expression Tags]
    Fragment --> Blocks[Control Blocks]
    Fragment --> Components[Component Tags]
    
    Elements --> Attributes[Attributes]
    Elements --> Directives[Directives]
    Elements --> Children[Child Nodes]
    
    Blocks --> IfBlock[If Blocks]
    Blocks --> EachBlock[Each Blocks]
    Blocks --> AwaitBlock[Await Blocks]
    Blocks --> KeyBlock[Key Blocks]
    Blocks --> SnippetBlock[Snippet Blocks]
    
    classDef root fill:#e1f5fe
    classDef container fill:#f3e5f5
    classDef content fill:#e8f5e8
    classDef control fill:#fff3e0
    
    class Root root
    class Fragment,Elements,Blocks container
    class Text,Expressions,Components,Attributes,Directives content
    class IfBlock,EachBlock,AwaitBlock,KeyBlock,SnippetBlock control
```

## Performance Considerations

The parser is optimized for performance through several strategies:

### Efficient String Operations
- Single-character matching optimization
- Minimal string slicing operations
- Regex pattern caching

### Memory Management
- Reusable parser state objects
- Minimal object allocation during parsing
- Efficient stack management

### Early Optimization
- TypeScript detection via single regex scan
- Whitespace handling optimization
- Pattern matching shortcuts

## Usage Examples

### Basic Parsing
```javascript
import { parse } from './phases/1-parse/index.js';

const template = `
<script>
  let count = 0;
</script>

<button on:click={() => count++}>
  Count: {count}
</button>
`;

const ast = parse(template);
console.log(ast.type); // 'Root'
console.log(ast.fragment.nodes.length); // Number of top-level nodes
```

### Loose Mode Parsing
```javascript
const incompleteTemplate = `
<div>
  <p>Unclosed paragraph
  <span>Some content
`;

const ast = parse(incompleteTemplate, true); // loose = true
// Returns partial AST instead of throwing error
```

## Related Documentation

- [Analysis Phase](analysis_phase.md) - Next phase that processes the parsed AST
- [Compiler Types](compiler_types.md) - Type definitions for AST nodes
- [Transform Phase](transform_phase.md) - Final compilation phase
- [Preprocessor](preprocessor.md) - Pre-parsing template transformation

## API Reference

### `parse(template, loose?)`
Main parsing function that creates a Parser instance and returns the AST.

**Parameters:**
- `template` (string): The Svelte component source code
- `loose` (boolean, optional): Enable loose parsing mode

**Returns:** `AST.Root` - The parsed AST root node

### `Parser` Class
Core parser implementation with methods for tokenization, state management, and AST construction.

**Constructor:**
- `new Parser(template, loose)` - Creates a new parser instance

**Key Methods:**
- `current()` - Returns the current parsing context
- `eat(str, required?, required_in_loose?)` - Consumes expected tokens
- `match(str)` - Tests for token presence
- `read_identifier(allow_reserved?)` - Parses JavaScript identifiers
- `append(node)` - Adds nodes to the current fragment

The parsing phase establishes the foundation for Svelte's compilation pipeline, transforming raw template strings into structured ASTs that enable powerful static analysis and optimization in subsequent phases.