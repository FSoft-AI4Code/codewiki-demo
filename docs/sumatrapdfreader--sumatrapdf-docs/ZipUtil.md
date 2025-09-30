# ZipUtil Module Documentation

## Introduction

The ZipUtil module provides ZIP archive creation and compression functionality for the SumatraPDF application. It offers a high-level interface for creating ZIP files from directories, individual files, or raw data, with built-in compression support using the zlib library.

## Architecture Overview

The ZipUtil module is built around a core `ZipCreator` class that handles the low-level details of ZIP file format creation, compression, and streaming. The module integrates with Windows COM interfaces for stream-based operations and uses zlib for data compression.

```mermaid
graph TB
    subgraph "ZipUtil Module Architecture"
        ZC[ZipCreator]
        FWS[FileWriteStream]
        ZC --> FWS
        
        subgraph "External Dependencies"
            ZLIB[zlib library]
            UNARR[unarr library]
            COM[Windows COM]
        end
        
        FWS --> COM
        ZC --> ZLIB
    end
    
    subgraph "Related Modules"
        FU[FileUtil]
        DU[DirIter]
        SW[ScopedWin]
        BW[ByteWriter]
        FU --> ZC
        DU --> ZC
        SW --> FWS
        BW --> ZC
    end
```

## Core Components

### FileWriteStream Class

The `FileWriteStream` class implements the Windows `ISequentialStream` interface to provide COM-compatible stream writing capabilities. It handles file creation, writing operations, and reference counting for memory management.

**Key Features:**
- Implements IUnknown interface for COM compatibility
- Provides thread-safe reference counting
- Handles Windows file operations through CreateFileW API
- Supports sequential write operations only (Read returns E_NOTIMPL)

### ZipCreator Class

The main class responsible for creating ZIP archives. It supports multiple input sources and handles the complete ZIP file format lifecycle.

**Key Features:**
- Stream-based architecture supporting both file and memory streams
- Automatic compression using zlib with fallback to store method
- Support for UTF-8 filenames
- DOS date/time preservation
- Central directory management

## Data Flow

```mermaid
sequenceDiagram
    participant Client
    participant ZipCreator
    participant FileWriteStream
    participant zlib
    participant FileSystem
    
    Client->>ZipCreator: Create(zipFilePath)
    ZipCreator->>FileWriteStream: new FileWriteStream(path)
    FileWriteStream->>FileSystem: CreateFileW()
    
    Client->>ZipCreator: AddFile(path, nameInZip)
    ZipCreator->>FileSystem: ReadFile()
    ZipCreator->>zlib: zip_compress()
    ZipCreator->>FileWriteStream: Write(localHeader)
    ZipCreator->>FileWriteStream: Write(compressedData)
    
    Client->>ZipCreator: Finish()
    ZipCreator->>FileWriteStream: Write(centralDirectory)
    ZipCreator->>FileWriteStream: Write(EOCD)
    
    Client->>ZipCreator: ~ZipCreator()
    ZipCreator->>FileWriteStream: Release()
    FileWriteStream->>FileSystem: CloseHandle()
```

## Component Interactions

```mermaid
graph LR
    subgraph "ZipUtil Internal Flow"
        A[AddFile/AddFileData] --> B[Compression]
        B --> C[Local Header Write]
        C --> D[Data Write]
        D --> E[Central Directory Entry]
        
        F[Finish] --> G[Write Central Directory]
        G --> H[Write EOCD]
    end
    
    subgraph "Compression Logic"
        B --> I{Compression Success?}
        I -->|Yes| J[Use Compressed Data]
        I -->|No| K[Use Store Method]
    end
```

## Key Functions and Methods

### ZipCreator Methods

- **AddFileData()**: Core method for adding file data with compression
- **AddFile()**: High-level method to add files from filesystem
- **AddFileFromDir()**: Adds files with relative path preservation
- **AddDir()**: Recursively adds entire directories
- **Finish()**: Completes ZIP creation by writing central directory

### Utility Functions

- **zip_compress()**: Custom compression function using zlib with DEFLATED method
- **Ungzip()**: Decompresses gzip-compressed data with memory management
- **OpenDirAsZipStream()**: Creates an IStream containing a directory as a ZIP

## Process Flow

### ZIP Creation Process

```mermaid
flowchart TD
    Start([Start]) --> Init[Initialize ZipCreator]
    Init --> AddFiles{Add Files?}
    
    AddFiles -->|Single File| AddFile[AddFile]
    AddFiles -->|Directory| AddDir[AddDir]
    AddFiles -->|Raw Data| AddFileData[AddFileData]
    
    AddFile --> ReadFile[Read File Content]
    AddDir --> Iterate[Iterate Directory]
    AddFileData --> Compress[Compress Data]
    
    ReadFile --> Compress
    Iterate --> AddFileFromDir
    AddFileFromDir --> ReadFile
    
    Compress --> WriteLocal[Write Local Header]
    WriteLocal --> WriteData[Write Compressed Data]
    WriteData --> UpdateCentral[Update Central Directory]
    
    UpdateCentral --> MoreFiles{More Files?}
    MoreFiles -->|Yes| AddFiles
    MoreFiles -->|No| Finish[Finish]
    
    Finish --> WriteCentral[Write Central Directory]
    WriteCentral --> WriteEOCD[Write EOCD Record]
    WriteEOCD --> Complete([Complete])
```

### Compression Decision Logic

```mermaid
flowchart LR
    Start([Data to Compress]) --> TryCompress[Attempt Compression]
    TryCompress --> Success{Compression Successful?}
    
    Success -->|Yes| UseCompressed[Use Compressed Data
    Method: Z_DEFLATED]
    Success -->|No| UseStored[Use Stored Data
    Method: Store]
    
    UseCompressed --> WriteFile[Write to ZIP]
    UseStored --> WriteFile
    WriteFile --> End([End])
```

## Dependencies

### Internal Dependencies
- **FileUtil**: For file reading and timestamp operations
- **DirIter**: For directory traversal
- **ByteWriter**: For structured binary data writing
- **ScopedWin**: For Windows handle management

### External Dependencies
- **zlib**: For compression and decompression operations
- **unarr**: For archive handling (header inclusion)
- **Windows COM**: For stream interfaces

## Integration with System

The ZipUtil module integrates with the broader SumatraPDF system through:

1. **File Operations**: Uses FileUtil for reading files and getting modification times
2. **Directory Handling**: Leverages DirIter for recursive directory processing
3. **Memory Management**: Utilizes the application's memory allocation functions
4. **String Handling**: Uses the application's string utilities for path manipulation

## Error Handling

The module implements several error handling strategies:

- **File Operation Errors**: Returns false on file read/write failures
- **Memory Allocation**: Checks for allocation failures and returns empty results
- **Compression Errors**: Falls back to store method if compression fails
- **Size Limits**: Validates against ZIP format size constraints (UINT32_MAX, UINT16_MAX)

## Performance Considerations

- **Memory Usage**: Uses temporary buffers for compression with automatic growth
- **Stream-Based**: Supports large files through streaming without loading entirely into memory
- **Compression Ratio**: Automatically determines optimal compression method
- **Reference Counting**: Proper COM object lifecycle management

## Related Documentation

- [FileUtil Module](FileUtil.md) - File operations and utilities
- [DirIter Module](DirIter.md) - Directory iteration functionality
- [ByteWriter Module](ByteWriter.md) - Binary data writing utilities
- [ScopedWin Module](ScopedWin.md) - Windows resource management