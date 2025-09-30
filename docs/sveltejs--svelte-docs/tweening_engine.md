# Tweening Engine Module

The tweening engine module provides smooth animation capabilities for Svelte applications through interpolated value transitions over time. It offers both legacy store-based and modern class-based APIs for creating smooth animations between different states.

## Overview

The tweening engine enables developers to create smooth transitions between values using customizable easing functions, durations, and interpolation methods. It supports various data types including numbers, objects, arrays, and dates, making it versatile for different animation scenarios.

## Architecture

```mermaid
graph TB
    subgraph "Tweening Engine Module"
        subgraph "Public API"
            TweenedInterface[Tweened Interface]
            TweenClass[Tween Class]
            TweenedFunction[tweened Function]
        end
        
        subgraph "Core Components"
            Interpolator[get_interpolator]
            TaskManager[Task Management]
            StateManagement[State Management]
        end
        
        subgraph "Configuration"
            TweenedOptions[TweenedOptions]
            EasingFunctions[Easing Functions]
            InterpolationLogic[Interpolation Logic]
        end
    end
    
    subgraph "Dependencies"
        StoreSystem[Store System]
        ReactivitySystem[Reactivity System]
        TimingSystem[Timing System]
        EasingModule[Easing Module]
    end
    
    TweenedInterface --> TweenClass
    TweenedFunction --> TweenedInterface
    TweenClass --> Interpolator
    TweenClass --> TaskManager
    TweenClass --> StateManagement
    
    Interpolator --> TweenedOptions
    TaskManager --> TweenedOptions
    
    TweenClass --> StoreSystem
    TweenClass --> ReactivitySystem
    TweenClass --> TimingSystem
    TweenClass --> EasingModule
    
    TweenedFunction --> StoreSystem
```

## Core Components

### Tween Class

The modern `Tween` class provides a reactive approach to value tweening with automatic state management.

**Key Features:**
- Reactive `current` and `target` properties
- Promise-based completion tracking
- Automatic interpolation between different data types
- Configurable easing and duration options

**Usage Pattern:**
```javascript
const tween = new Tween(initialValue, options);
tween.target = newValue; // Triggers smooth transition
```

### Tweened Interface & Function

The legacy `tweened` function creates store-based tweened values compatible with Svelte's store system.

**Key Features:**
- Store-compatible API with subscribe/set/update methods
- Backward compatibility with existing codebases
- Manual value management through function calls

### TweenedOptions Configuration

Comprehensive configuration interface supporting:
- **delay**: Animation start delay in milliseconds
- **duration**: Animation duration (static or dynamic based on values)
- **easing**: Timing function for animation progression
- **interpolate**: Custom interpolation logic for complex data types

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant Tween
    participant Interpolator
    participant TaskManager
    participant RAF as RequestAnimationFrame
    
    User->>Tween: set(newValue, options)
    Tween->>Tween: Update target state
    Tween->>Interpolator: get_interpolator(current, target)
    Interpolator-->>Tween: Interpolation function
    Tween->>TaskManager: Create animation task
    
    loop Animation Loop
        TaskManager->>RAF: Request frame
        RAF-->>TaskManager: Frame callback
        TaskManager->>Tween: Update current value
        Tween->>Tween: Apply easing function
        alt Animation Complete
            TaskManager->>Tween: Set final value
            TaskManager-->>User: Resolve promise
        else Continue Animation
            TaskManager->>TaskManager: Schedule next frame
        end
    end
```

## Interpolation System

```mermaid
graph TD
    subgraph "Interpolation Logic"
        InputValues[Input Values A & B]
        TypeCheck{Type Check}
        
        NumberInterp[Number Interpolation]
        ArrayInterp[Array Interpolation]
        ObjectInterp[Object Interpolation]
        DateInterp[Date Interpolation]
        SnapInterp[Snap to Final Value]
        
        InputValues --> TypeCheck
        TypeCheck -->|number| NumberInterp
        TypeCheck -->|array| ArrayInterp
        TypeCheck -->|object| ObjectInterp
        TypeCheck -->|date| DateInterp
        TypeCheck -->|other| SnapInterp
        
        ArrayInterp --> RecursiveInterp[Recursive Interpolation]
        ObjectInterp --> RecursiveInterp
        
        NumberInterp --> InterpolationFunction[t => interpolated_value]
        ArrayInterp --> InterpolationFunction
        ObjectInterp --> InterpolationFunction
        DateInterp --> InterpolationFunction
        SnapInterp --> InterpolationFunction
    end
```

## Component Interactions

```mermaid
graph LR
    subgraph "Tweening Engine"
        TweenClass[Tween Class]
        TweenedFunc[tweened Function]
        Interpolator[Interpolator]
    end
    
    subgraph "External Dependencies"
        Stores[stores]
        ReactivitySystem[reactivity_system]
        ClientRuntime[client_runtime]
        EasingFunctions[Easing Functions]
    end
    
    subgraph "Related Modules"
        SpringPhysics[spring_physics]
        Transitions[transitions]
        Animations[animations]
    end
    
    TweenClass --> ReactivitySystem
    TweenClass --> ClientRuntime
    TweenedFunc --> Stores
    Interpolator --> EasingFunctions
    
    TweenClass -.-> SpringPhysics
    TweenClass -.-> Transitions
    TweenClass -.-> Animations
```

## Implementation Details

### Type Safety and Interpolation

The tweening engine provides robust type checking and interpolation for various data types:

- **Numbers**: Linear interpolation with delta calculation
- **Arrays**: Element-wise recursive interpolation
- **Objects**: Property-wise recursive interpolation with key preservation
- **Dates**: Time-based interpolation using millisecond values
- **Other Types**: Immediate snap to final value

### Task Management

Animation tasks are managed through the client runtime's loop system:
- Integration with `requestAnimationFrame` for smooth animations
- Automatic cleanup of previous tasks when new animations start
- Promise-based completion tracking for chaining animations

### State Management

The modern `Tween` class leverages Svelte's reactivity system:
- Reactive state sources for current and target values
- Automatic effect tracking for derived animations
- Development-time debugging support with state tagging

## Migration Path

The module provides both legacy and modern APIs to support gradual migration:

**Legacy (Deprecated):**
```javascript
import { tweened } from 'svelte/motion';
const store = tweened(0);
store.set(100);
```

**Modern (Recommended):**
```javascript
import { Tween } from 'svelte/motion';
const tween = new Tween(0);
tween.target = 100;
```

## Integration Points

### With Store System
- Legacy `tweened` function creates store-compatible objects
- Seamless integration with existing store-based architectures
- See [stores](stores.md) for store system details

### With Reactivity System
- Modern `Tween` class uses reactive state sources
- Automatic dependency tracking and updates
- See [reactivity_system](reactivity_system.md) for reactivity details

### With Client Runtime
- Task scheduling through client runtime loop system
- Integration with animation frame timing
- See [client_runtime](client_runtime.md) for runtime details

### Related Motion Systems
- Complementary to spring physics for different animation styles
- Integration with transition and animation systems
- See [spring_physics](spring_physics.md), [transitions](transitions.md), and [animations](animations.md)

## Performance Considerations

- Efficient interpolation algorithms for different data types
- Automatic task cleanup to prevent memory leaks
- Optimized animation loops using `requestAnimationFrame`
- Minimal overhead for simple numeric interpolations

## Development Features

- Development-time state tagging for debugging
- Type-safe configuration options
- Comprehensive error handling for interpolation edge cases
- Promise-based API for animation sequencing