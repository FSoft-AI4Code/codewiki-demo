# CDP Page Module

## Overview

The CDP Page module provides the Chrome DevTools Protocol (CDP) implementation of the Page API in Puppeteer. The `CdpPage` class serves as the primary interface for interacting with web pages through the CDP, offering comprehensive page manipulation, navigation, and monitoring capabilities.

This module acts as a concrete implementation of the abstract `Page` class from the [core_api](core_api.md) module, specifically designed to work with Chrome/Chromium browsers through the CDP protocol.

## Architecture

```mermaid
graph TB
    subgraph "CDP Page Architecture"
        CdpPage["CdpPage"]
        
        subgraph "Core Components"
            FrameManager["FrameManager"]
            EmulationManager["EmulationManager"]
            NetworkManager["NetworkManager"]
            Coverage["Coverage"]
            Tracing["Tracing"]
        end
        
        subgraph "Input Devices"
            CdpKeyboard["CdpKeyboard"]
            CdpMouse["CdpMouse"]
            CdpTouchscreen["CdpTouchscreen"]
        end
        
        subgraph "CDP Infrastructure"
            CdpCDPSession["CdpCDPSession"]
            CdpTarget["CdpTarget"]
            Connection["Connection"]
        end
        
        subgraph "Page Features"
            FileChooser["FileChooser"]
            CdpDialog["CdpDialog"]
            CdpWebWorker["CdpWebWorker"]
            Binding["Binding"]
        end
    end
    
    CdpPage --> FrameManager
    CdpPage --> EmulationManager
    CdpPage --> NetworkManager
    CdpPage --> Coverage
    CdpPage --> Tracing
    CdpPage --> CdpKeyboard
    CdpPage --> CdpMouse
    CdpPage --> CdpTouchscreen
    CdpPage --> CdpCDPSession
    CdpPage --> CdpTarget
    CdpPage --> FileChooser
    CdpPage --> CdpDialog
    CdpPage --> CdpWebWorker
    CdpPage --> Binding
    
    FrameManager --> NetworkManager
    CdpCDPSession --> Connection
    CdpTarget --> CdpCDPSession
```

## Core Components

### CdpPage Class

The main class that implements the CDP-specific page functionality:

```typescript
export class CdpPage extends Page {
  static async _create(
    client: CdpCDPSession,
    target: CdpTarget,
    defaultViewport: Viewport | null,
  ): Promise<CdpPage>
}
```

**Key Responsibilities:**
- Page lifecycle management (creation, navigation, closing)
- Event handling and emission
- Resource management (frames, workers, sessions)
- Input device coordination
- Network and emulation management

## Dependencies

```mermaid
graph LR
    subgraph "External Dependencies"
        CoreAPI["core_api"]
        CDPImplementation["cdp_implementation"]
        NetworkHandling["network_handling"]
        InputInteraction["input_and_interaction"]
    end
    
    subgraph "Internal Dependencies"
        CDPBrowser["cdp_browser"]
        CDPBrowserContext["cdp_browser_context"]
        CDPFrame["cdp_frame"]
        CDPTarget["cdp_target"]
        CDPSession["cdp_session"]
        CDPConnection["cdp_connection"]
        CDPFrameManagement["cdp_frame_management"]
        CDPNetworkManagement["cdp_network_management"]
    end
    
    CdpPage --> CoreAPI
    CdpPage --> CDPImplementation
    CdpPage --> NetworkHandling
    CdpPage --> InputInteraction
    CdpPage --> CDPBrowser
    CdpPage --> CDPBrowserContext
    CdpPage --> CDPFrame
    CdpPage --> CDPTarget
    CdpPage --> CDPSession
    CdpPage --> CDPConnection
    CdpPage --> CDPFrameManagement
    CdpPage --> CDPNetworkManagement
```

## Data Flow

