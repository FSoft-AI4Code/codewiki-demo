# Flashers Module Documentation

## Introduction

The flashers module is a critical component of the QMK (Quantum Mechanical Keyboard) firmware ecosystem, responsible for handling the firmware flashing process to various keyboard microcontrollers and bootloaders. This module provides a unified interface for detecting connected bootloader devices and flashing firmware files using appropriate tools and protocols.

## Module Purpose

The primary purpose of the flashers module is to:
- Detect and identify connected keyboard bootloaders automatically
- Provide a standardized interface for flashing firmware to different microcontroller types
- Handle various bootloader protocols (DFU, Caterina, HID, UF2, etc.)
- Manage platform-specific differences (Windows, Linux, macOS, WSL)
- Ensure safe flashing operations with proper error handling

## Architecture Overview

```mermaid
graph TB
    subgraph "Flashers Module Architecture"
        A["flasher() - Main Entry Point"]
        B["_find_bootloader() - Device Detection"]
        C["_find_usb_device() - USB Device Search"]
        D["_find_serial_port() - Serial Port Detection"]
        E["_find_uf2_devices() - UF2 Device Discovery"]
        
        F["Flash Functions"]
        F1["_flash_atmel_dfu"]
        F2["_flash_caterina"]
        F3["_flash_hid_bootloader"]
        F4["_flash_dfu_util"]
        F5["_flash_uf2"]
        F6["_flash_isp"]
        F7["_flash_mdloader"]
        F8["_flash_wb32_dfu_updater"]
        
        G["Utility Functions"]
        G1["_check_dfu_programmer_version"]
        G2["DelayedKeyboardInterrupt"]
        
        A --> B
        B --> C
        B --> D
        B --> E
        A --> F
        F --> F1
        F --> F2
        F --> F3
        F --> F4
        F --> F5
        F --> F6
        F --> F7
        F --> F8
        
        C --> G2
        G1 --> F1
    end
```

## Core Components

### DelayedKeyboardInterrupt

A context manager that provides safe handling of keyboard interrupts during critical operations, particularly USB device detection which can be sensitive to interruptions.

**Purpose**: Prevents corruption or incomplete operations when users press Ctrl+C during flashing
**Usage**: Automatically applied during USB device detection operations

```mermaid
sequenceDiagram
    participant User
    participant DelayedKeyboardInterrupt
    participant USBOperation
    
    User->>DelayedKeyboardInterrupt: Enter context
    DelayedKeyboardInterrupt->>DelayedKeyboardInterrupt: Store old signal handler
    DelayedKeyboardInterrupt->>DelayedKeyboardInterrupt: Set custom handler
    
    Note over USBOperation: Critical USB operation
    User->>DelayedKeyboardInterrupt: Ctrl+C pressed
    DelayedKeyboardInterrupt->>DelayedKeyboardInterrupt: Store interrupt info
    
    USBOperation-->>DelayedKeyboardInterrupt: Operation complete
    DelayedKeyboardInterrupt->>DelayedKeyboardInterrupt: Restore old handler
    alt Interrupt was received
        DelayedKeyboardInterrupt->>User: Process stored interrupt
    end
```

## Bootloader Support Matrix

The module supports multiple bootloader types, each with specific characteristics:

```mermaid
graph LR
    subgraph "Supported Bootloaders"
        A["atmel-dfu"] -->|"MCUs"| B["atmega16u2/32u2<br/>atmega16u4/32u4<br/>at90usb64/162/128"]
        C["caterina"] -->|"Protocol"| D["AVR109"]
        E["hid-bootloader"] -->|"Tools"| F["teensy_loader_cli<br/>hid_bootloader_cli"]
        G["stm32-dfu"] -->|"Tool"| H["dfu-util"]
        I["apm32-dfu"] -->|"Tool"| H
        J["gd32v-dfu"] -->|"Tool"| H
        K["kiibohd"] -->|"Tool"| H
        L["wb32-dfu"] -->|"Tool"| M["wb32-dfu-updater_cli"]
        N["usbasploader"] -->|"Tool"| O["avrdude"]
        P["usbtinyisp"] -->|"Tool"| O
        Q["md-boot"] -->|"Tool"| R["mdloader"]
        S["_uf2_compatible_"] -->|"Tool"| T["uf2conv.py"]
    end
```

## Data Flow Architecture

