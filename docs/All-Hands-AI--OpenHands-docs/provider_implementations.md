# Provider Implementations Module

## Overview

The `provider_implementations` module provides concrete implementations of Git service providers within the OpenHands system. This module serves as the foundation for integrating with major Git hosting platforms including GitHub, GitLab, and Bitbucket. Each provider implementation extends the base Git service architecture with platform-specific functionality while maintaining a consistent interface for the broader system.

The module implements the adapter pattern to provide unified access to different Git platforms, handling authentication, API communication, and data transformation specific to each provider's requirements.

## Architecture

```mermaid
graph TB
    subgraph "Provider Implementations Layer"
        GHB[GitHubMixinBase]
        GLB[GitLabMixinBase]
        BBB[BitBucketMixinBase]
    end
    
    subgraph "Service Foundation Layer"
        BGS[BaseGitService]
        GS[GitService]
    end
    
    subgraph "Protocol Layer"
        HC[HTTPClient]
        RM[RequestMethod]
    end
    
    subgraph "External APIs"
        GHAPI[GitHub API]
        GLAPI[GitLab API]
        BBAPI[Bitbucket API]
    end
    
    GHB --> BGS
    GLB --> BGS
    BBB --> BGS
    
    GHB --> HC
    GLB --> HC
    BBB --> HC
    
    BGS --> GS
    
    GHB --> GHAPI
    GLB --> GLAPI
    BBB --> BBAPI
    
    classDef provider fill:#e1f5fe
    classDef foundation fill:#f3e5f5
    classDef protocol fill:#e8f5e8
    classDef external fill:#fff3e0
    
    class GHB,GLB,BBB provider
    class BGS,GS foundation
    class HC,RM protocol
    class GHAPI,GLAPI,BBAPI external
```

## Core Components

### GitHubMixinBase

The GitHub provider implementation that handles GitHub-specific API interactions and authentication patterns.

**Key Features:**
- OAuth Bearer token authentication
- GitHub REST API v3 integration
- GraphQL API support for complex queries
- Automatic token refresh handling
- GitHub-specific error handling and response parsing

**Authentication Flow:**
```mermaid
sequenceDiagram
    participant Client
    participant GHB as GitHubMixinBase
    participant GH as GitHub API
    participant Store as Settings Store
    
    Client->>GHB: Request operation
    GHB->>Store: Get latest token
    Store-->>GHB: Return token
    GHB->>GH: API request with Bearer token
    alt Token expired
        GH-->>GHB: 401 Unauthorized
        GHB->>Store: Refresh token
        Store-->>GHB: New token
        GHB->>GH: Retry with new token
    end
    GH-->>GHB: API response
    GHB-->>Client: Processed response
```

### GitLabMixinBase

The GitLab provider implementation supporting both GitLab.com and self-hosted GitLab instances.

**Key Features:**
- Bearer token authentication
- Support for self-hosted GitLab instances
- GraphQL API integration
- Project ID extraction and URL encoding
- Content-type aware response handling

**Project ID Handling:**
```mermaid
flowchart TD
    A[Repository String] --> B{Contains domain?}
    B -->|Yes| C[Extract domain/owner/repo]
    B -->|No| D[Use owner/repo format]
    C --> E[URL encode as owner%2Frepo]
    D --> E
    E --> F[Use as GitLab Project ID]
```

### BitBucketMixinBase

The Bitbucket provider implementation with support for both OAuth and Basic authentication.

**Key Features:**
- Dual authentication support (OAuth Bearer and Basic Auth)
- Pagination handling for large datasets
- Workspace/repository slug parsing
- Repository metadata extraction
- Microagent file discovery

**Authentication Strategy:**
```mermaid
flowchart TD
    A[Token Input] --> B{Contains colon?}
    B -->|Yes| C[Base64 encode as Basic Auth]
    B -->|No| D[Use as Bearer token]
    C --> E[Authorization: Basic <encoded>]
    D --> F[Authorization: Bearer <token>]
    E --> G[API Request]
    F --> G
```

## Data Flow

### Request Processing Flow

