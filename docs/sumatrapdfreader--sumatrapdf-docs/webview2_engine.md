# WebView2 Engine Module Documentation

## Introduction

The WebView2 Engine module provides modern HTML rendering capabilities for the SumatraPDF application using Microsoft's WebView2 technology. This module serves as an alternative to the legacy MSHTML engine, offering better performance, modern web standards support, and enhanced security features. It enables the application to render HTML content, display web-based UI components, and integrate web technologies within the desktop application.

## Architecture Overview

The WebView2 Engine module is built around a COM-based architecture that interfaces with Microsoft's WebView2 runtime. The core component `webview2_com_handler` implements multiple COM interfaces to handle WebView2 lifecycle events, messaging, and permission management.

```mermaid
graph TB
    subgraph "WebView2 Engine Architecture"
        A[WebView2 Runtime] --> B[webview2_com_handler]
        B --> C[ICoreWebView2Environment]
        B --> D[ICoreWebView2Controller]
        B --> E[ICoreWebView2WebMessageReceivedEventHandler]
        B --> F[ICoreWebView2PermissionRequestedEventHandler]
        
        G[WebviewWnd] --> B
        G --> H[Window Management]
        G --> I[JavaScript Execution]
        G --> J[Navigation Control]
        
        K[Application Core] --> G
        L[UI Components] --> G
    end
```

## Core Components

### webview2_com_handler

The `webview2_com_handler` is the central component that implements multiple COM interfaces to manage WebView2 operations:

- **ICoreWebView2CreateCoreWebView2EnvironmentCompletedHandler**: Handles environment creation completion
- **ICoreWebView2CreateCoreWebView2ControllerCompletedHandler**: Manages controller creation and initialization
- **ICoreWebView2WebMessageReceivedEventHandler**: Processes JavaScript-to-native messaging
- **ICoreWebView2PermissionRequestedEventHandler**: Handles permission requests from web content

```mermaid
classDiagram
    class webview2_com_handler {
        -HWND m_window
        -WebViewMsgCb msgCb
        -webview2_com_handler_cb_t m_cb
        +AddRef() ULONG
        +Release() ULONG
        +QueryInterface(REFIID, LPVOID*) HRESULT
        +Invoke(HRESULT, ICoreWebView2Environment*) HRESULT
        +Invoke(HRESULT, ICoreWebView2Controller*) HRESULT
        +Invoke(ICoreWebView2*, ICoreWebView2WebMessageReceivedEventArgs*) HRESULT
        +Invoke(ICoreWebView2*, ICoreWebView2PermissionRequestedEventArgs*) HRESULT
    }
```

### WebviewWnd

The `WebviewWnd` class provides the window management and high-level API for WebView2 integration:

- **Window Management**: Handles WebView2 embedding within application windows
- **Navigation Control**: Provides methods for loading HTML content and URLs
- **JavaScript Integration**: Enables bidirectional communication with web content
- **Size Management**: Automatically adjusts WebView2 bounds to match window size

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant App as Application
    participant WW as WebviewWnd
    participant CH as webview2_com_handler
    participant W2 as WebView2 Runtime
    participant JS as JavaScript

    App->>WW: CreateWebViewArgs
    WW->>CH: Create handler
    CH->>W2: CreateCoreWebView2EnvironmentWithOptions
    W2-->>CH: Environment created
    CH->>W2: CreateCoreWebView2Controller
    W2-->>CH: Controller created
    CH->>WW: ComHandlerCb
    
    Note over WW,W2: WebView2 ready
    
    WW->>W2: Navigate/SetHtml
    W2->>JS: Load content
    JS->>W2: Post message
    W2->>CH: WebMessageReceived
    CH->>WW: OnBrowserMessage
    WW->>App: Process message
```

## Component Interactions

### Environment Creation Process

```mermaid
flowchart TD
    A[Application Request] --> B[CreateCoreWebView2EnvironmentWithOptions]
    B --> C{Environment Available?}
    C -->|Yes| D[Create webview2_com_handler]
    C -->|No| E[Return Failure]
    D --> F[Initialize COM Interfaces]
    F --> G[Create Controller]
    G --> H[Setup Event Handlers]
    H --> I[Configure Settings]
    I --> J[WebView2 Ready]
```

### Message Handling Flow

```mermaid
flowchart LR
    A[JavaScript postMessage] --> B[WebView2 Runtime]
    B --> C[ICoreWebView2WebMessageReceivedEventHandler]
    C --> D[webview2_com_handler::Invoke]
    D --> E[Convert to UTF-8]
    E --> F[WebViewMsgCb callback]
    F --> G[Application Processing]
    G --> H[Optional Response]
    H --> I[PostWebMessageAsString]
