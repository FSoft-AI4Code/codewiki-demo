# Android JNI Validation Sub-Module

## Introduction

The android_jni_validation_sub_module is a critical build system component that ensures consistency between Java Native Interface (JNI) bindings defined in C/C++ source code and their corresponding native method declarations in Java source files. This validation tool prevents runtime linking errors by detecting mismatches between JNI method signatures before compilation.

## Purpose and Core Functionality

This sub-module serves as a quality assurance mechanism for SDL's Android port, specifically targeting the JNI bridge between Java Android application code and native C/C++ SDL libraries. It automatically validates that:

1. **Method Signature Consistency**: JNI method signatures in C/C++ match their Java native method declarations
2. **Class Completeness**: All JNI classes have corresponding implementations on both sides
3. **Method Presence**: All native methods declared in Java have matching C/C++ implementations
4. **Type Safety**: Java types are correctly mapped to JNI type specifications

## Architecture Overview

```mermaid
graph TB
    subgraph "android_jni_validation_sub_module"
        A[JniType] -->|converts| B[Java Type Strings]
        A -->|generates| C[JNI Type Specs]
        
        D[JniMethodBinding] -->|represents| E[JNI Method Signatures]
        D -->|validates| F[Method Consistency]
        
        G[collect_jni_bindings_from_c] -->|parses| H[SDL_android.c]
        G -->|parses| I[hid.cpp]
        G -->|extracts| J[C-side JNI Bindings]
        
        K[collect_jni_bindings_from_java] -->|scans| L[Java Source Files]
        K -->|extracts| M[Java-side Native Methods]
        
        J --> N{Comparison Engine}
        M --> N
        N -->|reports| O[Validation Results]
    end
```

## Core Components

### JniType Class

The `JniType` dataclass represents a Java type in the JNI context, handling both basic types and array dimensions.

```mermaid
classDiagram
    class JniType {
        +typ: str
        +array: int
    }
    
    class TypeConverter {
        +java_type_to_jni_spec_internal(type_str: str): tuple
        +java_type_to_jni_spec(type_str: str): str
        +java_method_to_jni_spec(ret: str, args: list): str
    }
    
    JniType --> TypeConverter : uses
```

**Key Features:**
- Immutable dataclass for type safety
- Supports multi-dimensional arrays through `array` field
- Integrates with type conversion utilities

### JniMethodBinding Class

The `JniMethodBinding` dataclass encapsulates a JNI method's signature information for comparison purposes.

```mermaid
classDiagram
    class JniMethodBinding {
        +name: str
        +spec: str
    }
```

**Key Features:**
- Immutable representation of JNI method bindings
- Combines method name and JNI signature specification
- Used as set elements for efficient comparison

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant Main as main()
    participant CParser as collect_jni_bindings_from_c
    participant JavaParser as collect_jni_bindings_from_java
    participant Comparator as Comparison Engine
    participant Reporter as Error Reporter
    
    Main->>CParser: Parse C/C++ sources
    CParser->>CParser: Read SDL_android.c
    CParser->>CParser: Read hid.cpp
    CParser->>CParser: Extract register_methods() calls
    CParser->>CParser: Parse JNINativeMethod tables
    CParser->>Main: Return C-side bindings
    
    Main->>JavaParser: Parse Java sources
    JavaParser->>JavaParser: Walk JAVA_ROOT directory
    JavaParser->>JavaParser: Find native method declarations
    JavaParser->>JavaParser: Convert to JNI specs
    JavaParser->>Main: Return Java-side bindings
    
    Main->>Comparator: Compare bindings
    Comparator->>Comparator: Check class presence
    Comparator->>Comparator: Check method signatures
    Comparator->>Reporter: Report mismatches
    Reporter->>Main: Return validation result
```

## Type Conversion System

The module implements a comprehensive type mapping system between Java types and JNI type specifications:

```mermaid
graph LR
    subgraph "Java Types"
        A[char] -->|C| B[JNI Spec]
        C[byte] -->|B| B
        D[short] -->|S| B
        E[int] -->|I| B
        F[long] -->|J| B
        G[float] -->|F| B
        H[double] -->|D| B
        I[void] -->|V| B
        J[boolean] -->|Z| B
        K[Object] -->|Ljava/lang/Object;| B
        L[String] -->|Ljava/lang/String;| B
    end
    
    subgraph "Array Handling"
        M["int[]"] -->|"[I"| N[JNI Array Spec]
        O["String[][]"] -->|"[[Ljava/lang/String;"| N
    end
