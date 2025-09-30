# Slider Events Module Documentation

## Introduction

The slider-events module provides the foundational event handling interfaces for Material Design slider components. This module defines the core callback interfaces that enable developers to respond to user interactions with slider controls, including value changes and touch events. As part of the larger slider component ecosystem, these interfaces serve as the contract between slider implementations and application code that needs to react to slider state changes.

## Architecture Overview

The slider-events module implements a generic, type-safe event handling pattern using Java generics. This design allows the same event interfaces to be used across different slider implementations (both single-value Slider and dual-thumb RangeSlider components) while maintaining type safety and consistency.

```mermaid
graph TB
    subgraph "Slider Events Module"
        BCL[BaseOnChangeListener<S>]
        BSTL[BaseOnSliderTouchListener<S>]
    end
    
    subgraph "Slider Implementations"
        RS[RangeSlider]
        S[Slider]
    end
    
    subgraph "Application Layer"
        AC[App Code]
    end
    
    BCL -.->|"implemented by"| RS
    BCL -.->|"implemented by"| S
    BSTL -.->|"implemented by"| RS
    BSTL -.->|"implemented by"| S
    
    AC -->|"registers listeners"| BCL
    AC -->|"registers listeners"| BSTL
    
    RS -->|"fires events"| BCL
    RS -->|"fires events"| BSTL
    S -->|"fires events"| BCL
    S -->|"fires events"| BSTL
```

## Core Components

### BaseOnChangeListener<S>

The `BaseOnChangeListener<S>` interface defines the contract for handling slider value change events. This generic interface uses a type parameter `S` to represent the specific slider type, ensuring type safety when implementing custom listeners.

**Key Features:**
- Generic interface supporting any slider type
- Provides value change notification with user interaction context
- Includes `fromUser` flag to distinguish programmatic vs. user-initiated changes
- Restricted to library group usage for internal consistency

**Method:**
- `onValueChange(@NonNull S slider, float value, boolean fromUser)` - Called when the slider's value changes

### BaseOnSliderTouchListener<S>

The `BaseOnSliderTouchListener<S>` interface handles touch interaction events, providing callbacks for when users start and stop interacting with slider controls.

**Key Features:**
- Generic interface for touch event handling
- Provides start/stop tracking for touch interactions
- Enables custom behaviors during user interaction
- Restricted to library group usage

**Methods:**
- `onStartTrackingTouch(@NonNull S slider)` - Called when user starts touching the slider
- `onStopTrackingTouch(@NonNull S slider)` - Called when user stops touching the slider

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant Slider
    participant BaseOnChangeListener
    participant BaseOnSliderTouchListener
    participant App
    
    User->>Slider: Touch down
    Slider->>BaseOnSliderTouchListener: onStartTrackingTouch()
    BaseOnSliderTouchListener->>App: Notify touch start
    
    User->>Slider: Drag thumb
    Slider->>BaseOnChangeListener: onValueChange(value, true)
    BaseOnChangeListener->>App: Notify value change
    
    User->>Slider: Touch up
    Slider->>BaseOnSliderTouchListener: onStopTrackingTouch()
    BaseOnSliderTouchListener->>App: Notify touch end
    
    App->>Slider: setValue() programmatically
    Slider->>BaseOnChangeListener: onValueChange(value, false)
    BaseOnChangeListener->>App: Notify programmatic change
