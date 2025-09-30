# Layout Manager Core Module

## Introduction

The layout-manager-core module is a fundamental component of the Material Design Carousel system, providing the core layout management functionality for creating sophisticated carousel interfaces. This module implements the `CarouselLayoutManager` class, which extends Android's `RecyclerView.LayoutManager` to create a unique list optimized for stylized viewing experiences with advanced masking, offsetting, and scrolling behaviors.

The module specializes in managing the positioning, sizing, and visual transformation of carousel items as they move along the scrolling axis, creating dynamic visual effects through a keyline-based layout system.

## Architecture Overview

### Core Components

```mermaid
graph TB
    subgraph "Layout Manager Core"
        CLM[CarouselLayoutManager]
        LD[LayoutDirection]
        KRS[KeylineRange]
        DID[DebugItemDecoration]
        CC[ChildCalculations]
    end
    
    subgraph "External Dependencies"
        CS[CarouselStrategy]
        KSL[KeylineStateList]
        KS[KeylineState]
        K[Keyline]
        COH[CarouselOrientationHelper]
        MFL[MaskableFrameLayout]
    end
    
    CLM --> CS
    CLM --> KSL
    CLM --> KS
    CLM --> K
    CLM --> COH
    CLM -.-> MFL
    CLM --> LD
    CLM --> KRS
    CLM --> DID
    CLM --> CC
```

### Component Relationships

```mermaid
graph LR
    subgraph "Layout Management System"
        CLM[CarouselLayoutManager]
        
        subgraph "Layout Direction Control"
            LD[LayoutDirection]
            LD --> |LAYOUT_START| CLM
            LD --> |LAYOUT_END| CLM
            LD --> |INVALID_LAYOUT| CLM
        end
        
        subgraph "Child Management"
            CC[ChildCalculations]
            KRS[KeylineRange]
            CC --> |uses| KRS
            CLM --> |creates| CC
        end
        
        subgraph "Debug Support"
            DID[DebugItemDecoration]
            CLM --> |manages| DID
        end
    end
```

## Core Functionality

### CarouselLayoutManager

The `CarouselLayoutManager` is the central component that orchestrates the entire carousel layout system. It extends `RecyclerView.LayoutManager` to provide specialized layout behavior for carousel interfaces.

#### Key Responsibilities:
- **Item Positioning**: Calculates and applies precise positioning for carousel items
- **Masking System**: Applies dynamic masking to items based on their position along keylines
- **Scroll Management**: Handles horizontal and vertical scrolling with keyline-based constraints
- **Layout Direction Support**: Supports both LTR and RTL layouts
- **Item Recycling**: Efficiently manages view recycling for performance

#### Core Features:

```mermaid
graph TD
    CLM[CarouselLayoutManager]
    
    subgraph "Layout Features"
        CLM --> |supports| HOR[Horizontal Orientation]
        CLM --> |supports| VER[Vertical Orientation]
        CLM --> |provides| RTL[RTL Layout Support]
        CLM --> |implements| SVP[ScrollVectorProvider]
        CLM --> |implements| CAR[Carousel Interface]
    end
    
    subgraph "Alignment Options"
        CLM --> |aligns| START[ALIGNMENT_START]
        CLM --> |aligns| CENTER[ALIGNMENT_CENTER]
    end
    
    subgraph "Scroll Management"
        CLM --> |manages| MIN[minScroll]
        CLM --> |manages| MAX[maxScroll]
        CLM --> |tracks| SO[scrollOffset]
    end
```

### LayoutDirection Helper Class

The `LayoutDirection` class provides constants for managing layout direction in focus navigation:

- `LAYOUT_START (-1)`: Indicates movement toward the start of the container
- `LAYOUT_END (1)`: Indicates movement toward the end of the container  
- `INVALID_LAYOUT (Integer.MIN_VALUE)`: Indicates invalid or unsupported layout direction

This class is crucial for proper focus navigation and accessibility support within the carousel.

## Data Flow Architecture

### Layout Process Flow

```mermaid
sequenceDiagram
    participant RV as RecyclerView
    participant CLM as CarouselLayoutManager
    participant CS as CarouselStrategy
    participant KSL as KeylineStateList
    participant KS as KeylineState
    
    RV->>CLM: onLayoutChildren()
    CLM->>CS: onFirstChildMeasuredWithMargins()
    CS->>KSL: create KeylineState
    KSL->>KS: generate keylines
    CLM->>KS: calculateChildOffsetCenterForLocation()
    CLM->>RV: addAndLayoutView()
    CLM->>RV: updateChildMaskForLocation()
```

### Scroll Event Processing

```mermaid
sequenceDiagram
    participant User as User Input
    participant RV as RecyclerView
    participant CLM as CarouselLayoutManager
    participant KS as KeylineState
    
    User->>RV: scroll gesture
    RV->>CLM: scrollHorizontallyBy()/scrollVerticallyBy()
    CLM->>CLM: calculateShouldScrollBy()
    CLM->>CLM: updateCurrentKeylineStateForScrollOffset()
    CLM->>KS: getShiftedState()
    CLM->>CLM: fill() - add/remove views
    CLM->>RV: return scrolled distance
```

## Keyline System Integration

The layout manager works closely with the keyline system to create sophisticated visual effects:

```mermaid
graph TB
    subgraph "Keyline Integration"
        CLM[CarouselLayoutManager]
        
        subgraph "Keyline Processing"
            CLM --> |calculates| SKR[getSurroundingKeylineRange]
            CLM --> |interpolates| CCO[calculateChildOffsetCenterForLocation]
            CLM --> |applies| UCM[updateChildMaskForLocation]
        end
        
        subgraph "Keyline State Management"
            CLM --> |updates| UCKS[updateCurrentKeylineStateForScrollOffset]
            CLM --> |calculates| CSS[calculateStartScroll]
            CLM --> |calculates| CES[calculateEndScroll]
        end
    end
```

## Child View Management

### View Addition Process

```mermaid
graph LR
    subgraph "View Addition Flow"
        START[Start Fill Process]
        CALC[Calculate Child Position]
        CHECK{In Bounds?}
        ADD[Add View to RecyclerView]
        MASK[Apply Mask]
        NEXT[Next Position]
        
        START --> CALC
        CALC --> CHECK
        CHECK -->|Yes| ADD
        CHECK -->|No| NEXT
        ADD --> MASK
        MASK --> NEXT
        NEXT --> CALC
    end
```

### ChildCalculations Class

The `ChildCalculations` class encapsulates all necessary information for positioning and transforming a child view:

- **child**: The actual View to be laid out
- **center**: Location in the end-to-end model
- **offsetCenter**: Actual layout position after keyline interpolation
- **range**: Keyline range that surrounds the child's position

## Orientation Support

### Horizontal Layout
- Primary orientation for most carousel implementations
- Supports both LTR and RTL layouts
- Keylines are positioned along the X-axis
- Masking affects width dimensions

### Vertical Layout
- Alternative orientation for vertical carousels
- Keylines are positioned along the Y-axis
- Masking affects height dimensions
- Same keyline principles apply

## Debug Support

### DebugItemDecoration

The module includes a sophisticated debugging system through `DebugItemDecoration`:

```mermaid
graph LR
    subgraph "Debug System"
        DID[DebugItemDecoration]
        CLM[CarouselLayoutManager]
        RV[RecyclerView]
        
        CLM --> |enables| DID
        DID --> |draws| KL[Keyline Visualizations]
        DID --> |overlays| RV
        KL --> |shows| MASK[Mask Values]
        KL --> |shows| POS[Keyline Positions]
    end
```

Features:
- Visual keyline overlay with color-coded mask values
- Configurable debug line width and colors
- Real-time keyline position updates during scrolling
- Integration with RecyclerView's item decoration system

## Integration with Carousel System

### Module Dependencies

```mermaid
graph TB
    subgraph "Carousel Module Dependencies"
        LMC[layout-manager-core]
        KS[keyline-system]
        SF[strategy-framework]
        
        LMC --> |depends on| KS
        LMC --> |uses| SF
        
        subgraph "Shared Components"
            CLM[CarouselLayoutManager]
            KSL[KeylineStateList]
            CS[CarouselStrategy]
            
            CLM --> |manages| KSL
            CLM --> |configures| CS
        end
    end
```

### Related Modules

- **[keyline-system](keyline-system.md)**: Provides the keyline state management and keyline calculation logic
- **[strategy-framework](strategy-framework.md)**: Supplies carousel strategies that define layout behavior
- **[carousel-overview](carousel.md)**: Parent module documentation for the complete carousel system

## Performance Considerations

### Optimization Strategies

1. **View Recycling**: Efficient view recycling minimizes memory allocation
2. **Keyline Caching**: Keyline states are cached and reused when possible
3. **Lazy Calculations**: Complex calculations are performed only when necessary
4. **Bounds Checking**: Early exit conditions prevent unnecessary processing

### Memory Management

```mermaid
graph LR
    subgraph "Memory Optimization"
        CLM[CarouselLayoutManager]
        
        CLM --> |manages| VREC[View Recycling]
        CLM --> |caches| KSL[KeylineStateList]
        CLM --> |reuses| CC[ChildCalculations]
        CLM --> |limits| DEBUG[Debug Overhead]
    end
```

## Usage Examples

### Basic Implementation

```java
// Create a carousel with default multi-browse strategy
CarouselLayoutManager layoutManager = new CarouselLayoutManager();

// Set custom strategy
layoutManager.setCarouselStrategy(new HeroCarouselStrategy());

// Configure alignment
layoutManager.setCarouselAlignment(CarouselLayoutManager.ALIGNMENT_CENTER);

// Apply to RecyclerView
recyclerView.setLayoutManager(layoutManager);
```

### Advanced Configuration

```java
// Create with specific orientation and strategy
CarouselLayoutManager layoutManager = new CarouselLayoutManager(
    new MultiBrowseCarouselStrategy(), 
    CarouselLayoutManager.HORIZONTAL
);

// Enable debugging for development
layoutManager.setDebuggingEnabled(recyclerView, true);
```

## Accessibility Support

The layout manager provides comprehensive accessibility features:

- **Focus Navigation**: Proper focus traversal through convertFocusDirectionToLayoutDirection()
- **Screen Reader Support**: Enhanced accessibility events with position information
- **Keyboard Navigation**: Support for directional navigation
- **RTL Support**: Full right-to-left layout support

## Error Handling

### Validation

The module includes extensive validation:

- **Child Order Validation**: Ensures proper adapter position ordering
- **View Type Validation**: Verifies all children use MaskableFrameLayout
- **Keyline State Validation**: Validates keyline calculations and ranges
- **Scroll Boundary Validation**: Enforces min/max scroll constraints

### Exception Handling

- `IllegalStateException`: Thrown for invalid child configurations
- `IllegalArgumentException`: Thrown for invalid orientation values
- Debug assertions for development-time validation

This comprehensive error handling ensures robust operation and early detection of configuration issues.