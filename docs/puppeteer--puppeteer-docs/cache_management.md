# Cache Management Module

The cache_management module provides a robust caching system for managing browser installations in Puppeteer. It handles the storage, retrieval, and lifecycle management of browser binaries across different platforms and versions, ensuring efficient reuse of downloaded browser installations.

## Overview

The cache management system is built around a hierarchical directory structure that organizes browser installations by browser type, platform, and build ID. This module serves as the foundation for the browser installation and management system, providing persistent storage and metadata management for browser binaries.

## Architecture

```mermaid
graph TB
    subgraph "Cache Management Architecture"
        Cache[Cache] --> |manages| InstalledBrowser[InstalledBrowser]
        Cache --> |stores| Metadata[Metadata]
        Cache --> |uses| BrowserData[Browser Data]
        Cache --> |detects| Platform[Platform Detection]
        
        InstalledBrowser --> |provides| ExecutablePath[Executable Path]
        InstalledBrowser --> |manages| InstallationDir[Installation Directory]
        
        Metadata --> |maps| Aliases[Version Aliases]
        Metadata --> |tracks| BuildIds[Build IDs]
        
        subgraph "File System Structure"
            RootDir[Root Directory]
            BrowserRoot[Browser Root]
            PlatformBuild[Platform-BuildId Dirs]
            MetadataFile[.metadata Files]
            
            RootDir --> BrowserRoot
            BrowserRoot --> PlatformBuild
            BrowserRoot --> MetadataFile
        end
        
        Cache --> RootDir
    end
```

## Core Components

### Cache Class

The `Cache` class is the central component that manages the entire browser cache system:

```mermaid
classDiagram
    class Cache {
        -rootDir: string
        +browserRoot(browser: Browser): string
        +metadataFile(browser: Browser): string
        +readMetadata(browser: Browser): Metadata
        +writeMetadata(browser: Browser, metadata: Metadata): void
        +resolveAlias(browser: Browser, alias: string): string
        +installationDir(browser: Browser, platform: BrowserPlatform, buildId: string): string
        +clear(): void
        +uninstall(browser: Browser, platform: BrowserPlatform, buildId: string): void
        +getInstalledBrowsers(): InstalledBrowser[]
        +computeExecutablePath(options: ComputeExecutablePathOptions): string
    }
    
    class InstalledBrowser {
        +browser: Browser
        +buildId: string
        +platform: BrowserPlatform
        +executablePath: string
        -cache: Cache
        +path: string
        +readMetadata(): Metadata
        +writeMetadata(metadata: Metadata): void
    }
    
    class Metadata {
        +aliases: Record~string, string~
    }
    
    Cache --> InstalledBrowser : creates
    Cache --> Metadata : manages
    InstalledBrowser --> Cache : references
```

### InstalledBrowser Class

The `InstalledBrowser` class represents a specific browser installation with its associated metadata and provides access to the executable path and installation directory.

## Directory Structure

The cache follows a well-defined hierarchical structure:

```mermaid
graph TD
    subgraph "Cache Directory Structure"
        Root[rootDir/] --> Chrome[chrome/]
        Root --> Firefox[firefox/]
        Root --> Edge[edge/]
        
        Chrome --> ChromeMeta[.metadata]
        Chrome --> ChromeWin[win64-123456/]
        Chrome --> ChromeMac[mac-123456/]
        Chrome --> ChromeLinux[linux-123456/]
        
        Firefox --> FirefoxMeta[.metadata]
        Firefox --> FirefoxWin[win64-789012/]
        Firefox --> FirefoxMac[mac-789012/]
        
        ChromeWin --> ChromeExe[chrome.exe]
        ChromeMac --> ChromeApp[Chrome.app/]
        ChromeLinux --> ChromeBin[chrome]
        
        FirefoxWin --> FirefoxExe[firefox.exe]
        FirefoxMac --> FirefoxApp[Firefox.app/]
    end
```

## Data Flow

```mermaid
sequenceDiagram
    participant Client
    participant Cache
    participant FileSystem
    participant PlatformDetector
    participant BrowserData
    
    Client->>Cache: computeExecutablePath(options)
    Cache->>PlatformDetector: detectBrowserPlatform()
    PlatformDetector-->>Cache: platform
    Cache->>Cache: resolveAlias(browser, buildId)
    Cache->>FileSystem: read .metadata file
    FileSystem-->>Cache: metadata
    Cache->>Cache: installationDir(browser, platform, buildId)
    Cache->>BrowserData: executablePathByBrowser[browser]
    BrowserData-->>Cache: executable path function
    Cache-->>Client: full executable path
```

## Key Operations

### Browser Installation Management

```mermaid
flowchart TD
    Start([Start Installation]) --> CheckCache{Cache Exists?}
    CheckCache -->|No| CreateCache[Create Cache Directory]
    CheckCache -->|Yes| CheckBrowser{Browser Installed?}
    
    CreateCache --> CheckBrowser
    CheckBrowser -->|No| Install[Install Browser]
    CheckBrowser -->|Yes| UpdateMeta[Update Metadata]
    
    Install --> CreateDir[Create Installation Directory]
    CreateDir --> DownloadBrowser[Download Browser Binary]
    DownloadBrowser --> ExtractBrowser[Extract Browser]
    ExtractBrowser --> UpdateMeta
    
    UpdateMeta --> WriteMetadata[Write .metadata File]
    WriteMetadata --> CreateInstalledBrowser[Create InstalledBrowser Instance]
    CreateInstalledBrowser --> End([End])
```

