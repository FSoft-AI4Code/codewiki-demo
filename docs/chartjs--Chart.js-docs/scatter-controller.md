# Scatter Controller Module

## Introduction

The Scatter Controller module is a specialized chart controller in Chart.js that handles the creation and management of scatter plots. Scatter plots are used to display the relationship between two numerical variables, with data points plotted on both x and y axes. This controller extends the base DatasetController to provide scatter-specific functionality including point rendering, optional line connections, and specialized data parsing for coordinate-based datasets.

## Architecture

### Core Component Structure

```mermaid
graph TB
    subgraph "Scatter Controller Module"
        SC[ScatterController]
    end
    
    subgraph "Core Dependencies"
        DC[DatasetController<br/>core.datasetController]
        HEL[isNullOrUndef<br/>helpers]
        MTH[isNumber<br/>helpers.math]
        EXT[_getStartAndCountOfVisiblePoints<br/>helpers.extras]
        SRC[_scaleRangesChanged<br/>helpers.extras]
    end
    
    subgraph "Registry System"
        REG[Registry<br/>core.registry]
        LE[LineElement<br/>registry]
    end
    
    subgraph "Scale System"
        XS[LinearScale<br/>scales.linear]
        YS[LinearScale<br/>scales.linear]
    end
    
    SC --> DC
    SC --> HEL
    SC --> MTH
    SC --> EXT
    SC --> SRC
    SC --> REG
    SC --> LE
    SC --> XS
    SC --> YS
    
    style SC fill:#e1f5fe
    style DC fill:#fff3e0
    style REG fill:#fff3e0
    style XS fill:#fff3e0
    style YS fill:#fff3e0
```

### Inheritance Hierarchy

```mermaid
graph TD
    DC[DatasetController<br/>core.datasetController]
    SC[ScatterController]
    
    DC --> SC
    
    style DC fill:#fff3e0
    style SC fill:#e1f5fe
```

## Component Details

### ScatterController Class

The `ScatterController` is the main component of this module, extending the base `DatasetController` to provide scatter plot-specific functionality.

#### Key Properties

- **Static Properties:**
  - `id`: 'scatter' - Unique identifier for the controller
  - `defaults`: Default configuration including dataset element type, data element type, and display options
  - `overrides`: Chart-specific overrides for interaction mode and scale types

#### Configuration Defaults

```javascript
// Default configuration for scatter charts
defaults = {
    datasetElementType: false,    // No dataset element by default
    dataElementType: 'point',     // Data points are rendered as points
    showLine: false,              // No connecting lines by default
    fill: false                   // No fill under the line
}

// Override configurations
overrides = {
    interaction: {
        mode: 'point'             // Point-based interaction
    },
    scales: {
        x: { type: 'linear' },    // Linear x-axis
        y: { type: 'linear' }     // Linear y-axis
    }
}
```

## Data Flow

### Chart Update Process

```mermaid
sequenceDiagram
    participant Chart
    participant SC as ScatterController
    participant Meta as Chart Metadata
    participant Points as Data Points
    participant Scale as Scale System
    
    Chart->>SC: update(mode)
    SC->>Meta: Get cached metadata
    SC->>Points: Get visible points
    SC->>SC: Calculate draw start/count
    
    alt Scale ranges changed
        SC->>Points: Use all points
    end
    
    alt showLine enabled
        SC->>SC: Add line element
        SC->>Points: Update line with points
    else showLine disabled
        SC->>SC: Remove line element
    end
    
    SC->>Points: Update individual points
    SC->>Scale: Get pixel positions
    SC->>Chart: Render updated elements
```

### Point Update Algorithm

```mermaid
graph TD
    Start[Start Update] --> Init[Initialize Parameters]
    Init --> Loop[Loop Through Points]
    Loop --> Parse[Parse Data Point]
    Parse --> CheckNull{Is Null?}
    CheckNull -->|Yes| SetBase[Set to Base Pixel]
    CheckNull -->|No| CalcPixel[Calculate Pixel Position]
    CalcPixel --> CheckStack{Is Stacked?}
    CheckStack -->|Yes| ApplyStack[Apply Stack Value]
    CheckStack -->|No| UseValue[Use Direct Value]
    SetBase --> CheckGap{Check Gap Length}
    ApplyStack --> CheckGap
    UseValue --> CheckGap
    CheckGap --> SetProps[Set Point Properties]
    SetProps --> UpdateElement[Update Element]
    UpdateElement --> MorePoints{More Points?}
    MorePoints -->|Yes| Loop
    MorePoints -->|No| Finish[Finish Update]
```

