# Command Palette Module Documentation

## Overview

The Command Palette module provides a powerful, keyboard-driven interface for accessing all application functionality in SumatraPDF. It serves as a unified search and command execution interface that allows users to quickly find and execute commands, switch between tabs, and access file history without navigating through traditional menus.

## Purpose and Core Functionality

The Command Palette module implements a modern command interface that:
- Provides fuzzy search across all available commands, open tabs, and file history
- Supports multiple search modes (commands, tabs, file history, or everything)
- Enables keyboard-only navigation and execution
- Offers smart tab switching with live preview
- Maintains context-aware command availability based on current document state

## Architecture

### Core Components

```mermaid
classDiagram
    class ItemDataCP {
        +i32 cmdId
        +WindowTab* tab
        +const char* filePath
    }
    
    class ListBoxModelCP {
        +StrVecCP strings
        +ItemsCount() int
        +Item(i int) const char*
        +Data(i int) ItemDataCP*
    }
    
    class CommandPaletteWnd {
        +HFONT font
        +MainWindow* win
        +Edit* editQuery
        +StrVecCP tabs
        +StrVecCP fileHistory
        +StrVecCP commands
        +ListBox* listBox
        +Static* staticInfo
        +currTabIdx int
        +smartTabMode bool
        +stickyMode bool
    }
    
    class CommandPaletteBuildCtx {
        +const char* filePath
        +isDocLoaded bool
        +supportsAnnots bool
        +hasSelection bool
        +isChm bool
        +canSendEmail bool
        +annotationUnderCursor Annotation*
        +hasUnsavedAnnotations bool
        +isCursorOnPage bool
        +cursorOnLinkTarget bool
        +cursorOnComment bool
        +cursorOnImage bool
        +hasToc bool
        +allowToggleMenuBar bool
        +canCloseOtherTabs bool
        +canCloseTabsToRight bool
        +canCloseTabsToLeft bool
    }
    
    ListBoxModelCP --|> ListBoxModel
    CommandPaletteWnd --|> Wnd
    ListBoxModelCP o-- ItemDataCP : contains
    CommandPaletteWnd o-- ListBoxModelCP : uses
    CommandPaletteWnd o-- CommandPaletteBuildCtx : uses
```

### Component Relationships

```mermaid
graph TD
    A[CommandPaletteWnd] --> B[ItemDataCP]
    A --> C[ListBoxModelCP]
    A --> D[CommandPaletteBuildCtx]
    A --> E[MainWindow]
    A --> F[Edit]
    A --> G[ListBox]
    A --> H[Static]
    
    C --> B
    D --> E
    
    I[Commands System] --> A
    J[Tab Management] --> A
    K[File History] --> A
    L[Document Context] --> D
```

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant CommandPaletteWnd
    participant CommandPaletteBuildCtx
    participant ListBoxModelCP
    participant MainWindow
    participant Commands
    
    User->>CommandPaletteWnd: Open Palette (Ctrl+K)
    CommandPaletteWnd->>MainWindow: Get current state
    CommandPaletteWnd->>CommandPaletteBuildCtx: Build context
    CommandPaletteWnd->>CommandPaletteWnd: CollectStrings()
    CommandPaletteWnd->>Commands: Filter available commands
    CommandPaletteWnd->>ListBoxModelCP: Populate model
    CommandPaletteWnd->>User: Display results
    
    User->>CommandPaletteWnd: Type search query
    CommandPaletteWnd->>ListBoxModelCP: FilterStringsForQuery()
    ListBoxModelCP->>CommandPaletteWnd: Return filtered results
    CommandPaletteWnd->>User: Update display
    
    User->>CommandPaletteWnd: Select item (Enter)
    CommandPaletteWnd->>ItemDataCP: Get selection data
    alt Command selected
        CommandPaletteWnd->>MainWindow: ExecuteCommand(cmdId)
    else Tab selected
        CommandPaletteWnd->>MainWindow: SelectTab(tab)
    else File selected
        CommandPaletteWnd->>MainWindow: LoadDocument(filePath)
    end
    CommandPaletteWnd->>CommandPaletteWnd: Close palette
