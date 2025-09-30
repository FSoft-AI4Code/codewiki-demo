# Material Design Checkbox Module

## Overview

The checkbox module provides a Material Design implementation of checkbox components, offering enhanced functionality beyond standard Android checkboxes. It supports three distinct states (unchecked, checked, and indeterminate), error state handling, and comprehensive theming capabilities that align with Material Design principles.

## Core Components

### MaterialCheckBox

The primary component `MaterialCheckBox` extends `AppCompatCheckBox` to provide Material Design styling and additional features. Key capabilities include:

- **Three-state support**: Unchecked, checked, and indeterminate states
- **Error state handling**: Visual error indication with accessibility support
- **Custom theming**: Material theme color integration
- **Animation support**: Smooth transitions between states
- **Accessibility**: Enhanced screen reader support with state descriptions

### SavedState

The `SavedState` class handles state persistence during configuration changes, ensuring that checkbox states (including indeterminate state) are properly maintained.

## Architecture

```mermaid
graph TB
    subgraph "Checkbox Module"
        MC[MaterialCheckBox]
        SS[SavedState]
        OCCL[OnCheckedChangeListener]
        OCSC[OnCheckedStateChangedListener]
        OEC[OnErrorChangedListener]
    end
    
    subgraph "Android Framework"
        ACC[AppCompatCheckBox]
        CB[CompoundButton]
        TCB[TintableCompoundButton]
    end
    
    subgraph "Material Dependencies"
        MCOL[MaterialColors]
        DU[DrawableUtils]
        TE[ThemeEnforcement]
        VU[ViewUtils]
    end
    
    MC -->|extends| ACC
    ACC -->|extends| CB
    MC -->|implements| TCB
    
    MC -->|uses| MCOL
    MC -->|uses| DU
    MC -->|uses| TE
    MC -->|uses| VU
    
    SS -->|extends| BaseSavedState
    MC -->|contains| SS
    
    OCCL -.->|callback| MC
    OCSC -.->|callback| MC
    OEC -.->|callback| MC
```

## State Management

The checkbox supports three distinct states with corresponding visual representations:

```mermaid
stateDiagram-v2
    [*] --> Unchecked: Initial state
    Unchecked --> Checked: User interaction
    Checked --> Unchecked: User interaction
    Unchecked --> Indeterminate: Programmatic
    Checked --> Indeterminate: Programmatic
    Indeterminate --> Unchecked: Programmatic
    Indeterminate --> Checked: Programmatic
    
    state Indeterminate {
        [*] --> VisualIndication
        VisualIndotation: Dash mark
        VisualIndotation: Intermediate state
    }
    
    state Error {
        [*] --> VisualError
        VisualError: Red color scheme
        VisualError: Error accessibility label
    }
```

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant MaterialCheckBox
    participant StateManager
    participant DrawableSystem
    participant Listeners
    
    User->>MaterialCheckBox: Click/Touch
    MaterialCheckBox->>StateManager: setCheckedState()
    StateManager->>StateManager: Validate state transition
    StateManager->>MaterialCheckBox: Update internal state
    MaterialCheckBox->>DrawableSystem: refreshDrawableState()
    DrawableSystem->>DrawableSystem: Apply visual changes
    MaterialCheckBox->>Listeners: Notify state change
    
    alt Error state change
        MaterialCheckBox->>MaterialCheckBox: setErrorShown()
        MaterialCheckBox->>DrawableSystem: refreshDrawableState()
        MaterialCheckBox->>Listeners: Notify error change
    end
```

## Component Interactions

```mermaid
graph LR
    subgraph "Checkbox Component"
        MC[MaterialCheckBox]
        BD[Button Drawable]
        BID[Button Icon Drawable]
        BTL[Button Tint List]
        BITL[Button Icon Tint List]
    end
    
    subgraph "State Management"
        CS[Current State]
        ES[Error State]
        CSD[Custom State Description]
    end
    
    subgraph "Event System"
        OCCL[OnCheckedChangeListener]
        OCSC[OnCheckedStateChangedListener]
        OEC[OnErrorChangedListener]
    end
    
    MC -->|controls| BD
    MC -->|controls| BID
    MC -->|applies| BTL
    MC -->|applies| BITL
    
    MC -->|manages| CS
    MC -->|manages| ES
    MC -->|manages| CSD
    
    MC -->|notifies| OCCL
    MC -->|notifies| OCSC
    MC -->|notifies| OEC
