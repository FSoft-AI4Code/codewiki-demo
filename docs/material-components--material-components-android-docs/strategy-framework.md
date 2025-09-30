# Strategy Framework Module Documentation

## Introduction

The strategy-framework module is a core component of the Material Design Carousel system that provides mathematical and algorithmic utilities for calculating item positioning, sizing, and layout arrangements. This module serves as the computational engine behind carousel layouts, handling complex keyline calculations and arrangement strategies that enable smooth, responsive carousel experiences.

## Module Overview

The strategy-framework module contains the `CarouselStrategyHelper` class, which provides essential utility methods for implementing carousel strategies. It acts as a bridge between high-level carousel requirements and low-level layout calculations, ensuring consistent behavior across different carousel configurations and screen sizes.

## Core Architecture

### Component Structure

```mermaid
graph TB
    subgraph "Strategy Framework Module"
        CSH[CarouselStrategyHelper]
        
        CSH --> SizeCalc[Size Calculations]
        CSH --> KeylineGen[Keyline Generation]
        CSH --> Alignment[Alignment Strategies]
        CSH --> Arrangement[Arrangement Processing]
        
        SizeCalc --> ExtraSmall[getExtraSmallSize]
        SizeCalc --> SmallMin[getSmallSizeMin]
        SizeCalc --> SmallMax[getSmallSizeMax]
        
        KeylineGen --> LeftAligned[createLeftAlignedKeylineState]
        KeylineGen --> CenterAligned[createCenterAlignedKeylineState]
        
        Alignment --> LeftAlign[Left Alignment Logic]
        Alignment --> CenterAlign[Center Alignment Logic]
        
        Arrangement --> PositionCalc[Position Calculations]
        Arrangement --> MaskCalc[Mask Percentage Calculations]
    end
```

### System Integration

```mermaid
graph LR
    subgraph "Carousel System"
        CS[CarouselStrategy]
        CSLM[CarouselLayoutManager]
        KS[KeylineState]
        ARR[Arrangement]
        
        CS --> |"uses"| CSH[CarouselStrategyHelper]
        CSLM --> |"provides context"| CSH
        ARR --> |"input"| CSH
        CSH --> |"generates"| KS
        
        CSH -.-> |"references"| layout-manager-core
        CSH -.-> |"references"| keyline-system
    end
```

## Key Components

### CarouselStrategyHelper

The `CarouselStrategyHelper` class is a utility class that provides essential methods for carousel strategy implementations. It cannot be instantiated (private constructor) and contains only static utility methods.

#### Key Responsibilities:
- **Size Management**: Calculate item sizes based on device dimensions and Material Design specifications
- **Keyline Generation**: Create keyline states for different alignment configurations
- **Position Calculation**: Compute precise positioning for carousel items
- **Mask Calculation**: Determine visibility masks for items at different positions

#### Core Methods:

```mermaid
classDiagram
    class CarouselStrategyHelper {
        <<utility>>
        -CarouselStrategyHelper()
        +getExtraSmallSize(Context): float
        +getSmallSizeMin(Context): float
        +getSmallSizeMax(Context): float
        +createKeylineState(Context, float, int, Arrangement, int): KeylineState
        +createLeftAlignedKeylineState(Context, float, int, Arrangement): KeylineState
        +createCenterAlignedKeylineState(Context, float, int, Arrangement): KeylineState
        +maxValue(int[]): int
        +addStart(float, float, int): float
        +addEnd(float, float, int): float
        +updateCurPosition(float, float, float, int): float
    }
```

## Data Flow Architecture

### Keyline State Generation Process

```mermaid
sequenceDiagram
    participant CS as CarouselStrategy
    participant CSH as CarouselStrategyHelper
    participant ARR as Arrangement
    participant KS as KeylineState.Builder
    participant CSLM as CarouselLayoutManager

    CS->>CSH: createKeylineState(context, margins, space, arrangement, alignment)
    CSH->>CSH: Determine alignment type
    alt Center Alignment
        CSH->>CSH: createCenterAlignedKeylineState()
    else Left Alignment
        CSH->>CSH: createLeftAlignedKeylineState()
    end
    
    CSH->>ARR: Extract size and count information
    CSH->>CSH: Calculate item positions
    CSH->>CSH: Calculate mask percentages
    CSH->>KS: Create builder with large size
    CSH->>KS: Add anchor keylines
    CSH->>KS: Add keyline ranges
    KS->>CSH: Build KeylineState
    CSH->>CS: Return KeylineState
```

### Size Calculation Flow

```mermaid
flowchart TD
    Start([Size Request]) --> Context{Context Available?}
    Context -->|Yes| Resource[Load Material Resources]
    Resource --> ExtraSmall[getExtraSmallSize]
    Resource --> SmallMin[getSmallSizeMin]
    Resource --> SmallMax[getSmallSizeMax]
    
    ExtraSmall --> Dimension[Extract Dimension]
    SmallMin --> Dimension
    SmallMax --> Dimension
    
    Dimension --> ApplyMargins[Apply Child Margins]
    ApplyMargins --> Clamp[Clamp to Valid Range]
    Clamp --> ReturnSize[Return Calculated Size]
    
    Context -->|No| Error[Throw Exception]
```

