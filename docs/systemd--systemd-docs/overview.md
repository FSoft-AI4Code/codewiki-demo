# systemd--systemd Module Documentation

## Overview

The systemd--systemd module represents the core systemd system and service manager. This module encompasses the fundamental components that make up the systemd ecosystem, including build tools, utilities, and core functionality for system initialization, service management, and system administration.

## Purpose and Scope

The systemd--systemd module serves as the central hub for:
- System initialization and boot process management
- Service and daemon control
- System resource management
- Logging and system state tracking
- Hardware and device management
- Security and authentication mechanisms

## Architecture Overview

```mermaid
graph TB
    subgraph "systemd--systemd Module"
        A[Build Tools]
        B[Core Utilities]
        C[UKI Management]
        D[Documentation Tools]
        E[Debug Tools]
    end
    
    A --> A1[ELF to EFI Converter]
    A --> A2[XML Processing]
    
    C --> C1[UKI Builder]
    C --> C2[Signing Tools]
    C --> C3[PE File Management]
    
    D --> D1[DBus Documentation]
    
    E --> E1[Hashmap Debugger]
```

## Sub-modules and Components

### 1. Build Tools Sub-module

The build tools sub-module provides essential utilities for converting and processing various file formats used in the systemd build process.

**Key Components:**
- **tools.elf2efi**: Converts ELF static PIE binaries to PE/EFI images for UEFI boot compatibility
- **tools.xml_helper**: XML processing utilities with custom entity resolution
- **tools.update-dbus-docs**: Automated DBus interface documentation generator

**Architecture:**
```mermaid
graph LR
    ELF[ELF Binary] --> elf2efi[elf2efi.py]
    elf2efi --> PE[PE/EFI Image]
    
    XML[XML Files] --> xml_helper[xml_helper.py]
    xml_helper --> Processed[Processed XML]
    
    DBus[DBus Interfaces] --> update_docs[update-dbus-docs.py]
    update_docs --> Docs[Documentation]
```

For detailed information about the build tools sub-module, see [build-tools.md](build-tools.md).

### 2. UKI (Unified Kernel Image) Management Sub-module

The UKI management sub-module handles the creation, signing, and management of Unified Kernel Images, which are essential for modern UEFI boot processes.

**Key Components:**
- **src.ukify.ukify**: Main UKI builder and management tool
- **UKI Class**: Represents Unified Kernel Images with multiple sections
- **SignTool Hierarchy**: Abstract base class for different signing implementations
- **Section Management**: Handles different UKI sections (.linux, .initrd, .cmdline, etc.)

**Architecture:**
```mermaid
graph TB
    subgraph "UKI Management"
        UKI[UKI Class]
        ST[SignTool]
        PS[PeSign]
        SS[SbSign]
        SSS[SystemdSbSign]
        SC[Section]
        UC[UkifyConfig]
    end
    
    ST --> PS
    ST --> SS
    ST --> SSS
    
    UKI --> SC
    UC --> UKI
    PS --> Signed[Signed UKI]
    SS --> Signed
    SSS --> Signed
```

For detailed information about the UKI management sub-module, see [uki-management.md](uki-management.md).

### 3. Debug and Development Tools Sub-module

This sub-module provides specialized tools for debugging and development purposes.

**Key Components:**
- **tools.gdb-sd_dump_hashmaps**: GDB extension for debugging systemd hashmaps

## Data Flow and Dependencies

### UKI Creation Process
```mermaid
sequenceDiagram
    participant Config as UkifyConfig
    participant UKI as UKI Builder
    participant Sections as Section Manager
    participant Signer as SignTool
    participant Output as PE Output
    
    Config->>UKI: Initialize with parameters
    UKI->>Sections: Add kernel sections
    UKI->>Sections: Add initrd sections
    UKI->>Sections: Add configuration sections
    UKI->>Signer: Sign if required
    Signer->>Output: Generate signed PE
    UKI->>Output: Write final UKI
```

### ELF to EFI Conversion Process
```mermaid
sequenceDiagram
    participant ELF as ELF Input
    participant Parser as ELF Parser
    participant Converter as PE Converter
    participant Reloc as Relocation Handler
    participant Writer as PE Writer
    
    ELF->>Parser: Parse ELF structure
    Parser->>Converter: Extract sections
    Converter->>Reloc: Convert relocations
    Reloc->>Writer: Generate PE relocations
    Converter->>Writer: Create PE sections
    Writer->>Writer: Write PE/EFI file
```

## Key Features and Capabilities

### 1. Multi-Architecture Support
The module supports multiple architectures including:
- x86_64 (x64)
- i386 (ia32)
- AArch64 (aa64)
- ARM (arm)
- LoongArch (loongarch32/64)
- RISC-V (riscv32/64)

### 2. Security and Signing
- Secure Boot support through multiple signing tools (pesign, sbsign, systemd-sbsign)
- PCR (Platform Configuration Register) measurement and signing
- Certificate and key management
- Policy digest generation

### 3. Flexible Configuration
- Command-line interface with extensive options
- Configuration file support
- Profile-based UKI building
- Section customization

### 4. Development and Debugging Tools
- Hashmap debugging for development
- XML processing utilities
- DBus documentation generation
- Comprehensive inspection capabilities

## Integration Points

The systemd--systemd module integrates with:
- **systemd-boot**: For boot management
- **systemd-stub**: For UKI stub functionality
- **systemd-measure**: For PCR measurements
- **systemd-keyutil**: For key management
- **External tools**: pesign, sbsign, various compression tools

## File Formats Supported

- **Input**: ELF binaries, compressed kernels (gzip, lz4, lzma, zstd), XML files
- **Output**: PE/EFI images, signed UKIs, documentation
- **Configuration**: INI-style config files, command-line arguments

## Error Handling and Validation

The module implements comprehensive error handling:
- Format validation for all input files
- Architecture compatibility checks
- Security validation for signing operations
- Resource allocation verification
- Cross-platform compatibility checks

This documentation provides a comprehensive overview of the systemd--systemd module's architecture, components, and functionality. For detailed information about specific sub-modules, refer to their individual documentation files.