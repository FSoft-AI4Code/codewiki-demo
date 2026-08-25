# Unity Editor Tooling

## 1. Purpose

The **Unity_Editor_Tooling** module contains all Unity Editor–only (design-time) extensions for the ML-Agents Unity package, located under `com.unity.ml-agents/Editor`. It has no role in the runtime game loop or in training — its sole purpose is to make configuring ML-Agents components inside the Unity Editor safer and more convenient. It provides:

- Custom Inspector UIs for every sensor and actuator `MonoBehaviour` component shipped with the package (Camera, Ray Perception, Grid, Buffer, Vector, Render Texture, Rigid Body, Match-3, Input).
- Custom Inspectors/Drawers for the core agent-configuration types: `Agent`, `BehaviorParameters`, and the `BrainParameters` struct, including live validation of a `BehaviorParameters`' assigned model against the Agent's sensors/actuators.
- Asset-pipeline tooling (`ScriptedImporter` + `CustomEditor`) to import and preview `.demo` demonstration recording files as Unity assets.
- Build-pipeline hooks that ensure the project's `MLAgentsSettings` asset is correctly preloaded into player builds.

A recurring theme across the module is **Play-mode safety**: fields that would change the shape of an observation/action tensor (names, sizes, counts) are disabled while the game is running, guarded via the shared `EditorUtilities.CanUpdateModelProperties()` helper, preventing silent desynchronization between a trained model and a live component.

## 2. Architecture Overview

The module is organized into two cohesive sub-modules, both living under `com.unity.ml-agents/Editor`, each targeting a different family of runtime types.

```mermaid
graph TB
    subgraph Unity_Editor_Tooling
        subgraph editor_component_inspectors["Editor Component Inspectors"]
            BSE[BufferSensorComponentEditor]
            CSE[CameraSensorComponentEditor]
            GSE[GridSensorComponentEditor]
            IAE[InputActuatorComponentEditor]
            M3AE[Match3ActuatorComponentEditor]
            M3SE[Match3SensorComponentEditor]
            RPE[RayPerceptionSensorComponent2D/3DEditor]
            RTSE[RenderTextureSensorComponentEditor]
            RBSE[RigidBodySensorComponentEditor]
            VSE[VectorSensorComponentEditor]
        end

        subgraph editor_core["Editor Core"]
            AE[AgentEditor]
            BPE[BehaviorParametersEditor]
            BPD[BrainParametersDrawer]
            DE[DemonstrationEditor]
            DI[DemonstrationImporter]
            BP[MLAgentsSettingsBuildProvider]
        end
    end

    subgraph Runtime["Runtime Modules (other packages)"]
        RS[runtime_sensors]
        RIM[runtime_integrations_match3]
        RI[runtime_input]
        RCA[runtime_core_agent / foundation]
        RINF[runtime_inference]
        RDEM[runtime_demonstrations]
    end

    editor_component_inspectors -->|CustomEditor targets| RS
    editor_component_inspectors -->|CustomEditor targets| RIM
    editor_component_inspectors -->|CustomEditor targets| RI
    editor_component_inspectors -->|uses CanUpdateModelProperties| editor_core

    AE -->|CustomEditor| RCA
    BPE -->|CustomEditor + model validation| RINF
    BPE -->|reads| RS
    DE -->|CustomEditor| RDEM
    DI -->|ScriptedImporter| RDEM
    BP -->|Build hooks| RCA
```

### Shared inspector pattern

Both sub-modules apply the same guarding pattern to protect against unsafe edits at runtime:

```mermaid
flowchart TD
    A[OnInspectorGUI / OnGUI] --> B[serializedObject.Update]
    B --> C[EditorGUI.BeginChangeCheck]
    C --> D["Draw shape-affecting fields\ninside BeginDisabledGroup(!CanUpdateModelProperties)"]
    D --> E[Draw freely-editable fields]
    E --> F[EditorGUI.EndChangeCheck]
    F --> G[serializedObject.ApplyModifiedProperties]
    G --> H{Changed AND not Play mode?}
    H -->|yes| I[Re-initialize component:\nUpdateSensor / UpdateActuator / ResetPoseExtractor]
    H -->|no| J[Done]
```

## 3. Core Components / Sub-modules

### 3.1 Editor Component Inspectors
Custom Inspectors for every sensor and actuator component (`BufferSensorComponentEditor`, `CameraSensorComponentEditor`, `GridSensorComponentEditor`, `RayPerceptionSensorComponentBaseEditor` and its 2D/3D subclasses, `RenderTextureSensorComponentEditor`, `RigidBodySensorComponentEditor`, `VectorSensorComponentEditor`, `Match3SensorComponentEditor`, `Match3ActuatorComponentEditor`, `InputActuatorComponentEditor`). Each is a 1:1 (or shared-base) `[CustomEditor]` wrapper around a runtime `*Component` class, locking shape-affecting fields during Play mode and triggering re-initialization on change.

📄 See [editor_component_inspectors](editor_component_inspectors.md) for full details.

### 3.2 Editor Core
Higher-level tooling covering:
- **Agent & Behavior Inspectors** — `AgentEditor`, `BehaviorParametersEditor`, `BrainParametersDrawer`, which render/edit the Agent and its Behavior/Brain configuration and validate the assigned Sentis model against sensors/actuators.
- **Demonstration Tooling** — `DemonstrationImporter` (ScriptedImporter for `.demo` files) and `DemonstrationEditor`, which parse and preview recorded demonstration data as Unity assets.
- **Build Pipeline Integration** — `MLAgentsSettingsBuildProvider`, an `IPreprocessBuildWithReport`/`IPostprocessBuildWithReport` implementation that temporarily preloads the `MLAgentsSettings` asset for player builds.

📄 See [editor_core](editor_core.md) for full details.

## 4. Cross-Module References

- **[editor_component_inspectors](editor_component_inspectors.md)** — sensor/actuator component inspectors; depends on `editor_core`'s `EditorUtilities.CanUpdateModelProperties()`.
- **[editor_core](editor_core.md)** — Agent/Behavior/BrainParameters inspectors, demonstration asset tooling, and build pipeline hooks.
- **[runtime_sensors](runtime_sensors.md)** / **[runtime_integrations_match3](runtime_integrations_match3.md)** / **[runtime_input](runtime_input.md)** — runtime components edited by `editor_component_inspectors`.
- **[runtime_core_agent](runtime_core_agent.md)** — runtime `Agent`/behavior types edited by `editor_core`'s Agent & Behavior inspectors.
- **[runtime_inference](runtime_inference.md)** — `SentisModelParamLoader`, used by `BehaviorParametersEditor` for model/sensor compatibility validation.
- **[runtime_demonstrations](runtime_demonstrations.md)** — `DemonstrationSummary`/`DemonstrationRecorder`, consumed by `DemonstrationImporter`/`DemonstrationEditor`.