# Userspace Module Documentation

## Introduction

The userspace module is a core component of the QMK (Quantum Mechanical Keyboard) ecosystem that manages user-specific keyboard configurations, build targets, and custom keymaps outside of the main QMK firmware repository. It provides a structured way for users to maintain their personal keyboard configurations, layouts, and build preferences in a separate directory while still leveraging the QMK build system.

This module enables users to create personalized keyboard firmware configurations without modifying the core QMK firmware repository, promoting better organization and easier maintenance of custom keyboard setups.

## Architecture Overview

The userspace module follows a schema-driven architecture with versioned configuration support and comprehensive validation mechanisms. It acts as a bridge between user configurations and the QMK build system.

```mermaid
graph TB
    subgraph "Userspace Module Architecture"
        US[UserspaceDefs] --> QJ[qmk.json]
        US --> BV[Build Targets Validation]
        US --> SV[Schema Validation]
        
        QJ --> VP[Versioned Schemas]
        VP --> V11[v1.1 Schema]
        VP --> V1[v1 Schema]
        
        BV --> KT[Keyboard Targets]
        BV --> JT[JSON Targets]
        BV --> ET[Environment Variables]
        
        SV --> JS[JSON Schema]
        JS --> VE[Validation Engine]
    end
    
    subgraph "External Dependencies"
        UJE[UserspaceJSONEncoder] --> QJE[QMKJSONEncoder]
        BT[Build Targets] --> KB[Keyboard Builds]
        BT --> KM[Keymap Management]
    end
    
    US --> UJE
    US --> BT
```

## Core Components

### UserspaceDefs Class

The `UserspaceDefs` class is the central component that manages userspace configurations. It handles loading, validation, and manipulation of user-specific build targets and settings.

```mermaid
classDiagram
    class UserspaceDefs {
        -path: Path
        -build_targets: list
        +__init__(userspace_json: Path)
        +save(): bool
        +add_target(keyboard, keymap, build_env, json_path, do_print): void
        +remove_target(keyboard, keymap, build_env, json_path, do_print): void
        -__load_v1(json): void
        -__load_v1_1(json): void
        -__load_v1_target(e): void
        -__load_v1_1_target(e): void
    }
```

#### Key Features:
- **Schema Validation**: Validates configurations against versioned JSON schemas
- **Build Target Management**: Supports both keyboard/keymap pairs and JSON file references
- **Environment Variable Support**: Handles build environment configurations
- **Version Migration**: Supports multiple schema versions with backward compatibility

### UserspaceValidationError Class

A custom exception class that aggregates multiple validation errors, providing comprehensive feedback when configuration validation fails.

## Configuration Schema

The userspace module supports versioned configuration schemas, with the current latest version being 1.1.

### Schema Evolution

```mermaid
graph LR
    V0[v0 - Basic] --> V1[v1 - Keyboard/Keymap]
    V1 --> V11[v1.1 - Environment Variables]
    
    V0 -->|userspace_version| V1
    V1 -->|build_env support| V11
```

### Configuration Structure

#### Version 1.1 (Current)
```json
{
    "userspace_version": "1.1",
    "build_targets": [
        ["keyboard_name", "keymap_name", {"ENV_VAR": "value"}],
        "path/to/keymap.json"
    ]
}
```

#### Version 1.0
```json
{
    "userspace_version": "1",
    "build_targets": [
        ["keyboard_name", "keymap_name"],
        "path/to/keymap.json"
    ]
}
```

## Data Flow

### Configuration Loading Process

```mermaid
sequenceDiagram
    participant US as UserspaceDefs
    participant JS as JSON Loader
    participant VAL as Validator
    participant SCH as Schema
    participant BT as Build Targets
    
    US->>JS: Load qmk.json
    JS->>VAL: Validate against schemas
    VAL->>SCH: Check v1.1 schema
    alt v1.1 validation fails
        VAL->>SCH: Check v1 schema
        VAL->>SCH: Check v0 schema
    end
    VAL->>US: Return validation result
    US->>BT: Load build targets
    BT->>US: Populate build_targets list
```

### Build Target Management

```mermaid
flowchart TD
    Start([Start]) --> CheckType{Target Type?}
    CheckType -->|Keyboard/Keymap| AddKK[Add Keyboard/Keymap Target]
    CheckType -->|JSON Path| AddJSON[Add JSON Target]
    
    AddKK --> CheckExists{Already Exists?}
    CheckExists -->|Yes| SkipKK[Skip - Already Exists]
    CheckExists -->|No| AddKKList[Add to build_targets]
    
    AddJSON --> CheckJSONExists{JSON Already Exists?}
    CheckJSONExists -->|Yes| SkipJSON[Skip - Already Exists]
    CheckJSONExists -->|No| AddJSONList[Add to build_targets]
    
    AddKKList --> LogKK[Log Addition]
    AddJSONList --> LogJSON[Log Addition]
    SkipKK --> End([End])
    SkipJSON --> End
    LogKK --> End
    LogJSON --> End
```

## Integration with Build System

The userspace module integrates with the QMK build system through the `BuildTarget` classes, enabling compilation of user-specific keymaps and configurations.

