# Behavior System Module Documentation

## Introduction

The behavior-system module is a foundational component of the Material Design AppBar library that provides core behavioral patterns for header views and view offset management. This module implements the CoordinatorLayout behavior pattern to enable sophisticated scrolling interactions, touch handling, and view positioning within Material Design layouts.

The module consists of two primary components: `HeaderBehavior` and `ViewOffsetBehavior`, which work together to create responsive, interactive header behaviors that respond to user gestures and scrolling content.

## Architecture Overview

```mermaid
graph TB
    subgraph "Behavior System Module"
        HB[HeaderBehavior<V>] --> VOB[ViewOffsetBehavior<V>]
        VOB --> VOH[ViewOffsetHelper]
        HB --> CL[CoordinatorLayout]
        HB --> OS[OverScroller]
        HB --> VT[VelocityTracker]
    end
    
    subgraph "External Dependencies"
        CL --> V[View]
        CL --> ME[MotionEvent]
        VOB --> CL
    end
    
    style HB fill:#e1f5fe
    style VOB fill:#e1f5fe
```

## Core Components

### HeaderBehavior

`HeaderBehavior<V extends View>` is an abstract behavior class that provides sophisticated touch interaction and scrolling capabilities for header views. It extends `ViewOffsetBehavior` to inherit offset management functionality while adding gesture recognition, velocity tracking, and fling animation support.

**Key Responsibilities:**
- Touch event interception and handling
- Drag gesture recognition and processing
- Velocity-based fling animations
- Scroll offset management with constraints
- Smooth scrolling with OverScroller integration

**Core Features:**

#### Touch Event Processing
The behavior implements a comprehensive touch handling system that distinguishes between taps, drags, and flings:

```mermaid
sequenceDiagram
    participant User
    participant TouchSystem
    participant HeaderBehavior
    participant View
    
    User->>TouchSystem: Touch Down
    TouchSystem->>HeaderBehavior: onInterceptTouchEvent()
    HeaderBehavior->>HeaderBehavior: Check if can drag view
    HeaderBehavior->>HeaderBehavior: Initialize tracking
    HeaderBehavior-->>TouchSystem: Return intercept status
    
    User->>TouchSystem: Move
    TouchSystem->>HeaderBehavior: onTouchEvent()
    HeaderBehavior->>HeaderBehavior: Calculate movement delta
    HeaderBehavior->>View: Apply offset changes
    
    User->>TouchSystem: Lift
    TouchSystem->>HeaderBehavior: onTouchEvent()
    HeaderBehavior->>HeaderBehavior: Calculate velocity
    HeaderBehavior->>HeaderBehavior: Start fling animation
```

#### Fling Animation System
The fling system uses Android's `OverScroller` to create smooth, physics-based animations that continue after the user lifts their finger:

```mermaid
graph LR
    A[Touch Release] --> B{Velocity > Threshold?}
    B -->|Yes| C[Create OverScroller]
    B -->|No| D[Stop Animation]
    C --> E[FlingRunnable]
    E --> F[Update View Position]
    F --> G{Animation Complete?}
    G -->|No| E
    G -->|Yes| H[onFlingFinished]
```

#### Offset Management
The behavior provides sophisticated offset management with boundary constraints:

```mermaid
graph TD
    A[Scroll Request] --> B{Within Bounds?}
    B -->|Yes| C[Calculate New Offset]
    B -->|No| D[Clamp to Boundaries]
    C --> E[Apply Offset]
    D --> E
    E --> F[Update View Position]
    F --> G[Return Consumed Distance]
```

### ViewOffsetBehavior

`ViewOffsetBehavior<V extends View>` is the base behavior class that provides view offset management capabilities. It automatically sets up and manages a `ViewOffsetHelper` to handle view positioning without requiring manual layout parameter modifications.

**Key Responsibilities:**
- Automatic ViewOffsetHelper setup and management
- Temporary offset storage before layout completion
- Horizontal and vertical offset application
- Offset state persistence across layout changes

**Core Features:**

#### Layout Integration
The behavior integrates with the CoordinatorLayout's layout process to ensure proper offset application:

```mermaid
sequenceDiagram
    participant CoordinatorLayout
    participant ViewOffsetBehavior
    participant ViewOffsetHelper
    participant View
    
    CoordinatorLayout->>ViewOffsetBehavior: onLayoutChild()
    ViewOffsetBehavior->>ViewOffsetHelper: Create/Update helper
    ViewOffsetHelper->>View: Apply stored offsets
    ViewOffsetHelper->>ViewOffsetHelper: Update layout state
    ViewOffsetBehavior-->>CoordinatorLayout: Layout complete
```

#### Offset Management
The behavior provides both immediate and deferred offset application:

```mermaid
graph LR
    A[Offset Request] --> B{View Laid Out?}
    B -->|Yes| C[Apply via ViewOffsetHelper]
    B -->|No| D[Store Temporarily]
    D --> E[Apply During Next Layout]
    C --> F[Update View Position]
    E --> F
```

## Component Interactions

### Behavior Hierarchy
```mermaid
graph TD
    A[CoordinatorLayout.Behavior<V>] --> B[ViewOffsetBehavior<V>]
    B --> C[HeaderBehavior<V>]
    C --> D[AppBarLayout.Behavior]
    C --> E[CollapsingToolbarLayout.Behavior]
    
    style A fill:#fff3e0
    style B fill:#e1f5fe
    style C fill:#e1f5fe
```

### Data Flow Architecture
```mermaid
graph LR
    subgraph "User Interaction"
        A[Touch Events] --> B[HeaderBehavior]
        B --> C[Velocity Calculation]
        C --> D[Fling Animation]
    end
    
    subgraph "View Management"
        D --> E[ViewOffsetBehavior]
        E --> F[ViewOffsetHelper]
        F --> G[View Position Update]
    end
    
    subgraph "Layout System"
        H[CoordinatorLayout] --> E
        E --> I[Layout Parameters]
        I --> G
    end
```

## Integration with AppBar System

The behavior-system module serves as the foundation for the broader AppBar system:

```mermaid
graph TB
    subgraph "behavior-system"
        A[HeaderBehavior] --> B[ViewOffsetBehavior]
    end
    
    subgraph "appbarlayout-core"
        C[AppBarLayout.Behavior] --> A
        D[AppBarLayout.ScrollingViewBehavior] --> B
    end
    
    subgraph "collapsing-toolbar"
        E[CollapsingToolbarLayout.Behavior] --> A
    end
    
    subgraph "bottomappbar"
        F[BottomAppBar.Behavior] --> A
    end
    
    A -.-> G[See appbarlayout-core.md]
    A -.-> H[See collapsing-toolbar.md]
    A -.-> I[See bottomappbar.md]
```

## Key Design Patterns

### Template Method Pattern
`HeaderBehavior` uses the template method pattern to allow subclasses to customize specific behaviors:

- `canDragView(V view)` - Determine if a view can be dragged
- `getMaxDragOffset(V view)` - Define maximum drag offset
- `getScrollRangeForDragFling(V view)` - Specify scroll range for fling calculations
- `onFlingFinished(CoordinatorLayout parent, V layout)` - Handle post-fling cleanup

### Strategy Pattern
The behavior system employs strategy pattern through CoordinatorLayout's behavior attachment mechanism, allowing different views to adopt different interaction strategies.

### Observer Pattern
The system integrates with CoordinatorLayout's dependency system to observe and respond to changes in related views and layout states.

## Performance Considerations

### Memory Management
- VelocityTracker is properly recycled after use
- FlingRunnable is cleaned up when animations complete
- ViewOffsetHelper is reused across layout cycles

### Animation Optimization
- Uses hardware-accelerated OverScroller for smooth animations
- Implements proper animation lifecycle management
- Provides early termination for conflicting animations

### Touch Event Efficiency
- Implements early return patterns for non-relevant touch events
- Uses touch slop to filter out accidental movements
- Maintains minimal state during touch processing

## Usage Guidelines

### Implementation Requirements
When extending `HeaderBehavior`:
1. Implement `canDragView()` to define drag eligibility
2. Override offset calculation methods as needed
3. Handle `onFlingFinished()` for cleanup operations
4. Consider touch slop for consistent user experience

### Integration Best Practices
1. Ensure proper CoordinatorLayout setup
2. Configure touch handling boundaries appropriately
3. Test with various scroll velocities and directions
4. Consider accessibility implications of custom behaviors

### Common Pitfalls
- Forgetting to call super methods in overridden functions
- Not properly handling edge cases in offset calculations
- Ignoring the touch slop configuration
- Not cleaning up animation resources

## Dependencies

### Internal Dependencies
- [appbarlayout-core.md](appbarlayout-core.md) - Uses HeaderBehavior for AppBarLayout interactions
- [collapsing-toolbar.md](collapsing-toolbar.md) - Extends HeaderBehavior for collapsing functionality
- [utility-components.md](utility-components.md) - Utilizes ViewUtilsLollipop for compatibility

### External Dependencies
- AndroidX CoordinatorLayout for behavior framework
- Android ViewConfiguration for touch parameters
- Android OverScroller for fling animations
- Android VelocityTracker for gesture velocity calculation

## Future Considerations

The behavior-system module provides a solid foundation for Material Design scrolling interactions. Future enhancements might include:

- Enhanced accessibility support for custom behaviors
- Additional animation interpolators and effects
- Performance optimizations for complex view hierarchies
- Extended gesture recognition capabilities

This module represents a critical component in creating responsive, interactive Material Design layouts that provide smooth, intuitive user experiences across the Android ecosystem.