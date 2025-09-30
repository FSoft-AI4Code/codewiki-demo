# gitGraphAst Module Documentation

## Introduction

The `gitGraphAst` module is the core Abstract Syntax Tree (AST) state management system for Git Graph diagrams in Mermaid. It provides a comprehensive API for managing Git repository visualization data, including commits, branches, merges, and cherry-pick operations. This module serves as the central data layer that transforms Git Graph diagram syntax into structured data that can be rendered visually.

## Architecture Overview

The gitGraphAst module implements a stateful architecture that maintains the complete Git repository structure in memory, providing operations to manipulate branches, commits, and relationships between them.

```mermaid
graph TB
    subgraph "gitGraphAst Module"
        GGAS[GitGraphState<br/>Core State Container]
        IDG[ImperativeState<br/>State Management]
        CF[Configuration<br/>System]
        
        GGAS --> IDG
        GGAS --> CF
    end
    
    subgraph "External Dependencies"
        LOG[Logger<br/>packages.mermaid.src.logger]
        UTIL[Utils<br/>packages.mermaid.src.utils]
        CONF[Config<br/>packages.mermaid.src.config]
        COMDB[CommonDB<br/>packages.mermaid.src.diagrams.common]
        GGTT[GitGraphTypes<br/>packages.mermaid.src.diagrams.git]
    end
    
    GGAS --> LOG
    GGAS --> UTIL
    GGAS --> CONF
    GGAS --> COMDB
    GGAS --> GGTT
    
    subgraph "Git Operations"
        COMMIT[commit]
        BRANCH[branch]
        MERGE[merge]
        CHERRY[cherryPick]
        CHECKOUT[checkout]
    end
    
    GGAS --> COMMIT
    GGAS --> BRANCH
    GGAS --> MERGE
    GGAS --> CHERRY
    GGAS --> CHECKOUT
```

## Core Components

### GitGraphState Interface

The `GitGraphState` interface defines the complete state structure for Git Graph diagrams:

```typescript
interface GitGraphState {
  commits: Map<string, Commit>;           // All commits indexed by ID
  head: Commit | null;                    // Current HEAD commit
  branchConfig: Map<string, { name: string; order: number | undefined }>; // Branch metadata
  branches: Map<string, string | null>;   // Branch names to commit ID mapping
  currBranch: string;                     // Currently active branch
  direction: DiagramOrientation;          // Layout direction (LR, TB, BT)
  seq: number;                            // Sequence counter for commits
  options: any;                           // Custom diagram options
}
```

### State Management

The module uses `ImperativeState` for robust state management with automatic reset capabilities:

```mermaid
sequenceDiagram
    participant Client
    participant GitGraphAst
    participant ImperativeState
    participant StateStorage
    
    Client->>GitGraphAst: Initialize diagram
    GitGraphAst->>ImperativeState: Create new state instance
    ImperativeState->>StateStorage: Initialize default state
    StateStorage-->>ImperativeState: Return initial state
    ImperativeState-->>GitGraphAst: State ready
    
    Client->>GitGraphAst: commit(data)
    GitGraphAst->>ImperativeState: Update state.records
    ImperativeState->>StateStorage: Store new commit
    StateStorage-->>ImperativeState: State updated
    ImperativeState-->>GitGraphAst: Operation complete
    
    Client->>GitGraphAst: clear()
    GitGraphAst->>ImperativeState: reset()
    ImperativeState->>StateStorage: Reset to initial state
    StateStorage-->>ImperativeState: State reset complete
```

## Data Flow Architecture

```mermaid
graph LR
    subgraph "Input Processing"
        SYNTAX[Git Graph Syntax]
        PARSER[Parser]
        AST[AST Operations]
    end
    
    subgraph "State Management"
        STATE[GitGraphState]
        VALIDATE[Validation Engine]
        TRANSFORM[Data Transformation]
    end
    
    subgraph "Output Generation"
        STRUCT[Structured Data]
        RENDER[Renderer Interface]
        VISUAL[Visual Output]
    end
    
    SYNTAX --> PARSER
    PARSER --> AST
    AST --> STATE
    STATE --> VALIDATE
    VALIDATE --> TRANSFORM
    TRANSFORM --> STRUCT
    STRUCT --> RENDER
    RENDER --> VISUAL
```

## Core Operations

### Commit Management

The commit operation creates new commits and manages the Git history:

```mermaid
flowchart TD
    Start([Commit Request])
    Sanitize{Sanitize Input}
    GenerateID[Generate Unique ID]
    CreateCommit[Create Commit Object]
    UpdateHead[Update HEAD Pointer]
    UpdateBranch[Update Branch Pointer]
    StoreCommit[Store in State]
    End([Commit Complete])
    
    Start --> Sanitize
    Sanitize --> GenerateID
    GenerateID --> CreateCommit
    CreateCommit --> UpdateHead
    UpdateHead --> UpdateBranch
    UpdateBranch --> StoreCommit
    StoreCommit --> End
```

### Branch Operations

Branch operations include creation, checkout, and management:

```mermaid
stateDiagram-v2
    [*] --> InitialState
    InitialState --> BranchExists: branch(name)
    BranchExists --> ActiveBranch: checkout(name)
    ActiveBranch --> BranchExists: branch(new_name)
    ActiveBranch --> AnotherBranch: checkout(other_name)
    AnotherBranch --> ActiveBranch: checkout(name)
    
    state BranchExists {
        [*] --> ValidName
        ValidName --> DuplicateCheck
        DuplicateCheck --> CreateBranch: Name Available
        DuplicateCheck --> Error: Name Exists
        CreateBranch --> SetConfig
        SetConfig --> ActiveBranch
    }
```

### Merge Operations

Merge operations handle complex Git merge scenarios with comprehensive validation:

```mermaid
flowchart TD
    Start([Merge Request])
    ValidateInput{Validate Input}
    CheckSelfMerge{Self-Merge Check}
    CheckBranchExists{Branch Exists?}
    CheckCommits{Commits Available?}
    CheckSameHead{Same HEAD?}
    CheckDuplicateID{Duplicate ID?}
    
    ValidateInput -->|Valid| CheckSelfMerge
    ValidateInput -->|Invalid| ErrorInvalid
    CheckSelfMerge -->|Different| CheckBranchExists
    CheckSelfMerge -->|Same| ErrorSelfMerge
    CheckBranchExists -->|Yes| CheckCommits
    CheckBranchExists -->|No| ErrorBranchMissing
    CheckCommits -->|Available| CheckSameHead
    CheckCommits -->|Missing| ErrorNoCommits
    CheckSameHead -->|Different| CheckDuplicateID
    CheckSameHead -->|Same| ErrorSameHead
    CheckDuplicateID -->|Unique| CreateMergeCommit
    CheckDuplicateID -->|Duplicate| ErrorDuplicateID
    
    CreateMergeCommit --> UpdateState
    UpdateState --> Success([Merge Complete])
    
    ErrorInvalid --> Fail([Validation Failed])
    ErrorSelfMerge --> Fail
    ErrorBranchMissing --> Fail
    ErrorNoCommits --> Fail
    ErrorSameHead --> Fail
    ErrorDuplicateID --> Fail
```

### Cherry-Pick Operations

Cherry-pick operations allow selective commit application:

```mermaid
sequenceDiagram
    participant Client
    participant GitGraphAst
    participant Validation
    participant StateManager
    
    Client->>GitGraphAst: cherryPick(sourceId, targetId)
    GitGraphAst->>Validation: Validate source commit
    Validation->>GitGraphAst: Source exists
    GitGraphAst->>Validation: Check target branch
    Validation->>GitGraphAst: Target validation
    
    alt Target commit provided
        GitGraphAst->>StateManager: Apply to specific commit
    else No target (current branch)
        GitGraphAst->>StateManager: Apply to HEAD
        StateManager->>Validation: Check current branch
        Validation->>StateManager: Branch validation
    end
    
    StateManager->>GitGraphAst: Create cherry-pick commit
    GitGraphAst->>Client: Operation complete
```

## Component Relationships

```mermaid
graph TB
    subgraph "gitGraphAst Core"
        STATE[GitGraphState]
        DB[GitGraphDB Interface]
        OPS[Operations]
    end
    
    subgraph "Type System"
        COMMIT[Commit Type]
        BRANCH[Branch Types]
        MERGE[Merge Types]
        CHERRY[CherryPick Types]
        ORIENT[DiagramOrientation]
    end
    
    subgraph "Configuration"
        CONFIG[GitGraphDiagramConfig]
        DEFAULT[Default Config]
        MERGE[Config Merge]
    end
    
    subgraph "Utilities"
        SANITIZE[Text Sanitization]
        RANDOM[ID Generation]
        LOGGER[Logging]
    end
    
    STATE --> COMMIT
    STATE --> BRANCH
    DB --> OPS
    
    CONFIG --> DEFAULT
    CONFIG --> MERGE
    
    OPS --> SANITIZE
    OPS --> RANDOM
    OPS --> LOGGER
    
    COMMIT --> ORIENT
    BRANCH --> ORIENT
```

