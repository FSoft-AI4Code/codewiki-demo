# GitLab Authentication Module

## Introduction

The GitLab Authentication module provides comprehensive authentication capabilities for GitLab repositories within the Git Credential Manager ecosystem. It implements multiple authentication methods including OAuth 2.0 browser flow, personal access tokens (PAT), and basic authentication, offering flexible and secure authentication options for GitLab users.

This module serves as the authentication gateway for GitLab operations, handling user credential acquisition, token management, and authentication flow orchestration while maintaining compatibility with Git Credential Manager's unified authentication framework.

## Architecture Overview

The GitLab Authentication module is built on a layered architecture that integrates with the broader authentication system while providing GitLab-specific implementations:

```mermaid
graph TB
    subgraph "GitLab Authentication Layer"
        GLA[GitLabAuthentication]
        IGLA[IGitLabAuthentication]
        GLC[GitLabOAuth2Client]
        GLV[CredentialsViewModel]
        GLCV[CredentialsView]
    end
    
    subgraph "Core Authentication Framework"
        OA[OAuthAuthentication]
        IOA[IOAuthAuthentication]
        O2C[OAuth2Client]
        IO2C[IOAuth2Client]
        AB[AuthenticationBase]
    end
    
    subgraph "System Dependencies"
        CC[CommandContext]
        SM[SessionManager]
        T[Terminal]
        S[Settings]
        HF[HttpClientFactory]
    end
    
    GLA -->|implements| IGLA
    GLA -->|inherits| AB
    GLA -->|uses| GLC
    GLA -->|coordinates| GLV
    GLV -->|renders| GLCV
    
    GLC -->|inherits| O2C
    O2C -->|implements| IO2C
    
    GLA -->|depends on| CC
    GLA -->|checks| SM
    GLA -->|interacts| T
    GLA -->|reads| S
    GLA -->|creates| HF
```

## Core Components

### GitLabAuthentication Class

The `GitLabAuthentication` class is the primary entry point for GitLab authentication operations. It inherits from `AuthenticationBase` and implements the `IGitLabAuthentication` interface, providing a unified API for all GitLab authentication methods.

**Key Responsibilities:**
- Authentication method selection and orchestration
- User interface coordination (GUI, TTY, helper applications)
- OAuth 2.0 browser flow implementation
- Token refresh operations
- Credential validation and packaging

**Authentication Modes Supported:**
- **Basic Authentication**: Username/password credentials
- **Browser Authentication**: OAuth 2.0 authorization code flow
- **Personal Access Token (PAT)**: Token-based authentication

### IGitLabAuthentication Interface

Defines the contract for GitLab authentication operations:

```csharp
public interface IGitLabAuthentication : IDisposable
{
    Task<AuthenticationPromptResult> GetAuthenticationAsync(Uri targetUri, string userName, AuthenticationModes modes);
    Task<OAuth2TokenResult> GetOAuthTokenViaBrowserAsync(Uri targetUri, IEnumerable<string> scopes);
    Task<OAuth2TokenResult> GetOAuthTokenViaRefresh(Uri targetUri, string refreshToken);
}
```

### GitLabOAuth2Client

Extends the base `OAuth2Client` class with GitLab-specific OAuth 2.0 implementation. Handles GitLab's OAuth endpoints, client configuration, and token acquisition processes.

## Authentication Flow Architecture

### Multi-Modal Authentication Flow