## Key Features

### 1. Coordinate-Based Data Handling

The scatter controller specializes in handling data as (x, y) coordinate pairs, making it ideal for correlation analysis and scientific data visualization.

### 2. Optional Line Connections

Unlike other chart types, scatter plots can optionally display connecting lines between points, controlled by the `showLine` configuration option.

### 3. Point-Specific Interactions

The controller implements point-based interaction mode, allowing users to interact with individual data points rather than datasets or categories.

### 4. Gap Handling

Supports intelligent gap detection and handling, with configurable maximum gap length for line connections.

## Integration with Other Modules

### Dependency Relationships

```mermaid
graph TB
    subgraph "Scatter Controller"
        SC[ScatterController]
    end
    
    subgraph "Core System"
        DC[DatasetController]
        REG[Registry]
        DEF[Defaults]
    end
    
    subgraph "Scale System"
        LS[LinearScale]
        SB[Scale Base]
    end
    
    subgraph "Element System"
        PE[PointElement]
        LE[LineElement]
    end
    
    subgraph "Helper System"
        HEL[Helpers]
        MTH[Math Helpers]
        EXT[Extra Helpers]
    end
    
    SC -.->|extends| DC
    SC -.->|uses| REG
    SC -.->|configures| DEF
    SC -.->|requires| LS
    SC -.->|renders| PE
    SC -.->|optional| LE
    SC -.->|utilizes| HEL
    SC -.->|calculations| MTH
    SC -.->|visibility| EXT
```

### Related Modules

- **[dataset-controller.md](dataset-controller.md)**: Base controller that ScatterController extends
- **[registry-system.md](registry-system.md)**: Manages element registration and retrieval
- **[scale-system.md](scale-system.md)**: Provides linear scaling for x and y axes
- **[configuration-system.md](configuration-system.md)**: Handles default configurations and overrides

## Usage Patterns

### Basic Scatter Chart Configuration

```javascript
const config = {
    type: 'scatter',
    data: {
        datasets: [{
            label: 'Scatter Dataset',
            data: [
                {x: 10, y: 20},
                {x: 15, y: 25},
                {x: 20, y: 30}
            ],
            backgroundColor: 'rgb(255, 99, 132)',
            showLine: false  // Default behavior
        }]
    },
    options: {
        scales: {
            x: {
                type: 'linear',
                position: 'bottom'
            },
            y: {
                type: 'linear'
            }
        }
    }
};
```

### Scatter with Connecting Lines

```javascript
const config = {
    type: 'scatter',
    data: {
        datasets: [{
            label: 'Connected Scatter',
            data: scatterData,
            showLine: true,  // Enable line connections
            fill: false,
            tension: 0.1
        }]
    }
};
```

## Performance Considerations

### Optimization Strategies

1. **Visible Point Calculation**: Uses `_getStartAndCountOfVisiblePoints` to limit processing to visible data points
2. **Animation Awareness**: Respects animation settings to optimize update cycles
3. **Scale Range Monitoring**: Detects scale changes to minimize unnecessary updates
4. **Direct Updates**: Uses direct property updates when animations are disabled

### Memory Management

- Efficiently manages point element lifecycle
- Properly cleans up line elements when `showLine` is toggled
- Implements shared options pattern to reduce object creation

## Error Handling

### Data Validation

- Handles null/undefined data points gracefully
- Validates numerical coordinates before processing
- Implements proper fallback for invalid pixel calculations

### Edge Cases

- Empty datasets
- Single data point scenarios
- Scale range validation
- Element type availability checks

## Extension Points

### Customization Options

The scatter controller provides several extension points:

1. **Custom Point Elements**: Through the registry system
2. **Line Styling**: Via dataset element options
3. **Interaction Modes**: Configurable through chart options
4. **Data Parsing**: Extensible through the dataset controller base class

### Plugin Integration

Compatible with Chart.js plugin system for:
- Custom data transformations
- Additional rendering layers
- Interaction enhancements
- Animation extensions

---

*This documentation covers the scatter-controller module's architecture, functionality, and integration within the Chart.js framework. For related functionality, see [dataset-controller.md](dataset-controller.md), [registry-system.md](registry-system.md), and [scale-system.md](scale-system.md).*