```mermaid
flowchart TD
    Start(["Start Flashing Process"])
    Input["MCU Type & Firmware File"]
    
    Start --> Input
    Input --> FindBootloader{"Find Bootloader"}
    
    FindBootloader -->|"Found"| IdentifyBootloader{"Identify Bootloader Type"}
    FindBootloader -->|"Not Found"| Error1["Error: No Bootloader"]
    
    IdentifyBootloader -->|"atmel-dfu"| FlashAtmelDFU["_flash_atmel_dfu"]
    IdentifyBootloader -->|"caterina"| FlashCaterina["_flash_caterina"]
    IdentifyBootloader -->|"hid-bootloader"| FlashHID["_flash_hid_bootloader"]
    IdentifyBootloader -->|"dfu-util variants"| FlashDFU["_flash_dfu_util"]
    IdentifyBootloader -->|"uf2"| FlashUF2["_flash_uf2"]
    IdentifyBootloader -->|"isp variants"| FlashISP["_flash_isp"]
    IdentifyBootloader -->|"md-boot"| FlashMD["_flash_mdloader"]
    IdentifyBootloader -->|"wb32-dfu"| FlashWB32["_flash_wb32_dfu_updater"]
    
    FlashAtmelDFU --> Success{"Success?"}
    FlashCaterina --> Success
    FlashHID --> Success
    FlashDFU --> Success
    FlashUF2 --> Success
    FlashISP --> Success
    FlashMD --> Success
    FlashWB32 --> Success
    
    Success -->|"Yes"| Complete(["Flashing Complete"])
    Success -->|"No"| Error2["Error: Flashing Failed"]
    Error1 --> ReturnError["Return Error Tuple"]
    Error2 --> ReturnError
    Complete --> ReturnSuccess["Return Success Tuple"]
```

## Platform-Specific Handling

The module includes special handling for different operating systems:

### Windows Subsystem for Linux (WSL)
- Uses PowerShell commands for USB device detection
- Falls back to Windows-specific serial port enumeration
- Handles path conversion for Windows compatibility

### Windows
- Uses Windows-specific serial port tools
- Implements special timing for port accessibility checks

### POSIX Systems (Linux/macOS)
- Standard USB and serial port detection
- File permission checks for serial port access

## Error Handling and Recovery

The module implements comprehensive error handling:

1. **Bootloader Detection Timeout**: 10-minute maximum search time
2. **Serial Port Detection Timeout**: 8-second timeout for Caterina
3. **Tool Availability Checks**: Verifies required flashing tools are installed
4. **Graceful Degradation**: Provides meaningful error messages for troubleshooting

## Integration with QMK Ecosystem

The flashers module integrates with other QMK components:

- **Constants Module**: Uses `BOOTLOADER_VIDS_PIDS` for device identification
- **CLI Module**: Leverages `milc.cli` for command execution and output handling
- **UF2 Conversion**: Delegates to [uf2conv module](uf2conv.md) for UF2 device handling

## Usage Patterns

### Basic Flashing Flow
```python
from qmk.flashers import flasher

# Flash firmware to detected bootloader
error, message = flasher(mcu_type, firmware_file)
if error:
    print(f"Flashing failed: {message}")
else:
    print("Flashing successful!")
```

### Device Detection
The module automatically handles the device detection process:
1. Iterates through known VID:PID pairs
2. Checks for UF2 devices separately
3. Identifies bootloader type and capabilities
4. Returns appropriate flashing function

## Security and Safety Considerations

1. **Interrupt Safety**: Uses `DelayedKeyboardInterrupt` to prevent corruption
2. **Tool Verification**: Checks tool availability before attempting flashing
3. **Timeout Protection**: Prevents infinite loops in device detection
4. **File Path Handling**: Converts paths to POSIX format for cross-platform compatibility

## Dependencies

### External Dependencies
- **pyusb**: USB device detection and communication
- **serial**: Serial port enumeration and communication
- **milc**: CLI framework for command execution

### Internal Dependencies
- **qmk.constants**: Bootloader VID:PID definitions
- **util.uf2conv**: UF2 file format handling

## Future Enhancements

The module is designed for extensibility:
- New bootloader types can be added by implementing corresponding flash functions
- Platform-specific handling can be extended for new operating systems
- Additional safety checks and validation can be incorporated

## Troubleshooting

Common issues and their solutions:

1. **"No bootloader found"**: Ensure device is in bootloader mode
2. **"Tool not available"**: Install required flashing tools (dfu-programmer, avrdude, etc.)
3. **"Port not writable"**: Check permissions or try running with elevated privileges
4. **"UF2 format required"**: Convert firmware to UF2 format before flashing

The module provides detailed error messages that guide users toward resolution, often referencing the `qmk doctor` command for system diagnostics.