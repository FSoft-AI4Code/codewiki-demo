# Instrumenter Core Module

## Introduction

The instrumenter_core module is a sophisticated debugging and interaction tracking system for Storybook. It provides runtime instrumentation capabilities that enable developers to monitor, intercept, and debug function calls within stories and components. This module is essential for the Storybook Interactions addon, offering step-through debugging, call tracing, and interactive testing features.

## Core Purpose

The instrumenter_core module serves as the foundation for:
- **Function Call Instrumentation**: Dynamically patches functions to track their execution
- **Interactive Debugging**: Provides step-through debugging capabilities for story interactions
- **Call Tracing**: Records and manages function call hierarchies and dependencies
- **State Management**: Maintains per-story debugging state across iframe reloads
- **Exception Handling**: Captures and processes errors with detailed context information

## Architecture Overview

```mermaid
graph TB
    subgraph "Instrumenter Core Architecture"
        IC[Instrumenter Class]
        IFunc[instrument Function]
        
        subgraph "State Management"
            SS[Story State]
            CS[Call State]
            CSR[Call References]
        end
        
        subgraph "Instrumentation Engine"
            FI[Function Instrumentation]
            CT[Call Tracking]
            II[Intercept & Invoke]
        end
        
        subgraph "Communication Layer"
            CH[Channel Events]
            PS[Parent Window State]
        end
        
        subgraph "Debugging Controls"
            DC[Debug Controls]
            SC[Step Controls]
            CS2[Call States]
        end
    end
    
    IC --> SS
    IC --> FI
    IC --> CH
    IC --> PS
    
    IFunc --> IC
    
    FI --> CT
    CT --> II
    
    SS --> CS
    CS --> CSR
    
    CH --> DC
    DC --> SC
    SC --> CS2
```

## Component Relationships

```mermaid
graph LR
    subgraph "External Dependencies"
        CE[Core Events]
        CH2[Channels]
        CL[Client Logger]
        GT[Global Types]
        PS2[Preview API]
    end
    
    subgraph "Instrumenter Core"
        INS[Instrumenter]
        TYP[Types]
        EVT[Events]
    end
    
    subgraph "Parent Module"
        INS2[Instrumenter Parent]
    end
    
    CE --> INS
    CH2 --> INS
    CL --> INS
    GT --> TYP
    PS2 --> INS
    
    INS --> INS2
    TYP --> INS
    EVT --> INS
```

## Core Components

### Instrumenter Class

The `Instrumenter` class is the main orchestrator that manages the instrumentation process. It maintains per-story state, handles communication with the Storybook manager, and coordinates the debugging workflow.

**Key Responsibilities:**
- State management for multiple stories
- Event handling and channel communication
- Function instrumentation coordination
- Exception handling and error processing
- Parent window state synchronization

### State Management

The module maintains sophisticated state tracking with the following structure:

```mermaid
graph TD
    subgraph "State Structure"
        S[State Object]
        
        S --> RP[renderPhase]
        S --> ID[isDebugging]
        S --> IP[isPlaying]
        S --> IL[isLocked]
        S --> C[cursor]
        
        S --> CALLS[calls Array]
        S --> SC[shadowCalls Array]
        
        S --> CR[callRefsByResult Map]
        S --> CC[chainedCallIds Set]
        S --> A[ancestors Array]
        
        S --> PU[playUntil]
        S --> R[resolvers Object]
        S --> ST[syncTimeout]
    end
```

### Function Instrumentation Process

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant Story as Story Component
    participant Inst as Instrumenter
    participant Func as Original Function
    participant Channel as Event Channel
    
    Dev->>Story: Interact with Story
    Story->>Inst: Call instrumented function
    Inst->>Inst: Check intercept conditions
    
    alt Is Debugging and Interceptable
        Inst->>Inst: Create Promise
        Inst->>Channel: Emit CALL event
        Inst-->>Story: Return Promise
        Note over Inst,Story: Function execution paused
        
        Dev->>Channel: Send continue command
        Channel->>Inst: Process control event
        Inst->>Func: Execute original function
        Func-->>Inst: Return result
        Inst->>Channel: Update call status
    else Normal Execution
        Inst->>Func: Execute original function
        Func-->>Inst: Return result
        Inst->>Channel: Emit CALL event
    end
    
    Inst->>Inst: Update state
    Inst-->>Story: Return result
```

## Data Flow

### Call Processing Pipeline

```mermaid
graph LR
    subgraph "Call Processing"
        FC[Function Call]
        CT[Call Tracking]
        SV[Serialize Values]
        II2[Intercept/Invoke]
        UE[Update Events]
        SS2[Sync State]
    end
    
    FC --> CT
    CT --> SV
    SV --> II2
    II2 --> UE
    UE --> SS2
    
    subgraph "Value Serialization"
        SV --> ARR[Arrays]
        SV --> DAT[Dates]
        SV --> ERR[Errors]
        SV --> REG[RegExp]
        SV --> ELE[HTMLElement]
        SV --> FUN[Functions]
        SV --> SYM[Symbols]
        SV --> CLS[Classes]
    end
