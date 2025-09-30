# FileSystemDiagnostic Module

## Introduction

The FileSystemDiagnostic module is a diagnostic component within the Git Credential Manager (GCM) system that validates the health and functionality of the file system operations. It ensures that basic file I/O operations work correctly and that the file system abstraction layer is properly configured, which is critical for credential storage and retrieval operations.

## Overview

FileSystemDiagnostic inherits from the base `Diagnostic` class and implements file system validation tests to ensure:
- Basic file read/write operations function correctly
- Temporary file creation and deletion work as expected
- The file system abstraction layer is properly configured
- Critical file system paths are accessible

## Architecture

### Component Structure

```mermaid
classDiagram
    class IDiagnostic {
        <<interface>>
        +Name: string
        +CanRun(): bool
        +RunAsync(): Task<DiagnosticResult>
    }
    
    class Diagnostic {
        #CommandContext: ICommandContext
        #Name: string
        +CanRun(): bool
        +RunAsync(): Task<DiagnosticResult>
        #RunInternalAsync(StringBuilder, IList<string>): Task<bool>
    }
    
    class FileSystemDiagnostic {
        +FileSystemDiagnostic(ICommandContext)
        #RunInternalAsync(StringBuilder, IList<string>): Task<bool>
    }
    
    class ICommandContext {
        <<interface>>
        +FileSystem: IFileSystem
        +Settings: ISettings
        +Streams: IStandardStreams
        ...
    }
    
    class IFileSystem {
        <<interface>>
        +UserHomePath: string
        +UserDataDirectoryPath: string
        +GetCurrentDirectory(): string
        +FileExists(string): bool
        +ReadAllText(string): string
        ...
    }
    
    IDiagnostic <|-- Diagnostic : implements
    Diagnostic <|-- FileSystemDiagnostic : inherits
    FileSystemDiagnostic ..> ICommandContext : uses
    FileSystemDiagnostic ..> IFileSystem : uses
```

### Module Dependencies

```mermaid
graph TD
    FileSystemDiagnostic --> Diagnostic
    FileSystemDiagnostic --> ICommandContext
    FileSystemDiagnostic --> IFileSystem
    FileSystemDiagnostic --> System.IO
    
    ICommandContext --> ISettings
    ICommandContext --> IStandardStreams
    ICommandContext --> ITerminal
    ICommandContext --> ISessionManager
    ICommandContext --> ITrace
    ICommandContext --> ITrace2
    ICommandContext --> ICredentialStore
    ICommandContext --> IHttpClientFactory
    ICommandContext --> IGit
    ICommandContext --> IEnvironment
    ICommandContext --> IProcessManager
    
    IFileSystem --> WindowsFileSystem
    IFileSystem --> MacOSFileSystem
    IFileSystem --> LinuxFileSystem
    
    Diagnostic --> IDiagnostic
    Diagnostic --> DiagnosticResult
```

## Core Components

### FileSystemDiagnostic Class

The `FileSystemDiagnostic` class is the main component that implements file system validation logic. It performs comprehensive tests to ensure the file system is functioning correctly.

**Key Features:**
- Validates basic file I/O operations (read/write/delete)
- Tests temporary file creation and cleanup
- Verifies file system abstraction layer configuration
- Reports critical file system paths and accessibility

**Constructor:**
```csharp
public FileSystemDiagnostic(ICommandContext commandContext)
```

**Main Method:**
```csharp
protected override Task<bool> RunInternalAsync(StringBuilder log, IList<string> additionalFiles)
```

## Diagnostic Process Flow

```mermaid
sequenceDiagram
    participant Client
    participant FileSystemDiagnostic
    participant ICommandContext
    participant IFileSystem
    participant System.IO
    
    Client->>FileSystemDiagnostic: RunAsync()
    FileSystemDiagnostic->>FileSystemDiagnostic: RunInternalAsync()
    
    FileSystemDiagnostic->>System.IO: GetTempPath()
    System.IO-->>FileSystemDiagnostic: tempDir
    
    FileSystemDiagnostic->>System.IO: Combine(tempDir, fileName)
    System.IO-->>FileSystemDiagnostic: filePath
    
    FileSystemDiagnostic->>System.IO: WriteAllText(filePath, content)
    System.IO-->>FileSystemDiagnostic: success
    
    FileSystemDiagnostic->>System.IO: ReadAllText(filePath)
    System.IO-->>FileSystemDiagnostic: actualContent
    
    FileSystemDiagnostic->>FileSystemDiagnostic: Compare content
    
    FileSystemDiagnostic->>System.IO: Delete(filePath)
    System.IO-->>FileSystemDiagnostic: success
    
    FileSystemDiagnostic->>ICommandContext: FileSystem
    ICommandContext-->>FileSystemDiagnostic: IFileSystem instance
    
    FileSystemDiagnostic->>IFileSystem: UserHomePath
    IFileSystem-->>FileSystemDiagnostic: homePath
    
    FileSystemDiagnostic->>IFileSystem: UserDataDirectoryPath
    IFileSystem-->>FileSystemDiagnostic: dataPath
    
    FileSystemDiagnostic->>IFileSystem: GetCurrentDirectory()
    IFileSystem-->>FileSystemDiagnostic: currentDir
    
    FileSystemDiagnostic-->>Client: DiagnosticResult
```

