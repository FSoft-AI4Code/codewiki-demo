# Enterprise Authentication

## Purpose

The `enterprise_auth` module provides the hosted SaaS authentication boundary for OpenHands. It manages Keycloak sessions, OAuth credentials for connected identity providers, GitHub allowlisting, Google Sheets-backed user eligibility, secure authentication cookies, terms-of-service enforcement, and post-refresh integration work.

The module is used by the SaaS server and is consumed indirectly by API routes, session authentication, provider integrations, and middleware. It is not a standalone identity provider; Keycloak, external OAuth providers, persistent token stores, and the GitHub integration remain the systems of record.

## Architecture overview

```mermaid
flowchart LR
    Client[Browser or API client] --> MW[SetAuthCookieMiddleware]
    MW --> UA[SaasUserAuth]
    UA --> TM[TokenManager]
    TM --> KC[Keycloak]
    TM --> TS[(AuthTokenStore / OfflineTokenStore)]
    TM --> IDP[GitHub / GitLab / Bitbucket OAuth]
    MW --> Cookie[Signed keycloak_auth cookie]
    MW --> Sync[Background GitLab repo sync]

    GH[GitHub authentication helpers] --> GHS[SaaSGitHubService]
    GH --> Allow[File allowlist or Google Sheets]
    Allow --> Sheets[GoogleSheetsClient]
    Sheets --> GAPI[Google Sheets API]
```

### Component relationships

```mermaid
graph TD
    subgraph Request boundary
        M[SetAuthCookieMiddleware]
        C[Cookie signing and deletion helpers]
        E[AuthError hierarchy]
    end

    subgraph Session and token services
        S[SaasUserAuth]
        T[TokenManager]
        K[Keycloak manager]
        A[(Encrypted token stores)]
    end

    subgraph Eligibility
        G[GitHub UserVerifier]
        U[Generic UserVerifier]
        H[SaaSGitHubService]
        W[GoogleSheetsClient]
    end

    M --> S
    M --> C
    M --> E
    S --> T
    T --> K
    T --> A
    T --> H
    G --> W
    U --> W
    G --> H
```

## Sub-modules

- [Token lifecycle](enterprise_auth_token_lifecycle.md) — `TokenManager`, encryption, Keycloak exchange/refresh, provider-token retrieval, offline tokens, and GitHub App installation tokens.
- [Allowlist verification](enterprise_auth_allowlist_verification.md) — file- and Google Sheets-backed eligibility checks, GitHub user authentication, and the 15-second Sheets cache.
- [Request authentication enforcement](enterprise_auth_request_enforcement.md) — request-path selection, credentials/TOS checks, cookie refresh, error responses, and GitLab synchronization.

## End-to-end flows

### Login/session refresh

```mermaid
sequenceDiagram
    participant B as Client
    participant M as Middleware
    participant U as SaasUserAuth
    participant T as TokenManager
    participant K as Keycloak
    participant C as Cookie helper

    B->>M: Request with keycloak_auth cookie
    M->>U: Resolve cookie or bearer credentials
    U->>T: Refresh when access/refresh state requires it
    T->>K: Refresh Keycloak token
    K-->>T: New access and refresh tokens
    T-->>U: Updated credentials, refreshed=true
    U-->>M: Authenticated user
    M->>C: Set signed refreshed cookie
    M-->>B: Response with updated cookie
```

### Provider-token lookup

```mermaid
flowchart TD
    Start[Need provider token] --> UserInfo[Read Keycloak user info]
    UserInfo --> Store[Open AuthTokenStore for user and provider]
    Store --> Expiry{Access token expires within 10 minutes?}
    Expiry -- No --> Decrypt[Decrypt stored access token]
    Expiry -- Yes --> RefreshExpiry{Refresh token expired?}
    RefreshExpiry -- Yes --> Fail[Raise authentication failure]
    RefreshExpiry -- No --> OAuth[Refresh at provider OAuth endpoint]
    OAuth --> Persist[Encrypt and persist new token pair]
    Persist --> Decrypt
    Decrypt --> Return[Return provider access token]
```

### Allowlist evaluation

```mermaid
flowchart TD
    GithubUser[Authenticated GitHub user] --> Active{Waitlist active?}
    Active -- No --> Allow[Allow]
    Active -- Yes --> File{Username in configured file?}
    File -- Yes --> Allow
    File -- No --> Sheet{Username in configured Google Sheet?}
    Sheet -- Yes --> Allow
    Sheet -- No --> Deny[Deny]
```

## Security and operational notes

- OAuth access and refresh tokens are encrypted with Fernet using a key derived from the configured JWT secret before persistence.
- The browser cookie is an HTTP-only, signed JWT containing Keycloak credentials and the TOS state. Production requests use the secure cookie flag; localhost is treated specially for development.
- Access-token refresh is intentionally proactive: a token is considered expired ten minutes before its provider-reported expiry.
- Keycloak connection failures are retried twice in the token manager; user-session refresh has its own retry policy in `SaasUserAuth`.
- The middleware excludes public/configuration and selected billing/auth callback paths from normal attachment checks, while MCP paths are protected.
- Invalid authentication errors remove the `keycloak_auth` cookie and attempt Keycloak logout.
- Waitlist configuration is read at verifier initialization. Changes to the file or environment generally require process reinitialization, whereas Google Sheets contents are re-read after the short cache expires.
- Provider refresh failures can invalidate stored provider credentials; callers may surface the failure as a general authentication error and require login again.

## Configuration inputs

| Input | Role |
|---|---|
| `GITHUB_USER_LIST_FILE` | Optional newline-delimited GitHub username allowlist |
| `GITHUB_USERS_SHEET_ID` | Optional Google Sheets allowlist source |
| `DISABLE_WAITLIST=true` | Disables the allowlist gate |
| JWT secret configuration | Derives token encryption and signs the auth cookie |
| Keycloak configuration | Selects internal/external Keycloak endpoints and realm |
| GitHub/GitLab/Bitbucket OAuth client credentials | Refreshes connected provider tokens |
| Google application default credentials | Authorizes read-only Sheets access |

## Related modules

- [Conversation service tier](conversation_service_tier.md) — owns server sessions and API request handling that consume authentication state.
- [Hosted SaaS overlay](hosted_saas_overlay.md) — contains the surrounding SaaS routes, configuration, integrations, and storage models.
- [Code host automation](code_host_automation.md) — consumes provider credentials and Git service abstractions.
- [User-facing clients](user_facing_clients.md) — sends browser/API credentials and receives authentication/error responses.

## Maintenance guidance

When changing authentication behavior, inspect the relevant sub-module first, then verify the contract with `SaasUserAuth`, cookie helpers, Keycloak manager functions, token-store implementations, and the affected provider service. In particular, preserve token encryption, refresh expiration semantics, cookie invalidation behavior, and the distinction between browser-cookie TOS enforcement and bearer/MCP requests.
