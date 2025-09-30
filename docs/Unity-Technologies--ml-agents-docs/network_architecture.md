# Network Architecture Module

The network_architecture module is the core neural network infrastructure of the ML-Agents training system, providing the fundamental building blocks for deep reinforcement learning models. This module implements the SharedActorCritic architecture and supporting network components that enable agents to learn from observations and generate actions.

## Overview

The network_architecture module serves as the neural network backbone for ML-Agents training algorithms, implementing actor-critic architectures with support for:

- **Multi-modal observation processing** through flexible encoder systems
- **Hybrid action spaces** supporting both continuous and discrete actions  
- **Memory-augmented networks** with LSTM support for partially observable environments
- **Multi-agent coordination** through attention mechanisms
- **Value function approximation** for reinforcement learning algorithms

This module integrates closely with the [training_algorithms](training_algorithms.md) module to provide the neural network foundations for PPO, SAC, and POCA trainers, while leveraging components from [unity_sensors](unity_sensors.md) for observation processing and [unity_actuators](unity_actuators.md) for action generation.

## Architecture Overview

```mermaid
graph TB
    subgraph "Network Architecture Module"
        SAC[SharedActorCritic]
        OE[ObservationEncoder]
        NB[NetworkBody]
        AM[ActionModel]
        VH[ValueHeads]
        
        subgraph "Supporting Components"
            SA[SimpleActor]
            VN[ValueNetwork]
            MANB[MultiAgentNetworkBody]
        end
        
        subgraph "Base Components"
            LSTM[LSTM Memory]
            LE[LinearEncoder]
            CE[ConditionalEncoder]
        end
    end
    
    subgraph "External Dependencies"
        US[Unity Sensors]
        UA[Unity Actuators]
        TA[Training Algorithms]
        TI[Training Infrastructure]
    end
    
    SAC --> OE
    SAC --> NB
    SAC --> AM
    SAC --> VH
    
    NB --> OE
    NB --> LE
    NB --> CE
    NB --> LSTM
    
    OE --> US
    AM --> UA
    SAC --> TA
    
    VN --> NB
    VN --> VH
    SA --> NB
    SA --> AM
    
    MANB --> OE
    MANB --> LSTM
    
    SAC --> TI
```

## Core Components

### SharedActorCritic

The `SharedActorCritic` class is the primary network architecture that combines both actor and critic functionality in a single network with shared parameters.

**Key Features:**
- **Shared Encoding**: Uses a common network body to encode observations for both policy and value estimation
- **Dual Functionality**: Implements both Actor and Critic interfaces for complete RL functionality
- **Memory Support**: Integrates LSTM memory for handling partially observable environments
- **Multi-stream Values**: Supports multiple value streams for different reward signals

**Architecture Flow:**
```mermaid
graph LR
    subgraph "SharedActorCritic"
        Obs[Observations] --> NB[NetworkBody]
        NB --> Encoding[Shared Encoding]
        
        Encoding --> AM[ActionModel]
        Encoding --> VH[ValueHeads]
        
        AM --> Actions[Actions & Log Probs]
        VH --> Values[Value Estimates]
    end
    
    subgraph "NetworkBody Components"
        OE[ObservationEncoder]
        BodyEncoder[Body Encoder]
        LSTM[LSTM Memory]
        
        OE --> BodyEncoder
        BodyEncoder --> LSTM
    end
```

### ObservationEncoder

The `ObservationEncoder` processes diverse observation types into unified tensor representations.

**Capabilities:**
- **Multi-modal Processing**: Handles vector, visual, and variable-length observations
- **Attention Mechanisms**: Uses Residual Self-Attention (RSA) for variable-length inputs
- **Goal Conditioning**: Special handling for goal-conditioned observations
- **Normalization**: Optional input normalization for stable training

