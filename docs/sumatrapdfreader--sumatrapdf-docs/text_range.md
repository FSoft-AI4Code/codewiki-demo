# Text Range Module Documentation

## Introduction

The text_range module provides UI Automation (UIA) text range functionality for SumatraPDF, enabling accessibility features and programmatic text manipulation. This module implements the `ITextRangeProvider` interface, which is a core component of Microsoft's UI Automation framework for text-based controls.

The module facilitates text selection, navigation, and manipulation at various granularities (character, word, line, paragraph, page, and document levels), making PDF documents accessible to screen readers and other assistive technologies.

## Architecture Overview

```mermaid
graph TB
    subgraph "UI Automation Layer"
        UIA[UIA Framework]
        TR[SumatraUIAutomationTextRange]
        DP[DocumentProvider]
        PP[PageProvider]
    end
    
    subgraph "Core Components"
        CEP[CharEndPointMover]
        WEP[WordEndPointMover]
        LEP[LineEndPointMover]
        TS[TextSelection]
        TC[TextCache]
    end
    
    subgraph "Document Engine"
        DM[DisplayModel]
        ENG[Engine]
    end
    
    UIA -->|uses| TR
    TR -->|implements| ITextRangeProvider
    TR -->|uses| CEP
    TR -->|uses| WEP
    TR -->|uses| LEP
    TR -->|manages| TS
    TR -->|accesses| DP
    DP -->|provides| DM
    DM -->|contains| TC
    DM -->|manages| ENG
    TS -->|operates on| TC
    
    style TR fill:#f9f,stroke:#333,stroke-width:4px
    style CEP fill:#bbf,stroke:#333,stroke-width:2px
    style WEP fill:#bbf,stroke:#333,stroke-width:2px
    style LEP fill:#bbf,stroke:#333,stroke-width:2px
```

## Core Components

### SumatraUIAutomationTextRange

The main class that implements the `ITextRangeProvider` interface. It represents a range of text within a document and provides methods for text manipulation, navigation, and selection.

**Key Responsibilities:**
- Text range management (start/end positions across pages)
- Text unit navigation (character, word, line, paragraph, page, document)
- Text selection and extraction
- Coordinate validation and range normalization

**Constructor Variants:**
- Default constructor (creates null range)
- Page-specific constructor (entire page range)
- TextSelection-based constructor (from existing selection)
- Copy constructor

### Endpoint Movers

Specialized classes for navigating text at different granularities:

#### CharEndPointMover
- **Purpose**: Handles character-by-character navigation
- **Methods**: `NextEndpoint()`, `PrevEndpoint()`
- **Behavior**: Simple glyph increment/decrement

#### WordEndPointMover
- **Purpose**: Handles word-by-word navigation
- **Methods**: `NextEndpoint()`, `PrevEndpoint()`
- **Behavior**: Uses word boundary detection via `FindNextWordEndpoint()` and `FindPreviousWordEndpoint()`

#### LineEndPointMover
- **Purpose**: Handles line-by-line navigation
- **Methods**: `NextEndpoint()`, `PrevEndpoint()`
- **Behavior**: Uses line boundary detection via `FindNextLineEndpoint()` and `FindPreviousLineEndpoint()`

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant UIA as UIA Client
    participant TR as TextRange
    participant DP as DocumentProvider
    participant DM as DisplayModel
    participant TC as TextCache
    participant ENG as Engine
    
    UIA->>TR: GetText(maxLength, text)
    TR->>TR: Validate range
    TR->>DP: Check document loaded
    DP->>DM: Get text cache
    TR->>TC: Get text for range
    TR->>TS: Create TextSelection
    TR->>TS: Extract text
    TS->>ENG: Get text content
    ENG->>TS: Return formatted text
    TS->>TR: Return extracted text
    TR->>UIA: Return BSTR text
```

## Component Interactions

```mermaid
graph LR
    subgraph "Text Range Operations"
        MOVE[Move]
        MOVEEP[MoveEndpointByUnit]
        EXPAND[ExpandToEnclosingUnit]
        GETTEXT[GetText]
        SELECT[Select]
    end
    
    subgraph "Navigation Logic"
        CEPM[CharEndPointMover]
        WEPM[WordEndPointMover]
        LEPM[LineEndPointMover]
        FINDW[FindWordEndpoint]
        FINDL[FindLineEndpoint]
    end
    
    subgraph "Validation"
        VALSTART[ValidateStartEndpoint]
        VALEND[ValidateEndEndpoint]
        ISNULL[IsNullRange]
        ISEMPTY[IsEmptyRange]
    end
    
    MOVE -->|uses| EXPAND
    MOVE -->|uses| MOVEEP
    MOVEEP -->|uses| CEPM
    MOVEEP -->|uses| WEPM
    MOVEEP -->|uses| LEPM
    WEPM -->|uses| FINDW
    LEPM -->|uses| FINDL
    MOVEEP -->|calls| VALSTART
    MOVEEP -->|calls| VALEND
    GETTEXT -->|checks| ISNULL
    GETTEXT -->|checks| ISEMPTY
    SELECT -->|checks| ISNULL
