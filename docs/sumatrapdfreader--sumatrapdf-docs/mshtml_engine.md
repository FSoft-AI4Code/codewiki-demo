# MSHTML Engine Module Documentation

## Introduction

The MSHTML Engine module provides a comprehensive wrapper around Microsoft's MSHTML (Trident) rendering engine, enabling SumatraPDF to display HTML content and CHM (Compiled HTML Help) documents. This module implements custom COM interfaces and protocol handlers to seamlessly integrate web content rendering within the application's native windowing system.

The module solves critical challenges in displaying CHM documents from network drives and provides a robust framework for handling custom protocols, in-memory HTML content, and complex navigation scenarios.

## Architecture Overview

### Core Components

The MSHTML Engine module consists of five primary components that work together to provide HTML rendering capabilities:

```mermaid
graph TB
    subgraph "MSHTML Engine Core"
        HW_IDocHostUIHandler["HW_IDocHostUIHandler<br/>UI Customization"]
        HW_DWebBrowserEvents2["HW_DWebBrowserEvents2<br/>Event Handling"]
        HW_IInternetProtocol["HW_IInternetProtocol<br/>Custom Protocol"]
        FrameSite["FrameSite<br/>COM Interface Hub"]
        HtmlMoniker["HtmlMoniker<br/>Content Binding"]
    end
    
    subgraph "External Dependencies"
        IWebBrowser2["IWebBrowser2<br/>MSHTML Control"]
        IHTMLDocument2["IHTMLDocument2<br/>Document Interface"]
        HtmlWindow["HtmlWindow<br/>Main Window Class"]
    end
    
    FrameSite --> HW_IDocHostUIHandler
    FrameSite --> HW_DWebBrowserEvents2
    FrameSite --> HW_IInternetProtocol
    FrameSite --> HtmlMoniker
    FrameSite --> IWebBrowser2
    FrameSite --> HtmlWindow
    HtmlMoniker --> IHTMLDocument2
```

### Component Relationships

```mermaid
graph LR
    subgraph "Interface Hierarchy"
        IUnknown["IUnknown"]
        IDocHostUIHandler["IDocHostUIHandler"]
        DWebBrowserEvents2["DWebBrowserEvents2"]
        IInternetProtocol["IInternetProtocol"]
        IMoniker["IMoniker"]
        
        IUnknown --> IDocHostUIHandler
        IUnknown --> DWebBrowserEvents2
        IUnknown --> IInternetProtocol
        IUnknown --> IMoniker
        
        IDocHostUIHandler -.-> HW_IDocHostUIHandler
        DWebBrowserEvents2 -.-> HW_DWebBrowserEvents2
        IInternetProtocol -.-> HW_IInternetProtocol
        IMoniker -.-> HtmlMoniker
    end
```

## Detailed Component Documentation

### FrameSite - The Central Hub

**Purpose**: FrameSite serves as the central coordination point for all COM interfaces required by the MSHTML engine. It implements a comprehensive set of OLE and COM interfaces needed for proper browser control integration.

**Key Responsibilities**:
- Manages the lifecycle of all COM interface implementations
- Provides interface aggregation and query services
- Coordinates between the HTML window and browser control
- Handles window activation and UI state management

**Interface Implementations**:
- `IOleInPlaceFrame` - Frame window management
- `IOleInPlaceSiteWindowless` - In-place activation support
- `IOleClientSite` - Client site services
- `IOleControlSite` - Control hosting
- `IOleCommandTarget` - Command processing
- `IDocHostUIHandler` - UI customization
- `IDropTarget` - Drag and drop support
- `IServiceProvider` - Service discovery

### HW_IDocHostUIHandler - UI Customization

**Purpose**: Provides comprehensive UI customization capabilities for the hosted browser control, allowing SumatraPDF to maintain consistent visual appearance and behavior.

**Key Features**:
- Disables context menus to prevent external navigation
- Customizes border appearance and 3D effects
- Controls scrollbar behavior and appearance
- Manages host CSS and namespace configurations
- Handles drag target customization

**Integration Points**:
- Works with [core_application_and_ui](core_application_and_ui.md) for consistent theming
- Coordinates with [windows_dark_mode](windows_dark_mode.md) for dark mode support

