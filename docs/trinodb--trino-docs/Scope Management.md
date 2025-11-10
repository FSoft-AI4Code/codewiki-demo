# Scope Management Module

## Introduction

The Scope Management module is a critical component of Trino's SQL Analyzer that manages the visibility and resolution of identifiers (tables, columns, expressions) during query analysis. It provides a hierarchical scoping mechanism that enables proper name resolution across different query contexts, including subqueries, joins, and nested expressions. The module ensures that SQL identifiers are correctly resolved according to SQL standard rules while maintaining proper isolation between different query scopes.

## Core Functionality

The Scope Management module provides:

- **Hierarchical Scope Resolution**: Manages nested scopes with parent-child relationships
- **Identifier Resolution**: Resolves table and column references within query contexts
- **Field Resolution**: Maps expressions to specific fields in relations
- **Named Query Management**: Handles CTE (Common Table Expression) references
- **Asterisk Resolution**: Resolves wildcard selections (`SELECT *`) with proper context
- **Scope Boundary Management**: Enforces query boundaries for proper isolation

## Architecture

### Core Components

```mermaid
classDiagram
    class Scope {
        -Optional<Scope> parent
        -boolean queryBoundary
        -RelationId relationId
        -RelationType relation
        -Map<String, WithQuery> namedQueries
        +create() Scope
        +builder() Builder
        +withRelationType(RelationType) Scope
        +getQueryBoundaryScope() Scope
        +getOuterQueryParent() Optional<Scope>
        +hasOuterParent(Scope) boolean
        +getLocalParent() Optional<Scope>
        +getLocalScopeFieldCount() int
        +getRelationId() RelationId
        +getRelationType() RelationType
        +resolveAsteriskedIdentifierChainBasis(QualifiedName, AllColumns) Optional<AsteriskedIdentifierChainBasis>
        +isLocalScope(Scope) boolean
        +resolveField(Expression, QualifiedName) ResolvedField
        +tryResolveField(Expression, QualifiedName) Optional<ResolvedField>
        +getField(int) ResolvedField
        +isColumnReference(QualifiedName) boolean
        +getNamedQuery(String) Optional<WithQuery>
    }

    class Builder {
        -RelationId relationId
        -RelationType relationType
        -Map<String, WithQuery> namedQueries
        -Optional<Scope> parent
        -boolean queryBoundary
        +like(Scope) Builder
        +withRelationType(RelationId, RelationType) Builder
        +withParent(Scope) Builder
        +withOuterQueryParent(Scope) Builder
        +withNamedQuery(String, WithQuery) Builder
        +containsNamedQuery(String) boolean
        +build() Scope
    }

    class AsteriskedIdentifierChainBasis {
        -BasisType basisType
        -Optional<Scope> scope
        -Optional<RelationType> relationType
        +getBasisType() BasisType
        +getScope() Optional<Scope>
        +getRelationType() Optional<RelationType>
    }

    class BasisType {
        <<enumeration>>
        TABLE
        FIELD
    }

    class ResolvedField {
        -Scope scope
        -Field field
        -int hierarchyFieldIndex
        -int relationFieldIndex
        -boolean local
    }

    class Field {
        -Optional<String> name
        -Type type
        -Optional<String> originalName
        -Optional<QualifiedName> relationAlias
        -boolean aliased
        -boolean hidden
        +matchesPrefix(Optional<QualifiedName>) boolean
    }

    class RelationType {
        -List<Field> fields
        +getAllFields() List<Field>
        +getFieldByIndex(int) Field
        +indexOf(Field) int
        +resolveFields(QualifiedName) List<Field>
    }

    Scope "1" --> "0..1" Scope : parent
    Scope "1" --> "1" RelationType : relation
    Scope "1" --> "*" AsteriskedIdentifierChainBasis : resolves
    Scope "1" --> "*" ResolvedField : contains
    Builder ..> Scope : creates
    AsteriskedIdentifierChainBasis --> BasisType : uses
    ResolvedField --> Field : references
    RelationType "1" --> "*" Field : contains
```

### Module Dependencies

```mermaid
graph TD
    SM[Scope Management] --> SPI[Trino SPI]
    SM --> AST[SQL Parser & AST]
    SM --> SA[SQL Analyzer]
    
    SPI --> Type[Type System]
    SPI --> Error[Error Handling]
    
    AST --> Tree[SQL Tree]
    AST --> Expression[Expression Types]
    
    SA --> Analysis[Analysis Framework]
    SA --> Semantic[Semantic Exceptions]
    
    subgraph "External Dependencies"
        Type
        Error
        Tree
        Expression
        Analysis
        Semantic
    end
    
    subgraph "Scope Management"
        Scope
        Builder
        Resolution
        Validation
    end
```