## Alignment Strategies

### Left-Aligned Layout

The left-aligned strategy positions items starting from the left edge of the available space, creating a traditional horizontal scroll layout.

```mermaid
graph LR
    subgraph "Left-Aligned Layout"
        A[Anchor Start] --> B[Large Items]
        B --> C[Medium Items]
        C --> D[Small Items]
        D --> E[Anchor End]
        
        A -.-> |"Extra Small"| A
        E -.-> |"Extra Small"| E
    end
```

### Center-Aligned Layout

The center-aligned strategy creates a symmetric layout with the focal item in the center, providing a more balanced visual experience.

```mermaid
graph LR
    subgraph "Center-Aligned Layout"
        A[Anchor Start] --> B[Half Small]
        B --> C[Half Medium]
        C --> D[Large Items]
        D --> E[Half Medium]
        E --> F[Half Small]
        F --> G[Anchor End]
        
        A -.-> |"Extra Small"| A
        G -.-> |"Extra Small"| G
    end
```

## Mathematical Operations

### Position Calculation

The strategy framework uses precise mathematical operations to calculate item positions:

1. **Start Position**: `start + itemSize / 2F`
2. **End Position**: `startKeylinePos + (max(0, count - 1) * itemSize)`
3. **Next Position**: `lastEndKeyline + itemSize / 2F`

### Mask Percentage Calculation

Mask percentages determine item visibility based on their position and size relative to the focal item:

```mermaid
graph TD
    ItemSize[Item Size] --> MaskCalc[Mask Calculation]
    LargeSize[Large Item Size] --> MaskCalc
    Margins[Child Margins] --> MaskCalc
    
    MaskCalc --> Percentage[Visibility Percentage]
    Percentage --> Keyline[Keyline State]
    
    style MaskCalc fill:#f9f,stroke:#333,stroke-width:4px
```

## Integration with Carousel System

### Dependency Relationships

```mermaid
graph TB
    subgraph "Strategy Framework Dependencies"
        CSH[CarouselStrategyHelper]
        
        CSH --> |"uses"| CS[CarouselStrategy]
        CSH --> |"creates"| KS[KeylineState]
        CSH --> |"processes"| ARR[Arrangement]
        CSH --> |"references"| CSLM[CarouselLayoutManager]
        
        KS --> |"built by"| KSB[KeylineState.Builder]
        ARR --> |"contains"| Sizes[Size Configurations]
        ARR --> |"contains"| Counts[Item Counts]
    end
```

### Resource Dependencies

The strategy framework relies on Material Design dimension resources:
- `m3_carousel_gone_size`: Size for completely hidden items
- `m3_carousel_small_item_size_min`: Minimum size for small items
- `m3_carousel_small_item_size_max`: Maximum size for small items

## Usage Patterns

### Basic Keyline Generation

```java
// Example usage pattern (conceptual)
KeylineState keylineState = CarouselStrategyHelper.createKeylineState(
    context,
    childMargins,
    availableSpace,
    arrangement,
    CarouselLayoutManager.ALIGNMENT_CENTER
);
```

### Size Calculation

```java
// Get Material Design specified sizes
float extraSmallSize = CarouselStrategyHelper.getExtraSmallSize(context);
float smallSizeMin = CarouselStrategyHelper.getSmallSizeMin(context);
float smallSizeMax = CarouselStrategyHelper.getSmallSizeMax(context);
```

## Performance Considerations

### Optimization Strategies

1. **Static Utility Methods**: All methods are static to avoid object instantiation overhead
2. **Efficient Calculations**: Mathematical operations are optimized for performance
3. **Resource Caching**: Dimension values are loaded once per context
4. **Minimal Object Creation**: Reuses calculation results where possible

### Memory Management

- No instance variables (static utility class)
- Temporary objects are scoped to method execution
- KeylineState.Builder pattern allows efficient object construction

## Error Handling

### Input Validation

The strategy framework performs implicit validation through:
- `@NonNull` annotations for required parameters
- Resource existence validation (throws if resources not found)
- Mathematical bounds checking (min/max operations)

### Edge Cases

- Empty arrangements (count = 0)
- Insufficient available space
- Invalid alignment values
- Missing dimension resources

## Extension Points

### Custom Alignment Strategies

Developers can extend the framework by:
1. Implementing custom alignment logic similar to left/center alignment
2. Creating new arrangement patterns
3. Adding specialized size calculation methods

### Integration with Custom Strategies

The helper methods can be used by custom `CarouselStrategy` implementations to ensure consistency with Material Design specifications.

## Related Documentation

- [layout-manager-core](layout-manager-core.md) - Carousel layout management
- [keyline-system](keyline-system.md) - Keyline state management
- [carousel-overview](carousel.md) - General carousel documentation

## Summary

The strategy-framework module provides the mathematical foundation for Material Design carousel layouts. Through its utility methods and calculation algorithms, it enables consistent, responsive, and visually appealing carousel experiences across different devices and configurations. The module's design emphasizes performance, accuracy, and adherence to Material Design principles while providing flexibility for various carousel implementations.