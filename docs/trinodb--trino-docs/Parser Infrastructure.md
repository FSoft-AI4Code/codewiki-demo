# Parser Infrastructure Module

## Introduction

The Parser Infrastructure module is a critical component of Trino's SQL processing pipeline, responsible for initializing and managing the SQL parser components. It provides thread-safe initialization and caching mechanisms for the ANTLR-based SQL parser, ensuring efficient and reliable parsing of SQL statements across the system.

## Overview

The Parser Infrastructure module serves as the foundation for SQL parsing in Trino, providing:

- **Thread-safe parser initialization**: Ensures concurrent access to parser components without race conditions
- **ATN cache management**: Optimizes parser performance through intelligent caching of ATN (Augmented Transition Network) structures
- **Parser refresh capabilities**: Allows dynamic refresh of parser caches for runtime optimization
- **Integration point**: Connects the ANTLR-generated parser with Trino's parsing framework

## Architecture

### Core Components

#### RefreshableSqlBaseParserInitializer

The `RefreshableSqlBaseParserInitializer` is the primary component of this module, implementing a thread-safe initialization strategy for SQL parser components.

**Key Features:**
- Thread-safe implementation using `AtomicReference` for cache management
- BiConsumer interface for configuring both lexer and parser components
- Automatic cache refresh capability
- Integration with ANTLR-generated parser components

### Architecture Diagram

```mermaid
graph TB
    subgraph "Parser Infrastructure Module"
        RSPI[RefreshableSqlBaseParserInitializer]
        APC[SqlBaseParserAndLexerATNCaches]
        ALCF[AntlrATNCacheFields - Lexer]
        APCF[AntlrATNCacheFields - Parser]
        
        RSPI --> APC
        APC --> ALCF
        APC --> APCF
    end
    
    subgraph "ANTLR Components"
        SBL[SqlBaseLexer]
        SBP[SqlBaseParser]
    end
    
    subgraph "SQL Parser Module"
        SPI[SqlParser]
        SPE[SqlParserErrorHandler]
    end
    
    RSPI -.->|configure| SBL
    RSPI -.->|configure| SBP
    SBP --> SPI
    SPI --> SPE
    
    style RSPI fill:#e1f5fe
    style APC fill:#fff3e0
    style SBL fill:#f3e5f5
    style SBP fill:#f3e5f5
```

## Component Details

### RefreshableSqlBaseParserInitializer

```java
@ThreadSafe
public final class RefreshableSqlBaseParserInitializer
        implements BiConsumer<SqlBaseLexer, SqlBaseParser>
```

**Responsibilities:**
- Initialize and manage parser ATN caches
- Provide thread-safe access to parser configuration
- Enable runtime refresh of parser caches
- Configure both lexer and parser components atomically

**Key Methods:**
- `refresh()`: Refreshes the internal caches with new ATN configurations
- `accept(SqlBaseLexer, SqlBaseParser)`: Configures provided lexer and parser instances

### Cache Management

The module uses a nested static class `SqlBaseParserAndLexerATNCaches` to manage separate caches for lexer and parser ATN structures:

```java
private static final class SqlBaseParserAndLexerATNCaches
{
    public final AntlrATNCacheFields lexer = new AntlrATNCacheFields(SqlBaseLexer._ATN);
    public final AntlrATNCacheFields parser = new AntlrATNCacheFields(SqlBaseParser._ATN);
}
```

## Data Flow

### Parser Initialization Flow

```mermaid
sequenceDiagram
    participant Client
    participant ParserInfrastructure
    participant ATNCache
    participant ANTLRParser
    participant SQLParser
    
    Client->>ParserInfrastructure: Create RefreshableSqlBaseParserInitializer
    ParserInfrastructure->>ATNCache: Initialize caches
    ATNCache-->>ParserInfrastructure: Cache ready
    
    Client->>ParserInfrastructure: accept(lexer, parser)
    ParserInfrastructure->>ATNCache: Get current caches
    ATNCache->>ANTLRParser: Configure lexer
    ATNCache->>ANTLRParser: Configure parser
    ANTLRParser-->>SQLParser: Parser ready
    SQLParser-->>Client: Parsing available
```

### Cache Refresh Flow

