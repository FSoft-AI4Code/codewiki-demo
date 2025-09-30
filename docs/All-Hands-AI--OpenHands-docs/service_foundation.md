# Service Foundation Module

## Overview

The Service Foundation module (`openhands.integrations.service_types`) provides the foundational abstractions and protocols for Git service integrations within the OpenHands system. This module defines the core interfaces, data models, and base implementations that enable seamless integration with various Git providers (GitHub, GitLab, Bitbucket) while maintaining a consistent API across different provider implementations.

## Core Purpose

- **Unified Git Provider Interface**: Establishes a common protocol for interacting with different Git service providers
- **Microagent Integration**: Provides standardized mechanisms for discovering and managing microagents across repositories
- **Task Management**: Defines structures for automated task suggestions and repository operations
- **Authentication Abstraction**: Standardizes authentication patterns across different Git providers

## Architecture Overview

```mermaid
graph TB
    subgraph "Service Foundation Layer"
        GitService[GitService Protocol]
        BaseGitService[BaseGitService ABC]
        InstallationsService[InstallationsService Protocol]
    end
    
    subgraph "Data Models"
        User[User Model]
        Repository[Repository Model]
        Branch[Branch Model]
        Comment[Comment Model]
        SuggestedTask[SuggestedTask Model]
        CreateMicroagent[CreateMicroagent Model]
    end
    
    subgraph "Provider Implementations"
        GitHub[GitHub Service]
        GitLab[GitLab Service]
        Bitbucket[Bitbucket Service]
    end
    
    subgraph "Integration Points"
        MicroagentSystem[Microagent System]
        ServerAPI[Server & API]
        EnterpriseIntegrations[Enterprise Integrations]
    end
    
    GitService --> BaseGitService
    BaseGitService --> GitHub
    BaseGitService --> GitLab
    BaseGitService --> Bitbucket
    
    GitService --> User
    GitService --> Repository
    GitService --> Branch
    GitService --> Comment
    GitService --> SuggestedTask
    
    GitHub --> MicroagentSystem
    GitLab --> MicroagentSystem
    Bitbucket --> MicroagentSystem
    
    GitService --> ServerAPI
    GitService --> EnterpriseIntegrations
    
    InstallationsService --> GitHub
    InstallationsService --> GitLab
    InstallationsService --> Bitbucket
```

## Core Components

### GitService Protocol

The primary interface defining the contract for all Git service implementations:

```mermaid
classDiagram
    class GitService {
        <<protocol>>
        +__init__(user_id, token, external_auth_id, ...)
        +get_latest_token() SecretStr
        +get_user() User
        +search_repositories(...) List[Repository]
        +get_all_repositories(...) List[Repository]
        +get_paginated_repos(...) List[Repository]
        +get_suggested_tasks() List[SuggestedTask]
        +get_repository_details_from_repo_name(...) Repository
        +get_branches(...) List[Branch]
        +get_paginated_branches(...) PaginatedBranchesResponse
        +search_branches(...) List[Branch]
        +get_microagents(...) List[MicroagentResponse]
        +get_microagent_content(...) MicroagentContentResponse
        +get_pr_details(...) dict
        +is_pr_open(...) bool
    }
```

### BaseGitService Abstract Base Class

Provides common functionality and abstract methods for concrete implementations:

```mermaid
classDiagram
    class BaseGitService {
        <<abstract>>
        +provider: str
        +_make_request(url, params, method)* tuple
        +_get_cursorrules_url(repository)* str
        +_get_microagents_directory_url(...)* str
        +_get_microagents_directory_params(...)* dict
        +_is_valid_microagent_file(item)* bool
        +_get_file_name_from_item(item)* str
        +_get_file_path_from_item(...)* str
        +_determine_microagents_path(repository) str
        +_create_microagent_response(...) MicroagentResponse
        +_parse_microagent_content(...) MicroagentContentResponse
        +_fetch_cursorrules_content(...) Any
        +_check_cursorrules_file(...) MicroagentResponse
        +_process_microagents_directory(...) List[MicroagentResponse]
        +get_microagents(repository) List[MicroagentResponse]
        +_truncate_comment(...) str
    }
```

