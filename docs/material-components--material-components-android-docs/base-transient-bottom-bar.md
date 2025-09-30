# Base Transient Bottom Bar Module

## Introduction

The `base-transient-bottom-bar` module provides the foundational framework for displaying lightweight transient notification bars along the bottom edge of the application window. This module serves as the abstract base class for Material Design snackbars and similar transient UI components, offering a robust architecture for managing display duration, animations, user interactions, and system integration.

## Core Architecture

### Primary Components

```mermaid
classDiagram
    class BaseTransientBottomBar {
        -ViewGroup targetParent
        -Context context
        -SnackbarBaseLayout view
        -ContentViewCallback contentViewCallback
        -int duration
        -List~BaseCallback~ callbacks
        -Behavior behavior
        -Anchor anchor
        -Handler handler
        +show()
        +dismiss()
        +setDuration(int)
        +setAnimationMode(int)
        +setAnchorView(View)
        +addCallback(BaseCallback)
    }

    class ContentViewCallback {
        <<interface>>
        +animateContentIn(int, int)
        +animateContentOut(int, int)
    }

    class BaseCallback {
        <<abstract>>
        +onShown(B)
        +onDismissed(B, int)
    }

    class SnackbarBaseLayout {
        -BaseTransientBottomBar baseTransientBottomBar
        -ShapeAppearanceModel shapeAppearanceModel
        -int animationMode
        -Rect originalMargins
        +addToTargetParent(ViewGroup)
        +setAnimationMode(int)
    }

    class Behavior {
        -BehaviorDelegate delegate
        +canSwipeDismissView(View)
        +onInterceptTouchEvent(...)
    }

    BaseTransientBottomBar --> ContentViewCallback : uses
    BaseTransientBottomBar --> BaseCallback : notifies
    BaseTransientBottomBar --> SnackbarBaseLayout : contains
    BaseTransientBottomBar --> Behavior : configures
    Behavior --> BehaviorDelegate : delegates to
```

### Animation System

```mermaid
stateDiagram-v2
    [*] --> Hidden
    Hidden --> Showing : show()
    Showing --> Shown : animation complete
    Shown --> Hiding : dismiss()/timeout
    Hiding --> Hidden : animation complete
    
    state Showing {
        [*] --> SlideInAnimation
        [*] --> FadeInAnimation
        SlideInAnimation --> Shown
        FadeInAnimation --> Shown
    }
    
    state Hiding {
        [*] --> SlideOutAnimation
        [*] --> FadeOutAnimation
        SlideOutAnimation --> Hidden
        FadeOutAnimation --> Hidden
    }
```

### System Integration Architecture

```mermaid
graph TD
    A[BaseTransientBottomBar] --> B[SnackbarManager]
    A --> C[AccessibilityManager]
    A --> D[WindowInsets]
    A --> E[SwipeDismissBehavior]
    
    B --> F[Message Queue]
    B --> G[Timeout Management]
    
    C --> H[Screen Readers]
    C --> I[Accessibility Services]
    
    D --> J[System Gestures]
    D --> K[Navigation Bar]
    D --> L[Display Cutouts]
    
    E --> M[Touch Handling]
    E --> N[Swipe Detection]
```

## Component Relationships

### Dependency Flow

```mermaid
graph LR
    subgraph "Core Module"
        BTB[BaseTransientBottomBar]
        CVCB[ContentViewCallback]
    end
    
    subgraph "Supporting Systems"
        SM[SnackbarManager]
        SBL[SnackbarBaseLayout]
        BC[BaseCallback]
        B[Behavior]
    end
    
    subgraph "External Dependencies"
        CL[CoordinatorLayout]
        SDB[SwipeDismissBehavior]
        AM[AccessibilityManager]
        MU[MaterialUtils]
    end
    
    BTB --> CVCB
    BTB --> SM
    BTB --> SBL
    BTB --> BC
    BTB --> B
    B --> SDB
    SBL --> CL
    BTB --> AM
    BTB --> MU
```

## Key Features

### 1. Animation Management
- **Slide Animation**: Traditional bottom-up slide with content fade
- **Fade Animation**: Material Design 3 fade and scale animations
- **Configurable Duration**: Theme-based animation timing
- **Accessibility Aware**: Disables animations when accessibility services are active

### 2. Positioning System
- **Anchor View Support**: Position above specific UI elements
- **System Insets**: Automatic adjustment for navigation bars and display cutouts
- **Gesture Insets**: Android Q+ gesture area avoidance
- **Margin Management**: Dynamic margin calculation and updates

