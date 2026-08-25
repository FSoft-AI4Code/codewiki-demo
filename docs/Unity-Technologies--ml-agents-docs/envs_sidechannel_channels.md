# Side Channel Implementations (`envs_sidechannel_channels`)

## Introduction

This module contains the **concrete SideChannel implementations** used by the ML-Agents Python-Unity communication layer. Side channels are auxiliary, out-of-band communication pipes that run alongside the main reinforcement-learning data exchange (observations/actions), allowing Python and Unity to exchange metadata such as engine configuration, environment parameters, custom float properties, raw bytes, statistics, and analytics events.

All channels in this module inherit from the abstract `SideChannel` base class and rely on the `IncomingMessage`/`OutgoingMessage` serialization utilities defined in the parent [envs_sidechannel_framework](envs_sidechannel_framework.md) module. Message routing and multiplexing across all registered channels is performed by the `SideChannelManager`, also part of that framework module.

This document covers:
1. The purpose and responsibilities of each side channel implementation
2. How channels plug into the broader side-channel framework and communication stack
3. Data flow and message-format diagrams
4. How these channels are consumed by downstream modules (training orchestration, environment wrappers)

## Module Position in the System

`envs_sidechannel_channels` is a child of `envs_sidechannel`, which itself lives under the [Python_Environment_Interface_Layer](envs_core.md) area of the system. It is a sibling of `envs_sidechannel_framework`, which supplies the abstract plumbing (`SideChannel`, `IncomingMessage`, `OutgoingMessage`, `SideChannelManager`) that every channel in this module depends on.

```mermaid
graph TD
    subgraph envs_sidechannel_framework
        SC[SideChannel - ABC]
        IM[IncomingMessage]
        OM[OutgoingMessage]
        SCM[SideChannelManager]
    end

    subgraph envs_sidechannel_channels[envs_sidechannel_channels - this module]
        ECC[EngineConfigurationChannel]
        EPC[EnvironmentParametersChannel]
        FPC[FloatPropertiesChannel]
        RBC[RawBytesChannel]
        SSC[StatsSideChannel]
        DTASC[DefaultTrainingAnalyticsSideChannel]
    end

    ECC --> SC
    EPC --> SC
    FPC --> SC
    RBC --> SC
    SSC --> SC
    DTASC --> SC

    ECC -. uses .-> OM
    EPC -. uses .-> OM
    FPC -. uses .-> OM
    FPC -. uses .-> IM
    RBC -. uses .-> OM
    RBC -. uses .-> IM
    SSC -. uses .-> IM
    DTASC -. uses .-> OM

    SCM -->|routes messages by channel_id| ECC
    SCM --> EPC
    SCM --> FPC
    SCM --> RBC
    SCM --> SSC
    SCM --> DTASC
```

See [envs_sidechannel_framework](envs_sidechannel_framework.md) for details on the abstract `SideChannel` contract and message wire format, and [envs_core](envs_core.md) for how `UnityEnvironment` registers side channels and drives the overall step loop.

## Core Components

| Component | Direction | Purpose |
|---|---|---|
| `EngineConfigurationChannel` | Python → Unity | Configures Unity engine runtime settings (screen resolution, quality, time scale, frame rates) |
| `EnvironmentParametersChannel` | Python → Unity | Sends environment/curriculum parameters, including fixed values and randomization samplers |
| `FloatPropertiesChannel` | Bidirectional | Generic key/float property exchange, readable and writable from both sides |
| `RawBytesChannel` | Bidirectional | Generic raw-byte message exchange for custom research use cases |
| `StatsSideChannel` | Unity → Python | Collects arbitrary (string, float) statistics emitted by the Unity environment for reporting |
| `DefaultTrainingAnalyticsSideChannel` | Python → Unity | Sends anonymized training-environment initialization analytics to Unity |

Each channel is uniquely identified by a fixed `uuid.UUID` (`channel_id`), which the `SideChannelManager` uses to route incoming byte blobs to the correct handler and to tag outgoing messages.

