# Trainers Torch Components

## Purpose

The **Trainers Torch Components** module provides pluggable, self-contained PyTorch building blocks that extend the
core RL training loop with auxiliary learning signals and imitation-learning support. It sits on top of the generic
neural-network primitives defined in [Neural Network Building Blocks](trainers_torch_entities.md) and is consumed by
the RL algorithm optimizers in [Built-in RL Algorithms](trainers_ppo.md) (PPO, SAC, POCA) as well as by the generic
training infrastructure in [Training Orchestration & Lifecycle Infrastructure](trainers_core.md).

Concretely, the module contains two families of components:

1. **Behavioral Cloning (`BCModule`)** — an inline pretrainer/regularizer that clones expert demonstrations into the
   policy being trained, usable alongside any RL optimizer.
2. **Reward Providers** — a family of `BaseRewardProvider` implementations (`Extrinsic`, `Curiosity`, `GAIL`, `RND`)
   that compute additional or replacement reward signals from batches of experience. These are aggregated by
   `TorchOptimizer` (see [trainers_optimizer](trainers_optimizer.md)) to form the total training reward.

Both families are designed to be attached to a `TorchPolicy` (see [trainers_policy](trainers_policy.md)) and operate
on `AgentBuffer` mini-batches (see [trainers_core_data_pipeline](trainers_core_data_pipeline.md)), making them
interchangeable, composable extensions rather than hard-coded parts of any single trainer.

## Architecture Overview

```mermaid
graph TB
    subgraph "trainers_torch_components"
        BC[BCModule]
        BASE[BaseRewardProvider]
        EXT[ExtrinsicRewardProvider]
        CUR[CuriosityRewardProvider / CuriosityNetwork]
        GAIL[GAILRewardProvider / DiscriminatorNetwork]
        RND[RNDRewardProvider / RNDNetwork]

        BASE --> EXT
        BASE --> CUR
        BASE --> GAIL
        BASE --> RND
    end

    subgraph "trainers_policy"
        POLICY[TorchPolicy]
    end

    subgraph "trainers_optimizer"
        OPT[TorchOptimizer]
    end

    subgraph "trainers_torch_entities"
        NB[NetworkBody]
        AF[ActionFlattener]
        AA[AgentAction]
        ALP[ActionLogProbs]
        MU[ModelUtils]
    end

    subgraph "trainers_core_data_pipeline"
        AB[AgentBuffer]
        OU[ObsUtil]
    end

    subgraph "trainers_core_config"
        SET[Settings: BehavioralCloningSettings, CuriositySettings, GAILSettings, RNDSettings, RewardSignalSettings]
    end

    OPT -->|instantiates & aggregates| BASE
    OPT -->|instantiates| BC
    BC --> POLICY
    CUR --> NB
    GAIL --> NB
    RND --> NB
    CUR --> AF
    GAIL --> AF
    BC --> AA
    BC --> ALP
    BASE --> AB
    CUR --> OU
    GAIL --> OU
    RND --> OU
    BC --> MU
    CUR --> MU
    GAIL --> MU
    RND --> MU
    BC -.config.-> SET
    CUR -.config.-> SET
    GAIL -.config.-> SET
    RND -.config.-> SET
```

## Sub-modules

| Sub-module | Description | Documentation |
|---|---|---|
| Behavioral Cloning | Inline imitation-learning module that fine-tunes the policy's actor towards expert demonstrations while RL training proceeds. | Documented below (single-file module) |
| Reward Providers | Family of auxiliary/alternative reward computation modules (Extrinsic, Curiosity, GAIL, RND) sharing a common `BaseRewardProvider` interface. | [trainers_torch_components_reward_providers.md](trainers_torch_components_reward_providers.md) |

---

## Behavioral Cloning: `BCModule`

### Purpose

`BCModule` (`ml-agents/mlagents/trainers/torch_entities/components/bc/module.py`) implements **inline behavioral
cloning**: it periodically nudges the policy's actor network towards actions recorded in expert demonstration data,
independent of (and concurrently with) the primary RL loss. This is used to speed up learning or bias the policy
towards known-good behavior, controlled by `BehavioralCloningSettings` (see
[trainers_core_config_settings](trainers_core_config_settings.md)).

### Responsibilities

- Loads a demonstration buffer via `demo_to_buffer` from the configured `demo_path`.
- Maintains its own Adam optimizer over `policy.actor.parameters()`, separate from the main RL optimizer.
- Anneals its learning rate over `settings.steps` using `ModelUtils.DecayedValue` (linear or constant schedule), from
  [trainers_torch_entities_utils_serialization_utils](trainers_torch_entities_utils_serialization_utils.md).
- On `update()`, repeatedly samples mini-batches from the demonstration buffer, computes a behavioral cloning loss,
  and performs a gradient step on the actor.
- Supports both continuous actions (MSE loss) and discrete actions (cross-entropy against one-hot expert actions).

### Key Interactions

