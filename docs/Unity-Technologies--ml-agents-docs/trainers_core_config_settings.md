# Trainers Core Config Settings

## Introduction

`trainers_core_config_settings` is the **single source of truth for all typed configuration** used by the ML-Agents Python trainer stack. It is implemented almost entirely in [`ml-agents/mlagents/trainers/settings.py`](#) and defines the `attrs`-based data classes that represent every configurable aspect of a training run: network architecture, hyperparameters for each trainer algorithm, intrinsic reward signals, environment parameter randomization/curricula, checkpointing behavior, and engine/environment/torch runtime options.

This module is the schema and validation layer that sits between:
- **User input** — YAML configuration files and CLI arguments (parsed by [`trainers_core_config_cli`](trainers_core_config_cli.md))
- **Runtime consumers** — the orchestration layer ([`trainers_core_orchestration`](trainers_core_orchestration.md)), trainer implementations ([`trainers_trainer_base`](trainers_trainer_base.md), [`Built-in_RL_Algorithms`](trainers_ppo.md)), and neural network construction ([`Neural_Network_Building_Blocks`](trainers_torch_entities.md))

Because it converts loosely-typed dictionaries (from YAML/CLI) into strongly-typed, validated Python objects, it is the primary guard-rail against misconfiguration in ML-Agents training runs.

---

## Module Position in the System

```mermaid
graph TB
    subgraph "trainers_core_config (parent)"
        CLI[trainers_core_config_cli<br/>argparse setup, YAML loading]
        SETTINGS[trainers_core_config_settings<br/>THIS MODULE]
    end

    CLI -->|"parser defaults,<br/>StoreConfigFile,<br/>load_config()"| SETTINGS

    SETTINGS -->|RunOptions| ORCH[trainers_core_orchestration<br/>TrainerController]
    SETTINGS -->|TrainerSettings| FACTORY[trainers_trainer_base<br/>TrainerFactory]
    SETTINGS -->|NetworkSettings| TORCH[trainers_torch_entities<br/>NetworkBody, ActionModel]
    SETTINGS -->|RewardSignalSettings| REWARDS[trainers_torch_components<br/>reward_providers]
    SETTINGS -->|PPO/SAC/POCA Settings| ALGOS[Built-in RL Algorithms<br/>PPOTrainer, SACTrainer, POCATrainer]
    SETTINGS -->|EnvironmentSettings| ENVMGMT[trainers_core_env_management<br/>SubprocessEnvManager]
    SETTINGS -->|EnvironmentParameterSettings| EPM[EnvironmentParameterManager<br/>trainers_core_orchestration]

    style SETTINGS fill:#4a90d9,color:#fff
```

---

## Core Responsibilities

1. **Typed schema definition** for every trainer-facing configuration object using `attrs` (`@attr.s(auto_attribs=True)`).
2. **Structuring/unstructuring** raw `dict`/YAML data into these typed objects via `cattr`, including custom hooks for polymorphic fields (e.g., choosing `PPOSettings` vs `SACSettings` based on `trainer_type`).
3. **Validation** of cross-field constraints (e.g., memory size must divide batch size, sampler min ≤ max, curriculum lesson chains must be well-formed).
4. **Defaulting** — every field either has a static default or draws its default from CLI parser defaults (via [`trainers_core_config_cli`](trainers_core_config_cli.md)'s `parser.get_default(...)`), guaranteeing CLI and YAML consistency.
5. **Merging CLI overrides into YAML config** through `RunOptions.from_argparse`.
6. **Extensibility hooks** so that external plugins (see [`Extensible_RL_Algorithm_Plugins`](trainer_plugin_a2c.md)) can register new trainer-specific hyperparameter classes via `mlagents.plugins.all_trainer_settings`.

---

## Top-Level Structure (`RunOptions`)

`RunOptions` is the root configuration object for an entire `mlagents-learn` invocation. Everything else in this module is either a field of `RunOptions` or a field nested within one of its fields.

```mermaid
classDiagram
    class RunOptions {
        +TrainerSettings default_settings
        +DefaultTrainerDict behaviors
        +EnvironmentSettings env_settings
        +EngineSettings engine_settings
        +Dict~str,EnvironmentParameterSettings~ environment_parameters
        +CheckpointSettings checkpoint_settings
        +TorchSettings torch_settings
        +bool debug
        +from_argparse(args) RunOptions
        +from_dict(options_dict) RunOptions
    }

    class TrainerSettings {
        +str trainer_type
        +HyperparamSettings hyperparameters
        +int checkpoint_interval
        +NetworkSettings network_settings
        +Dict~RewardSignalType,RewardSignalSettings~ reward_signals
        +Optional~str~ init_path
        +int keep_checkpoints
        +bool even_checkpoints
        +int max_steps
        +int time_horizon
        +int summary_freq
        +bool threaded
        +Optional~SelfPlaySettings~ self_play
        +Optional~BehavioralCloningSettings~ behavioral_cloning
        +structure(d, t)$ TrainerSettings
        +dict_to_trainerdict(d, t)$ DefaultTrainerDict
    }

    class DefaultTrainerDict {
        <<defaultdict>>
        +__missing__(key) TrainerSettings
        +set_config_specified(bool)
    }

    class EnvironmentSettings {
        +Optional~str~ env_path
        +Optional~List~str~~ env_args
        +int base_port
        +int num_envs
        +int num_areas
        +int timeout_wait
        +int seed
        +int max_lifetime_restarts
        +int restarts_rate_limit_n
        +int restarts_rate_limit_period_s
    }

    class EngineSettings {
        +int width
        +int height
        +int quality_level
        +float time_scale
        +int target_frame_rate
        +int capture_frame_rate
        +bool no_graphics
        +bool no_graphics_monitor
    }

    class CheckpointSettings {
        +str run_id
        +Optional~str~ initialize_from
        +bool load_model
        +bool resume
        +bool force
        +bool train_model
        +bool inference
        +str results_dir
        +write_path str
        +maybe_init_path Optional~str~
        +run_logs_dir str
        +prioritize_resume_init()
    }

    class TorchSettings {
        +Optional~str~ device
    }

    class EnvironmentParameterSettings {
        +List~Lesson~ curriculum
        +structure(d, t)$ Dict
    }

    RunOptions "1" o-- "1" TrainerSettings : default_settings
    RunOptions "1" o-- "1" DefaultTrainerDict : behaviors
    RunOptions "1" o-- "1" EnvironmentSettings : env_settings
    RunOptions "1" o-- "1" EngineSettings : engine_settings
    RunOptions "1" o-- "1" CheckpointSettings : checkpoint_settings
    RunOptions "1" o-- "1" TorchSettings : torch_settings
    RunOptions "1" o-- "*" EnvironmentParameterSettings : environment_parameters
    DefaultTrainerDict "1" o-- "*" TrainerSettings
```

---

## Trainer Hyperparameter Hierarchy

`TrainerSettings.hyperparameters` is polymorphic: its concrete type depends on `trainer_type` and is resolved through the `all_trainer_settings` plugin registry (populated by [`Built-in_RL_Algorithms`](trainers_ppo.md) and [`Extensible_RL_Algorithm_Plugins`](trainer_plugin_a2c.md)).

```mermaid
classDiagram
    class HyperparamSettings {
        +int batch_size = 1024
        +int buffer_size = 10240
        +float learning_rate = 3e-4
        +ScheduleType learning_rate_schedule
    }
    class OnPolicyHyperparamSettings {
        +int num_epoch = 3
    }
    class OffPolicyHyperparamSettings {
        +int batch_size = 128
        +int buffer_size = 50000
        +int buffer_init_steps = 0
        +float steps_per_update = 1
        +bool save_replay_buffer = false
        +float reward_signal_steps_per_update = 4
    }
    HyperparamSettings <|-- OnPolicyHyperparamSettings
    HyperparamSettings <|-- OffPolicyHyperparamSettings

    class PPOSettings {
        (defined in trainers_ppo)
    }
    class POCASettings {
        (defined in trainers_poca)
    }
    class SACSettings {
        (defined in trainers_sac)
    }
    class A2CSettings {
        (Extensible_RL_Algorithm_Plugins)
    }
    class DQNSettings {
        (Extensible_RL_Algorithm_Plugins)
    }
    OnPolicyHyperparamSettings <|-- PPOSettings
    OnPolicyHyperparamSettings <|-- POCASettings
    OnPolicyHyperparamSettings <|-- A2CSettings
    OffPolicyHyperparamSettings <|-- SACSettings
    OffPolicyHyperparamSettings <|-- DQNSettings
```

> Concrete algorithm hyperparameter classes (`PPOSettings`, `SACSettings`, `POCASettings`, `A2CSettings`, `DQNSettings`) live in their respective trainer modules — see [`Built-in_RL_Algorithms`](trainers_ppo.md) and [`Extensible_RL_Algorithm_Plugins`](trainer_plugin_a2c.md) — but they subclass `HyperparamSettings`/`OnPolicyHyperparamSettings`/`OffPolicyHyperparamSettings` defined here.

---

## Network Settings

`NetworkSettings` configures the shared neural-network architecture consumed by [`trainers_torch_entities`](trainers_torch_entities.md) (`NetworkBody`, `ObservationEncoder`, `ActionModel`, etc.):

| Field | Type | Purpose |
|---|---|---|
| `normalize` | `bool` | Enable running observation normalization |
| `hidden_units` | `int` | Width of fully-connected layers |
| `num_layers` | `int` | Depth of fully-connected encoder |
| `vis_encode_type` | `EncoderType` | Visual encoder architecture (`SIMPLE`, `NATURE_CNN`, `RESNET`, `MATCH3`, `FULLY_CONNECTED`) |
| `memory` | `Optional[MemorySettings]` | Enables recurrent (LSTM) policy; validates `memory_size` divisibility/positivity |
| `goal_conditioning_type` | `ConditioningType` | `HYPER` (hypernetwork-based) or `NONE` |
| `deterministic` | `bool` | Deterministic vs. stochastic action selection at inference |

```mermaid
graph LR
    NS[NetworkSettings] --> EncoderType
    NS --> MemorySettings
    NS --> ConditioningType
    NS -.consumed by.-> NB[NetworkBody / ObservationEncoder]
    NS -.consumed by.-> AM[ActionModel]
    NB -.-> DOC1[trainers_torch_entities.md]
    AM -.-> DOC1
```

---

## Reward Signal Settings

Intrinsic/extrinsic reward configuration is resolved polymorphically by `RewardSignalType`, mirroring the trainer-hyperparameter pattern. Each subtype maps to a reward provider implemented in [`trainers_torch_components`](trainers_torch_components.md).

```mermaid
classDiagram
    class RewardSignalSettings {
        +float gamma = 0.99
        +float strength = 1.0
        +NetworkSettings network_settings
        +structure(d, t)$ Dict
    }
    class GAILSettings {
        +float learning_rate = 3e-4
        +Optional~int~ encoding_size
        +bool use_actions = false
        +bool use_vail = false
        +str demo_path
    }
    class CuriositySettings {
        +float learning_rate = 3e-4
        +Optional~int~ encoding_size
    }
    class RNDSettings {
        +float learning_rate = 1e-4
        +Optional~int~ encoding_size
    }
    RewardSignalSettings <|-- GAILSettings
    RewardSignalSettings <|-- CuriositySettings
    RewardSignalSettings <|-- RNDSettings

    class RewardSignalType {
        <<enum>>
        EXTRINSIC
        GAIL
        CURIOSITY
        RND
        +to_settings() type
    }
    RewardSignalType ..> RewardSignalSettings : resolves to
```

`RewardSignalType.to_settings()` is used by `RewardSignalSettings.structure()` (a `cattr` structure hook) to pick the correct subtype while parsing YAML, and each type is ultimately instantiated as a `BaseRewardProvider` subclass at runtime — see [`trainers_torch_components`](trainers_torch_components.md).

---

## Environment Parameter Randomization & Curriculum

Environment parameters support three concepts, all defined in this module:

1. **Samplers** (`ParameterRandomizationSettings` subtypes) — how a scalar parameter value is drawn each episode.
2. **Lessons** — a named sampler bound to an optional `CompletionCriteriaSettings`.
3. **Curricula** (`EnvironmentParameterSettings`) — an ordered list of `Lesson`s for one parameter, consumed by `EnvironmentParameterManager` in [`trainers_core_orchestration`](trainers_core_orchestration.md).

```mermaid
classDiagram
    class ParameterRandomizationSettings {
        <<abstract>>
        +int seed
        +apply(key, env_channel)*
        +structure(d, t)$ ParameterRandomizationSettings
        +unstructure(d)$ Mapping
    }
    class ConstantSettings {
        +float value = 0.0
    }
    class UniformSettings {
        +float min_value = 0.0
        +float max_value = 1.0
    }
    class GaussianSettings {
        +float mean = 1.0
        +float st_dev = 1.0
    }
    class MultiRangeUniformSettings {
        +List~Tuple~ intervals
    }
    ParameterRandomizationSettings <|-- ConstantSettings
    ParameterRandomizationSettings <|-- UniformSettings
    ParameterRandomizationSettings <|-- GaussianSettings
    ParameterRandomizationSettings <|-- MultiRangeUniformSettings

    class Lesson {
        +ParameterRandomizationSettings value
        +str name
        +Optional~CompletionCriteriaSettings~ completion_criteria
    }
    class CompletionCriteriaSettings {
        +MeasureType measure
        +int min_lesson_length
        +bool signal_smoothing
        +float threshold
        +bool require_reset
        +need_increment(progress, reward_buffer, smoothing) Tuple
    }
    class EnvironmentParameterSettings {
        +List~Lesson~ curriculum
    }

    Lesson --> ParameterRandomizationSettings : value
    Lesson --> CompletionCriteriaSettings : completion_criteria
    EnvironmentParameterSettings --> "*" Lesson
```

Each sampler's `apply(key, env_channel)` method sends the sampling configuration to Unity through an `EnvironmentParametersChannel` (see [`envs_sidechannel_channels`](envs_sidechannel_channels.md)), decoupling the Python-side schema from the Unity-side side-channel protocol.

---

## Configuration Loading & Structuring Flow

`RunOptions` is produced from CLI args + YAML through a well-defined pipeline that combines this module with [`trainers_core_config_cli`](trainers_core_config_cli.md).

```mermaid
sequenceDiagram
    participant User
    participant CLI as trainers_core_config_cli<br/>(argparse, parser)
    participant Settings as settings.py<br/>(this module)
    participant cattr as cattr / attrs

    User->>CLI: mlagents-learn config.yaml --run-id=X ...
    CLI->>CLI: parse_args() populates argparse.Namespace
    CLI->>CLI: StoreConfigFile.__call__ captures trainer_config_path
    CLI->>Settings: RunOptions.from_argparse(args)
    Settings->>CLI: load_config(config_path) reads YAML into dict
    Settings->>Settings: merge YAML dict with CLI non-default args<br/>(per CheckpointSettings/EnvironmentSettings/<br/>EngineSettings/TorchSettings field ownership)
    Settings->>Settings: RunOptions.from_dict(configured_dict)
    Settings->>cattr: cattr.structure(options_dict, RunOptions)
    cattr->>Settings: invoke registered structure hooks<br/>(TrainerSettings.structure,<br/>EnvironmentParameterSettings.structure,<br/>ParameterRandomizationSettings.structure, ...)
    Settings->>Settings: TrainerSettings.structure() resolves<br/>trainer_type -> concrete HyperparamSettings<br/>via all_trainer_settings registry
    Settings->>Settings: validators run (attrs validators)<br/>e.g. batch_size vs sequence_length,<br/>min_value <= max_value
    Settings-->>CLI: fully validated RunOptions instance
    CLI-->>User: raises TrainerConfigError on any violation
```

Key structuring/validation utilities defined at module scope:

- `check_and_structure(key, value, class_type)` — validates a field exists on the target attrs class and structures its value with `cattr`.
- `strict_to_cls(d, t)` — structures an entire mapping into an attrs class `t`, rejecting unknown keys.
- `deep_update_dict(d, update_d)` — recursively merges nested dict configs (used to layer `default_settings` under per-behavior overrides).
- `defaultdict_to_dict(d)` — unstructure helper for `collections.defaultdict`-based containers like `TrainerSettings.DefaultTrainerDict`.
- `check_hyperparam_schedules(val, trainer_type)` — backfills `beta_schedule`/`epsilon_schedule` from `learning_rate_schedule` for PPO/POCA if unspecified.

---

## `TrainerSettings.DefaultTrainerDict`: Per-Behavior Configuration

Unity environments can expose multiple distinct "Behaviors" (agent policies). `RunOptions.behaviors` is a `TrainerSettings.DefaultTrainerDict`, a `collections.defaultdict` subclass keyed by behavior name:

```mermaid
flowchart TD
    A["behaviors[key] accessed"] --> B{Key present?}
    B -->|Yes| C[Return existing TrainerSettings]
    B -->|No, __missing__ triggered| D{default_override set?<br/>i.e. default_settings in YAML}
    D -->|Yes| E[Deep-copy default_override,<br/>store & return]
    D -->|No| F{_config_specified?<br/>i.e. YAML file was provided}
    F -->|Yes| G[Raise TrainerConfigError:<br/>behavior not specified]
    F -->|No| H[Log warning,<br/>use bare TrainerSettings defaults]
```

This mechanism allows:
- Strict validation when a full YAML config is supplied (every behavior must be explicitly configured or covered by `default_settings`).
- Lenient auto-defaulting when running without a config file (e.g., quick experiments), while still logging a warning.

This dict is consumed directly by `TrainerFactory` (see [`trainers_trainer_base`](trainers_trainer_base.md)) to construct the correct `Trainer`/`Optimizer` per behavior name.

---

## Command-Line & Runtime Settings

Several `attrs` classes mirror groups of CLI flags, each deriving its defaults from the shared `argparse.ArgumentParser` (`parser`) defined in [`trainers_core_config_cli`](trainers_core_config_cli.md):

| Class | Fields (highlights) | Consumed By |
|---|---|---|
| `CheckpointSettings` | `run_id`, `resume`, `force`, `initialize_from`, `results_dir`, `inference` | `TrainerController`, `ModelCheckpointManager` ([`trainers_policy`](trainers_policy.md)) |
| `EnvironmentSettings` | `env_path`, `num_envs`, `num_areas`, `base_port`, `seed`, restart-rate-limiting fields | `SubprocessEnvManager`/`SimpleEnvManager` ([`trainers_core_env_management`](trainers_core_env_management.md)) |
| `EngineSettings` | `width`, `height`, `time_scale`, `no_graphics`, `target_frame_rate` | Unity engine configuration channel ([`envs_sidechannel_channels`](envs_sidechannel_channels.md)) |
| `TorchSettings` | `device` | `TorchPolicy`/`TorchOptimizer` device placement ([`trainers_policy`](trainers_policy.md), [`trainers_optimizer`](trainers_optimizer.md)) |

`CheckpointSettings` also implements `prioritize_resume_init()`, which resolves conflicts when both `--resume` and `--initialize-from` are set (from CLI or YAML), always preferring `resume` and logging a warning when overridden.

`SerializationSettings` (a plain class, not `attrs`) holds static export configuration (`convert_to_onnx`, `onnx_opset`) used by the model export pipeline (`ModelSerializer` in [`trainers_torch_entities`](trainers_torch_entities.md)).

---

## Self-Play Settings

`SelfPlaySettings` configures competitive self-play training, consumed by `GhostTrainer`/`GhostController` (see [`trainers_ghost`](trainers_ghost.md)):

| Field | Default | Description |
|---|---|---|
| `save_steps` | 20000 | Steps between saving a new snapshot opponent |
| `team_change` | `save_steps * 5` | Steps between switching learning team |
| `swap_steps` | 2000 | Steps between swapping opponent snapshot |
| `window` | 10 | Number of snapshots retained for opponent sampling |
| `play_against_latest_model_ratio` | 0.5 | Probability of playing against the most recent policy vs. a historical snapshot |
| `initial_elo` | 1200.0 | Starting ELO rating for self-play ranking |

---

## Behavioral Cloning Settings

`BehavioralCloningSettings` configures pretraining/BC-loss from demonstration data, consumed by `BCModule` in [`trainers_torch_components`](trainers_torch_components.md):

- `demo_path` (required) — path to a `.demo` file (see [`runtime_demonstrations`](runtime_demonstrations.md) / `DemonstrationRecorder`)
- `steps`, `strength`, `samples_per_update`
- `num_epoch`, `batch_size` — `None` defers to the parent trainer's hyperparameters

---

## Extensibility Model

New trainer algorithms (built-in or third-party plugins) integrate with this module purely through **registration**, without modifying `settings.py`:

```mermaid
graph LR
    subgraph "mlagents.plugins registry"
        ATS[all_trainer_settings]
        ATT[all_trainer_types]
    end

    PPO[PPOSettings] -->|registers under 'ppo'| ATS
    SAC[SACSettings] -->|registers under 'sac'| ATS
    POCA[POCASettings] -->|registers under 'poca'| ATS
    A2C[A2CSettings<br/>plugin] -->|registers under 'a2c'| ATS
    DQN[DQNSettings<br/>plugin] -->|registers under 'dqn'| ATS

    ATS -.used by.-> TS["TrainerSettings._set_default_hyperparameters()<br/>TrainerSettings.structure()"]
    ATT -.used by.-> TS

    style TS fill:#4a90d9,color:#fff
```

`TrainerSettings.structure()` looks up `d_copy["trainer_type"]` in `all_trainer_types` (validating it is a recognized value) and `all_trainer_settings` (to select the concrete hyperparameter class), meaning any RL algorithm module that registers itself in these dictionaries automatically gains full YAML/CLI configuration support. See [`Built-in_RL_Algorithms`](trainers_ppo.md) and [`Extensible_RL_Algorithm_Plugins`](trainer_plugin_a2c.md) for concrete examples.

---

## Error Handling

All configuration errors raised by this module use `TrainerConfigError` (and non-fatal issues use `TrainerConfigWarning`), both defined in `mlagents.trainers.exception`. Representative validation failures include:

- Unknown YAML key for a given settings class (`check_and_structure`)
- Invalid `trainer_type`
- Missing `sampler_type`/`sampler_parameters` in a parameter randomization config
- `min_value > max_value` in `UniformSettings`, or malformed intervals in `MultiRangeUniformSettings`
- Non-terminal curriculum lesson missing a `completion_criteria`
- `memory_size` not positive or not divisible by 2
- `sequence_length > batch_size` when memory is enabled
- Behavior name missing from YAML when a full config file is required

These errors surface to the user at CLI startup (via `RunOptions.from_argparse`), before any Unity environment or training loop is started — see [`trainers_core_orchestration`](trainers_core_orchestration.md) for how `TrainerController` consumes the validated `RunOptions`.

---

## Summary of Key Types

| Category | Types |
|---|---|
| Root | `RunOptions` |
| Trainer config | `TrainerSettings`, `TrainerSettings.DefaultTrainerDict`, `HyperparamSettings` (+ On/OffPolicy variants) |
| Network | `NetworkSettings`, `EncoderType`, `ScheduleType`, `ConditioningType` |
| Reward signals | `RewardSignalSettings`, `GAILSettings`, `CuriositySettings`, `RNDSettings`, `RewardSignalType` |
| Env parameter randomization | `ParameterRandomizationSettings`, `ConstantSettings`, `UniformSettings`, `GaussianSettings`, `MultiRangeUniformSettings`, `ParameterRandomizationType` |
| Curriculum | `Lesson`, `CompletionCriteriaSettings`, `CompletionCriteriaSettings.MeasureType`, `EnvironmentParameterSettings` |
| Runtime/CLI | `CheckpointSettings`, `EnvironmentSettings`, `EngineSettings`, `TorchSettings`, `SerializationSettings` |
| Auxiliary trainer features | `SelfPlaySettings`, `BehavioralCloningSettings` |

## Related Modules

- [`trainers_core_config_cli`](trainers_core_config_cli.md) — argparse definitions and YAML loading that feed this module's defaults and raw config dicts.
- [`trainers_core_orchestration`](trainers_core_orchestration.md) — `TrainerController` and `EnvironmentParameterManager`, primary consumers of `RunOptions`.
- [`trainers_trainer_base`](trainers_trainer_base.md) — `TrainerFactory` uses `TrainerSettings.DefaultTrainerDict` to instantiate trainers per behavior.
- [`trainers_core_env_management`](trainers_core_env_management.md) — consumes `EnvironmentSettings` to launch/manage Unity environment subprocesses.
- [`trainers_torch_entities`](trainers_torch_entities.md) / [`trainers_torch_components`](trainers_torch_components.md) — consume `NetworkSettings` and `RewardSignalSettings` respectively.
- [`Built-in_RL_Algorithms`](trainers_ppo.md) and [`Extensible_RL_Algorithm_Plugins`](trainer_plugin_a2c.md) — define concrete `HyperparamSettings` subclasses registered into this module's polymorphic resolution system.
- [`envs_sidechannel_channels`](envs_sidechannel_channels.md) — `EnvironmentParametersChannel` receives sampler configuration via `ParameterRandomizationSettings.apply()`.