### HW_DWebBrowserEvents2 - Event Management

**Purpose**: Captures and processes all browser events, providing a bridge between the MSHTML engine and SumatraPDF's navigation system.

**Event Handling**:
- `DISPID_BEFORENAVIGATE2` - Pre-navigation validation
- `DISPID_DOCUMENTCOMPLETE` - Document loading completion
- `DISPID_NAVIGATEERROR` - Navigation error handling
- `DISPID_COMMANDSTATECHANGE` - Browser state changes
- `DISPID_NEWWINDOW3` - New window requests

**Protocol Integration**:
- Intercepts `its://` protocol requests
- Routes navigation through SumatraPDF's document system
- Handles network drive CHM document access

### HW_IInternetProtocol - Custom Protocol Handler

**Purpose**: Implements a custom protocol handler that overrides the `its://` protocol to provide seamless access to CHM documents, particularly from network drives.

**Protocol Flow**:
```mermaid
sequenceDiagram
    participant Browser as "MSHTML Browser"
    participant Protocol as "HW_IInternetProtocol"
    participant Window as "HtmlWindow"
    participant Callback as "HtmlWindowCallback"
    
    Browser->>Protocol: Start(its://windowId/url)
    Protocol->>Protocol: ParseProtoUrl()
    Protocol->>Window: FindHtmlWindowById()
    Protocol->>Callback: GetDataForUrl()
    Callback-->>Protocol: ByteSlice data
    Protocol->>Browser: ReportData()
    Protocol->>Browser: ReportResult(S_OK)
    Browser-->>Protocol: Read() calls
    Protocol-->>Browser: Stream data
```

**Key Features**:
- URL parsing with window ID extraction
- MIME type detection and reporting
- Data streaming with progress notifications
- Error handling for missing content

### HtmlMoniker - Content Binding

**Purpose**: Provides a custom moniker implementation that allows loading HTML content from memory rather than from files or URLs, enabling dynamic content generation and display.

**Content Flow**:
```mermaid
graph TD
    A["SetHtml()"] --> B["Create IStream"]
    C["SetBaseUrl()"] --> D["Store Base URL"]
    E["BindToStorage()"] --> F["Return IStream"]
    G["GetDisplayName()"] --> H["Return Base URL"]
    
    B --> I["IPersistMoniker::Load()"]
    D --> I
    F --> J["IHTMLDocument2"]
    H --> K["URL Resolution"]
```

## Data Flow Architecture

### Navigation Process

```mermaid
graph TB
    subgraph "Navigation Flow"
        A["NavigateToUrl()"] --> B["OnBeforeNavigate()"]
        B --> C{"Protocol Check"}
        C -->|"its://"| D["ParseProtoUrl()"]
        C -->|"Other"| E["Direct Navigation"]
        D --> F["Strip Protocol"]
        F --> G["Callback Validation"]
        E --> G
        G --> H{"Allow Navigation?"}
        H -->|"Yes"| I["Proceed with Navigation"]
        H -->|"No"| J["Cancel Navigation"]
        I --> K["Document Loading"]
        K --> L["OnDocumentComplete()"]
    end
```

### Content Loading Process

```mermaid
graph LR
    subgraph "Content Loading"
        A["SetHtml()"] --> B["NavigateToAboutBlank()"]
        B --> C["OnDocumentComplete()"]
        C --> D{"Is Blank URL?"}
        D -->|"Yes"| E["SetHtmlReal()"]
        D -->|"No"| F["Regular Navigation"]
        E --> G["Create HtmlMoniker"]
        G --> H["IPersistMoniker::Load()"]
        H --> I["IHTMLDocument2"]
        I --> J["Content Displayed"]
    end
```

## Integration with SumatraPDF

### CHM Document Support

The MSHTML Engine is crucial for CHM document rendering, providing:
- Custom protocol handling for `its://` URLs
- Network drive CHM document access
- Embedded image and resource resolution
- Navigation within CHM content

### Relationship to Other Modules

