# Keyboard Module Documentation

## Introduction

The keyboard module is a core component of the QMK (Quantum Mechanical Keyboard) firmware build system. It provides essential functionality for discovering, managing, and working with keyboard definitions within the QMK ecosystem. This module serves as the central hub for keyboard-related operations, from basic keyboard discovery to complex layout rendering and configuration management.

The module handles the intricate relationships between physical keyboards, their configurations, aliases, and build targets, making it an indispensable part of the QMK build pipeline. It provides both programmatic access to keyboard information and utility functions for rendering keyboard layouts in various formats.

## Architecture Overview

```mermaid
graph TB
    subgraph "Keyboard Module Core"
        AK[AllKeyboards<br/>Singleton Class]
        KF[Keyboard Functions<br/>Module Level]
        LR[Layout Rendering<br/>Subsystem]
    end
    
    subgraph "External Dependencies"
        QP[QMK Path Module]
        JC[JSON Config Module]
        MF[Makefile Parser]
        CH[Config H Parser]
        BT[Build Targets]
    end
    
    subgraph "Data Sources"
        KA[Keyboard Aliases<br/>HJSON]
        RJ[Rules.mk Files]
        CHF[Config.h Files]
        KB[Keyboard.json Files]
    end
    
    AK --> KF
    KF --> LR
    KF --> QP
    KF --> JC
    KF --> MF
    KF --> CH
    BT --> AK
    
    KF --> KA
    KF --> RJ
    KF --> CHF
    KF --> KB
    
    style AK fill:#e1f5fe
    style KF fill:#f3e5f5
    style LR fill:#e8f5e9
```

## Core Components

### AllKeyboards Class

The `AllKeyboards` class is a singleton-like representation that encapsulates the concept of "all keyboards" within the QMK system. This class provides a unified interface for operations that need to target or reference all available keyboards.

**Key Characteristics:**
- Immutable representation of the universal keyboard set
- Provides consistent string representation ("all")
- Enables polymorphic behavior in build systems
- Supports equality comparisons

**Usage Pattern:**
```python
# Used in build targets and CLI operations
all_kb = AllKeyboards()
if is_all_keyboards(all_kb):
    # Process all keyboards
    pass
```

### Keyboard Discovery System

The keyboard discovery system forms the backbone of the module, providing comprehensive functionality for finding and enumerating keyboards within the QMK firmware structure.

```mermaid
graph LR
    subgraph "Discovery Process"
        LP[List Keyboards<br/>list_keyboards]
        FK[Find Keyboard<br/>from Directory]
        RK[Resolve Keyboard<br/>resolve_keyboard]
    end
    
    subgraph "File System Scanning"
        RM[Rules.mk Search]
        KJ[Keyboard.json Search]
        FP[Path Processing]
    end
    
    subgraph "Resolution Logic"
        AD[Alias Resolution]
        DF[Default Folder<br/>Processing]
        VD[Validation]
    end
    
    LP --> RM
    LP --> KJ
    RM --> FP
    KJ --> FP
    
    FK --> RK
    RK --> AD
    RK --> DF
    RK --> VD
    
    style LP fill:#fff3e0
    style FK fill:#fff3e0
    style RK fill:#fff3e0
```

**Discovery Algorithm:**
1. **File System Scanning**: Searches for `rules.mk` and `keyboard.json` files in the keyboards directory
2. **Path Extraction**: Extracts keyboard names from file paths using `_find_name()`
3. **Alias Resolution**: Resolves keyboard aliases from the aliases mapping file
4. **Default Folder Processing**: Handles `DEFAULT_FOLDER` directives in rules.mk files
5. **Validation**: Ensures resolved keyboards are valid QMK keyboards

### Keyboard Resolution and Aliasing

The module implements a sophisticated keyboard resolution system that handles historical aliases, default folders, and path resolution.

```mermaid
sequenceDiagram
    participant Client
    participant KF as Keyboard Functions
    participant KA as Keyboard Aliases
    participant RK as Resolve Keyboard
    participant VP as Validation
    
    Client->>KF: keyboard_folder("ergodox")
    KF->>KA: Load aliases from HJSON
    KF->>KA: Check if ergodox in aliases
    KA-->>KF: Return target keyboard
    KF->>RK: resolve_keyboard(target)
    RK->>RK: Parse rules.mk
    RK->>RK: Check DEFAULT_FOLDER
    RK->>VP: Validate path exists
    VP-->>RK: Validation result
    RK-->>KF: Return resolved path
    KF-->>Client: Return keyboard folder
```

**Alias Resolution Features:**
- **Hierarchical Resolution**: Supports chained aliases (A -> B -> C)
- **Circular Reference Protection**: Prevents infinite loops in alias chains
- **Target Validation**: Ensures final resolved keyboard exists
- **Historical Compatibility**: Maintains backward compatibility with legacy keyboard names

