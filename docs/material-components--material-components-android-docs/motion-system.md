# Motion System Module Documentation

## Introduction

The Motion System module is a core component of the Material Design Components library that provides essential utilities and helpers for implementing Material Design motion patterns. This module serves as the foundation for creating smooth, consistent animations and transitions across Android applications, ensuring they adhere to Material Design motion guidelines.

The module specializes in two primary areas: back gesture animation support and motion utility functions. It provides a standardized approach to handling predictive back gestures introduced in Android 13+ and offers comprehensive utilities for resolving motion attributes from Material Design themes.

## Architecture Overview

The motion system module is architected around two core components that work together to provide comprehensive motion support:

### Core Components

1. **MaterialBackAnimationHelper** - A base helper class for views that support back handling
2. **MotionUtils** - A utility class for motion system functions including theme attribute resolution

### Module Structure

```
motion-system/
├── MaterialBackAnimationHelper - Back gesture animation support
└── MotionUtils - Motion utility functions and theme resolution
```

## Component Architecture

### MaterialBackAnimationHelper Architecture

The MaterialBackAnimationHelper serves as an abstract base class that provides common functionality for views that need to handle back gestures with animations. It manages the animation lifecycle and provides standardized duration values based on Material Design motion specifications.

```mermaid
classDiagram
    class MaterialBackAnimationHelper {
        -view: V
        -hideDurationMax: int
        -hideDurationMin: int
        -cancelDuration: int
        -backEvent: BackEventCompat
        -progressInterpolator: TimeInterpolator
        +MaterialBackAnimationHelper(V view)
        +interpolateProgress(float): float
        +onStartBackProgress(BackEventCompat): void
        +onUpdateBackProgress(BackEventCompat): BackEventCompat
        +onHandleBackInvoked(): BackEventCompat
        +onCancelBackProgress(): BackEventCompat
    }
```

### MotionUtils Architecture

MotionUtils provides static utility methods for resolving motion-related attributes from Material Design themes, including spring forces, durations, and interpolators.

```mermaid
classDiagram
    class MotionUtils {
        <<utility>>
        +resolveThemeSpringForce(Context, int, int): SpringForce
        +resolveThemeDuration(Context, int, int): int
        +resolveThemeInterpolator(Context, int, TimeInterpolator): TimeInterpolator
        -getLegacyThemeInterpolator(String): TimeInterpolator
        -isLegacyEasingAttribute(String): boolean
        -isLegacyEasingType(String, String): boolean
        -getLegacyEasingContent(String, String): String
        -getLegacyControlPoint(String[], int): float
    }
```

## Data Flow and Dependencies

### Theme Attribute Resolution Flow

```mermaid
flowchart TD
    A[MotionUtils.resolveTheme* Method] --> B{Attribute Type}
    B -->|Spring Force| C[resolveThemeSpringForce]
    B -->|Duration| D[resolveThemeDuration]
    B -->|Interpolator| E[resolveThemeInterpolator]
    
    C --> F[MaterialAttributes.resolve]
    D --> G[MaterialAttributes.resolveInteger]
    E --> H{Legacy Format?}
    
    H -->|Yes| I[getLegacyThemeInterpolator]
    H -->|No| J[AnimationUtils.loadInterpolator]
    
    I --> K[Parse Control Points/Path]
    K --> L[Create PathInterpolator]
    
    F --> M[Configure SpringForce]
    G --> N[Return Duration]
    J --> O[Return Interpolator]
    L --> O
    M --> P[Return SpringForce]
```

### Back Gesture Animation Flow

