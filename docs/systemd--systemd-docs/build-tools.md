# build-tools Module Documentation

## Introduction

The build-tools module provides essential utilities for converting and processing binary formats in the systemd-boot ecosystem. It consists of two main components: an ELF to PE/EFI converter (`elf2efi.py`) and an XML processing helper (`xml_helper.py`). These tools are critical for creating bootable EFI images from ELF binaries and handling XML configuration files with custom entity resolution.

## Module Architecture

### Core Components Overview

The build-tools module contains the following core components:

- **tools.elf2efi.PeCoffHeader**: PE COFF header structure definition
- **tools.elf2efi.PeOptionalHeader**: PE optional header with 32-bit and 64-bit variants
- **tools.elf2efi.PeSection**: PE section structure for managing code and data sections
- **tools.elf2efi.PeRelocationBlock**: PE relocation block for runtime address fixing
- **tools.elf2efi.PeRelocationEntry**: Individual PE relocation entry
- **tools.xml_helper.CustomResolver**: Custom XML entity resolver for documentation processing

### Architecture Diagram

```mermaid
graph TB
    subgraph "build-tools Module"
        subgraph "ELF to PE/EFI Converter"
            PCH[PeCoffHeader]
            POH[PeOptionalHeader<br/>32-bit & 64-bit variants]
            PS[PeSection]
            PRB[PeRelocationBlock]
            PRE[PeRelocationEntry]
            
            PCH --> POH
            POH --> PS
            PS --> PRB
            PRB --> PRE
        end
        
        subgraph "XML Helper"
            CR[CustomResolver]
        end
    end
    
    subgraph "External Dependencies"
        ELFT[ELFTools]
        CTYPES[ctypes]
        LXML[lxml]
    end
    
    ELFT --> PCH
    ELFT --> POH
    ELFT --> PS
    CTYPES --> PCH
    CTYPES --> POH
    CTYPES --> PS
    CTYPES --> PRB
    CTYPES --> PRE
    LXML --> CR
```

## Component Details

### ELF to PE/EFI Converter (elf2efi.py)

The ELF to PE/EFI converter is the primary component of this module, responsible for transforming ELF static PIE (Position Independent Executable) binaries into PE/EFI format suitable for UEFI firmware loading.

#### Key Features

- **Static PIE Conversion**: Specifically designed to work with static PIE binaries that contain only base relocations
- **Section Preservation**: Maintains memory layout while copying desired ELF sections to PE format
- **Relocation Translation**: Converts ELF relocations to PE relocations for runtime loading
- **Multi-Architecture Support**: Supports x86, x86_64, ARM, AArch64, RISC-V, and LoongArch architectures

#### Conversion Process Flow

```mermaid
flowchart TD
    Start([ELF Input]) --> Validate[Validate ELF File]
    Validate --> CheckArch{Check Architecture}
    CheckArch -->|Supported| ExtractSections[Extract Sections]
    CheckArch -->|Unsupported| Error[Error: Unsupported Arch]
    ExtractSections --> ConvertSections[Convert to PE Sections]
    ConvertSections --> HandleRelocations[Process Relocations]
    HandleRelocations --> BuildPE[Build PE Structure]
    BuildPE --> WritePE[Write PE Output]
    WritePE --> End([PE/EFI Output])
    Error --> End
```

#### PE Structure Components

##### PeCoffHeader
The COFF (Common Object File Format) header contains essential information about the PE file:
- Machine architecture identifier
- Number of sections
- Timestamp
- Characteristics flags
- Size of optional header

##### PeOptionalHeader
The optional header (required for executable images) comes in two variants:
- **PeOptionalHeader32**: For 32-bit executables
- **PeOptionalHeader32Plus**: For 64-bit executables

Contains critical information such as:
- Image base address
- Entry point address
- Section alignment
- Stack and heap sizes
- Data directories

##### PeSection
Represents individual sections within the PE file:
- Section name (up to 8 characters)
- Virtual address and size
- Raw data location and size
- Characteristics (read/write/execute permissions)

##### PeRelocationBlock and PeRelocationEntry
Handle runtime address relocation:
- **PeRelocationBlock**: Groups relocations by memory page
- **PeRelocationEntry**: Individual relocation with offset and type

#### Section Processing

The converter processes ELF sections according to the following rules:

```mermaid
graph LR
    ELF_Section[ELF Section] --> CheckFlags{Check Flags}
    CheckFlags -->|SHF_EXECINSTR| RX[RX: Executable Code<br/>PE_CHARACTERISTICS_RX]
    CheckFlags -->|SHF_WRITE| RW[RW: Writable Data<br/>PE_CHARACTERISTICS_RW]
    CheckFlags -->|Default| R[R: Read-Only Data<br/>PE_CHARACTERISTICS_R]
    
    RX --> StandardName[Standard Names:
    .text for code
    .data for writable
    .rodata for read-only]
    RW --> StandardName
    R --> StandardName
```

#### Architecture Support

