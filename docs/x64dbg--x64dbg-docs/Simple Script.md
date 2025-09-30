# Simple Script Module

## Introduction

The Simple Script module is a core component of the x64dbg debugger that provides a lightweight scripting engine for automating debugging tasks. It implements a custom scripting language with support for labels, branches, commands, breakpoints, and stack-based execution flow control. The module enables users to create automated debugging workflows, perform repetitive tasks, and extend the debugger's functionality through script execution.

## Architecture Overview

The Simple Script module operates as an embedded scripting engine within the debugger, providing a complete execution environment with its own instruction pointer, call stack, and state management system.

```mermaid
graph TB
    subgraph "Simple Script Engine"
        A[Script Loader] --> B[Line Parser]
        B --> C[Line Map Builder]
        C --> D[Script Executor]
        D --> E[Command Processor]
        D --> F[Branch Handler]
        D --> G[Stack Manager]
        
        H[Breakpoint Manager] --> D
        I[State Controller] --> D
        J[Error Handler] --> D
    end
    
    K[Debugger Core] --> E
    E --> K
    L[GUI Interface] --> A
    L --> H
    M[File System] --> A
    
    style A fill:#e1f5fe
    style D fill:#e1f5fe
    style H fill:#fff3e0
    style I fill:#fff3e0
```

## Core Components

### SCRIPTFRAME Structure

The `SCRIPTFRAME` structure represents execution context within the script engine, maintaining the instruction pointer and execution state for proper call stack management.

```mermaid
classDiagram
    class SCRIPTFRAME {
        +int ip
        +SCRIPTSTATE state
    }
    
    class SCRIPTSTATE {
        <<enumeration>>
        SCRIPT_PAUSED
        SCRIPT_RUNNING
        SCRIPT_STEPPING
    }
    
    SCRIPTFRAME --> SCRIPTSTATE : uses
```

**Key Responsibilities:**
- Maintains instruction pointer for script execution flow
- Tracks execution state (paused, running, stepping)
- Enables proper call stack management for script functions
- Supports nested script execution through stack frames

### SCRIPTBP Structure

The `SCRIPTBP` structure manages script breakpoints, providing debugging capabilities within script execution.

```mermaid
classDiagram
    class SCRIPTBP {
        +int line
        +bool silent
    }
    
    class BreakpointManager {
        +ToggleBreakpoint(line)
        +GetBreakpoint(line)
        +ClearAllBreakpoints()
    }
    
    BreakpointManager --> SCRIPTBP : manages
```

**Key Responsibilities:**
- Defines breakpoint locations within script code
- Controls breakpoint visibility in GUI
- Enables script debugging and step-through execution
- Supports both user-set and internal breakpoints

### LINEMAPENTRY Structure

The `LINEMAPENTRY` structure represents parsed script lines with type information and associated data, forming the core of the script's intermediate representation.

```mermaid
classDiagram
    class LINEMAPENTRY {
        +SCRIPTLINETYPE type
        +char raw[256]
        +union u
    }
    
    class SCRIPTLINETYPE {
        <<enumeration>>
        lineempty
        linecomment
        linelabel
        linebranch
        linecommand
    }
    
    class UnionData {
        +char command[256]
        +SCRIPTBRANCH branch
        +char label[256]
        +char comment[256]
    }
    
    LINEMAPENTRY --> SCRIPTLINETYPE : has
    LINEMAPENTRY --> UnionData : contains
```

**Key Responsibilities:**
- Stores parsed script line information
- Maintains both raw and processed line data
- Handles different line types (commands, labels, branches, comments)
- Provides unified access to line-specific data through unions

## Data Flow Architecture

### Script Loading and Parsing Flow

```mermaid
sequenceDiagram
    participant User
    participant ScriptLoader
    participant FileHelper
    participant LineParser
    participant LineMapBuilder
    participant GUI
    
    User->>ScriptLoader: LoadScript(filename)
    ScriptLoader->>FileHelper: ReadAllText(filename)
    FileHelper-->>ScriptLoader: filedata
    ScriptLoader->>LineParser: ParseLines(filedata)
    LineParser->>LineParser: ProcessComments
    LineParser->>LineParser: TrimWhitespace
    LineParser->>LineParser: IdentifyLineTypes
    LineParser-->>ScriptLoader: parsedLines
    ScriptLoader->>LineMapBuilder: BuildLineMap(parsedLines)
    LineMapBuilder->>LineMapBuilder: ValidateLabels
    LineMapBuilder->>LineMapBuilder: ResolveBranchTargets
    LineMapBuilder->>LineMapBuilder: AddTermination
    LineMapBuilder-->>ScriptLoader: completeMap
    ScriptLoader->>GUI: UpdateScriptView(completeMap)
    ScriptLoader-->>User: Success/Failure
```

