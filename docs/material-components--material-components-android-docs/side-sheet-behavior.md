# Side Sheet Behavior Module

## Overview

The side-sheet-behavior module provides the core interaction behavior for Material Design side sheets, enabling horizontal sliding panels that can be expanded and collapsed from either the left or right edge of the screen. This module implements the `SideSheetBehavior` class, which serves as a CoordinatorLayout behavior plugin to make child views function as side sheets.

## Purpose and Core Functionality

The side-sheet-behavior module is responsible for:

- **Gesture Handling**: Managing touch interactions, drag detection, and velocity tracking for smooth sheet animations
- **State Management**: Controlling sheet states (expanded, hidden, dragging, settling) with proper state transitions
- **Layout Coordination**: Integrating with CoordinatorLayout to handle child view positioning and coplanar sibling relationships
- **Accessibility**: Providing proper accessibility support with pane titles and actions
- **Back Navigation**: Supporting predictive back gestures and system back button handling
- **Animation Control**: Managing smooth transitions between states with customizable friction and thresholds

## Architecture

### Core Components

```mermaid
classDiagram
    class SideSheetBehavior {
        -SheetDelegate sheetDelegate
        -ViewDragHelper viewDragHelper
        -MaterialSideContainerBackHelper sideContainerBackHelper
        -Set~SideSheetCallback~ callbacks
        -int state
        -int lastStableState
        -boolean draggable
        -float hideFriction
        -WeakReference~V~ viewRef
        -StateSettlingTracker stateSettlingTracker
        +expand()
        +hide()
        +setState(int)
        +getState()
        +addCallback(SideSheetCallback)
        +removeCallback(SideSheetCallback)
        +onLayoutChild(CoordinatorLayout, V, int)
        +onInterceptTouchEvent(CoordinatorLayout, V, MotionEvent)
        +onTouchEvent(CoordinatorLayout, V, MotionEvent)
    }

    class SheetDelegate {
        <<interface>>
        +getSheetEdge()
        +getExpandedOffset()
        +getHiddenOffset()
        +calculateSlideOffset(int)
        +shouldHide(View, float)
        +updateCoplanarSiblingLayoutParams(MarginLayoutParams, int, int)
    }

    class LeftSheetDelegate {
        -SideSheetBehavior behavior
        +getSheetEdge() int
        +getExpandedOffset() int
        +getHiddenOffset() int
        +calculateSlideOffset(int) float
    }

    class RightSheetDelegate {
        -SideSheetBehavior behavior
        +getSheetEdge() int
        +getExpandedOffset() int
        +getHiddenOffset() int
        +calculateSlideOffset(int) float
    }

    class StateSettlingTracker {
        -int targetState
        -boolean isContinueSettlingRunnablePosted
        -Runnable continueSettlingRunnable
        +continueSettlingToState(int)
    }

    class SavedState {
        -int state
        +SavedState(Parcelable, SideSheetBehavior)
        +writeToParcel(Parcel, int)
    }

    SideSheetBehavior --> SheetDelegate : uses
    SideSheetBehavior --> StateSettlingTracker : contains
    SideSheetBehavior --> SavedState : creates
    LeftSheetDelegate ..|> SheetDelegate : implements
    RightSheetDelegate ..|> SheetDelegate : implements
```

### State Management

```mermaid
stateDiagram-v2
    [*] --> STATE_HIDDEN
    STATE_HIDDEN --> STATE_SETTLING : expand()
    STATE_SETTLING --> STATE_EXPANDED : animation complete
    STATE_EXPANDED --> STATE_SETTLING : hide()
    STATE_SETTLING --> STATE_HIDDEN : animation complete
    
    STATE_EXPANDED --> STATE_DRAGGING : user drag
    STATE_HIDDEN --> STATE_DRAGGING : user drag
    STATE_DRAGGING --> STATE_SETTLING : release
    STATE_SETTLING --> STATE_EXPANDED : velocity/position
    STATE_SETTLING --> STATE_HIDDEN : velocity/position
```

## Component Relationships

### Integration with CoordinatorLayout

```mermaid
sequenceDiagram
    participant App
    participant CoordinatorLayout
    participant SideSheetBehavior
    participant ViewDragHelper
    
    App->>SideSheetBehavior: setState(STATE_EXPANDED)
    SideSheetBehavior->>SideSheetBehavior: startSettling()
    SideSheetBehavior->>ViewDragHelper: smoothSlideViewTo()
    ViewDragHelper->>SideSheetBehavior: onViewPositionChanged()
    SideSheetBehavior->>SideSheetBehavior: dispatchOnSlide()
    SideSheetBehavior->>SideSheetBehavior: setStateInternal(STATE_SETTLING)
    ViewDragHelper-->>SideSheetBehavior: continueSettling()
    SideSheetBehavior->>SideSheetBehavior: setStateInternal(STATE_EXPANDED)
```