```mermaid
graph TB
    subgraph "Module Dependencies"
        MSHTML["mshtml_engine"]
        CHM["chm_document_support"]
        UI["ui_components"]
        CORE["core_application_and_ui"]
        
        MSHTML -->|"Provides HTML Rendering"| CHM
        MSHTML -->|"UI Customization"| UI
        MSHTML -->|"Window Management"| CORE
        CHM -->|"Document Content"| MSHTML
        UI -->|"Theming Support"| MSHTML
    end
```

**Related Modules**:
- [core_application_and_ui](core_application_and_ui.md) - Main window management and UI coordination
- [ui_components](ui_components.md) - UI element theming and customization
- [ebook_engines](ebook_engines.md) - CHM document processing and content extraction

## Technical Implementation Details

### COM Interface Management

The module implements a comprehensive set of COM interfaces required for MSHTML integration:

```cpp
// Interface aggregation pattern used in FrameSite
STDMETHODIMP FrameSite::QueryInterface(REFIID riid, void** ppv) {
    if (riid == IID_IDocHostUIHandler) {
        *ppv = docHostUIHandler;
    } else if (riid == IID_DWebBrowserEvents2) {
        *ppv = hwDWebBrowserEvents2;
    }
    // ... additional interface mappings
}
```

### Protocol Registration

The custom protocol handler is registered application-wide:

```cpp
// Registration of custom protocol
HRESULT hr = internetSession->RegisterNameSpace(
    gInternetProtocolFactory, 
    CLSID_HW_IInternetProtocol, 
    HW_PROTO_PREFIX, 0, nullptr, 0
);
```

### Window Management

The module provides sophisticated window subclassing for proper message handling:

```cpp
// Subclassing for message interception
void HtmlWindow::SubclassHwnd() {
    subclassId = NextSubclassId();
    SetWindowSubclass(hwndParent, WndProcParent2, subclassId, (DWORD_PTR)this);
}
```

## Error Handling and Recovery

### Navigation Error Management

The module implements comprehensive error handling for various failure scenarios:

- **INET_E_INVALID_URL**: Malformed protocol URLs
- **INET_E_OBJECT_NOT_FOUND**: Missing window or callback
- **INET_E_DATA_NOT_AVAILABLE**: Content retrieval failures
- **OLE Errors**: COM interface failures

### Resource Cleanup

Proper resource management ensures no memory leaks or COM reference issues:

```cpp
HtmlWindow::~HtmlWindow() {
    UnsubclassHwnd();
    if (connectionPoint) {
        connectionPoint->Unadvise(adviseCookie);
        connectionPoint->Release();
    }
    if (oleObject) {
        oleObject->Close(OLECLOSE_NOSAVE);
        oleObject->SetClientSite(nullptr);
        oleObject->Release();
    }
    // ... additional cleanup
}
```

## Performance Considerations

### Memory Management

- Efficient ByteSlice usage for data transfer
- Stream-based content loading to handle large documents
- Reference counting for COM object lifecycle management

### Threading Model

- STA (Single Threaded Apartment) COM model
- UI thread execution for all browser interactions
- Synchronous protocol handling for immediate response

## Security Considerations

### Content Restrictions

- Silent mode operation prevents script errors
- Disabled context menus prevent external navigation
- Custom protocol limits to internal content only
- Download manager interception for controlled file access

### URL Validation

- Strict protocol URL parsing and validation
- Window ID verification to prevent cross-window access
- Base URL validation for content integrity

## Future Enhancements

### Potential Improvements

1. **WebView2 Integration**: Consider migration to modern WebView2 engine
2. **Async Protocol Handling**: Implement asynchronous protocol processing
3. **Enhanced Error Pages**: Custom error page generation for navigation failures
4. **Performance Monitoring**: Add navigation timing and performance metrics
5. **Accessibility Support**: Enhanced accessibility features for HTML content

### Compatibility Notes

- Designed for Windows platforms with MSHTML support
- Requires Internet Explorer components
- Compatible with Windows 7 and later versions
- Supports both 32-bit and 64-bit architectures

## Conclusion

The MSHTML Engine module provides a robust foundation for HTML content rendering within SumatraPDF, with particular strength in CHM document support. Its custom protocol handling, comprehensive COM interface implementation, and seamless integration with the application's architecture make it an essential component for document viewing capabilities. The module's design allows for future enhancements while maintaining compatibility and performance requirements.