## Data Models

### Core Entity Models

```mermaid
erDiagram
    User {
        string id
        string login
        string avatar_url
        string company
        string name
        string email
    }
    
    Repository {
        string id
        string full_name
        ProviderType git_provider
        bool is_public
        int stargazers_count
        string link_header
        string pushed_at
        OwnerType owner_type
        string main_branch
    }
    
    Branch {
        string name
        string commit_sha
        bool protected
        string last_push_date
    }
    
    Comment {
        string id
        string body
        string author
        datetime created_at
        datetime updated_at
        bool system
    }
    
    SuggestedTask {
        ProviderType git_provider
        TaskType task_type
        string repo
        int issue_number
        string title
    }
    
    Repository ||--o{ Branch : contains
    Repository ||--o{ Comment : has
    User ||--o{ Repository : owns
```

### Enumeration Types

```mermaid
classDiagram
    class ProviderType {
        <<enumeration>>
        GITHUB
        GITLAB
        BITBUCKET
        ENTERPRISE_SSO
    }
    
    class TaskType {
        <<enumeration>>
        MERGE_CONFLICTS
        FAILING_CHECKS
        UNRESOLVED_COMMENTS
        OPEN_ISSUE
        OPEN_PR
        CREATE_MICROAGENT
    }
    
    class OwnerType {
        <<enumeration>>
        USER
        ORGANIZATION
    }
    
    class RequestMethod {
        <<enumeration>>
        POST
        GET
    }
```

## Microagent Integration

The service foundation provides comprehensive microagent discovery and management capabilities:

```mermaid
sequenceDiagram
    participant Client
    participant GitService
    participant BaseGitService
    participant MicroagentSystem
    participant GitProvider
    
    Client->>GitService: get_microagents(repository)
    GitService->>BaseGitService: get_microagents(repository)
    
    BaseGitService->>BaseGitService: _determine_microagents_path()
    BaseGitService->>BaseGitService: _check_cursorrules_file()
    BaseGitService->>GitProvider: fetch .cursorrules
    GitProvider-->>BaseGitService: cursorrules content
    
    BaseGitService->>BaseGitService: _process_microagents_directory()
    BaseGitService->>GitProvider: fetch microagents directory
    GitProvider-->>BaseGitService: directory contents
    
    BaseGitService->>BaseGitService: _create_microagent_response()
    BaseGitService-->>GitService: List[MicroagentResponse]
    GitService-->>Client: microagents list
    
    Client->>GitService: get_microagent_content(repo, path)
    GitService->>GitProvider: fetch file content
    GitProvider-->>GitService: raw content
    GitService->>MicroagentSystem: parse content
    MicroagentSystem-->>GitService: parsed microagent
    GitService-->>Client: MicroagentContentResponse
```

## Task Suggestion System

The module includes a sophisticated task suggestion system that analyzes repositories and suggests actionable tasks:

```mermaid
flowchart TD
    A[Repository Analysis] --> B{Task Type Detection}
    
    B --> C[Merge Conflicts]
    B --> D[Failing Checks]
    B --> E[Unresolved Comments]
    B --> F[Open Issues]
    B --> G[Open PRs]
    B --> H[Create Microagent]
    
    C --> I[Generate Prompt]
    D --> I
    E --> I
    F --> I
    G --> I
    H --> I
    
    I --> J[Provider-Specific Terms]
    J --> K[Template Rendering]
    K --> L[Task Suggestion]
```

## Error Handling

The module defines a comprehensive error hierarchy for robust error handling:

```mermaid
classDiagram
    class ValueError {
        <<built-in>>
    }
    
    class AuthenticationError {
        +message: str
    }
    
    class UnknownException {
        +message: str
    }
    
    class RateLimitError {
        +message: str
    }
    
    class ResourceNotFoundError {
        +message: str
    }
    
    class MicroagentParseError {
        +message: str
    }
    
    ValueError <|-- AuthenticationError
    ValueError <|-- UnknownException
    ValueError <|-- RateLimitError
    ValueError <|-- ResourceNotFoundError
    ValueError <|-- MicroagentParseError
```

## Integration Dependencies

The service foundation module integrates with several other system components:

```mermaid
graph LR
    ServiceFoundation[Service Foundation] --> MicroagentSystem[microagent_system.md]
    ServiceFoundation --> ServerAPI[server_and_api.md]
    ServiceFoundation --> EnterpriseIntegrations[enterprise_integrations.md]
    ServiceFoundation --> CoreConfig[core_configuration.md]
    
    ProviderImplementations[provider_implementations.md] --> ServiceFoundation
    
    subgraph "External Dependencies"
        Jinja2[Jinja2 Templates]
        Pydantic[Pydantic Models]
        AsyncHTTP[Async HTTP Clients]
    end
    
    ServiceFoundation --> Jinja2
    ServiceFoundation --> Pydantic
    ServiceFoundation --> AsyncHTTP
```

## Provider Implementation Pattern

The module establishes a clear pattern for implementing provider-specific services:

```mermaid
sequenceDiagram
    participant ConcreteService
    participant BaseGitService
    participant GitProvider
    
    Note over ConcreteService: Implements GitService Protocol
    ConcreteService->>BaseGitService: Inherits common functionality
    
    ConcreteService->>ConcreteService: Implement abstract methods
    Note over ConcreteService: _make_request()<br/>_get_cursorrules_url()<br/>_get_microagents_directory_url()<br/>etc.
    
    ConcreteService->>GitProvider: Provider-specific API calls
    GitProvider-->>ConcreteService: Provider response
    
    ConcreteService->>BaseGitService: Use common processing
    BaseGitService-->>ConcreteService: Standardized response
```

## Configuration and Authentication

The service foundation supports multiple authentication patterns:

- **Direct Token Authentication**: Using provider-specific tokens
- **External Authentication**: Integration with external auth systems
- **Enterprise SSO**: Support for enterprise single sign-on
- **Token Management**: Automatic token refresh and validation

## Key Features

### Repository Management
- Repository discovery and search
- Branch management and pagination
- Repository metadata extraction
- Access control validation

### Microagent Discovery
- Automatic microagent detection in repositories
- Support for `.cursorrules` files
- Microagent content parsing and validation
- Template-based microagent creation

### Task Automation
- Intelligent task suggestion based on repository state
- Provider-specific prompt generation
- Template-driven task descriptions
- Multi-provider task normalization

### Performance Optimization
- Paginated API responses
- Efficient directory scanning
- Content truncation for large responses
- Caching-friendly data structures

## Usage Patterns

The service foundation enables consistent usage patterns across all Git providers:

```python
# Initialize service (provider-specific implementation)
service = GitHubService(user_id="user123", token=SecretStr("token"))

# Common operations work across all providers
user = await service.get_user()
repositories = await service.get_all_repositories(sort="updated", app_mode=AppMode.OSS)
microagents = await service.get_microagents("owner/repo")
tasks = await service.get_suggested_tasks()
```

## Related Documentation

- [Provider Implementations](provider_implementations.md) - Concrete implementations for GitHub, GitLab, and Bitbucket
- [Microagent System](microagent_system.md) - Microagent parsing and execution system
- [Server and API](server_and_api.md) - Web API integration points
- [Enterprise Integrations](enterprise_integrations.md) - Enterprise-specific Git service features
- [Core Configuration](core_configuration.md) - Configuration management for Git services

The Service Foundation module serves as the cornerstone for Git provider integrations, ensuring consistent behavior, robust error handling, and extensible architecture across the entire OpenHands ecosystem.