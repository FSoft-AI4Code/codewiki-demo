# Trainers Torch Entities: Actions Module

## Introduction

The **`trainers_torch_entities_actions`** module is the core PyTorch subsystem responsible for translating a policy network's internal encoding into concrete agent actions, and for computing the statistical quantities (log probabilities, entropies) needed by policy-gradient RL algorithms. It sits at the boundary between the generic neural-network "trunk" (see [trainers_torch_entities_networks](trainers_torch_entities_networks.md)) and the algorithm-specific optimizers (see [Built-in_RL_Algorithms](trainers_ppo.md)).

Three files make up this module:

| File | Responsibility |
|---|---|
| `distributions.py` | Defines probability distributions (`Gaussian`, `TanhGaussian`, `Categorical`, `MultiCategorical`) used to model continuous and discrete action spaces, along with their `nn.Module` wrappers that map a hidden encoding to distribution parameters. |
| `action_model.py` | The `ActionModel`, which composes continuous/discrete distributions into a single interface for sampling actions, evaluating log-probabilities/entropy, and producing ONNX/Sentis-exportable outputs. |
| `action_flattener.py` | The `ActionFlattener`, a small utility that converts an `AgentAction` (structured continuous + discrete tensors) into a single flat tensor (continuous concatenated with one-hot discrete), used e.g. to feed actions back into critic/Q networks. |

This module is a **leaf-level building block**: it has no dependency on the trainer orchestration layer, but it is used pervasively by policies and optimizers across all built-in and pluggable RL algorithms.

---

## 1. Purpose and Core Functionality

ML-Agents supports **hybrid action spaces** — an agent's action can be a mix of continuous (real-valued) and discrete (categorical, possibly multi-branch) components. This module provides the abstractions to:

1. **Parameterize distributions** from a policy network's hidden encoding (`GaussianDistribution`, `MultiCategoricalDistribution`).
2. **Sample actions** stochastically (training) or deterministically (inference/evaluation) from those distributions.
3. **Compute log-probabilities and entropies** of taken actions, required for policy gradient losses (PPO/POCA clipped objectives, entropy bonuses, importance sampling ratios).
4. **Support masking** of discrete branches (e.g., invalid actions in a game) via `_mask_branch`.
5. **Squash continuous actions** using `tanh` for the SAC algorithm's bounded action spaces (`TanhGaussianDistInstance`).
6. **Flatten structured actions** into single tensors for input into critics, discriminators (GAIL), or Q-networks (`ActionFlattener`).
7. **Export deterministic and stochastic outputs** in a form compatible with ONNX/Sentis for run-time inference in Unity (`get_action_out`).

### Key Types

- **`AgentAction`** (external, from `torch_entities/agent_action.py`) — a `NamedTuple` bundling a continuous tensor and a list of discrete tensors. It is the canonical in-memory representation of an action batch used throughout the trainer codebase (buffer serialization, trajectory storage, `ActionTuple` conversion for the environment).
- **`ActionLogProbs`** (external, from `torch_entities/action_log_probs.py`) — parallel structure holding log-probabilities (sampled and, for discrete branches, "all" log-probs used for KL/entropy computations).
- **`ActionSpec`** (from [Python_Environment_Interface_Layer](envs_core_api.md)) — describes the shape of the action space (`continuous_size`, `discrete_branches`) and is the configuration input to both `ActionModel` and `ActionFlattener`.

---

## 2. Architecture

### 2.1 Component Relationships