## Error Handling

The module implements comprehensive error handling with detailed error contexts:

```mermaid
stateDiagram-v2
    [*] --> OperationRequested
    OperationRequested --> Validation: Validate Input
    Validation --> PreconditionCheck: Valid Input
    Validation --> ValidationError: Invalid Input
    
    PreconditionCheck --> StateCheck: Check State
    PreconditionCheck --> PreconditionError: Precondition Failed
    
    StateCheck --> ExecuteOperation: State Valid
    StateCheck --> StateError: Invalid State
    
    ExecuteOperation --> Success: Operation Complete
    ExecuteOperation --> ExecutionError: Operation Failed
    
    ValidationError --> ErrorContext: Add Context
    PreconditionError --> ErrorContext: Add Context
    StateError --> ErrorContext: Add Context
    ExecutionError --> ErrorContext: Add Context
    
    ErrorContext --> ErrorResponse: Return Error
    Success --> SuccessResponse: Return Result
    
    ErrorResponse --> [*]
    SuccessResponse --> [*]
```

## Integration with Mermaid System

The gitGraphAst module integrates with the broader Mermaid ecosystem:

```mermaid
graph LR
    subgraph "Mermaid Core"
        MERMAID[Mermaid Engine]
        CONFIG[Configuration System]
        RENDER[Rendering Pipeline]
    end
    
    subgraph "gitGraphAst Module"
        AST[GitGraphAst]
        STATE[State Management]
        TYPES[Type Definitions]
    end
    
    subgraph "Git Diagram Components"
        PARSER[Git Parser]
        RENDERER[Git Renderer]
        LAYOUT[Layout Engine]
    end
    
    MERMAID --> PARSER
    CONFIG --> AST
    AST --> STATE
    STATE --> TYPES
    
    PARSER --> AST
    AST --> RENDERER
    RENDERER --> LAYOUT
    LAYOUT --> RENDER
    
    RENDER --> MERMAID
```

## Configuration System

The module supports extensive configuration through the Mermaid configuration system:

- **Main Branch Configuration**: Configurable main branch name and order
- **Layout Direction**: Support for Left-to-Right (LR), Top-to-Bottom (TB), and Bottom-to-Top (BT) orientations
- **Custom Options**: JSON-based custom options for diagram-specific settings
- **Text Sanitization**: Configurable text processing for security and consistency

## API Reference

### Primary Operations

- `commit(commitDB: CommitDB)`: Create a new commit
- `branch(branchDB: BranchDB)`: Create a new branch
- `merge(mergeDB: MergeDB)`: Merge branches
- `cherryPick(cherryPickDB: CherryPickDB)`: Cherry-pick commits
- `checkout(branch: string)`: Switch branches

### State Management

- `clear()`: Reset all state
- `setDirection(dir: DiagramOrientation)`: Set layout direction
- `setOptions(rawOptString: string)`: Set custom options
- `getOptions()`: Retrieve current options

### Data Access

- `getBranches()`: Get all branches
- `getCommits()`: Get all commits
- `getCommitsArray()`: Get commits as sorted array
- `getCurrentBranch()`: Get current branch name
- `getHead()`: Get HEAD commit
- `getDirection()`: Get layout direction

## Dependencies

- **[config](config.md)**: Configuration management system
- **[common](common.md)**: Common utilities and text processing
- **[logger](logger.md)**: Logging infrastructure
- **[utils](utils.md)**: Utility functions including ID generation
- **[gitGraphTypes](gitGraphTypes.md)**: Type definitions for Git Graph components

## Usage Patterns

The gitGraphAst module is typically used as part of the Git Graph diagram parsing and rendering pipeline. It maintains the complete state of the Git repository being visualized and provides the structured data needed for rendering the final diagram.

The module's stateful design allows for incremental building of complex Git histories while maintaining data consistency and providing comprehensive validation for Git operations.