### Alias Resolution

```mermaid
flowchart TD
    ResolveAlias([Resolve Alias]) --> IsLatest{Alias == 'latest'?}
    IsLatest -->|Yes| GetAllVersions[Get All Build IDs]
    IsLatest -->|No| LookupAlias[Lookup in Aliases Map]
    
    GetAllVersions --> SortVersions[Sort by Version Comparator]
    SortVersions --> GetLatest[Get Last Version]
    GetLatest --> ReturnBuildId[Return Build ID]
    
    LookupAlias --> Found{Found in Map?}
    Found -->|Yes| ReturnBuildId
    Found -->|No| ReturnUndefined[Return undefined]
    
    ReturnBuildId --> End([End])
    ReturnUndefined --> End
```

## Integration Points

### Browser Management Integration

The cache_management module integrates closely with other browser management components:

- **[installation_system](installation_system.md)**: Provides storage for downloaded browser installations
- **[launch_system](launch_system.md)**: Supplies executable paths for browser launching
- **[cli_interface](cli_interface.md)**: Exposes cache operations through command-line interface

### Platform Detection

```mermaid
graph LR
    subgraph "Platform Detection Flow"
        OS[Operating System] --> Detector[Platform Detector]
        Arch[Architecture] --> Detector
        Detector --> Platform[BrowserPlatform]
        Platform --> Cache[Cache System]
        Cache --> InstallPath[Installation Path]
    end
```

## Metadata Management

The cache system maintains metadata for each browser type:

```mermaid
graph TB
    subgraph "Metadata Structure"
        MetadataFile[.metadata File] --> Aliases[aliases: Record<string, string>]
        Aliases --> Latest[latest → buildId]
        Aliases --> Canary[canary → buildId]
        Aliases --> Dev[dev → buildId]
        Aliases --> Custom[custom-alias → buildId]
    end
    
    subgraph "Metadata Operations"
        Read[readMetadata] --> Parse[JSON Parse]
        Write[writeMetadata] --> Stringify[JSON Stringify]
        Resolve[resolveAlias] --> Lookup[Alias Lookup]
        Resolve --> Sort[Version Sort for 'latest']
    end
```

## Error Handling and Resilience

The cache system implements robust error handling:

```mermaid
flowchart TD
    Operation[Cache Operation] --> TryExecute{Try Execute}
    TryExecute -->|Success| Success[Return Result]
    TryExecute -->|File Error| RetryLogic{Retry Available?}
    TryExecute -->|Parse Error| ValidationError[Validation Error]
    TryExecute -->|Platform Error| PlatformError[Platform Detection Error]
    
    RetryLogic -->|Yes| Retry[Retry with Delay]
    RetryLogic -->|No| FailGracefully[Fail Gracefully]
    
    Retry --> TryExecute
    ValidationError --> DefaultValue[Return Default Value]
    PlatformError --> ThrowError[Throw Descriptive Error]
    
    Success --> End([End])
    FailGracefully --> End
    DefaultValue --> End
    ThrowError --> End
```

## Performance Considerations

### Caching Strategy

- **Lazy Loading**: Metadata is read only when needed
- **Directory Scanning**: Efficient traversal of cache directories
- **Version Sorting**: Optimized version comparison for alias resolution

### File System Operations

- **Atomic Operations**: Metadata writes are atomic to prevent corruption
- **Retry Logic**: Built-in retry mechanism for file system operations
- **Cleanup**: Efficient removal of unused installations

## Usage Examples

### Basic Cache Operations

```typescript
// Create cache instance
const cache = new Cache('/path/to/cache');

// Get installed browsers
const browsers = cache.getInstalledBrowsers();

// Compute executable path
const executablePath = cache.computeExecutablePath({
  browser: Browser.CHROME,
  buildId: 'latest',
  platform: BrowserPlatform.LINUX
});

// Manage metadata
const metadata = cache.readMetadata(Browser.CHROME);
metadata.aliases['stable'] = '123456';
cache.writeMetadata(Browser.CHROME, metadata);
```

### Installation Management

```typescript
// Install browser
const installedBrowser = new InstalledBrowser(
  cache,
  Browser.CHROME,
  '123456',
  BrowserPlatform.LINUX
);

// Access installation details
console.log(installedBrowser.path);
console.log(installedBrowser.executablePath);

// Uninstall browser
cache.uninstall(Browser.CHROME, BrowserPlatform.LINUX, '123456');
```

## Dependencies

The cache_management module depends on:

- **Node.js File System APIs**: For directory and file operations
- **Platform Detection**: For determining the appropriate browser platform
- **Browser Data**: For browser-specific executable path resolution
- **Debug Logging**: For troubleshooting and monitoring

## Security Considerations

- **Path Validation**: All paths are validated to prevent directory traversal
- **Metadata Integrity**: JSON parsing includes error handling for malformed data
- **File Permissions**: Proper file system permissions are maintained
- **Cleanup Safety**: Safe removal operations with retry logic

## Future Enhancements

- **Compression**: Support for compressed browser installations
- **Checksums**: Integrity verification for cached binaries
- **Distributed Caching**: Support for shared cache across multiple systems
- **Cache Policies**: Configurable retention and cleanup policies