## Validation Tests

### 1. Temporary Directory Validation
- **Purpose**: Verify the system temporary directory is accessible
- **Test**: Retrieves and logs the temporary directory path
- **Failure Impact**: Indicates system-level file system issues

### 2. Basic File I/O Operations
- **Purpose**: Validate fundamental file operations work correctly
- **Tests**:
  - File creation with unique name
  - Content writing to file
  - Content reading from file
  - Data integrity verification
  - File deletion and cleanup
- **Failure Impact**: Prevents credential storage and retrieval operations

### 3. File System Abstraction Validation
- **Purpose**: Ensure the file system abstraction layer is properly configured
- **Tests**:
  - User home path accessibility
  - User data directory path accessibility
  - Current directory retrieval
- **Failure Impact**: Indicates configuration issues with platform-specific file system implementations

## Integration with Diagnostic Framework

The FileSystemDiagnostic integrates with the broader diagnostic framework through:

1. **Base Diagnostic Class**: Inherits common diagnostic functionality
2. **Command Context**: Accesses file system and other services
3. **Diagnostic Results**: Returns structured results with logs and status

```mermaid
graph LR
    subgraph "Diagnostic Framework"
        IDiagnostic
        Diagnostic
        DiagnosticResult
    end
    
    subgraph "FileSystemDiagnostic"
        FileSystemDiagnostic
        FileSystemTests
        PathValidation
    end
    
    subgraph "System Services"
        ICommandContext
        IFileSystem
        System.IO
    end
    
    IDiagnostic --> Diagnostic
    Diagnostic --> FileSystemDiagnostic
    FileSystemDiagnostic --> ICommandContext
    FileSystemDiagnostic --> System.IO
    ICommandContext --> IFileSystem
    FileSystemDiagnostic --> DiagnosticResult
```

## Platform Considerations

The FileSystemDiagnostic works across different platforms through the file system abstraction layer:

- **Windows**: Uses `WindowsFileSystem` implementation
- **macOS**: Uses `MacOSFileSystem` implementation  
- **Linux**: Uses `LinuxFileSystem` implementation

Each platform-specific implementation handles:
- Path conventions and separators
- File permissions and security
- Platform-specific file system features
- Credential storage locations

## Error Handling

The diagnostic implements comprehensive error handling:

1. **File Operation Failures**: Catches and logs file I/O exceptions
2. **Permission Issues**: Detects and reports permission-related problems
3. **Path Access Issues**: Identifies inaccessible directories
4. **Data Corruption**: Validates file content integrity

## Usage Scenarios

### Primary Use Cases
1. **System Health Checks**: Part of comprehensive system diagnostics
2. **Troubleshooting**: Identifies file system-related credential issues
3. **Installation Validation**: Ensures proper GCM installation
4. **Platform Compatibility**: Verifies cross-platform functionality

### Integration Points
- **DiagnoseCommand**: Invoked through the diagnostic command system
- **Automated Diagnostics**: Part of automated health checks
- **Manual Troubleshooting**: Used for manual diagnostic operations

## Related Documentation

- [Diagnostic Framework](DiagnosticFramework.md) - Overview of the diagnostic system
- [File System Abstraction](FileSystem.md) - File system interface and implementations
- [Command Context](CommandContext.md) - Command execution context
- [Cross-Platform Support](CrossPlatformSupport.md) - Platform-specific implementations

## Summary

The FileSystemDiagnostic module provides essential validation of file system operations within the Git Credential Manager. By testing basic I/O operations and validating the file system abstraction layer, it ensures that credential storage and retrieval operations can function correctly across all supported platforms. The module's integration with the diagnostic framework makes it a crucial component for system health monitoring and troubleshooting.