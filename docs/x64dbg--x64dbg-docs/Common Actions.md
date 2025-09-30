# Common Actions Module

## Introduction

The Common Actions module serves as the central command dispatch and user interaction hub within the x64dbg debugger interface. It provides a unified framework for creating, managing, and executing context-sensitive actions across various debugger views including disassembly, dump, stack, and memory map views. This module implements the core action system that enables users to perform essential debugging operations through context menus, keyboard shortcuts, and toolbar actions.

## Architecture Overview

The Common Actions module follows a sophisticated action-based architecture that separates action definition from execution logic, enabling dynamic menu generation and context-sensitive behavior.

```mermaid
graph TB
    subgraph "Common Actions Architecture"
        CA[CommonActions Class] --> AH[ActionHelperProxy]
        CA --> MB[MenuBuilder]
        CA --> AF[ActionHelperFuncs]
        
        AH --> AM[Action Management]
        MB --> DM[Dynamic Menus]
        AF --> CF[Callback Functions]
        
        subgraph "Action Categories"
            AM --> NAV[Navigation Actions]
            AM --> BRK[Breakpoint Actions]
            AM --> MEM[Memory Actions]
            AM --> ANN[Annotation Actions]
            AM --> THR[Thread Actions]
        end
        
        subgraph "Context System"
            DM --> CS[Context Sensitivity]
            CS --> VC[View Context]
            CS --> DC[Debug Context]
            CS --> AC[Address Context]
        end
    end
```

## Core Components

### ActionHolder Structure

The `ActionHolder` structure serves as a container for breakpoint-related actions, providing organized access to hardware and software breakpoint operations.

```mermaid
classDiagram
    class ActionHolder {
        +QAction* toggleBreakpointAction
        +QAction* editSoftwareBreakpointAction
        +QAction* setHwBreakpointAction
        +QAction* removeHwBreakpointAction
        +QMenu* replaceSlotMenu
        +QAction* replaceSlotAction[4]
        +buildBreakpointMenu() void
    }
```

### CommonActions Class

The main class that orchestrates all common debugging actions through a unified interface.

```mermaid
classDiagram
    class CommonActions {
        -GetSelectionFunc mGetSelection
        -ActionHelperProxy ActionHelperProxy
        +build(MenuBuilder* builder, int actions) void
        +makeCommandAction() QAction*
        +makeCommandDescAction() QAction*
        +followDisassemblySlot() void
        +setLabelSlot() void
        +setCommentSlot() void
        +setBookmarkSlot() void
        +toggleInt3BPActionSlot() void
        +editSoftBpActionSlot() void
        +toggleHwBpActionSlot() void
        +graphSlot() void
        +displayTypeSlot() void
        +setNewOriginHereActionSlot() void
        +createThreadSlot() void
    }
```

## Action Categories

### Navigation Actions

Navigation actions provide seamless movement between different debugger views and memory locations.

```mermaid
graph LR
    subgraph "Navigation Flow"
        A[Address Selection] --> FD[Follow Disassembly]
        A --> FDUMP[Follow Dump]
        A --> FS[Follow Stack]
        A --> FMM[Follow Memory Map]
        A --> FG[Graph View]
        
        FD --> DASM[Disassembler View]
        FDUMP --> DUMP[Dump View]
        FS --> STACK[Stack View]
        FMM --> MEMMAP[Memory Map View]
        FG --> GRAPH[Control Flow Graph]
    end
```

**Key Navigation Actions:**
- **ActionDisasm**: Follow address in disassembler view
- **ActionDump**: Follow address in dump view
- **ActionStackDump**: Follow address in stack view
- **ActionMemoryMap**: Follow address in memory map view
- **ActionGraph**: Display control flow graph

### Breakpoint Management

The breakpoint system provides comprehensive hardware and software breakpoint management with intelligent slot allocation.

```mermaid
stateDiagram-v2
    [*] --> NoBreakpoint
    NoBreakpoint --> SoftwareBP : Toggle Int3
    SoftwareBP --> NoBreakpoint : Toggle Int3
    NoBreakpoint --> HardwareBP : Set Hardware
    HardwareBP --> NoBreakpoint : Remove Hardware
    
    HardwareBP --> SlotFull : All 4 Slots Used
    SlotFull --> ReplaceSlot : User Selects Slot
    ReplaceSlot --> HardwareBP : New BP Set
    
    SoftwareBP --> EditBP : Edit Breakpoint
    HardwareBP --> EditBP : Edit Breakpoint
    EditBP --> [*]
```

