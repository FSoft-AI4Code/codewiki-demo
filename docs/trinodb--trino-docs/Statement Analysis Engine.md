# Statement Analysis Engine

## Introduction

The Statement Analysis Engine is a core component of Trino's SQL processing pipeline responsible for analyzing and validating SQL statements. It serves as the semantic analysis layer that transforms parsed SQL statements into analyzed query representations, performing crucial validation, type checking, and metadata resolution tasks.

## Overview

The Statement Analysis Engine operates as the bridge between the SQL Parser and the Query Planner, taking abstract syntax trees (AST) and enriching them with semantic information. It validates SQL statements against the database schema, resolves references, checks permissions, and prepares statements for optimization and execution.

## Architecture

### Core Components

```mermaid
graph TB
    subgraph "Statement Analysis Engine"
        SA[StatementAnalyzer]
        VA[Visitor Pattern]
        AN[Analysis Context]
        SC[Scope Management]
        EX[Expression Analysis]
    end
    
    subgraph "External Dependencies"
        SP[SQL Parser]
        MD[Metadata Manager]
        AC[Access Control]
        PM[Property Managers]
    end
    
    SP --> SA
    SA --> VA
    VA --> AN
    VA --> SC
    VA --> EX
    
    MD --> SA
    AC --> SA
    PM --> SA
    
    SA --> QP[Query Planner]
```

### Component Relationships

```mermaid
graph LR
    subgraph "Analysis Components"
        SA[StatementAnalyzer.Visitor]
        EA[ExpressionAnalyzer]
        AA[AggregationAnalyzer]
        WA[WindowAnalyzer]
        PA[PatternRecognitionAnalyzer]
    end
    
    SA --> EA
    SA --> AA
    SA --> WA
    SA --> PA
    
    subgraph "Data Structures"
        AN[Analysis]
        SC[Scope]
        RT[RelationType]
        FI[Field]
    end
    
    SA --> AN
    SA --> SC
    SC --> RT
    RT --> FI
```

## Core Functionality

### Statement Analysis Process

```mermaid
sequenceDiagram
    participant Client
    participant Parser
    participant StatementAnalyzer
    participant Metadata
    participant AccessControl
    participant Analysis
    
    Client->>Parser: Submit SQL Statement
    Parser->>Parser: Parse to AST
    Parser->>StatementAnalyzer: AST Node
    StatementAnalyzer->>Metadata: Request Schema Info
    Metadata-->>StatementAnalyzer: Schema Metadata
    StatementAnalyzer->>AccessControl: Check Permissions
    AccessControl-->>StatementAnalyzer: Permission Result
    StatementAnalyzer->>Analysis: Store Analysis Results
    StatementAnalyzer->>Client: Return Analysis
```

### Visitor Pattern Implementation

The Statement Analysis Engine employs the visitor pattern to traverse and analyze different types of SQL statements:

```mermaid
graph TD
    V[Visitor] --> QS[visitQuerySpecification]
    V --> I[visitInsert]
    V --> U[visitUpdate]
    V --> D[visitDelete]
    V --> CT[visitCreateTable]
    V --> CV[visitCreateView]
    V --> J[visitJoin]
    V --> T[visitTable]
    V --> ST[visitSetOperation]
    
    QS --> SEL[analyzeSelect]
    QS --> FROM[analyzeFrom]
    QS --> WHERE[analyzeWhere]
    QS --> GROUP[analyzeGroupBy]
    QS --> HAVING[analyzeHaving]
    QS --> ORDER[analyzeOrderBy]
```

## Key Features

### 1. Semantic Validation

- **Schema Resolution**: Validates table and column existence
- **Type Checking**: Ensures type compatibility in expressions
- **Reference Resolution**: Resolves table and column references
- **Function Validation**: Validates function calls and signatures

### 2. Security Integration

- **Access Control**: Integrates with Trino's security framework
- **Row-Level Security**: Applies row filters and column masks
- **Permission Checking**: Validates user permissions for operations

### 3. Query Analysis

- **Aggregation Analysis**: Validates GROUP BY and HAVING clauses
- **Window Function Analysis**: Analyzes window specifications
- **Subquery Analysis**: Handles correlated and uncorrelated subqueries
- **Join Analysis**: Validates join conditions and types

### 4. Metadata Management

- **Table Metadata**: Retrieves and validates table information
- **Column Metadata**: Handles column types and constraints
- **View Expansion**: Expands views and materialized views
- **Function Resolution**: Resolves function implementations

## Detailed Component Analysis

### StatementAnalyzer.Visitor

The core visitor class that implements the analysis logic for each SQL statement type:

```mermaid
classDiagram
    class Visitor {
        -outerQueryScope: Optional~Scope~
        -warningCollector: WarningCollector
        -updateKind: Optional~UpdateKind~
        -isTopLevel: boolean
        +process(Node, Optional~Scope~): Scope
        +visitQuerySpecification(QuerySpecification, Optional~Scope~): Scope
        +visitInsert(Insert, Optional~Scope~): Scope
        +visitUpdate(Update, Optional~Scope~): Scope
        +visitDelete(Delete, Optional~Scope~): Scope
        +visitTable(Table, Optional~Scope~): Scope
        +visitJoin(Join, Optional~Scope~): Scope
    }
```

### Scope Management

Manages variable and relation scoping during analysis:

```mermaid
graph LR
    subgraph "Scope Hierarchy"
        GS[Global Scope]
        QS[Query Scope]
        TS[Table Scope]
        FS[Field Scope]
    end
    
    GS --> QS
    QS --> TS
    TS --> FS
    
    subgraph "Scope Functions"
        CR[createScope]
        WR[withParent]
        RT[withRelationType]
        NR[withNamedQuery]
    end
    
    CR --> WR
    WR --> RT
    RT --> NR
```

