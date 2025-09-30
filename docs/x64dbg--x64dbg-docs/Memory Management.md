# Memory Management Module

## Introduction

The Memory Management module is a core component of the x64dbg debugger that provides comprehensive memory analysis and manipulation capabilities for Windows processes. It handles memory page enumeration, memory reading/writing operations, heap analysis, and memory protection management. The module is specifically designed to work with modern Windows versions, including Windows 11 24H2+ with its updated heap structures.

## Core Functionality

### Memory Page Management
The module maintains a comprehensive map of all memory pages in the target process, providing detailed information about memory regions, their protection attributes, and associated modules or system structures.

### Memory Operations
Provides safe and unsafe memory read/write operations with automatic page boundary handling and error recovery mechanisms.

### Heap Analysis
Advanced heap enumeration capabilities, including support for Windows 11 24H2+ segment heap structures and process heap descriptors.

### Memory Protection
Comprehensive memory protection management with string-based rights conversion and validation.

## Architecture

```mermaid
graph TB
    subgraph "Memory Management Core"
        MM[Memory Manager]
        MP[Memory Pages]
        MO[Memory Operations]
        HA[Heap Analysis]
        MPV[Memory Protection]
    end
    
    subgraph "Windows 11 24H2+ Support"
        W11H[_WIN11_HEAP]
        W11PHD[_WIN11_PROCESS_HEAP_DESCRIPTOR]
        W11SH[_WIN11_SEGMENT_HEAP]
    end
    
    subgraph "External Dependencies"
        DBG[Debugger Engine]
        MOD[Module Management]
        THR[Thread Management]
        GUI[GUI Interface]
    end
    
    MM --> MP
    MM --> MO
    MM --> HA
    MM --> MPV
    
    HA --> W11H
    HA --> W11PHD
    HA --> W11SH
    
    MM --> DBG
    MM --> MOD
    MM --> THR
    MM --> GUI
```

## Component Relationships

```mermaid
graph LR
    subgraph "Memory Management Components"
        A[MemUpdateMap]
        B[QueryMemPages]
        C[ProcessFileSections]
        D[ProcessSystemPages]
        E[MemRead/MemWrite]
        F[Heap Enumeration]
    end
    
    A --> B
    A --> C
    A --> D
    
    B --> E
    C --> E
    D --> E
    
    D --> F
    
    E --> G[Memory Cache]
    F --> H[Heap Cache]
```

## Data Flow

```mermaid
sequenceDiagram
    participant GUI
    participant MM
    participant OS
    participant Cache
    
    GUI->>MM: Request memory map update
    MM->>OS: VirtualQueryEx for memory regions
    OS-->>MM: Memory information
    MM->>OS: Get module information
    OS-->>MM: Module details
    MM->>OS: Get thread information
    OS-->>MM: Thread/TEB details
    MM->>OS: Get heap information
    OS-->>MM: Heap descriptors
    MM->>Cache: Update memory pages
    MM->>GUI: Notify update complete
```

## Key Components

### Memory Page Enumeration
- **QueryMemPages()**: Enumerates all memory pages in the process address space
- **ProcessFileSections()**: Breaks down module pages into individual sections
- **ProcessSystemPages()**: Identifies system structures (PEB, TEB, heaps, stacks)

### Memory Operations
- **MemRead()**: Safe memory reading with caching and validation
- **MemWrite()**: Memory writing with page boundary handling
- **MemReadUnsafe()**: Direct memory access without safety checks
- **MemoryReadSafePage()**: Page-aligned safe reading with working set validation

### Heap Analysis (Windows 11 24H2+)
- **_WIN11_HEAP**: Structure for Windows 11 NT heap format
- **_WIN11_SEGMENT_HEAP**: Structure for Windows 11 segment heap format
- **_WIN11_PROCESS_HEAP_DESCRIPTOR**: Process heap descriptor chain

