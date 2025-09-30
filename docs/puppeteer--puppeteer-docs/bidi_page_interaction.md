# BiDi Page Interaction Module

## Overview

The `bidi_page_interaction` module provides WebDriver BiDi-based implementations for page and frame interactions in Puppeteer. This module serves as the primary interface for browser automation tasks using the modern WebDriver BiDi protocol, offering enhanced cross-browser compatibility and standardized automation capabilities.

The module consists of two core components:
- **BidiPage**: High-level page automation interface implementing the WebDriver BiDi protocol
- **BidiFrame**: Frame-specific operations and navigation handling within BiDi contexts

## Architecture

```mermaid
graph TB
    subgraph "BiDi Page Interaction Layer"
        BP[BidiPage]
        BF[BidiFrame]
    end
    
    subgraph "Core API Layer"
        P[Page]
        F[Frame]
    end
    
    subgraph "BiDi Core Layer"
        BC[BrowsingContext]
        BR[BidiRealm]
        BConn[BidiConnection]
    end
    
    subgraph "Input & Interaction"
        BK[BidiKeyboard]
        BM[BidiMouse]
        BT[BidiTouchscreen]
    end
    
    subgraph "Element Handling"
        BEH[BidiElementHandle]
        BJH[BidiJSHandle]
    end
    
    subgraph "Network & Navigation"
        BHR[BidiHTTPRequest]
        BHRES[BidiHTTPResponse]
    end
    
    BP --> P
    BF --> F
    BP --> BC
    BF --> BC
    BP --> BK
    BP --> BM
    BP --> BT
    BF --> BR
    BP --> BEH
    BF --> BEH
    BP --> BJH
    BF --> BJH
    BF --> BHR
    BF --> BHRES
    
    style BP fill:#e1f5fe
    style BF fill:#e1f5fe
    style BC fill:#f3e5f5
    style BR fill:#f3e5f5
```

## Component Dependencies

```mermaid
graph LR
    subgraph "External Dependencies"
        BIDI[chromium-bidi]
        CDP[devtools-protocol]
        RXJS[rxjs]
    end
    
    subgraph "Internal Dependencies"
        CA[core_api]
        II[input_and_interaction]
        EH[bidi_element_handling]
        BC[bidi_core]
        CL[bidi_connection_layer]
        CU[common_utilities]
    end
    
    BPI[bidi_page_interaction] --> BIDI
    BPI --> CDP
    BPI --> RXJS
    BPI --> CA
    BPI --> II
    BPI --> EH
    BPI --> BC
    BPI --> CL
    BPI --> CU
    
    style BPI fill:#e1f5fe
```

## Core Components

### BidiPage

The `BidiPage` class implements the abstract `Page` interface using WebDriver BiDi protocol, providing comprehensive browser page automation capabilities.

#### Key Features

- **Navigation Control**: URL navigation, page reloading, history traversal
- **Content Manipulation**: HTML content setting, script injection, function exposure
- **Input Simulation**: Keyboard, mouse, and touch interactions
- **Network Management**: Request/response interception, cookie handling, authentication
- **Media Emulation**: Device emulation, network conditions, geolocation
- **Document Generation**: PDF creation, screenshot capture
- **Worker Management**: Service worker and web worker handling

#### Architecture Integration

```mermaid
graph TB
    subgraph "BidiPage Core"
        BP[BidiPage]
        BF[BidiFrame]
        BC[BrowsingContext]
    end
    
    subgraph "Input Systems"
        BK[BidiKeyboard]
        BM[BidiMouse]
        BT[BidiTouchscreen]
    end
    
    subgraph "CDP Compatibility"
        CEM[EmulationManager]
        TR[Tracing]
        COV[Coverage]
        CDPS[BidiCdpSession]
    end
    
    subgraph "Network Layer"
        INT[Interception]
        AUTH[Authentication]
        COOK[Cookie Management]
    end
    
    BP --> BF
    BP --> BC
    BP --> BK
    BP --> BM
    BP --> BT
    BP --> CEM
    BP --> TR
    BP --> COV
    BP --> CDPS
    BP --> INT
    BP --> AUTH
    BP --> COOK
    
    style BP fill:#e1f5fe
    style BF fill:#e8f5e8
```

### BidiFrame

The `BidiFrame` class extends the abstract `Frame` interface, providing frame-specific operations within BiDi browsing contexts.

#### Key Features

- **Frame Hierarchy**: Parent-child frame relationships and navigation
- **Content Loading**: DOM content loading, network idle detection
- **Script Execution**: JavaScript evaluation in different realms
- **Event Handling**: Console messages, navigation events, worker lifecycle
- **Element Interaction**: Element location, file uploads, accessibility

#### Frame Lifecycle Management

```mermaid
sequenceDiagram
    participant BC as BrowsingContext
    participant BF as BidiFrame
    participant P as BidiPage
    participant E as EventEmitter
    
    BC->>BF: Create frame
    BF->>BF: Initialize realms
    BF->>P: Emit FrameAttached
    
    loop Frame Operations
        BF->>BC: Navigate/Load content
        BC->>BF: Navigation events
        BF->>P: Emit navigation events
    end
    
    BC->>BF: Frame closed
    BF->>E: Cleanup sessions
    BF->>P: Emit FrameDetached
```

