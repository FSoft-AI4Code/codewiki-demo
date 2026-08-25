# Python Environment Interface Layer

## 1. Purpose

The `Python_Environment_Interface_Layer` module (`mlagents_envs`) is the Python-side gateway to a running Unity ML-Agents simulation. It provides:

- A **stable public API** (`UnityEnvironment`, `BaseEnv`, `DecisionSteps`/`TerminalSteps`, `ActionTuple`) for stepping, resetting, and exchanging observations/actions with Unity.
- The **transport layer** (gRPC-based `RpcCommunicator` and generated protobuf stubs) that physically carries messages between the Python process and the Unity executable/editor.
- **Side channels** for out-of-band data exchange (engine configuration, environment parameters, statistics, analytics) that runs alongside the main RL step loop.
- **Third-party ecosystem adapters** (OpenAI Gym, PettingZoo) that expose Unity environments through standardized RL interfaces.
- A **registry** of pre-built, downloadable Unity environments for quick experimentation without requiring the Unity Editor.
- Supporting **utilities** for decoding wire-format data into NumPy arrays and hierarchical performance timing.

This module underpins the entire Python ML-Agents ecosystem: it is consumed directly by the [Training Orchestration & Lifecycle Infrastructure](trainers_core.md) (via `SimpleEnvManager`/`SubprocessEnvManager`) and by external users who want Gym/PettingZoo-compatible access to Unity environments.

## 2. Architecture Overview

```mermaid
graph TB
    subgraph "External Consumers"
        Trainer["mlagents.trainers<br/>(Training Orchestration)"]
        ThirdParty["Third-party RL libraries<br/>(Stable-Baselines3, RLlib, etc.)"]
    end

    subgraph "Python_Environment_Interface_Layer"
        subgraph "envs_core"
            UE["UnityEnvironment / BaseEnv"]
            BE["DecisionSteps / TerminalSteps / ActionTuple"]
            RPC["RpcCommunicator"]
            Utils["rpc_utils / timers"]
        end

        subgraph "envs_wrappers"
            Gym["UnityToGymWrapper"]
            PZ["UnityAECEnv / UnityParallelEnv"]
            Factory["PettingZooEnvFactory"]
        end

        subgraph "envs_sidechannel"
            SCM["SideChannelManager"]
            Channels["EngineConfigurationChannel / EnvironmentParametersChannel /<br/>StatsSideChannel / FloatPropertiesChannel / etc."]
        end

        subgraph "envs_registry"
            Registry["UnityEnvRegistry (default_registry)"]
            Entry["RemoteRegistryEntry"]
        end
    end

    subgraph "Unity Process"
        UnityApp["Unity Simulation<br/>(Academy / Communicator)"]
    end

    Trainer --> UE
    ThirdParty --> Gym
    ThirdParty --> PZ
    Gym --> UE
    PZ --> UE
    Factory --> Registry
    Factory --> PZ
    Registry --> Entry
    Entry --> UE
    UE --> BE
    UE --> RPC
    UE --> SCM
    SCM --> Channels
    UE -.profiling.-> Utils
    RPC <--gRPC--> UnityApp

    style UE fill:#f9f,stroke:#333,stroke-width:2px
```

### Step-cycle interaction

```mermaid
sequenceDiagram
    participant Client as Trainer / Wrapper
    participant UE as UnityEnvironment
    participant SC as SideChannelManager
    participant RPC as RpcCommunicator
    participant Unity as Unity Process

    Client->>UE: set_actions(behavior, ActionTuple)
    Client->>UE: step()
    UE->>SC: generate_side_channel_messages()
    UE->>RPC: exchange(UnityInputProto)
    RPC->>Unity: gRPC message
    Unity-->>RPC: gRPC response
    RPC-->>UE: UnityOutputProto
    UE->>UE: rpc_utils.steps_from_proto()
    UE->>SC: process_side_channel_message()
    Client->>UE: get_steps(behavior) -> DecisionSteps, TerminalSteps
```

## 3. Sub-modules

| Sub-module | Description | Documentation |
|---|---|---|
| **envs_core** | Foundational API (`UnityEnvironment`, `BaseEnv`, `DecisionSteps`/`TerminalSteps`), the gRPC communication transport (`RpcCommunicator`, generated protobuf stubs, `MockCommunicator`), and supporting utilities (protobuf→NumPy decoding, hierarchical timers). | [envs_core.md](envs_core.md) |
| **envs_wrappers** | Adapters exposing `BaseEnv` as OpenAI Gym (`UnityToGymWrapper`) and PettingZoo (`UnityAECEnv`, `UnityParallelEnv`, `PettingZooEnvFactory`) compatible environments. | [envs_wrappers.md](envs_wrappers.md) |
| **envs_registry** | Catalog of pre-built, downloadable Unity environments (`UnityEnvRegistry`, `RemoteRegistryEntry`, `default_registry`) enabling environment creation without the Unity Editor. | [envs_registry.md](envs_registry.md) |
| **envs_sidechannel** | Out-of-band messaging framework (`SideChannel`, `IncomingMessage`, `OutgoingMessage`, `SideChannelManager`) plus built-in channels for engine config, environment parameters, stats, and analytics. | [envs_sidechannel.md](envs_sidechannel.md) |

## 4. Relationship to Other Modules

- **[Training_Orchestration_&_Lifecycle_Infrastructure](trainers_core.md)** — drives `UnityEnvironment` instances directly through `SimpleEnvManager`/`SubprocessEnvManager` during RL training loops, and reuses `DefaultTrainingAnalyticsSideChannel` for analytics reporting.
- **[Unity-Python_Bridge_&_ML_Integration](runtime_communicator.md)** — the C# counterpart (`Academy`, `Communicator`, C# `SideChannels`) implements the matching wire protocol that this module's `RpcCommunicator` and side channels communicate with over gRPC.
- **External RL ecosystems** — via `envs_wrappers`, this module is the primary integration surface for Gym- and PettingZoo-based training tools outside of the native `mlagents_envs`/`mlagents.trainers` stack.

## 5. Key Design Points

- **Batched, behavior-grouped data model**: `DecisionSteps`/`TerminalSteps` group all agents sharing a `BehaviorName` for efficient vectorized processing.
- **Version-gated compatibility**: API and capability negotiation with the connected Unity build fails fast on incompatible versions.
- **Pluggable transport**: `RpcCommunicator` (production) and `MockCommunicator` (testing) are interchangeable behind the `Communicator` abstraction.
- **Out-of-band side channels**: auxiliary data (config, parameters, stats, analytics) is multiplexed over the same connection without polluting the core observation/action loop.
- **Decoupled ecosystem adapters**: Gym/PettingZoo wrappers and the environment registry depend only on the small, stable `BaseEnv` surface, keeping them independent from low-level gRPC/transport details.