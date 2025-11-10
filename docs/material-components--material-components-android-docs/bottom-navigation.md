# Bottom Navigation Module Documentation

## Overview

The bottom-navigation module provides the BottomNavigationView component, a Material Design implementation of bottom navigation bars that enable users to explore and switch between top-level views in a single tap. This module is part of the Material Components for Android library and follows the Material Design guidelines for navigation patterns.

## Purpose and Core Functionality

The BottomNavigationView serves as a primary navigation component for applications with three to five top-level destinations. It provides:

- **Primary Navigation**: Easy access to top-level application sections
- **Visual Feedback**: Clear indication of the currently selected destination
- **Responsive Behavior**: Adaptive layout that works across different screen sizes
- **Scroll Integration**: Optional auto-hide behavior when scrolling
- **Accessibility**: Full support for accessibility features and screen readers

## Architecture and Component Relationships

### Core Components

The module consists of two main listener interfaces that handle user interaction:

1. **OnNavigationItemSelectedListener**: Handles selection events when users tap on navigation items
2. **OnNavigationItemReselectedListener**: Handles reselection events when users tap on the already selected item

### Component Hierarchy

```mermaid
graph TD
    A[BottomNavigationView] --> B[NavigationBarView]
    B --> C[NavigationBarMenuView]
    A --> D[BottomNavigationMenuView]
    A --> E[OnNavigationItemSelectedListener]
    A --> F[OnNavigationItemReselectedListener]
    A --> G[HideBottomViewOnScrollBehavior]
    
    style A fill:#1976d2,stroke:#333,stroke-width:2px,color:#fff
    style B fill:#2196f3,stroke:#333,stroke-width:2px,color:#fff
    style C fill:#64b5f6,stroke:#333,stroke-width:2px,color:#fff
    style D fill:#64b5f6,stroke:#333,stroke-width:2px,color:#fff
    style E fill:#81c784,stroke:#333,stroke-width:2px,color:#fff
    style F fill:#81c784,stroke:#333,stroke-width:2px,color:#fff
    style G fill:#ffb74d,stroke:#333,stroke-width:2px,color:#fff
```

### Dependencies

The BottomNavigationView extends NavigationBarView and integrates with several other Material Components:

```mermaid
graph LR
    A[bottom-navigation] --> B[navigation]
    A --> C[behavior]
    A --> D[internal]
    A --> E[theme]
    
    B --> F[NavigationBarView]
    B --> G[NavigationBarMenuView]
    C --> H[HideBottomViewOnScrollBehavior]
    D --> I[ThemeEnforcement]
    D --> J[ViewUtils]
    
    style A fill:#1976d2,stroke:#333,stroke-width:2px,color:#fff
    style B fill:#2196f3,stroke:#333,stroke-width:2px,color:#fff
    style C fill:#4caf50,stroke:#333,stroke-width:2px,color:#fff
    style D fill:#ff9800,stroke:#333,stroke-width:2px,color:#fff
    style E fill:#9c27b0,stroke:#333,stroke-width:2px,color:#fff
```

## Data Flow and Component Interaction

### Navigation Item Selection Flow

```mermaid
sequenceDiagram
    participant User
    participant BottomNavigationView
    participant OnNavigationItemSelectedListener
    participant NavigationBarMenuView
    participant App
    
    User->>BottomNavigationView: Tap navigation item
    BottomNavigationView->>NavigationBarMenuView: Update selection state
    NavigationBarMenuView->>BottomNavigationView: Return selection result
    BottomNavigationView->>OnNavigationItemSelectedListener: Notify selection event
    OnNavigationItemSelectedListener->>App: Handle navigation action
    App->>BottomNavigationView: Update UI/content
    
    Note over BottomNavigationView: Item selection is visually indicated
    Note over OnNavigationItemSelectedListener: Deprecated interface, use NavigationBarView.OnItemSelectedListener
```

### Scroll Behavior Integration

```mermaid
flowchart TD
    A[User Scrolls] --> B{CoordinatorLayout detects scroll}
    B --> C[HideBottomViewOnScrollBehavior]
    C --> D{Scroll direction?}
    D -->|Up| E[Hide BottomNavigationView]
    D -->|Down| F[Show BottomNavigationView]
    E --> G[Animate out with translation]
    F --> H[Animate in with translation]
    
    style A fill:#f5f5f5,stroke:#333,stroke-width:2px
    style B fill:#e3f2fd,stroke:#333,stroke-width:2px
    style C fill:#bbdefb,stroke:#333,stroke-width:2px
    style D fill:#e3f2fd,stroke:#333,stroke-width:2px
    style E fill:#ffcdd2,stroke:#333,stroke-width:2px
    style F fill:#c8e6c9,stroke:#333,stroke-width:2px
    style G fill:#ffeb3b,stroke:#333,stroke-width:2px
    style H fill:#4caf50,stroke:#333,stroke-width:2px
```