## Component Relationships

### Scope Hierarchy

```mermaid
graph TD
    subgraph "Query Structure"
        Q1[Main Query]
        SQ1[Subquery 1]
        SQ2[Subquery 2]
        SQ3[Nested Subquery]
        CTE1[CTE users]
        CTE2[CTE orders]
    end
    
    subgraph "Scope Hierarchy"
        S1[Main Scope<br/>Relation customers<br/>Fields id name email]
        S2[Subquery Scope 1<br/>Relation SELECT<br/>Parent Main]
        S3[Subquery Scope 2<br/>Relation SELECT<br/>Parent Main]
        S4[Nested Scope<br/>Relation SELECT<br/>Parent SQ2]
        S5[CTE Scope 1<br/>Named Query users<br/>Parent Main]
        S6[CTE Scope 2<br/>Named Query orders<br/>Parent Main]
    end
    
    Q1 --> S1
    SQ1 --> S2
    SQ2 --> S3
    SQ3 --> S4
    CTE1 --> S5
    CTE2 --> S6
    
    S1 -.-> S2
    S1 -.-> S3
    S3 -.-> S4
    S1 -.-> S5
    S1 -.-> S6
```

### Field Resolution Process

```mermaid
sequenceDiagram
    participant Analyzer
    participant Scope
    participant RelationType
    participant Field
    
    Analyzer->>Scope: resolveField(expression, name)
    Scope->>RelationType: resolveFields(name)
    RelationType->>Field: find matching fields
    Field-->>RelationType: return matches
    RelationType-->>Scope: return field list
    
    alt Multiple matches
        Scope-->>Analyzer: throw ambiguousAttributeException
    else Single match
        Scope->>Scope: calculate field indices
        Scope-->>Analyzer: return ResolvedField
    else No match in current scope
        Scope->>Scope: check parent scope
        alt Has parent
            Scope->>Scope: resolveField(parent, name)
        else No parent
            Scope-->>Analyzer: return Optional.empty()
        end
    end
```

## Data Flow

### Identifier Resolution Flow

```mermaid
flowchart TD
    Start([Identifier Reference]) --> Parse{Parse Identifier}
    Parse --> QualifiedName[Qualified Name]
    
    QualifiedName --> CheckLocal{Check Local Scope}
    CheckLocal -->|Found| CheckMultiple{Multiple Matches?}
    CheckMultiple -->|Yes| ErrorAmbiguous[Throw Ambiguous Exception]
    CheckMultiple -->|No| CreateResolved[Create ResolvedField]
    
    CheckLocal -->|Not Found| CheckParent{Has Parent Scope?}
    CheckParent -->|Yes| CheckParentScope[Check Parent Scope]
    CheckParentScope --> CheckLocal
    CheckParent -->|No| CheckOuter{Has Outer Query?}
    
    CheckOuter -->|Yes| CheckOuterScope[Check Outer Query Scope]
    CheckOuterScope --> CheckLocal
    CheckOuter -->|No| ErrorMissing[Throw Missing Attribute Exception]
    
    CreateResolved --> End([Resolved Field])
    ErrorAmbiguous --> End
    ErrorMissing --> End
```

### Asterisk Resolution Flow

```mermaid
flowchart TD
    Start([Asterisk Reference]) --> ParseChain[Parse Identifier Chain]
    ParseChain --> CheckLength{Chain Length <= 3?}
    
    CheckLength -->|Yes| TryTable[Try Table Reference]
    TryTable --> FindTable{Find Matching Table?}
    FindTable -->|Found| MarkTable[Mark as TABLE Basis]
    
    CheckLength -->|No| CheckLength2{Chain Length >= 2?}
    CheckLength2 -->|Yes| TryField[Try Row Field Reference]
    TryField --> FindField{Find Row Field?}
    FindField -->|Found| MarkField[Mark as FIELD Basis]
    
    FindTable -->|Not Found| CheckField
    FindField -->|Not Found| CheckAmbiguous
    
    CheckField --> CheckLength2
    CheckAmbiguous{Both Table & Field Found?}
    CheckAmbiguous -->|Yes| ErrorAmbiguous[Throw Ambiguous Exception]
    CheckAmbiguous -->|No| CheckOuter[Check Outer Query]
    
    CheckOuter -->|Has Outer| CheckOuterScope[Check Outer Query Scope]
    CheckOuterScope --> ParseChain
    CheckOuter -->|No Outer| ReturnEmpty[Return Empty]
    
    MarkTable --> ReturnBasis[Return Basis]
    MarkField --> ReturnBasis
    ReturnEmpty --> ReturnBasis
    ErrorAmbiguous --> ReturnBasis
```