```mermaid
sequenceDiagram
    participant Thread1
    participant Thread2
    participant ParserInfrastructure
    participant AtomicReference
    
    Thread1->>ParserInfrastructure: refresh()
    ParserInfrastructure->>AtomicReference: set(new caches)
    AtomicReference-->>ParserInfrastructure: Update complete
    
    Thread2->>ParserInfrastructure: accept(lexer, parser)
    ParserInfrastructure->>AtomicReference: get()
    AtomicReference-->>ParserInfrastructure: Return latest caches
    ParserInfrastructure-->>Thread2: Configure with latest
```

## Dependencies

### Internal Dependencies

The Parser Infrastructure module depends on several key components:

- **ANTLR Generated Classes**: `SqlBaseLexer` and `SqlBaseParser` from the grammar module
- **ATN Cache Fields**: `AntlrATNCacheFields` for managing parser state
- **Error Handling**: Integration with Trino's error handling framework

### External Dependencies

```mermaid
graph LR
    subgraph "Parser Infrastructure"
        PI[Parser Infrastructure]
    end
    
    subgraph "ANTLR Runtime"
        AR[ANTLR Runtime]
    end
    
    subgraph "SQL Parser Module"
        SPM[SQL Parser Module]
    end
    
    subgraph "Grammar Module"
        GM[Grammar Module]
    end
    
    PI -->|uses| AR
    PI -->|configures| SPM
    PI -->|depends on| GM
```

## Integration with SQL Parser Module

The Parser Infrastructure module integrates closely with the broader [SQL Parser & AST](SQL Parser & AST.md) module:

### Relationship with AST Node Hierarchy

The initialized parser components are used to generate AST nodes:

```mermaid
graph TD
    PI[Parser Infrastructure]
    ANTLR[ANTLR Parser]
    AST[AST Node Hierarchy]
    Node[Node Interface]
    Statement[Statement Nodes]
    Expression[Expression Nodes]
    Query[Query Nodes]
    
    PI -->|configure| ANTLR
    ANTLR -->|generate| AST
    AST -->|implements| Node
    AST -->|creates| Statement
    AST -->|creates| Expression
    AST -->|creates| Query
```

### Integration with SQL Formatting

Parser infrastructure supports SQL formatting utilities:

```mermaid
graph LR
    PI[Parser Infrastructure]
    SP[SqlParser]
    SF[SqlFormatter]
    QU[QueryUtil]
    
    PI -->|initialize| SP
    SP -->|parse| SF
    SP -->|parse| QU
    SF -->|format| Output
    QU -->|build| Queries
```

## Performance Considerations

### Thread Safety

The module uses `AtomicReference` to ensure thread-safe access to parser caches:

- **Lock-free operations**: No synchronized blocks, reducing contention
- **Atomic updates**: Cache refreshes are atomic operations
- **Consistent state**: Readers always see a consistent cache state

### Memory Management

- **Lazy initialization**: Caches are created only when needed
- **Immutable caches**: Once created, cache contents are immutable
- **Garbage collection**: Old cache instances are eligible for GC after refresh

## Error Handling

The Parser Infrastructure module integrates with Trino's error handling framework:

- **Parser errors**: Delegated to [SqlParserErrorHandler](SQL Parser & AST.md)
- **Configuration errors**: Handled through Trino's exception framework
- **Runtime errors**: Managed by the calling parser components

## Testing and Validation

The module is designed for testability:

- **Unit tests**: Individual component testing
- **Integration tests**: Full parser initialization testing
- **Concurrency tests**: Multi-threaded access validation
- **Performance tests**: Cache performance benchmarking

## Future Enhancements

Potential improvements to the Parser Infrastructure module:

1. **Dynamic grammar loading**: Support for runtime grammar updates
2. **Cache statistics**: Expose cache hit/miss ratios
3. **Configurable cache sizes**: Allow tuning of cache parameters
4. **Multiple parser instances**: Support for different SQL dialects
5. **Hot reload**: Dynamic parser updates without restart

## Related Documentation

- [SQL Parser & AST](SQL Parser & AST.md) - The parent module containing AST nodes and SQL formatting
- [SQL Analyzer, Planner & Optimizer](SQL Analyzer, Planner & Optimizer.md) - Components that use the parsed SQL
- [Trino SPI](Trino SPI.md) - Service provider interface for plugins

## Conclusion

The Parser Infrastructure module provides a robust, thread-safe foundation for SQL parsing in Trino. Its design emphasizes performance, reliability, and maintainability, making it an essential component of Trino's query processing pipeline. The module's cache management and thread-safety features ensure that Trino can handle high-concurrency SQL parsing workloads efficiently.