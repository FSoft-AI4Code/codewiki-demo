# Action Specification Module

The action_specification module defines the fundamental structure and specification of actions within Unity ML-Agents, providing the core data structure that describes the action space available to agents.

## Overview

The action_specification module is a critical component of the Unity ML-Agents actuator system, responsible for defining and managing action space specifications. It provides the `ActionSpec` structure that describes both continuous and discrete action spaces, enabling agents to understand what actions they can perform and how those actions are structured.

## Core Components

### ActionSpec
The primary component that defines the structure of actions available to agents, supporting both continuous and discrete action spaces with flexible configuration options.

## Architecture

```mermaid
graph TB
    subgraph "Action Specification Module"
        AS[ActionSpec]
        AS --> |defines| CA[Continuous Actions]
        AS --> |defines| DA[Discrete Actions]
        AS --> |provides| CF[Creation Factories]
        AS --> |supports| CB[Combination Logic]
    end
    
    subgraph "Integration Points"
        AE[Action Execution Module]
        AI[Action Interfaces Module]
        UC[Unity Runtime Core]
    end
    
    AS --> |used by| AE
    AS --> |implements| AI
    AS --> |integrates with| UC
    
    subgraph "Action Types"
        CA --> |count| NC[NumContinuousActions]
        DA --> |branches| BS[BranchSizes Array]
        DA --> |total| SB[SumOfDiscreteBranchSizes]
    end
```

## Component Details

### ActionSpec Structure

The `ActionSpec` is a serializable struct that encapsulates the complete specification of an agent's action space:

#### Key Properties
- **NumContinuousActions**: Defines the number of continuous actions available
- **BranchSizes**: Array defining discrete action branches and their sizes
- **NumDiscreteActions**: Computed property returning the number of discrete action branches
- **SumOfDiscreteBranchSizes**: Total number of discrete actions across all branches

#### Action Space Types

```mermaid
graph LR
    subgraph "Action Space Types"
        AS[ActionSpec]
        AS --> CT[Continuous Type]
        AS --> DT[Discrete Type]
        AS --> HT[Hybrid Type]
    end
    
    subgraph "Continuous Actions"
        CT --> CA[Float Values]
        CA --> CR[Continuous Range]
    end
    
    subgraph "Discrete Actions"
        DT --> DA[Integer Choices]
        DA --> BR[Branch Structure]
        BR --> BS[Branch Sizes]
    end
    
    subgraph "Hybrid Actions"
        HT --> HC[Continuous + Discrete]
        HC --> VC[Version Compatibility]
    end
```

## Data Flow

```mermaid
sequenceDiagram
    participant Agent as Agent
    participant AS as ActionSpec
    participant Act as Actuator
    participant Env as Environment
    
    Agent->>AS: Request Action Space
    AS->>AS: Define Continuous/Discrete
    AS->>Act: Provide Specification
    Act->>Env: Execute Actions
    Env->>Agent: Return Observations
    
    Note over AS: Validates action space compatibility
    Note over Act: Uses spec for action execution
```

## Factory Methods

The ActionSpec provides static factory methods for creating different types of action specifications:

### Continuous Action Creation
```mermaid
graph TD
    MC[MakeContinuous] --> |input| NA[numActions: int]
    MC --> |creates| CAS[Continuous ActionSpec]
    CAS --> |sets| NCA[NumContinuousActions = numActions]
    CAS --> |sets| BS[BranchSizes = empty array]
```

### Discrete Action Creation
```mermaid
graph TD
    MD[MakeDiscrete] --> |input| BSA["branchSizes: int[]"]
    MD --> |creates| DAS[Discrete ActionSpec]
    DAS --> |sets| NCA["NumContinuousActions = 0"]
    DAS --> |sets| BS["BranchSizes = branchSizes"]
```

## Action Space Combination

The module supports combining multiple ActionSpec instances:

```mermaid
graph TB
    subgraph "Combination Process"
        C[Combine Method]
        C --> |input| SA[ActionSpec Array]
        C --> |process| AC[Aggregate Continuous]
        C --> |process| AD[Aggregate Discrete]
        C --> |output| CAS[Combined ActionSpec]
    end
    
    subgraph "Aggregation Logic"
        AC --> SNC[Sum NumContinuous]
        AD --> SND[Sum NumDiscrete]
        AD --> CBS[Concatenate BranchSizes]
    end
    
    CAS --> |result| FAS[Final ActionSpec]
```

## Integration with Other Modules

### Unity Actuators Integration
- **[action_execution](action_execution.md)**: ActionSpec defines the action space that VectorActuator executes
- **[action_interfaces](action_interfaces.md)**: Provides specification structure for IActionReceiver implementations
- **[action_data_structures](action_data_structures.md)**: ActionSegment uses ActionSpec to understand action layout

### Unity Runtime Core Integration
- **[agent_core](agent_core.md)**: AgentVectorActuator uses ActionSpec to define agent capabilities
- **[decision_management](decision_management.md)**: DecisionRequester considers ActionSpec for decision timing

## Validation and Compatibility

```mermaid
graph TD
    subgraph "Validation Process"
        V[Validation]
        V --> |check| CC[CheckAllContinuousOrDiscrete]
        CC --> |validates| HS[Hybrid Support]
        HS --> |throws| UE[UnityAgentsException]
    end
    
    subgraph "Compatibility Modes"
        CM[Compatibility Mode]
        CM --> |legacy| LC[Legacy Trainers]
        CM --> |modern| MC[Modern Trainers]
        LC --> |requires| SC[Single Action Type]
        MC --> |supports| HA[Hybrid Actions]
    end
```

## Usage Patterns

### Basic Action Space Definition
1. **Continuous Actions**: Use `MakeContinuous(n)` for n-dimensional continuous control
2. **Discrete Actions**: Use `MakeDiscrete(sizes...)` for categorical choices
3. **Custom Construction**: Use constructor for specific configurations

### Multi-Actuator Scenarios
1. **Combination**: Use `Combine()` to merge multiple ActionSpecs
2. **Validation**: Ensure compatibility with target training infrastructure
3. **Integration**: Coordinate with actuator implementations

## Error Handling

The module includes validation for:
- **Hybrid Action Compatibility**: Prevents unsupported mixed action types for legacy trainers
- **Array Bounds**: Ensures proper branch size array handling
- **Null Safety**: Handles null branch size arrays gracefully

## Performance Considerations

- **Struct Design**: Value type for efficient memory usage
- **Array Reuse**: Minimizes allocations through careful array management
- **Lazy Evaluation**: Computed properties calculated on demand
- **Serialization**: Unity-compatible serialization for inspector integration

## Future Extensions

The ActionSpec design supports:
- **New Action Types**: Extensible for future action space types
- **Enhanced Validation**: Additional compatibility checks
- **Optimization**: Performance improvements for large action spaces
- **Metadata**: Additional action space metadata support

This module serves as the foundation for all action-related operations in Unity ML-Agents, providing a robust and flexible specification system that supports diverse agent behaviors and training scenarios.