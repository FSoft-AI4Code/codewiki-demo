# Navigation View Core Module

## Overview

The navigation-view-core module provides the foundational components for implementing Material Design navigation drawers in Android applications. This module contains the core `NavigationView` component and its state management system, serving as the primary interface for creating navigation menus within drawer layouts.

## Purpose and Core Functionality

The navigation-view-core module enables developers to:
- Create navigation drawers with Material Design styling
- Manage navigation menu state and persistence
- Handle navigation item selection and user interactions
- Integrate with drawer layouts for slide-out navigation
- Support customizable theming and styling options

## Architecture

### Component Structure

```mermaid
graph TB
    subgraph "navigation-view-core"
        NV["NavigationView"]
        SS["SavedState"]
    end
    
    subgraph "Dependencies"
        NL["NavigationLayout"]
        NMP["NavigationMenuPresenter"]
        MSD["MaterialShapeDrawable"]
        MSCBH["MaterialSideContainerBackHelper"]
    end
    
    NV --> SS
    NV --> NL
    NV --> NMP
    NV --> MSD
    NV --> MSCBH
    
    style NV fill:#4285f4,stroke:#333,stroke-width:2px,color:#fff
    style SS fill:#34a853,stroke:#333,stroke-width:2px,color:#fff
```

### Core Components

#### NavigationView
The main component that represents a standard navigation menu for applications. It extends `ScrimInsetsFrameLayout` and implements `MaterialBackHandler` to provide:
- Menu population from resource files
- Header view support
- Item selection handling
- Material Design theming
- Drawer layout integration
- Back gesture support

#### SavedState
Handles the persistence of navigation view state across configuration changes and activity lifecycle events. It stores:
- Menu presenter states
- Checked item information
- User interaction states

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant NavigationView
    participant NavigationMenuPresenter
    participant Menu
    participant SavedState
    
    User->>NavigationView: Select item
    NavigationView->>NavigationMenuPresenter: Handle selection
    NavigationMenuPresenter->>Menu: Update checked state
    NavigationMenuPresenter->>NavigationView: Notify listener
    NavigationView->>User: Trigger callback
    
    Note over NavigationView,SavedState: Configuration change
    NavigationView->>SavedState: Save state
    SavedState-->>NavigationView: Restore state
    NavigationView->>NavigationMenuPresenter: Restore presenter states
```

## Component Interactions

```mermaid
graph LR
    subgraph "Navigation View System"
        NV["NavigationView"]
        NMP["NavigationMenuPresenter"]
        NM["NavigationMenu"]
        SS["SavedState"]
        MSCBH["MaterialSideContainerBackHelper"]
        DL["DrawerLayout"]
    end
    
    NV -->|"manages"| NMP
    NV -->|"contains"| NM
    NV -->|"saves/restores"| SS
    NV -->|"integrates with"| MSCBH
    NV -->|"placed in"| DL
    
    NMP -->|"presents"| NM
    NMP -->|"saves state to"| SS
    MSCBH -->|"handles back gestures"| DL
    
    style NV fill:#4285f4,stroke:#333,stroke-width:2px,color:#fff
    style NMP fill:#ea4335,stroke:#333,stroke-width:2px,color:#fff
    style SS fill:#34a853,stroke:#333,stroke-width:2px,color:#fff
```

## Key Features

### State Management
- **SavedState**: Preserves navigation menu state across configuration changes
- **Menu Persistence**: Maintains item selection and menu structure
- **Presenter State**: Saves and restores the internal state of menu presenters

### Material Design Integration
- **Theming Support**: Integrates with Material Design themes and color schemes
- **Shape Appearance**: Supports customizable shapes and corner radius
- **Elevation**: Proper elevation handling for Material Design surfaces
- **Ripple Effects**: Built-in support for Material Design ripple animations

### Drawer Layout Integration
- **Automatic Detection**: Detects when placed inside a DrawerLayout
- **Corner Shaping**: Automatically shapes exposed corners when in drawer
- **Back Gesture Support**: Handles predictive back gestures for drawer dismissal
- **Scrim Management**: Manages inset scrims for system bars

### Customization Options
- **Item Styling**: Customizable text appearance, colors, and backgrounds
- **Icon Support**: Tinting and sizing options for menu item icons
- **Padding Control**: Horizontal and vertical padding for menu items
- **Header Support**: Support for custom header views

## Process Flow

### Navigation Item Selection
```mermaid
flowchart TD
    A[User taps item] --> B{Item exists?}
    B -->|Yes| C[Update checked state]
    B -->|No| D[Ignore]
    C --> E[Notify presenter]
    E --> F[Update UI]
    F --> G[Call listener]
    G --> H[Return result]
```

### State Saving/Restoration
```mermaid
flowchart TD
    A[Configuration change] --> B[onSaveInstanceState called]
    B --> C[Create SavedState]
    C --> D[Save menu presenter states]
    D --> E[Store in Bundle]
    
    F[View recreated] --> G[onRestoreInstanceState called]
    G --> H[Retrieve SavedState]
    H --> I[Restore presenter states]
    I --> J[Update menu UI]
```

## Integration with Other Modules

### Related Modules
- **[navigation-bar-core](navigation-bar-core.md)**: Provides navigation bar components that complement navigation views
- **[drawer-utils](drawer-utils.md)**: Utility functions for drawer layout integration
- **[shape](shape.md)**: Material shape system for customizable backgrounds
- **[color](color.md)**: Color theming and harmonization support

### Dependencies
- **MaterialShapeDrawable**: For customizable backgrounds and shapes
- **MaterialSideContainerBackHelper**: For predictive back gesture support
- **NavigationMenuPresenter**: For menu presentation logic
- **ScrimInsetsFrameLayout**: For inset scrim management

## Usage Examples

### Basic Implementation
```xml
<androidx.drawerlayout.widget.DrawerLayout>
    <com.google.android.material.navigation.NavigationView
        android:id="@+id/navigation_view"
        android:layout_width="wrap_content"
        android:layout_height="match_parent"
        android:layout_gravity="start"
        app:menu="@menu/navigation_menu" />
</androidx.drawerlayout.widget.DrawerLayout>
```

### Programmatic Usage
```java
NavigationView navigationView = findViewById(R.id.navigation_view);
navigationView.setNavigationItemSelectedListener(item -> {
    // Handle navigation item selection
    return true;
});

// Customize appearance
navigationView.setItemIconTintList(iconTint);
navigationView.setItemTextColor(textColor);
navigationView.setItemBackground(itemBackground);
```

## Best Practices

1. **State Persistence**: Always test state restoration during configuration changes
2. **Performance**: Use appropriate item limits to avoid performance issues
3. **Accessibility**: Ensure proper content descriptions for navigation items
4. **Theming**: Leverage Material Design themes for consistent appearance
5. **Testing**: Test integration with DrawerLayout and back gesture handling

## API Reference

### Key Classes
- `NavigationView`: Main navigation view component
- `NavigationView.SavedState`: State persistence for navigation view
- `OnNavigationItemSelectedListener`: Interface for handling item selection

### Key Methods
- `setNavigationItemSelectedListener()`: Set item selection listener
- `inflateMenu()`: Inflate menu from resource
- `setCheckedItem()`: Set checked item programmatically
- `getMenu()`: Access the underlying menu

For detailed API documentation, refer to the official Material Design Components documentation.