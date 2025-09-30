# ProgressIndicator Module Documentation

## Introduction

The ProgressIndicator module is a core component of the Material Design Components library that provides animated progress indicators for Android applications. It extends the standard Android ProgressBar with Material Design principles, offering both determinate and indeterminate progress visualization with sophisticated animation behaviors and customization options.

## Module Architecture

### Core Components

The module is built around a single primary component:

- **BaseProgressIndicator**: Abstract base class that provides common functionality for all progress indicator types

### Module Structure

```
progressindicator/
└── BaseProgressIndicator (abstract base class)
    ├── Determinate mode support
    ├── Indeterminate mode support
    ├── Animation behaviors
    └── Customization attributes
```

## Component Details

### BaseProgressIndicator

The `BaseProgressIndicator` is an abstract class that extends Android's `ProgressBar` and serves as the foundation for all Material Design progress indicators. It provides:

#### Key Features

1. **Dual Mode Support**: Seamlessly switches between determinate and indeterminate progress modes
2. **Animation Behaviors**: Configurable show/hide animations with multiple behavior options
3. **Material Design Compliance**: Follows Material Design guidelines for progress indicators
4. **Customization**: Extensive styling options for colors, thickness, corner radius, and wave properties
5. **Performance Optimization**: Efficient drawing and animation management

#### Animation Behaviors

The component supports various animation behaviors:

**Show Animations:**
- `SHOW_NONE`: No animation
- `SHOW_OUTWARD`: Expands outward
- `SHOW_INWARD`: Expands inward

**Hide Animations:**
- `HIDE_NONE`: No animation
- `HIDE_OUTWARD`: Contracts outward
- `HIDE_INWARD`: Contracts inward
- `HIDE_ESCAPE`: Escape-style animation

#### Core Attributes

- **trackThickness**: Thickness of the indicator and track
- **indicatorColor**: Color(s) of the progress indicator
- **trackColor**: Color of the background track
- **trackCornerRadius**: Rounded corner radius
- **showAnimationBehavior**: Animation for showing the indicator
- **hideAnimationBehavior**: Animation for hiding the indicator
- **showDelay**: Delay before showing the indicator
- **minHideDelay**: Minimum time before hiding

## Architecture Diagram

```mermaid
graph TB
    subgraph "ProgressIndicator Module"
        BPI[BaseProgressIndicator]
        
        subgraph "Core Functionality"
            BPI --> DM[Determinate Mode]
            BPI --> IM[Indeterminate Mode]
            BPI --> AB[Animation Behaviors]
            BPI --> VC[Visibility Control]
        end
        
        subgraph "Customization"
            BPI --> TC[Track Customization]
            BPI --> IC[Indicator Customization]
            BPI --> AC[Animation Customization]
        end
        
        subgraph "Drawing System"
            BPI --> DD[DeterminateDrawable]
            BPI --> ID[IndeterminateDrawable]
            BPI --> DWAVC[DrawableWithAnimatedVisibilityChange]
        end
    end
    
    subgraph "Android Framework"
        PB[ProgressBar]
        D[Drawable]
        V[View]
    end
    
    BPI -.->|extends| PB
    DD -.->|implements| DWAVC
    ID -.->|implements| DWAVC
    DWAVC -.->|extends| D
    PB -.->|extends| V
```

## Data Flow

```mermaid
sequenceDiagram
    participant App
    participant BPI as BaseProgressIndicator
    participant DWAVC as DrawableWithAnimatedVisibilityChange
    participant DD as DeterminateDrawable
    participant ID as IndeterminateDrawable
    
    App->>BPI: show()
    BPI->>BPI: internalShow()
    BPI->>DWAVC: setVisible(true, false, animate)
    
    App->>BPI: setProgress(progress, animated)
    alt isIndeterminate()
        BPI->>ID: requestCancelAnimatorAfterCurrentCycle()
        ID->>BPI: switchIndeterminateModeCallback
        BPI->>BPI: setIndeterminate(false)
    end
    BPI->>DD: setLevelByFraction()
    
    App->>BPI: hide()
    BPI->>BPI: internalHide()
    BPI->>DWAVC: setVisible(false, false, true)
    DWAVC->>BPI: hideAnimationCallback
    BPI->>BPI: setVisibility(INVISIBLE)
```

## Component Relationships

```mermaid
graph LR
    subgraph "Material Components Dependencies"
        BPI[BaseProgressIndicator]
        MC[MaterialColors]
        TE[ThemeEnforcement]
        ADSP[AnimatorDurationScaleProvider]
    end
    
    subgraph "Android Framework"
        PB[ProgressBar]
        D[Drawable]
        C[Canvas]
        VA[ViewGroup.LayoutParams]
    end
    
    subgraph "Support Libraries"
        AVD[Animatable2Compat]
        DA[DynamicAnimation]
    end
    
    BPI -->|uses| MC
    BPI -->|uses| TE
    BPI -->|uses| ADSP
    BPI -->|extends| PB
    BPI -->|uses| D
    BPI -->|uses| C
    BPI -->|implements| AVD
    BPI -->|uses| DA
```

