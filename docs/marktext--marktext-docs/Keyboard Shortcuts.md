# Keyboard Shortcuts Module

## Introduction

The Keyboard Shortcuts module is a core component of the application's main process services, responsible for managing keyboard shortcuts and keybindings throughout the application. It provides a flexible system for handling user-defined shortcuts, platform-specific keybindings, and dynamic keyboard layout adaptation.

## Overview

The module serves as the central hub for keyboard input management, offering:
- Platform-specific default keybindings (Windows, macOS, Linux)
- User-customizable keybinding configuration
- Dynamic keyboard layout detection and adaptation
- Integration with the command system for executing actions
- Conflict resolution for duplicate shortcuts

## Architecture

### Core Components

```mermaid
graph TB
    subgraph "Keyboard Shortcuts Module"
        KB[Keybindings<br/>src.main.keyboard.shortcutHandler.Keybindings]
        KD[keybindingsDarwin]
        KL[keybindingsLinux]
        KW[keybindingsWindows]
        CM[CommandManager]
        AE[AppEnvironment]
    end
    
    subgraph "External Dependencies"
        ELS[electron-localshortcut]
        KLM[keyboardLayoutMonitor]
        KI[getKeyboardInfo]
        FS[File System]
    end
    
    KB --> KD
    KB --> KL
    KB --> KW
    KB --> CM
    KB --> AE
    KB --> ELS
    KB --> KLM
    KB --> KI
    KB --> FS
```

### Module Dependencies

```mermaid
graph LR
    subgraph "Main Process Services"
        KS[Keyboard Shortcuts]
        CM[Command Management]
        UP[User Preferences]
    end
    
    subgraph "Application Core"
        AE[App Environment]
        WM[Window Manager]
    end
    
    KS --> CM
    KS --> AE
    CM --> WM
```

## Key Features

### 1. Platform-Specific Keybindings

The module automatically selects appropriate default keybindings based on the operating system:

- **macOS**: Uses `keybindingsDarwin` configuration
- **Linux**: Uses `keybindingsLinux` configuration  
- **Windows**: Uses `keybindingsWindows` configuration

### 2. User Customization

Users can customize keybindings through a `keybindings.json` file stored in the application's user data directory. The system supports:

- Overriding default shortcuts
- Disabling shortcuts (setting to empty string)
- Custom accelerator definitions

### 3. Keyboard Layout Adaptation

The module dynamically adapts to different keyboard layouts:

```mermaid
sequenceDiagram
    participant App as Application
    participant KB as Keybindings
    participant KLM as KeyboardLayoutMonitor
    participant ELS as electron-localshortcut
    
    App->>KB: Initialize Keybindings
    KB->>KLM: Register layout change listener
    KLM-->>KB: Layout change notification
    KB->>ELS: Update keyboard layout
    Note over KB,ELS: Prevents issues with non-US keyboards
```

### 4. Conflict Resolution

The system implements sophisticated conflict resolution:

1. **Duplicate Detection**: Identifies duplicate accelerators in user configuration
2. **Default Override**: User shortcuts take precedence over defaults
3. **Automatic Unbinding**: Conflicting default shortcuts are automatically disabled

## Data Flow

### Keybinding Registration Process

```mermaid
flowchart TD
    Start[Window Created] --> LoadDefaults[Load Platform Defaults]
    LoadDefaults --> LoadUser[Load User Keybindings]
    LoadUser --> Validate[Validate Accelerators]
    Validate --> ResolveConflicts[Resolve Conflicts]
    ResolveConflicts --> Register[Register with electron-localshortcut]
    Register --> End[Ready for Input]
    
    Validate -->|Invalid| Error[Log Error & Skip]
    ResolveConflicts -->|Duplicate| DisableDefault[Disable Default]
```

### Shortcut Execution Flow

```mermaid
sequenceDiagram
    participant User as User
    participant Win as BrowserWindow
    participant ELS as electron-localshortcut
    participant KB as Keybindings
    participant CM as CommandManager
    
    User->>Win: Press keyboard shortcut
    Win->>ELS: Key event intercepted
    ELS->>KB: Call registered callback
    KB->>CM: Execute command by ID
    CM->>Win: Perform action on window
    KB-->>ELS: Return true (prevent default)
```

## Configuration Management

### User Configuration File

The user keybindings are stored in `keybindings.json`:

```json
{
  "file.save": "CmdOrCtrl+S",
  "file.save-as": "CmdOrCtrl+Shift+S",
  "file.new": "CmdOrCtrl+N"
}
```

### Configuration Loading Process

```mermaid
flowchart LR
    ConfigFile[keybindings.json] --> Parse[Parse JSON]
    Parse --> Validate[Validate Format]
    Validate --> CheckCommands[Check Command Existence]
    CheckCommands --> Resolve[Resolve Conflicts]
    Resolve --> Apply[Apply to Key Map]
    
    Parse -->|Invalid| ErrorLog[Log Error]
    Validate -->|Invalid| Skip[Skip User Config]
```

## Integration Points

### Command Manager Integration

The module integrates closely with the [Command Management](Command Management.md) system:

- **Command Execution**: Shortcuts trigger commands through `CommandManager.execute(id, win)`
- **Validation**: Ensures all keybound commands exist in development mode
- **Dynamic Registration**: Registers shortcuts for each editor window

### Window Manager Integration

Works with the [Window Management](Window Management.md) system to:

- Register shortcuts per window instance
- Handle window-specific key events
- Support multiple editor windows simultaneously

## Error Handling

The module implements comprehensive error handling:

1. **Invalid Accelerators**: Logs warnings for malformed accelerator strings
2. **Missing Commands**: In development mode, alerts about non-existent commands
3. **File System Errors**: Gracefully handles missing or corrupted configuration files
4. **Duplicate Shortcuts**: Prevents registration and logs conflicts

## Security Considerations

- **Safe Mode**: Disables user keybindings in safe mode
- **Validation**: Validates all accelerator strings before registration
- **File Access**: Uses proper file system operations with error handling

## Performance Optimizations

- **Lazy Loading**: User keybindings loaded only when needed
- **Map-based Storage**: Uses Maps for O(1) key lookup performance
- **Event-driven Updates**: Only updates keyboard layout when actually changed

## Development Features

### Debug Mode

When `MARKTEXT_DEBUG` and `MARKTEXT_DEBUG_KEYBOARD` are enabled:

- Logs keyboard layout changes
- Provides detailed debugging information
- Helps troubleshoot keyboard-related issues

### Development Validation

In development mode, the system:

- Validates all default keybindings against available commands
- Logs missing commands for accelerator assignments
- Helps ensure all shortcuts have valid targets

## API Reference

### Key Methods

- `getAccelerator(id)`: Retrieve accelerator for a command ID
- `registerAccelerator(win, accelerator, callback)`: Register a shortcut
- `registerEditorKeyHandlers(win)`: Register all shortcuts for a window
- `setUserKeybindings(userKeybindings)`: Update user keybindings
- `openConfigInFileManager()`: Open user configuration file

### Configuration Files

- **Platform Defaults**: `keybindingsDarwin.js`, `keybindingsLinux.js`, `keybindingsWindows.js`
- **User Configuration**: `keybindings.json` in user data directory

## Related Modules

- [Command Management](Command Management.md) - Executes commands triggered by shortcuts
- [User Preferences](User Preferences.md) - Manages user settings and preferences
- [Window Management](Window Management.md) - Handles window lifecycle and events
- [Application Core](Application Core.md) - Provides application environment and paths