```

## Command Filtering Logic

```mermaid
flowchart TD
    Start[Command ID] --> CheckDebug{Debug Command?}
    CheckDebug -->|Yes| DebugBuild{Debug Build?}
    CheckDebug -->|No| CheckBlacklist{Blacklisted?}
    
    DebugBuild -->|No| Reject1[Reject]
    DebugBuild -->|Yes| CheckBlacklist
    
    CheckBlacklist -->|Yes| Reject1
    CheckBlacklist -->|No| CheckDocLoaded{Document Loaded?}
    
    CheckDocLoaded -->|No| CheckWhitelist[In Whitelist?]
    CheckDocLoaded -->|Yes| CheckContext[Context Checks]
    
    CheckWhitelist -->|Yes| Accept[Accept]
    CheckWhitelist -->|No| Reject1
    
    CheckContext --> CheckSelection{Has Selection?}
    CheckContext --> CheckAnnots{Supports Annotations?}
    CheckContext --> CheckPerms{Has Permissions?}
    CheckContext --> CheckCursor{Cursor Context?}
    
    CheckSelection -->|Fail| Reject1
    CheckAnnots -->|Fail| Reject1
    CheckPerms -->|Fail| Reject1
    CheckCursor -->|Fail| Reject1
    
    CheckSelection -->|Pass| Accept
    CheckAnnots -->|Pass| Accept
    CheckPerms -->|Pass| Accept
    CheckCursor -->|Pass| Accept
```

## Search Modes

The Command Palette supports multiple search prefixes that determine which content to search:

```mermaid
graph LR
    Input[User Input] --> Prefix{Prefix Check}
    
    Prefix -->|"#"| FileHistory[File History Only]
    Prefix -->|">"| Commands[Commands Only]
    Prefix -->|"@"| Tabs[Open Tabs Only]
    Prefix -->|":"| Everything[Everything]
    Prefix -->|None| Default[Commands Default]
    
    FileHistory --> Filter[Apply Filter]
    Commands --> Filter
    Tabs --> Filter
    Everything --> Filter
    Default --> Filter
    
    Filter --> Results[Filtered Results]
```

## Smart Tab Mode

The Command Palette includes a special "smart tab" mode for quick tab switching:

```mermaid
stateDiagram-v2
    [*] --> NormalMode
    NormalMode --> SmartTabMode: Ctrl+Tab
    SmartTabMode --> Selecting: Navigate with Ctrl+Tab/Shift+Ctrl+Tab
    Selecting --> Selecting: Continue navigation
    Selecting --> Execute: Release Ctrl
    Selecting --> StickyMode: Press Space
    StickyMode --> Execute: Release Ctrl or Enter
    StickyMode --> NormalMode: Esc
    Execute --> [*]: Close Palette
    NormalMode --> [*]: Esc or Execute
```

## Integration with Other Modules

### Dependencies

- **[MainWindow](main_window.md)**: Provides current application state and tab management
- **[Commands](commands.md)**: Command definitions and execution system
- **[Settings](settings.md)**: Global preferences and file history
- **[Document Formats](document_formats.md)**: Document-specific capabilities
- **[UI Components](ui_components.md)**: Shared UI elements and theming

### Context-Aware Filtering

The Command Palette integrates deeply with the application's state to provide contextually relevant commands:

```mermaid
graph TD
    A[Document State] --> B[CommandPaletteBuildCtx]
    C[Tab State] --> B
    D[Selection State] --> B
    E[Permission State] --> B
    F[Engine Capabilities] --> B
    
    B --> G[AllowCommand Function]
    G --> H[Filtered Command List]
    H --> I[Command Palette Display]
```

## Key Features

### 1. Fuzzy Search
- Multi-word search with case-insensitive matching
- All words must match for a result to appear
- Real-time filtering as the user types

### 2. Context Awareness
- Commands are filtered based on current document type
- Annotation commands only appear for supported formats
- Selection-dependent commands require active selection
- Permission-based filtering for restricted operations

### 3. Multiple Content Types
- **Commands**: All available application commands
- **Tabs**: Currently open document tabs
- **File History**: Recently opened files
- **Everything**: Combined search across all types

### 4. Smart Navigation
- Keyboard-only operation
- Smart tab mode for quick tab switching
- Sticky mode for extended browsing
- Live preview in smart tab mode

## Performance Considerations

The Command Palette is designed for responsiveness:
- String collection happens once when opened
- Filtering is performed on pre-collected data
- UI updates are batched to prevent flicker
- Memory is managed efficiently with temporary string allocations

## Extensibility

The module supports custom commands through the [Commands](commands.md) system:
- External viewer commands are dynamically added
- Selection handlers appear contextually
- Keyboard shortcuts are included in search results
- Custom commands can be filtered by file type

## Error Handling

The Command Palette includes robust error handling:
- Invalid commands are logged and skipped
- Missing files in history are gracefully handled
- UI state is preserved during filtering operations
- Safe cleanup on unexpected closure

This design ensures the Command Palette remains a reliable and efficient interface for accessing all application functionality while maintaining responsiveness and contextual relevance.