## Key Features

### 1. Hierarchical Scope Management

The Scope class maintains a parent-child relationship between scopes, enabling proper name resolution across nested query contexts. Each scope can have:
- A parent scope for inheritance
- Query boundaries to isolate outer query contexts
- Local scope fields that are only visible within the current scope

### 2. Field Resolution

The field resolution mechanism handles:
- **Qualified Names**: Resolving `table.column` references
- **Ambiguous References**: Detecting and reporting ambiguous field references
- **Nested References**: Resolving fields in subqueries and CTEs
- **Outer Query References**: Allowing access to outer query fields

### 3. Asterisk Resolution

The asterisk resolution system implements SQL standard rules for:
- **Table References**: Resolving `table.*` to all fields from a specific table
- **Row Field References**: Resolving `row_field.*` for structured types
- **Ambiguity Detection**: Preventing ambiguous asterisk references
- **Outer Scope Resolution**: Resolving asterisks in outer query contexts

### 4. Named Query Management

Handles Common Table Expressions (CTEs) by:
- Storing named queries in scope
- Enabling recursive CTE resolution
- Preventing duplicate CTE definitions
- Supporting CTE inheritance across scopes

## Integration with SQL Analyzer

### Analysis Process Integration

```mermaid
graph TD
    subgraph "SQL Analysis Pipeline"
        Parse[SQL Parser] --> AST[AST Generation]
        AST --> Analyze[Statement Analysis]
        Analyze --> ScopeCreate[Scope Creation]
        ScopeCreate --> ScopeResolve[Name Resolution]
        ScopeResolve --> Validate[Validation]
        Validate --> Plan[Query Planning]
    end
    
    subgraph "Scope Management Role"
        ScopeCreate --> ScopeMgr[Scope Manager]
        ScopeResolve --> ScopeMgr
        ScopeMgr --> FieldRes[Field Resolution]
        ScopeMgr --> TableRes[Table Resolution]
        ScopeMgr --> ExprRes[Expression Resolution]
    end
```

### Statement Analysis Integration

The Scope Management module integrates with various statement analyzers:

- **SELECT Statement Analysis**: Resolves column references, table aliases, and join conditions
- **FROM Clause Analysis**: Handles table references and alias resolution
- **WHERE Clause Analysis**: Resolves predicate expressions
- **ORDER BY Analysis**: Resolves sort expressions
- **GROUP BY Analysis**: Resolves grouping expressions
- **HAVING Analysis**: Resolves filter expressions

## Error Handling

### Semantic Exceptions

The module throws specific semantic exceptions for various error conditions:

- **AmbiguousNameException**: When multiple fields match a reference
- **MissingAttributeException**: When no field matches a reference
- **SemanticException**: For general semantic errors

### Error Context

Each exception includes:
- **Expression Context**: The expression that caused the error
- **Qualified Name**: The name that couldn't be resolved
- **Location Information**: Line and column numbers when available
- **Suggestion Context**: Hints for resolving the issue

## Performance Considerations

### Optimization Strategies

1. **Lazy Resolution**: Fields are resolved only when needed
2. **Caching**: Resolved fields are cached within scope
3. **Early Termination**: Resolution stops at first match
4. **Scope Reuse**: Scopes are reused across similar contexts

### Memory Management

- **Immutable Design**: Scopes are immutable for thread safety
- **Builder Pattern**: Efficient scope construction
- **Optional Usage**: Minimal memory overhead for absent values
- **Relation Sharing**: Relation types are shared across scopes

## Testing and Validation

### Unit Testing

The module includes comprehensive unit tests for:
- Basic field resolution
- Nested scope resolution
- Outer query references
- Asterisk resolution
- Error conditions
- Edge cases

### Integration Testing

Integration tests verify:
- Complex query scenarios
- Multi-level nesting
- CTE interactions
- Join resolution
- Subquery correlations

## Related Documentation

- [SQL Analyzer](SQL Analyzer.md) - Parent module that uses Scope Management
- [SQL Parser & AST](SQL Parser & AST.md) - Provides the AST nodes that Scope analyzes
- [Trino SPI](Trino SPI.md) - Provides the type system and error handling infrastructure
- [Query Execution Engine](Query Execution Engine.md) - Uses resolved scopes for query execution

## Conclusion

The Scope Management module is fundamental to Trino's query analysis capabilities, providing the infrastructure for proper name resolution and scope management. Its hierarchical design enables complex query scenarios while maintaining SQL standard compliance and providing clear error messages for debugging.