```mermaid
sequenceDiagram
    participant View
    participant MaterialBackAnimationHelper
    participant BackEventCompat
    participant AnimationSystem
    
    View->>MaterialBackAnimationHelper: startBackProgress(backEvent)
    MaterialBackAnimationHelper->>MaterialBackAnimationHelper: onStartBackProgress()
    MaterialBackAnimationHelper->>BackEventCompat: Store backEvent
    
    loop During Gesture
        View->>MaterialBackAnimationHelper: updateBackProgress(backEvent)
        MaterialBackAnimationHelper->>MaterialBackAnimationHelper: onUpdateBackProgress()
        MaterialBackAnimationHelper->>MaterialBackAnimationHelper: interpolateProgress()
        MaterialBackAnimationHelper->>View: Return interpolated progress
        View->>AnimationSystem: Update animation state
    end
    
    alt Gesture Completed
        View->>MaterialBackAnimationHelper: handleBackInvoked()
        MaterialBackAnimationHelper->>MaterialBackAnimationHelper: onHandleBackInvoked()
        MaterialBackAnimationHelper->>AnimationSystem: Complete animation
    else Gesture Cancelled
        View->>MaterialBackAnimationHelper: cancelBackProgress()
        MaterialBackAnimationHelper->>MaterialBackAnimationHelper: onCancelBackProgress()
        MaterialBackAnimationHelper->>AnimationSystem: Cancel animation
    end
```

## Component Interactions

### Integration with Material Design System

The motion system module integrates with several other Material Design components:

```mermaid
graph TB
    subgraph "Motion System"
        MBH[MaterialBackAnimationHelper]
        MU[MotionUtils]
    end
    
    subgraph "Theme System"
        MA[MaterialAttributes]
        MT[MaterialTheme]
    end
    
    subgraph "Animation System"
        SF[SpringForce]
        PI[PathInterpolator]
        AU[AnimationUtils]
    end
    
    subgraph "Component Library"
        ABL[AppBarLayout]
        BSB[BottomSheetBehavior]
        SFB[FloatingActionButton.Behavior]
    end
    
    MBH -->|Uses| MU
    MU -->|Resolves attributes| MA
    MU -->|Creates| SF
    MU -->|Creates| PI
    MU -->|Delegates to| AU
    
    ABL -->|Inherits from| MBH
    BSB -->|Inherits from| MBH
    SFB -->|Inherits from| MBH
    
    MT -->|Provides attributes| MA
```

## Process Flows

### Motion Attribute Resolution Process

```mermaid
flowchart LR
    Start([Start]) --> CheckAttr{Check Theme Attribute}
    CheckAttr -->|Exists| ResolveType{Determine Type}
    CheckAttr -->|Not Found| UseDefault[Use Default Value]
    
    ResolveType -->|Spring| ParseSpring[Parse Spring Attributes]
    ResolveType -->|Duration| ParseDuration[Parse Duration Value]
    ResolveType -->|Interpolator| ParseEasing[Parse Easing Function]
    
    ParseSpring --> ValidateSpring{Valid Spring?}
    ParseDuration --> ValidateDuration{Valid Duration?}
    ParseEasing --> ValidateEasing{Valid Easing?}
    
    ValidateSpring -->|Yes| CreateSpring[Create SpringForce]
    ValidateSpring -->|No| ThrowError[Throw IllegalArgumentException]
    
    ValidateDuration -->|Yes| ReturnDuration[Return Duration]
    ValidateDuration -->|No| UseDefault
    
    ValidateEasing -->|Legacy Format| ProcessLegacy[Process Legacy Format]
    ValidateEasing -->|Resource ID| LoadResource[Load from Resource]
    
    ProcessLegacy --> CreateInterpolator[Create PathInterpolator]
    LoadResource --> ReturnInterpolator[Return Interpolator]
    CreateSpring --> ReturnSpring[Return SpringForce]
    
    UseDefault --> End([End])
    ReturnDuration --> End
    ReturnInterpolator --> End
    ReturnSpring --> End
    ThrowError --> End
```

