# Update Check Module Documentation

## Introduction

The update_check module is responsible for managing automatic and user-initiated software updates in SumatraPDF. It handles version checking, update notifications, and the download/installation process for new versions. The module ensures users stay current with the latest features and security updates while providing control over the update process.

## Core Architecture

### Primary Components

The module centers around the `UpdateInfo` structure which encapsulates all update-related information:

```cpp
struct UpdateInfo {
    HWND hwndParent = nullptr;
    const char* latestVer = nullptr;
    const char* installer64 = nullptr;
    const char* installerArm64 = nullptr;
    const char* installer32 = nullptr;
    const char* portable64 = nullptr;
    const char* portableArm64 = nullptr;
    const char* portable32 = nullptr;
    const char* dlURL = nullptr;
    const char* installerPath = nullptr;
};
```

### Update Information Format

Update information is retrieved from remote servers in a structured format:

```
[SumatraPDF]
Latest: 14276
Installer64: https://www.sumatrapdfreader.org/dl/prerel/14276/SumatraPDF-prerel-64-install.exe
Installer32: https://www.sumatrapdfreader.org/dl/prerel/14276/SumatraPDF-prerel-install.exe
PortableExe64: https://www.sumatrapdfreader.org/dl/prerel/14276/SumatraPDF-prerel-64.exe
PortableExe32: https://www.sumatrapdfreader.org/dl/prerel/14276/SumatraPDF-prerel.exe
PortableZip64: https://www.sumatrapdfreader.org/dl/prerel/14276/SumatraPDF-prerel-64.zip
PortableZip32: https://www.sumatrapdfreader.org/dl/prerel/14276/SumatraPDF-prerel.zip
```

## System Architecture

### Module Dependencies

The update_check module integrates with several other system components:

```mermaid
graph TD
    UC[Update Check Module]
    HU[HttpUtil]
    STP[SquareTreeParser]
    TU[ThreadUtil]
    UT[UITask]
    SP[Settings/Preferences]
    NW[Notifications]
    WU[WinUtil]
    
    UC --> HU
    UC --> STP
    UC --> TU
    UC --> UT
    UC --> SP
    UC --> NW
    UC --> WU
    
    HU -.->|HTTP Requests| Internet
    STP -.->|Parse| UpdateInfo
    TU -.->|Async Operations| BackgroundThreads
    UT -.->|UI Updates| MainThread
    SP -.->|Read/Write| ConfigFiles
    NW -.->|Display| UserInterface
```

### Update Check Flow

```mermaid
sequenceDiagram
    participant User
    participant UI[UI Thread]
    participant UC[Update Check]
    participant HTTP[HTTP Client]
    participant Parser[SquareTree Parser]
    participant Downloader[File Downloader]
    
    User->>UI: Trigger Update Check
    UI->>UC: StartAsyncUpdateCheck()
    UC->>UC: ShouldCheckForUpdate()
    alt Should Check
        UC->>HTTP: HttpGet(updateInfoURL)
        HTTP-->>UC: Response Data
        UC->>Parser: ParseUpdateInfo()
        Parser-->>UC: UpdateInfo Structure
        UC->>UC: ShouldDownloadUpdate()
        alt Should Download
            UC->>Downloader: DownloadUpdateAsync()
            Downloader-->>UC: Download Complete
            UC->>UI: NotifyUserOfUpdate()
            UI-->>User: Update Available Dialog
        else No Update Available
            UC->>UI: Show "Latest Version" Message
        end
    else Skip Check
        UC-->>UI: Return Early
    end
```

## Update Check Logic

### Update Check Types

The module supports two types of update checks:

1. **Automatic Update Check**: Triggered periodically based on user preferences
2. **User-Initiated Update Check**: Triggered explicitly by user action

### Update Check Conditions

```mermaid
graph TD
    Start[Update Check Request]
    StoreBuild{Is Store Build?}
    InProgress{Check In Progress?}
    Permission{Has Internet Permission?}
    UserInitiated{User Initiated?}
    SavePrefs{Can Save Preferences?}
    CheckEnabled{Updates Enabled?}
    FirstStart{First Start?}
    TimeCheck{Time Since Last Check}
    Proceed[Proceed with Check]
    Skip[Skip Check]
    
    Start --> StoreBuild
    StoreBuild -->|Yes| Skip
    StoreBuild -->|No| InProgress
    InProgress -->|Yes| Skip
    InProgress -->|No| Permission
    Permission -->|No| Skip
    Permission -->|Yes| UserInitiated
    UserInitiated -->|Yes| Proceed
    UserInitiated -->|No| SavePrefs
    SavePrefs -->|No| Skip
    SavePrefs -->|Yes| CheckEnabled
    CheckEnabled -->|No| Skip
    CheckEnabled -->|Yes| FirstStart
    FirstStart -->|Yes| Skip
    FirstStart -->|No| TimeCheck
    TimeCheck -->|Sufficient| Proceed
    TimeCheck -->|Insufficient| Skip
```

### Version Comparison Logic

The update check compares versions using a sophisticated comparison algorithm:

```mermaid
graph TD
    Parse[Parse Update Info]
    GetCurrent[Get Current Version]
    Compare[Compare Versions]
    SkipVersion{User Skip This Version?}
    DebugBuild{Debug Build?}
    HasUpdate{Has Update?}
    Download[Download Update]
    Skip[Skip Update]
    
    Parse --> GetCurrent
    GetCurrent --> Compare
    Compare --> HasUpdate
    HasUpdate -->|Yes| SkipVersion
    HasUpdate -->|No| Skip
    SkipVersion -->|Yes| Skip
    SkipVersion -->|No| DebugBuild
    DebugBuild -->|Yes| UserInitiated
    DebugBuild -->|No| Download
    UserInitiated -->|Yes| Download
    UserInitiated -->|No| Skip
```

