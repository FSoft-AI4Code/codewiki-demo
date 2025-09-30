# Navigation Bar Core Module

## Overview

The navigation-bar-core module provides the foundational components for implementing Material Design navigation bars in Android applications. This module serves as the abstract base for both Bottom Navigation and Navigation Rail components, offering a unified API for navigation patterns that enable users to explore and switch between top-level views with a single tap.

## Purpose and Core Functionality

The navigation-bar-core module delivers essential functionality for:

- **State Management**: Preserving navigation state across configuration changes and application lifecycle events
- **Menu Integration**: Seamless integration with Android's menu system for dynamic content population
- **Visual Customization**: Comprehensive theming and styling capabilities for navigation items
- **Interaction Handling**: Event-driven architecture for item selection and reselection
- **Badge Support**: Built-in notification badge system for navigation items
- **Accessibility**: Full accessibility support with proper state management

## Architecture

### Core Components

The module is built around two primary components that work in tandem to provide navigation functionality:

#### NavigationBarView
The abstract base class that serves as the foundation for all navigation bar implementations. It provides:
- Menu integration and management
- Item selection and state handling
- Visual customization APIs
- Event listener management
- State persistence through SavedState

#### NavigationBarPresenter
The presentation layer that bridges the menu data model with the visual representation:
- Menu-to-view coordination
- State synchronization
- Badge management integration
- Update suspension for batch operations

### Component Relationships

```mermaid
graph TB
    subgraph "Navigation Bar Core Architecture"
        NBV[NavigationBarView<br/><i>Abstract Base Class</i>]
        NBP[NavigationBarPresenter<br/><i>Presentation Layer</i>]
        NBM[NavigationBarMenu<br/><i>Menu Model</i>]
        NBMV[NavigationBarMenuView<br/><i>Visual Representation</i>]
        
        NBV -->|manages| NBM
        NBV -->|creates| NBMV
        NBV -->|uses| NBP
        
        NBP -->|coordinates| NBM
        NBP -->|updates| NBMV
        NBM -->|provides data| NBP
        NBMV -->|displays| NBM
    end
    
    subgraph "State Management"
        NBVSS[NavigationBarView.SavedState<br/><i>View State</i>]
        NBPS[NavigationBarPresenter.SavedState<br/><i>Presenter State</i>]
        
        NBV -.->|saves/restores| NBVSS
        NBP -.->|saves/restores| NBPS
    end
    
    NBV -.-> NBVSS
    NBP -.-> NBPS
```

### Data Flow Architecture

```mermaid
sequenceDiagram
    participant App as Application
    participant NBV as NavigationBarView
    participant NBP as NavigationBarPresenter
    participant NBM as NavigationBarMenu
    participant NBMV as NavigationBarMenuView
    
    App->>NBV: inflateMenu(resId)
    NBV->>NBP: setUpdateSuspended(true)
    NBV->>MenuInflater: inflate(resId, menu)
    MenuInflater->>NBM: populate menu items
    NBV->>NBP: setUpdateSuspended(false)
    NBV->>NBP: updateMenuView(true)
    NBP->>NBMV: buildMenuView()
    NBMV->>NBMV: create item views
    
    App->>NBV: setSelectedItemId(id)
    NBV->>NBM: findItem(id)
    NBV->>NBM: performItemAction(item, presenter)
    NBM->>NBP: callback.onMenuItemSelected()
    NBP->>NBMV: setCheckedItem(item)
    NBMV->>NBMV: update visual state
```

## Key Features

### State Persistence
The module implements comprehensive state management through two SavedState classes:

- **NavigationBarView.SavedState**: Preserves the overall view state including menu presenter states
- **NavigationBarPresenter.SavedState**: Maintains selection state and badge information

### Visual Customization
Extensive customization options include:

- **Label Visibility Modes**: AUTO, SELECTED, LABELED, UNLABELED
- **Icon Gravity**: TOP (vertical) and START (horizontal) configurations
- **Item Gravity**: TOP_CENTER, CENTER, START_CENTER positioning
- **Active Indicators**: Customizable shape, color, size, and padding
- **Theming Support**: Text appearance, colors, ripples, and backgrounds

