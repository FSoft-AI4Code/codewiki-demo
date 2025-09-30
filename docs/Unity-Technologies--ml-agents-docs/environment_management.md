# Environment Management Module

The environment_management module is a critical component of the ML-Agents training system that manages the interaction between training environments and the training process. It provides an abstraction layer for handling multiple environments, coordinating agent actions, and processing environment steps during training.

## Overview

This module serves as the bridge between Unity environments and the training algorithms, managing the flow of observations, actions, and rewards. It handles environment lifecycle management, policy updates, and agent experience collection in a structured and efficient manner.

## Architecture

```mermaid
graph TB
    subgraph "Environment Management Layer"
        EM[EnvManager<br/>Abstract Base]
        SEM[SimpleEnvManager<br/>Concrete Implementation]
        ES[EnvironmentStep<br/>Data Structure]
    end
    
    subgraph "External Dependencies"
        BE[BaseEnv<br/>Unity Environment]
        POL[Policy<br/>Decision Making]
        AM[AgentManager<br/>Experience Processing]
        EPC[EnvironmentParametersChannel<br/>Configuration]
    end
    
    subgraph "Training System"
        TR[Trainer]
        AS[ActionInfo]
        TS[TrainerSettings]
    end
    
    EM --> SEM
    SEM --> BE
    SEM --> EPC
    EM --> POL
    EM --> AM
    EM --> ES
    
    TR --> EM
    EM --> AS
    TR --> TS
    
    style EM fill:#e1f5fe
    style SEM fill:#f3e5f5
    style ES fill:#fff3e0
```

## Core Components

### EnvManager (Abstract Base Class)

The `EnvManager` is an abstract base class that defines the interface for environment management. It provides the core functionality for:

- **Policy Management**: Maintains a registry of policies for different behavior types
- **Agent Management**: Coordinates with AgentManager instances for experience processing
- **Environment Lifecycle**: Handles environment reset and step operations
- **Parameter Configuration**: Manages environment parameter updates

#### Key Responsibilities

```mermaid
graph LR
    subgraph "EnvManager Responsibilities"
        PM[Policy<br/>Management]
        AM[Agent<br/>Management]
        EL[Environment<br/>Lifecycle]
        PC[Parameter<br/>Configuration]
        SP[Step<br/>Processing]
    end
    
    PM --> |Updates| POL[Policies]
    AM --> |Coordinates| AGM[AgentManagers]
    EL --> |Controls| ENV[Environments]
    PC --> |Configures| PAR[Parameters]
    SP --> |Processes| STEP[EnvironmentSteps]
    
    style PM fill:#e8f5e8
    style AM fill:#fff2e8
    style EL fill:#e8e8ff
    style PC fill:#ffe8e8
    style SP fill:#f0e8ff
```

#### Core Methods

- `set_policy()`: Associates a policy with a behavior name
- `set_agent_manager()`: Registers an agent manager for a behavior
- `reset()`: Resets environments and prepares for new episodes
- `get_steps()`: Retrieves and processes environment steps
- `process_steps()`: Processes step information through agent managers

### SimpleEnvManager (Concrete Implementation)

The `SimpleEnvManager` is a concrete implementation designed for single-environment scenarios, primarily used for testing and development.

#### Features

```mermaid
graph TD
    subgraph "SimpleEnvManager Features"
        SE[Single Environment<br/>Management]
        SS[Synchronous<br/>Step Processing]
        PC[Parameter<br/>Configuration]
        AS[Action<br/>Synchronization]
    end
    
    subgraph "Implementation Details"
        PS[Previous Step<br/>Tracking]
        AI[Action Info<br/>Management]
        SR[Step Result<br/>Generation]
    end
    
    SE --> PS
    SS --> AI
    PC --> EPC[EnvironmentParametersChannel]
    AS --> SR
    
    style SE fill:#e1f5fe
    style SS fill:#f3e5f5
    style PC fill:#fff3e0
    style AS fill:#e8f5e8
```