## Update Download and Installation

### Download Process

```mermaid
sequenceDiagram
    participant UC[Update Check]
    participant HTTP[HTTP Client]
    participant FS[File System]
    participant UI[UI Thread]
    
    UC->>HTTP: HttpGetToFile(dlURL, tempPath)
    loop Download Progress
        HTTP-->>UC: Progress Callback
        UC->>UI: Update Notification
    end
    HTTP-->>UC: Download Complete
    alt Download Success
        UC->>FS: Store Installer Path
        UC->>UI: NotifyUserOfUpdate()
    else Download Failed
        UC->>FS: Delete Partial File
        UC->>UI: Show Error
    end
```

### Installation Process

The module supports two installation scenarios:

1. **DLL Build**: Launches installer with appropriate flags
2. **Portable Build**: Self-update mechanism with file replacement

```mermaid
graph TD
    UserAccept{User Accepts Update?}
    SkipVersion[Skip This Version]
    DownloadExists{Installer Downloaded?}
    GoToWebsite[Open Download Page]
    IsDllBuild{Is DLL Build?}
    LaunchInstaller[Launch Installer]
    SelfUpdate[Self Update Process]
    ExitApp[Exit Application]
    
    UserAccept -->|No| SkipVersion
    UserAccept -->|Yes| DownloadExists
    DownloadExists -->|No| GoToWebsite
    DownloadExists -->|Yes| IsDllBuild
    IsDllBuild -->|Yes| LaunchInstaller
    IsDllBuild -->|No| SelfUpdate
    LaunchInstaller --> ExitApp
    SelfUpdate --> ExitApp
```

## Error Handling and Fallbacks

### URL Fallback Strategy

The module implements a robust fallback mechanism for update server URLs:

1. **Primary URL**: Main update server (sumatrapdfreader.org)
2. **Secondary URL**: Backup server (Backblaze B2 storage)

### Error Scenarios

```mermaid
graph TD
    HTTPError{HTTP Error?}
    StatusError{Non-200 Status?}
    InvalidURL{Invalid URL?}
    EmptyResponse{Empty Response?}
    ParseError{Parse Error?}
    ShowNetworkError[Show Network Error]
    LogError[Log Error]
    
    HTTPError -->|Yes| ShowNetworkError
    StatusError -->|Yes| LogError
    InvalidURL -->|Yes| LogError
    EmptyResponse -->|Yes| LogError
    ParseError -->|Yes| LogError
```

## Integration with Other Modules

### Settings and Preferences

The update_check module interacts with the [settings](settings.md) module to:
- Read update check preferences (`checkForUpdates`)
- Store last update check timestamp (`timeOfLastUpdateCheck`)
- Manage version skip preferences (`versionToSkip`)

### Notifications System

Integration with the [notifications](notifications.md) module provides:
- Progress notifications during download
- Update availability notifications
- Error notifications for failed checks

### UI Components

The module leverages [ui_components](ui_components.md) for:
- Update dialog presentation
- User interaction handling
- Progress indication

## Security Considerations

### Certificate and Network Security

- Uses HTTPS for all update communications
- Implements certificate validation
- Provides fallback for older Windows versions with limited cipher support
- Validates response format before parsing

### Update Verification

- Validates version strings before processing
- Checks URL authenticity
- Implements permission-based access control
- Provides user consent mechanisms

## Configuration and URLs

### Update URLs

```cpp
// Pre-release builds
constexpr const char* kUpdateInfoURL = "https://www.sumatrapdfreader.org/updatecheck-pre-release.txt";
constexpr const char* kUpdateInfoURL2 = "https://kjk-files.s3.us-west-001.backblazeb2.com/software/sumatrapdf/sumpdf-prerelease-update.txt";

// Release builds
constexpr const char* kUpdateInfoURL = "https://www.sumatrapdfreader.org/update-check-rel.txt";
constexpr const char* kUpdateInfoURL2 = "https://www.sumatrapdfreader.org/update-check-rel.txt";
```

### Download Page URLs

```cpp
// Pre-release builds
#define kWebisteDownloadPageURL "https://www.sumatrapdfreader.org/prerelease"

// Release builds
#define kWebisteDownloadPageURL "https://www.sumatrapdfreader.org/download-free-pdf-viewer"
```

## Threading Model

The update_check module implements a multi-threaded architecture:

1. **UI Thread**: Handles user interface updates and notifications
2. **Background Thread**: Performs HTTP requests and file downloads
3. **Task Queue**: Coordinates between threads using the UITask system

```mermaid
graph TD
    UI[UI Thread]
    BG[Background Thread]
    TQ[Task Queue]
    
    UI -->|StartAsyncUpdateCheck| TQ
    TQ -->|UpdateCheckAsync| BG
    BG -->|HttpGet| HTTP
    BG -->|UpdateCheckFinish| TQ
    TQ -->|NotifyUserOfUpdate| UI
    
    UI -->|DownloadUpdateAsync| TQ
    TQ -->|DownloadUpdateAsync| BG
    BG -->|HttpGetToFile| HTTP
    BG -->|DownloadUpdateFinish| TQ
    TQ -->|UpdateDownloadProgressNotif| UI
```

This architecture ensures responsive user interface while performing network operations and file downloads in the background.