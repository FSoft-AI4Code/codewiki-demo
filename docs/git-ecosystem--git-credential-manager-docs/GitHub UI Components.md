# GitHub UI Components Module

## Introduction

The GitHub UI Components module provides specialized user interface components for GitHub authentication and account management within the Git Credential Manager (GCM) system. This module extends the core UI framework with GitHub-specific views, view models, and custom controls designed to handle various authentication scenarios including OAuth, device code flow, two-factor authentication, and account selection.

## Architecture Overview

The GitHub UI Components module follows the Model-View-ViewModel (MVVM) pattern and integrates with the Avalonia UI framework. It provides a cohesive set of components that handle the complete GitHub authentication user experience.

```mermaid
graph TB
    subgraph "GitHub UI Components Module"
        VM[ViewModels]
        V[Views]
        C[Controls]
        
        subgraph "Authentication Flows"
            CVM[CredentialsViewModel]
            DCVM[DeviceCodeViewModel]
            TFVM[TwoFactorViewModel]
            SAVM[SelectAccountViewModel]
        end
        
        subgraph "UI Components"
            CV[CredentialsView]
            DCV[DeviceCodeView]
            TFV[TwoFactorView]
            SAV[SelectAccountView]
            SDI[SixDigitInput]
            HSD[HorizontalShadowDivider]
        end
    end
    
    subgraph "Core Dependencies"
        WVM[WindowViewModel]
        ENV[IEnvironment]
        PM[IProcessManager]
        BU[BrowserUtils]
    end
    
    VM --> WVM
    CVM --> ENV
    CVM --> PM
    DCVM --> ENV
    TFVM --> ENV
    TFVM --> PM
    SAVM --> ENV
    
    CV --> CVM
    DCV --> DCVM
    TFV --> TFVM
    SAV --> SAVM
    SDI --> IF
    
    CVM --> BU
    DCVM --> BU
    TFVM --> BU
    SAVM --> BU
```

## Component Architecture

### ViewModels Layer

The ViewModels layer implements the business logic for GitHub authentication scenarios:

```mermaid
classDiagram
    class WindowViewModel {
        <<abstract>>
        +Title: string
        +Accept()
        +Cancel()
    }
    
    class CredentialsViewModel {
        -IEnvironment _environment
        -IProcessManager _processManager
        +EnterpriseUrl: string
        +Token: string
        +UserName: string
        +Password: string
        +ShowBrowserLogin: bool
        +ShowDeviceLogin: bool
        +ShowTokenLogin: bool
        +ShowBasicLogin: bool
        +SelectedMode: AuthenticationModes
        +SignUpCommand: ICommand
        +SignInBrowserCommand: ICommand
        +SignInDeviceCommand: ICommand
        +SignInTokenCommand: RelayCommand
        +SignInBasicCommand: RelayCommand
    }
    
    class DeviceCodeViewModel {
        -IEnvironment _environment
        +UserCode: string
        +VerificationUrl: string
        +VerificationUrlCommand: ICommand
    }
    
    class TwoFactorViewModel {
        -IEnvironment _environment
        -IProcessManager _processManager
        +Code: string
        +IsSms: bool
        +Description: string
        +LearnMoreCommand: ICommand
        +VerifyCommand: RelayCommand
    }
    
    class SelectAccountViewModel {
        -IEnvironment _environment
        +SelectedAccount: AccountViewModel
        +EnterpriseUrl: string
        +Accounts: ObservableCollection~AccountViewModel~
        +ContinueCommand: RelayCommand
        +NewAccountCommand: ICommand
        +LearnMoreCommand: ICommand
        +ShowHelpLink: bool
    }
    
    class AccountViewModel {
        +UserName: string
    }
    
    WindowViewModel <|-- CredentialsViewModel
    WindowViewModel <|-- DeviceCodeViewModel
    WindowViewModel <|-- TwoFactorViewModel
    WindowViewModel <|-- SelectAccountViewModel
    ViewModel <|-- AccountViewModel
```

### Views Layer

The Views layer provides the visual representation and user interaction handling:

```mermaid
graph LR
    subgraph "View Components"
        CV[CredentialsView]
        DCV[DeviceCodeView]
        TFV[TwoFactorView]
        SAV[SelectAccountView]
    end
    
    subgraph "Interface Implementation"
        IF[IFocusable]
    end
    
    subgraph "Platform Integration"
        AU[Avalonia UserControl]
        PM[PlatformUtils]
    end
    
    CV -.->|implements| IF
    TFV -.->|implements| IF
    
    CV --> AU
    DCV --> AU
    TFV --> AU
    SAV --> AU
    
    CV -.->|uses| PM
    TFV -.->|uses| PM
```