```mermaid
flowchart TD
    A[Client Request] --> B[Provider Mixin]
    B --> C[Get Headers]
    C --> D[Token Available?]
    D -->|No| E[Get Latest Token]
    D -->|Yes| F[Make HTTP Request]
    E --> F
    F --> G[Response Status]
    G -->|401| H[Token Expired?]
    G -->|Success| I[Parse Response]
    G -->|Error| J[Handle Error]
    H -->|Yes| K[Refresh Token]
    H -->|No| J
    K --> F
    I --> L[Return Data]
    J --> M[Throw Exception]
```

### User Information Retrieval

```mermaid
sequenceDiagram
    participant C as Client
    participant P as Provider
    participant API as Git Provider API
    
    C->>P: get_user()
    P->>P: _get_headers()
    P->>API: GET /user
    API-->>P: User data response
    P->>P: Parse to User object
    P-->>C: Standardized User
    
    Note over P: Each provider maps<br/>platform-specific fields<br/>to common User structure
```

## Component Interactions

### Provider Integration Pattern

```mermaid
classDiagram
    class BaseGitService {
        +token: SecretStr
        +refresh: bool
        +get_latest_token()
        +verify_access()
        +get_user()
    }
    
    class HTTPClient {
        +execute_request()
        +handle_http_status_error()
        +handle_http_error()
    }
    
    class GitHubMixinBase {
        +BASE_URL: str
        +GRAPHQL_URL: str
        +_get_headers()
        +_make_request()
        +execute_graphql_query()
    }
    
    class GitLabMixinBase {
        +BASE_URL: str
        +GRAPHQL_URL: str
        +_extract_project_id()
        +execute_graphql_query()
    }
    
    class BitBucketMixinBase {
        +BASE_URL: str
        +_extract_owner_and_repo()
        +_fetch_paginated_data()
        +_parse_repository()
    }
    
    BaseGitService <|-- GitHubMixinBase
    BaseGitService <|-- GitLabMixinBase
    BaseGitService <|-- BitBucketMixinBase
    
    HTTPClient <|-- GitHubMixinBase
    HTTPClient <|-- GitLabMixinBase
    HTTPClient <|-- BitBucketMixinBase
```

## Error Handling Strategy

### HTTP Error Processing

```mermaid
flowchart TD
    A[HTTP Request] --> B[Response Received]
    B --> C{Status Code}
    C -->|2xx| D[Success Path]
    C -->|401| E[Token Expired]
    C -->|4xx| F[Client Error]
    C -->|5xx| G[Server Error]
    
    E --> H[Refresh Token]
    H --> I[Retry Request]
    I --> C
    
    F --> J[handle_http_status_error]
    G --> J
    J --> K[Throw Specific Exception]
    
    D --> L[Parse Response]
    L --> M[Return Data]
```

## Integration Points

### Service Foundation Integration

The provider implementations integrate with the [service_foundation](service_foundation.md) module through:

- **BaseGitService**: Provides the common interface and base functionality
- **GitService**: Defines the service contract for Git operations
- **User Model**: Standardized user representation across providers
- **Repository Model**: Common repository metadata structure

### Authentication Flow

```mermaid
sequenceDiagram
    participant App as Application
    participant Provider as Provider Mixin
    participant Store as Settings Store
    participant API as Git Provider API
    
    App->>Provider: Initialize with token
    Provider->>Store: Store token securely
    
    loop For each API call
        Provider->>Store: Get current token
        Store-->>Provider: Return token
        Provider->>API: Request with token
        alt Token valid
            API-->>Provider: Success response
        else Token expired
            API-->>Provider: 401 Unauthorized
            Provider->>Store: Request token refresh
            Store-->>Provider: New token
            Provider->>API: Retry with new token
            API-->>Provider: Success response
        end
    end
```

## Configuration and Setup

### Provider-Specific Configuration

Each provider requires specific configuration parameters:

**GitHub:**
- Base URL: `https://api.github.com`
- GraphQL URL: `https://api.github.com/graphql`
- Authentication: OAuth Bearer token
- Headers: GitHub API v3 Accept header