**Breakpoint Actions:**
- **ActionBreakpoint**: Toggle software breakpoints
- **Hardware Breakpoint Management**: Set/remove hardware breakpoints with slot replacement
- **Conditional Breakpoints**: Edit breakpoint conditions and properties

### Annotation System

The annotation system enables users to add contextual information to memory addresses.

```mermaid
graph TD
    subgraph "Annotation Workflow"
        A[Address Selection] --> L[Label Dialog]
        A --> C[Comment Dialog]
        A --> B[Bookmark Toggle]
        
        L --> LV[Label Validation]
        LV --> LS[Label Set]
        
        C --> CV[Comment Validation]
        CV --> CS[Comment Set]
        
        B --> BV[Bookmark Validation]
        BV --> BT[Bookmark Toggle]
        
        LS --> UV[Update Views]
        CS --> UV
        BT --> UV
    end
```

**Annotation Actions:**
- **ActionLabel**: Set/clear labels at addresses
- **ActionComment**: Add/edit comments
- **ActionBookmark**: Toggle bookmarks for quick navigation

### Memory and Type Operations

Advanced memory operations and type visualization capabilities.

```mermaid
graph LR
    subgraph "Memory Operations"
        A[Address] --> DT[Display Type]
        A --> W[Watch Variable]
        A --> DD[Dump Data]
        
        DT --> TV[Type Viewer]
        W --> WV[Watch View]
        DD --> DV[Dump View]
        
        TV --> TS[Type Selection]
        WV --> WE[Watch Expression]
        DV --> DS[Dump Settings]
    end
```

**Memory Actions:**
- **ActionDisplayType**: Display structured types at addresses
- **ActionWatch**: Add variables to watch view
- **ActionDumpData**: Follow pointer data in dump views

### Thread Control

Thread management operations for advanced debugging scenarios.

```mermaid
sequenceDiagram
    participant User
    participant CommonActions
    participant Debugger
    
    User->>CommonActions: Set New Origin
    CommonActions->>CommonActions: Validate Address
    CommonActions->>User: Warning if Not Executable
    User->>CommonActions: Confirm
    CommonActions->>Debugger: Execute cip=address
    
    User->>CommonActions: Create Thread
    CommonActions->>User: Show Argument Dialog
    User->>CommonActions: Provide Argument
    CommonActions->>Debugger: Execute createthread
```

**Thread Actions:**
- **ActionNewOrigin**: Set instruction pointer to new location
- **ActionNewThread**: Create new thread at specified address

## Context Sensitivity System

The module implements sophisticated context sensitivity to ensure actions are only available when appropriate.

```mermaid
graph TD
    subgraph "Context Evaluation"
        A[Action Request] --> CE[Context Evaluation]
        CE --> DC[Debug Context]
        CE --> AC[Address Context]
        CE --> VC[View Context]
        
        DC --> DD[Debugging?]
        AC --> VAR[Valid Address?]
        AC --> VER[Executable?]
        VC --> VTR[Valid Read Ptr?]
        
        DD --> EN[Enable Action]
        VAR --> EN
        VER --> EN
        VTR --> EN
        
        EN --> AB[Action Build]
        AB --> DI[Dynamic Items]
    end
```

### Context Conditions

- **isDebugging**: Validates active debugging session
- **isValidReadPtr**: Checks memory readability
- **WarningBoxNotExecutable**: Warns about non-executable addresses

## Integration with Other Modules

The Common Actions module serves as a central hub that integrates with multiple debugger subsystems.

```mermaid
graph TB
    subgraph "Module Dependencies"
        CA[Common Actions] --> BP[Breakpoint System]
        CA --> SYM[Symbol Resolution]
        CA --> MM[Memory Management]
        CA --> REF[Reference Management]
        CA --> GUI[GUI Bridge]
        
        BP --> BPL[Breakpoint Lists]
        BP --> BPT[Breakpoint Types]
        
        SYM --> SYMRES[Symbol Resolution]
        SYM --> SYMLOAD[Symbol Loading]
        
        MM --> MEMREAD[Memory Reading]
        MM --> MEMVALID[Memory Validation]
        
        REF --> XREF[Cross References]
        REF --> ADDRINFO[Address Information]
        
        GUI --> VIEWUPD[View Updates]
        GUI --> STATBAR[Status Bar]
    end
```

