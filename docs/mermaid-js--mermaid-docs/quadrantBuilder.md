# Quadrant Builder Module Documentation

## Introduction

The `quadrantBuilder` module is a core component of the Mermaid quadrant chart diagram system. It provides a comprehensive builder pattern implementation for creating quadrant charts, which are used to visualize data points distributed across four quadrants with customizable styling, themes, and configurations. This module handles the transformation of raw data into renderable chart elements including points, quadrants, axis labels, borders, and titles.

## Architecture Overview

The quadrantBuilder module follows a builder pattern architecture that separates concerns into distinct configuration layers: data, styling, and rendering. It integrates with the broader Mermaid ecosystem through configuration types, theme systems, and rendering utilities.

```mermaid
graph TB
    subgraph "Quadrant Builder Core"
        QB[QuadrantBuilder]
        QBC[QuadrantBuilderConfig]
        QBD[QuadrantBuilderData]
        QBTC[QuadrantBuilderThemeConfig]
        QBT[QuadrantBuildType]
    end
    
    subgraph "Configuration Layer"
        BDC[BaseDiagramConfig]
        QCC[QuadrantChartConfig]
        DC[defaultConfig]
    end
    
    subgraph "Theme Layer"
        TV[ThemeVariables]
        DT[Default Theme]
    end
    
    subgraph "Rendering Layer"
        D3[D3 Scales]
        RT[Render Types]
    end
    
    subgraph "Mermaid Core"
        LOG[Logger]
        PT[Point Type]
    end
    
    QB --> QBC
    QB --> QBD
    QB --> QBTC
    QB --> QBT
    
    QBC --> BDC
    QBC --> QCC
    QBC --> DC
    
    QBTC --> TV
    TV --> DT
    
    QB --> D3
    QB --> RT
    
    QB --> LOG
    QB --> PT
```

## Component Relationships

The quadrantBuilder module consists of several interconnected components that work together to build quadrant charts:

```mermaid
graph LR
    subgraph "Input Layer"
        QPID[QuadrantPointInputType]
        QBD2[QuadrantBuilderData]
        QBC2[QuadrantBuilderConfig]
        QBTC2[QuadrantBuilderThemeConfig]
    end
    
    subgraph "Processing Layer"
        QB2[QuadrantBuilder]
        CSD[CalculateSpaceData]
    end
    
    subgraph "Output Layer"
        QPT[QuadrantPointType]
        QQT[QuadrantQuadrantsType]
        QTT[QuadrantTextType]
        QLT[QuadrantLineType]
        QBT2[QuadrantBuildType]
    end
    
    QPID --> QB2
    QBD2 --> QB2
    QBC2 --> QB2
    QBTC2 --> QB2
    
    QB2 --> CSD
    CSD --> QB2
    
    QB2 --> QPT
    QB2 --> QQT
    QB2 --> QTT
    QB2 --> QLT
    QB2 --> QBT2
```

## Data Flow Architecture

The data transformation pipeline in quadrantBuilder follows a systematic approach from raw input to renderable output:

```mermaid
sequenceDiagram
    participant User
    participant QB as QuadrantBuilder
    participant Config as Configuration
    participant Theme as Theme System
    participant Space as Space Calculator
    participant D3 as D3 Scales
    participant Output as Output Builder
    
    User->>QB: Initialize QuadrantBuilder
    QB->>Config: Load default config
    QB->>Theme: Load default theme
    
    User->>QB: setData(data)
    QB->>QB: Update internal data state
    
    User->>QB: setConfig(config)
    QB->>Config: Merge with existing config
    
    User->>QB: setThemeConfig(theme)
    QB->>Theme: Merge with existing theme
    
    User->>QB: build()
    QB->>Space: calculateSpace()
    Space-->>QB: Return space dimensions
    
    QB->>D3: Create x/y scales
    D3-->>QB: Return scaled coordinates
    
    QB->>Output: Generate quadrants
    QB->>Output: Generate points
    QB->>Output: Generate axis labels
    QB->>Output: Generate borders
    QB->>Output: Generate title
    
    Output-->>User: Return QuadrantBuildType
```