### Controls Layer

Custom controls provide specialized UI elements for GitHub-specific interactions:

```mermaid
graph TD
    subgraph "Custom Controls"
        SDI[SixDigitInput]
        HSD[HorizontalShadowDivider]
    end
    
    subgraph "Avalonia Base"
        UC[UserControl]
        DP[DependencyProperty]
    end
    
    subgraph "Interfaces"
        IF[IFocusable]
    end
    
    subgraph "Functionality"
        KB[Keyboard Navigation]
        PT[Paste Handling]
        VF[Validation]
        FC[Focus Control]
    end
    
    SDI --> UC
    HSD --> UC
    
    SDI -.->|implements| IF
    
    SDI --> KB
    SDI --> PT
    SDI --> VF
    SDI --> FC
```

## Authentication Flow Integration

The GitHub UI Components integrate with the broader authentication system:

```mermaid
sequenceDiagram
    participant User
    participant GitHubAuth
    participant CredentialsVM
    participant CredentialsV
    participant Browser
    
    User->>GitHubAuth: Initiate authentication
    GitHubAuth->>CredentialsVM: Create with available modes
    CredentialsVM->>CredentialsV: Bind data context
    CredentialsV->>User: Display authentication options
    
    alt Browser Authentication
        User->>CredentialsV: Click "Sign in with Browser"
        CredentialsV->>CredentialsVM: Execute SignInBrowserCommand
        CredentialsVM->>GitHubAuth: Set SelectedMode = Browser
        GitHubAuth->>Browser: Open OAuth flow
    else Device Code Authentication
        User->>CredentialsV: Click "Sign in with Device"
        CredentialsV->>CredentialsVM: Execute SignInDeviceCommand
        CredentialsVM->>GitHubAuth: Set SelectedMode = Device
        GitHubAuth->>DeviceCodeVM: Create device code flow
    else Token Authentication
        User->>CredentialsV: Enter PAT token
        CredentialsV->>CredentialsVM: Update Token property
        User->>CredentialsV: Click "Sign in with Token"
        CredentialsV->>CredentialsVM: Execute SignInTokenCommand
        CredentialsVM->>GitHubAuth: Set SelectedMode = Pat
    else Basic Authentication
        User->>CredentialsV: Enter username/password
        CredentialsV->>CredentialsVM: Update credentials
        User->>CredentialsV: Click "Sign in with Basic Auth"
        CredentialsV->>CredentialsVM: Execute SignInBasicCommand
        CredentialsVM->>GitHubAuth: Set SelectedMode = Basic
    end
```

## Key Features

### Multi-Modal Authentication Support

The CredentialsViewModel supports four authentication modes:
- **Browser OAuth**: Redirects to GitHub's web-based OAuth flow
- **Device Code**: Provides device code for authentication on another device
- **Personal Access Token**: Direct token-based authentication
- **Basic Authentication**: Username/password credentials

### Two-Factor Authentication

The TwoFactorViewModel handles both SMS and authenticator app-based 2FA:
- Six-digit code input with validation
- Context-aware descriptions based on 2FA method
- Help link integration for user assistance

### Account Selection

The SelectAccountViewModel manages multiple GitHub accounts:
- Account list presentation with selection
- New account creation option
- Enterprise URL support for GitHub Enterprise instances

### Custom Input Controls

The SixDigitInput control provides specialized 2FA code entry:
- Automatic tab navigation between digit fields
- Paste support for complete codes
- Keyboard filtering for numeric input only
- Cross-platform focus management

## Dependencies

The GitHub UI Components module depends on several core systems:

```mermaid
graph TB
    subgraph "GitHub UI Components"
        GITHUB_VM[GitHub ViewModels]
        GITHUB_V[GitHub Views]
        GITHUB_C[GitHub Controls]
    end
    
    subgraph "Core UI Framework"
        CORE_VM[WindowViewModel]
        CORE_V[Views]
        CORE_C[Controls]
        DISPATCH[Dispatcher]
    end
    
    subgraph "Core Infrastructure"
        ENV[Environment]
        PROC[ProcessManager]
        BROWSER[BrowserUtils]
        PLATFORM[PlatformUtils]
    end
    
    subgraph "External Libraries"
        AVALONIA[Avalonia UI]
        REACTIVE[ReactiveUI]
    end
    
    GITHUB_VM --> CORE_VM
    GITHUB_V --> CORE_V
    GITHUB_C --> CORE_C
    
    GITHUB_VM --> ENV
    GITHUB_VM --> PROC
    GITHUB_VM --> BROWSER
    GITHUB_V --> PLATFORM
    GITHUB_C --> PLATFORM
    
    CORE_V --> AVALONIA
    CORE_C --> AVALONIA
    CORE_VM --> REACTIVE
```

