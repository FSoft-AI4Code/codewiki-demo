# Search View Module Documentation

## Overview

The search-view module provides a comprehensive full-screen search interface component for Android applications following Material Design principles. It implements the `SearchView` class that offers an immersive search experience with smooth animations, gesture handling, and seamless integration with the search-bar module.

## Purpose and Core Functionality

The SearchView module serves as the primary interface for full-screen search interactions within the Material Design component library. It provides:

- **Full-screen search interface**: A dedicated search view that overlays the entire screen
- **Seamless integration with SearchBar**: Automatic coordination with SearchBar components for expand/collapse animations
- **Gesture support**: Back gesture handling and predictive back navigation
- **Accessibility features**: Comprehensive accessibility support including modal behavior and keyboard navigation
- **Customizable appearance**: Support for themes, colors, and custom layouts
- **State management**: Robust state handling for visibility, text content, and transition states

## Architecture and Component Relationships

### Core Components

The search-view module consists of three primary components:

1. **SearchView.Behavior**: CoordinatorLayout behavior for automatic SearchBar integration
2. **SearchView.TransitionListener**: Interface for monitoring transition state changes
3. **SearchView.SavedState**: Parcelable state preservation for configuration changes

### Module Dependencies

```mermaid
graph TD
    A[search-view] --> B[search-bar]
    A --> C[appbar]
    A --> D[animation]
    A --> E[color]
    A --> F[internal]
    A --> G[motion]
    A --> H[shape]
    A --> I[theme]
    
    B --> A
    C --> A
    D --> A
    E --> A
    F --> A
    G --> A
    H --> A
    I --> A
```

### Component Architecture

```mermaid
classDiagram
    class SearchView {
        -View scrim
        -ClippableRoundedCornerLayout rootView
        -MaterialToolbar toolbar
        -EditText editText
        -ImageButton clearButton
        -TouchObserverFrameLayout contentContainer
        -SearchViewAnimationHelper searchViewAnimationHelper
        -MaterialBackOrchestrator backOrchestrator
        -Set~TransitionListener~ transitionListeners
        -TransitionState currentTransitionState
        +show()
        +hide()
        +setVisible(boolean)
        +setupWithSearchBar(SearchBar)
        +addTransitionListener(TransitionListener)
        +getEditText()
        +getText()
        +setText(CharSequence)
        +clearText()
    }
    
    class Behavior {
        +onDependentViewChanged(CoordinatorLayout, SearchView, View)
    }
    
    class TransitionListener {
        <<interface>>
        +onStateChanged(SearchView, TransitionState, TransitionState)
    }
    
    class SavedState {
        -String text
        -int visibility
        +writeToParcel(Parcel, int)
    }
    
    class TransitionState {
        <<enumeration>>
        HIDING
        HIDDEN
        SHOWING
        SHOWN
    }
    
    SearchView ..|> CoordinatorLayout.AttachedBehavior
    SearchView ..|> MaterialBackHandler
    SearchView --> Behavior : contains
    SearchView --> TransitionListener : uses
    SearchView --> SavedState : uses
    SearchView --> TransitionState : uses
```

## Data Flow and Component Interaction

### SearchView State Management Flow

```mermaid
stateDiagram-v2
    [*] --> HIDDEN
    HIDDEN --> SHOWING : show()
    SHOWING --> SHOWN : animation complete
    SHOWN --> HIDING : hide() / back gesture
    HIDING --> HIDDEN : animation complete
    
    SHOWING --> SHOWING : cancel animation
    HIDING --> HIDING : cancel animation
```

### Integration with SearchBar

```mermaid
sequenceDiagram
    participant User
    participant SearchBar
    participant SearchView
    participant AnimationHelper
    
    User->>SearchBar: click
    SearchBar->>SearchView: show()
    SearchView->>AnimationHelper: startShowAnimation()
    AnimationHelper->>SearchView: setTransitionState(SHOWING)
    AnimationHelper->>SearchView: setTransitionState(SHOWN)
    SearchView->>User: display full search interface
    
    User->>SearchView: back gesture
    SearchView->>AnimationHelper: startBackProgress()
    SearchView->>AnimationHelper: handleBackInvoked()
    AnimationHelper->>SearchView: setTransitionState(HIDING)
    AnimationHelper->>SearchView: setTransitionState(HIDDEN)
    SearchView->>SearchBar: transfer focus
```

### Back Gesture Handling