```mermaid
classDiagram
    class ActionSpec {
        +int continuous_size
        +Tuple~int~ discrete_branches
        +discrete_size
    }

    class ActionModel {
        -GaussianDistribution _continuous_distribution
        -MultiCategoricalDistribution _discrete_distribution
        -bool clip_action
        -bool _deterministic
        +forward(inputs, masks)
        +evaluate(inputs, masks, actions)
        +get_action_out(inputs, masks)
        -_get_dists(inputs, masks)
        -_sample_action(dists)
        -_get_probs_and_entropy(actions, dists)
    }

    class DistInstances {
        <<NamedTuple>>
        +continuous
        +discrete
    }

    class GaussianDistribution {
        +mu: Linear
        +log_sigma: Linear|Parameter
        +forward(inputs) DistInstance
    }

    class MultiCategoricalDistribution {
        +branches: ModuleList
        +forward(inputs, masks) List~DistInstance~
        -_mask_branch(logits, mask)
        -_split_masks(masks)
    }

    class DistInstance {
        <<abstract>>
        +sample()
        +deterministic_sample()
        +log_prob(value)
        +entropy()
        +exported_model_output()
    }

    class DiscreteDistInstance {
        <<abstract>>
        +all_log_prob()
    }

    class GaussianDistInstance
    class TanhGaussianDistInstance
    class CategoricalDistInstance

    class ActionFlattener {
        -ActionSpec _specs
        +flattened_size
        +forward(action) Tensor
    }

    class AgentAction {
        <<NamedTuple>>
        +continuous_tensor
        +discrete_list
        +to_action_tuple()
        +to_flat()
        +from_buffer()
    }

    class ActionLogProbs {
        <<NamedTuple>>
        +continuous_tensor
        +discrete_list
        +all_discrete_list
        +flatten()
    }

    ActionModel --> ActionSpec : configured by
    ActionModel --> GaussianDistribution : owns (if continuous)
    ActionModel --> MultiCategoricalDistribution : owns (if discrete)
    ActionModel --> DistInstances : builds
    ActionModel --> AgentAction : produces / consumes
    ActionModel --> ActionLogProbs : produces
    GaussianDistribution --> GaussianDistInstance : creates
    GaussianDistribution --> TanhGaussianDistInstance : creates (tanh_squash)
    MultiCategoricalDistribution --> CategoricalDistInstance : creates (per branch)
    DistInstance <|-- GaussianDistInstance
    GaussianDistInstance <|-- TanhGaussianDistInstance
    DistInstance <|-- DiscreteDistInstance
    DiscreteDistInstance <|-- CategoricalDistInstance
    ActionFlattener --> ActionSpec : configured by
    ActionFlattener --> AgentAction : flattens
```

### 2.2 Module Position within the System

```mermaid
graph TD
    subgraph Neural_Network_Building_Blocks
        NET[networks.py<br/>NetworkBody / Actor-Critic]
        ACT[trainers_torch_entities_actions<br/>ActionModel / Distributions / ActionFlattener]
        ENC[trainers_torch_entities_layers_encoders<br/>Encoders / Layers]
        ATT[trainers_torch_entities_attention_conditioning]
        UTILS[trainers_torch_entities_utils_serialization<br/>ModelUtils / ModelSerializer]
    end

    subgraph Policy_Optimizer_Layer
        POLICY[TorchPolicy]
        OPT[TorchOptimizer]
    end

    subgraph Built-in_RL_Algorithms
        PPO[TorchPPOOptimizer]
        SAC[TorchSACOptimizer]
        POCA[TorchPOCAOptimizer]
    end

    subgraph Python_Environment_Interface_Layer
        ENVS[ActionSpec / AgentAction environment I-O]
    end

    ENC --> NET
    ATT --> NET
    NET --> ACT
    UTILS --> ACT
    ACT --> POLICY
    POLICY --> OPT
    OPT --> PPO
    OPT --> SAC
    OPT --> POCA
    ENVS --> ACT
    ACT --> ENVS

    click NET "trainers_torch_entities_networks.md"
    click ENC "trainers_torch_entities_layers_encoders.md"
    click ATT "trainers_torch_entities_attention_conditioning.md"
    click UTILS "trainers_torch_entities_utils_serialization.md"
    click POLICY "trainers_policy.md"
    click OPT "trainers_optimizer.md"
    click PPO "trainers_ppo.md"
    click SAC "trainers_sac.md"
    click POCA "trainers_poca.md"
    click ENVS "envs_core_api.md"
```