### Configuration Management

The module provides comprehensive configuration management through integration with QMK's configuration parsing systems.

```mermaid
graph TD
    subgraph "Configuration Sources"
        CH[Config.h Files]
        RM[Rules.mk Files]
        KJ[Keyboard.json Files]
    end
    
    subgraph "Parsing Functions"
        PC[parse_config_h_file]
        PR[parse_rules_mk_file]
        JL[json_load]
    end
    
    subgraph "Aggregation Functions"
        CF[config_h Function]
        RF[rules_mk Function]
    end
    
    subgraph "Output"
        CD[Config Dictionary]
        RD[Rules Dictionary]
    end
    
    CH --> PC
    RM --> PR
    KJ --> JL
    
    PC --> CF
    PR --> RF
    JL --> CF
    
    CF --> CD
    RF --> RD
    
    style CF fill:#e3f2fd
    style RF fill:#e3f2fd
```

**Configuration Hierarchy:**
1. **Base Configuration**: Root-level config.h and rules.mk files
2. **Keyboard-Specific**: Keyboard directory configurations
3. **Sub-Keyboard**: Sub-folder specific configurations
4. **Final Aggregation**: Merged configuration dictionaries

### Layout Rendering System

The layout rendering system provides sophisticated ASCII and Unicode visualization of keyboard layouts, supporting various key types and special cases.

```mermaid
graph TB
    subgraph "Rendering Pipeline"
        RL[render_layout]
        RLS[render_layouts]
        RK[render_key_rect]
        RIE[render_key_isoenter]
        RBE[render_key_baenter]
        RE[render_encoder]
    end
    
    subgraph "Character Sets"
        BC[Box Characters<br/>Unicode/ASCII]
        EC[Encoder Characters<br/>Unicode/ASCII]
    end
    
    subgraph "Layout Data"
        LD[Layout JSON]
        KL[Key Labels]
        KA[Key Attributes<br/>x,y,w,h]
    end
    
    LD --> RL
    KL --> RL
    KA --> RK
    KA --> RIE
    KA --> RBE
    KA --> RE
    
    BC --> RK
    BC --> RIE
    BC --> RBE
    EC --> RE
    
    RL --> RLS
    
    style RL fill:#fce4ec
    style RLS fill:#fce4ec
```

**Rendering Features:**
- **Multi-Style Support**: Both Unicode and ASCII rendering modes
- **Key Type Handling**: Standard keys, ISO Enter, Big Ass Enter, Encoders
- **Dynamic Labeling**: Support for custom key labels
- **Proportional Scaling**: Accurate key size representation
- **Text Buffer Management**: Efficient character array manipulation

## Data Flow Architecture

```mermaid
graph LR
    subgraph "Input Sources"
        FS[File System<br/>keyboards/]
        AL[Alias Files<br/>HJSON]
        CF[Config Files]
    end
    
    subgraph "Processing Layer"
        KD[Keyboard Discovery]
        KR[Keyboard Resolution]
        CM[Config Management]
        LR[Layout Rendering]
    end
    
    subgraph "Output Formats"
        KL[Keyboard Lists]
        KP[Keyboard Paths]
        CD[Config Dictionaries]
        LV[Layout Visualizations]
    end
    
    subgraph "Consumers"
        BT[Build Targets]
        CLI[CLI Tools]
        API[API Endpoints]
    end
    
    FS --> KD
    AL --> KR
    CF --> CM
    
    KD --> KL
    KR --> KP
    CM --> CD
    LR --> LV
    
    KL --> BT
    KP --> BT
    CD --> BT
    LV --> CLI
    
    style KD fill:#e8eaf6
    style KR fill:#e8eaf6
    style CM fill:#e8eaf6
    style LR fill:#e8eaf6
```

## Integration with Build System

The keyboard module integrates closely with the [build_targets](build_targets.md) module to provide keyboard-specific build functionality.

```mermaid
graph TD
    subgraph "Keyboard Module"
        KF[Keyboard Functions]
        AK[AllKeyboards]
    end
    
    subgraph "Build Targets Module"
        BT[BuildTarget Base Class]
        KB[KeyboardKeymapBuildTarget]
    end
    
    subgraph "Build Process"
        KP[Keyboard Path Resolution]
        KA[Keymap Location]
        CC[Compile Command]
    end
    
    KF --> BT
    AK --> KB
    KB --> KP
    KP --> KA
    KA --> CC
    
    style KF fill:#fff8e1
    style AK fill:#fff8e1
    style BT fill:#f3e5f5
    style KB fill:#f3e5f5
```