## Core Components

### QuadrantBuilder Class

The main builder class that orchestrates the creation of quadrant charts. It manages configuration, data, and theme settings while providing methods for building the final chart structure.

**Key Responsibilities:**
- Configuration management (data, styling, themes)
- Space calculation and layout planning
- Coordinate transformation using D3 scales
- Generation of all chart elements (points, quadrants, labels, borders)

**Key Methods:**
- `build()`: Main method that constructs the complete chart
- `calculateSpace()`: Determines layout dimensions based on configuration
- `getQuadrantPoints()`: Transforms input points to chart coordinates
- `getQuadrants()`: Creates quadrant definitions with styling
- `getAxisLabels()`: Generates axis label positioning and styling
- `getBorders()`: Creates border line definitions

### Configuration Types

#### QuadrantBuilderConfig
Extends the base diagram configuration with quadrant-specific settings including chart dimensions, padding, font sizes, and axis positioning options.

#### QuadrantBuilderData
Defines the input data structure including title text, quadrant labels, axis labels, and point data.

#### QuadrantBuilderThemeConfig
Manages color schemes and styling for all chart elements including quadrant fills, text colors, and border strokes.

### Data Types

#### QuadrantPointInputType
Raw input format for data points with position, text, and optional styling properties.

#### QuadrantPointType
Processed point data ready for rendering with calculated coordinates and applied styling.

#### QuadrantQuadrantsType
Defines quadrant regions with positioning, dimensions, and text styling.

#### QuadrantTextType
Comprehensive text styling including position, color, font size, and rotation.

#### QuadrantLineType
Border line definitions with stroke properties and coordinates.

#### QuadrantBuildType
The final output structure containing all renderable chart elements.

## Integration with Mermaid Ecosystem

The quadrantBuilder module integrates with several other Mermaid components:

```mermaid
graph TB
    subgraph "quadrantBuilder"
        QB3[QuadrantBuilder]
    end
    
    subgraph "Configuration System"
        QCC3[QuadrantChartConfig]
        BDC3[BaseDiagramConfig]
        DC3[defaultConfig]
    end
    
    subgraph "Theme System"
        TV3[ThemeVariables]
        GT3[getThemeVariables]
    end
    
    subgraph "Rendering System"
        PT3[Point Type]
        SL3[scaleLinear]
    end
    
    subgraph "Utility System"
        LOG3[Logger]
    end
    
    QB3 --> QCC3
    QB3 --> BDC3
    QB3 --> DC3
    
    QB3 --> TV3
    TV3 --> GT3
    
    QB3 --> PT3
    QB3 --> SL3
    
    QB3 --> LOG3
```

## Process Flow

The quadrantBuilder follows a systematic process to transform input data into a complete chart structure:

```mermaid
flowchart TD
    Start([Start]) --> Init[Initialize QuadrantBuilder]
    Init --> SetDefaults[Set Default Config & Theme]
    
    SetDefaults --> SetData{Set Data?}
    SetData -->|Yes| UpdateData[Update Internal Data]
    SetData -->|No| SetConfig{Set Config?}
    
    UpdateData --> SetConfig
    
    SetConfig -->|Yes| UpdateConfig[Update Configuration]
    SetConfig -->|No| SetTheme{Set Theme?}
    
    UpdateConfig --> SetTheme
    
    SetTheme -->|Yes| UpdateTheme[Update Theme]
    SetTheme -->|No| Build{Build Requested?}
    
    UpdateTheme --> Build
    
    Build -->|Yes| CalcSpace[Calculate Space]
    CalcSpace --> CreateScales[Create D3 Scales]
    CreateScales --> GenQuadrants[Generate Quadrants]
    GenQuadrants --> GenPoints[Generate Points]
    GenPoints --> GenAxisLabels[Generate Axis Labels]
    GenAxisLabels --> GenBorders[Generate Borders]
    GenBorders --> GenTitle[Generate Title]
    GenTitle --> ReturnResult[Return QuadrantBuildType]
    ReturnResult --> End([End])
    
    Build -->|No| SetData
```

