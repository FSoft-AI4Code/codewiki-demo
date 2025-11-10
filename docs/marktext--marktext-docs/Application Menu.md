# Application Menu Module

## Introduction

The Application Menu module is a core component of the main process services layer, responsible for managing the application's menu system across all windows. It provides dynamic menu creation, window-specific menu management, and real-time menu updates based on application state changes. The module handles recently used documents, menu state synchronization, and cross-platform menu behavior differences.

## Architecture Overview

The Application Menu module serves as the central hub for menu management in the Electron application, integrating with multiple system components to provide a cohesive user interface experience.

```mermaid
graph TB
    subgraph "Application Menu Module"
        AM[AppMenu]
        AM --> MM[Menu Management]
        AM --> RUD[Recently Used Documents]
        AM --> MS[Menu State]
        AM --> MU[Menu Updates]
    end
    
    subgraph "External Dependencies"
        P[Preference]
        K[Keybindings]
        WM[WindowManager]
        CM[CommandManager]
        DC[DataCenter]
    end
    
    AM -.-> P
    AM -.-> K
    AM <--> WM
    AM <---> CM
    AM -.-> DC
    
    subgraph "Platform Integration"
        EL[Electron]
        OS[OS Integration]
    end
    
    AM --> EL
    AM --> OS
```

## Core Components

### AppMenu Class

The `AppMenu` class is the primary component that orchestrates all menu-related functionality. It manages window-specific menus, handles recently used documents, and coordinates menu updates across the application.

**Key Responsibilities:**
- Window-specific menu creation and management
- Recently used documents tracking and storage
- Dynamic menu updates based on application state
- Cross-platform menu behavior handling
- Menu state synchronization across windows

**Constructor Parameters:**
- `preferences`: Preference instance for accessing user settings
- `keybindings`: Keybindings instance for keyboard shortcut management
- `userDataPath`: Path to user data directory for storing recent documents

## Component Relationships

### Internal Architecture

```mermaid
graph LR
    subgraph "AppMenu Internal Structure"
        AM[AppMenu] --> WM[windowMenus Map]
        AM --> RUD[Recently Used Documents]
        AM --> MT[Menu Types]
        AM --> IPC[IPC Listeners]
        
        WM --> WM1[Window 1 Menu]
        WM --> WM2[Window 2 Menu]
        WM --> WMn[Window N Menu]
        
        MT --> MT1[DEFAULT]
        MT --> MT2[EDITOR]
        MT --> MT3[SETTINGS]
    end
```

### External Dependencies

```mermaid
graph TB
    AM[AppMenu] --> P[Preference Module]
    AM --> K[Keybindings Module]
    AM --> EL[Electron Main Process]
    AM --> FS[File System]
    
    P --> PT[Theme Settings]
    P --> PAS[AutoSave Settings]
    
    K --> KH[Key Handler Registration]
    K --> AC[Accelerator Management]
    
    EL --> EM[Electron Menu]
    EL --> EIPC[Electron IPC]
    EL --> EAD[Electron App Dock]
    
    FS --> RUF[Recent Documents File]
    FS --> UD[User Data Directory]
```

## Data Flow

### Menu Creation Flow

```mermaid
sequenceDiagram
    participant WM as WindowManager
    participant AM as AppMenu
    participant KB as Keybindings
    participant P as Preference
    participant EM as Electron Menu
    
    WM->>AM: createWindow(windowType)
    AM->>KB: getKeybindings()
    AM->>P: getPreferences()
    AM->>AM: buildMenuTemplate()
    AM->>EM: Menu.buildFromTemplate()
    AM->>AM: storeWindowMenu()
    AM->>EM: Menu.setApplicationMenu()
```

### Recently Used Documents Flow

```mermaid
sequenceDiagram
    participant ED as Editor
    participant IPC as IPC Main
    participant AM as AppMenu
    participant FS as File System
    participant OS as OS Integration
    
    ED->>IPC: fileOpened(filePath)
    IPC->>AM: addRecentlyUsedDocument()
    AM->>AM: validateFilePath()
    AM->>FS: readRecentDocuments()
    AM->>AM: updateRecentList()
    AM->>FS: writeRecentDocuments()
    AM->>OS: addRecentDocument() [macOS/Windows]
    AM->>AM: updateAllMenus()
```

## Menu Types and Templates

### Menu Type Classification

The module supports three distinct menu types, each serving specific application contexts:

```mermaid
graph TD
    subgraph "Menu Types"
        MT[MenuType Enum] --> D[DEFAULT]
        MT --> E[EDITOR]
        MT --> S[SETTINGS]
    end
    
    subgraph "Use Cases"
        D --> DF[Fallback Menu]
        E --> EM[Editor Window]
        S --> SM[Settings Window]
    end
    
    subgraph "Features"
        EM --> EF[Full Feature Set]
        EM --> ER[Recent Documents]
        EM --> EMU[Mode Switching]
        SM --> SS[Minimal Set]
        SS --> SM[macOS Only]
    end
```

### Dynamic Menu Updates

The module implements real-time menu updates based on application state changes:

```mermaid
graph LR
    subgraph "Update Triggers"
        UT[Update Triggers] --> UC[Content Changes]
        UT --> UV[View Changes]
        UT --> UP[Preference Changes]
        UT --> US[Selection Changes]
    end
    
    subgraph "Update Types"
        UC --> UF[Format Menu]
        UV --> UVL[View Layout]
        UP --> UT[Theme]
        UP --> UAS[AutoSave]
        US --> USM[Selection Menus]
    end
    
    subgraph "Update Process"
        UF --> UR[Rebuild Menu]
        UVL --> UR
        UT --> UM[Modify Items]
        UAS --> UM
        USM --> UR
    end
```

## Cross-Platform Considerations

### Platform-Specific Behavior

```mermaid
graph TB
    subgraph "Platform Detection"
        PD[Platform Detection] --> PL[isLinux]
        PD --> PO[isOsx]
        PD --> PW[isWindows]
    end
    
    subgraph "macOS Specific"
        PO --> POA[App Dock Integration]
        PO --> POS[Settings Menu Only]
        PO --> POP[Recent Documents]
    end
    
    subgraph "Windows Specific"
        PW --> PWA[Alt+F4 Handling]
        PW --> PWP[Recent Documents]
    end
    
    subgraph "Linux Specific"
        PL --> PLL[Menu Visibility Workaround]
        PL --> PLD[Dummy Menu Fallback]
    end
```

## IPC Communication

### IPC Event Handling

The module listens for various IPC events to maintain menu state synchronization:

```mermaid
graph TD
    subgraph "IPC Events"
        IE[IPC Events] --> IAD[Add Document]
        IE --> IUL[Update Line Ending]
        IE --> IUF[Update Format]
        IE --> IUS[Update Sidebar]
        IE --> IUV[Update View]
        IE --> IUE[Update Editor Selection]
        IE --> IBC[Broadcast Preferences]
    end
    
    subgraph "Event Sources"
        IAD --> ES[Editor Window]
        IUL --> ES
        IUF --> ES
        IUS --> ES
        IUV --> ES
        IUE --> ES
        IBC --> PS[Preference System]
    end
    
    subgraph "Event Handlers"
        IAD --> HAD[addRecentlyUsedDocument]
        IUL --> HUL[updateLineEndingMenu]
        IUF --> HUF[updateFormatMenu]
        IUS --> HUS[updateSidebarMenu]
        IUV --> HUV[viewLayoutChanged]
        IUE --> HUE[updateSelectionMenus]
        IBC --> HBC[updateTheme/AutoSave]
    end
```

## Integration with Other Modules

### Window Management Integration

The Application Menu module works closely with the [Window Management](Window%20Management.md) module to provide window-specific menu instances:

- **Window Creation**: Creates appropriate menu when new windows are opened
- **Window Focus**: Switches application menu when window focus changes
- **Window Closure**: Removes menu references when windows are closed

### Command Management Integration

Menu items are linked to the [Command Management](Command%20Management.md) system:

- **Command Binding**: Menu items trigger registered commands
- **State Synchronization**: Menu state reflects command availability
- **Keyboard Shortcuts**: Menu accelerators managed by keybindings system

### Preference System Integration

The module integrates with the [User Preferences](User%20Preferences.md) system for:

- **Theme Management**: Updates theme menu items based on current theme
- **AutoSave Settings**: Reflects autosave state in menu
- **User Customization**: Adapts menu structure based on preferences

## File System Operations

### Recently Used Documents Storage

```mermaid
graph LR
    subgraph "Storage Process"
        SP[Storage Process] --> VF[Validate File]
        SP --> LR[Load Recent]
        SP --> UR[Update Recent]
        SP --> WR[Write File]
    end
    
    subgraph "File Operations"
        VF --> IF[isFile2/isDirectory2]
        LR --> JR[JSON Read]
        UR --> US[Update Array]
        WR --> JW[JSON Write]
    end
    
    subgraph "Storage Location"
        SL[Storage Location] --> UDP[User Data Path]
        UDP --> RUF[recently-used-documents.json]
        RUF --> ML[MAX_RECENTLY_USED_DOCUMENTS = 12]
    end
```

## Error Handling

### Error Scenarios

The module implements robust error handling for various scenarios:

- **File System Errors**: Handles corrupted recent documents files
- **Missing Windows**: Gracefully handles requests for non-existent window menus
- **Menu Rebuild Failures**: Maintains menu consistency during updates
- **Platform Differences**: Adapts behavior based on platform capabilities

## Performance Considerations

### Optimization Strategies

- **Menu Caching**: Maintains window-specific menu instances to avoid recreation
- **Selective Updates**: Only updates affected menu items when possible
- **Lazy Loading**: Defers menu creation until window initialization
- **Batch Operations**: Groups menu updates to minimize UI flicker

## Security Considerations

### File Path Validation

- **Path Validation**: Validates file paths before adding to recent documents
- **File System Checks**: Verifies file existence before menu updates
- **User Data Protection**: Stores recent documents in user data directory

## Testing Considerations

### Test Scenarios

- **Menu Creation**: Verify correct menu type for different window types
- **Recent Documents**: Test addition, removal, and clearing of recent items
- **State Updates**: Validate menu state changes based on application events
- **Platform Behavior**: Ensure correct behavior across different platforms
- **IPC Communication**: Test all IPC event handlers and responses

## Future Enhancements

### Potential Improvements

- **Menu Customization**: Allow users to customize menu structure
- **Plugin Integration**: Support for menu items added by plugins
- **Accessibility**: Enhanced accessibility features for menu navigation
- **Performance**: Further optimization of menu rebuild operations
- **Internationalization**: Support for localized menu labels and shortcuts