```mermaid
sequenceDiagram
    participant User
    participant GitLabAuth as GitLabAuthentication
    participant SessionManager
    participant UI as UI System
    participant OAuth as OAuth2Client
    participant GitLab as GitLab Server
    
    User->>GitLabAuth: Request Authentication
    GitLabAuth->>SessionManager: Check Desktop Session
    alt Desktop Session Available
        GitLabAuth->>UI: Show GUI Prompt
        UI->>User: Display Options (Basic/Browser/PAT)
        User->>UI: Select Authentication Method
        alt Browser Selected
            UI->>GitLabAuth: Return Browser Mode
            GitLabAuth->>OAuth: Initiate Browser Flow
            OAuth->>GitLab: Request Authorization
            GitLab->>User: Browser Authentication
            User->>GitLab: Authorize Application
            GitLab->>OAuth: Return Authorization Code
            OAuth->>GitLab: Exchange Code for Token
            GitLab->>OAuth: Return Access Token
        else Basic/PAT Selected
            UI->>User: Request Credentials
            User->>UI: Enter Credentials
            UI->>GitLabAuth: Return Credentials
        end
    else Terminal Only
        GitLabAuth->>User: Show TTY Menu
        User->>GitLabAuth: Select Option
        GitLabAuth->>User: Prompt for Credentials
        User->>GitLabAuth: Enter Credentials
    end
    GitLabAuth->>User: Return Authentication Result
```

### OAuth 2.0 Browser Flow Implementation

```mermaid
flowchart LR
    A[Start Browser Flow] --> B[Create OAuth2Client]
    B --> C[Configure Endpoints]
    C --> D[Generate PKCE Parameters]
    D --> E[Build Authorization URL]
    E --> F[Launch System Browser]
    F --> G[User Authenticates]
    G --> H[Receive Authorization Code]
    H --> I[Exchange Code for Token]
    I --> J[Return Token Result]
    
    subgraph "PKCE Security"
        D1[Generate Code Verifier]
        D2[Create Code Challenge]
        D3[Include in Request]
    end
    
    D -.-> D1
    D -.-> D2
    D -.-> D3
```

## User Interface Integration

### GUI Authentication Interface

The module integrates with the Avalonia UI framework to provide rich graphical authentication experiences:

```mermaid
graph TB
    subgraph "GitLab UI Components"
        VM[CredentialsViewModel]
        CV[CredentialsView]
        GLV[GitLab-specific Views]
    end
    
    subgraph "Core UI Framework"
        AUI[AvaloniaUI]
        WM[Window Management]
        DIS[Dispatcher]
    end
    
    subgraph "Authentication Logic"
        GA[GitLabAuthentication]
        APR[AuthenticationPromptResult]
    end
    
    GA -->|creates| VM
    VM -->|binds to| CV
    CV -->|renders via| AUI
    AUI -->|manages| WM
    GA -->|returns| APR
    
    VM -.->|validates| GLV
```

### Terminal-Based Authentication

For headless environments, the module provides terminal-based authentication with interactive menus and secure password prompting.

## Integration with Core Systems

### Dependency Relationships

```mermaid
graph LR
    subgraph "GitLab Authentication"
        GLA[GitLabAuthentication]
    end
    
    subgraph "Core Framework Dependencies"
        CC[CommandContext]
        ICS[ICommandContext]
        SM[SessionManager]
        T[ITerminal]
        S[ISettings]
        HCF[HttpClientFactory]
        TS[ITrace2]
    end
    
    subgraph "Authentication Dependencies"
        AB[AuthenticationBase]
        O2C[OAuth2Client]
        SWB[OAuth2SystemWebBrowser]
    end
    
    GLA -->|inherits| AB
    GLA -->|uses| O2C
    GLA -->|depends on| CC
    GLA -->|checks| SM
    GLA -->|reads| S
    GLA -->|creates| HCF
    GLA -->|launches| SWB
    AB -->|requires| ICS
    AB -->|uses| T
    AB -->|writes to| TS
```

### Settings and Configuration Integration

The module integrates with the settings system to support configuration-based behavior:

- **GUI Prompts**: Controlled via `ISettings.IsGuiPromptsEnabled`
- **Authentication Helpers**: Configurable via Git configuration and environment variables
- **OAuth Settings**: Client ID, redirect URI, and other OAuth parameters
- **Developer Overrides**: Support for development environment customization

## Security Implementation

### PKCE (Proof Key for Code Exchange)

The OAuth 2.0 implementation uses PKCE to enhance security:

```mermaid
sequenceDiagram
    participant Client as GitLabAuthentication
    participant Generator as CodeGenerator
    participant Browser as Web Browser
    participant Server as GitLab OAuth
    
    Client->>Generator: Create Code Verifier
    Generator-->>Client: Random String
    Client->>Generator: Create Code Challenge (SHA256)
    Generator-->>Client: Challenge String
    
    Client->>Browser: Authorization Request + Challenge
    Browser->>Server: Forward Request
    Server-->>Browser: Authorization Code
    Browser-->>Client: Return Code
    
    Client->>Server: Token Request + Verifier
    Server->>Server: Verify Challenge
    Server-->>Client: Access Token
```

### Credential Handling

- **Secure Storage**: Integration with platform-specific credential stores
- **Memory Management**: Proper cleanup of sensitive data
- **Transport Security**: HTTPS enforcement for all OAuth communications
- **Token Refresh**: Automatic token refresh using secure refresh tokens

## Error Handling and Diagnostics

### Exception Management

The module implements comprehensive error handling with trace2 integration:

- **User Cancellation**: Graceful handling of authentication cancellation
- **Network Errors**: Retry logic and timeout management
- **OAuth Errors**: Detailed error parsing and reporting
- **Validation Errors**: Input validation and sanitization

### Diagnostic Integration

```mermaid
graph TB
    subgraph "Error Flow"
        OP[Operation]
        VAL[Validation]
        TRY[Try Block]
        CATCH[Catch Block]
        TRACE[Trace2 Logging]
        EX[Exception]
    end
    
    OP --> VAL
    VAL --> TRY
    TRY -->|success| OP
    TRY -->|failure| CATCH
    CATCH --> EX
    CATCH --> TRACE
    
    subgraph "Trace Categories"
        AUTH[Authentication]
        OAUTH[OAuth Flow]
        UI[User Interface]
        NET[Network]
    end
    
    TRACE --> AUTH
    TRACE --> OAUTH
    TRACE --> UI
    TRACE --> NET
```

## Platform Compatibility

### Cross-Platform Support

The module supports multiple authentication methods across different platforms:

| Platform | GUI Support | Browser Support | TTY Support |
|----------|-------------|-----------------|-------------|
| Windows | ✓ (WPF/Avalonia) | ✓ | ✓ |
| macOS | ✓ (Avalonia) | ✓ | ✓ |
| Linux | ✓ (Avalonia) | ✓ | ✓ |

### Session Detection

Automatic detection of desktop sessions to determine available authentication methods:

```csharp
if (!Context.SessionManager.IsDesktopSession)
{
    modes = modes & ~AuthenticationModes.Browser;
}
```

## Usage Patterns

### Basic Authentication Flow

```csharp
var gitLabAuth = new GitLabAuthentication(commandContext);
var result = await gitLabAuth.GetAuthenticationAsync(
    targetUri: new Uri("https://gitlab.com"),
    userName: null,
    modes: AuthenticationModes.All
);
```

### OAuth Token Acquisition

```csharp
var tokenResult = await gitLabAuth.GetOAuthTokenViaBrowserAsync(
    targetUri: new Uri("https://gitlab.com"),
    scopes: new[] { "read_user", "read_repository", "write_repository" }
);
```

### Token Refresh

```csharp
var refreshedToken = await gitLabAuth.GetOAuthTokenViaRefresh(
    targetUri: new Uri("https://gitlab.com"),
    refreshToken: storedRefreshToken
);
```

## Related Documentation

- [Core Authentication Framework](Core%20Authentication%20Framework.md) - Base authentication classes and interfaces
- [OAuth Authentication](OAuth%20Authentication.md) - OAuth 2.0 implementation details
- [GitLab Provider](GitLab%20Provider.md) - GitLab host provider integration
- [UI Framework](UI%20Framework.md) - User interface components and patterns
- [Cross-Platform Support](Cross-Platform%20Support.md) - Platform-specific implementations

## Summary

The GitLab Authentication module provides a robust, secure, and user-friendly authentication system for GitLab repositories. Its multi-modal approach ensures compatibility across different environments while maintaining security best practices. The modular architecture allows for easy extension and maintenance while providing consistent user experiences across GUI, browser, and terminal interfaces.