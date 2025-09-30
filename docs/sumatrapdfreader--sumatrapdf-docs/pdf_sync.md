# PDF Sync Module Documentation

## Introduction

The PDF Sync module provides bidirectional synchronization between PDF documents and their source files, enabling seamless navigation between compiled PDF output and the original LaTeX source code. This functionality is essential for LaTeX editors and PDF viewers that support forward and inverse search operations.

The module implements two synchronization protocols:
- **PDFSync**: Legacy synchronization based on `.pdfsync` files
- **SyncTeX**: Modern synchronization based on `.synctex` files (compressed or uncompressed)

## Architecture Overview

```mermaid
graph TB
    subgraph "PDF Sync Module"
        Synchronizer["Synchronizer<br/><i>Abstract Base Class</i>"]
        Pdfsync["Pdfsync<br/><i>Legacy Implementation</i>"]
        SyncTex["SyncTex<br/><i>Modern Implementation</i>"]
        
        Synchronizer --> Pdfsync
        Synchronizer --> SyncTex
    end
    
    subgraph "External Dependencies"
        EngineBase["EngineBase"]
        synctex_parser["synctex_parser.h"]
        FileUtil["File Utilities"]
        ZipUtil["Zip Utilities"]
    end
    
    Pdfsync -.-> EngineBase
    SyncTex -.-> synctex_parser
    Pdfsync -.-> FileUtil
    SyncTex -.-> FileUtil
    SyncTex -.-> ZipUtil
    
    subgraph "Data Structures"
        PdfsyncLine["PdfsyncLine"]
        PdfsyncPoint["PdfsyncPoint"]
        PdfsyncFileIndex["PdfsyncFileIndex"]
    end
    
    Pdfsync -.-> PdfsyncLine
    Pdfsync -.-> PdfsyncPoint
    Pdfsync -.-> PdfsyncFileIndex
```

## Core Components

### Synchronizer (Abstract Base Class)

The `Synchronizer` class serves as the abstract base for all synchronization implementations, providing common functionality for file management and timestamp checking.

**Key Responsibilities:**
- File path management and directory resolution
- Timestamp-based change detection
- Index rebuilding coordination
- Common utility functions

**Core Methods:**
- `Create()`: Factory method for creating appropriate synchronizer instances
- `NeedsToRebuildIndex()`: Determines if synchronization data needs refreshing
- `PrependDir()`: Resolves relative file paths to absolute paths

### Pdfsync Implementation

The `Pdfsync` class implements synchronization using the legacy PDFSync format, which generates `.pdfsync` files during LaTeX compilation.

**Key Features:**
- Custom binary format parsing
- Coordinate system transformation
- Multi-file source support
- Record-based mapping system

**Data Structures:**
- `PdfsyncLine`: Maps source file locations to synchronization records
- `PdfsyncPoint`: Maps PDF coordinates to synchronization records
- `PdfsyncFileIndex`: Indexes line mappings by source file

### SyncTex Implementation

The `SyncTex` class implements modern synchronization using the SyncTeX format, which is now the standard for LaTeX synchronization.

**Key Features:**
- Integration with `synctex_parser` library
- Compressed file support (`.synctex.gz`)
- UTF-8 and ANSI encoding support
- Robust error handling and logging

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant User
    participant PDFViewer
    participant Synchronizer
    participant SyncFile
    participant SourceEditor
    
    %% Forward Search (Source to PDF)
    User->>SourceEditor: Click "Go to PDF"
    SourceEditor->>Synchronizer: SourceToDoc(filename, line, col)
    Synchronizer->>SyncFile: Read synchronization data
    Synchronizer->>Synchronizer: Map source to PDF coordinates
    Synchronizer->>PDFViewer: Return page and rectangles
    PDFViewer->>User: Highlight PDF location
    
    %% Inverse Search (PDF to Source)
    User->>PDFViewer: Double-click PDF
    PDFViewer->>Synchronizer: DocToSource(page, point)
    Synchronizer->>SyncFile: Read synchronization data
    Synchronizer->>Synchronizer: Map PDF to source coordinates
    Synchronizer->>SourceEditor: Return filename, line, col
    SourceEditor->>User: Jump to source location
```

## Synchronization Process Flow

```mermaid
flowchart TD
    Start([Synchronization Request])
    
    subgraph "File Detection"
        A{Check for .synctex}
        B{Check for .synctex.gz}
        C{Check for .pdfsync}
    end
    
    subgraph "Synchronizer Creation"
        D[Create SyncTex]
        E[Create Pdfsync]
        F[Return Error]
    end
    
    subgraph "Index Building"
        G{Needs Rebuild?}
        H[Parse Sync File]
        I[Build Index]
        J[Update Timestamp]
    end
    
    Start --> A
    A -->|Found| D
    A -->|Not Found| B
    B -->|Found| D
    B -->|Not Found| C
    C -->|Found| E
    C -->|Not Found| F
    
    D --> G
    E --> G
    
    G -->|Yes| H
    G -->|No| K[Process Request]
    H --> I
    I --> J
    J --> K
    
    K --> L{Forward or Inverse?}
    L -->|Forward| M[Map Source to PDF]
    L -->|Inverse| N[Map PDF to Source]
    
    M --> O[Return PDF Coordinates]
    N --> P[Return Source Location]
```

## Coordinate System Handling

The module handles coordinate system transformations between PDF and source file coordinates:

```mermaid
graph LR
    subgraph "Source Coordinates"
        LineNo["Line Number"]
        ColNo["Column Number"]
        FileName["File Name"]
    end
    
    subgraph "Synchronization Records"
        RecordID["Record ID"]
        SyncCoord["Sync Coordinates"]
    end
    
    subgraph "PDF Coordinates"
        PageNo["Page Number"]
        XCoord["X Position"]
        YCoord["Y Position"]
    end
    
    LineNo --> RecordID
    ColNo --> RecordID
    FileName --> RecordID
    
    RecordID --> SyncCoord
    SyncCoord --> PageNo
    SyncCoord --> XCoord
    SyncCoord --> YCoord
    
    style RecordID fill:#f9f,stroke:#333,stroke-width:4px