## Space Calculation Algorithm

The space calculation is a critical component that determines the layout of all chart elements:

```mermaid
graph LR
    subgraph "Input Parameters"
        XAP[XAxisPosition]
        SXA[ShowXAxis]
        SYA[ShowYAxis]
        ST[ShowTitle]
    end
    
    subgraph "Calculations"
        XAS[XAxisSpace]
        YAS[YAxisSpace]
        TS[TitleSpace]
        QS[QuadrantSpace]
    end
    
    subgraph "Output"
        CSD2[CalculateSpaceData]
    end
    
    XAP --> XAS
    SXA --> XAS
    
    SYA --> YAS
    
    ST --> TS
    
    XAS --> QS
    YAS --> QS
    TS --> QS
    
    XAS --> CSD2
    YAS --> CSD2
    TS --> CSD2
    QS --> CSD2
```

## Theme Integration

The module integrates with Mermaid's theme system to provide consistent styling:

```mermaid
graph TD
    subgraph "Theme Variables"
        Q1F[quadrant1Fill]
        Q2F[quadrant2Fill]
        Q3F[quadrant3Fill]
        Q4F[quadrant4Fill]
        QTF[quadrantTitleFill]
        QPF[quadrantPointFill]
        QXF[quadrantXAxisTextFill]
        QYF[quadrantYAxisTextFill]
        QIB[quadrantInternalBorderStrokeFill]
        QEB[quadrantExternalBorderStrokeFill]
    end
    
    subgraph "QuadrantBuilderThemeConfig"
        QBTC2[Theme Configuration Object]
    end
    
    subgraph "Application"
        QB4[QuadrantBuilder]
        Q[Quadrants]
        P[Points]
        AL[Axis Labels]
        B[Borders]
        T[Title]
    end
    
    Q1F --> QBTC2
    Q2F --> QBTC2
    Q3F --> QBTC2
    Q4F --> QBTC2
    QTF --> QBTC2
    QPF --> QBTC2
    QXF --> QBTC2
    QYF --> QBTC2
    QIB --> QBTC2
    QEB --> QBTC2
    
    QBTC2 --> QB4
    QB4 --> Q
    QB4 --> P
    QB4 --> AL
    QB4 --> B
    QB4 --> T
```

## Usage Patterns

The quadrantBuilder module is designed to be used in a fluent, chainable manner:

1. **Initialization**: Create a new QuadrantBuilder instance
2. **Configuration**: Set data, configuration, and theme options
3. **Building**: Call the build() method to generate the final chart structure
4. **Rendering**: Use the returned QuadrantBuildType with rendering systems

## Dependencies

The quadrantBuilder module has the following key dependencies:

- **D3.js**: For scale calculations and coordinate transformations
- **Mermaid Configuration System**: For base configuration and chart-specific settings
- **Mermaid Theme System**: For consistent styling and color management
- **Mermaid Logger**: For debugging and trace information
- **Mermaid Types**: For shared type definitions like Point

## Related Documentation

For more information about related components, see:

- [config module](config.md) - Configuration system details
- [themes module](themes.md) - Theme system and styling
- [types module](types.md) - Shared type definitions
- [quadrant-chart module](quadrant-chart.md) - Parent module documentation

## Summary

The quadrantBuilder module provides a robust, flexible system for creating quadrant charts within the Mermaid ecosystem. Its builder pattern design allows for incremental configuration and customization while maintaining clean separation of concerns between data, styling, and rendering logic. The module's integration with D3.js for coordinate transformation and the Mermaid theme system ensures consistent, high-quality chart generation that can be easily customized and extended.