### EngineConfigurationChannel

Configures Unity's rendering/simulation engine. It is **write-only from Python's perspective** — Unity never sends the engine configuration back, so `on_message_received` always raises `UnityCommunicationException` if invoked.

Key API:
- `set_configuration_parameters(width, height, quality_level, time_scale, target_frame_rate, capture_frame_rate)` — queues one `OutgoingMessage` per non-`None` parameter, each tagged with an `EngineConfigurationChannel.ConfigurationType` enum discriminator (`SCREEN_RESOLUTION`, `QUALITY_LEVEL`, `TIME_SCALE`, `TARGET_FRAME_RATE`, `CAPTURE_FRAME_RATE`).
- `set_configuration(config: EngineConfig)` — convenience wrapper around a `NamedTuple` bundling all engine settings, with `EngineConfig.default_config()` providing sane defaults (80x80, quality 1, time_scale 20.0, uncapped target frame rate, 60 capture frame rate).

```mermaid
sequenceDiagram
    participant Trainer as Training Script / EngineSettings
    participant ECC as EngineConfigurationChannel
    participant OM as OutgoingMessage
    participant SCM as SideChannelManager
    participant Unity as Unity Environment

    Trainer->>ECC: set_configuration_parameters(width=84, height=84, time_scale=20)
    ECC->>OM: write_int32(ConfigurationType), write_int32/float32(value)
    ECC->>ECC: queue_message_to_send(msg) [inherited]
    SCM->>ECC: generate_side_channel_messages()
    SCM->>Unity: packed bytes (channel_id + length + payload)
    Unity->>Unity: applies engine settings
```

### EnvironmentParametersChannel

Used to push environment/curriculum parameters (fixed floats or randomization samplers) into the Unity simulation, commonly driven by `EnvironmentParameterManager` in the [trainers_core](trainers_core.md) module.

Key API:
- `set_float_parameter(key, value)` — sends a fixed float value tagged as `EnvironmentDataTypes.FLOAT`.
- `set_uniform_sampler_parameters(key, min_value, max_value, seed)` — configures a uniform-distribution sampler (`SamplerTypes.UNIFORM`).
- `set_gaussian_sampler_parameters(key, mean, st_dev, seed)` — configures a Gaussian sampler (`SamplerTypes.GAUSSIAN`).
- `set_multirangeuniform_sampler_parameters(key, intervals, seed)` — configures a multi-interval uniform sampler (`SamplerTypes.MULTIRANGEUNIFORM`), flattening the interval tuples before writing as a float list.

Like `EngineConfigurationChannel`, this channel is write-only from Python; any inbound message triggers `UnityCommunicationException`.

```mermaid
flowchart LR
    A[EnvironmentParameterManager] -->|set_float_parameter / set_*_sampler_parameters| B(EnvironmentParametersChannel)
    B -->|OutgoingMessage: key, DataType, [seed, SamplerType], values| C[SideChannelManager]
    C -->|serialized bytes| D[Unity Environment]
    D -->|applies curriculum / randomization each episode| D
```

### FloatPropertiesChannel

A general-purpose, **bidirectional** key→float store shared between Python and Unity. Unlike the configuration channels, it maintains local state (`_float_properties` dict) so Python can also read values pushed by Unity.

Key API:
- `set_property(key, value)` — updates local cache and sends an `OutgoingMessage`.
- `get_property(key)` — reads from local cache (returns `None` if unknown).
- `list_properties()` — lists all known keys.
- `get_property_dict_copy()` — snapshot of the full dict.
- `on_message_received(msg)` — parses `(string, float32)` pairs sent by Unity and updates the cache.