```mermaid
flowchart TD
    A[Back Gesture Detected] --> B{Is SearchView shown?}
    B -->|Yes| C{Is back handling enabled?}
    B -->|No| Z[Ignore gesture]
    
    C -->|Yes| D{Android version >= U?}
    C -->|No| Z
    
    D -->|Yes| E[Start predictive back animation]
    D -->|No| F[Hide SearchView]
    
    E --> G{Gesture completed?}
    G -->|Yes| H[Finish back animation]
    G -->|No| I[Cancel back animation]
    
    H --> J[Hide SearchView]
    I --> K[Restore SearchView state]
```

## Key Features and Implementation Details

### Animation System

The SearchView employs a sophisticated animation system through `SearchViewAnimationHelper` that handles:

- **Show/Hide animations**: Smooth transitions between hidden and shown states
- **Back gesture animations**: Predictive back navigation with progress tracking
- **Navigation icon morphing**: Animated transitions between SearchBar and SearchView navigation icons
- **Menu item animations**: Coordinated animation of toolbar menu items

### Accessibility Features

The module implements comprehensive accessibility support:

- **Modal behavior**: Prevents interaction with background content when shown
- **Keyboard navigation**: Full keyboard accessibility with proper focus management
- **Screen reader support**: Proper content descriptions and accessibility events
- **Focus management**: Automatic focus transfer between SearchBar and SearchView

### Window Insets Handling

SearchView properly handles system window insets:

- **Status bar spacer**: Automatic adjustment for translucent status bars
- **Toolbar padding**: Dynamic padding based on system bars and display cutouts
- **Divider margins**: Proper margin adjustment for system insets
- **Keyboard management**: Coordination with soft keyboard appearance/disappearance

### State Preservation

The SavedState implementation ensures:

- **Text content preservation**: Search text is maintained across configuration changes
- **Visibility state**: Current visibility state is preserved
- **Parcelable implementation**: Efficient state serialization

## Integration Patterns

### Basic Integration with SearchBar

```xml
<androidx.coordinatorlayout.widget.CoordinatorLayout>
    <com.google.android.material.appbar.AppBarLayout>
        <com.google.android.material.search.SearchBar
            android:id="@+id/search_bar" />
    </com.google.android.material.appbar.AppBarLayout>
    
    <com.google.android.material.search.SearchView
        android:id="@+id/search_view"
        app:layout_anchor="@id/search_bar" />
</androidx.coordinatorlayout.widget.CoordinatorLayout>
```

### Programmatic Setup

```java
SearchBar searchBar = findViewById(R.id.search_bar);
SearchView searchView = findViewById(R.id.search_view);

// Automatic setup via CoordinatorLayout
searchView.setupWithSearchBar(searchBar);

// Manual transition control
searchView.addTransitionListener(new SearchView.TransitionListener() {
    @Override
    public void onStateChanged(@NonNull SearchView searchView, 
                             @NonNull SearchView.TransitionState previousState,
                             @NonNull SearchView.TransitionState newState) {
        // Handle state changes
    }
});
```

## Related Documentation

- [search-bar.md](search-bar.md) - SearchBar component documentation
- [appbar.md](appbar.md) - AppBarLayout integration
- [animation.md](animation.md) - Animation system details
- [motion.md](motion.md) - Motion and gesture handling
- [internal.md](internal.md) - Internal utilities and helpers

## Process Flows

### Search Interaction Flow

```mermaid
flowchart LR
    A[User initiates search] --> B{SearchBar clicked}
    B --> C[SearchView shows]
    C --> D[Keyboard appears]
    D --> E[User types query]
    E --> F{Text changed}
    F --> G[Update clear button visibility]
    F --> H[Notify text listeners]
    E --> I[User clears text]
    I --> J[Clear button clicked]
    J --> K[Text cleared]
    K --> D
    
    E --> L[User submits search]
    L --> M[Process search]
    
    E --> N[User cancels]
    N --> O[Back gesture/click]
    O --> P[SearchView hides]
    P --> Q[Focus returns to SearchBar]
```

### Configuration Change Handling

```mermaid
flowchart TD
    A[Configuration change] --> B[Activity recreated]
    B --> C[SearchView.onSaveInstanceState called]
    C --> D[Save text and visibility]
    D --> E[State parcelled]
    
    F[New instance created] --> G[SearchView.onRestoreInstanceState called]
    G --> H[State unparcelled]
    H --> I[Restore text content]
    I --> J[Restore visibility]
    J --> K[UI updated]
```

This comprehensive documentation provides developers with a complete understanding of the search-view module's architecture, functionality, and integration patterns within the Material Design component system.