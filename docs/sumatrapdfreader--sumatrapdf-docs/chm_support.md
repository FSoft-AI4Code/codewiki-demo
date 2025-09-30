# CHM Support Module Documentation

## Introduction

The CHM (Compiled HTML Help) support module provides comprehensive functionality for reading, parsing, and displaying Microsoft CHM files within the SumatraPDF document viewer. This module implements a complete CHM document engine that handles the proprietary CHM file format, extracts content, manages navigation, and provides an interactive viewing experience through HTML rendering.

## Module Overview

The CHM support module consists of two primary components that work together to provide complete CHM file handling capabilities:

- **ChmFile**: Low-level CHM file parser and data extractor
- **ChmModel**: High-level document model that integrates with SumatraPDF's document controller system

## Architecture

### Core Components Architecture

```mermaid
graph TB
    subgraph "CHM Support Module"
        CF[ChmFile]
        CM[ChmModel]
        HW[HtmlWindowHandler]
        CTT[ChmTocTraceItem]
    end
    
    subgraph "External Dependencies"
        DC[DocController]
        HW2[HtmlWindow]
        EF[EbookTocVisitor]
        DC2[DocControllerCallback]
    end
    
    CF -->|provides data| CM
    CM -->|implements| DC
    HW -->|handles events| CM
    HW -->|interfaces with| HW2
    CM -->|uses| CTT
    CM -->|builds via| EF
    CM -->|communicates via| DC2
```

### Data Flow Architecture

```mermaid
graph LR
    subgraph "CHM File Processing"
        CHM[CHM File]
        CF[ChmFile Parser]
        SD[System Data Parser]
        WD[Windows Data Parser]
        TD[Toc/Index Parser]
    end
    
    subgraph "Content Management"
        CM[ChmModel]
        PC[Page Cache]
        TC[Toc Cache]
        HC[HtmlWindow Handler]
    end
    
    subgraph "User Interface"
        DC[Document Controller]
        HW[HtmlWindow]
        UI[User Interface]
    end
    
    CHM -->|load| CF
    CF -->|parse metadata| SD
    CF -->|parse windows| WD
    CF -->|parse navigation| TD
    CF -->|provide content| CM
    CM -->|manage| PC
    CM -->|build| TC
    CM -->|handle events| HC
    CM -->|integrate| DC
    HC -->|render| HW
    DC -->|display| UI
```

## Component Details

### ChmFile Class

The `ChmFile` class serves as the primary interface for accessing CHM file content and metadata. It provides low-level functionality for reading and parsing CHM files using the chmlib library.

#### Key Responsibilities:
- **File Loading**: Opens and validates CHM files
- **Data Extraction**: Retrieves file content by path
- **Metadata Parsing**: Extracts document properties, codepage information, and navigation structures
- **Path Resolution**: Handles CHM internal path resolution and normalization
- **Character Encoding**: Manages text encoding conversion for different codepages

#### Core Methods:

```mermaid
classDiagram
    class ChmFile {
        -chmHandle: chmFile*
        -data: ByteSlice
        -codepage: uint
        -title: AutoFreeStr
        -tocPath: AutoFreeStr
        -indexPath: AutoFreeStr
        -homePath: AutoFreeStr
        -creator: AutoFreeStr
        +Load(path: const char*): bool
        +HasData(fileName: const char*): bool
        +GetData(fileName: const char*): ByteSlice
        +ParseWindowsData(): void
        +ParseSystemData(): bool
        +ParseTocOrIndex(visitor: EbookTocVisitor*, path: const char*, isIndex: bool): bool
        +ResolveTopicID(id: unsigned int): char*
        +GetPropertyTemp(name: const char*): TempStr
        +GetAllPaths(v: StrVec*): void
    }
```

#### File Structure Parsing:

The ChmFile class implements sophisticated parsing for CHM internal structures:

```mermaid
graph TD
    subgraph "CHM Internal Files"
        SYSTEM["/#SYSTEM"]
        WINDOWS["/#WINDOWS"]
        STRINGS["/#STRINGS"]
        IVB["/#IVB"]
    end
    
    subgraph "Parsing Process"
        SP[System Parser]
        WP[Windows Parser]
        TP[Toc/Index Parser]
        ID[Topic ID Resolver]
    end
    
    subgraph "Extracted Information"
        META[Metadata]
        NAV[Navigation Paths]
        CP[Codepage Info]
        TIT[Title/Creator]
    end
    
    SYSTEM -->|contains| SP
    WINDOWS -->|contains| WP
    STRINGS -->|referenced by| WP
    IVB -->|used by| ID
    SP -->|extracts| META
    WP -->|extracts| NAV
    SP -->|determines| CP
    WP -->|extracts| TIT
```

