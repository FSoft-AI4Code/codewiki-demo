# Visual Sensors Module

The visual_sensors module provides camera-based observation capabilities for Unity ML-Agents, enabling agents to perceive their environment through visual input. This module is part of the broader [unity_sensors](unity_sensors.md) system and specializes in capturing and processing visual observations from Unity Camera components.

## Overview

Visual sensors transform Unity Camera outputs into structured observations that can be consumed by machine learning models. The module handles image capture, format conversion, compression, and integration with the ML-Agents observation pipeline. It supports both color and grayscale observations with configurable resolution and compression settings.

## Architecture

```mermaid
graph TB
    subgraph "Visual Sensors Module"
        CSC[CameraSensorComponent]
        CS[CameraSensor]
        
        subgraph "Core Interfaces"
            ISensor[ISensor Interface]
            IBuiltIn[IBuiltInSensor Interface]
            SensorComp[SensorComponent Base]
        end
        
        subgraph "Unity Integration"
            Camera[Unity Camera]
            RT[RenderTexture]
            Tex2D[Texture2D]
        end
        
        subgraph "Observation Pipeline"
            ObsSpec[ObservationSpec]
            ObsWriter[ObservationWriter]
            CompSpec[CompressionSpec]
        end
    end
    
    CSC --> CS
    CSC -.->|inherits| SensorComp
    CS -.->|implements| ISensor
    CS -.->|implements| IBuiltIn
    
    CS --> Camera
    CS --> RT
    CS --> Tex2D
    
    CS --> ObsSpec
    CS --> ObsWriter
    CS --> CompSpec
    
    Camera --> RT
    RT --> Tex2D
```

## Core Components

### CameraSensor

The `CameraSensor` class is the primary component that wraps a Unity Camera to generate visual observations.

**Key Features:**
- **Camera Integration**: Direct integration with Unity Camera components
- **Format Support**: Both color (RGB) and grayscale observations
- **Compression**: PNG compression for efficient data transmission
- **Resolution Control**: Configurable width and height for observations
- **Performance Optimization**: Efficient texture rendering and memory management

**Core Methods:**
- `Update()`: Captures current camera frame to internal texture
- `Write(ObservationWriter)`: Writes uncompressed observation data
- `GetCompressedObservation()`: Returns PNG-compressed image data
- `ObservationToTexture()`: Static utility for camera-to-texture rendering

### CameraSensorComponent

The `CameraSensorComponent` provides Unity Editor integration and configuration management for camera sensors.

**Configuration Options:**
- **Camera Reference**: Target Unity Camera component
- **Resolution**: Width and height of captured observations
- **Color Mode**: Grayscale or color (RGB) output
- **Compression**: PNG compression settings
- **Observation Stacking**: Support for temporal observation stacking
- **Runtime Control**: Enable/disable camera during runtime for performance

## Data Flow

```mermaid
sequenceDiagram
    participant Agent
    participant CSC as CameraSensorComponent
    participant CS as CameraSensor
    participant Camera as Unity Camera
    participant RT as RenderTexture
    participant Tex2D as Texture2D
    participant Pipeline as ML Pipeline
    
    Agent->>CSC: Initialize Sensors
    CSC->>CS: Create CameraSensor
    
    loop Each Agent Step
        Agent->>CS: Update()
        CS->>Camera: Render to RenderTexture
        Camera->>RT: Generate Frame
        CS->>RT: ReadPixels()
        RT->>Tex2D: Copy Pixel Data
        
        Agent->>CS: Write(ObservationWriter)
        CS->>Tex2D: Extract Pixel Data
        CS->>Pipeline: Write Observation
        
        alt Compression Enabled
            Agent->>CS: GetCompressedObservation()
            CS->>Tex2D: EncodeToPNG()
            CS->>Pipeline: Return Compressed Data
        end
    end
```

## Integration with Unity ML-Agents

### Sensor Infrastructure Integration

The visual sensors module integrates with the broader sensor infrastructure:

```mermaid
graph LR
    subgraph "Agent System"
        Agent[Agent]
        SensorManager[Sensor Manager]
    end
    
    subgraph "Visual Sensors"
        CSC[CameraSensorComponent]
        CS[CameraSensor]
    end
    
    subgraph "Sensor Infrastructure"
        ISensor[ISensor Interface]
        ObsSpec[ObservationSpec]
        StackingSensor[StackingSensor]
    end
    
    subgraph "Training Pipeline"
        ObsWriter[ObservationWriter]
        Trainer[Trainer]
    end
    
    Agent --> SensorManager
    SensorManager --> CSC
    CSC --> CS
    CS --> ISensor
    CS --> ObsSpec
    CS --> StackingSensor
    CS --> ObsWriter
    ObsWriter --> Trainer
```

