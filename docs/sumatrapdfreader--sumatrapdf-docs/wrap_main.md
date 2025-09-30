# wrap_main Module Documentation

## Overview

The `wrap_main` module is the core entry point and orchestrator for the MuPDF wrapper generation system. It serves as the main command-line interface for building C++, Python, and C# language bindings for the MuPDF library, providing a comprehensive wrapper generation framework that transforms the native C API into higher-level, object-oriented interfaces.

## Purpose and Core Functionality

The primary purpose of the `wrap_main` module is to:

1. **Generate Language Bindings**: Create C++, Python, and C# wrappers for the MuPDF C API
2. **Automate Build Processes**: Orchestrate the complex build pipeline involving multiple tools (Clang, SWIG, compilers)
3. **Provide Cross-Platform Support**: Handle platform-specific build requirements for Windows, Linux, and macOS
4. **Manage Dependencies**: Coordinate between different MuPDF components and external tools
5. **Enable Testing**: Provide comprehensive testing capabilities for generated bindings

## Architecture and Component Relationships

### High-Level Architecture

```mermaid
graph TB
    subgraph "wrap_main Module"
        WM[wrap_main.py<br/>Main Entry Point]
        FI[FzItem<br/>Function Analysis]
        EN[encoder<br/>JSON Serialization]
    end
    
    subgraph "Supporting Modules"
        JLIB[jlib<br/>Utility Functions]
        PARSE[parse<br/>Clang AST Parsing]
        CPP[cpp<br/>C++ Code Generation]
        SWIG[swig<br/>SWIG Interface Generation]
        STATE[state<br/>Build State Management]
    end
    
    subgraph "External Tools"
        CLANG[Clang Python<br/>AST Parsing]
        SWIG_TOOL[SWIG<br/>Binding Generation]
        COMPILER[Compiler<br/>C++/C# Compilation]
    end
    
    subgraph "MuPDF Core"
        MUPDF[MuPDF C API<br/>Headers & Libraries]
        DOCUMENTATION[Generated Documentation<br/>Doxygen/Pydoc]
    end
    
    WM --> JLIB
    WM --> PARSE
    WM --> CPP
    WM --> SWIG
    WM --> STATE
    
    PARSE --> CLANG
    SWIG --> SWIG_TOOL
    CPP --> COMPILER
    
    WM --> MUPDF
    WM --> DOCUMENTATION
    
    FI --> PARSE
    EN --> JLIB
```

### Build Process Flow

```mermaid
sequenceDiagram
    participant User
    participant wrap_main
    participant parse
    participant cpp
    participant swig
    participant compiler
    
    User->>wrap_main: Command line arguments
    wrap_main->>parse: Parse MuPDF headers
    parse->>wrap_main: AST information
    wrap_main->>cpp: Generate C++ wrappers
    cpp->>compiler: Compile C++ code
    compiler->>wrap_main: libmupdfcpp.so
    wrap_main->>swig: Generate SWIG interfaces
    swig->>compiler: Compile Python/C# bindings
    compiler->>wrap_main: _mupdf.so / mupdfcsharp.dll
    wrap_main->>User: Test and documentation
```

## Core Components

### FzItem Class

The `FzItem` class represents a MuPDF function or structure element for analysis and wrapper generation.

```mermaid
classDiagram
    class FzItem {
        +type_: str
        +uses_structs: bool
        +__init__(type_, uses_structs)
    }
    
    FzItem --> FunctionAnalysis : used in
    FzItem --> WrapperGeneration : input for
```

**Purpose**: Encapsulates information about MuPDF API elements during the parsing phase

**Key Attributes**:
- `type_`: Specifies whether the item is a 'function' or other type
- `uses_structs`: Boolean indicating if the function uses MuPDF structures

### encoder Class

The `encoder` class provides JSON serialization capabilities for wrapper configuration data.

```mermaid
classDiagram
    class encoder {
        +default(obj)
        +JSON serialization
    }
    
    encoder --> ConfigurationExport : used for
    encoder --> ClassExtras : serializes
```

**Purpose**: Handles serialization of complex wrapper configuration objects to JSON format

**Key Features**:
- Custom serialization for Extra* and ClassExtra* objects
- Handles callable objects and complex data structures
- Used for debugging and configuration persistence

## Build System Integration

### Module Dependencies

```mermaid
graph LR
    wrap_main --> jlib
    wrap_main --> classes
    wrap_main --> cpp
    wrap_main --> parse
    wrap_main --> state
    wrap_main --> swig
    
    jlib --> UtilityFunctions
    classes --> ClassConfiguration
    cpp --> CppGeneration
    parse --> ASTParsing
    state --> BuildState
    swig --> BindingGeneration
```