### ChmModel Class

The `ChmModel` class implements the document controller interface and provides high-level CHM document management. It integrates CHM files into SumatraPDF's document viewing system.

#### Key Responsibilities:
- **Document Management**: Implements the DocController interface for CHM files
- **Page Navigation**: Manages virtual page numbering based on CHM content structure
- **HTML Rendering**: Coordinates with HtmlWindow for content display
- **Table of Contents**: Builds and manages hierarchical navigation structures
- **Zoom Control**: Handles zoom levels for HTML content
- **Thumbnail Generation**: Creates document thumbnails

#### Core Methods:

```mermaid
classDiagram
    class ChmModel {
        -doc: ChmFile*
        -htmlWindow: HtmlWindow*
        -htmlWindowCb: HtmlWindowHandler*
        -pages: StrVec
        -currentPageNo: int
        -tocTrace: Vec<ChmTocTraceItem>*
        -tocTree: TocTree*
        -urlDataCache: Vec<ChmCacheEntry*>
        -poolAlloc: Allocator
        -docAccess: CRITICAL_SECTION
        +Load(fileName: const char*): bool
        +DisplayPage(pageUrl: const char*): bool
        +GetDataForUrl(url: const char*): ByteSlice
        +OnBeforeNavigate(url: const char*, newWindow: bool): bool
        +OnDocumentComplete(url: const char*): void
        +GetToc(): TocTree*
        +GetNamedDest(name: const char*): IPageDestination*
        +CreateThumbnail(size: Size, saveThumbnail: const OnBitmapRendered*): void
    }
```

#### Navigation and Page Management:

```mermaid
graph LR
    subgraph "CHM Content Structure"
        TOC[Table of Contents]
        IDX[Index]
        HOM[Home Page]
        URL[Internal URLs]
    end
    
    subgraph "Virtual Page System"
        VP[Virtual Pages]
        PN[Page Numbers]
        PC[Page Cache]
        NT[Navigation Tracking]
    end
    
    subgraph "User Navigation"
        GT[Goto Page]
        HL[Handle Links]
        NB[Navigate Back/Forward]
        ZM[Zoom Control]
    end
    
    TOC -->|builds| VP
    IDX -->|builds| VP
    HOM -->|becomes| PN
    URL -->|mapped to| PC
    VP -->|enables| GT
    PC -->|supports| HL
    NT -->|enables| NB
    ZM -->|controls| VP
```

### HtmlWindowHandler Class

The `HtmlWindowHandler` class implements the callback interface for HTML window events, bridging between the HTML rendering engine and the CHM model.

#### Key Responsibilities:
- **Navigation Events**: Handles before-navigate and document-complete events
- **Data Requests**: Provides CHM content data to the HTML renderer
- **User Interaction**: Processes mouse events and focus management
- **Download Handling**: Manages file downloads from CHM content

### ChmTocTraceItem Structure

The `ChmTocTraceItem` structure represents individual entries in the CHM table of contents, maintaining hierarchical relationships and navigation information.

## Integration with SumatraPDF

### Document Controller Interface

The ChmModel implements the DocController interface, allowing seamless integration with SumatraPDF's document management system:

```mermaid
graph TB
    subgraph "SumatraPDF Document System"
        DC[DocController Interface]
        DM[Display Model]
        EM[Engine Manager]
    end
    
    subgraph "CHM Implementation"
        CM[ChmModel]
        CF[ChmFile]
        HW[HtmlWindow Integration]
    end
    
    subgraph "User Interface"
        MW[Main Window]
        TB[Toolbar]
        TC[Table of Contents]
        ZC[Zoom Controls]
    end
    
    CM -->|implements| DC
    CM -->|uses| CF
    CM -->|integrates| HW
    EM -->|creates| CM
    DC -->|provides interface| DM
    MW -->|hosts| TB
    MW -->|displays| TC
    MW -->|controls| ZC
    CM -->|notifies| MW
```

### File Type Support

The module registers support for CHM files through the `IsSupportedFileType` method, enabling automatic detection and loading of CHM documents.

## Data Processing Pipeline

### CHM File Loading Process

