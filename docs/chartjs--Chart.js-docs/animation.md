# Animation Module Documentation

## Introduction

The Animation module is a core component of Chart.js that provides smooth, configurable animations for chart transitions and updates. It manages the lifecycle of individual animations, coordinates multiple animations, and ensures efficient rendering through optimized animation loops. The module is designed to handle complex animation scenarios including property interpolation, easing effects, and animation queuing.

## Architecture Overview

The Animation module consists of three primary components that work together to provide a complete animation system:

### Core Components

1. **Animation** - Individual animation instances that handle property interpolation
2. **Animations** - Collection manager that creates and coordinates multiple animations
3. **Animator** - Global animation loop manager that handles timing and rendering

### Architecture Diagram

```mermaid
graph TB
    subgraph "Animation Module"
        A[Animation] -->|creates| B[Individual Property Animations]
        C[Animations] -->|manages| A
        C -->|configures| D[Animation Properties]
        E[Animator] -->|coordinates| C
        E -->|controls| F[Animation Loop]
        E -->|notifies| G[Chart Rendering]
    end
    
    H[Chart Controller] -->|triggers| C
    I[Element Properties] -->|interpolates| A
    J[Easing Functions] -->|applies| A
    K[Color Helpers] -->|handles| L[Color Animations]
```

## Component Details

### Animation Class

The `Animation` class represents a single animated property transition. It handles the interpolation between start and end values over a specified duration using various easing functions.

#### Key Features:
- **Property Interpolation**: Supports boolean, color, and number interpolation
- **Easing Functions**: Integrates with easing effects for smooth transitions
- **Loop Support**: Can loop animations continuously
- **Promise Support**: Provides wait capabilities for animation completion
- **Dynamic Updates**: Allows mid-animation configuration changes

#### Animation Lifecycle:

```mermaid
stateDiagram-v2
    [*] --> Created: new Animation()
    Created --> Active: tick() called
    Active --> Updating: elapsed < duration
    Updating --> Active: property updated
    Active --> Completed: elapsed >= duration
    Completed --> [*]: animation finished
    Active --> Cancelled: cancel() called
    Cancelled --> [*]: animation terminated
```

#### Interpolation Types:

```mermaid
graph LR
    A[From Value] -->|interpolator| B[Interpolated Value]
    C[To Value] -->|factor| B
    
    subgraph "Interpolators"
        D[boolean: threshold at 0.5]
        E[color: mix colors]
        F[number: linear interpolation]
    end
```

### Animations Class

The `Animations` class manages collections of animations for chart elements. It handles the creation, configuration, and coordination of multiple simultaneous animations.

#### Key Responsibilities:
- **Property Mapping**: Maps animation configurations to target properties
- **Animation Creation**: Instantiates Animation objects based on configuration
- **Shared Options**: Manages shared animation options across elements
- **Batch Updates**: Handles multiple property updates simultaneously

#### Animation Management Flow:

```mermaid
sequenceDiagram
    participant Chart
    participant Animations
    participant Animation
    participant Animator
    
    Chart->>Animations: update(target, values)
    Animations->>Animations: _createAnimations()
    loop For each property
        Animations->>Animation: new Animation(cfg, target, prop, value)
        Animation-->>Animations: animation instance
    end
    Animations->>Animator: add(chart, animations)
    Animator->>Animator: start animation loop
    Animator->>Animation: tick(date)
    Animation->>Target: update property
```

### Animator Class

The `Animator` class serves as the global animation coordinator, managing the animation loop for all charts and ensuring efficient rendering.

#### Key Features:
- **Singleton Pattern**: Single instance manages all chart animations
- **Request Animation Frame**: Uses browser's RAF for smooth 60fps animations
- **Chart Isolation**: Maintains separate animation states per chart
- **Event System**: Provides progress and completion callbacks
- **Performance Optimization**: Efficiently manages multiple concurrent animations

#### Animation Loop Architecture:

```mermaid
graph TB
    A[requestAnimFrame] -->|triggers| B[_update]
    B -->|iterates| C[Chart Animations]
    C -->|processes| D[Active Animations]
    D -->|tick| E[Update Properties]
    E -->|if changed| F[Chart.draw]
    F -->|notify| G[Progress Callbacks]
    
    B -->|no animations| H[Stop Loop]
    D -->|completed| I[Remove Animation]
    I -->|notify| J[Complete Callbacks]
```

## Data Flow

### Animation Configuration Flow

```mermaid
graph LR
    A[Chart Configuration] -->|animation property| B[Animations.configure]
    B -->|parse| C[Animation Options]
    C -->|map| D[Property Configurations]
    D -->|store| E[properties Map]
```

### Animation Execution Flow

```mermaid
graph TB
    A[Chart Update] -->|new values| B[Animations.update]
    B -->|create| C[Animation Instances]
    C -->|add| D[Animator.add]
    D -->|start| E[Animator.start]
    E -->|if not running| F[Request Animation Frame]
    F -->|loop| G[Animator.update]
    G -->|tick| H[Animation.tick]
    H -->|interpolate| I[Property Update]
    I -->|trigger| J[Chart Re-render]
```