#### Key Characteristics

- **Single Environment**: Manages only one BaseEnv instance
- **Synchronous Operation**: Processes steps sequentially
- **Testing Focus**: Optimized for development and testing scenarios
- **Parameter Management**: Handles environment parameter updates via side channels

### EnvironmentStep (Data Structure)

The `EnvironmentStep` is a named tuple that encapsulates all information from a single environment step.

#### Structure

```mermaid
graph LR
    subgraph "EnvironmentStep Components"
        ASR[current_all_step_result<br/>Step Results Dict]
        WID[worker_id<br/>int]
        BAI[brain_name_to_action_info<br/>Action Info Dict]
        ES[environment_stats<br/>EnvironmentStats]
    end
    
    subgraph "Step Result Contents"
        DS[DecisionSteps]
        TS[TerminalSteps]
    end
    
    ASR --> DS
    ASR --> TS
    
    style ASR fill:#e1f5fe
    style WID fill:#f3e5f5
    style BAI fill:#fff3e0
    style ES fill:#e8f5e8
```

## Data Flow

```mermaid
sequenceDiagram
    participant T as Trainer
    participant EM as EnvManager
    participant P as Policy
    participant AM as AgentManager
    participant E as Environment
    
    T->>EM: get_steps()
    EM->>P: get_action(decision_steps)
    P-->>EM: ActionInfo
    EM->>E: set_actions() & step()
    E-->>EM: DecisionSteps & TerminalSteps
    EM->>EM: Create EnvironmentStep
    EM-->>T: List[EnvironmentStep]
    
    T->>EM: process_steps(step_infos)
    EM->>AM: add_experiences()
    EM->>AM: record_environment_stats()
    AM-->>EM: Processing complete
    EM-->>T: Number of processed steps
```

## Integration with Other Modules

### Dependencies

- **[python_environment](python_environment.md)**: Interfaces with BaseEnv for Unity environment communication
- **[policy_system](policy_system.md)**: Utilizes Policy instances for agent decision making
- **[trainer_abstractions](trainer_abstractions.md)**: Integrates with Trainer and AgentManager components
- **[python_side_channels](python_side_channels.md)**: Uses EnvironmentParametersChannel for configuration

### Relationships

```mermaid
graph TB
    subgraph "Environment Management"
        EM[EnvManager]
        SEM[SimpleEnvManager]
    end
    
    subgraph "Training Core"
        T[Trainer]
        AM[AgentManager]
        P[Policy]
    end
    
    subgraph "Environment Layer"
        BE[BaseEnv]
        EPC[EnvironmentParametersChannel]
    end
    
    subgraph "Data Structures"
        ES[EnvironmentStep]
        AI[ActionInfo]
        TS[TrainerSettings]
    end
    
    T --> EM
    EM --> P
    EM --> AM
    SEM --> BE
    SEM --> EPC
    EM --> ES
    EM --> AI
    T --> TS
    
    style EM fill:#e1f5fe
    style SEM fill:#f3e5f5
    style T fill:#fff3e0
    style BE fill:#e8f5e8
```

## Process Flow

### Environment Step Processing

```mermaid
flowchart TD
    Start([Start Training Step]) --> FI{First Step<br/>After Reset?}
    FI -->|Yes| PFS[Process First<br/>Step Infos]
    FI -->|No| UPQ[Update Policy<br/>Queue]
    PFS --> UPQ
    
    UPQ --> GPQ{Get Policy from<br/>Queue}
    GPQ -->|Policy Available| SP[Set Policy]
    GPQ -->|Queue Empty| SE[Step Environment]
    SP --> SE
    
    SE --> GAS[Get All Step<br/>Results]
    GAS --> CES[Create Environment<br/>Steps]
    CES --> RES[Return Environment<br/>Steps]
    
    RES --> PS[Process Steps]
    PS --> AE[Add Experiences<br/>to AgentManager]
    AE --> RES_STATS[Record Environment<br/>Statistics]
    RES_STATS --> End([End])
    
    style Start fill:#e8f5e8
    style End fill:#ffe8e8
    style FI fill:#fff3e0
    style SE fill:#e1f5fe
    style PS fill:#f3e5f5
```