```mermaid
sequenceDiagram
    participant User
    participant Engine
    participant ChmModel
    participant ChmFile
    participant HtmlWindow
    
    User->>Engine: Open CHM file
    Engine->>ChmModel: Create(fileName)
    ChmModel->>ChmFile: CreateFromFile(path)
    ChmFile->>ChmFile: Load(path)
    ChmFile->>ChmFile: ParseWindowsData()
    ChmFile->>ChmFile: ParseSystemData()
    ChmFile->>ChmModel: Return document
    ChmModel->>ChmModel: Build page list
    ChmModel->>ChmModel: Parse TOC
    ChmModel->>HtmlWindow: Create(hwnd)
    ChmModel->>User: Document ready
```

### Content Retrieval Process

```mermaid
sequenceDiagram
    participant HtmlWindow
    participant ChmModel
    participant ChmFile
    participant CHM_Lib
    
    HtmlWindow->>ChmModel: GetDataForUrl(url)
    ChmModel->>ChmModel: Find in cache
    alt Cache miss
        ChmModel->>ChmFile: GetData(url)
        ChmFile->>CHM_Lib: chm_resolve_object()
        CHM_Lib->>ChmFile: Return unit info
        ChmFile->>CHM_Lib: chm_retrieve_object()
        CHM_Lib->>ChmFile: Return data
        ChmFile->>ChmModel: Return ByteSlice
        ChmModel->>ChmModel: Cache data
    end
    ChmModel->>HtmlWindow: Return data
```

## Error Handling and Validation

### File Validation

The module implements comprehensive validation for CHM files:

- **File Format Validation**: Verifies CHM file structure and integrity
- **Data Size Limits**: Enforces 128MB limit on extracted content
- **Path Validation**: Normalizes and validates internal paths
- **Encoding Detection**: Handles various character encodings and codepages

### Error Recovery

- **Graceful Degradation**: Continues operation with partial data if some components fail
- **Fallback Mechanisms**: Uses alternative methods for content extraction
- **User Feedback**: Provides meaningful error messages for common issues

## Performance Optimizations

### Caching Strategy

```mermaid
graph LR
    subgraph "Cache Layers"
        UC[URL Data Cache]
        PC[Page Content Cache]
        TC[TOC Structure Cache]
    end
    
    subgraph "Memory Management"
        PA[Pool Allocator]
        SM[String Interning]
        LD[Lazy Data Loading]
    end
    
    subgraph "Performance Benefits"
        FR[Faster Rendering]
        RM[Reduced Memory]
        SN[Smoother Navigation]
    end
    
    UC -->|enables| FR
    PC -->|enables| RM
    TC -->|enables| SN
    PA -->|supports| UC
    SM -->|optimizes| PC
    LD -->|improves| RM
```

### Memory Management

- **Pool Allocation**: Uses memory pools for efficient allocation of small objects
- **Reference Counting**: Manages object lifetimes through reference counting
- **Lazy Loading**: Defers expensive operations until needed
- **String Interning**: Reduces memory usage for repeated strings

## Security Considerations

### Content Security

- **Path Traversal Protection**: Validates and sanitizes file paths
- **External URL Handling**: Opens external links in system browser
- **Script Execution**: Controls JavaScript execution within CHM content
- **Data Validation**: Validates all extracted data before processing

### Sandboxing

- **Isolated Rendering**: CHM content is rendered in isolated HTML windows
- **Limited File System Access**: Restricted access to file system operations
- **Controlled Navigation**: Navigation events are validated before processing

## Dependencies

### External Libraries

- **chmlib**: Core CHM file format parsing library
- **HtmlWindow**: HTML rendering and display component
- **TrivialHtmlParser**: Lightweight HTML parsing for TOC extraction

### Internal Dependencies

- **DocController**: Base document controller interface
- **EbookTocVisitor**: TOC building and navigation interface
- **StrFormat**: String formatting and manipulation utilities
- **FileUtil**: File system operations

## Related Modules

- [ebook_support](ebook_support.md) - Shared ebook functionality and base classes
- [html_parser](html_parser.md) - HTML parsing utilities used for TOC extraction
- [wingui](wingui.md) - Windows GUI components including HtmlWindow
- [document_formats](document_formats.md) - Document format detection and management

## Future Enhancements

### Planned Improvements

- **Enhanced Search**: Full-text search within CHM content
- **Better TOC Support**: Improved handling of complex TOC structures
- **Performance Optimization**: Faster loading and rendering of large CHM files
- **Accessibility**: Enhanced accessibility features for screen readers

### Technical Debt

- **Code Modernization**: Update to use modern C++ features
- **Error Handling**: Improve error reporting and recovery mechanisms
- **Testing**: Add comprehensive unit tests for all components
- **Documentation**: Expand inline documentation and examples