## Process Flow

### Initialization Process

```mermaid
flowchart TD
    A[Constructor Called] --> B[Create Spec Object]
    B --> C[Load Attributes from XML]
    C --> D[Initialize Animation Provider]
    D --> E[Set Parent Initialization Flag]
    E --> F[Ready for Use]
```

### Show/Hide Animation Process

```mermaid
sequenceDiagram
    participant App
    participant BPI as BaseProgressIndicator
    participant DWAVC as DrawableWithAnimatedVisibilityChange
    
    rect rgb(200, 230, 255)
        Note over App,BPI: Show Process
        App->>BPI: show()
        alt showDelay > 0
            BPI->>BPI: postDelayed(delayedShow, showDelay)
        else showDelay <= 0
            BPI->>BPI: internalShow()
        end
        BPI->>BPI: setVisibility(VISIBLE)
        BPI->>DWAVC: setVisible(true, false, animate)
    end
    
    rect rgb(255, 230, 200)
        Note over App,BPI: Hide Process
        App->>BPI: hide()
        alt getVisibility() != VISIBLE
            BPI->>BPI: return early
        else is visible
            alt minHideDelay > 0
                BPI->>BPI: check time elapsed
                alt enough time elapsed
                    BPI->>BPI: internalHide()
                else not enough time
                    BPI->>BPI: postDelayed(delayedHide, remainingTime)
                end
            else minHideDelay <= 0
                BPI->>BPI: internalHide()
            end
            BPI->>DWAVC: setVisible(false, false, true)
            DWAVC->>BPI: hideAnimationCallback
            BPI->>BPI: setVisibility(INVISIBLE)
        end
    end
```

### Mode Switching Process

```mermaid
sequenceDiagram
    participant App
    participant BPI as BaseProgressIndicator
    participant DD as DeterminateDrawable
    participant ID as IndeterminateDrawable
    
    App->>BPI: setIndeterminate(boolean)
    
    alt indeterminate == isIndeterminate()
        BPI->>BPI: return early (no change)
    else mode change requested
        BPI->>BPI: hide current drawable
        BPI->>BPI: call super.setIndeterminate()
        
        alt new mode is indeterminate
            BPI->>BPI: show indeterminate drawable
            alt component is visible
                BPI->>ID: startAnimator()
            end
        else new mode is determinate
            BPI->>BPI: show determinate drawable
        end
        
        Note over BPI: Mode switch complete
    end
```

## Integration with Other Modules

The ProgressIndicator module integrates with several other Material Design components:

### Color Module Integration
- Uses [`MaterialColors`](color.md) for theme-aware color resolution
- Supports dynamic color theming through the color system

### Theme System Integration
- Leverages [`ThemeEnforcement`](theme.md) for consistent theming
- Respects Material Design theme attributes

### Animation System Integration
- Uses [`AnimatorDurationScaleProvider`](animation.md) for system-wide animation scaling
- Supports accessibility settings for reduced motion

## Usage Examples

### Basic Usage

```xml
<com.google.android.material.progressindicator.LinearProgressIndicator
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:progress="75"
    app:trackThickness="4dp"
    app:indicatorColor="@color/colorPrimary"
    app:trackColor="@color/colorSurfaceVariant" />
```

### Programmatic Control

```java
progressIndicator.show();
progressIndicator.setProgressCompat(50, true);
progressIndicator.setIndicatorColor(Color.RED, Color.BLUE);
progressIndicator.hide();
```

## Performance Considerations

1. **Animation Optimization**: Uses hardware acceleration when available
2. **Memory Management**: Properly manages drawable lifecycle
3. **Drawing Efficiency**: Custom onDraw implementation optimized for progress indicators
4. **Thread Safety**: Synchronized methods for progress updates

## Accessibility

- Supports screen readers with proper content descriptions
- Respects system animation settings
- Provides haptic feedback options
- Supports high contrast mode

## Testing

The module includes comprehensive testing utilities:

- [`@VisibleForTesting`](testing.md) annotations for testable methods
- Mock animation providers for unit testing
- Accessibility testing support

## Future Enhancements

Potential areas for expansion:

1. Additional progress indicator types (circular, linear variants)
2. Enhanced animation curves and transitions
3. Integration with motion design system
4. Performance optimizations for low-end devices

## References

- [Material Design Progress Indicators](https://material.io/components/progress-indicators)
- [Android ProgressBar Documentation](https://developer.android.com/reference/android/widget/ProgressBar)
- Related module documentation:
  - [Color Module](color.md)
  - [Animation Module](animation.md)
  - [Theme System](theme.md)