```

## Validation Process Flow

```mermaid
flowchart TD
    A[Start Validation] --> B{Parse C Sources}
    B -->|Success| C[Extract JNI Bindings]
    B -->|Failure| D[Report Parse Error]
    
    C --> E{Parse Java Sources}
    E -->|Success| F[Extract Native Methods]
    E -->|Failure| G[Report Parse Error]
    
    F --> H{Compare Bindings}
    H -->|Identical| I[Report OK]
    H -->|Different| J[Analyze Differences]
    
    J --> K[Missing Classes in Java?]
    K -->|Yes| L[Report Missing Java Classes]
    
    J --> M[Missing Classes in C?]
    M -->|Yes| N[Report Missing C Classes]
    
    J --> O[Method Signature Mismatches?]
    O -->|Yes| P[Report Specific Mismatches]
    
    I --> Q[Exit Success]
    D --> R[Exit Failure]
    G --> R
    L --> R
    N --> R
    P --> R
```

## Integration with Build System

The android_jni_validation_sub_module integrates with the broader [build_scripts_module](build_scripts_module.md) as part of the SDL build process:

```mermaid
graph TB
    subgraph "Build Scripts Module"
        A[build_release_sub_module] -->|produces| B[Release Artifacts]
        C[android_jni_validation_sub_module] -->|validates| D[JNI Bindings]
        E[macro_management_sub_module] -->|processes| F[Source Code]
        G[gdk_desktop_setup_sub_module] -->|configures| H[GDK Environment]
    end
    
    subgraph "SDL Android Components"
        I[android_sdl_core_module] -->|uses| D
        J[android_hid_module] -->|uses| D
        K[android_sdl_input_module] -->|uses| D
    end
    
    C -->|ensures compatibility| I
    C -->|ensures compatibility| J
    C -->|ensures compatibility| K
```

## Source File Analysis

The validation process examines specific source files within the SDL codebase:

### C/C++ Source Files
- **`src/core/android/SDL_android.c`**: Primary JNI implementation file containing native method tables
- **`src/hidapi/android/hid.cpp`**: HID-specific JNI implementations

### Java Source Files
- **`android-project/app/src/main/java/`**: Recursive scan of all Java source files for native method declarations

## Error Detection and Reporting

The module provides detailed error reporting for various mismatch scenarios:

### Missing Class Errors
- Classes present in C but missing in Java implementation
- Classes present in Java but missing in C implementation

### Method Signature Errors
- Methods existing only in C sources
- Methods existing only in Java sources
- Methods with mismatched signatures between C and Java

### Type Conversion Errors
- Unsupported Java types in method signatures
- Invalid array specifications
- Malformed JNI type specifications

## Usage and Command Line Interface

The module operates as a standalone Python script with the following interface:

```bash
python check_android_jni.py [--help]
```

**Exit Codes:**
- `0`: Validation successful, all JNI bindings match
- `1`: Validation failed, mismatches detected

## Dependencies and Requirements

### External Dependencies
- **Python 3.6+**: Required for dataclass support
- **argparse**: Command-line argument parsing
- **pathlib**: Path manipulation utilities
- **re**: Regular expression pattern matching

### SDL-Specific Dependencies
- Access to SDL source code directory structure
- Read permissions for C/C++ and Java source files
- Knowledge of SDL's JNI naming conventions

## Best Practices and Recommendations

### For SDL Developers
1. **Run validation before commits**: Always validate JNI bindings after modifying native method signatures
2. **Maintain consistency**: Ensure Java and C method signatures are updated together
3. **Use standard types**: Stick to basic Java types supported by the type conversion system

### For Build System Integration
1. **Early validation**: Run JNI validation as early as possible in the build process
2. **Fail fast**: Treat validation failures as build-breaking errors
3. **Automated checking**: Integrate validation into continuous integration pipelines

## Relationship to Other Modules

The android_jni_validation_sub_module serves as a quality gate for the Android-specific SDL modules:

- **[android_sdl_core_module](android_sdl_core_module.md)**: Validates JNI bindings for core SDL functionality
- **[android_hid_module](android_hid_module.md)**: Ensures HID device JNI interfaces are consistent
- **[android_sdl_input_module](android_sdl_input_module.md)**: Validates input-related JNI method bindings

This validation sub-module is essential for maintaining the integrity of SDL's cross-language interface on the Android platform, preventing runtime errors that would otherwise occur from JNI binding mismatches.