## Data Flow

### Authentication Mode Selection

```mermaid
graph LR
    subgraph "User Interaction"
        UI[User Interface]
        CMD[Command Execution]
    end
    
    subgraph "ViewModel Processing"
        PROP[Property Updates]
        VALID[Validation]
        MODE[Mode Selection]
    end
    
    subgraph "Authentication System"
        AUTH[GitHub Authentication]
        FLOW[Authentication Flow]
    end
    
    UI -->|user input| PROP
    CMD -->|execute| VALID
    VALID -->|success| MODE
    MODE -->|set| AUTH
    AUTH -->|initiate| FLOW
```

### Two-Factor Code Entry

```mermaid
graph TD
    subgraph "SixDigitInput Control"
        INPUT[Digit Input]
        NAV[Auto Navigation]
        VALID[Code Validation]
        PASTE[Paste Handling]
    end
    
    subgraph "TwoFactorViewModel"
        CODE[Code Property]
        VERIFY[VerifyCommand]
        ENABLE[Command Enable]
    end
    
    subgraph "Authentication Service"
        SUBMIT[Code Submission]
        RESULT[Auth Result]
    end
    
    INPUT -->|6 digits| CODE
    NAV -->|auto-tab| INPUT
    PASTE -->|complete code| CODE
    CODE -->|length=6| ENABLE
    VERIFY -->|execute| SUBMIT
    SUBMIT -->|response| RESULT
```

## Platform Considerations

The GitHub UI Components include platform-specific workarounds and optimizations:

### macOS Focus Management
Due to platform limitations, certain focus operations are disabled on macOS to prevent UI issues.

### Cross-Platform Browser Integration
Browser opening functionality adapts to platform-specific URL handling mechanisms.

### Input Validation
Keyboard input filtering ensures consistent behavior across Windows, macOS, and Linux platforms.

## Integration Points

### Host Provider Integration
The UI components integrate with the [GitHub Provider](GitHub Provider.md) module to provide authentication services.

### Core UI Framework
Components extend the base classes provided by the [UI Framework](UI Framework.md) module.

### Authentication System
UI flows coordinate with the [Authentication System](Authentication System.md) for credential validation and storage.

## Usage Patterns

### Basic Authentication Flow
```csharp
// Create credentials view model
var vm = new CredentialsViewModel(environment, processManager);

// Configure available authentication modes
vm.ShowBrowserLogin = true;
vm.ShowTokenLogin = true;
vm.ShowBasicLogin = true;

// Handle authentication result
if (vm.ShowDialog() == true)
{
    var selectedMode = vm.SelectedMode;
    // Process authentication based on selected mode
}
```

### Two-Factor Authentication
```csharp
// Create 2FA view model
var vm = new TwoFactorViewModel(environment, processManager);
vm.IsSms = false; // or true for SMS

// Get user input
if (vm.ShowDialog() == true)
{
    var code = vm.Code;
    // Submit 2FA code
}
```

### Account Selection
```csharp
// Create account selection view model
var accounts = new[] { "user1", "user2", "user3" };
var vm = new SelectAccountViewModel(environment, accounts);

// Handle selection
if (vm.ShowDialog() == true)
{
    var selectedAccount = vm.SelectedAccount;
    if (selectedAccount == null)
    {
        // New account flow
    }
    else
    {
        // Existing account flow
    }
}
```

## Error Handling

The GitHub UI Components implement comprehensive error handling:

- **Input Validation**: Real-time validation of user inputs with visual feedback
- **Command Validation**: Enable/disable commands based on input validity
- **Platform Error Handling**: Graceful handling of platform-specific issues
- **Browser Integration**: Fallback mechanisms for browser opening failures

## Security Considerations

- **Credential Masking**: Password and token inputs are masked in the UI
- **Secure Storage**: Credentials are passed to secure storage systems, not persisted in UI components
- **Input Sanitization**: All user inputs are validated and sanitized before processing
- **Browser Security**: OAuth flows use system default browsers for security

## Testing

The module supports comprehensive testing through:

- **Mock Dependencies**: All external dependencies are interface-based for easy mocking
- **Designer Support**: ViewModels include parameterless constructors for XAML designer support
- **Platform Testing**: Platform-specific code paths can be tested with appropriate mocks
- **UI Automation**: Custom controls support UI automation for testing frameworks