## Key Features and Configuration

### Item Management
- **Maximum Items**: Supports up to 6 navigation items (MAX_ITEM_COUNT = 6)
- **Horizontal Translation**: Configurable horizontal translation animation when items are selected
- **Menu Integration**: Uses standard Android menu resources for item definition

### Window Insets Handling
The component automatically handles system window insets:
- Applies bottom padding to avoid system navigation bar
- Handles RTL layout direction for proper start/end padding
- Integrates with edge-to-edge display modes

### Measurement and Layout
- Enforces minimum height requirements
- Supports both exact and at-most measurement modes
- Handles padding calculations automatically

## Process Flows

### Initialization Process

```mermaid
flowchart TD
    A[Constructor Called] --> B[Theme Context Resolution]
    B --> C[Attribute Parsing]
    C --> D[Horizontal Translation Setting]
    D --> E[Minimum Height Configuration]
    E --> F[Window Insets Application]
    F --> G[Component Ready]
    
    style A fill:#e1f5fe,stroke:#333,stroke-width:2px
    style B fill:#b3e5fc,stroke:#333,stroke-width:2px
    style C fill:#81d4fa,stroke:#333,stroke-width:2px
    style D fill:#4fc3f7,stroke:#333,stroke-width:2px
    style E fill:#29b6f6,stroke:#333,stroke-width:2px
    style F fill:#039be5,stroke:#333,stroke-width:2px
    style G fill:#0288d1,stroke:#333,stroke-width:2px
```

### Touch Event Handling

```mermaid
flowchart LR
    A[Touch Event Received] --> B[Call super.onTouchEvent]
    B --> C[Return true to consume event]
    C --> D[Prevent underlying views from receiving events]
    
    style A fill:#fff3e0,stroke:#333,stroke-width:2px
    style B fill:#ffe0b2,stroke:#333,stroke-width:2px
    style C fill:#ffcc02,stroke:#333,stroke-width:2px
    style D fill:#ffb74d,stroke:#333,stroke-width:2px
```

## Integration with Other Modules

### Navigation Module Integration
The bottom-navigation module extends the [navigation](navigation.md) module's NavigationBarView, inheriting:
- Menu management capabilities
- Item selection handling
- State persistence
- Accessibility features

### Behavior Module Integration
Integrates with [behavior](behavior.md) module for scroll-based hiding:
- HideBottomViewOnScrollBehavior for auto-hide functionality
- CoordinatorLayout integration for scroll detection
- Animation handling for show/hide transitions

### Theme Module Integration
Works with [theme](theme.md) module for:
- Material Design theming support
- Style attribute resolution
- Theme enforcement for consistent appearance

## Usage Guidelines

### When to Use
- Applications with 3-5 top-level destinations
- Primary navigation that should be always visible (except when scrolling)
- Mobile-first applications where thumb reachability is important

### When Not to Use
- Applications with more than 5 top-level destinations (consider [navigation-rail](navigation-rail.md) or drawer)
- Secondary navigation or deep navigation hierarchies
- Desktop or large tablet layouts where space is abundant

### Best Practices
- Keep labels short and meaningful
- Use recognizable icons
- Maintain consistent navigation structure
- Test with accessibility services
- Consider edge-to-edge layouts for modern Android versions

## API Reference

### Key Methods
- `setItemHorizontalTranslationEnabled(boolean)`: Controls horizontal translation animation
- `isItemHorizontalTranslationEnabled()`: Returns current translation setting
- `getMaxItemCount()`: Returns maximum supported items (6)
- `setOnNavigationItemSelectedListener()`: Sets selection listener (deprecated)
- `setOnNavigationItemReselectedListener()`: Sets reselection listener (deprecated)

### Deprecated APIs
The original listener interfaces are deprecated in favor of NavigationBarView's interfaces:
- Use `NavigationBarView.OnItemSelectedListener` instead of `OnNavigationItemSelectedListener`
- Use `NavigationBarView.OnItemReselectedListener` instead of `OnNavigationItemReselectedListener`

## Related Documentation

- [Navigation Module](navigation.md) - Base navigation functionality
- [Behavior Module](behavior.md) - Scroll behavior integration
- [Theme Module](theme.md) - Theming and styling support
- [Material Design Guidelines](https://m3.material.io/components/navigation-bar/overview) - Design specifications