## Data Flow Patterns

### Navigation Flow

```mermaid
sequenceDiagram
    participant U as User Code
    participant BP as BidiPage
    participant BF as BidiFrame
    participant BC as BrowsingContext
    participant N as Navigation
    
    U->>BP: goto(url)
    BP->>BF: waitForNavigation()
    BP->>BC: navigate(url)
    BC->>N: Create navigation
    N->>BF: Navigation events
    BF->>BP: Response/Error
    BP->>U: Return response
```

### Request Interception Flow

```mermaid
sequenceDiagram
    participant BP as BidiPage
    participant BC as BrowsingContext
    participant R as Request
    participant HR as BidiHTTPRequest
    
    BP->>BC: addIntercept()
    BC->>R: Intercept request
    R->>HR: Create HTTP request
    HR->>HR: Apply headers/auth
    HR->>R: Continue/Modify
    R->>BC: Complete request
```

## Integration Points

### Core API Integration

The module integrates with the [core_api](core_api.md) module by implementing abstract interfaces:

- Extends `Page` and `Frame` base classes
- Implements standard event emission patterns
- Provides consistent API surface across protocols

### Input and Interaction Integration

Leverages the [input_and_interaction](input_and_interaction.md) module for:

- Keyboard input simulation via `BidiKeyboard`
- Mouse interaction via `BidiMouse`
- Touch gesture support via `BidiTouchscreen`

### Element Handling Integration

Works with [bidi_element_handling](bidi_element_handling.md) for:

- Element location and manipulation
- JavaScript handle management
- DOM interaction capabilities

### BiDi Core Integration

Depends on [bidi_core](bidi_core.md) for:

- `BrowsingContext` management
- `Realm` execution contexts
- Protocol-level communication

## Error Handling

### Navigation Error Handling

```mermaid
graph TD
    A[Navigation Request] --> B{Navigation Success?}
    B -->|Yes| C[Return Response]
    B -->|No| D[Check Error Type]
    D --> E[HTTP Response Code Failure]
    D --> F[Navigation Canceled]
    D --> G[Navigation Aborted]
    D --> H[Other Errors]
    E --> I[Continue Silently]
    F --> I
    G --> I
    H --> J[Rewrite Error]
    J --> K[Throw Enhanced Error]
```

### Common Error Scenarios

- **UnsupportedOperation**: Features not available in BiDi protocol
- **TargetCloseError**: Frame/page closed during operation
- **Navigation Errors**: Network failures, timeouts, redirects
- **Protocol Errors**: BiDi command failures, connection issues

## Performance Considerations

### Optimization Strategies

1. **Event Filtering**: Only process relevant events for current frame context
2. **Lazy Initialization**: Create child frames and workers on-demand
3. **Request Batching**: Combine multiple BiDi commands when possible
4. **Memory Management**: Proper cleanup of event listeners and sessions

### Resource Management

```mermaid
graph TB
    subgraph "Resource Lifecycle"
        A[Create Resources]
        B[Active Usage]
        C[Cleanup Triggers]
        D[Resource Disposal]
    end
    
    A --> B
    B --> C
    C --> D
    
    subgraph "Cleanup Triggers"
        E[Frame Detached]
        F[Page Closed]
        G[Navigation Complete]
        H[Explicit Disposal]
    end
    
    C --> E
    C --> F
    C --> G
    C --> H
```

## Usage Examples

### Basic Page Navigation

```typescript
const page = await browser.newPage();
await page.goto('https://example.com');
await page.waitForLoadState('networkidle');
```

### Request Interception

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

### Frame Interaction

```typescript
const frame = page.mainFrame();
const childFrames = frame.childFrames();
await frame.evaluate(() => document.title);
```

## Future Enhancements

### Planned Features

1. **Enhanced BiDi Support**: Additional WebDriver BiDi capabilities as they become available
2. **Performance Optimization**: Improved event handling and resource management
3. **Cross-Browser Compatibility**: Enhanced support for Firefox and other BiDi-compliant browsers
4. **Advanced Debugging**: Better error reporting and debugging capabilities

### Migration Path

For users transitioning from CDP-based implementations:

1. **API Compatibility**: Most existing APIs remain unchanged
2. **Feature Parity**: BiDi implementations provide equivalent functionality
3. **Gradual Migration**: Can run both CDP and BiDi implementations side-by-side
4. **Enhanced Capabilities**: BiDi offers improved cross-browser support

## Related Documentation

- [Core API](core_api.md) - Base interfaces and event patterns
- [Input and Interaction](input_and_interaction.md) - User input simulation
- [BiDi Element Handling](bidi_element_handling.md) - Element manipulation
- [BiDi Core](bidi_core.md) - Protocol-level BiDi implementation
- [BiDi Connection Layer](bidi_connection_layer.md) - WebDriver BiDi communication
- [Network Handling](network_handling.md) - HTTP request/response management