```

## Error Handling and Recovery

The module implements comprehensive error handling for various synchronization scenarios:

**Error Codes:**
- `PDFSYNCERR_SUCCESS`: Operation completed successfully
- `PDFSYNCERR_INVALID_ARGUMENT`: Invalid parameters provided
- `PDFSYNCERR_SYNCFILE_NOTFOUND`: No synchronization file found
- `PDFSYNCERR_SYNCFILE_CANNOT_BE_OPENED`: Cannot read synchronization file
- `PDFSYNCERR_OUTOFMEMORY`: Memory allocation failed
- `PDFSYNCERR_INVALID_PAGE_NUMBER`: Invalid page number specified
- `PDFSYNCERR_NO_SYNC_AT_LOCATION`: No synchronization data at location
- `PDFSYNCERR_UNKNOWN_SOURCEFILE`: Source file not found in index
- `PDFSYNCERR_NORECORD_IN_SOURCEFILE`: No records for source file
- `PDFSYNCERR_NORECORD_FOR_THATLINE`: No records for specified line
- `PDFSYNCERR_NOSYNCPOINT_FOR_LINERECORD`: No PDF points for line record

## Integration with Document Engine

The synchronization module integrates with the document engine through the `EngineBase` interface:

```mermaid
classDiagram
    class Synchronizer {
        <<abstract>>
        +syncFilePath: char*
        +syncfileTimestamp: _stat
        +Create(path, engine, sync): int
        +NeedsToRebuildIndex(): bool
        +PrependDir(filename): char*
    }
    
    class Pdfsync {
        -engine: EngineBase*
        -srcfiles: StrVec
        -lines: Vec~PdfsyncLine~
        -points: Vec~PdfsyncPoint~
        -fileIndex: Vec~PdfsyncFileIndex~
        -sheetIndex: Vec~size_t~
        +DocToSource(pageNo, pt, filename, line, col): int
        +SourceToDoc(srcfilename, line, col, page, rects): int
    }
    
    class SyncTex {
        -engine: EngineBase*
        -scanner: synctex_scanner_p
        +DocToSource(pageNo, pt, filename, line, col): int
        +SourceToDoc(srcfilename, line, col, page, rects): int
    }
    
    class EngineBase {
        <<interface>>
        +PageCount(): int
        +PageMediabox(pageNo): RectF
    }
    
    Synchronizer <|-- Pdfsync
    Synchronizer <|-- SyncTex
    Pdfsync ..> EngineBase : uses
    SyncTex ..> EngineBase : uses
```

## File Format Support

### PDFSync Format (.pdfsync)
- Legacy format used by older LaTeX distributions
- Custom binary format with specific parsing rules
- Supports multiple source files
- Coordinate system: 65781.76 units per PDF unit

### SyncTeX Format (.synctex/.synctex.gz)
- Modern standard format
- Compressed and uncompressed variants
- UTF-8 encoding support
- More accurate synchronization data
- Better error handling

## Performance Considerations

**Index Rebuilding:**
- Automatic detection of file changes via timestamp monitoring
- Lazy loading of synchronization data
- Efficient binary search for record lookup

**Memory Management:**
- Dynamic allocation of synchronization structures
- Automatic cleanup of temporary files
- Memory-efficient storage of coordinate mappings

**Coordinate Transformation:**
- Optimized coordinate conversion algorithms
- Caching of page media box information
- Efficient distance calculations for nearest-point searches

## Usage Examples

### Creating a Synchronizer
```cpp
Synchronizer* sync = nullptr;
int result = Synchronizer::Create(pdfPath, engine, &sync);
if (result == PDFSYNCERR_SUCCESS) {
    // Use synchronizer
    // ...
    delete sync;
}
```

### Forward Search (Source to PDF)
```cpp
int page;
Vec<Rect> rects;
int result = sync->SourceToDoc("main.tex", 42, 0, &page, rects);
if (result == PDFSYNCERR_SUCCESS) {
    // Highlight rectangles on page
    // ...
}
```

### Inverse Search (PDF to Source)
```cpp
AutoFreeStr filename;
int line, col;
Point pt = { 100, 200 };
int result = sync->DocToSource(1, pt, filename, &line, &col);
if (result == PDFSYNCERR_SUCCESS) {
    // Open filename at line, col
    // ...
}
```

## Dependencies

The PDF Sync module depends on several other system components:

- **[EngineBase](engine_base.md)**: Document engine interface for page information
- **[File Utilities](file_util.md)**: File I/O operations
- **[Zip Utilities](zip_util.md)**: Compressed file handling
- **[String Utilities](str_util.md)**: String manipulation and encoding
- **[Path Utilities](path_util.md)**: Path resolution and manipulation

## Related Modules

- **[Document Formats](document_formats.md)**: Parent module containing PDF sync functionality
- **[MuPDF Integration](mupdf_java_bindings.md)**: PDF rendering engine integration
- **[UI Components](ui_components.md)**: User interface for synchronization features

## Future Enhancements

Potential improvements to the PDF Sync module include:

1. **Performance Optimization**: Implement caching mechanisms for frequently accessed synchronization data
2. **Format Extensions**: Support for additional synchronization formats
3. **Error Recovery**: Enhanced error recovery mechanisms for corrupted sync files
4. **Multi-Document Support**: Synchronization across multiple PDF documents
5. **Real-time Updates**: Live synchronization updates during document editing