### Key Dependencies

- **[Breakpoint System](Breakpoint%20System.md)**: Hardware/software breakpoint management
- **[Symbol Resolution](Symbol%20Resolution.md)**: Address-to-symbol translation
- **[Memory Management](Memory%20Management.md)**: Memory validation and reading
- **[Reference Management](Reference%20Management.md)**: Cross-reference information
- **[GUI Bridge](GUI%20Bridge.md)**: View updates and user interface integration

## Action Creation Framework

The module provides a comprehensive framework for creating different types of actions with consistent behavior.

```mermaid
graph LR
    subgraph "Action Creation Pipeline"
        AC[Action Creation] --> MA[Make Action]
        MA --> CA[Command Action]
        MA --> SA[Shortcut Action]
        MA --> DA[Desc Action]
        
        CA --> CC[Command Connection]
        SA --> SC[Shortcut Configuration]
        DA --> DS[Description Set]
        
        CC --> EX[Execution]
        SC --> KB[Keyboard Binding]
        DS --> TT[Tooltip Text]
    end
```

### Action Factory Methods

- **makeCommandAction**: Creates actions that execute debugger commands
- **makeCommandDescAction**: Creates command actions with descriptions
- **makeShortcutAction**: Creates keyboard-shortcut enabled actions
- **makeShortcutDescAction**: Creates shortcut actions with descriptions

## Error Handling and Validation

The module implements comprehensive error handling and user feedback mechanisms.

```mermaid
graph TD
    subgraph "Error Handling Flow"
        A[Action Execution] --> V[Validation]
        V --> S[Success?]
        S -->|Yes| C[Continue]
        S -->|No| E[Error Type]
        
        E --> IV[Invalid Address]
        E --> NE[Not Executable]
        E --> DD[Debug Error]
        
        IV --> UM[User Message]
        NE --> WB[Warning Box]
        DD --> EB[Error Box]
        
        UM --> UV[Update Views]
        WB --> UV
        EB --> UV
    end
```

### Validation Checks

- **Address Validation**: Ensures selected addresses are valid
- **Memory Validation**: Verifies memory accessibility
- **Executable Validation**: Warns about non-executable addresses
- **Debug State Validation**: Confirms appropriate debugging state

## Configuration and Customization

The module supports extensive configuration through the action helper system and menu builder framework.

```mermaid
graph LR
    subgraph "Configuration System"
        CONFIG[Configuration] --> SC[Shortcut Configuration]
        CONFIG --> IC[Icon Configuration]
        CONFIG --> TC[Text Configuration]
        
        SC --> SKB[Keyboard Bindings]
        IC --> ICON[Icon Themes]
        TC --> LANG[Language Support]
        
        SKB --> AHS[Action Helper System]
        ICON --> MB[Menu Builder]
        LANG --> UI[User Interface]
    end
```

## Performance Considerations

The module is designed for optimal performance in debugging scenarios:

- **Lazy Evaluation**: Context conditions evaluated only when needed
- **Action Caching**: Reusable action objects to minimize allocation
- **Efficient Lookups**: Direct command execution without intermediate layers
- **Minimal Overhead**: Lightweight action creation and management

## Usage Examples

### Basic Action Creation
```cpp
// Create a simple command action
auto* action = makeCommandAction(DIcon("icon"), "Action Text", "command $", "Shortcut");

// Create a context-sensitive action
builder->addAction(action, [this](QMenu*) {
    return DbgIsDebugging() && mGetSelection() != 0;
});
```

### Complex Menu Building
```cpp
// Build breakpoint submenu with dynamic content
builder->addMenu(makeMenu(DIcon("breakpoint"), tr("Breakpoint")), 
    [this](QMenu* menu) {
        // Dynamic content based on current breakpoint state
        return buildBreakpointMenu(menu);
    });
```

## Future Enhancements

The module architecture supports extensibility for future debugging features:

- **Plugin Integration**: Action registration from plugins
- **Custom Action Types**: User-defined action categories
- **Advanced Scripting**: Scriptable action sequences
- **Workflow Automation**: Complex debugging workflow support

## Summary

The Common Actions module represents a critical component of the x64dbg debugger, providing the essential user interaction layer that connects user intentions with debugger functionality. Its sophisticated architecture enables context-sensitive operations, comprehensive breakpoint management, and seamless navigation across different debugger views while maintaining extensibility for future enhancements.