```

## Process Flows

### Text Range Creation

```mermaid
flowchart TD
    A[UIA Client Request] --> B{Range Type?}
    B -->|Null Range| C[Create with SetToNullRange]
    B -->|Page Range| D[Create with page number]
    B -->|Selection Range| E[Create from TextSelection]
    B -->|Copy Range| F[Use Copy Constructor]
    
    C --> G[Set startPage=-1, endPage=-1]
    D --> H[Set page boundaries]
    E --> I[Extract from TextSelection]
    F --> J[Copy all properties]
    
    G --> K[Return TextRange]
    H --> K
    I --> K
    J --> K
```

### Text Navigation Process

```mermaid
flowchart TD
    A[MoveEndpointByUnit Called] --> B{Unit Type?}
    B -->|Character| C[Use CharEndPointMover]
    B -->|Word| D[Use WordEndPointMover]
    B -->|Line/Paragraph| E[Use LineEndPointMover]
    B -->|Page| F[Direct page navigation]
    B -->|Document| G[Set to document bounds]
    
    C --> H[Simple glyph increment/decrement]
    D --> I[Find word boundaries]
    E --> J[Find line boundaries]
    F --> K[Page-based navigation]
    G --> L[Set start=1,0 and end=lastPage,end]
    
    H --> M[Validate endpoints]
    I --> M
    J --> M
    K --> M
    L --> M
    
    M --> N[Return moved count]
```

## Key Dependencies

### Internal Dependencies
- **[DocumentProvider](document_provider.md)**: Provides document context and display model access
- **[PageProvider](page_provider.md)**: Manages page-level information
- **[TextSelection](text_selection.md)**: Handles text selection logic and text extraction
- **[DisplayModel](display_model.md)**: Provides access to text cache and page management

### External Dependencies
- **UI Automation Framework**: Implements `ITextRangeProvider` interface
- **Windows COM**: Uses SAFEARRAY, BSTR, and COM interface patterns
- **Text Cache**: Accesses cached text content for efficient navigation

## Text Unit Support

The module supports the following text units for navigation and selection:

| Unit | Description | Implementation |
|------|-------------|----------------|
| Character | Individual characters | Simple glyph navigation |
| Word | Word boundaries | Word character detection |
| Line | Line boundaries | Newline character detection |
| Paragraph | Same as line (PDF limitation) | Line boundary detection |
| Page | Entire pages | Page-based navigation |
| Document | Entire document | Document boundary navigation |
| Format | Not supported | Returns immediately |

## Error Handling

The module implements comprehensive error handling:

- **Null Pointer Checks**: All output parameters are validated
- **Document State Validation**: Checks if document is loaded before operations
- **Range Validation**: Ensures ranges are valid and non-overlapping
- **Memory Management**: Proper COM reference counting and memory allocation
- **Boundary Validation**: Prevents navigation beyond document limits

## Performance Considerations

- **Text Caching**: Leverages DisplayModel's text cache for efficient text access
- **Lazy Evaluation**: Text extraction only when needed via `GetText()`
- **Boundary Optimization**: Efficient word/line boundary detection algorithms
- **Memory Efficiency**: Minimal memory footprint for range objects

## Accessibility Integration

The text_range module is a critical component for accessibility support:

- **Screen Reader Support**: Provides text content to assistive technologies
- **Text Navigation**: Enables keyboard navigation for users with motor disabilities
- **Text Selection**: Supports programmatic text selection for automation tools
- **Bounding Rectangle Support**: Provides text positioning information (TODO: implementation)

## Future Enhancements

- **Bounding Rectangle Implementation**: Complete `GetBoundingRectangles()` method
- **Text Search**: Implement `FindText()` for text searching within ranges
- **Attribute Support**: Add text attribute support (font, color, style)
- **Multi-language Support**: Enhanced word boundary detection for complex scripts