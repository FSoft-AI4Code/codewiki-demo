# DynAPI Module Documentation

## Introduction

The DynAPI module is a critical component of the SDL (Simple DirectMedia Layer) library that manages the dynamic API jump table system. This module automatically generates and maintains the dynamic API infrastructure that allows SDL to provide runtime API resolution and compatibility across different platforms and configurations.

The module's primary purpose is to parse SDL header files, extract public API function declarations, and automatically update the dynamic API jump table files. This ensures that when new public APIs are added to SDL, they are properly integrated into the dynamic API system without manual intervention.

## Architecture Overview

```mermaid
graph TB
    subgraph "DynAPI Module Architecture"
        A[Header Parser] --> B[Procedure Analyzer]
        B --> C[API Validator]
        C --> D[Code Generator]
        D --> E[File Updater]
        
        F[SDL Headers] --> A
        G[Existing API Files] --> C
        D --> H[SDL_dynapi_procs.h]
        D --> I[SDL_dynapi_overrides.h]
        D --> J[SDL_dynapi.sym]
        
        K[Documentation Checker] --> L[Validation Reports]
    end
```

## Core Components

### SdlProcedure Class

The `SdlProcedure` class is a dataclass that represents a single SDL API function with all its metadata:

```mermaid
classDiagram
    class SdlProcedure {
        +str retval
        +str name
        +list parameter
        +list parameter_name
        +str header
        +str comment
        +bool variadic()
    }
```

**Properties:**
- `retval`: The return value type of the function
- `name`: The function name
- `parameter`: List of parameter types with anonymized parameter names
- `parameter_name`: List of actual parameter names
- `header`: The header file where the function is declared
- `comment`: The documentation comment associated with the function

**Methods:**
- `variadic()`: Returns true if the function has variadic parameters (contains "...")

### CallOnce Class

The `CallOnce` class is a utility that ensures a callback function is executed only once, regardless of how many times it's called:

```mermaid
classDiagram
    class CallOnce {
        -function _cb
        -bool _called
        +__init__(cb)
        +__call__(*args, **kwargs)
    }
```

**Purpose:**
- Prevents duplicate execution of initialization or warning functions
- Used in documentation checking to ensure warning headers are printed only once

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant Main as Main Process
    participant Parser as Header Parser
    participant Analyzer as Procedure Analyzer
    participant Validator as API Validator
    participant Generator as Code Generator
    participant Files as API Files
    
    Main->>Parser: Parse SDL headers
    Parser->>Parser: parse_header()
    Parser-->>Main: Return procedures
    Main->>Validator: Check existing APIs
    Validator->>Files: find_existing_proc_names()
    Files-->>Validator: Existing functions
    Validator-->>Main: Return existing names
    Main->>Generator: Generate new APIs
    Generator->>Files: Update API files
    Main->>Validator: Check documentation
    Validator-->>Main: Validation results
```

## Processing Pipeline

### 1. Header Parsing Phase

```mermaid
flowchart TD
    A[Start Header Parsing] --> B[Read Header File]
    B --> C{Contains extern & SDLCALL?}
    C -->|Yes| D[Extract Function Prototype]
    C -->|No| E[Skip Line]
    D --> F[Parse Return Type]
    F --> G[Parse Function Name]
    G --> H[Parse Parameters]
    H --> I[Handle Special Cases]
    I --> J[Create SdlProcedure]
    J --> K[Add to Procedure List]
    K --> B
    E --> B
