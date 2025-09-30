# Sensor Infrastructure Module

The sensor_infrastructure module provides the foundational specification system for all sensor observations in Unity ML-Agents. It defines the core data structures and metadata that describe how observations are structured, processed, and interpreted by the machine learning pipeline.

## Overview

This module serves as the cornerstone of the sensor system, providing standardized specifications that enable different sensor types to communicate their observation characteristics to the training infrastructure. The `ObservationSpec` class acts as a contract between sensors and the ML pipeline, ensuring consistent data interpretation across all sensor implementations.

## Core Components

### ObservationSpec

The `ObservationSpec` struct is the primary component that encapsulates all metadata about sensor observations, including dimensional properties, data types, and training usage patterns.

**Key Responsibilities:**
- Define observation tensor shapes and dimensions
- Specify dimensional properties for training optimization
- Categorize observation types for specialized handling
- Provide factory methods for common observation patterns

**Core Properties:**
- **Shape**: Defines the dimensional structure of observations
- **DimensionProperties**: Specifies properties of each dimension for training optimization
- **ObservationType**: Categorizes the observation for specialized processing
- **Rank**: Provides the number of dimensions in the observation tensor

## Architecture

```mermaid
graph TB
    subgraph "Sensor Infrastructure"
        OS[ObservationSpec]
        OS --> |defines| Shape[Shape Array]
        OS --> |specifies| DimProps[Dimension Properties]
        OS --> |categorizes| ObsType[Observation Type]
    end
    
    subgraph "Factory Methods"
        Vector[Vector Spec]
        Visual[Visual Spec]
        VarLen[Variable Length Spec]
        General[General Spec]
    end
    
    subgraph "Sensor Types"
        VS[Vector Sensors]
        CS[Camera Sensors]
        RS[Ray Perception Sensors]
        BS[Buffer Sensors]
    end
    
    Vector --> OS
    Visual --> OS
    VarLen --> OS
    General --> OS
    
    OS --> VS
    OS --> CS
    OS --> RS
    OS --> BS
    
    VS --> |uses| Vector
    CS --> |uses| Visual
    RS --> |uses| Vector
    BS --> |uses| VarLen
```

## Component Relationships

```mermaid
graph LR
    subgraph "Unity Sensors Module"
        SI[sensor_infrastructure]
        DS[data_sensors]
        VS[visual_sensors]
        SS[spatial_sensors]
    end
    
    subgraph "Unity Runtime Core"
        AC[agent_core]
        DM[decision_management]
    end
    
    subgraph "Training Infrastructure"
        TC[training_core]
        TA[training_algorithms]
    end
    
    SI --> |provides specs to| DS
    SI --> |provides specs to| VS
    SI --> |provides specs to| SS
    
    DS --> |sensor data to| AC
    VS --> |sensor data to| AC
    SS --> |sensor data to| AC
    
    AC --> |observations to| DM
    DM --> |training data to| TC
    TC --> |processed by| TA
```

## Data Flow

```mermaid
sequenceDiagram
    participant Sensor as Sensor Implementation
    participant Spec as ObservationSpec
    participant Agent as Agent Core
    participant Training as Training Pipeline
    
    Sensor->>Spec: Create specification
    Spec->>Spec: Validate dimensions
    Spec->>Agent: Provide observation metadata
    Agent->>Training: Forward spec with observations
    Training->>Training: Use spec for tensor processing
```

## Observation Specification Types

### Vector Observations
```mermaid
graph TD
    V[Vector Observation] --> |length| L[Length Parameter]
    V --> |type| T[Observation Type]
    V --> |creates| S1[1D Shape Array]
    V --> |sets| D1[None Dimension Property]
```

**Usage Pattern:**
- Numerical data arrays (velocities, positions, health values)
- Feature vectors from processed game state
- Scalar measurements and statistics

### Visual Observations
```mermaid
graph TD
    Vis[Visual Observation] --> |channels| C[Channels]
    Vis --> |height| H[Height]
    Vis --> |width| W[Width]
    Vis --> |creates| S2[3D Shape Array]
    Vis --> |sets| D2[Translational Equivariance Properties]
```

**Usage Pattern:**
- Camera sensor outputs
- Rendered game views
- Processed image data

### Variable Length Observations
```mermaid
graph TD
    VL[Variable Length] --> |obsSize| OS[Observation Size]
    VL --> |maxNumObs| MN[Max Number]
    VL --> |creates| S3[2D Shape Array]
    VL --> |sets| D3[Variable Size + None Properties]
```

**Usage Pattern:**
- Dynamic lists of entities
- Varying number of detected objects
- Flexible buffer-based observations

## Integration Points

### With Data Sensors
The sensor_infrastructure module provides specifications that [data_sensors](data_sensors.md) use to define their observation characteristics:
- Vector sensors use `Vector()` factory method
- Buffer sensors use `VariableLength()` factory method

### With Visual Sensors
[Visual_sensors](visual_sensors.md) rely on the infrastructure for camera-based observations:
- Camera sensors use `Visual()` factory method for RGB/grayscale images
- Supports translational equivariance properties for CNN optimization

### With Spatial Sensors
[Spatial_sensors](spatial_sensors.md) utilize vector specifications for ray-based perception:
- Ray perception sensors use `Vector()` for hit distance arrays
- 2D and 3D variants share the same specification pattern

### With Agent Core
The specifications flow to [agent_core](agent_core.md) where they inform:
- Observation collection and validation
- Tensor shape verification
- Training data preparation

## Training Pipeline Integration

```mermaid
graph TB
    subgraph "Observation Processing"
        Spec[ObservationSpec]
        Spec --> |shape info| TensorGen[Tensor Generation]
        Spec --> |dim properties| Optimizer[Training Optimization]
        Spec --> |obs type| Processor[Specialized Processing]
    end
    
    subgraph "Training Algorithms"
        PPO[PPO Trainer]
        SAC[SAC Trainer]
        POCA[POCA Trainer]
    end
    
    TensorGen --> PPO
    TensorGen --> SAC
    TensorGen --> POCA
    
    Optimizer --> PPO
    Optimizer --> SAC
    Optimizer --> POCA
```

## Dimension Properties

The module supports various dimension properties that optimize training:

- **None**: Standard dimensions without special properties
- **TranslationalEquivariance**: For spatial dimensions in visual data
- **VariableSize**: For dynamic dimensions in buffer observations

These properties inform the training algorithms about how to process different types of observations efficiently.

## Error Handling and Validation

The `ObservationSpec` constructor includes validation to ensure:
- Shape and dimension properties arrays have matching lengths
- Consistent specification across all sensor implementations
- Early detection of configuration errors

## Performance Considerations

- Uses `InplaceArray<T>` for memory-efficient storage
- Struct-based design minimizes allocation overhead
- Factory methods provide optimized common configurations
- Validation occurs at construction time, not during runtime observation processing

## Future Extensibility

The modular design allows for:
- New observation types through additional factory methods
- Extended dimension properties for specialized training algorithms
- Custom observation specifications for domain-specific sensors
- Integration with new ML frameworks and training approaches

This infrastructure module forms the foundation that enables the entire Unity ML-Agents sensor ecosystem to operate cohesively while maintaining flexibility for diverse observation types and training scenarios.