See also related documentation:
- [trainers_torch_entities_networks.md](trainers_torch_entities_networks.md) — the `NetworkBody`/`Actor-Critic` classes that produce the `inputs` encoding consumed by `ActionModel`.
- [trainers_torch_entities_layers_encoders.md](trainers_torch_entities_layers_encoders.md) — `linear_layer`, `Initialization` used to build distribution heads.
- [trainers_torch_entities_utils_serialization.md](trainers_torch_entities_utils_serialization.md) — `ModelUtils` (one-hot encoding, tensor conversions) and `ModelSerializer` (ONNX export using `ActionModel.get_action_out`).
- [trainers_policy.md](trainers_policy.md) — `TorchPolicy`, which owns an `ActionModel` instance and orchestrates the sample→act→store cycle.
- [envs_core_api.md](envs_core_api.md) — `ActionSpec`, `ActionTuple` and the environment step protocol that `AgentAction`/`ActionFlattener` interoperate with.

---

## 3. Detailed Component Documentation

### 3.1 `distributions.py`

Implements the distribution abstraction hierarchy used to model policy outputs.

#### Class Hierarchy

```mermaid
classDiagram
    DistInstance <|-- GaussianDistInstance
    GaussianDistInstance <|-- TanhGaussianDistInstance
    DistInstance <|-- DiscreteDistInstance
    DiscreteDistInstance <|-- CategoricalDistInstance

    class DistInstance {
        <<abstract nn.Module>>
        +sample()* Tensor
        +deterministic_sample()* Tensor
        +log_prob(value)* Tensor
        +entropy()* Tensor
        +exported_model_output()* Tensor
    }
    class DiscreteDistInstance {
        <<abstract>>
        +all_log_prob()* Tensor
    }
    class GaussianDistInstance {
        +mean
        +std
        +pdf(value)
    }
    class TanhGaussianDistInstance {
        +transform: TanhTransform
        -_inverse_tanh(value)
    }
    class CategoricalDistInstance {
        +logits
        +probs
        +pdf(value)
    }
```

- **`GaussianDistInstance`**: Standard normal distribution parameterized by `mean`/`std`. Implements reparameterized `sample()`, closed-form `log_prob()`, and analytic Gaussian `entropy()`.
- **`TanhGaussianDistInstance`**: Wraps `GaussianDistInstance` with a `TanhTransform` to bound samples in `[-1, 1]` (used by SAC for bounded continuous actions). Adjusts `log_prob` via the change-of-variables Jacobian term.
- **`CategoricalDistInstance`**: Discrete distribution from `logits` (softmax to get `probs`). Implements `sample()` via `torch.multinomial`, `all_log_prob()` for full-branch log-probability vectors (used in discrete entropy/KL calculations), and an ONNX-friendly `pdf()` via `torch.gather` (avoiding unsupported `torch.diag`).

#### Distribution "Head" Modules

- **`GaussianDistribution(nn.Module)`**: Produces a `GaussianDistInstance` (or `TanhGaussianDistInstance` if `tanh_squash=True`) from a hidden encoding.
  - `mu`: linear layer (`KaimingHeNormal` init, gain 0.2).
  - `log_sigma`: either a **state-conditioned** linear layer (`conditional_sigma=True`) or a single learned parameter broadcast across the batch (workaround for Sentis inference not supporting `expand`).
  - Clamps `log_sigma` to `[-20, 2]` for numerical stability when conditional.

- **`MultiCategoricalDistribution(nn.Module)`**: Handles **multiple discrete action branches** (e.g., "move" + "jump" as separate categorical spaces).
  - Builds one linear "branch" per discrete action size (`_create_policy_branches`).
  - Splits a combined action-mask tensor into per-branch masks (`_split_masks`) and applies masking (`_mask_branch`) by combining a multiplicative zero-out and a large negative additive term — designed to be robust to ONNX/Sentis operator quirks (comment about `Sub` operand order).
  - Returns one `CategoricalDistInstance` per branch.

```mermaid
sequenceDiagram
    participant NB as NetworkBody (encoding)
    participant MCD as MultiCategoricalDistribution
    participant CDI as CategoricalDistInstance (per branch)

    NB->>MCD: forward(inputs, masks)
    MCD->>MCD: _split_masks(masks)
    loop for each branch
        MCD->>MCD: logits = branch(inputs)
        MCD->>MCD: _mask_branch(logits, branch_mask)
        MCD->>CDI: new CategoricalDistInstance(norm_logits)
    end
    MCD-->>NB: List[DistInstance]
```

### 3.2 `action_model.py`

