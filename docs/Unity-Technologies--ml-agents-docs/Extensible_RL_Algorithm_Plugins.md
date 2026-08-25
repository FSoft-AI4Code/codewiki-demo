# Extensible RL Algorithm Plugins

## 1. Purpose

The `Extensible_RL_Algorithm_Plugins` module (`ml-agents-trainer-plugin/mlagents_trainer_plugin`) demonstrates and provides the **out-of-tree plugin mechanism** for adding new reinforcement learning algorithms to the ML-Agents Toolkit without modifying the core `mlagents` package.

It contains two fully-worked example trainer plugins:

- **A2C (Advantage Actor-Critic)** — an on-policy, policy-gradient algorithm.
- **DQN (Deep Q-Network)** — an off-policy, value-based algorithm for discrete action spaces.

Both plugins reuse the core training infrastructure (`Trainer`, `RLTrainer`, `OnPolicyTrainer`/`OffPolicyTrainer`, `TorchOptimizer`, `TorchPolicy`) and the shared neural-network building blocks (`NetworkBody`, `ValueNetwork`, `ValueHeads`, `ModelUtils`, reward-signal providers) documented in the core `ml-agents/mlagents/trainers` package. Each plugin exposes a module-level `get_type_and_setting()` function that is discovered by the core `TrainerFactory`, allowing the trainer type (e.g. `"a2c"`, `"dqn"`) and its settings schema to be registered dynamically at runtime — the canonical pattern for extending ML-Agents with custom algorithms.

## 2. Architecture

### 2.1 Module Composition

```mermaid
graph TB
    subgraph Extensible_RL_Algorithm_Plugins["Extensible_RL_Algorithm_Plugins"]
        subgraph A2C["trainer_plugin_a2c"]
            A2CTrainer["A2CTrainer"]
            A2COptimizer["A2COptimizer"]
            A2CSettings["A2CSettings"]
        end
        subgraph DQN["trainer_plugin_dqn"]
            DQNTrainer["DQNTrainer"]
            DQNOptimizer["DQNOptimizer"]
            QNetwork["QNetwork"]
            DQNSettings["DQNSettings"]
        end
    end

    A2CTrainer -->|creates| A2COptimizer
    A2COptimizer -->|uses| A2CSettings
    DQNTrainer -->|creates| DQNOptimizer
    DQNTrainer -->|passes as actor_cls| QNetwork
    DQNOptimizer -->|uses| DQNSettings
    DQNOptimizer -->|owns target network| QNetwork
```

### 2.2 Integration with Core Training Infrastructure

```mermaid
graph TB
    subgraph Plugins["Extensible_RL_Algorithm_Plugins"]
        A2CTrainer["A2CTrainer"]
        A2COptimizer["A2COptimizer"]
        DQNTrainer["DQNTrainer"]
        DQNOptimizer["DQNOptimizer"]
        QNetwork["QNetwork"]
    end

    subgraph TrainerBase["Training_Orchestration_&_Lifecycle_Infrastructure"]
        TrainerFactory["TrainerFactory"]
        OnPolicyTrainer["OnPolicyTrainer"]
        OffPolicyTrainer["OffPolicyTrainer"]
        RLTrainer["RLTrainer"]
        TorchOptimizer["TorchOptimizer"]
        TorchPolicy["TorchPolicy"]
        AgentBuffer["AgentBuffer / Trajectory"]
        TrainerSettings["TrainerSettings"]
    end

    subgraph NNBlocks["Neural_Network_Building_Blocks"]
        ValueNetwork["ValueNetwork"]
        NetworkBody["NetworkBody"]
        SharedActorCritic["SharedActorCritic / SimpleActor"]
        ModelUtils["ModelUtils"]
        RewardProviders["Reward Signal Providers"]
    end

    TrainerFactory -->|discovers via get_type_and_setting| A2CTrainer
    TrainerFactory -->|discovers via get_type_and_setting| DQNTrainer

    A2CTrainer -->|extends| OnPolicyTrainer
    DQNTrainer -->|extends| OffPolicyTrainer
    OnPolicyTrainer -->|extends| RLTrainer
    OffPolicyTrainer -->|extends| RLTrainer

    A2COptimizer -->|extends| TorchOptimizer
    DQNOptimizer -->|extends| TorchOptimizer

    A2CTrainer -->|creates| TorchPolicy
    DQNTrainer -->|creates| TorchPolicy

    A2CSettings -.->|extends| TrainerSettings
    DQNSettings -.->|extends| TrainerSettings

    A2COptimizer -->|uses| ValueNetwork
    QNetwork -->|delegates to| ValueNetwork
    ValueNetwork --> NetworkBody
    A2CTrainer -->|configures| SharedActorCritic

    A2COptimizer -->|uses| ModelUtils
    DQNOptimizer -->|uses| ModelUtils
    A2CTrainer -->|reads via| AgentBuffer
    DQNTrainer -->|reads via| AgentBuffer

    A2CTrainer -->|evaluates| RewardProviders
    DQNOptimizer -->|updates| RewardProviders
```

### 2.3 Plugin Registration Flow

```mermaid
sequenceDiagram
    participant TF as TrainerFactory
    participant A2C as trainer_plugin_a2c
    participant DQN as trainer_plugin_dqn

    TF->>A2C: discover get_type_and_setting()
    A2C-->>TF: {"a2c": A2CTrainer}, {"a2c": A2CSettings}
    TF->>DQN: discover get_type_and_setting()
    DQN-->>TF: {"dqn": DQNTrainer}, {"dqn": DQNSettings}
    TF->>TF: register trainer types & settings schemas
    Note over TF: Trainers become selectable via run config (trainer_type: a2c / dqn)
```

## 3. Sub-modules & Core Components

| Sub-module | Path | Core Components | Summary |
|---|---|---|---|
| **trainer_plugin_a2c** | `ml-agents-trainer-plugin/mlagents_trainer_plugin/a2c` | `A2CTrainer`, `A2COptimizer`, `A2CSettings` | On-policy Advantage Actor-Critic algorithm; single-epoch policy-gradient update with GAE, optional shared actor-critic network, and aggregated multi-reward-signal advantages/returns. Extends `OnPolicyTrainer` / `TorchOptimizer`. |
| **trainer_plugin_dqn** | `ml-agents-trainer-plugin/mlagents_trainer_plugin/dqn` | `QNetwork`, `DQNOptimizer`, `DQNSettings`, `DQNTrainer` | Off-policy Deep Q-Network algorithm for discrete actions; combined actor/critic `QNetwork`, epsilon-greedy exploration, Double-DQN-style target computation with soft target updates. Extends `OffPolicyTrainer` / `TorchOptimizer`. |

### References

- [trainer_plugin_a2c](trainer_plugin_a2c.md) — Advantage Actor-Critic plugin implementation.
- [trainer_plugin_dqn](trainer_plugin_dqn.md) — Deep Q-Network plugin implementation.
- [Training_Orchestration_&_Lifecycle_Infrastructure](trainers_core.md) — `Trainer`, `RLTrainer`, `TrainerFactory`, settings schema, and data pipeline consumed by both plugins.
- [Neural_Network_Building_Blocks](trainers_torch_entities_networks.md) — shared network components (`NetworkBody`, `ValueNetwork`, `ValueHeads`, `ModelUtils`, reward signal providers) used by both algorithms.
- [Built-in_RL_Algorithms](trainers_ppo.md) — PPO/SAC/POCA implementations that serve as the architectural reference the plugins mirror.