```

### Debugging Control Flow

```mermaid
stateDiagram-v2
    [*] --> Preparing
    Preparing --> Playing: Start Debugging
    Playing --> Paused: Intercept Call
    Paused --> Playing: Continue/Next
    Playing --> Played: Complete Execution
    Playing --> Errored: Exception Occurred
    Playing --> Aborted: User Abort
    
    Paused --> [*]: End Debugging
    Played --> [*]: Cleanup
    Errored --> [*]: Error Handled
    Aborted --> [*]: State Reset
```

## Key Features

### 1. Dynamic Function Instrumentation

The module can dynamically patch any function to add tracking capabilities:

```typescript
// Functions are wrapped with tracking logic
originalFunction(...args) {
  // Track call metadata
  // Handle interception logic
  // Execute original function
  // Process results and exceptions
  // Update state and emit events
}
```

### 2. Advanced Value Serialization

Complex values are serialized for cross-frame communication:

- **Circular Reference Detection**: Prevents infinite loops
- **Special Object Handling**: Dates, Errors, RegExp, DOM elements
- **Function Serialization**: Preserves function names and mock information
- **Class Instance Tracking**: Maintains constructor information

### 3. Exception Processing

Errors are enhanced with debugging context:

```typescript
exception = {
  name: error.name,
  message: error.message,
  stack: error.stack,
  callId: originatingCallId,
  showDiff: boolean,     // For assertion errors
  diff: string,          // Visual diff for assertions
  actual: unknown,       // Expected value
  expected: unknown      // Actual value
}
```

### 4. Parent Window State Synchronization

State persists across iframe reloads through parent window communication:

```typescript
// State is synchronized with parent window
global.window.parent.__STORYBOOK_ADDON_INTERACTIONS_INSTRUMENTER_STATE__ = state;
```

## Integration Points

### Channel Events

The module communicates through a dedicated event system:

- `EVENTS.START`: Begin debugging session
- `EVENTS.BACK`: Step backward
- `EVENTS.GOTO`: Jump to specific call
- `EVENTS.NEXT`: Step forward
- `EVENTS.END`: End debugging session
- `EVENTS.SYNC`: Synchronize state
- `EVENTS.CALL`: Report function call

### Core Events Integration

Integrates with Storybook's core event system:

- `FORCE_REMOUNT`: Handle story remounting
- `STORY_RENDER_PHASE_CHANGED`: Track render phases
- `SET_CURRENT_STORY`: Handle story switching

## Usage Patterns

### Basic Instrumentation

```typescript
// Instrument an object or module
const instrumented = instrument(obj, {
  intercept: true,        // Enable interception
  retain: false,          // Don't retain after execution
  mutate: false,          // Create new object
  path: [],               // Base path
});
```

### Advanced Configuration

```typescript
// Custom key selection for instrumentation
const instrumented = instrument(obj, {
  getKeys: (obj, depth) => {
    // Custom logic for selecting properties to instrument
    return Object.keys(obj).filter(key => shouldInstrument(key));
  },
  getArgs: (call, state) => {
    // Custom argument processing
    return transformArgs(call.args);
  }
});
```

## Error Handling

### Exception Types

1. **Already Completed Exception**: Thrown when functions run after play completion
2. **Chaining Exceptions**: Errors that bubble up through call chains
3. **Serialization Errors**: Handled gracefully during value processing
4. **Cross-Origin Errors**: Managed when parent window access is restricted

### Error Context Preservation

Errors maintain their originating call context for debugging:

```typescript
// Errors track their source call
if (call.ancestors?.length) {
  Object.defineProperty(e, 'callId', { value: call.id });
  throw e; // Bubble up to parent call
}
```

## Performance Considerations

### Optimization Strategies

1. **Debounced Synchronization**: State sync uses 0ms timeout for batching
2. **Selective Instrumentation**: Only instrumentable objects are processed
3. **Memory Management**: Retained state is cleaned up appropriately
4. **Circular Reference Prevention**: Serialization limits depth and detects cycles

### State Retention

```typescript
// Only retain necessary state
const getRetainedState = (state: State, isDebugging = false) => {
  const calls = (isDebugging ? state.shadowCalls : state.calls)
    .filter((call) => call.retain);
  
  if (!calls.length) {
    return undefined; // No retention needed
  }
  // Return minimal retained state
};
```

## Dependencies

### Internal Dependencies

- **[instrumenter_types](instrumenter_types.md)**: Type definitions and enums
- **[preview_api](preview_api.md)**: Preview integration and channel access
- **[core_events](storybook_configuration.md)**: Event system integration

### External Dependencies

- **storybook/internal/channels**: Event communication
- **storybook/internal/client-logger**: Logging utilities
- **storybook/internal/types**: Core type definitions
- **@storybook/global**: Global object access
- **@vitest/utils/error**: Error processing utilities

## Module Relationships

```mermaid
graph TB
    subgraph "Module Hierarchy"
        IC2[Instrumenter Core]
        
        IC2 --> ICT[instrumenter_types]
        IC2 --> SBC[storybook_configuration]
        IC2 --> PA[preview_api]
        
        SBC --> CE[core_events]
        SBC --> CH3[channels]
        
        PA --> PV[preview-web]
        PA --> WR[WebRenderer]
    end
    
    subgraph "Addon Integration"
        IC2 --> INT[Interactions Addon]
        INT --> MAN[Manager UI]
        INT --> PRE[Preview Integration]
    end
```

This comprehensive documentation provides developers with a deep understanding of the instrumenter_core module's architecture, functionality, and integration points within the Storybook ecosystem.