### Platform-Specific Build Process

```mermaid
graph TD
    A[Build Command] --> B{Platform Check}
    
    B -->|Windows| C[Visual Studio Build]
    B -->|Linux| D[GNU Make Build]
    B -->|macOS| E[Clang Build]
    
    C --> F[devenv.com]
    C --> G[mupdf.sln]
    
    D --> H[make -j]
    D --> I[libmupdf.so]
    
    E --> J[clang++]
    E --> K[libmupdf.dylib]
    
    F --> L[mupdfcpp.dll]
    H --> M[libmupdfcpp.so]
    J --> N[libmupdfcpp.dylib]
```

## Command-Line Interface

### Primary Build Actions

The module supports a comprehensive set of build actions through the `-b` flag:

```mermaid
graph LR
    A[-b flag] --> B[m - Build libmupdf.so]
    A --> C[0 - Generate C++ source]
    A --> D[1 - Compile C++ code]
    A --> E[2 - Generate SWIG interfaces]
    A --> F[3 - Compile bindings]
    
    B --> G[MuPDF Core Library]
    C --> H[C++ Wrappers]
    D --> I[libmupdfcpp.so]
    E --> J[SWIG .i files]
    F --> K[_mupdf.so / mupdfcsharp.dll]
```

### Configuration Options

```mermaid
graph TD
    A[Configuration] --> B[--dir-so <directory>]
    A --> C[--python / --csharp]
    A --> D[--regress]
    A --> E[--trace-if <condition>]
    A --> F[--refcheck-if <condition>]
    
    B --> G[Build Output Directory]
    C --> H[Language Selection]
    D --> I[Regression Testing]
    E --> J[Debug Tracing]
    F --> K[Reference Counting]
```

## Wrapper Generation Process

### C++ Wrapper Architecture

```mermaid
graph TB
    A[MuPDF C API] --> B[Clang AST Parsing]
    B --> C[Function Analysis]
    C --> D[Wrapper Class Generation]
    D --> E[Method Generation]
    E --> F[Memory Management]
    F --> G[C++ API]
    
    G --> H[Automatic Reference Counting]
    G --> I[Exception Handling]
    G --> J[Type Safety]
    G --> K[Object-Oriented Interface]
```

### Python Binding Generation

```mermaid
sequenceDiagram
    participant Cpp as CppWrappers
    participant SWIG as SWIGTool
    participant Python as PythonModule
    
    Cpp->>SWIG: .i interface files
    SWIG->>SWIG: Parse C++ API
    SWIG->>Python: Generate mupdf.py
    SWIG->>Python: Generate _mupdf.so source
    Note over Python: Out-parameter handling<br/>Buffer management<br/>Exception conversion
```

## Testing and Validation

### Test Infrastructure

```mermaid
graph LR
    A[Test System] --> B[--test-python]
    A --> C[--test-csharp]
    A --> D[--test-cpp]
    A --> E[--test-setup.py]
    
    B --> F[mupdfwrap_test.py]
    C --> G[C# Test Suite]
    D --> H[C++ Test Suite]
    E --> I[Virtual Environment Test]
```

### Quality Assurance

```mermaid
graph TD
    A[Quality Checks] --> B[Header Validation]
    A --> C[Regression Testing]
    A --> D[Reference Counting]
    A --> E[Memory Leak Detection]
    
    B --> F[--check-headers]
    C --> G[--regress flag]
    D --> H[MUPDF_check_refs]
    E --> I[Runtime Diagnostics]
```

## Documentation Generation

### Multi-Language Documentation

```mermaid
graph TB
    A[Documentation System] --> B[--doc c]
    A --> C[--doc c++]
    A --> D[--doc python]
    A --> E[--doc all]
    
    B --> F[Doxygen C API]
    C --> G[Doxygen C++ API]
    D --> H[Pydoc Python API]
    E --> I[Unified Documentation]
    
    I --> J[index.html]
    I --> K[Cross-references]
    I --> L[Usage Examples]
```

## Integration with MuPDF Ecosystem

### Related Module Dependencies

The `wrap_main` module integrates with several other modules in the MuPDF ecosystem:

- **[mupdf_java_bindings](mupdf_java_bindings.md)**: Provides Java language bindings using similar wrapper generation techniques. The Java bindings share the same underlying MuPDF C API but target a different language runtime.
- **[mupdf_wrap_scripts](mupdf_wrap_scripts.md)**: Contains supporting scripts and utilities for the wrapper generation process. The `jlib` module provides essential utility functions used throughout the build process.
- **[metadata](metadata.md)**: Handles metadata structures used in document processing. The wrapper generation process needs to understand these structures to create appropriate language bindings.
- **[gumbo_parser](gumbo_parser.md)**: HTML parsing capabilities for document processing. While not directly used in wrapper generation, it's part of the broader MuPDF processing pipeline.

### Data Flow Integration

```mermaid
graph LR
    A[MuPDF Core] --> B[wrap_main]
    B --> C[Language Bindings]
    
    C --> D[Python API]
    C --> E[C++ API]
    C --> F[C# API]
    
    D --> G[Application Layer]
    E --> G
    F --> G
    
    G --> H[Document Processing]
    G --> I[Rendering]
    G --> J[Content Extraction]
```

### Cross-Module Communication

```mermaid
graph TD
    A[wrap_main] -->|uses| B[jlib utilities]
    A -->|parses| C[MuPDF headers]
    A -->|generates| D[C++ wrappers]
    A -->|coordinates| E[SWIG processing]
    
    F[mupdf_java_bindings] -->|shares| C
    F -->|similar process| D
    
    G[metadata] -->|structure info| A
    H[gumbo_parser] -->|HTML processing| I[Document pipeline]
    
    style A fill:#f9f,stroke:#333,stroke-width:4px
```

## Technical Implementation Details

### Build Process State Machine

```mermaid
stateDiagram-v2
    [*] --> Initialization
    
    Initialization --> ArgumentParsing: Command line args
    ArgumentParsing --> PlatformDetection: Detect OS/Compiler
    PlatformDetection --> DependencyCheck: Check tools
    
    DependencyCheck --> BuildActionSelection: -b flag
    
    BuildActionSelection --> BuildMupdf: action 'm'
    BuildActionSelection --> GenerateCpp: action '0'
    BuildActionSelection --> CompileCpp: action '1'
    BuildActionSelection --> GenerateSwig: action '2'
    BuildActionSelection --> CompileBindings: action '3'
    
    BuildMupdf --> MakeCommand: Generate make command
    MakeCommand --> ExecuteMake: Run make
    ExecuteMake --> CheckLibmupdf: Verify libmupdf.so
    CheckLibmupdf --> [*]
    
    GenerateCpp --> ClangParse: Parse headers
    ClangParse --> AnalyzeAST: Extract functions
    AnalyzeAST --> GenerateWrappers: Create C++ code
    GenerateWrappers --> SaveGenerated: Write files
    SaveGenerated --> [*]
    
    CompileCpp --> SetupCompiler: Configure flags
    SetupCompiler --> CompileSource: Build .cpp files
    CompileSource --> LinkLibrary: Create libmupdfcpp.so
    LinkLibrary --> [*]
    
    GenerateSwig --> LoadGenerated: Load C++ info
    LoadGenerated --> GenerateInterface: Create .i files
    GenerateInterface --> RunSwig: Execute SWIG
    RunSwig --> GenerateBindings: Create language files
    GenerateBindings --> [*]
    
    CompileBindings --> SetupLanguage: Python/C#
    SetupLanguage --> CompileSwigOutput: Build SWIG code
    CompileSwigOutput --> LinkBinding: Create _mupdf.so
    LinkBinding --> [*]
```

### Memory Management Architecture

```mermaid
graph TB
    A[MuPDF C Objects] --> B[Reference Counting]
    B --> C[Automatic Management]
    
    C --> D[Wrapper Classes]
    D --> E[Constructor: fz_keep_*]
    D --> F[Destructor: fz_drop_*]
    D --> G[Copy: Reference increment]
    
    G --> H[Memory Safety]
    H --> I[No Double Free]
    H --> J[No Memory Leaks]
    H --> K[Thread Safety]
    
    style A fill:#ff9,stroke:#333,stroke-width:2px
    style H fill:#9f9,stroke:#333,stroke-width:2px
```

### Cross-Platform Build Strategy

```mermaid
graph TD
    A[Cross-Platform Build] --> B{Platform Detection}
    
    B -->|Windows| C[Visual Studio]
    B -->|Linux| D[GCC/Clang]
    B -->|macOS| E[Clang]
    B -->|Pyodide| F[Emscripten]
    
    C --> G[devenv.com]
    C --> H[.vcxproj files]
    C --> I[mupdfcpp.dll]
    
    D --> J[make -j]
    D --> K[Makefile]
    D --> L[libmupdfcpp.so]
    
    E --> M[clang++]
    E --> N[Darwin flags]
    E --> O[libmupdfcpp.dylib]
    
    F --> P[emcc/em++]
    F --> Q[WebAssembly]
    F --> R[.wasm modules]
    
    style B fill:#f9f,stroke:#333,stroke-width:4px
```