- **`TorchPolicy`**: `BCModule` wraps and mutates the actor of a `TorchPolicy` instance (see
  [trainers_policy](trainers_policy.md)). It queries `policy.behavior_spec`, `policy.sequence_length`,
  `policy.use_recurrent`, and `policy.m_size` to correctly shape observations, action masks, and memories.
- **`AgentBuffer` / `ObsUtil`**: Demonstration data is stored and sampled using the same `AgentBuffer` abstraction
  used by the rest of the trainer stack (see [trainers_core_data_pipeline](trainers_core_data_pipeline.md)).
- **`AgentAction` / `ActionLogProbs`**: Uses the shared action representation and log-prob container types from
  [trainers_torch_entities_actions](trainers_torch_entities_actions.md) to compute the BC loss.
- **`ModelUtils`**: Uses helper functions (`list_to_tensor`, `actions_to_onehot`, `break_into_branches`,
  `update_learning_rate`) from
  [trainers_torch_entities_utils_serialization_utils](trainers_torch_entities_utils_serialization_utils.md).

### Update Flow

```mermaid
sequenceDiagram
    participant Trainer as RL Trainer / Optimizer
    participant BC as BCModule
    participant DemoBuf as Demonstration AgentBuffer
    participant Policy as TorchPolicy.actor

    Trainer->>BC: update()
    BC->>BC: decay_learning_rate.get_value(current_step)
    loop for each epoch
        BC->>DemoBuf: shuffle(sequence_length)
        loop for each mini-batch
            BC->>DemoBuf: make_mini_batch(start, end)
            BC->>Policy: get_action_and_stats(obs, masks, memories)
            Policy-->>BC: selected_actions, log_probs
            BC->>BC: _behavioral_cloning_loss(...)
            BC->>Policy: backward() + optimizer.step()
        end
    end
    BC->>Trainer: {"Losses/Pretraining Loss": mean_loss}
```

### Class Diagram

```mermaid
classDiagram
    class BCModule {
        +TorchPolicy policy
        +float current_lr
        +DecayedValue decay_learning_rate
        +Adam optimizer
        +AgentBuffer demonstration_buffer
        +int batch_size
        +int num_epoch
        +int n_sequences
        +bool has_updated
        +update() Dict~str, ndarray~
        -_behavioral_cloning_loss(selected_actions, log_probs, expert_actions) Tensor
        -_update_batch(mini_batch_demo, n_sequences) Dict~str, float~
    }
    BCModule --> "1" TorchPolicy : drives actor of
```

---

## Relationship to Reward Providers

While `BCModule` directly modifies the policy's actor weights via imitation loss, the **Reward Providers** sub-module
takes a different approach: it computes *reward signals* (intrinsic or from a discriminator) that are fed back into
the standard RL objective (e.g., PPO's advantage estimation) rather than directly updating the actor. Both mechanisms
can be combined for a given behavior (e.g., PPO + GAIL + BC), and both are configured through the settings classes in
[trainers_core_config_settings](trainers_core_config_settings.md) and wired together by the optimizers in
[trainers_optimizer](trainers_optimizer.md) and algorithm-specific optimizers such as
[trainers_ppo](trainers_ppo.md), [trainers_sac](trainers_sac.md), and [trainers_poca](trainers_poca.md).

See [trainers_torch_components_reward_providers.md](trainers_torch_components_reward_providers.md) for full details
on the reward provider implementations.

## Where This Module Fits in the Overall System

```mermaid
graph LR
    ENVS[Unity-Python Bridge & ML Integration / Python Env Interface] --> CORE[trainers_core]
    CORE --> POLICY[trainers_policy]
    POLICY --> OPT[trainers_optimizer]
    OPT --> COMPONENTS[trainers_torch_components]
    COMPONENTS --> ENTITIES[trainers_torch_entities]
    OPT --> ALGOS[trainers_ppo / trainers_sac / trainers_poca]
    ALGOS --> COMPONENTS
```

## Related Documentation

- [trainers_torch_components_reward_providers.md](trainers_torch_components_reward_providers.md) — detailed reward
  provider documentation (Extrinsic, Curiosity, GAIL, RND).
- [trainers_torch_entities.md](trainers_torch_entities.md) — overview of the generic neural network building blocks
  (`NetworkBody`, `ActionFlattener`, `AgentAction`, `ModelUtils`, etc.) reused by this module.
- [trainers_policy.md](trainers_policy.md) — the `TorchPolicy` class extended by `BCModule`.
- [trainers_optimizer.md](trainers_optimizer.md) — the `TorchOptimizer` that instantiates and aggregates reward
  providers.
- [trainers_core_data_pipeline.md](trainers_core_data_pipeline.md) — `AgentBuffer` and `ObsUtil`, the data containers
  consumed by all components in this module.
- [trainers_core_config_settings.md](trainers_core_config_settings.md) — configuration schema
  (`BehavioralCloningSettings`, `CuriositySettings`, `GAILSettings`, `RNDSettings`, `RewardSignalSettings`).
- [trainers_ppo.md](trainers_ppo.md), [trainers_sac.md](trainers_sac.md), [trainers_poca.md](trainers_poca.md) — the
  built-in RL algorithms that consume these components.
