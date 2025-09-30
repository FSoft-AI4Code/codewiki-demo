# Dataset Controller Module

## Introduction

The Dataset Controller module is a fundamental component of Chart.js that manages individual datasets within a chart. It serves as the bridge between raw data and visual representation, handling data parsing, scaling, stacking, and element management. This module provides the base class that all specific chart type controllers (line, bar, pie, etc.) extend to implement their unique behaviors.

## Architecture Overview

The DatasetController acts as an abstract base class that orchestrates the relationship between data, scales, and visual elements. It manages the complete lifecycle of dataset rendering, from initial data parsing through final visual representation.

```mermaid
graph TB
    subgraph "Dataset Controller Architecture"
        DC[DatasetController]
        
        subgraph "Data Management"
            DP[Data Parsing]
            DS[Data Storage]
            DCN[Data Conversion]
        end
        
        subgraph "Scale Integration"
            LS[Link Scales]
            SV[Scale Values]
            SR[Scale Ranges]
        end
        
        subgraph "Element Management"
            DE[Dataset Elements]
            VE[Visual Elements]
            EM[Element Updates]
        end
        
        subgraph "Stacking System"
            SS[Stack Detection]
            SU[Stack Updates]
            SV2[Stack Values]
        end
        
        subgraph "Animation System"
            AS[Animation Setup]
            AU[Animation Updates]
            AR[Animation Resolution]
        end
        
        DC --> DP
        DC --> DS
        DC --> DCN
        DC --> LS
        DC --> SV
        DC --> SR
        DC --> DE
        DC --> VE
        DC --> EM
        DC --> SS
        DC --> SU
        DC --> SV2
        DC --> AS
        DC --> AU
        DC --> AR
    end
```

## Core Components

### DatasetController Class

The `DatasetController` class is the central component that manages dataset operations. It provides a comprehensive API for data manipulation, scale integration, and element lifecycle management.

#### Key Properties

- **chart**: Reference to the parent chart instance
- **_cachedMeta**: Cached metadata about the dataset
- **_data**: The actual dataset data
- **options**: Merged dataset configuration options
- **_parsing**: Parsing configuration for data transformation
- **datasetElementType**: Type of element for dataset representation
- **dataElementType**: Type of element for individual data points

#### Constructor and Initialization

```mermaid
sequenceDiagram
    participant Chart
    participant DatasetController
    participant Scales
    participant Elements
    
    Chart->>DatasetController: new DatasetController(chart, index)
    DatasetController->>DatasetController: initialize()
    DatasetController->>DatasetController: configure()
    DatasetController->>DatasetController: linkScales()
    DatasetController->>Scales: getScaleForId()
    DatasetController->>DatasetController: addElements()
    DatasetController->>Elements: create dataset/data elements
```

## Data Flow Architecture

### Data Processing Pipeline

The dataset controller implements a sophisticated data processing pipeline that handles various data formats and ensures proper integration with scales.

```mermaid
graph LR
    subgraph "Data Input"
        RAW[Raw Data]
        ARR[Array Data]
        OBJ[Object Data]
        PRI[Primitive Data]
    end
    
    subgraph "Parsing Process"
        DC{Data Check}
        PD[Parse Data]
        PPA[Parse Primitive Array]
        PAO[Parse Array of Objects]
        PAA[Parse Array of Arrays]
    end
    
    subgraph "Scale Integration"
        SP[Scale Parsing]
        SV3[Scale Values]
        PS[Parsed Storage]
    end
    
    subgraph "Output"
        META[Metadata]
        ELEM[Elements]
        REND[Render Ready]
    end
    
    RAW --> DC
    ARR --> PD
    OBJ --> PD
    PRI --> PD
    
    DC --> PPA
    DC --> PAO
    DC --> PAA
    
    PPA --> SP
    PAO --> SP
    PAA --> SP
    
    SP --> SV3
    SV3 --> PS
    PS --> META
    META --> ELEM
    ELEM --> REND
```

### Data Parsing Methods

The controller supports three primary data parsing strategies:

1. **Primitive Data Parsing**: Handles simple arrays of values
2. **Array Data Parsing**: Processes arrays of coordinate pairs
3. **Object Data Parsing**: Manages complex objects with configurable property keys

## Scale Integration

### Scale Linking System

The dataset controller automatically links datasets to appropriate scales based on axis configuration and chart type.