The converter supports multiple architectures with specific PE machine types:

| Architecture | PE Machine Type | Value |
|--------------|-----------------|--------|
| x86 | IMAGE_FILE_MACHINE_I386 | 0x014C |
| x86_64 | IMAGE_FILE_MACHINE_AMD64 | 0x8664 |
| ARM | IMAGE_FILE_MACHINE_ARM | 0x01C2 |
| AArch64 | IMAGE_FILE_MACHINE_ARM64 | 0xAA64 |
| RISC-V 32-bit | IMAGE_FILE_MACHINE_RISCV32 | 0x5032 |
| RISC-V 64-bit | IMAGE_FILE_MACHINE_RISCV64 | 0x5064 |
| LoongArch 32-bit | IMAGE_FILE_MACHINE_LOONGARCH32 | 0x6232 |
| LoongArch 64-bit | IMAGE_FILE_MACHINE_LOONGARCH64 | 0x6264 |

### XML Helper (xml_helper.py)

The XML helper provides custom entity resolution for XML processing, primarily used in documentation generation.

#### CustomResolver

The `CustomResolver` class extends lxml's resolver to handle custom entity references:

- **custom-entities.ent**: Resolves to `man/custom-entities.ent`
- **ethtool-link-mode**: Resolves to `src/shared/ethtool-link-mode.xml`
- **bpf-delegate**: Resolves to `src/core/bpf-delegate.xml`

This enables XML documents to include external entities and maintain consistency across the systemd documentation.

## Data Flow

### ELF to PE Conversion Data Flow

```mermaid
sequenceDiagram
    participant ELF as ELF File
    participant Parser as ELF Parser
    participant Converter as PE Converter
    participant Builder as PE Builder
    participant Output as PE Output
    
    ELF->>Parser: Read ELF headers
    Parser->>Parser: Validate PIE status
    Parser->>Converter: Extract sections
    Converter->>Converter: Map ELF->PE sections
    Converter->>Converter: Process relocations
    Converter->>Builder: Build PE structures
    Builder->>Output: Write PE headers
    Builder->>Output: Write section data
    Builder->>Output: Write relocations
```

## Integration with Other Modules

The build-tools module serves as a foundational component for the [uki-management](uki-management.md) module, which uses the PE/EFI conversion capabilities to create Unified Kernel Images (UKIs).

### Relationship with uki-management

```mermaid
graph LR
    subgraph "build-tools"
        elf2efi[elf2efi.py]
    end
    
    subgraph "uki-management"
        uki[UKI Builder]
        sign[Signing Tools]
    end
    
    elf2efi -->|Provides PE/EFI| uki
    uki -->|Uses| elf2efi
    uki -->|Signs output| sign
```

## Usage Examples

### Basic ELF to PE Conversion

```bash
python3 tools/elf2efi.py input.elf output.pe
```

### Advanced Conversion with Custom Parameters

```bash
python3 tools/elf2efi.py \
    --version-major 1 \
    --version-minor 0 \
    --efi-major 2 \
    --efi-minor 70 \
    --subsystem 10 \
    --minimum-sections 16 \
    --copy-sections ".note,.comment" \
    input.elf output.pe
```

### XML Processing

```python
from tools.xml_helper import xml_parse, xml_print

# Parse XML with custom entity resolution
doc = xml_parse('documentation.xml')

# Process and print formatted XML
formatted_xml = xml_print(doc)
```

## Error Handling

The module implements comprehensive error handling for various scenarios:

- **BadSectionError**: Raised when ELF sections are in an invalid state
- **ValueError**: Raised for unsupported ELF types or architectures
- **Validation Errors**: Checked for PIE status, architecture support, and alignment requirements

## Configuration and Customization

### PE Header Configuration

The converter allows customization of various PE header fields:

- **Version Information**: Major and minor image versions
- **EFI Subsystem**: Minimum EFI subsystem version requirements
- **PE Subsystem**: Target subsystem (default: 10 for EFI application)
- **Section Management**: Minimum section count and additional sections to copy

### Memory Layout

The converter maintains specific memory alignment requirements:

- **Section Alignment**: 4KiB (EFI requirement)
- **File Alignment**: 512 bytes
- **Image Base**: Automatically calculated based on filename hash

## Performance Considerations

- **Static PIE Requirement**: Only processes static PIE binaries to minimize relocation complexity
- **Base Relocations Only**: Focuses on base relocations for optimal performance
- **Memory Efficiency**: Uses bytearray operations for efficient data manipulation
- **Streaming Processing**: Processes large files without loading entire content into memory

## Security Features

- **PIE Validation**: Ensures input binaries are position-independent
- **Alignment Enforcement**: Maintains proper memory alignment for security
- **Relocation Validation**: Validates all relocations before processing
- **Buffer Overflow Protection**: Uses proper bounds checking in all operations

This comprehensive approach ensures that the build-tools module provides reliable, secure, and efficient binary format conversion capabilities essential for the systemd-boot ecosystem.