**GitLab:**
- Base URL: Configurable (GitLab.com or self-hosted)
- GraphQL URL: `{base_url}/api/graphql`
- Authentication: OAuth Bearer token
- Project ID: URL-encoded namespace/project format

**Bitbucket:**
- Base URL: `https://api.bitbucket.org/2.0`
- Authentication: OAuth Bearer or Basic Auth
- Pagination: Cursor-based pagination support
- Repository format: workspace/repo_slug

## Performance Considerations

### Request Optimization

```mermaid
flowchart LR
    A[Request] --> B[Token Cache]
    B --> C[HTTP Connection Pool]
    C --> D[Response Cache]
    D --> E[Parsed Data]
    
    subgraph "Optimization Strategies"
        F[Token Reuse]
        G[Connection Pooling]
        H[Response Caching]
        I[Pagination Handling]
    end
```

### Pagination Strategies

- **GitHub**: Link header-based pagination
- **GitLab**: Link header with total count
- **Bitbucket**: Cursor-based pagination with next URL

## Security Features

### Token Management

```mermaid
flowchart TD
    A[Token Input] --> B[SecretStr Wrapper]
    B --> C[Secure Storage]
    C --> D[Runtime Access]
    D --> E[Automatic Refresh]
    E --> F[Secure Disposal]
    
    subgraph "Security Measures"
        G[No Plain Text Logging]
        H[Memory Protection]
        I[Automatic Expiry]
        J[Refresh Mechanism]
    end
```

## Extension Points

### Adding New Providers

To add a new Git provider:

1. **Create Provider Mixin**: Extend `BaseGitService` and `HTTPClient`
2. **Implement Required Methods**: `_get_headers()`, `_make_request()`, `get_user()`
3. **Handle Authentication**: Provider-specific token handling
4. **Error Mapping**: Map provider errors to standard exceptions
5. **Data Transformation**: Convert provider responses to standard models

### Custom Authentication

```mermaid
flowchart TD
    A[Custom Provider] --> B[Implement _get_headers]
    B --> C[Handle Token Format]
    C --> D[Implement Refresh Logic]
    D --> E[Error Handling]
    E --> F[Integration Testing]
```

## Dependencies

### Internal Dependencies
- [service_foundation](service_foundation.md): Base service interfaces and models
- [events_and_actions](events_and_actions.md): Event handling for Git operations
- [storage_system](storage_system.md): Token and settings storage

### External Dependencies
- `httpx`: Async HTTP client for API communication
- `pydantic`: Data validation and SecretStr handling
- Provider-specific API libraries and authentication flows

## Testing Strategy

### Provider Testing Pattern

```mermaid
flowchart TD
    A[Unit Tests] --> B[Mock API Responses]
    B --> C[Authentication Tests]
    C --> D[Error Handling Tests]
    D --> E[Integration Tests]
    E --> F[Live API Tests]
    
    subgraph "Test Categories"
        G[Token Management]
        H[Request/Response]
        I[Error Scenarios]
        J[Pagination]
    end
```

## Future Enhancements

### Planned Improvements

1. **Rate Limiting**: Implement provider-specific rate limiting
2. **Caching Layer**: Add response caching for frequently accessed data
3. **Webhook Support**: Integrate with provider webhook systems
4. **Advanced Authentication**: Support for App installations and JWT tokens
5. **Metrics Collection**: Add performance and usage metrics

### Extensibility Roadmap

```mermaid
timeline
    title Provider Implementation Roadmap
    
    section Current
        GitHub Support    : GitHub REST API
                          : GitHub GraphQL
                          : OAuth Bearer Auth
        
        GitLab Support    : GitLab REST API
                          : Self-hosted Support
                          : Project ID Handling
        
        Bitbucket Support : Bitbucket REST API
                          : Dual Auth Methods
                          : Pagination Support
    
    section Near Term
        Enhanced Features : Rate Limiting
                          : Response Caching
                          : Webhook Integration
    
    section Future
        New Providers     : Azure DevOps
                          : Gitea Support
                          : Custom Git Servers
```

This module serves as the critical bridge between the OpenHands system and external Git hosting platforms, providing a unified interface while handling the complexities of each provider's unique API characteristics and authentication requirements.