### Script Execution Flow

```mermaid
sequenceDiagram
    participant User
    participant ScriptExecutor
    participant StateController
    participant CommandProcessor
    participant BranchHandler
    participant StackManager
    participant Debugger
    
    User->>ScriptExecutor: RunScript()
    ScriptExecutor->>StateController: SetState(SCRIPT_RUNNING)
    loop Execution Loop
        ScriptExecutor->>ScriptExecutor: GetCurrentLine()
        alt LineType = command
            ScriptExecutor->>CommandProcessor: ExecuteCommand()
            CommandProcessor->>Debugger: ExecuteDebuggerCommand()
            Debugger-->>CommandProcessor: Result
            CommandProcessor-->>ScriptExecutor: Status
        else LineType = branch
            ScriptExecutor->>BranchHandler: EvaluateBranch()
            BranchHandler->>BranchHandler: CheckConditions()
            alt BranchTaken
                BranchHandler->>StackManager: UpdateIP()
                BranchHandler-->>ScriptExecutor: CONTINUE_BRANCH
            else BranchNotTaken
                BranchHandler-->>ScriptExecutor: CONTINUE
            end
        end
        ScriptExecutor->>StateController: CheckState()
        alt State = PAUSED
            ScriptExecutor-->>User: Paused
        else State = RUNNING
            ScriptExecutor->>ScriptExecutor: NextIP()
        end
    end
    ScriptExecutor->>StateController: SetState(SCRIPT_PAUSED)
    ScriptExecutor-->>User: ExecutionComplete
```

## Component Interactions

### Script State Management

```mermaid
stateDiagram-v2
    [*] --> SCRIPT_PAUSED: Initialize
    SCRIPT_PAUSED --> SCRIPT_RUNNING: RunScript()
    SCRIPT_PAUSED --> SCRIPT_STEPPING: StepScript()
    SCRIPT_RUNNING --> SCRIPT_PAUSED: Pause/Breakpoint
    SCRIPT_RUNNING --> SCRIPT_STEPPING: StepMode
    SCRIPT_STEPPING --> SCRIPT_PAUSED: StepComplete
    SCRIPT_STEPPING --> SCRIPT_RUNNING: Continue
    SCRIPT_RUNNING --> [*]: ScriptComplete/Error
    SCRIPT_PAUSED --> [*]: UnloadScript
```

### Branch Evaluation System

```mermaid
graph LR
    A[Branch Command] --> B{Parse Branch Type}
    B -->|jmp/goto| C[Unconditional]
    B -->|call| D[Function Call]
    B -->|conditional| E[Check Flags]
    
    E --> F{Flag Evaluation}
    F -->|$_EZ_FLAG=1| G[Equal/Zero]
    F -->|$_EZ_FLAG=0| H[Not Equal]
    F -->|$_BS_FLAG=1| I[Above/Greater]
    F -->|$_BS_FLAG=0| J[Below/Less]
    
    C --> K[Take Branch]
    D --> L[Push Stack Frame]
    L --> K
    G --> M{Branch Type}
    H --> M
    I --> M
    J --> M
    
    M -->|matching| K
    M -->|not matching| N[Continue]
```

## Integration with Debugger System

### Dependency Relationships

The Simple Script module integrates with multiple debugger subsystems:

```mermaid
graph TB
    SS[Simple Script]
    
    SS -->|executes commands| DC[Debugger Core]
    SS -->|displays output| CON[Console]
    SS -->|manages variables| VAR[Variable System]
    SS -->|file operations| FH[File Helper]
    SS -->|thread safety| THR[Threading]
    SS -->|GUI updates| GUI[GUI Bridge]
    SS -->|job scheduling| JQ[Job Queue]
    
    BP[Breakpoint System] -->|script breakpoints| SS
    SM[Symbol Management] -->|command resolution| DC
    MM[Memory Management] -->|command execution| DC
```

### Thread Safety Architecture