```mermaid
graph TB
    subgraph "Scale Linking Process"
        DS[Dataset]
        CFG[Configuration]
        
        subgraph "Axis Detection"
            XID[X Axis ID]
            YID[Y Axis ID]
            RID[R Axis ID]
            IDX[Index Axis]
        end
        
        subgraph "Scale Assignment"
            XS[X Scale]
            YS[Y Scale]
            RS[R Scale]
            IS[Index Scale]
            VS[Value Scale]
        end
        
        subgraph "Metadata Storage"
            META[Cached Meta]
            SM[Scale Mappings]
        end
        
        DS --> CFG
        CFG --> XID
        CFG --> YID
        CFG --> RID
        CFG --> IDX
        
        XID --> XS
        YID --> YS
        RID --> RS
        IDX --> IS
        IDX --> VS
        
        XS --> META
        YS --> META
        RS --> META
        IS --> META
        VS --> META
        META --> SM
    end
```

### Scale Range Calculation

The controller calculates appropriate scale ranges by analyzing parsed data values and applying stacking logic when enabled.

## Stacking System

### Stack Detection and Management

The stacking system automatically detects when datasets should be stacked and manages stack values across multiple datasets.

```mermaid
graph LR
    subgraph "Stack Detection"
        SC[Scale Configuration]
        DS2[Dataset Stack]
        SD[Stack Detection]
    end
    
    subgraph "Stack Key Generation"
        IS2[Index Scale]
        VS2[Value Scale]
        SK[Stack Key]
    end
    
    subgraph "Stack Updates"
        US[Update Stacks]
        SV4[Stack Values]
        TB[Top/Bottom]
    end
    
    subgraph "Value Application"
        AS2[Apply Stack]
        UV[Updated Values]
        VR[Value Range]
    end
    
    SC --> SD
    DS2 --> SD
    SD --> SK
    IS2 --> SK
    VS2 --> SK
    SK --> US
    US --> SV4
    SV4 --> TB
    TB --> AS2
    AS2 --> UV
    UV --> VR
```

### Stack Value Calculation

The system supports multiple stacking modes including single-mode stacking and maintains visual stack values for proper rendering.

## Element Lifecycle Management

### Element Creation and Updates

The controller manages the complete lifecycle of visual elements, from creation through updates and removal.

```mermaid
sequenceDiagram
    participant DC as DatasetController
    participant Meta as Metadata
    participant Data as Data Array
    participant Elem as Elements
    
    DC->>DC: buildOrUpdateElements()
    DC->>Data: _dataCheck()
    DC->>Meta: Check stack changes
    alt Stack changed
        DC->>Meta: clearStacks()
        DC->>Meta: Update stack metadata
    end
    DC->>DC: _resyncElements()
    DC->>Data: parse data
    
    alt More data than elements
        DC->>Elem: _insertElements()
        DC->>Elem: create new elements
        DC->>Elem: updateElements()
    else Fewer data than elements
        DC->>Elem: _removeElements()
    end
    
    DC->>Elem: Final element updates
```

### Element Options Resolution

The controller implements a sophisticated options resolution system that merges dataset-level options with element-specific configurations and applies animations appropriately.

## Animation Integration

### Animation System Integration

The dataset controller integrates with the animation system to provide smooth transitions during data updates and interactions.

```mermaid
graph TB
    subgraph "Animation Integration"
        DC2[DatasetController]
        
        subgraph "Animation Resolution"
            AR2[_resolveAnimations]
            AS3[Animation Scopes]
            AO[Animation Options]
        end
        
        subgraph "Element Updates"
            UE[updateElement]
            USO[updateSharedOptions]
            SU2[_setStyle]
        end
        
        subgraph "Animation Types"
            DA[Direct Animation]
            IA[Interpolated Animation]
            SA[Style Animation]
        end
        
        DC2 --> AR2
        AR2 --> AS3
        AS3 --> AO
        AO --> UE
        AO --> USO
        AO --> SU2
        UE --> DA
        UE --> IA
        USO --> IA
        SU2 --> SA
    end
```

## Configuration System Integration

### Options Merging and Resolution

The controller works with the configuration system to merge user-supplied options with defaults and resolve them appropriately for different contexts.

See [configuration-system.md](configuration-system.md) for detailed information about the configuration system.

## Registry System Integration

### Controller Registration

Dataset controllers are managed through the registry system, allowing for dynamic registration and retrieval of controller types.

See [registry-system.md](registry-system.md) for detailed information about the registry system.

## Data Synchronization

### Array Event Handling

The controller implements sophisticated array event handling to detect data changes and synchronize the internal state accordingly.