```

## Integration with HTML Rendering Components

The WebView2 Engine module is part of the broader HTML rendering components family, which includes:

- **[MSHTML Engine](mshtml_engine.md)**: Legacy Internet Explorer-based rendering
- **WebView2 Engine (Current)**: Modern Chromium-based rendering

```mermaid
graph LR
    subgraph "HTML Rendering Components"
        A[Application UI] --> B{Rendering Engine}
        B -->|Legacy| C[MSHTML Engine]
        B -->|Modern| D[WebView2 Engine]
        
        C --> E[HW_IDocHostUIHandler]
        C --> F[HW_DWebBrowserEvents2]
        
        D --> G[webview2_com_handler]
        D --> H[WebView2 Runtime]
    end
```

## Key Features and Capabilities

### 1. Modern Web Standards Support
- Full HTML5, CSS3, and ES6+ JavaScript support
- WebGL and Canvas rendering
- Modern DOM APIs and event handling

### 2. Security Features
- Sandboxed rendering environment
- Configurable permission management
- Isolated from system resources

### 3. Performance Benefits
- Hardware-accelerated rendering
- Multi-process architecture
- Optimized memory usage

### 4. JavaScript Integration
- Bidirectional messaging between native and web content
- Custom JavaScript injection
- External object exposure

## Configuration and Settings

The WebView2 Engine provides several configuration options:

```cpp
// Available settings via ICoreWebView2Settings
settings->put_AreDefaultContextMenusEnabled(FALSE);    // Disable context menus
settings->put_AreDevToolsEnabled(FALSE);              // Disable developer tools
settings->put_IsStatusBarEnabled(FALSE);              // Disable status bar
settings->put_IsWebMessageEnabled(TRUE);              // Enable web messaging
settings->put_AreDefaultScriptDialogsEnabled(FALSE);  // Disable script dialogs
```

## Error Handling and Fallback

The module implements robust error handling for WebView2 availability:

```mermaid
flowchart TD
    A[Check WebView2 Availability] --> B{Runtime Installed?}
    B -->|Yes| C[Proceed with WebView2]
    B -->|No| D[Log Error]
    D --> E[Fallback to MSHTML]
    E --> F[Notify User]
```

## Usage Patterns

### Basic WebView2 Creation
```cpp
WebviewWnd* webview = new WebviewWnd();
CreateWebViewArgs args;
args.parent = parentWindow;
args.pos = initialPosition;
HWND hwnd = webview->Create(args);
```

### HTML Content Loading
```cpp
// Load HTML string
webview->SetHtml("<html><body>Hello World</body></html>");

// Navigate to URL
webview->Navigate("https://example.com");
```

### JavaScript Execution
```cpp
// Execute JavaScript
webview->Eval("console.log('Hello from native code');");

// Inject initialization script
webview->Init("window.external = { invoke: s => window.chrome.webview.postMessage(s) };");
```

## Dependencies and Requirements

### System Requirements
- Windows 10 version 1803 or later
- WebView2 Runtime (Evergreen or Fixed Version)
- Microsoft Edge Chromium-based browser components

### Module Dependencies
- `utils/BaseUtil.h`: Base utility functions
- `utils/WinUtil.h`: Windows-specific utilities
- `wingui/UIModels.h`: UI model definitions
- `webview2.h`: WebView2 SDK headers

## Performance Considerations

### Memory Management
- Automatic cleanup of COM objects
- Reference counting for WebView2 components
- Proper disposal of event handlers

### Thread Safety
- COM apartment threading model
- Message queue processing during initialization
- Synchronous environment creation

### Resource Usage
- Shared WebView2 runtime across applications
- Configurable user data folder for caching
- Optimized for multiple WebView2 instances

## Future Enhancements

Potential areas for future development include:

1. **Enhanced JavaScript Bridge**: More sophisticated native-to-JavaScript communication
2. **Custom Protocol Handling**: Support for custom URL schemes
3. **Print Integration**: Web content printing capabilities
4. **Accessibility Improvements**: Better screen reader and accessibility support
5. **Performance Monitoring**: Built-in performance metrics and profiling

## Related Documentation

- [MSHTML Engine](mshtml_engine.md) - Legacy HTML rendering implementation
- [Core Application and UI](core_application_and_ui.md) - Main application components
- [Windows Dark Mode](windows_dark_mode.md) - UI theming integration

## Conclusion

The WebView2 Engine module represents a significant modernization of the SumatraPDF application's HTML rendering capabilities. By leveraging Microsoft's WebView2 technology, it provides a secure, performant, and feature-rich environment for rendering web content within the desktop application. The modular design allows for easy integration with existing UI components while maintaining compatibility with legacy systems through the parallel MSHTML engine implementation.