### 3. Interaction Handling
- **Swipe to Dismiss**: Integrated swipe dismiss behavior
- **Touch Handling**: Consumes touches to prevent background interaction
- **Timeout Management**: Automatic dismissal with pause/resume capability
- **Manual Control**: Programmatic show/dismiss with event tracking

### 4. Accessibility Integration
- **Screen Reader Support**: Proper accessibility announcements
- **Keyboard Navigation**: Dismiss action via accessibility services
- **Live Regions**: Appropriate content updates for assistive technologies
- **Focus Management**: Proper focus handling during show/hide transitions

## Data Flow

### Show Process Flow

```mermaid
sequenceDiagram
    participant App
    participant BTB as BaseTransientBottomBar
    participant SM as SnackbarManager
    participant SBL as SnackbarBaseLayout
    participant View
    
    App->>BTB: show()
    BTB->>SM: show(duration, callback)
    SM->>BTB: managerCallback.show()
    BTB->>BTB: showView()
    BTB->>SBL: addToTargetParent()
    SBL->>View: addView()
    BTB->>BTB: animateViewIn()
    BTB->>SBL: setVisibility(VISIBLE)
    BTB->>App: onViewShown()
```

### Dismiss Process Flow

```mermaid
sequenceDiagram
    participant User
    participant BTB as BaseTransientBottomBar
    participant SM as SnackbarManager
    participant CB as Callbacks
    
    User->>BTB: dismiss()/timeout/swipe
    BTB->>SM: dismiss(event)
    SM->>BTB: managerCallback.dismiss(event)
    BTB->>BTB: hideView(event)
    BTB->>BTB: animateViewOut()
    BTB->>CB: onDismissed(event)
    BTB->>View: removeView()
```

## Integration Points

### CoordinatorLayout Integration
- **Behavior System**: Custom SwipeDismissBehavior implementation
- **Layout Parameters**: CoordinatorLayout.LayoutParams support
- **Inset Edges**: Proper inset edge configuration for dodging

### Theme Integration
- **Material Theming**: Automatic theme overlay application
- **Shape Appearance**: Support for Material shape theming
- **Color System**: Material Colors integration for backgrounds
- **Motion System**: Theme-based animation interpolators and durations

### Window Management
- **Insets Handling**: System window inset processing
- **Gesture Areas**: Android Q+ mandatory gesture inset handling
- **Multi-window**: Proper behavior in multi-window environments

## Configuration Options

### Animation Modes
- `ANIMATION_MODE_SLIDE`: Traditional slide animation (default)
- `ANIMATION_MODE_FADE`: Material Design 3 fade and scale animation

### Duration Constants
- `LENGTH_SHORT`: Short display duration
- `LENGTH_LONG`: Long display duration  
- `LENGTH_INDEFINITE`: Display until manually dismissed
- Custom duration in milliseconds

### Dismiss Events
- `DISMISS_EVENT_SWIPE`: User swiped the bar away
- `DISMISS_EVENT_ACTION`: User clicked action button
- `DISMISS_EVENT_TIMEOUT`: Duration expired
- `DISMISS_EVENT_MANUAL`: Programmatically dismissed
- `DISMISS_EVENT_CONSECUTIVE`: Replaced by new bar

## Related Modules

- [snackbar-implementation.md](snackbar-implementation.md) - Concrete Snackbar implementation
- [content-layout-system.md](content-layout-system.md) - Content layout management
- [behavior-system.md](behavior-system.md) - Swipe dismiss behavior framework
- [material-motion.md](material-motion.md) - Animation and motion system
- [accessibility-framework.md](accessibility-framework.md) - Accessibility integration

## Usage Patterns

### Basic Implementation
```java
// Extend BaseTransientBottomBar for custom implementation
public class CustomBottomBar extends BaseTransientBottomBar<CustomBottomBar> {
    
    protected CustomBottomBar(ViewGroup parent, View content, ContentViewCallback callback) {
        super(parent, content, callback);
    }
    
    // Custom configuration and behavior
}
```

### Content View Callback Implementation
```java
public class CustomContentCallback implements ContentViewCallback {
    @Override
    public void animateContentIn(int delay, int duration) {
        // Custom content entry animation
    }
    
    @Override
    public void animateContentOut(int delay, int duration) {
        // Custom content exit animation
    }
}
```

This module provides the essential foundation for creating consistent, accessible, and well-behaved transient notification components that integrate seamlessly with the Material Design system and Android platform features.