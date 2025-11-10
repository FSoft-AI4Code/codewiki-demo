# GitHubAuthentication Module Documentation

## Overview

The GitHubAuthentication module provides comprehensive authentication capabilities for GitHub repositories, supporting multiple authentication methods including OAuth2, personal access tokens, basic authentication, and two-factor authentication. It serves as the primary authentication interface for GitHub operations within the Git Credential Manager ecosystem.

## Purpose and Core Functionality

The module is designed to:
- Handle various GitHub authentication scenarios (OAuth2 browser flow, device code flow, personal access tokens, basic auth)
- Provide user-friendly authentication prompts via GUI, terminal, or helper applications
- Support two-factor authentication for enhanced security
- Manage account selection for multi-account scenarios
- Integrate seamlessly with Git operations requiring authentication

## Architecture

### Component Structure

```mermaid
classDiagram
    class IGitHubAuthentication {
        <<interface>>
        +SelectAccountAsync(targetUri, accounts) Task<string>
        +GetAuthenticationAsync(targetUri, userName, modes) Task<AuthenticationPromptResult>
        +GetTwoFactorCodeAsync(targetUri, isSms) Task<string>
        +GetOAuthTokenViaBrowserAsync(targetUri, scopes, loginHint) Task<OAuth2TokenResult>
        +GetOAuthTokenViaDeviceCodeAsync(targetUri, scopes) Task<OAuth2TokenResult>
    }

    class AuthenticationPromptResult {
        +AuthenticationMode: AuthenticationModes
        +Credential: ICredential
        +AuthenticationPromptResult(mode, credential)
    }

    class GitHubAuthentication {
        -HttpClient: HttpClient
        -AuthorityIds: string[]
        +GitHubAuthentication(context)
        +SelectAccountAsync(targetUri, accounts) Task<string>
        +GetAuthenticationAsync(targetUri, userName, modes) Task<AuthenticationPromptResult>
        +GetTwoFactorCodeAsync(targetUri, isSms) Task<string>
        +GetOAuthTokenViaBrowserAsync(targetUri, scopes, loginHint) Task<OAuth2TokenResult>
        +GetOAuthTokenViaDeviceCodeAsync(targetUri, scopes) Task<OAuth2TokenResult>
        +Dispose()
    }

    class AuthenticationModes {
        <<enumeration>>
        None
        Basic
        Browser
        Pat
        Device
        OAuth
        All
    }

    IGitHubAuthentication <|-- GitHubAuthentication
    GitHubAuthentication ..> AuthenticationPromptResult
    GitHubAuthentication ..> AuthenticationModes
```

### Module Dependencies

```mermaid
graph TD
    GitHubAuthentication --> Core.Authentication.OAuthAuthentication[OAuthAuthentication]
    GitHubAuthentication --> Core.Authentication.OAuth[OAuth2 Components]
    GitHubAuthentication --> Core.UI[UI Framework]
    GitHubAuthentication --> Core.Settings[Settings]
    GitHubAuthentication --> Core.Environment[Environment]
    GitHubAuthentication --> Core.Terminal[Terminal]
    GitHubAuthentication --> Core.SessionManager[Session Manager]
    GitHubAuthentication --> GitHubOAuth2Client[GitHubOAuth2Client]
    GitHubAuthentication --> GitHubHostProvider[GitHubHostProvider]
    GitHubAuthentication --> GitHubUI[GitHub UI Components]

    GitHubOAuth2Client --> Core.Authentication.OAuth
    GitHubHostProvider --> Core.HostProvider
    GitHubUI --> Core.UI
```

## Core Components

### IGitHubAuthentication Interface
The primary interface defining the contract for GitHub authentication operations:

- **SelectAccountAsync**: Presents account selection for multi-account scenarios
- **GetAuthenticationAsync**: Main authentication method supporting multiple modes
- **GetTwoFactorCodeAsync**: Handles two-factor authentication code collection
- **GetOAuthTokenViaBrowserAsync**: Implements OAuth2 browser flow
- **GetOAuthTokenViaDeviceCodeAsync**: Implements OAuth2 device code flow

### AuthenticationPromptResult
Encapsulates the result of authentication prompts:
- **AuthenticationMode**: The selected authentication method
- **Credential**: Optional credential object (for non-OAuth methods)

### GitHubAuthentication Class
The main implementation providing:
- Multi-modal authentication support (Basic, OAuth, PAT, Device Code)
- Adaptive UI selection (GUI, Terminal, Helper application)
- Two-factor authentication handling
- OAuth2 flow management
- Resource cleanup via IDisposable

## Authentication Flows

### Authentication Mode Selection

```mermaid
flowchart TD
    Start[Authentication Request] --> CheckModes{Available Modes?}
    CheckModes -->|Single Mode| DirectReturn[Return Mode Directly]
    CheckModes -->|Multiple Modes| CheckInteraction{User Interaction Enabled?}
    
    CheckInteraction -->|No| Error[Throw Exception]
    CheckInteraction -->|Yes| CheckGUI{GUI Available?}
    
    CheckGUI -->|Yes| CheckHelper{Helper Available?}
    CheckHelper -->|Yes| HelperFlow[Helper Authentication]
    CheckHelper -->|No| UIFlow[UI Authentication]
    
    CheckGUI -->|No| TTYFlow[Terminal Authentication]
    
    HelperFlow --> ReturnResult[Return Result]
    UIFlow --> ReturnResult
    TTYFlow --> ReturnResult
    DirectReturn --> ReturnResult
```

### OAuth2 Browser Flow