```mermaid
graph TB
    subgraph "Userspace Integration"
        US[UserspaceDefs] --> BT[Build Targets]
        BT --> KKB[KeyboardKeymapBuildTarget]
        BT --> JKB[JsonKeymapBuildTarget]
        
        KKB --> MK[Make System]
        JKB --> MK
        
        MK --> FW[Firmware Build]
    end
    
    subgraph "Build Process"
        KKB --> KV[Keymap Validation]
        KKB --> KL[Keymap Location]
        KKB --> CP[Compile Parameters]
        
        JKB --> JV[JSON Validation]
        JKB --> JP[JSON Processing]
        JKB --> CP
    end
```

## Path Detection and Discovery

The module implements a sophisticated path detection mechanism to locate userspace directories:

1. **Current Working Directory**: Checks if the current directory contains a `qmk.json` file and keyboard/layouts directories
2. **Environment Variable**: Uses `QMK_USERSPACE` environment variable if set
3. **Configuration**: Uses `cli.config.user.overlay_dir` if configured
4. **Parent Directory Traversal**: Walks up the directory tree looking for valid userspace configurations

```mermaid
flowchart TD
    Start([Start Path Detection]) --> CheckCWD{Check ORIG_CWD}
    CheckCWD -->|Exists| Traverse[Traverse Upwards]
    CheckCWD -->|Not Set| CheckEnv
    
    Traverse --> FindQMK{Find qmk.json?}
    FindQMK -->|Yes| AddPath[Add to test_dirs]
    FindQMK -->|No| ContinueUp[Continue Up]
    
    CheckEnv --> CheckQMKEnv{QMK_USERSPACE set?}
    CheckQMKEnv -->|Yes| AddEnvPath[Add to test_dirs]
    CheckQMKEnv -->|No| CheckConfig
    
    CheckConfig --> CheckOverlay{overlay_dir set?}
    CheckOverlay -->|Yes| AddConfigPath[Add to test_dirs]
    CheckOverlay -->|No| ValidatePaths
    
    AddPath --> ContinueUp
    AddEnvPath --> ValidatePaths
    AddConfigPath --> ValidatePaths
    ContinueUp --> CheckEnv
    
    ValidatePaths --> RemoveDups[Remove Duplicates]
    RemoveDups --> ReturnPaths[Return test_dirs]
```

## Error Handling and Validation

The module implements comprehensive error handling with detailed validation feedback:

- **Schema Validation**: Multiple schema version attempts with detailed error reporting
- **File System Validation**: Checks for file existence and accessibility
- **Build Target Validation**: Ensures build targets are valid and accessible
- **JSON Schema Validation**: Leverages jsonschema for robust validation

## Dependencies

The userspace module has several key dependencies:

- **[json_encoders](json_encoders.md)**: Custom JSON encoding for userspace configurations
- **[build_targets](build_targets.md)**: Build target management and compilation
- **milc**: Command-line interface framework
- **jsonschema**: JSON schema validation
- **pathlib**: File system path manipulation

## Usage Examples

### Creating a Userspace Configuration

```python
from pathlib import Path
from qmk.userspace import UserspaceDefs

# Create a new userspace configuration
userspace = UserspaceDefs(Path('/path/to/qmk.json'))

# Add keyboard/keymap targets
userspace.add_target(keyboard='planck/rev6', keymap='my_custom_keymap')
userspace.add_target(keyboard='ergodox_ez', keymap='my_ergodox_keymap', build_env={'RGBLIGHT_ENABLE': 'yes'})

# Add JSON keymap files
userspace.add_target(json_path=Path('keymaps/my_keymap.json'))

# Save the configuration
userspace.save()
```

### Detecting Userspace

```python
from qmk.userspace import detect_qmk_userspace

# Automatically detect userspace directory
userspace_path = detect_qmk_userspace()
if userspace_path:
    print(f"Found userspace at: {userspace_path}")
else:
    print("No valid userspace found")
```

## Best Practices

1. **Version Management**: Always use the latest schema version for new configurations
2. **Path Management**: Use relative paths for JSON keymap files within the userspace directory
3. **Environment Variables**: Use build environment variables sparingly and document their purpose
4. **Validation**: Always validate configurations before saving to prevent corruption
5. **Backup**: Maintain backups of your `qmk.json` file as it contains all your build targets

## Troubleshooting

### Common Issues

1. **Validation Errors**: Check the schema version and ensure all required fields are present
2. **Path Resolution**: Verify that the userspace directory contains a valid `qmk.json` file
3. **Build Target Issues**: Ensure keyboard names and keymap names are valid and exist
4. **Environment Variables**: Check that build environment variables are properly formatted

### Debug Information

The module provides detailed logging through the milc CLI framework. Enable verbose mode to see detailed information about:
- Path detection process
- Schema validation attempts
- Build target addition/removal
- Configuration saving process

## Future Enhancements

The userspace module is designed to be extensible, with potential future enhancements including:

- Additional schema versions with new features
- Integration with external keymap editors
- Support for additional build target types
- Enhanced validation and error reporting
- Migration tools for schema upgrades