```mermaid
graph LR
    subgraph "Data Synchronization"
        DE2[Data Events]
        
        subgraph "Event Handlers"
            PUSH[_onDataPush]
            POP[_onDataPop]
            SHIFT[_onDataShift]
            SPLICE[_onDataSplice]
            UNSHIFT[_onDataUnshift]
        end
        
        subgraph "Synchronization"
            SYNC[_sync]
            SYL[_syncList]
            UP[Update Operations]
        end
        
        subgraph "Chart Updates"
            DC3[Data Changes]
            RD[Re-parse Data]
            UE2[Update Elements]
        end
        
        DE2 --> PUSH
        DE2 --> POP
        DE2 --> SHIFT
        DE2 --> SPLICE
        DE2 --> UNSHIFT
        
        PUSH --> SYNC
        POP --> SYNC
        SHIFT --> SYNC
        SPLICE --> SYNC
        UNSHIFT --> SYNC
        
        SYNC --> SYL
        SYL --> UP
        UP --> DC3
        DC3 --> RD
        RD --> UE2
    end
```

## Interaction with Other Modules

### Scale System Integration

The dataset controller works closely with the scale system to ensure proper data mapping and range calculation.

See [scale-system.md](scale-system.md) for detailed information about scales.

### Animation System Integration

The controller leverages the animation system for smooth transitions during data updates and state changes.

See [animation-system.md](animation-system.md) for detailed information about animations.

### Element System Integration

The controller manages element creation and updates, working with the element system to provide visual representations.

See [elements.md](elements.md) for detailed information about elements.

## Process Flows

### Dataset Update Process

```mermaid
sequenceDiagram
    participant Chart
    participant DC as DatasetController
    participant Scales
    participant Elements
    
    Chart->>DC: update dataset
    DC->>DC: _update(mode)
    DC->>DC: update(mode)
    DC->>DC: configure()
    DC->>DC: linkScales()
    DC->>Scales: get scale references
    DC->>DC: buildOrUpdateElements()
    DC->>DC: _dataCheck()
    DC->>DC: parse data
    DC->>Elements: update elements
    DC->>DC: _clip calculation
    DC->>Chart: update complete
```

### Data Parsing Process

```mermaid
flowchart TD
    Start[Data Update] --> Check{Parsing Enabled?}
    Check -->|No| Store[Store Raw Data]
    Check -->|Yes| Type{Data Type?}
    
    Type -->|Array of Primitives| ParsePrimitive[parsePrimitiveData]
    Type -->|Array of Arrays| ParseArray[parseArrayData]
    Type -->|Array of Objects| ParseObject[parseObjectData]
    
    ParsePrimitive --> ScaleParse[Scale.parse]
    ParseArray --> ScaleParse
    ParseObject --> ScaleParse
    
    ScaleParse --> SortCheck{Check Sorting}
    SortCheck -->|Sorted| StoreParsed[Store Parsed Data]
    SortCheck -->|Not Sorted| MarkUnsorted[Mark as Unsorted]
    
    StoreParsed --> StackCheck{Stacked?}
    MarkUnsorted --> StackCheck
    Store --> StackCheck
    
    StackCheck -->|Yes| UpdateStacks[updateStacks]
    StackCheck -->|No| Finish[Finish]
    UpdateStacks --> Finish
```

## Key Features

### Automatic Scale Detection

The controller automatically detects and links to appropriate scales based on dataset configuration and chart type.

### Flexible Data Parsing

Supports multiple data formats including primitive arrays, coordinate arrays, and complex objects with configurable property mapping.

### Intelligent Stacking

Automatically detects stacking requirements and manages stack values across multiple datasets with support for different stacking modes.

### Real-time Data Updates

Provides comprehensive array event handling for real-time data updates with proper synchronization and animation support.

### Context-Aware Options

Implements sophisticated options resolution that considers dataset context, element state, and animation requirements.

### Performance Optimization

Includes multiple optimization strategies such as option sharing, caching mechanisms, and efficient update algorithms.

## Usage Patterns

### Extending DatasetController

Specific chart types extend the base DatasetController to implement their unique behaviors:

```javascript
export default class CustomController extends DatasetController {
  static defaults = {
    // Custom defaults
  };
  
  static datasetElementType = CustomDatasetElement;
  static dataElementType = CustomDataElement;
  
  update(mode) {
    // Custom update logic
  }
  
  updateElements(elements, start, count, mode) {
    // Custom element updates
  }
}
```

### Data Format Support

The controller supports various data formats through its parsing system:

- **Primitive arrays**: `[1, 2, 3, 4]`
- **Coordinate arrays**: `[[1, 2], [3, 4]]`
- **Object arrays**: `[{x: 1, y: 2}, {x: 3, y: 4}]`
- **Object mapping**: `{"label1": 10, "label2": 20}`

This comprehensive data handling makes the DatasetController a versatile foundation for all chart types in the Chart.js ecosystem.