### Analysis Context

Stores analysis results and intermediate state:

```mermaid
graph TB
    AN[Analysis]
    
    subgraph "Analysis Components"
        AN --> SC[Scope Information]
        AN --> TY[Type Information]
        AN --> EX[Expression Analysis]
        AN --> SU[Subquery Analysis]
        AN --> AG[Aggregation Analysis]
        AN --> WI[Window Analysis]
    end
    
    subgraph "Access Control"
        AN --> RF[Row Filters]
        AN --> CM[Column Masks]
        AN --> CC[Check Constraints]
        AN --> TC[Table Column References]
    end
```

## Data Flow

### Analysis Data Flow

```mermaid
graph LR
    subgraph "Input"
        AST[AST Node]
        SES[Session Context]
        PAR[Parameters]
    end
    
    subgraph "Processing"
        VAL[Validation]
        RES[Resolution]
        TYP[Type Inference]
        SEC[Security Checks]
    end
    
    subgraph "Output"
        ANA[Analysis Object]
        SCO[Scope Information]
        ERR[Error Messages]
        WAR[Warnings]
    end
    
    AST --> VAL
    SES --> VAL
    PAR --> VAL
    
    VAL --> RES
    RES --> TYP
    TYP --> SEC
    
    SEC --> ANA
    SEC --> SCO
    VAL --> ERR
    VAL --> WAR
```

### Expression Analysis Flow

```mermaid
sequenceDiagram
    participant Visitor
    participant ExpressionAnalyzer
    participant TypeResolver
    participant FunctionResolver
    participant SecurityChecker
    
    Visitor->>ExpressionAnalyzer: Analyze Expression
    ExpressionAnalyzer->>TypeResolver: Resolve Types
    TypeResolver-->>ExpressionAnalyzer: Type Information
    ExpressionAnalyzer->>FunctionResolver: Resolve Functions
    FunctionResolver-->>ExpressionAnalyzer: Function Metadata
    ExpressionAnalyzer->>SecurityChecker: Check Access
    SecurityChecker-->>ExpressionAnalyzer: Access Result
    ExpressionAnalyzer-->>Visitor: Expression Analysis
```

## Integration Points

### With SQL Parser

- Receives parsed AST nodes from the SQL Parser
- Validates parser output for semantic correctness
- Handles parser errors and provides context

### With Metadata Manager

- Queries table and column metadata
- Resolves function implementations
- Validates schema objects
- Retrieves view definitions

### With Access Control

- Checks table and column access permissions
- Applies row-level security filters
- Validates function execution permissions
- Enforces column-level security

### With Query Planner

- Provides analyzed statements to the planner
- Supplies type information for optimization
- Passes security constraints
- Transfers scope and metadata information

## Error Handling

### Validation Errors

The Statement Analysis Engine handles various types of validation errors:

- **Schema Errors**: Table/column not found, invalid references
- **Type Errors**: Type mismatches, incompatible operations
- **Security Errors**: Access denied, insufficient permissions
- **Semantic Errors**: Invalid SQL constructs, constraint violations

### Error Context

Provides detailed error information including:

- Error location in the SQL statement
- Suggested corrections
- Related metadata information
- Security context details

## Performance Considerations

### Caching

- Caches metadata lookups to reduce database queries
- Reuses analysis results for similar statements
- Maintains scope information for efficient lookups

### Optimization

- Lazy evaluation of expensive operations
- Efficient scope resolution algorithms
- Optimized type checking procedures

## Security Features

### Row-Level Security

```mermaid
graph LR
    subgraph "Row Filter Application"
        RF[Row Filter Definition]
        AN[Analysis Engine]
        EX[Expression Analysis]
        AP[Applied Filter]
    end
    
    RF --> AN
    AN --> EX
    EX --> AP
```

### Column-Level Security

```mermaid
graph LR
    subgraph "Column Mask Application"
        CM[Column Mask Definition]
        AN[Analysis Engine]
        EX[Expression Analysis]
        AM[Applied Mask]
    end
    
    CM --> AN
    AN --> EX
    EX --> AM
```

## Advanced Features

### Recursive Query Analysis

Supports analysis of recursive WITH queries:

- Validates recursive query structure
- Ensures proper termination conditions
- Handles recursive references
- Validates type consistency

### Window Function Analysis

Comprehensive window function support:

- Window specification validation
- Frame boundary analysis
- Partition and order by validation
- Function-specific validation

### Pattern Recognition

Advanced pattern matching analysis:

- MATCH_RECOGNIZE clause analysis
- Pattern validation
- Measure expression analysis
- Partition and order by validation

## Testing and Validation

### Unit Testing

- Comprehensive test coverage for all statement types
- Edge case validation
- Error condition testing
- Performance benchmarking

### Integration Testing

- End-to-end query analysis testing
- Cross-component integration validation
- Security feature testing
- Performance validation

## References

- [SQL Parser & AST](SQL Parser & AST.md) - For AST structure and parsing details
- [SQL Analyzer, Planner & Optimizer](SQL Analyzer, Planner & Optimizer.md) - For overall analysis pipeline
- [Metadata & Connector Abstraction](Metadata & Connector Abstraction.md) - For metadata integration
- [Security Framework](Security Framework.md) - For security integration details

## Conclusion

The Statement Analysis Engine is a critical component that ensures SQL statements are semantically valid, secure, and ready for optimization and execution. Its comprehensive validation capabilities, security integration, and support for advanced SQL features make it essential for Trino's query processing pipeline.