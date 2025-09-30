# SearchView Core Module Documentation

## Overview

The searchview-core module provides the core functionality for Material Design SearchView components, implementing a full-screen search interface that can be used in conjunction with SearchBar components. This module handles the complex animation system, state management, and user interaction patterns required for modern search experiences.

## Core Components

### SearchView.Behavior
A CoordinatorLayout.Behavior implementation that automatically sets up SearchView with SearchBar components when they are anchored together in a CoordinatorLayout. This behavior enables seamless integration between the search bar and search view without manual configuration.

### SearchView.SavedState
Handles state persistence for SearchView instances, preserving search text content and visibility state across configuration changes like screen rotations or activity recreation.

### SearchView.TransitionListener
Interface for monitoring SearchView transition states, allowing developers to respond to show/hide animations and state changes with custom logic.

## Architecture

```mermaid
graph TB
    subgraph "SearchView Core Architecture"
        SV[SearchView]
        SB[SearchBar]
        CL[CoordinatorLayout]
        
        subgraph "Core Components"
            B[Behavior]
            SS[SavedState]
            TL[TransitionListener]
        end
        
        subgraph "Animation System"
            SVAH[SearchViewAnimationHelper]
            MMBH[MaterialMainContainerBackHelper]
            MBO[MaterialBackOrchestrator]
        end
        
        subgraph "UI Components"
            ET[EditText]
            TB[Toolbar]
            CC[ContentContainer]
            SCR[Scrim]
        end
    end
    
    CL -->|"anchors"| SB
    CL -->|"anchors"| SV
    SB -->|"triggers"| SV
    B -->|"auto-setup"| SV
    SV -->|"uses"| SVAH
    SV -->|"implements"| MBO
    SVAH -->|"manages"| MMBH
    SV -->|"contains"| ET
    SV -->|"contains"| TB
    SV -->|"contains"| CC
    SV -->|"contains"| SCR
```

## Component Relationships

```mermaid
graph LR
    subgraph "Module Dependencies"
        SV[searchview-core]
        SB[searchbar-core]
        AS[animation-system]
        MT[Material Theme]
        CL[CoordinatorLayout]
    end
    
    SV -->|"depends on"| SB
    SV -->|"uses"| AS
    SV -->|"extends"| MT
    SV -->|"integrates with"| CL
    
    subgraph "External Dependencies"
        MSA[MaterialShapeUtils]
        MCO[MaterialColors]
        EOP[ElevationOverlayProvider]
        VU[ViewUtils]
    end
    
    SV -->|"uses"| MSA
    SV -->|"uses"| MCO
    SV -->|"uses"| EOP
    SV -->|"uses"| VU
```

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant SearchBar
    participant SearchView
    participant Behavior
    participant AnimationHelper
    
    User->>SearchBar: Click
    SearchBar->>SearchView: Trigger show()
    SearchView->>AnimationHelper: Start show animation
    AnimationHelper->>SearchView: Update transition state
    SearchView->>User: Display search interface
    
    User->>SearchView: Type search query
    SearchView->>SearchView: Update EditText
    SearchView->>SearchView: Show/hide clear button
    
    User->>SearchView: Press back
    SearchView->>AnimationHelper: Start hide animation
    AnimationHelper->>SearchView: Update transition state
    SearchView->>SearchBar: Collapse to search bar
```

## State Management

```mermaid
stateDiagram-v2
    [*] --> HIDDEN
    HIDDEN --> SHOWING: show()
    SHOWING --> SHOWN: Animation complete
    SHOWN --> HIDING: hide()
    HIDING --> HIDDEN: Animation complete
    
    SHOWN --> SHOWN: Configuration change
    HIDDEN --> HIDDEN: Configuration change
    
    note right of SHOWING : Loading animation
    note right of HIDING : Collapse animation
    note right of SHOWN : Full search interface
    note right of HIDDEN : Collapsed/minimized
```

## Process Flow

```mermaid
flowchart TD
    A[SearchView Initialization] --> B[Layout Inflation]
    B --> C[Component Setup]
    C --> D[Event Listener Configuration]
    D --> E[Inset Listener Setup]
    E --> F[Ready for Interaction]
    
    F --> G{User Action}
    G -->|Click SearchBar| H[Show Animation]
    G -->|Back Button| I[Hide Animation]
    G -->|Text Input| J[Update UI]
    
    H --> K[Transition State: SHOWING]
    K --> L[Transition State: SHOWN]
    
    I --> M[Transition State: HIDING]
    M --> N[Transition State: HIDDEN]
    
    J --> O[Update Clear Button]
    O --> P[Trigger Listeners]
```

## Key Features

### Animation System
The SearchView implements sophisticated animation capabilities through the SearchViewAnimationHelper, supporting:
- Expand/collapse animations
- Back gesture handling (Android 14+)
- Navigation icon morphing
- Menu item transitions
- Keyboard synchronization

### State Persistence
SavedState mechanism ensures:
- Search text preservation
- Visibility state maintenance
- Seamless configuration changes

### Accessibility
Comprehensive accessibility support including:
- Modal behavior for screen readers
- Keyboard navigation
- Focus management
- TalkBack compatibility

### CoordinatorLayout Integration
Automatic behavior setup when used with SearchBar in CoordinatorLayout, eliminating manual configuration requirements.

## Integration Patterns

### Basic Usage
```xml
<androidx.coordinatorlayout.widget.CoordinatorLayout>
    <com.google.android.material.appbar.AppBarLayout>
        <com.google.android.material.search.SearchBar android:id="@+id/search_bar" />
    </com.google.android.material.appbar.AppBarLayout>
    
    <com.google.android.material.search.SearchView
        app:layout_anchor="@id/search_bar">
        <!-- Search content -->
    </com.google.android.material.search.SearchView>
</androidx.coordinatorlayout.widget.CoordinatorLayout>
```

### Programmatic Control
```java
SearchView searchView = findViewById(R.id.search_view);
searchView.addTransitionListener(new SearchView.TransitionListener() {
    @Override
    public void onStateChanged(SearchView searchView, 
                             TransitionState previousState, 
                             TransitionState newState) {
        // Handle state changes
    }
});
```

## Related Documentation

- [SearchBar Core Documentation](searchbar-core.md) - Companion search bar component
- [Animation System Documentation](animation-system.md) - Animation framework details
- [Material Design Search Guidelines](https://material.io/components/search/overview) - Design principles and usage patterns

## Technical Considerations

### Performance
- Efficient state management prevents unnecessary redraws
- Animation system uses hardware acceleration when available
- Memory optimization through view recycling

### Compatibility
- Supports Android API 21+ (Lollipop)
- Back gesture handling for Android 14+ (API 34+)
- Graceful degradation on older platforms

### Customization
- Extensive theming support through MaterialThemeOverlay
- Custom header layouts
- Configurable animation behaviors
- Flexible content areas for search results