The **`ActionModel`** is the primary orchestrator combining continuous and discrete distributions into one coherent action interface tied to an `ActionSpec`.

#### Construction

```python
ActionModel(hidden_size, action_spec, conditional_sigma=False, tanh_squash=False, deterministic=False)
```
- Instantiates `GaussianDistribution` if `action_spec.continuous_size > 0`.
- Instantiates `MultiCategoricalDistribution` if `action_spec.discrete_size > 0`.
- `clip_action = not tanh_squash` — continuous outputs are clipped to `[-3, 3]/3` unless tanh squashing already bounds them (SAC uses `tanh_squash=True`; PPO/POCA typically clip).
- `deterministic` flag toggles between stochastic sampling (training rollouts) and greedy/mean action selection (deterministic evaluation mode).

#### Internal Data Flow

```mermaid
flowchart TD
    A[Hidden encoding from NetworkBody] --> B["_get_dists(inputs, masks)"]
    B --> C{Continuous?}
    C -->|Yes| D[GaussianDistribution forward]
    C -->|No| E[skip]
    B --> F{Discrete?}
    F -->|Yes| G[MultiCategoricalDistribution forward]
    F -->|No| H[skip]
    D --> I[DistInstances]
    G --> I
    I --> J["forward: _sample_action(dists)"]
    I --> K["evaluate: _get_probs_and_entropy(actions, dists)"]
    I --> L["get_action_out: exported_model_output / deterministic_sample"]
    J --> M[AgentAction]
    K --> N[ActionLogProbs + entropy sum]
    L --> O[ONNX/Sentis export tensors]
```

#### Public API

| Method | Used By | Purpose |
|---|---|---|
| `forward(inputs, masks)` | `TorchPolicy.get_action()` (rollout collection) | Samples action, computes log-probs & entropy in one pass. |
| `evaluate(inputs, masks, actions)` | Optimizers (`TorchPPOOptimizer`, `TorchPOCAOptimizer`, `TorchSACOptimizer`) during gradient updates | Recomputes log-probs/entropy for **already-taken** actions (from buffer), needed for importance-ratio and entropy-bonus terms. |
| `get_action_out(inputs, masks)` | `ModelSerializer` ([trainers_torch_entities_utils_serialization.md](trainers_torch_entities_utils_serialization.md)) | Produces ONNX-exportable continuous/discrete/deterministic outputs for Unity runtime inference. |
| `_sample_action`, `_get_dists`, `_get_probs_and_entropy` | internal | Helper stages shared by `forward`/`evaluate`. |

Note: the **deprecated** `action_out_deprecated` field in `get_action_out` supports legacy single-space (pure continuous or pure discrete) models only; hybrid action spaces set it to `None`.

#### Sequence: Training Rollout vs. Optimizer Update

```mermaid
sequenceDiagram
    participant Policy as TorchPolicy
    participant AM as ActionModel
    participant Env as Unity Environment

    Note over Policy,Env: Rollout collection (acting)
    Policy->>AM: forward(encoding, masks)
    AM-->>Policy: (AgentAction, ActionLogProbs, entropy)
    Policy->>Env: AgentAction.to_action_tuple()

    Note over Policy,AM: Optimizer update (learning)
    Policy->>AM: evaluate(encoding, masks, buffered_actions)
    AM-->>Policy: (ActionLogProbs, entropy_sum)
    Policy->>Policy: compute PPO/SAC/POCA loss using log-probs, entropy, old_log_probs
```

### 3.3 `action_flattener.py`

**`ActionFlattener`** provides a stateless conversion of a structured `AgentAction` into a single dense tensor:

```
flattened = concat(continuous_tensor, one_hot(discrete_branch_1), ..., one_hot(discrete_branch_n))
```

- `flattened_size` = `continuous_size + sum(discrete_branches)` — useful for sizing downstream network inputs (e.g., Q-network state-action concatenation in SAC, or discriminator input in GAIL).
- `forward(action: AgentAction) -> Tensor` uses `ModelUtils.actions_to_onehot` (see [trainers_torch_entities_utils_serialization.md](trainers_torch_entities_utils_serialization.md)) to one-hot encode each discrete branch before concatenation.