```mermaid
sequenceDiagram
    participant Client
    participant CdpPage
    participant FrameManager
    participant NetworkManager
    participant CdpCDPSession
    participant Browser
    
    Client->>CdpPage: navigate(url)
    CdpPage->>FrameManager: navigate
    FrameManager->>CdpCDPSession: Page.navigate
    CdpCDPSession->>Browser: CDP Command
    Browser-->>CdpCDPSession: Navigation Response
    CdpCDPSession-->>FrameManager: Response
    FrameManager-->>CdpPage: Navigation Complete
    
    Browser->>CdpCDPSession: Network Events
    CdpCDPSession->>NetworkManager: Process Events
    NetworkManager->>CdpPage: Emit Events
    CdpPage->>Client: Page Events
```

## Key Features

### 1. Page Lifecycle Management

```mermaid
stateDiagram-v2
    [*] --> Creating
    Creating --> Initializing: _create()
    Initializing --> Ready: #initialize()
    Ready --> Navigating: navigate()
    Navigating --> Ready: navigation complete
    Ready --> Closing: close()
    Closing --> Closed: cleanup complete
    Closed --> [*]
    
    Ready --> Swapping: target swap
    Swapping --> Ready: #onActivation()
```

### 2. Event System

The page implements a comprehensive event system:

- **Page Events**: Load, DOMContentLoaded, Close, Error
- **Frame Events**: FrameAttached, FrameDetached, FrameNavigated
- **Network Events**: Request, Response, RequestFailed, RequestFinished
- **Console Events**: Console messages and API calls
- **Worker Events**: WorkerCreated, WorkerDestroyed
- **Dialog Events**: JavaScript dialogs

### 3. Input Device Management

Coordinates multiple input devices:
- **Keyboard**: Text input and key combinations
- **Mouse**: Clicks, movements, and drag operations
- **Touchscreen**: Touch gestures and multi-touch

### 4. Network Management

Provides network control through the NetworkManager:
- Request/response interception
- Network condition emulation
- Cache management
- Service worker bypass

### 5. Emulation Capabilities

Supports various emulation features:
- Viewport and device emulation
- Media type and feature emulation
- Geolocation simulation
- CPU throttling
- Vision deficiency simulation

## Component Interactions

```mermaid
graph TD
    subgraph "Page Operations"
        Navigate["navigate()"]
        Screenshot["screenshot()"]
        PDF["pdf()"]
        Evaluate["evaluate()"]
    end
    
    subgraph "Manager Layer"
        FrameManager["FrameManager"]
        EmulationManager["EmulationManager"]
        NetworkManager["NetworkManager"]
    end
    
    subgraph "CDP Layer"
        CdpCDPSession["CdpCDPSession"]
        Protocol["CDP Protocol"]
    end
    
    Navigate --> FrameManager
    Screenshot --> EmulationManager
    PDF --> CdpCDPSession
    Evaluate --> FrameManager
    
    FrameManager --> CdpCDPSession
    EmulationManager --> CdpCDPSession
    NetworkManager --> CdpCDPSession
    
    CdpCDPSession --> Protocol
```

## Process Flows

### Page Creation Flow

```mermaid
flowchart TD
    Start([Start]) --> CreateSession[Create CDP Session]
    CreateSession --> CreatePage["new CdpPage()"]
    CreatePage --> Initialize[Initialize Components]
    Initialize --> SetupListeners[Setup Event Listeners]
    SetupListeners --> SetViewport{Default Viewport?}
    SetViewport -->|Yes| ApplyViewport[Apply Viewport]
    SetViewport -->|No| Ready[Page Ready]
    ApplyViewport --> Ready
    Ready --> End([End])
```

### Navigation Flow

```mermaid
flowchart TD
    Start([Navigate Request]) --> WaitForNav[Setup Navigation Waiter]
    WaitForNav --> SendCommand[Send Page.navigate]
    SendCommand --> WaitEvents[Wait for Events]
    WaitEvents --> LoadEvent{Load Event?}
    LoadEvent -->|Yes| CheckTimeout{Timeout?}
    LoadEvent -->|No| WaitEvents
    CheckTimeout -->|No| Success[Navigation Success]
    CheckTimeout -->|Yes| Timeout[Navigation Timeout]
    Success --> End([End])
    Timeout --> End
```

### Event Processing Flow