### Touch Event Processing

```mermaid
flowchart TD
    A[Touch Event] --> B{shouldInterceptTouchEvent?}
    B -->|Yes| C[Record Velocity]
    C --> D{Action Type}
    D -->|ACTION_DOWN| E[Set initialX]
    D -->|ACTION_MOVE| F{isDraggedFarEnough?}
    F -->|Yes| G[captureChildView]
    F -->|No| H[Continue Monitoring]
    D -->|ACTION_UP| I[calculateTargetStateOnViewReleased]
    I --> J[startSettling]
    B -->|No| K[Return False]
```

## Key Features

### 1. Edge-based Positioning
The behavior automatically determines sheet positioning based on layout gravity:
- `Gravity.LEFT` → LeftSheetDelegate
- `Gravity.RIGHT` → RightSheetDelegate

### 2. Coplanar Sibling Support
Sheets can be configured to work with sibling views that adjust their layout during expansion/collapse:
```java
// Set by ID
setCoplanarSiblingViewId(R.id.main_content)

// Set by reference
setCoplanarSiblingView(mainContentView)
```

### 3. Back Gesture Integration
Full support for Android's predictive back gestures:
- `startBackProgress()` - Initialize back gesture
- `updateBackProgress()` - Update animation during gesture
- `handleBackInvoked()` - Complete back action
- `cancelBackProgress()` - Cancel gesture

### 4. Accessibility Features
- Automatic pane title setting for TalkBack
- Expand/Collapse accessibility actions
- Proper visibility management
- Screen reader support

## State Persistence

The `SavedState` class handles configuration changes:

```mermaid
classDiagram
    class SavedState {
        -int state
        +SavedState(Parcelable, SideSheetBehavior)
        +writeToParcel(Parcel, int)
        +CREATOR: Creator~SavedState~
    }
    
    class AbsSavedState {
        <<abstract>>
    }
    
    SavedState --|> AbsSavedState : extends
```

## Configuration Options

### XML Attributes
- `behavior_draggable` - Enable/disable drag interactions
- `backgroundTint` - Background color tint
- `shapeAppearance` - Shape appearance model
- `coplanarSiblingViewId` - Sibling view for coplanar expansion
- `android:elevation` - Sheet elevation

### Programmatic Configuration
- `setDraggable(boolean)` - Control drag behavior
- `setHideFriction(float)` - Adjust swipe sensitivity
- `addCallback(SideSheetCallback)` - Listen to state changes
- `setCoplanarSiblingView(View)` - Configure coplanar relationships

## Dependencies

The side-sheet-behavior module integrates with several other Material Design components:

- **[CoordinatorLayout](coordinator-layout.md)** - Parent layout for behavior integration
- **[MaterialShapeDrawable](shape.md)** - Background shape rendering
- **[ViewDragHelper](appbar-behaviors.md)** - Drag gesture processing
- **[MaterialSideContainerBackHelper](motion.md)** - Back gesture support
- **[Sheet](sheet.md)** - Common sheet interface

## Usage Examples

### Basic Setup
```xml
<androidx.coordinatorlayout.widget.CoordinatorLayout>
    <LinearLayout
        android:layout_width="300dp"
        android:layout_height="match_parent"
        android:layout_gravity="start"
        app:layout_behavior="com.google.android.material.sidesheet.SideSheetBehavior"
        app:behavior_draggable="true">
        <!-- Side sheet content -->
    </LinearLayout>
</androidx.coordinatorlayout.widget.CoordinatorLayout>
```

### Programmatic Control
```java
SideSheetBehavior<LinearLayout> behavior = SideSheetBehavior.from(sideSheetView);
behavior.addCallback(new SideSheetCallback() {
    @Override
    public void onStateChanged(@NonNull View sheet, int newState) {
        // Handle state changes
    }
    
    @Override
    public void onSlide(@NonNull View sheet, float slideOffset) {
        // Handle slide progress
    }
});

// Expand the sheet
behavior.expand();

// Hide the sheet
behavior.hide();
```

## Performance Considerations

- **View Recycling**: Uses WeakReference for view references to prevent memory leaks
- **Velocity Tracking**: Efficient velocity calculation for smooth animations
- **State Optimization**: Minimal state transitions and layout passes
- **Animation Performance**: Hardware-accelerated animations with proper invalidation

## Testing

The module provides several testing utilities:
- `getBackHelper()` - Access back gesture helper for testing
- `shouldSkipSmoothAnimation()` - Control animation behavior in tests
- `getLastStableState()` - Verify state persistence

## Related Documentation

- [Sheet Dialog Management](sheet-dialog-management.md) - Dialog-based side sheets
- [Sheet Utilities](sheet-utilities.md) - Utility functions for sheet operations
- [Material Motion](motion.md) - Animation and transition system
- [Shape System](shape.md) - Shape appearance and customization