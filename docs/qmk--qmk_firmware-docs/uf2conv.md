# UF2 Converter Module Documentation

## Introduction

The `uf2conv` module is a utility for converting firmware files between different formats and flashing them to microcontrollers. It provides functionality to convert between UF2 (USB Flashing Format), Intel HEX, and binary formats, as well as direct flashing capabilities to UF2-compatible devices.

UF2 is a file format designed by Microsoft that allows microcontrollers to be programmed by simply copying files to a virtual USB drive. This module serves as a critical tool in the QMK firmware build and deployment pipeline, enabling developers to convert compiled firmware into formats suitable for different flashing methods.

## Architecture Overview

```mermaid
graph TB
    subgraph "UF2 Converter Core Architecture"
        A["Input File"] --> B{"Format Detector"}
        B -->|UF2| C["UF2 Parser"]
        B -->|HEX| D["HEX Parser"]
        B -->|Binary| E["Binary Handler"]
        
        C --> F["UF2 to Binary Converter"]
        D --> G["HEX to UF2 Converter"]
        E --> H["Binary to UF2 Converter"]
        
        F --> I["Output Generator"]
        G --> I
        H --> I
        
        I --> J{"Output Options"}
        J -->|File| K["File Writer"]
        J -->|C Array| L["C Array Generator"]
        J -->|Flash| M["Device Flasher"]
        
        N["Block Class"] --> G
        N --> H
        
        O["Device Manager"] --> M
        O --> P["Drive Detector"]
    end
```

## Core Components

### Block Class

The `Block` class is the fundamental data structure for handling UF2 blocks:

```mermaid
classDiagram
    class Block {
        -addr: int
        -bytes: bytearray
        +__init__(addr: int)
        +encode(blockno: int, numblocks: int) bytes
    }
```

**Purpose**: Represents a single 256-byte data block in the UF2 format
**Key Features**:
- Manages memory address and data payload
- Handles UF2 block encoding with proper headers and footers
- Supports family ID and device type extensions

### Format Detection and Conversion Pipeline

```mermaid
flowchart LR
    A["Input Buffer"] --> B{"is_uf2()"}
    B -->|True| C["convert_from_uf2()"]
    B -->|False| D{"is_hex()"}
    D -->|True| E["convert_from_hex_to_uf2()"]
    D -->|False| F["convert_to_uf2()"]
    
    G["convert_to_carray()"] --> H["C Header Output"]
    
    style C fill:#f9f,stroke:#333
    style E fill:#f9f,stroke:#333
    style F fill:#f9f,stroke:#333
```

## Data Flow Architecture

### UF2 Format Structure

```mermaid
graph LR
    subgraph "UF2 Block Structure (512 bytes)"
        A["Magic Start 0\n(4 bytes)"] --> B["Magic Start 1\n(4 bytes)"]
        B --> C["Flags\n(4 bytes)"]
        C --> D["Target Address\n(4 bytes)"]
        D --> E["Data Size\n(4 bytes)"]
        E --> F["Block Number\n(4 bytes)"]
        F --> G["Total Blocks\n(4 bytes)"]
        G --> H["Family ID\n(4 bytes)"]
        H --> I["Data Payload\n(256 bytes)"]
        I --> J["Padding\n(476-256 bytes)"]
        J --> K["Magic End\n(4 bytes)"]
    end
```

### Conversion Process Flow

```mermaid
sequenceDiagram
    participant U as User
    participant M as Main Function
    participant D as Detector
    participant C as Converter
    participant O as Output
    
    U->>M: Input file + arguments
    M->>D: Detect format
    D->>M: Format type
    
    alt UF2 input
        M->>C: convert_from_uf2()
        C->>O: Binary output
    else HEX input
        M->>C: convert_from_hex_to_uf2()
        C->>O: UF2 output
    else Binary input
        M->>C: convert_to_uf2()
        C->>O: UF2 output
    end
    
    M->>O: Write file or flash device
```

## Device Management and Flashing

### Drive Detection System

```mermaid
graph TB
    subgraph "Platform-Specific Drive Detection"
        A["get_drives()"] --> B{"Platform Check"}
        
        B -->|Windows| C["wmic command"]
        B -->|macOS| D["/Volumes search"]
        B -->|Linux| E["/media search"]
        
        C --> F["Filter FAT drives"]
        D --> G["Check INFO_UF2.TXT"]
        E --> G
        
        F --> H["Valid UF2 Drives"]
        G --> H
    end
```

### Flashing Process

```mermaid
stateDiagram-v2
    [*] --> DetectDrives
    DetectDrives --> CheckWaitFlag
    
    CheckWaitFlag --> WaitForDevice: wait flag set
    CheckWaitFlag --> FlashNow: device found
    
    WaitForDevice --> PollDevice: sleep(0.1)
    PollDevice --> DeviceFound: device detected
    PollDevice --> WaitForDevice: no device
    
    DeviceFound --> FlashNow
    FlashNow --> WriteUF2: copy NEW.UF2
    WriteUF2 --> [*]: complete
    
    FlashNow --> Error: no drives
    Error --> [*]: exit
```

## Key Functions and Algorithms

### UF2 Validation Algorithm

```python
def is_uf2(buf):
    w = struct.unpack("<II", buf[0:8])
    return w[0] == UF2_MAGIC_START0 and w[1] == UF2_MAGIC_START1
```