### Runtime Diagnostics

The module provides comprehensive diagnostic capabilities through environmental variables:

```mermaid
graph TD
    A[Diagnostics] --> B[MUPDF_trace]
    A --> C[MUPDF_trace_director]
    A --> D[MUPDF_trace_exceptions]
    A --> E[MUPDF_check_refs]
    
    B --> F[Function Call Tracing]
    C --> G[Director Tracing]
    D --> H[Exception Handling]
    E --> I[Reference Counting]
```

## Usage Examples and Best Practices

### Basic Build Commands

```bash
# Complete build for Python bindings
./scripts/mupdfwrap.py -b all

# Build with specific output directory
./scripts/mupdfwrap.py -d build/shared-debug -b all

# Build only C++ wrappers
./scripts/mupdfwrap.py -b 01

# Build only Python bindings
./scripts/mupdfwrap.py -b 23

# Force rebuild
./scripts/mupdfwrap.py -b all -f
```

### Advanced Configuration

```bash
# Build with regression testing
./scripts/mupdfwrap.py -b all --regress

# Build with custom trace conditions
./scripts/mupdfwrap.py -b all --trace-if '#if 1'

# Build with reference checking
./scripts/mupdfwrap.py -b all --refcheck-if '#ifndef NDEBUG'

# Parallel build with 8 cores
./scripts/mupdfwrap.py -b all -j 8
```

### Testing and Validation

```bash
# Test Python bindings
./scripts/mupdfwrap.py --test-python

# Test C# bindings
./scripts/mupdfwrap.py --test-csharp

# Test with specific PDF file
./scripts/mupdfwrap.py --test-python /path/to/test.pdf

# Generate documentation
./scripts/mupdfwrap.py --doc all
```

### Platform-Specific Examples

#### Windows
```cmd
# Build with Visual Studio
python scripts\mupdfwrap.py -b all

# Build with specific Python version
python scripts\mupdfwrap.py -d build/shared-release-x64-py3.9 -b all
```

#### Linux
```bash
# Standard build
./scripts/mupdfwrap.py -b all

# Debug build
./scripts/mupdfwrap.py -d build/shared-debug -b all
```

#### macOS
```bash
# Build with Apple Clang
./scripts/mupdfwrap.py -b all

# Build with specific architecture
ARCHFLAGS="-arch arm64" ./scripts/mupdfwrap.py -b all
```

### Best Practices

```mermaid
graph TD
    A[Best Practices] --> B[Development]
    A --> C[Production]
    A --> D[Debugging]
    
    B --> E[Use virtual environments]
    B --> F[Enable trace flags]
    B --> G[Run regression tests]
    
    C --> H[Use release builds]
    C --> I[Disable debug flags]
    C --> J[Optimize for performance]
    
    D --> K[Enable all trace flags]
    D --> L[Use reference checking]
    D --> M[Generate detailed logs]
```

### Troubleshooting Common Issues

```mermaid
graph TD
    A[Common Issues] --> B[Build Failures]
    A --> C[Import Errors]
    A --> D[Runtime Crashes]
    
    B --> E[Check dependencies]
    B --> F[Verify tool versions]
    B --> G[Clean rebuild]
    
    C --> H[Check LD_LIBRARY_PATH]
    C --> I[Verify Python path]
    C --> J[Check architecture match]
    
    D --> K[Enable trace flags]
    D --> L[Check reference counts]
    D --> M[Use debug build]
```

### Build Error Handling

```mermaid
graph LR
    A[Build Errors] --> B[Clang Parsing Errors]
    A --> C[SWIG Generation Errors]
    A --> D[Compilation Errors]
    A --> E[Linking Errors]
    
    B --> F[Detailed Logging]
    C --> G[Error Recovery]
    D --> H[Platform-Specific Handling]
    E --> I[Dependency Resolution]
```

## Performance Considerations

### Build Optimization

```mermaid
graph TB
    A[Performance] --> B[Parallel Building]
    A --> C[Incremental Compilation]
    A --> D[Cache Management]
    A --> E[Memory Optimization]
    
    B --> F[-j <N> flag]
    C --> G[File Timestamp Checking]
    D --> H[Generated Code Caching]
    E --> I[Resource Management]
```

### Runtime Performance

The generated wrappers include several performance optimizations:

- **Reference Counting**: Automatic memory management to prevent leaks
- **Inline Methods**: Critical methods are inlined for performance
- **Exception Optimization**: Efficient exception handling with minimal overhead
- **Buffer Management**: Optimized buffer handling for large documents