This is functionally similar to `AgentAction.to_flat()`, but implemented as an injectable `nn.Module`-style helper configured once per `ActionSpec` (typically instantiated inside a network body or reward provider that needs a fixed-size action representation, e.g., `CuriosityNetwork`, `DiscriminatorNetwork`, or SAC's Q-network — see [trainers_torch_components](trainers_torch_components.md) and [trainers_sac.md](trainers_sac.md)).

```mermaid
flowchart LR
    AS[ActionSpec] --> AF[ActionFlattener]
    AA[AgentAction] -->|forward| AF
    AF -->|continuous_tensor| CAT[torch.cat]
    AF -->|discrete branches one-hot| CAT
    CAT --> OUT[Flat Tensor: batch x flattened_size]
    OUT --> QNET[SAC Q-Network / GAIL Discriminator / Curiosity Network]
```

---

## 4. Data Structures Interop

This module relies on and produces several `NamedTuple`-based data structures defined elsewhere but central to its operation:

```mermaid
graph LR
    ActionSpec -->|configures| ActionModel
    ActionSpec -->|configures| ActionFlattener
    ActionModel -->|produces| AgentAction
    ActionModel -->|produces| ActionLogProbs
    AgentAction -->|consumed by| ActionFlattener
    AgentAction -->|to_action_tuple| ActionTuple[ActionTuple<br/>sent to Unity]
    AgentAction -->|from_buffer| AgentBuffer[AgentBuffer<br/>trajectory storage]
    ActionLogProbs -->|from_buffer / flatten| AgentBuffer
```

- **`AgentAction`** and **`ActionLogProbs`** know how to (de)serialize themselves from/to an `AgentBuffer` (see [trainers_core_data_pipeline](trainers_core_data_pipeline.md)), enabling trajectories collected during rollouts to be replayed for gradient computation via `ActionModel.evaluate`.
- **`ActionSpec`** and **`ActionTuple`** originate in the environment interface layer ([envs_core_api.md](envs_core_api.md)) and define the contract between the Unity environment and the trainer's action-generation logic.

---

## 5. Usage Across Algorithms

| Algorithm | How it uses this module |
|---|---|
| **PPO** ([trainers_ppo.md](trainers_ppo.md)) | Uses `ActionModel.evaluate()` to get log-probs/entropy for the clipped surrogate objective (`ModelUtils.trust_region_policy_loss`) and entropy bonus. |
| **SAC** ([trainers_sac.md](trainers_sac.md)) | Uses `tanh_squash=True` in `ActionModel` for bounded continuous actions; uses `ActionFlattener`/`AgentAction.to_flat()` to feed actions into Q-networks. |
| **POCA** ([trainers_poca.md](trainers_poca.md)) | Same as PPO but extended for multi-agent counterfactual baselines; consumes grouped `AgentAction`s via `AgentAction.group_from_buffer`. |
| **A2C / DQN plugins** ([Extensible_RL_Algorithm_Plugins](trainer_plugin_a2c.md)) | Reuse `ActionModel`/`distributions.py` primitives for custom optimizer implementations, demonstrating the extensibility of this module beyond built-in trainers. |

---

## 6. Design Notes & Constraints

- **ONNX/Sentis compatibility**: Several implementation choices (`_mask_branch`'s formula, avoiding `torch.diag`, avoiding `torch.expand`, clamping ranges) exist specifically to ensure the exported graph works with Unity's Sentis inference engine. See [trainers_torch_entities_utils_serialization.md](trainers_torch_entities_utils_serialization.md) for the `ModelSerializer` that performs this export using `ActionModel.get_action_out`.
- **Deterministic vs. Stochastic**: The `deterministic` flag on `ActionModel` supports evaluation/inference workflows where reproducible, greedy actions are desired (as opposed to training-time exploration).
- **Backward compatibility**: The deprecated single-tensor `action_out_deprecated` output path exists only for non-hybrid action specs, preserving compatibility with older Unity-side inference code that expected a single action tensor.
- **Entropy aggregation**: Entropies across continuous and multiple discrete branches are **summed** (not averaged) per the `torch.sum(entropies, dim=1)` calls in `evaluate`/`forward`, matching the standard policy-gradient entropy bonus formulation.