```mermaid
sequenceDiagram
    participant User
    participant GitHubAuth
    participant OAuthClient
    participant Browser
    participant GitHubAPI

    User->>GitHubAuth: Request OAuth Authentication
    GitHubAuth->>OAuthClient: Create GitHubOAuth2Client
    GitHubAuth->>Browser: Launch System Browser
    GitHubAuth->>User: Display "Complete in Browser" Message
    
    Browser->>GitHubAPI: Authorization Request
    GitHubAPI->>Browser: Authorization Code
    Browser->>GitHubAuth: Return Authorization Code
    
    GitHubAuth->>OAuthClient: Exchange Code for Token
    OAuthClient->>GitHubAPI: Token Request with Code
    GitHubAPI->>OAuthClient: Access Token
    OAuthClient->>GitHubAuth: Return OAuth2TokenResult
    GitHubAuth->>User: Authentication Complete
```

### Device Code Flow

```mermaid
sequenceDiagram
    participant User
    participant GitHubAuth
    participant OAuthClient
    participant GitHubAPI
    participant DeviceDisplay

    User->>GitHubAuth: Request Device Code Authentication
    GitHubAuth->>OAuthClient: Create GitHubOAuth2Client
    GitHubAuth->>OAuthClient: Request Device Code
    OAuthClient->>GitHubAPI: Device Code Request
    GitHubAPI->>OAuthClient: Device Code + Verification URI
    OAuthClient->>GitHubAuth: Return Device Code Result
    
    GitHubAuth->>DeviceDisplay: Show Device Code & URI
    GitHubAuth->>User: Display Instructions
    
    par Parallel Execution
        User->>GitHubAPI: Manual Authorization
        GitHubAuth->>OAuthClient: Poll for Token
    end
    
    GitHubAPI->>OAuthClient: Return Access Token
    OAuthClient->>GitHubAuth: Return OAuth2TokenResult
    GitHubAuth->>DeviceDisplay: Close Display
    GitHubAuth->>User: Authentication Complete
```

## User Interface Adaptation

The module adapts to different environments and user preferences:

### GUI Mode (Desktop Sessions)
- **Avalonia UI**: Modern cross-platform UI framework
- **Helper Applications**: External authentication helpers
- **Rich User Experience**: Full-featured dialogs and forms

### Terminal Mode (SSH/Headless)
- **Interactive Prompts**: Command-line input collection
- **Menu Selection**: Terminal-based option selection
- **Minimal Dependencies**: No GUI requirements

### Helper Application Mode
- **External Tools**: Pluggable authentication helpers
- **Process Communication**: Standard input/output protocols
- **Flexible Integration**: Custom authentication implementations

## Integration Points

### Core Dependencies
- **[CommandContext](Core.md)**: Provides execution context and services
- **[OAuth2Client](OAuth2.md)**: Handles OAuth2 protocol implementation
- **[GitHubHostProvider](GitHubHostProvider.md)**: GitHub-specific host integration
- **[ICredentialStore](CredentialManagement.md)**: Credential persistence

### Platform Integration
- **Windows**: DPAPI credential storage, Windows Credential Manager
- **macOS**: Keychain integration, native dialogs
- **Linux**: Secret Service, GPG pass store

## Security Considerations

### Authentication Security
- **Secure Storage**: Platform-specific encrypted credential storage
- **Token Management**: OAuth tokens with proper expiration handling
- **Input Validation**: Sanitization of user inputs and URLs
- **HTTPS Enforcement**: All OAuth flows use secure connections

### Two-Factor Authentication
- **TOTP Support**: Time-based one-time passwords
- **SMS Support**: SMS-delivered authentication codes
- **Fallback Mechanisms**: Multiple 2FA method support

## Error Handling

### Exception Types
- **Trace2Exception**: Traced errors with diagnostic information
- **InvalidOperationException**: Invalid authentication state
- **ArgumentException**: Invalid parameter validation
- **HttpRequestException**: Network-related failures

### User Experience
- **Graceful Degradation**: Fallback to alternative authentication methods
- **Clear Error Messages**: User-friendly error descriptions
- **Retry Mechanisms**: Automatic retry for transient failures

## Configuration

### Environment Variables
- `GCM_GITHUB_AUTH_HELPER`: Specifies authentication helper command
- `GCM_GUI_PROMPT`: Controls GUI prompt preference
- `GCM_TERMINAL_PROMPT`: Controls terminal prompt preference

### Git Configuration
- `credential.github.authHelper`: Repository-specific helper configuration
- `credential.github.provider`: Authentication provider selection

## Usage Examples

### Basic Authentication
```csharp
var auth = new GitHubAuthentication(context);
var result = await auth.GetAuthenticationAsync(
    targetUri: new Uri("https://github.com"),
    userName: null,
    modes: AuthenticationModes.Basic | AuthenticationModes.Pat
);
```

### OAuth2 Browser Flow
```csharp
var tokenResult = await auth.GetOAuthTokenViaBrowserAsync(
    targetUri: new Uri("https://github.com"),
    scopes: new[] { "repo", "user" },
    loginHint: "user@example.com"
);
```

### Device Code Flow
```csharp
var tokenResult = await auth.GetOAuthTokenViaDeviceCodeAsync(
    targetUri: new Uri("https://github.com"),
    scopes: new[] { "repo", "user" }
);
```

## Related Documentation

- [Core Authentication Framework](Core.Authentication.md)
- [OAuth2 Implementation](OAuth2.md)
- [GitHub Host Provider](GitHubHostProvider.md)
- [Credential Management](CredentialManagement.md)
- [UI Framework](Core.UI.md)
- [Platform Integration](Platform.md)