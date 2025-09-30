# StrFormat Module Documentation

## Introduction

The StrFormat module provides a flexible and type-safe string formatting system for C++ applications. It implements a printf-style formatting mechanism with support for both positional arguments (`{n}`) and traditional printf-style format specifiers (`%d`, `%s`, etc.). The module is designed to handle various data types including integers, floating-point numbers, strings, and wide strings while providing compile-time type safety and runtime validation.

## Architecture Overview

The StrFormat module is built around two core components that work together to provide a complete formatting solution:

### Core Components

1. **Fmt** - The main formatting engine that parses format strings and evaluates them against provided arguments
2. **Inst** - Individual formatting instructions that represent parsed format specifiers

```mermaid
classDiagram
    class Fmt {
        -format: const char*
        -instructions[32]: Inst
        -nInst: int
        -currArgNo: int
        -currPercArgNo: int
        -res: str::Str
        -buf[256]: char
        -isOk: bool
        +Eval(args: const Arg**, nArgs: int): bool
    }
    
    class Inst {
        -t: Type
        -width: int
        -prec: int
        -fill: char
        -argNo: int
        -s: const char*
        -sLen: int
    }
    
    class Arg {
        +t: Type
        +u: union
    }
    
    Fmt "1" *-- "many" Inst : contains
    Fmt ..> Arg : uses
```

## Data Flow Architecture

The formatting process follows a clear two-phase approach:

```mermaid
flowchart TD
    A[Format String Input] --> B[ParseFormat Function]
    B --> C{Parsing Mode}
    C -->|Positional| D[parseArgDefPositional]
    C -->|Printf-style| E[parseArgDefPerc]
    C -->|Raw Text| F[addRawStr]
    
    D --> G[Inst Array]
    E --> G
    F --> G
    
    G --> H[Fmt Object]
    I[Arguments Array] --> H
    H --> J[Fmt.Eval Method]
    J --> K{Type Validation}
    K -->|Valid| L[Format Output]
    K -->|Invalid| M[Error Return]
    
    L --> N[Formatted String]
```

## Format String Parsing

The module supports two distinct format specification styles:

### Positional Format Specifiers
- Syntax: `{n}` where `n` is the argument index
- Example: `"Value: {0}, Count: {1}"`
- Allows reordering and reuse of arguments

### Printf-style Format Specifiers
- Syntax: `%[flags][width][.precision]type`
- Supported types: `c` (char), `d` (integer), `f` (float), `s` (string), `v` (any)
- Example: `"Name: %s, Age: %d, Score: %.2f"`

```mermaid
stateDiagram-v2
    [*] --> Scanning
    Scanning --> Escaped: Backslash \
    Escaped --> Scanning: Skip next char
    
    Scanning --> Positional: {
    Positional --> Scanning: parseArgDefPositional
    
    Scanning --> Printf: %
    Printf --> Scanning: parseArgDefPerc
    
    Scanning --> RawText: Other characters
    RawText --> Scanning: addRawStr
    
    Scanning --> [*]: End of string
```

## Type System

The module implements a comprehensive type system that ensures type safety during formatting:

### Supported Types
- **Type::None**: Empty/unused argument
- **Type::Char**: Single character
- **Type::Int**: Integer values
- **Type::Float**: Single-precision floating point
- **Type::Double**: Double-precision floating point
- **Type::Str**: C-style string (const char*)
- **Type::WStr**: Wide string (const WCHAR*)
- **Type::Any**: Generic type acceptance
- **Type::RawStr**: Literal string segments

### Type Validation Matrix

```mermaid
graph TD
    subgraph "Format Specifier Types"
        FS1[Type::Char]
        FS2[Type::Int]
        FS3[Type::Float]
        FS4[Type::Str]
        FS5[Type::Any]
    end
    
    subgraph "Argument Types"
        AT1[Type::Char]
        AT2[Type::Int]
        AT3[Type::Float]
        AT4[Type::Double]
        AT5[Type::Str]
        AT6[Type::WStr]
    end
    
    FS1 -.-> AT1
    FS2 -.-> AT2
    FS3 -.-> AT3
    FS3 -.-> AT4
    FS4 -.-> AT5
    FS4 -.-> AT6
    FS5 -.-> AT1
    FS5 -.-> AT2
    FS5 -.-> AT3
    FS5 -.-> AT4
    FS5 -.-> AT5
    FS5 -.-> AT6
```

## Component Interactions

The formatting system interacts with several utility modules:

```mermaid
sequenceDiagram
    participant Client
    participant Format
    participant ParseFormat
    participant Fmt.Eval
    participant str
    participant ToUtf8Temp
    
    Client->>Format: Format(string, args...)
    Format->>ParseFormat: Parse format string
    ParseFormat->>Format: Return Fmt object
    Format->>Fmt.Eval: Evaluate with arguments
    
    loop For each instruction
        Fmt.Eval->>str: BufFmt for numbers
        Fmt.Eval->>ToUtf8Temp: Convert WStr to UTF-8
        Fmt.Eval->>str::Str: Append formatted data
    end
    
    Fmt.Eval->>Format: Return result
    Format->>Client: Return formatted string
```

## Error Handling

The module implements comprehensive error handling at multiple levels:

1. **Parse-time validation**: Ensures format string syntax is correct
2. **Argument count validation**: Verifies all referenced arguments are provided
3. **Type compatibility validation**: Checks that argument types match format specifiers
4. **Buffer overflow protection**: Uses fixed-size buffers with bounds checking

## Performance Characteristics

- **Memory allocation**: Uses stack-allocated buffer (256 bytes) for temporary formatting
- **Instruction limit**: Supports up to 32 format instructions per format string
- **String building**: Efficient appending using str::Str for result construction
- **Type conversion**: Lazy conversion of wide strings to UTF-8 only when needed

## Integration with System

The StrFormat module serves as a foundational utility used throughout the application:

```mermaid
graph BT
    subgraph "StrFormat Module"
        SF[StrFormat]
    end
    
    subgraph "Dependent Modules"
        ENG[Engines]
        UI[UI Components]
        UTIL[Utils]
        DOC[Document Formats]
    end
    
    ENG -.->|String formatting| SF
    UI -.->|User messages| SF
    UTIL -.->|Diagnostic output| SF
    DOC -.->|Content processing| SF
```

## API Usage Patterns

The module provides multiple convenience functions for different use cases:

1. **Dynamic allocation**: `Format()` - Returns newly allocated string
2. **Temporary strings**: `FormatTemp()` - Returns temporary buffer (for immediate use)
3. **Variable arguments**: Overloaded functions supporting 1-6 arguments
4. **Array-based**: Direct argument array processing for advanced scenarios

## Thread Safety

- The formatting functions themselves are thread-safe
- Returned strings from `Format()` are owned by the caller
- `FormatTemp()` returns thread-local temporary storage
- No shared mutable state between concurrent formatting operations

This design makes the StrFormat module a robust, efficient, and type-safe solution for string formatting needs throughout the application.