### Badge System Integration
Seamless integration with the badge module provides:
- Badge creation and management per menu item
- State persistence for badge data
- Visual coordination with navigation items

## Integration with Material Design System

### Dependencies
The navigation-bar-core module integrates with several Material Design components:

```mermaid
graph LR
    NBC[navigation-bar-core]
    Badge[badge]
    Shape[shape]
    Drawable[drawable-utils]
    Theme[theme-overlay]
    Resources[resources]
    
    NBC -->|uses| Badge
    NBC -->|uses| Shape
    NBC -->|uses| Drawable
    NBC -->|uses| Theme
    NBC -->|uses| Resources
```

### Related Modules
- **[bottomnavigation](bottomnavigation.md)**: Bottom navigation implementation
- **[navigation-view-core](navigation-view-core.md)**: Navigation drawer implementation
- **[badge](badge.md)**: Badge system for notifications

## Usage Patterns

### Basic Implementation
Navigation bar implementations extend NavigationBarView and provide concrete behavior:

```java
public class BottomNavigationView extends NavigationBarView {
    @Override
    protected NavigationBarMenuView createNavigationBarMenuView(Context context) {
        return new BottomNavigationMenuView(context);
    }
    
    @Override
    public int getMaxItemCount() {
        return 5; // Material Design recommends max 5 items
    }
}
```

### State Management
The SavedState pattern ensures consistent state across configuration changes:

```mermaid
stateDiagram-v2
    [*] --> Active
    Active --> Saving: onSaveInstanceState()
    Saving --> Restoring: Configuration Change
    Restoring --> Active: onRestoreInstanceState()
    
    state Saving {
        [*] --> SaveViewState
        SaveViewState --> SavePresenterState
        SavePresenterState --> [*]
    }
    
    state Restoring {
        [*] --> RestoreViewState
        RestoreViewState --> RestorePresenterState
        RestorePresenterState --> [*]
    }
```

## Process Flows

### Menu Inflation Process
```mermaid
flowchart TD
    Start([Menu Inflation Request])
    --> Suspend[Suspend Updates]
    --> Inflate[Inflate Menu Resource]
    --> Populate[Populate NavigationBarMenu]
    --> Resume[Resume Updates]
    --> Update[Update Menu View]
    --> Build[Build Menu Views]
    --> Render[Render Navigation Items]
    --> End([Inflation Complete])
```

### Item Selection Process
```mermaid
flowchart TD
    Start([User Taps Item])
    --> Find[Find Menu Item by ID]
    --> Check{Item Found?}
    -->|No| End([No Action])
    -->|Yes| Perform[Perform Item Action]
    --> Callback{Has Callback?}
    -->|No| Check2[Set Checked State]
    -->|Yes| Invoke[Invoke Callback]
    --> Response{Callback Response}
    -->|true| Check2
    -->|false| End
    Check2 --> Update[Update Visual State]
    --> End
```

## Best Practices

### Performance Considerations
- Use `setUpdateSuspended(true)` during batch operations
- Leverage state restoration for configuration changes
- Implement proper view recycling in custom menu views

### Accessibility
- Ensure proper content descriptions for navigation items
- Maintain focus management during item selection
- Support screen reader navigation patterns

### Theming
- Use Material theme attributes for consistent styling
- Leverage color state lists for dynamic theming
- Consider contrast ratios for accessibility compliance

## API Reference

### Key Classes
- `NavigationBarView`: Abstract base for navigation implementations
- `NavigationBarPresenter`: Presentation layer coordination
- `NavigationBarView.SavedState`: View state management
- `NavigationBarPresenter.SavedState`: Presenter state management

### Important Constants
- `LABEL_VISIBILITY_AUTO`: Automatic label visibility based on item count
- `LABEL_VISIBILITY_SELECTED`: Show labels only for selected items
- `LABEL_VISIBILITY_LABELED`: Always show labels
- `LABEL_VISIBILITY_UNLABELED`: Never show labels
- `ITEM_ICON_GRAVITY_TOP`: Vertical icon placement
- `ITEM_ICON_GRAVITY_START`: Horizontal icon placement

This documentation provides a comprehensive understanding of the navigation-bar-core module's architecture, functionality, and integration patterns within the Material Design system.