**Processing Pipeline:**
```mermaid
graph TD
    subgraph "Observation Processing"
        Obs[Raw Observations] --> Proc[Input Processors]
        Proc --> Fixed[Fixed-Length Encodings]
        Proc --> VarLen[Variable-Length Inputs]
        
        VarLen --> EE[Entity Embedding]
        EE --> RSA[Residual Self-Attention]
        
        Fixed --> Concat[Concatenation]
        RSA --> Concat
        
        Concat --> Output[Encoded Observations]
    end
    
    subgraph "Processor Types"
        VI[Vector Input]
        CS[Camera Sensor]
        RPS[Ray Perception]
        BS[Buffer Sensor]
    end
    
    VI --> Proc
    CS --> Proc
    RPS --> Proc
    BS --> Proc
```

### NetworkBody

The `NetworkBody` serves as the core encoding infrastructure that processes observations and optional actions into feature representations.

**Components:**
- **Observation Encoding**: Integrates ObservationEncoder for multi-modal input processing
- **Conditional Encoding**: Supports goal-conditioned policies through ConditionalEncoder
- **Memory Integration**: Optional LSTM for temporal dependencies
- **Action Conditioning**: Can incorporate previous actions for improved learning

### ActionModel

The `ActionModel` generates actions from network encodings, supporting both continuous and discrete action spaces.

**Action Generation Flow:**
```mermaid
graph LR
    subgraph "ActionModel"
        Encoding[Network Encoding] --> Dists[Distribution Parameters]
        
        Dists --> ContDist[Continuous Distribution]
        Dists --> DiscDist[Discrete Distribution]
        
        ContDist --> ContActions[Continuous Actions]
        DiscDist --> DiscActions[Discrete Actions]
        
        ContActions --> AgentAction[AgentAction]
        DiscActions --> AgentAction
        
        AgentAction --> LogProbs[Log Probabilities]
        AgentAction --> Entropy[Entropy]
    end
```

## Multi-Agent Support

### MultiAgentNetworkBody

The `MultiAgentNetworkBody` extends the standard architecture to handle variable numbers of agents through attention mechanisms.

**Key Features:**
- **Variable Agent Count**: Handles dynamic numbers of agents in the environment
- **Self-Attention**: Uses attention mechanisms to process agent interactions
- **Shared Parameters**: All agents share the same network parameters
- **Scalable Architecture**: Efficiently scales to large numbers of agents

**Multi-Agent Processing:**
```mermaid
graph TD
    subgraph "Multi-Agent Processing"
        Agents[Multiple Agents] --> ObsEnc[Observation Encoding]
        ObsEnc --> EntEmb[Entity Embedding]
        
        EntEmb --> SelfAttn[Self-Attention]
        SelfAttn --> AgentEnc[Agent Encodings]
        
        AgentEnc --> LinearEnc[Linear Encoder]
        LinearEnc --> Output[Final Encoding]
        
        subgraph "Attention Mechanism"
            Masks[Attention Masks]
            QKV[Query-Key-Value]
            
            Masks --> SelfAttn
            QKV --> SelfAttn
        end
    end
```

## Memory and Temporal Processing

### LSTM Integration

The module supports memory-augmented networks through LSTM integration for handling partially observable environments.

**Memory Architecture:**
```mermaid
graph LR
    subgraph "Memory Processing"
        Input[Input Sequence] --> LSTM[LSTM Layer]
        Memory[Previous Memory] --> LSTM
        
        LSTM --> Output[Output Sequence]
        LSTM --> NewMemory[Updated Memory]
        
        subgraph "Memory State"
            Hidden[Hidden State]
            Cell[Cell State]
            
            Hidden --> Memory
            Cell --> Memory
        end
    end
```

## Value Function Architecture

### ValueHeads

The `ValueHeads` component implements multiple value function heads for different reward streams.

**Multi-Stream Values:**
```mermaid
graph TD
    subgraph "Value Function Architecture"
        Encoding[Shared Encoding] --> VH[ValueHeads]
        
        VH --> Extrinsic[Extrinsic Value]
        VH --> Curiosity[Curiosity Value]
        VH --> GAIL[GAIL Value]
        VH --> Custom[Custom Streams]
        
        subgraph "Value Processing"
            Linear[Linear Layers]
            Activation[Activation Functions]
            
            Linear --> Activation
        end
    end
```