### Back Gesture Handling Process

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> BackProgressStarted: startBackProgress()
    BackProgressStarted --> BackProgressUpdated: updateBackProgress()
    BackProgressUpdated --> BackProgressUpdated: updateBackProgress()
    BackProgressStarted --> BackCancelled: cancelBackProgress()
    BackProgressUpdated --> BackCancelled: cancelBackProgress()
    BackProgressUpdated --> BackInvoked: handleBackInvoked()
    BackCancelled --> Idle: Animation Complete
    BackInvoked --> Idle: Animation Complete
    
    state BackProgressStarted {
        [*] --> StoreEvent
        StoreEvent --> ValidateState
        ValidateState --> [*]
    }
    
    state BackProgressUpdated {
        [*] --> InterpolateProgress
        InterpolateProgress --> UpdateAnimation
        UpdateAnimation --> [*]
    }
```

## Key Features and Capabilities

### MaterialBackAnimationHelper Features

1. **Progress Interpolation**: Provides smooth progress interpolation using Material Design easing curves
2. **Duration Management**: Automatically resolves appropriate animation durations from theme attributes
3. **Back Event Handling**: Manages the complete lifecycle of back gesture events
4. **State Validation**: Ensures proper sequencing of back gesture method calls
5. **Generic View Support**: Works with any View type through generics

### MotionUtils Features

1. **Spring Force Resolution**: Creates SpringForce objects from Material Design theme attributes
2. **Duration Resolution**: Resolves animation durations with fallback values
3. **Interpolator Resolution**: Supports both legacy and modern interpolator formats
4. **Legacy Compatibility**: Maintains backward compatibility with older theme formats
5. **Validation**: Comprehensive validation of resolved values

## Usage Patterns

### Implementing Back Gesture Support

```java
public class CustomView extends View {
    private final MaterialBackAnimationHelper<CustomView> backHelper;
    
    public CustomView(Context context) {
        super(context);
        backHelper = new MaterialBackAnimationHelper<>(this);
    }
    
    public void startBackProgress(BackEventCompat event) {
        backHelper.onStartBackProgress(event);
        // Custom animation setup
    }
    
    public void updateBackProgress(BackEventCompat event) {
        BackEventCompat previousEvent = backHelper.onUpdateBackProgress(event);
        float progress = backHelper.interpolateProgress(event.getProgress());
        // Update animation based on progress
    }
}
```

### Resolving Motion Attributes

```java
// Resolve spring force from theme
SpringForce springForce = MotionUtils.resolveThemeSpringForce(
    context, 
    R.attr.motionSpringMedium, 
    R.style.MaterialSpring_Medium
);

// Resolve duration from theme
int duration = MotionUtils.resolveThemeDuration(
    context,
    R.attr.motionDurationMedium2,
    300 // default duration
);

// Resolve interpolator from theme
TimeInterpolator interpolator = MotionUtils.resolveThemeInterpolator(
    context,
    R.attr.motionEasingStandardInterpolator,
    new AccelerateDecelerateInterpolator() // default
);
```

## Integration with Other Modules

The motion system module serves as a foundational component that other Material Design modules depend on for consistent motion behavior:

- **[AppBarLayout](appbar.md)**: Uses MaterialBackAnimationHelper for back gesture handling in collapsing toolbars
- **[BottomSheetBehavior](bottom-sheet.md)**: Leverages motion utilities for animation configuration
- **[FloatingActionButton](fab.md)**: Utilizes motion helpers for transformation animations
- **[Transition System](transition.md)**: Builds upon motion utilities for complex transition animations

## Best Practices

1. **Theme Consistency**: Always use theme attributes for motion values to ensure consistency across the application
2. **Error Handling**: Handle potential IllegalArgumentException when resolving motion attributes
3. **State Management**: Ensure proper sequencing of back gesture method calls
4. **Performance**: Reuse resolved motion values when possible to avoid repeated theme lookups
5. **Testing**: Test motion behavior with different theme configurations and system settings

## Future Considerations

The motion system module is designed to evolve with Material Design specifications and Android platform capabilities. Future enhancements may include:

- Additional animation helpers for new gesture types
- Enhanced spring physics configurations
- Support for new interpolator types
- Integration with emerging animation APIs
- Performance optimizations for complex motion scenarios