**Integration Points:**
- **Keyboard Resolution**: `keyboard_folder()` function used in `BuildTarget.__init__()`
- **Path Validation**: Integration with QMK path utilities for validation
- **Alias Support**: Build targets respect keyboard aliases for compatibility
- **Userspace Integration**: Support for keymaps in userspace directories

## Performance Optimizations

The module implements several performance optimizations to handle the large number of keyboards in the QMK ecosystem efficiently.

### Caching Strategy

```mermaid
graph LR
    subgraph "Cache Layers"
        LC[LRU Cache<br/>Decorators]
        KD[Keyboard Data<br/>Cache]
        AD[Alias Data<br/>Cache]
    end
    
    subgraph "Cache Targets"
        KA[keyboard_alias_definitions]
        RK[resolve_keyboard]
        LK[list_keyboards]
    end
    
    subgraph "Performance Benefits"
        FR[Faster Resolution]
        RM[Reduced Memory]
        IO[Less I/O]
    end
    
    LC --> KA
    LC --> RK
    LC --> LK
    
    KA --> KD
    RK --> KD
    LK --> AD
    
    KD --> FR
    AD --> RM
    KD --> IO
    
    style LC fill:#e1f5fe
    style KD fill:#e1f5fe
    style AD fill:#e1f5fe
```

**Optimization Techniques:**
- **LRU Caching**: `@lru_cache` decorators on expensive functions
- **File System Minimization**: Efficient glob patterns to reduce file system access
- **Path String Operations**: Optimized string manipulation for path processing
- **Lazy Loading**: Configuration files loaded only when needed

## Error Handling and Validation

The module implements comprehensive error handling to ensure robust operation across various edge cases and invalid inputs.

```mermaid
graph TD
    subgraph "Validation Points"
        KV[Keyboard Validation<br/>qmk.path.is_keyboard]
        AV[Alias Validation<br/>Circular Reference Check]
        PV[Path Validation<br/>Path Existence Check]
    end
    
    subgraph "Error Types"
        VE[ValueError<br/>Invalid Keyboard]
        FE[FileNotFoundError<br/>Missing Files]
        CE[CircularError<br/>Alias Loop]
    end
    
    subgraph "Error Handling"
        EH[Exception Handling]
        DF[Default Fallbacks]
        LG[Logging]
    end
    
    KV --> VE
    AV --> CE
    PV --> FE
    
    VE --> EH
    CE --> EH
    FE --> EH
    
    EH --> DF
    EH --> LG
    
    style KV fill:#ffebee
    style AV fill:#ffebee
    style PV fill:#ffebee
```

## Module Dependencies

The keyboard module has several key dependencies that provide supporting functionality:

### Internal Dependencies
- **[qmk.path](path.md)**: Path resolution and validation utilities
- **[qmk.c_parse](c_parse.md)**: C header file parsing for configuration
- **[qmk.json_schema](json_schema.md)**: JSON schema validation and loading
- **[qmk.makefile](makefile.md)**: Makefile parsing for build rules

### External Dependencies
- **pathlib**: Modern path manipulation
- **glob**: File system pattern matching
- **array**: Efficient character array operations for rendering

## Usage Examples

### Basic Keyboard Discovery
```python
from qmk.keyboard import list_keyboards, keyboard_folder

# Get all available keyboards
keyboards = list_keyboards()
print(f"Found {len(keyboards)} keyboards")

# Resolve a keyboard with aliases
resolved = keyboard_folder("planck")
print(f"Planck resolves to: {resolved}")
```

### Configuration Access
```python
from qmk.keyboard import config_h, rules_mk

# Get merged configuration for a keyboard
config = config_h("clueboard/66/rev4")
rules = rules_mk("clueboard/66/rev4")

print(f"MCU: {config.get('MCU')}")
print(f"Bootloader: {rules.get('BOOTLOADER')}")
```

### Layout Rendering
```python
from qmk.keyboard import render_layout

# Render a layout with Unicode characters
layout_data = [
    {"x": 0, "y": 0, "w": 1, "h": 1, "label": "Q"},
    {"x": 1, "y": 0, "w": 1, "h": 1, "label": "W"},
    # ... more keys
]

rendered = render_layout(layout_data, render_ascii=False)
print(rendered)
```

## Future Considerations

The keyboard module is designed with extensibility in mind, supporting future enhancements such as:

- **Dynamic Keyboard Registration**: Runtime keyboard discovery
- **Enhanced Layout Support**: Additional key types and layouts
- **Performance Improvements**: Further caching and optimization
- **Extended Validation**: More comprehensive keyboard validation
- **Plugin Architecture**: Extensible keyboard processing plugins

This module serves as the foundation for all keyboard-related operations in QMK, providing a robust and efficient interface for keyboard discovery, management, and visualization.