```mermaid
graph LR
    subgraph "Thread-Safe Operations"
        A[Script Queue] -->|serializes| B[Script Execution]
        C[LockScriptLineMap] -->|protects| D[Line Map Access]
        E[LockScriptBreakpoints] -->|protects| F[Breakpoint List]
    end
    
    subgraph "Atomic Operations"
        G[scriptState] -->|atomic| H[State Changes]
        I[bScriptAbort] -->|atomic| J[Abort Signals]
        K[bScriptLogEnabled] -->|atomic| L[Log Control]
    end
    
    M[Multiple Threads] --> A
    M --> C
    M --> E
    M --> G
    M --> I
    M --> K
```

## Error Handling and Recovery

### Error Management Flow

```mermaid
graph TD
    A[Script Error] --> B{Error Type}
    B -->|Parse Error| C[ScriptLoad Error]
    B -->|Runtime Error| D[Command Error]
    B -->|Validation Error| E[Label/Branch Error]
    
    C --> F[Clear Line Map]
    C --> G[Display Error]
    C --> H[Return Failure]
    
    D --> I[Log Error]
    D --> J[Set IP to Error Line]
    D --> K[Pause Execution]
    
    E --> L[Detailed Message]
    E --> M[Line Information]
    E --> H
    
    G --> N{GUI Mode?}
    N -->|Yes| O[GuiScriptError]
    N -->|No| P[dputs_untranslated]
```

## Performance Considerations

### Execution Optimization

- **Line Map Caching**: Parsed script lines are cached to avoid re-parsing during execution
- **Branch Target Resolution**: Branch destinations are pre-calculated during script loading
- **Atomic State Management**: Script state changes use atomic operations for thread safety
- **Job Queue Serialization**: Script operations are serialized through a job queue to prevent race conditions

### Memory Management

- **Static Data Structures**: Core script data structures are statically allocated for performance
- **Shared Locks**: Read-heavy operations use shared locks for concurrent access
- **Exclusive Locks**: Write operations use exclusive locks to ensure data consistency

## API Integration

### External Interfaces

The Simple Script module provides several public interfaces for external integration:

- **ScriptLoadAwait**: Synchronous script loading with GUI feedback
- **ScriptRunAsync/ScriptRunAwait**: Asynchronous and synchronous script execution
- **ScriptStepAsync**: Single-step script execution for debugging
- **ScriptCmdExecAwait**: Direct command execution within script context
- **ScriptBpToggleLocked**: Breakpoint management with thread safety

### GUI Bridge Integration

```mermaid
sequenceDiagram
    participant ScriptEngine
    participant GUIBridge
    participant ScriptView
    
    ScriptEngine->>GUIBridge: GuiScriptClear()
    ScriptEngine->>GUIBridge: GuiScriptAdd(lines, script)
    ScriptEngine->>GUIBridge: GuiScriptSetIp(ip)
    ScriptEngine->>GUIBridge: GuiScriptMessage(message)
    ScriptEngine->>GUIBridge: GuiScriptError(line, error)
    ScriptEngine->>GUIBridge: GuiScriptMsgyn(message)
    ScriptEngine->>GUIBridge: GuiScriptEnableHighlighting(enable)
    ScriptEngine->>GUIBridge: GuiScriptSetInfoLine(line, info)
    GUIBridge->>ScriptView: UpdateDisplay()
```

## Security Considerations

### Script Safety Features

- **Timeout Protection**: Scripts automatically timeout after 30 seconds to prevent infinite loops
- **Recursive Execution Prevention**: Scripts cannot recursively execute other scripts
- **State Validation**: Script state is validated before execution to prevent invalid operations
- **Breakpoint Safety**: Breakpoints are validated against the line map to prevent invalid access

### Command Execution Security

- **Command Validation**: All commands are validated before execution
- **Debugger State Checks**: Script execution requires the debugger to be in a valid state
- **Error Propagation**: Errors are properly propagated to prevent silent failures

## Related Modules

- [Breakpoint System](Breakpoint%20System.md) - Script breakpoint integration
- [GUI Bridge](GUI%20Bridge.md) - Script display and user interaction
- [Job Queue](Job%20Queue.md) - Script execution serialization
- [Variable System](Variable%20System.md) - Script variable access and manipulation
- [Console](Console.md) - Script output and error display
- [File Helper](File%20Helper.md) - Script file loading and management