### Environment Reset Process

```mermaid
flowchart TD
    Reset([Reset Request]) --> EE[End Episodes for<br/>All AgentManagers]
    EE --> SEP[Set Environment<br/>Parameters]
    SEP --> RE[Reset Environment]
    RE --> GIR[Get Initial<br/>Results]
    GIR --> SFS[Save First<br/>Step Infos]
    SFS --> RC[Return Environment<br/>Count]
    
    style Reset fill:#e8f5e8
    style RC fill:#ffe8e8
    style SEP fill:#fff3e0
    style RE fill:#e1f5fe
```

## Configuration and Parameters

### Environment Parameters

The module supports dynamic environment parameter configuration through the EnvironmentParametersChannel:

- **Float Parameters**: Numerical configuration values
- **Randomization Settings**: Parameter randomization for curriculum learning
- **Runtime Updates**: Dynamic parameter changes during training

### Training Integration

```mermaid
graph LR
    subgraph "Configuration Flow"
        TS[TrainerSettings] --> EM[EnvManager]
        EM --> EPC[EnvironmentParametersChannel]
        EPC --> UE[Unity Environment]
    end
    
    subgraph "Parameter Types"
        FP[Float Parameters]
        RS[Randomization Settings]
        CC[Curriculum Config]
    end
    
    TS --> FP
    TS --> RS
    TS --> CC
    
    style TS fill:#e1f5fe
    style EM fill:#f3e5f5
    style EPC fill:#fff3e0
    style UE fill:#e8f5e8
```

## Performance Considerations

### Single Environment Limitations

The SimpleEnvManager is designed for single-environment scenarios and has inherent limitations:

- **Sequential Processing**: No parallel environment execution
- **Limited Scalability**: Not suitable for production training with multiple environments
- **Testing Focus**: Optimized for development and debugging rather than performance

### Memory Management

- **Step Information Caching**: Maintains previous step information for action generation
- **Policy Queue Management**: Handles policy updates without blocking environment steps
- **Agent Memory**: Coordinates with AgentManager for experience storage

## Error Handling and Logging

The module includes comprehensive error handling and logging:

- **Missing Agent Managers**: Warns when agent managers are not created for behavior IDs
- **Policy Queue Management**: Handles empty policy queues gracefully
- **Environment Statistics**: Processes and forwards environment statistics to reporting systems

## Usage Patterns

### Basic Environment Management

```python
# Create environment manager
env_manager = SimpleEnvManager(env, env_params_channel)

# Set up policies and agent managers
env_manager.set_policy(behavior_name, policy)
env_manager.set_agent_manager(behavior_name, agent_manager)

# Training loop
while training:
    # Get environment steps
    step_infos = env_manager.get_steps()
    
    # Process steps
    num_steps = env_manager.process_steps(step_infos)
    
    # Training logic here...
```

### Environment Reset and Configuration

```python
# Reset with configuration
config = {"parameter_name": 1.0}
num_envs = env_manager.reset(config)

# Update parameters during training
env_manager.set_env_parameters(new_config)
```

## Future Considerations

The environment_management module is designed to be extensible:

- **Multi-Environment Support**: The abstract EnvManager allows for implementations that handle multiple environments
- **Asynchronous Processing**: Future implementations could support asynchronous environment stepping
- **Advanced Parameter Management**: Enhanced support for complex parameter randomization and curriculum learning

This module forms a crucial part of the ML-Agents training pipeline, providing the necessary abstraction and coordination between environments and training algorithms while maintaining flexibility for different deployment scenarios.