```

**Special Cases Handled:**
- Variadic functions (printf-style functions)
- Function pointer parameters (callbacks)
- Array parameters
- Platform-specific attributes and macros
- Comment blocks and documentation

### 2. API Generation Phase

```mermaid
flowchart LR
    A[New Procedure] --> B{Variadic?}
    B -->|Yes| C[Add #ifndef Guard]
    B -->|No| D[Direct Generation]
    C --> E[Generate SDL_DYNAPI_PROC]
    D --> E
    E --> F[Update SDL_dynapi_procs.h]
    E --> G[Update SDL_dynapi_overrides.h]
    E --> H[Update SDL_dynapi.sym]
```

### 3. Documentation Validation Phase

```mermaid
flowchart TD
    A[Validate Documentation] --> B[Check param Count]
    B --> C{Matches Parameter Count?}
    C -->|No| D[Log Warning]
    C -->|Yes| E[Check Parameter Names]
    E --> F{All Parameters Documented?}
    F -->|No| G[Log Missing param]
    F -->|Yes| H[Check returns]
    H --> I{Return Type Documented?}
    I -->|No| J[Log Missing returns]
    I -->|Yes| K[Check since]
    K --> L{Version Documented?}
    L -->|No| M[Log Missing since]
```

## File Structure and Dependencies

```mermaid
graph TB
    subgraph "Input Files"
        A[SDL Headers/*.h]
        B[SDL_dynapi_procs.h]
    end
    
    subgraph "DynAPI Module"
        C[gendynapi.py]
        D[SdlProcedure]
        E[CallOnce]
    end
    
    subgraph "Output Files"
        F[SDL_dynapi_procs.h]
        G[SDL_dynapi_overrides.h]
        H[SDL_dynapi.sym]
        I[sdl.json - Optional]
    end
    
    A --> C
    B --> C
    C --> D
    C --> E
    C --> F
    C --> G
    C --> H
    C --> I
```

## Integration with SDL Build System

The DynAPI module integrates with the SDL build system in several ways:

1. **Automatic API Discovery**: Scans all SDL header files in `include/SDL3/`
2. **Dynamic API Maintenance**: Updates three critical files that enable SDL's dynamic API system
3. **Build Validation**: Ensures all public APIs are properly documented and follow SDL conventions
4. **Version Control Integration**: Designed to be run during development and committed with new API additions

## Usage Workflow

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant Script as gendynapi.py
    participant Git as Git
    participant Build as Build System
    
    Dev->>Dev: Add new SDL API
    Dev->>Script: Run gendynapi.py
    Script->>Script: Parse headers
    Script->>Script: Generate API files
    Script->>Dev: Show new APIs found
    Dev->>Git: git diff (review changes)
    Dev->>Git: Commit changes
    Build->>Build: Build SDL with new API
```

## Command Line Interface

The script supports several command-line options:

```bash
# Basic usage - update API files
./gendynapi.py

# Debug mode - show detailed parsing information
./gendynapi.py --debug

# Dump complete API to JSON file
./gendynapi.py --dump api.json

# Dump to default file (sdl.json)
./gendynapi.py --dump
```

## Error Handling and Validation

The module implements comprehensive error handling:

1. **Parsing Errors**: Validates function prototypes and provides detailed error messages
2. **Documentation Warnings**: Checks for missing or incorrect documentation tags
3. **File System Errors**: Handles missing files and permission issues
4. **API Consistency**: Ensures API declarations match across all generated files

## Performance Considerations

- **Efficient Parsing**: Uses compiled regular expressions for performance
- **Memory Management**: Processes files line-by-line to handle large headers
- **Incremental Updates**: Only processes new APIs, preserving existing entries
- **Reproducible Output**: Sorts headers and procedures for consistent results

## Relationship to Other Modules

The DynAPI module has dependencies and relationships with several other SDL modules:

- **[hid_api_module](hid_api_module.md)**: Manages HID device APIs that are processed by DynAPI
- **[android_hid_module](android_hid_module.md)**: Android-specific HID implementations included in dynamic API
- **[android_sdl_core_module](android_sdl_core_module.md)**: Core SDL functionality that relies on dynamic API
- **[gameinput_module](gameinput_module.md)**: Game input APIs that need dynamic resolution

## Maintenance and Development

When adding new SDL APIs, developers should:

1. Add the API declaration to the appropriate header file
2. Run `gendynapi.py` to update the dynamic API files
3. Review the changes with `git diff`
4. Commit the updated API files along with the new API
5. Ensure proper documentation with `\param`, `\returns`, and `\since` tags

The module is designed to be maintenance-free for routine API additions while providing comprehensive validation and error reporting for edge cases and documentation issues.