### Memory Protection
- **MemGetProtect()**: Retrieves memory protection attributes
- **MemSetProtect()**: Modifies memory protection
- **MemPageRightsToString()**: Converts protection flags to string format
- **MemPageRightsFromString()**: Parses string protection format

## Process Flow

```mermaid
flowchart TD
    A[Memory Map Update Request] --> B{Debugging Active?}
    B -->|Yes| C[Query Memory Pages]
    B -->|No| Z[Return Empty]
    
    C --> D[Process File Sections]
    D --> E[Process System Pages]
    E --> F[Update Memory Cache]
    F --> G[Notify GUI Update]
    
    subgraph "System Page Processing"
        E --> H[Identify PEB]
        E --> I[Identify TEBs]
        E --> J[Identify Stacks]
        E --> K[Identify Heaps]
        E --> L[Identify KUSER_SHARED_DATA]
    end
```

## Windows 11 24H2+ Heap Support

The module includes specialized support for Windows 11 24H2+ enhanced heap structures:

```mermaid
graph TD
    A[PEB ProcessHeaps] --> B{Windows 11 24H2+?}
    B -->|Yes| C[Check Segment Signature]
    C --> D{NT Heap or Segment Heap?}
    D -->|NT Heap| E[Read UserContext]
    D -->|Segment Heap| F[Read UserContext]
    E --> G[Traverse Heap Descriptor Chain]
    F --> G
    G --> H[Enumerate All Heaps]
```

## Integration with Other Modules

### Module Management Integration
- Uses [Module Management](Module%20Management.md) for section information
- Retrieves module base addresses and sizes
- Processes PE header information for proper section alignment

### Thread Management Integration
- Uses [Thread Management](Thread%20Management.md) for TEB and stack identification
- Correlates thread IDs with memory regions
- Handles both 32-bit and 64-bit thread contexts

### GUI Integration
- Notifies GUI components of memory map updates
- Provides progress information during memory searches
- Updates memory view displays

## Memory Safety Features

### Page Boundary Handling
All memory operations automatically handle page boundaries, ensuring that reads and writes don't cross page boundaries which could cause partial operations or errors.

### Working Set Validation
The module can validate memory pages against the working set to avoid accessing pages that are not currently resident in memory.

### Canonical Address Validation
Ensures that addresses are valid canonical addresses, particularly important for 64-bit processes.

### Error Recovery
Implements comprehensive error handling and recovery mechanisms, including fallback strategies for memory operations.

## Performance Optimizations

### Caching System
Maintains a comprehensive cache of memory page information to avoid repeated system calls and improve performance.

### Asynchronous Updates
Memory map updates can be performed asynchronously to avoid blocking the debugger interface.

### Section-Aware Processing
Processes memory at the section level for modules, providing more detailed and useful information while reducing overhead.

## Security Considerations

### Process Cookie Support
Implements pointer decoding using process cookies, essential for analyzing encoded pointers in modern Windows versions.

### Safe Memory Access
Provides both safe and unsafe memory access methods, allowing users to choose the appropriate level of safety for their use case.

### Protection Validation
Validates memory protection attributes before performing operations to ensure compliance with system security policies.

## Usage Examples

### Basic Memory Reading
```cpp
duint address = 0x00400000;
byte buffer[256];
duint bytesRead;
if(MemRead(address, buffer, sizeof(buffer), &bytesRead))
{
    // Process memory data
}
```

### Memory Page Information
```cpp
MEMPAGE pageInfo;
if(MemGetPageInfo(address, &pageInfo))
{
    // Access page protection, size, and other information
}
```

### Heap Enumeration
```cpp
// Heap information is automatically populated during memory map updates
// Access through the memory pages map
```

## Related Documentation

- [Module Management](Module%20Management.md) - For module and section information
- [Thread Management](Thread%20Management.md) - For thread and TEB information
- [Breakpoint System](Breakpoint%20System.md) - For memory breakpoint functionality
- [Symbol Resolution](Symbol%20Resolution.md) - For symbol information in memory regions