**Purpose**: Validates UF2 file format by checking magic numbers
**Input**: Byte buffer
**Output**: Boolean validation result

### Intel HEX to UF2 Conversion

```mermaid
graph TD
    A["HEX Line"] --> B{"Record Type"}
    B -->|0x00| C["Data Record"]
    B -->|0x01| D["End Record"]
    B -->|0x02| E["Extended Segment"]
    B -->|0x04| F["Extended Linear"]
    
    C --> G["Update Address"]
    G --> H["Create/Update Block"]
    H --> I["Store Data"]
    
    E --> J["Update Upper Address"]
    F --> J
    J --> A
    
    D --> K["Finalize Blocks"]
    K --> L["Encode All Blocks"]
    L --> M["UF2 Output"]
```

## Configuration and Families

### Family ID System

The module supports a family ID system for targeting specific microcontroller families:

```mermaid
graph LR
    A["load_families()"] --> B["Load uf2families.json"]
    B --> C["Parse Family Data"]
    C --> D["Create Name->ID Map"]
    
    E["User Input"] --> F{"Family String"}
    F -->|Known Name| G["Lookup ID"]
    F -->|Unknown| H["Parse as Hex"]
    
    G --> I["Set familyid"]
    H --> I
```

## Command Line Interface

### Argument Processing

```mermaid
flowchart TD
    A["argparse"] --> B["Input File"]
    A --> C["Base Address"]
    A --> D["Family ID"]
    A --> E["Device Type"]
    A --> F["Output File"]
    A --> G["Device Path"]
    A --> H["Operation Flags"]
    
    H --> I["--list: List drives"]
    H --> J["--convert: Convert only"]
    H --> K["--deploy: Flash only"]
    H --> L["--wait: Wait for device"]
    H --> M["--carray: C array output"]
    H --> N["--info: Show UF2 info"]
```

## Integration with QMK Build System

The uf2conv module integrates with the broader QMK ecosystem:

```mermaid
graph TB
    subgraph "QMK Build Pipeline"
        A["QMK Build"] --> B["Firmware Binary"]
        B --> C["uf2conv"]
        C --> D["UF2 File"]
        D --> E["Device Flash"]
        
        F["keyboard module"] --> A
        G["build_targets module"] --> A
        H["flashers module"] --> E
    end
    
    subgraph "uf2conv Dependencies"
        I["uf2families.json"] --> C
        J["Platform-specific tools"] --> C
    end
```

## Error Handling and Validation

### Input Validation

- **Format Detection**: Validates file formats before processing
- **Address Bounds**: Ensures memory addresses are within valid ranges
- **Block Consistency**: Verifies UF2 block sequence and integrity
- **Platform Compatibility**: Handles platform-specific drive detection

### Error Recovery

```mermaid
graph TD
    A["Error Condition"] --> B{"Error Type"}
    B -->|Format Error| C["Skip Invalid Block"]
    B -->|Address Error| D["Assert and Exit"]
    B -->|Device Error| E["Retry or Wait"]
    B -->|File Error| F["User Feedback"]
    
    C --> G["Continue Processing"]
    D --> H["Terminate"]
    E --> I["User Intervention"]
    F --> J["Next Operation"]
```

## Performance Considerations

### Memory Management

- **Streaming Processing**: Processes files in 512-byte blocks
- **Buffer Reuse**: Reuses Block objects during conversion
- **Lazy Loading**: Loads family data only when needed

### Platform Optimizations

- **Windows**: Uses WMIC for efficient drive enumeration
- **Unix**: Leverages standard mount points for drive detection
- **Cross-platform**: Consistent interface across operating systems

## Security Considerations

### Input Sanitization

- **Buffer Bounds**: Validates all buffer accesses
- **Path Traversal**: Sanitizes file paths before operations
- **Command Injection**: Uses safe subprocess calls

### Device Access

- **Permission Checks**: Verifies write permissions before flashing
- **Drive Validation**: Confirms UF2 compatibility before operations
- **User Confirmation**: Provides clear feedback before destructive operations

## Usage Examples

### Basic Conversion

```bash
# Convert binary to UF2
python uf2conv.py firmware.bin -o firmware.uf2

# Convert HEX to UF2
python uf2conv.py firmware.hex -o firmware.uf2

# Convert UF2 to binary
python uf2conv.py firmware.uf2 -o firmware.bin
```

### Advanced Usage

```bash
# Flash with specific family ID
python uf2conv.py firmware.bin -f SAMD21 -d /media/UF2BOOT

# Generate C array
python uf2conv.py firmware.bin -c -o firmware.h

# List available devices
python uf2conv.py -l
```

## Module Dependencies

The uf2conv module operates independently but integrates with:

- **[flashers module](flashers.md)**: Provides delayed interrupt handling for flashing operations
- **[build_targets module](build_targets.md)**: Supplies target information for firmware builds
- **[keyboard module](keyboard.md)**: Manages keyboard-specific configurations

## References

- [UF2 File Format Specification](https://github.com/microsoft/uf2)
- [QMK Firmware Documentation](https://docs.qmk.fm/)
- [Microsoft UF2 Implementation](https://github.com/microsoft/uf2-samdx1)