### Observation Specification

Visual sensors use the `ObservationSpec.Visual()` factory method to define their observation characteristics:

- **Shape**: `[channels, height, width]` where channels = 1 (grayscale) or 3 (RGB)
- **Dimension Properties**: Translational equivariance for height and width dimensions
- **Observation Type**: Default or goal-based observations

## Performance Considerations

### Memory Management

```mermaid
graph TD
    subgraph "Memory Lifecycle"
        Create[Create Texture2D]
        Render[Render to RenderTexture]
        Read[ReadPixels to Texture2D]
        Process[Process Observation]
        Dispose[Dispose Resources]
    end
    
    Create --> Render
    Render --> Read
    Read --> Process
    Process --> Render
    Process --> Dispose
    
    subgraph "Optimization Strategies"
        TempRT[Temporary RenderTexture]
        Reuse[Texture Reuse]
        Compression[PNG Compression]
    end
    
    Render --> TempRT
    Read --> Reuse
    Process --> Compression
```

### Performance Optimizations

1. **Temporary RenderTexture Usage**: Uses `RenderTexture.GetTemporary()` for efficient memory allocation
2. **Camera State Management**: Preserves and restores camera settings during rendering
3. **Conditional Camera Enabling**: Runtime camera control for performance optimization
4. **Compression Support**: PNG compression reduces data transmission overhead

## Configuration Examples

### Basic Camera Sensor Setup

```csharp
// Create camera sensor with standard settings
var cameraSensor = new CameraSensor(
    camera: myCamera,
    width: 84,
    height: 84,
    grayscale: false,
    name: "CameraSensor",
    compression: SensorCompressionType.PNG
);
```

### Component Configuration

```csharp
// Configure CameraSensorComponent in Unity Editor
cameraSensorComponent.Camera = myCamera;
cameraSensorComponent.Width = 128;
cameraSensorComponent.Height = 128;
cameraSensorComponent.Grayscale = true;
cameraSensorComponent.CompressionType = SensorCompressionType.PNG;
cameraSensorComponent.ObservationStacks = 4; // Stack 4 frames
```

## Dependencies

### Internal Dependencies
- **[sensor_infrastructure](sensor_infrastructure.md)**: Core sensor interfaces and specifications
- **[unity_runtime_core](unity_runtime_core.md)**: Agent integration and lifecycle management

### Unity Dependencies
- **UnityEngine.Camera**: Core camera functionality
- **UnityEngine.RenderTexture**: Render target management
- **UnityEngine.Texture2D**: Texture data processing
- **UnityEngine.Rendering**: Graphics pipeline integration

### External Dependencies
- **System.IDisposable**: Resource cleanup interface
- **PNG Encoding**: Built-in Unity texture compression

## Related Modules

- **[spatial_sensors](spatial_sensors.md)**: Ray-based perception sensors
- **[data_sensors](data_sensors.md)**: Vector and buffer-based sensors
- **[unity_actuators](unity_actuators.md)**: Action execution system
- **[training_core](training_core.md)**: Model training pipeline

## Best Practices

### Camera Setup
1. **Resolution Selection**: Balance observation quality with computational cost
2. **Color vs Grayscale**: Use grayscale for simpler environments to reduce data size
3. **Camera Positioning**: Ensure camera captures relevant environmental information
4. **Lighting Considerations**: Maintain consistent lighting for stable observations

### Performance Optimization
1. **Runtime Camera Control**: Disable cameras when not needed for training
2. **Observation Stacking**: Use temporal stacking for motion-dependent tasks
3. **Compression Usage**: Enable PNG compression for network training scenarios
4. **Resolution Tuning**: Start with lower resolutions and increase as needed

### Integration Guidelines
1. **Sensor Naming**: Use consistent, descriptive names for deterministic sensor ordering
2. **Multiple Cameras**: Consider multiple camera angles for complex environments
3. **Observation Types**: Use appropriate observation types for goal-conditioned tasks
4. **Memory Management**: Properly dispose of sensors to prevent memory leaks

The visual_sensors module provides a robust foundation for visual perception in Unity ML-Agents, enabling agents to learn from rich visual information while maintaining performance and flexibility in diverse training scenarios.