Note there is a Unity-side (C#) counterpart of the same name (`FloatPropertiesChannel` in [runtime_sidechannels](runtime_sidechannels.md)) implementing the mirrored behavior in C#.

### RawBytesChannel

A minimal, general-research channel for exchanging arbitrary byte payloads. It buffers all received messages in `_received_messages` until drained via `get_and_clear_received_messages()`. Sending is via `send_raw_data(data: bytearray)`. Unlike the other channels, its `channel_id` is **not fixed** — it must be supplied by the caller, allowing multiple independent raw-byte channels to coexist. This mirrors the C# `RawBytesChannel` in [runtime_sidechannels](runtime_sidechannels.md).

### StatsSideChannel

Receives arbitrary `(string key, float value, StatsAggregationMethod)` triples emitted by the Unity environment (e.g., custom reward diagnostics, environment-side metrics) and buffers them for later consumption.

- `StatsAggregationMethod` enum defines how repeated values within a summary window should be combined: `AVERAGE`, `MOST_RECENT`, `SUM`, `HISTOGRAM`.
- `stats: EnvironmentStats` is a `defaultdict(list)` mapping key → list of `(value, aggregation_method)` tuples.
- `get_and_reset_stats()` atomically returns and clears the buffer — typically called once per training step by the environment manager so accumulated stats can be forwarded to `StatsReporter` (see [trainers_core](trainers_core.md)).

```mermaid
sequenceDiagram
    participant Unity as Unity Environment
    participant SCM as SideChannelManager
    participant SSC as StatsSideChannel
    participant EnvMgr as EnvManager / SubprocessEnvManager
    participant Reporter as StatsReporter

    Unity->>SCM: raw side-channel bytes (per step)
    SCM->>SSC: on_message_received(IncomingMessage)
    SSC->>SSC: stats[key].append((val, agg_type))
    EnvMgr->>SSC: get_and_reset_stats()
    SSC-->>EnvMgr: EnvironmentStats
    EnvMgr->>Reporter: add_stat(...) per key
```

### DefaultTrainingAnalyticsSideChannel

Sends a one-time `TrainingEnvironmentInitialized` protobuf analytics event to Unity when a training session starts, containing Python/mlagents_envs version info. It deliberately **shares the same fixed `channel_id`** as `TrainingAnalyticsSideChannel` (see [trainers_core](trainers_core.md)) — only one of the two is normally registered in a given run, letting the trainer package substitute a richer implementation (with actual `mlagents` version and torch device info) when available, while `mlagents_envs` alone still provides a working default.

- `environment_initialized()` — packs a `TrainingEnvironmentInitialized` protobuf message into a `google.protobuf.Any`, serializes it, and queues it as raw bytes via `OutgoingMessage.set_raw_bytes`.
- Like the configuration channels, it is write-only; receiving a message from Unity raises `UnityCommunicationException`.

```mermaid
classDiagram
    class SideChannel {
        <<abstract>>
        +channel_id: UUID
        +message_queue: List~bytearray~
        +queue_message_to_send(msg)
        +on_message_received(msg)*
    }
    class EngineConfigurationChannel {
        +ConfigurationType
        +set_configuration_parameters(...)
        +set_configuration(config)
    }
    class EnvironmentParametersChannel {
        +EnvironmentDataTypes
        +SamplerTypes
        +set_float_parameter(key, value)
        +set_uniform_sampler_parameters(...)
        +set_gaussian_sampler_parameters(...)
        +set_multirangeuniform_sampler_parameters(...)
    }
    class FloatPropertiesChannel {
        -_float_properties: Dict
        +set_property(key, value)
        +get_property(key)
        +list_properties()
        +get_property_dict_copy()
    }
    class RawBytesChannel {
        -_received_messages: List~bytes~
        +get_and_clear_received_messages()
        +send_raw_data(data)
    }
    class StatsSideChannel {
        +stats: EnvironmentStats
        +get_and_reset_stats()
    }
    class DefaultTrainingAnalyticsSideChannel {
        +CHANNEL_ID: UUID
        +environment_initialized()
    }

    SideChannel <|-- EngineConfigurationChannel
    SideChannel <|-- EnvironmentParametersChannel
    SideChannel <|-- FloatPropertiesChannel
    SideChannel <|-- RawBytesChannel
    SideChannel <|-- StatsSideChannel
    SideChannel <|-- DefaultTrainingAnalyticsSideChannel
```

## End-to-End Data Flow

The diagram below shows how these channels fit into the overall Python↔Unity communication cycle, orchestrated by `UnityEnvironment` and `SideChannelManager` (both in [envs_core](envs_core.md)).

```mermaid
sequenceDiagram
    participant User as Trainer / User Script
    participant Env as UnityEnvironment
    participant SCM as SideChannelManager
    participant Channels as Side Channels (this module)
    participant Unity as Unity Executable

    User->>Env: UnityEnvironment(side_channels=[ECC, EPC, FPC, SSC, ...])
    Env->>SCM: register side_channels (by channel_id)
    User->>Channels: set_configuration_parameters() / set_float_parameter() / set_property()
    Channels->>Channels: queue_message_to_send(OutgoingMessage)
    User->>Env: env.step()
    Env->>SCM: generate_side_channel_messages()
    SCM-->>Env: packed bytes (all channels)
    Env->>Unity: gRPC message including side-channel bytes
    Unity-->>Env: gRPC response including side-channel bytes
    Env->>SCM: process_side_channel_message(data)
    SCM->>Channels: on_message_received(IncomingMessage) [per channel_id]
    Channels-->>User: get_property() / get_and_reset_stats() / get_and_clear_received_messages()
```

## Wire Format Recap

Every message queued by a channel is a raw byte buffer built with `OutgoingMessage`. When gathered by `SideChannelManager.generate_side_channel_messages()`, each message is framed as:

```
[16 bytes: channel_id (UUID, little-endian)] [4 bytes: message length (int32)] [message bytes...]
```

Multiple framed messages from multiple channels are concatenated together into a single payload sent over the gRPC/communicator transport (see `RpcCommunicator` in [envs_core_communicator](envs_core.md)). On the receiving side, `SideChannelManager.process_side_channel_message()` walks the buffer, extracts each frame by `channel_id`, and dispatches it via `on_message_received`.

## Usage in the Broader System

- **Training orchestration**: `EnvironmentParameterManager` and `EngineSettings`/`RunOptions` (in [trainers_core](trainers_core.md)) use `EnvironmentParametersChannel` and `EngineConfigurationChannel` to drive curriculum learning and control simulation speed/quality during training.
- **Statistics pipeline**: `StatsSideChannel` output feeds into `StatsReporter` writers (`ConsoleWriter`, `TensorboardWriter`) documented in [trainers_core](trainers_core.md).
- **Analytics**: `DefaultTrainingAnalyticsSideChannel` is the fallback used when the fuller `TrainingAnalyticsSideChannel` (in [trainers_core](trainers_core.md)) is not present; both share a channel ID so Unity only needs a single consumer implementation.
- **Environment wrappers**: Gym/PettingZoo wrappers in [envs_wrappers](envs_wrappers.md) construct `UnityEnvironment` instances that may be pre-configured with these channels (e.g., to fix engine settings or pass environment parameters at construction time).
- **Unity-side counterparts**: `EngineConfigurationChannel`, `FloatPropertiesChannel`, and `RawBytesChannel` have matching C# implementations under [runtime_sidechannels](runtime_sidechannels.md), completing the cross-language protocol.

## Related Documentation

- [envs_sidechannel_framework](envs_sidechannel_framework.md) — abstract `SideChannel` base class, `IncomingMessage`/`OutgoingMessage` serialization primitives, and `SideChannelManager` routing logic.
- [envs_core](envs_core.md) — `UnityEnvironment` and communicator layer that transports side-channel bytes between Python and Unity.
- [envs_wrappers](envs_wrappers.md) — Gym/PettingZoo environment wrappers that consume `UnityEnvironment` (and therefore these channels).
- [trainers_core](trainers_core.md) — `EnvironmentParameterManager`, `StatsReporter`, and `TrainingAnalyticsSideChannel`, the primary Python-side consumers of these channels during training.
- [runtime_sidechannels](runtime_sidechannels.md) — C#/Unity-side counterparts of `FloatPropertiesChannel` and `RawBytesChannel`.