```

## Theming and Styling

The checkbox module integrates with Material Design theming system:

```mermaid
graph TD
    subgraph "Material Theme"
        CA[colorControlActivated]
        CE[colorError]
        CS[colorSurface]
        COS[colorOnSurface]
    end
    
    subgraph "Checkbox States"
        S1[Enabled + Error]
        S2[Enabled + Checked]
        S3[Enabled + Unchecked]
        S4[Disabled + Checked]
        S5[Disabled + Unchecked]
    end
    
    subgraph "Color Application"
        CSL[ColorStateList]
        MTCL[MaterialThemeColorsTintList]
    end
    
    CA -->|layered| MTCL
    CE -->|layered| MTCL
    CS -->|layered| MTCL
    COS -->|layered| MTCL
    
    MTCL -->|applied to| CSL
    CSL -->|tints| S1
    CSL -->|tints| S2
    CSL -->|tints| S3
    CSL -->|tints| S4
    CSL -->|tints| S5
```

## Process Flow

### Initialization Process

```mermaid
flowchart TD
    Start([MaterialCheckBox Creation])
    --> ContextWrap[Wrap Context with Material Theme]
    --> AttrObtain[Obtain Styled Attributes]
    --> DrawableInit[Initialize Button Drawable]
    --> IconInit[Initialize Button Icon]
    --> TintInit[Initialize Tint Lists]
    --> StateInit[Initialize State]
    --> ErrorInit[Initialize Error State]
    --> Refresh[Refresh Button Drawable]
    --> End([Ready for Interaction])
    
    ContextWrap -->|uses| ThemeOverlay
    AttrObtain -->|uses| ThemeEnforcement
    DrawableInit -->|checks| Material3Theme
    IconInit -->|conditionally| SetDefaultIcon
    TintInit -->|uses| MaterialResources
    StateInit -->|sets| CheckedState
    ErrorInit -->|configures| ErrorAccessibility
```

### State Change Process

```mermaid
flowchart TD
    Start([State Change Request])
    --> Validate[Validate New State]
    --> UpdateInternal[Update Internal State]
    --> RefreshDrawable[Refresh Drawable State]
    --> UpdateDescription[Update State Description]
    --> NotifyListeners[Notify All Listeners]
    --> AutofillNotify[Notify Autofill Manager]
    --> End([State Change Complete])
    
    Validate -->|if invalid| Reject[Reject Change]
    Validate -->|if valid| Continue[Continue Process]
    
    RefreshDrawable -->|triggers| VisualUpdate[Visual Update]
    UpdateDescription -->|for accessibility| ScreenReader[Screen Reader Support]
    NotifyListeners -->|broadcasts| StateChangeEvent[State Change Event]
    NotifyListeners -->|broadcasts| ErrorChangeEvent[Error Change Event]
```

## Key Features

### Three-State Support
- **Unchecked**: Default state with empty checkbox
- **Checked**: Filled checkbox with checkmark icon
- **Indeterminate**: Dash mark indicating partial selection

### Error State Management
- Visual error indication through color changes
- Accessibility support with error labels
- Independent error state management

### Theming Integration
- Material Design color system integration
- Automatic color scheme application
- Custom tint list support

### Animation Support
- Smooth transitions between checked/unchecked states
- AnimatedVectorDrawable integration
- Color transition animations (API 24+)

### Accessibility Features
- Enhanced state descriptions for screen readers
- Error state announcements
- Autofill manager integration

## Dependencies

The checkbox module relies on several Material Design components:

- **[Material Colors](color.md)**: For theme color integration
- **[Drawable Utilities](drawable.md)**: For drawable manipulation and tinting
- **[Theme Enforcement](theme.md)**: For consistent theming application
- **[View Utilities](view.md)**: For layout and RTL support

## Usage Considerations

### Performance
- Drawable state caching for optimal performance
- Efficient state change notifications
- Minimal redraw operations

### Customization
- Support for custom button drawables
- Independent icon and button tinting
- Custom state description support

### Compatibility
- Backward compatibility with AppCompatCheckBox
- Material 3 theme detection and adaptation
- API level specific feature handling

## Integration Points

The checkbox module integrates with the broader Material Design system through:

- **Theme system**: Color and style inheritance
- **Drawable system**: Custom drawable support and tinting
- **Accessibility system**: Enhanced accessibility features
- **Animation system**: Smooth state transitions
- **State management system**: Comprehensive state handling

This modular approach ensures consistent behavior across the Material Design component library while providing flexibility for customization and extension.