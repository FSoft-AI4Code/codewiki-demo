# Git provider integrations

The `git_provider_integrations` module is the provider-neutral integration boundary for OpenHands' code-host automation. It lets the rest of the system authenticate against GitHub, GitLab, or Bitbucket, discover repositories and branches, retrieve microagents, generate authenticated Git URLs, and inspect pull/merge request state without embedding provider-specific API logic in callers.

## Position in the system

```mermaid
flowchart LR
    UI[Web/CLI clients] --> S[Server sessions and API routes]
    S --> H[ProviderHandler]
    H --> C[GitService protocol]
    C --> P[GitHub / GitLab / Bitbucket services]
    P --> G[External Git provider APIs]
    H --> R[IssueResolver and PR handlers]
    H --> RT[Runtime env + EventStream secret masking]
    C --> MA[Microagent infrastructure]
```

The module belongs to the broader [code_host_automation.md](code_host_automation.md) area. Its primary downstream consumer is the resolver layer, documented in [issue_resolver.md](issue_resolver.md). It uses shared event, server, logging, and microagent types rather than owning those subsystems.

## Architecture

```mermaid
graph TD
    T[ProviderToken / CustomSecret] --> H[ProviderHandler]
    E[ProviderType and domain models] --> H
    E --> G[GitService protocol]
    G --> B[BaseGitService]
    B --> GH[GitHub implementation]
    B --> GL[GitLab implementation]
    B --> BB[Bitbucket implementation]
    H --> O[Repository, branch, user, task operations]
    H --> M[Microagent operations]
    H --> U[Authenticated URL + token export]
```

The design separates orchestration from contracts. The generated documentation index is:

- [git_provider_integrations_provider_handler.md](git_provider_integrations_provider_handler.md) documents `ProviderHandler`, credential flow, provider selection, aggregation, and runtime integration.
- [git_provider_integrations_service_contracts.md](git_provider_integrations_service_contracts.md) documents `GitService`, `BaseGitService`, shared models/enums, exceptions, and microagent normalization.

## Core flows

### Repository and branch access

```mermaid
sequenceDiagram
    participant Caller
    participant H as ProviderHandler
    participant Service as Provider GitService
    participant API as Git provider API

    Caller->>H: search/list/verify repository
    alt provider selected
        H->>Service: instantiate selected service
        Service->>API: provider-specific request
        API-->>Service: normalized response
        Service-->>H: Repository/Branch data
    else provider omitted
        loop configured providers
            H->>Service: probe or aggregate request
            Service->>API: request
            API-->>Service: result or error
        end
        H-->>Caller: first match or combined results
    end
```

### Microagent discovery

Microagent listing checks `.cursorrules` and provider-specific repository directories. Content retrieval parses the file through the shared microagent loader and returns content plus trigger metadata. Missing files are treated as a cross-provider lookup opportunity; parsing and provider errors are retained for final diagnostics.

## Operational characteristics

- All provider calls are asynchronous.
- Provider failures are logged and commonly isolated so another configured provider can succeed.
- Explicit provider requests require pagination parameters where the underlying API requires them.
- Secret values are represented with `SecretStr` until deliberately exported, then masked in the event stream.
- Custom enterprise hosts are supported through the token's `host` field and are used in repository URL detection and Git remote construction.
- PR status lookup fails safe by treating an unknown status as open.

## Change checklist

When modifying this module, keep the provider-neutral protocol, facade mapping, shared response models, token-export behavior, and resolver expectations aligned. A new provider should be added consistently to `ProviderType`, service construction, domains, environment-key mapping, URL construction, and tests for aggregation/fallback behavior.