```

## Component Relationships

```mermaid
classDiagram
    class BaseOnChangeListener~S~ {
        <<interface>>
        +onValueChange(S slider, float value, boolean fromUser)
    }
    
    class BaseOnSliderTouchListener~S~ {
        <<interface>>
        +onStartTrackingTouch(S slider)
        +onStopTrackingTouch(S slider)
    }
    
    class RangeSlider {
        -OnChangeListener onChangeListener
        -OnSliderTouchListener onTouchListener
    }
    
    class Slider {
        -OnChangeListener onChangeListener
        -OnSliderTouchListener onTouchListener
    }
    
    class RangeSliderOnChangeListener {
        <<interface>>
        +onValueChange(RangeSlider slider, float value, boolean fromUser)
    }
    
    class RangeSliderOnSliderTouchListener {
        <<interface>>
        +onStartTrackingTouch(RangeSlider slider)
        +onStopTrackingTouch(RangeSlider slider)
    }
    
    class SliderOnChangeListener {
        <<interface>>
        +onValueChange(Slider slider, float value, boolean fromUser)
    }
    
    class SliderOnSliderTouchListener {
        <<interface>>
        +onStartTrackingTouch(Slider slider)
        +onStopTrackingTouch(Slider slider)
    }
    
    BaseOnChangeListener~S~ <|-- RangeSliderOnChangeListener
    BaseOnChangeListener~S~ <|-- SliderOnChangeListener
    BaseOnSliderTouchListener~S~ <|-- RangeSliderOnSliderTouchListener
    BaseOnSliderTouchListener~S~ <|-- SliderOnSliderTouchListener
    
    RangeSlider --> RangeSliderOnChangeListener
    RangeSlider --> RangeSliderOnSliderTouchListener
    Slider --> SliderOnChangeListener
    Slider --> SliderOnSliderTouchListener
```

## Integration with Slider Module

The slider-events module serves as the foundation for the complete slider implementation. The base interfaces defined here are extended by specific listener types in the [range-slider](range-slider.md) and main slider modules.

```mermaid
graph LR
    subgraph "slider-events"
        BCL[BaseOnChangeListener]
        BSTL[BaseOnSliderTouchListener]
    end
    
    subgraph "range-slider"
        RSCL[RangeSlider.OnChangeListener]
        RSSL[RangeSlider.OnSliderTouchListener]
    end
    
    subgraph "slider-main"
        SCL[Slider.OnChangeListener]
        SSL[Slider.OnSliderTouchListener]
    end
    
    BCL -.->|"extends"| RSCL
    BCL -.->|"extends"| SCL
    BSTL -.->|"extends"| RSSL
    BSTL -.->|"extends"| SSL
```

## Usage Patterns

### Value Change Handling

Applications implement the base interfaces to respond to slider value changes:

```java
// Example implementation for a custom slider listener
BaseOnChangeListener<Slider> listener = new BaseOnChangeListener<Slider>() {
    @Override
    public void onValueChange(@NonNull Slider slider, float value, boolean fromUser) {
        if (fromUser) {
            // Handle user-initiated change
            updateUI(value);
        } else {
            // Handle programmatic change
            syncWithModel(value);
        }
    }
};
```

### Touch Event Handling

Touch listeners enable custom behaviors during user interaction:

```java
BaseOnSliderTouchListener<Slider> touchListener = new BaseOnSliderTouchListener<Slider>() {
    @Override
    public void onStartTrackingTouch(@NonNull Slider slider) {
        // Pause animations or other UI updates
        pauseUIUpdates();
    }
    
    @Override
    public void onStopTrackingTouch(@NonNull Slider slider) {
        // Resume normal operation
        resumeUIUpdates();
        // Commit final value
        commitValue(slider.getValue());
    }
};
```

## Design Principles

### Type Safety
The use of generics ensures compile-time type checking, preventing runtime errors when working with different slider types.

### Consistency
Both interfaces follow similar naming patterns and parameter structures, providing a consistent API across different event types.

### Extensibility
The generic design allows for easy extension to support new slider variants without modifying the base interfaces.

### Library Internal Design
The `@RestrictTo(Scope.LIBRARY_GROUP)` annotation ensures these interfaces are used consistently within the Material Components library while allowing specific implementations to expose public APIs.

## Related Modules

- [range-slider](range-slider.md) - Extends these base interfaces for dual-thumb slider functionality
- [slider-orientation](slider-orientation.md) - Provides orientation support for slider components
- Main slider module - Implements the complete slider component using these event interfaces

## Best Practices

1. **Implement Both Interfaces**: For complete slider interaction handling, implement both change and touch listeners
2. **Check fromUser Flag**: Use the `fromUser` parameter to distinguish between user interactions and programmatic changes
3. **Handle Touch States**: Implement touch tracking for scenarios requiring interaction state awareness
4. **Type Safety**: Use the appropriate listener type for your specific slider implementation
5. **Performance**: Keep listener implementations lightweight to maintain smooth UI interactions