## Integration with Training System

### Training Algorithm Integration

The network architecture integrates seamlessly with the training algorithms:

```mermaid
graph TB
    subgraph "Training Integration"
        Trainer[RL Trainer] --> Policy[Policy]
        Policy --> SAC[SharedActorCritic]
        
        SAC --> Forward[Forward Pass]
        Forward --> Actions[Action Generation]
        Forward --> Values[Value Estimation]
        
        Actions --> Env[Environment]
        Values --> Loss[Loss Computation]
        
        Loss --> Optimizer[Optimizer]
        Optimizer --> Updates[Parameter Updates]
        Updates --> SAC
    end
```

### Data Flow

The complete data flow through the network architecture:

```mermaid
sequenceDiagram
    participant Env as Environment
    participant Obs as Observations
    participant Net as Network
    participant Act as Actions
    participant Train as Training
    
    Env->>Obs: Raw Observations
    Obs->>Net: Processed Inputs
    Net->>Net: Encode Observations
    Net->>Net: Generate Actions
    Net->>Net: Estimate Values
    Net->>Act: Action Outputs
    Act->>Env: Environment Actions
    Net->>Train: Values & Log Probs
    Train->>Net: Gradient Updates
```

## Configuration and Settings

The network architecture is configured through the [configuration_system](configuration_system.md) module:

- **NetworkSettings**: Defines architecture parameters (hidden units, layers, memory)
- **EncoderType**: Specifies visual encoder types (CNN, ResNet, etc.)
- **ConditioningType**: Controls goal conditioning mechanisms
- **Memory Settings**: Configures LSTM memory parameters

## Performance Considerations

### Optimization Features

- **Parameter Sharing**: Efficient memory usage through shared encoders
- **Attention Mechanisms**: Scalable processing for variable-length inputs
- **Gradient Clipping**: Stable training through action and gradient clipping
- **Normalization**: Input normalization for training stability

### Scalability

- **Multi-Agent Support**: Efficient scaling to hundreds of agents
- **Memory Management**: Optimized memory usage for large networks
- **Batch Processing**: Efficient batch processing for training throughput

## Export and Deployment

The network architecture supports model export for deployment:

- **ONNX Export**: Compatible with Unity's Sentis inference engine
- **Version Management**: Model versioning for compatibility
- **Deterministic Inference**: Support for deterministic action selection

## Dependencies

The network_architecture module depends on several other modules:

- **[unity_sensors](unity_sensors.md)**: For observation processing components
- **[unity_actuators](unity_actuators.md)**: For action space definitions
- **[training_infrastructure](training_infrastructure.md)**: For optimization components
- **[configuration_system](configuration_system.md)**: For network settings

## Usage Examples

### Basic Actor-Critic Setup

```python
# Create SharedActorCritic network
network = SharedActorCritic(
    observation_specs=obs_specs,
    network_settings=network_settings,
    action_spec=action_spec,
    stream_names=["extrinsic"]
)

# Forward pass for training
action, stats, memories = network.get_action_and_stats(
    inputs=observations,
    memories=previous_memories
)

# Value estimation
values, critic_memories = network.critic_pass(
    inputs=observations,
    memories=previous_memories
)
```

### Multi-Agent Configuration

```python
# Multi-agent network body
ma_network = MultiAgentNetworkBody(
    observation_specs=obs_specs,
    network_settings=network_settings,
    action_spec=action_spec
)

# Process multiple agents
encoding, memories = ma_network(
    obs_only=observations_only,
    obs=observations_with_actions,
    actions=agent_actions,
    memories=previous_memories
)
```

This network architecture module provides the foundational neural network infrastructure that enables ML-Agents to learn complex behaviors across diverse environments and agent configurations.