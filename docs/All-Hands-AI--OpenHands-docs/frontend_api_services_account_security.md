# Frontend API Services: Account and Security

This sub-module contains account-management and security-policy clients. They share the Axios transport but target separate backend concerns.

## Account services

`SecretsService` manages custom secrets and Git provider tokens:

- `getSecrets()` returns metadata without secret values.
- `createSecret()` sends a name, value, and optional description and returns `true` for HTTP 201.
- `updateSecret()` changes name/description without sending a value and returns `true` for HTTP 200.
- `deleteSecret()` removes a secret and returns `true` for HTTP 200.
- `addGitProvider()` sends a provider-to-token map to `/api/add-git-providers`.

`ApiKeysClient` lists, creates, and deletes user API keys. The full key is returned only by `createApiKey()`; list results contain the safe `prefix` and timestamps. `getApiKeys()` defensively returns an empty array if the backend payload is not an array.

`OpenHands` additionally owns billing helpers for checkout, customer setup, credits, and subscription access.

## Security service

`InvariantService` reads or updates the active security policy and risk severity and exports security traces:

```mermaid
flowchart TB
    UI[Account/security UI] --> Secrets[SecretsService]
    UI --> Keys[ApiKeysClient]
    UI --> Inv[InvariantService]
    Secrets --> SecretAPI[/api/secrets\n/api/add-git-providers]
    Keys --> KeyAPI[/api/keys]
    Inv --> Policy[/api/security/policy]
    Inv --> Severity[/api/security/settings]
    Inv --> Trace[/api/security/export-trace]
```

`GetSecretsResponse` intentionally uses `Omit<CustomSecret, "value">[]`, reflecting that secret values are write-only from the frontend's perspective. Mutations propagate transport errors unless the caller handles them.