## Security Considerations

### Code Generation Security

```mermaid
graph LR
    A[Security] --> B[Input Validation]
    A --> C[Code Injection Prevention]
    A --> D[Memory Safety]
    A --> E[Access Control]
    
    B --> F[Header File Validation]
    C --> G[Safe Code Generation]
    D --> H[Buffer Overflow Protection]
    E --> I[API Access Control]
```

## Future Enhancements

### Planned Features

```mermaid
graph TD
    A[Future Enhancements] --> B[Additional Language Support]
    A --> C[Improved Documentation]
    A --> D[Performance Optimization]
    A --> E[Enhanced Testing]
    
    B --> F[JavaScript Bindings]
    B --> G[Rust Bindings]
    C --> H[Interactive Examples]
    D --> I[JIT Compilation]
    E --> J[Automated Testing]
```

## Conclusion

The `wrap_main` module serves as the central orchestrator for MuPDF's multi-language binding generation system. It provides a robust, extensible framework for creating high-quality language bindings that maintain the performance and functionality of the native MuPDF library while offering modern, object-oriented APIs for different programming languages.

The module's architecture demonstrates sophisticated software engineering practices, including modular design, comprehensive error handling, cross-platform compatibility, and extensive testing capabilities. Its integration with the broader MuPDF ecosystem makes it an essential component for developers seeking to leverage MuPDF's capabilities across different programming environments.

### Key Strengths

1. **Comprehensive Language Support**: Generates bindings for C++, Python, and C# with consistent APIs
2. **Cross-Platform Compatibility**: Supports Windows, Linux, macOS, and WebAssembly builds
3. **Automated Memory Management**: Implements reference counting and automatic cleanup
4. **Extensive Testing**: Provides comprehensive testing and validation capabilities
5. **Documentation Generation**: Automatically generates API documentation for all supported languages
6. **Performance Optimization**: Includes numerous optimizations for runtime performance

### Integration Benefits

The `wrap_main` module seamlessly integrates with other MuPDF components:

- **Shared Core**: Uses the same MuPDF C API as other language bindings
- **Consistent Interface**: Provides uniform APIs across different programming languages
- **Documentation Consistency**: Generates coordinated documentation across all bindings
- **Testing Coordination**: Ensures consistent behavior across language implementations

This comprehensive approach makes MuPDF accessible to developers regardless of their preferred programming language while maintaining the high performance and reliability of the underlying C library.

### Build Optimization

```mermaid
graph TB
    A[Performance] --> B[Parallel Building]
    A --> C[Incremental Compilation]
    A --> D[Cache Management]
    A --> E[Memory Optimization]
    
    B --> F[-j <N> flag]
    C --> G[File Timestamp Checking]
    D --> H[Generated Code Caching]
    E --> I[Resource Management]
```

### Runtime Performance

The generated wrappers include several performance optimizations:

- **Reference Counting**: Automatic memory management to prevent leaks
- **Inline Methods**: Critical methods are inlined for performance
- **Exception Optimization**: Efficient exception handling with minimal overhead
- **Buffer Management**: Optimized buffer handling for large documents

## Security Considerations

### Code Generation Security

```mermaid
graph LR
    A[Security] --> B[Input Validation]
    A --> C[Code Injection Prevention]
    A --> D[Memory Safety]
    A --> E[Access Control]
    
    B --> F[Header File Validation]
    C --> G[Safe Code Generation]
    D --> H[Buffer Overflow Protection]
    E --> I[API Access Control]
```

## Future Enhancements

### Planned Features

```mermaid
graph TD
    A[Future Enhancements] --> B[Additional Language Support]
    A --> C[Improved Documentation]
    A --> D[Performance Optimization]
    A --> E[Enhanced Testing]
    
    B --> F[JavaScript Bindings]
    B --> G[Rust Bindings]
    C --> H[Interactive Examples]
    D --> I[JIT Compilation]
    E --> J[Automated Testing]
```

## Conclusion

The `wrap_main` module serves as the central orchestrator for MuPDF's multi-language binding generation system. It provides a robust, extensible framework for creating high-quality language bindings that maintain the performance and functionality of the native MuPDF library while offering modern, object-oriented APIs for different programming languages.

The module's architecture demonstrates sophisticated software engineering practices, including modular design, comprehensive error handling, cross-platform compatibility, and extensive testing capabilities. Its integration with the broader MuPDF ecosystem makes it an essential component for developers seeking to leverage MuPDF's capabilities across different programming environments.