## Integration with Core Engine

The Animation module integrates closely with the core engine components:

### Dependencies

- **[core.defaults](core.md)**: Provides default animation configurations
- **[helpers.easing](helpers.md)**: Supplies easing function implementations
- **[helpers.color](helpers.md)**: Handles color interpolation
- **[helpers.options](helpers.md)**: Resolves animation option values
- **[helpers.extras](helpers.md)**: Provides requestAnimFrame wrapper

### Integration Points

```mermaid
graph TB
    subgraph "Core Engine"
        A[Chart Controller] -->|manages| B[Animation State]
        C[Dataset Controller] -->|updates| D[Element Properties]
        E[Element] -->|animated| F[Property Changes]
    end
    
    subgraph "Animation Module"
        G[Animations] -->|configures| H[Animation Options]
        I[Animator] -->|coordinates| J[Render Timing]
        K[Animation] -->|interpolates| L[Property Values]
    end
    
    A -->|triggers| G
    C -->|provides| K
    E -->|receives| L
    I -->|calls| M[Chart draw]
```

## Configuration System

### Animation Properties

Animations can be configured with the following properties:

```javascript
{
  duration: number,        // Animation duration in milliseconds
  easing: string,          // Easing function name
  delay: number,           // Delay before animation starts
  loop: boolean,           // Whether to loop the animation
  fn: function,            // Custom interpolation function
  type: string,            // Interpolation type ('number', 'color', 'boolean')
  from: any,               // Start value (optional)
  to: any                  // End value (optional)
}
```

### Property-Specific Configuration

```mermaid
graph TD
    A[Animation Config] -->|applies to| B[Specific Properties]
    B --> C["x: {duration: 1000}"]
    B --> D["y: {easing: 'easeOutQuad'}"]
    B --> E["radius: {type: 'number'}"]
    B --> F["backgroundColor: {type: 'color'}"]
    
    G[Properties Array] -->|alternative| H[Multiple Properties]
    H --> I["['x', 'y']: shared config"]
```

## Performance Considerations

### Optimization Strategies

1. **Batch Processing**: Multiple animations are processed in a single frame
2. **Early Termination**: Completed animations are removed immediately
3. **Shared Options**: Common configurations are shared across elements
4. **Efficient Removal**: Uses swap-and-pop for O(1) animation removal
5. **Conditional Rendering**: Only redraws charts when properties actually change

### Memory Management

```mermaid
graph LR
    A[Animation Created] -->|stores| B[Target Reference]
    C[Animation Completed] -->|clears| D[Promise References]
    E[Animation Cancelled] -->|removes| F[From Collections]
    G[Chart Destroyed] -->|cleans up| H[All Animations]
```

## Event System

The animation module provides a comprehensive event system for monitoring animation progress:

### Event Types

- **progress**: Fired on each frame during animation
- **complete**: Fired when all animations for a chart complete

### Event Data Structure

```javascript
{
  chart: Chart,           // Reference to the chart
  initial: boolean,       // Whether this is the initial animation
  numSteps: number,       // Total animation duration
  currentStep: number     // Current animation progress
}
```

## Error Handling

The animation module implements robust error handling:

1. **Graceful Degradation**: Falls back to immediate property assignment if animation fails
2. **Validation**: Validates animation configurations before processing
3. **Cancellation**: Properly handles animation cancellation and cleanup
4. **Promise Rejection**: Handles promise rejections in animation completion

## Usage Examples

### Basic Animation Configuration

```javascript
// Configure animations for a chart
chart.options.animation = {
  duration: 1000,
  easing: 'easeInOutQuart'
};
```

### Property-Specific Animation

```javascript
// Animate specific properties with different settings
chart.options.animation = {
  x: {
    duration: 800,
    easing: 'easeOutBounce'
  },
  y: {
    duration: 1200,
    easing: 'easeInOutQuad'
  },
  radius: {
    duration: 600,
    delay: 200
  }
};
```

### Animation Events

```javascript
// Listen for animation events
chart.options.animation = {
  onProgress: function(animation) {
    console.log(`Animation progress: ${animation.currentStep}/${animation.numSteps}`);
  },
  onComplete: function(animation) {
    console.log('Animation completed!');
  }
};
```

## Related Documentation

- [Core Engine](core.md) - Core chart functionality and configuration
- [Controllers](controllers.md) - Chart type controllers that use animations
- [Elements](elements.md) - Visual elements that can be animated
- [Helpers](helpers.md) - Utility functions used by the animation system
- [Plugins](plugins.md) - Plugin system that may trigger animations

## API Reference

For detailed API documentation, refer to the TypeScript definitions and inline JSDoc comments in the source files. The animation module exports the following main classes:

- `Animation` - Individual animation instances
- `Animations` - Animation collection manager  
- `Animator` - Global animation coordinator (singleton)

Each class provides methods for configuration, control, and monitoring of animations within the Chart.js framework.