```mermaid
flowchart TD
    CDPEvent[CDP Event] --> EventRouter{Event Type}
    EventRouter -->|Page| PageHandler[Page Event Handler]
    EventRouter -->|Runtime| RuntimeHandler[Runtime Event Handler]
    EventRouter -->|Network| NetworkHandler[Network Event Handler]
    EventRouter -->|Target| TargetHandler[Target Event Handler]
    
    PageHandler --> EmitPageEvent[Emit Page Event]
    RuntimeHandler --> ProcessConsole[Process Console/Exception]
    NetworkHandler --> EmitNetworkEvent[Emit Network Event]
    TargetHandler --> ManageTargets[Manage Child Targets]
    
    EmitPageEvent --> Listeners[Event Listeners]
    ProcessConsole --> Listeners
    EmitNetworkEvent --> Listeners
    ManageTargets --> Listeners
```

## Integration Points

### With Core API
- Extends the abstract `Page` class from [core_api](core_api.md)
- Implements all required page methods
- Provides CDP-specific functionality

### With CDP Implementation
- Uses [cdp_browser](cdp_browser.md) for browser context
- Integrates with [cdp_frame](cdp_frame.md) for frame management
- Leverages [cdp_target](cdp_target.md) for target operations
- Utilizes [cdp_session](cdp_session.md) for protocol communication

### With Network Management
- Integrates [cdp_network_management](cdp_network_management.md) for request handling
- Provides network interception capabilities
- Manages network conditions and caching

### With Frame Management
- Uses [cdp_frame_management](cdp_frame_management.md) for frame operations
- Coordinates frame navigation and lifecycle
- Manages isolated worlds and execution contexts

## Error Handling

The module implements comprehensive error handling:

```mermaid
graph TD
    Error[Error Occurs] --> ErrorType{Error Type}
    ErrorType -->|Target Closed| TargetError[TargetCloseError]
    ErrorType -->|Protocol Error| ProtocolError[Protocol Error]
    ErrorType -->|Timeout| TimeoutError[Timeout Error]
    ErrorType -->|Navigation| NavigationError[Navigation Error]
    
    TargetError --> CleanupResources[Cleanup Resources]
    ProtocolError --> RetryLogic{Retry?}
    TimeoutError --> CancelOperation[Cancel Operation]
    NavigationError --> EmitError[Emit Error Event]
    
    RetryLogic -->|Yes| RetryOperation[Retry Operation]
    RetryLogic -->|No| EmitError
    
    CleanupResources --> EmitError
    CancelOperation --> EmitError
    RetryOperation --> Success[Operation Success]
    EmitError --> ErrorHandled[Error Handled]
```

## Performance Considerations

1. **Resource Management**: Proper disposal of handles and sessions
2. **Event Listener Cleanup**: Automatic cleanup on page close
3. **Memory Optimization**: Efficient handling of large responses (PDF, screenshots)
4. **Connection Pooling**: Reuse of CDP sessions where possible
5. **Lazy Loading**: Components initialized only when needed

## Usage Examples

### Basic Page Operations
```typescript
// Create and navigate
const page = await CdpPage._create(session, target, viewport);
await page.goto('https://example.com');

// Take screenshot
const screenshot = await page.screenshot({ type: 'png' });

// Generate PDF
const pdf = await page.pdf({ format: 'A4' });
```

### Event Handling
```typescript
page.on('console', msg => console.log('PAGE LOG:', msg.text()));
page.on('request', request => console.log('REQUEST:', request.url()));
page.on('response', response => console.log('RESPONSE:', response.url()));
```

### Network Interception
```typescript
await page.setRequestInterception(true);
page.on('request', request => {
  if (request.url().includes('analytics')) {
    request.abort();
  } else {
    request.continue();
  }
});
```

## Related Modules

- [core_api](core_api.md) - Base Page interface and events
- [cdp_implementation](cdp_implementation.md) - CDP-specific implementations
- [cdp_frame_management](cdp_frame_management.md) - Frame lifecycle management
- [cdp_network_management](cdp_network_management.md) - Network request handling
- [input_and_interaction](input_and_interaction.md) - Input device abstractions
- [cdp_browser](cdp_browser.md) - Browser context management
- [cdp_target](cdp_target.md) - Target lifecycle management