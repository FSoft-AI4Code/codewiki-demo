# Jira Cloud integration

Jira Cloud uses signed webhooks to trigger work from `@openhands` comments or the `openhands` label. `JiraManager` authenticates the workspace and user, loads issue details with a service account, infers a repository, and creates or resumes a Jira conversation.

```mermaid
flowchart TD
    J[Jira webhook] --> SIG[Workspace lookup + HMAC validation]
    SIG --> PARSE[Parse comment or label JobContext]
    PARSE --> AUTH[Authenticate Jira user]
    AUTH --> ISSUE[Fetch title and description]
    ISSUE --> FACT[JiraFactory]
    FACT --> EXIST{Conversation mapped?}
    EXIST -- no --> REPO[Infer repository]
    REPO --> NEW[JiraNewConversationView]
    EXIST -- yes --> OLD[JiraExistingConversationView]
    NEW --> C[Create conversation + store mapping]
    OLD --> U[Resume loop + send MessageAction]
    C --> POST[Comment tracking response]
    U --> POST
```

Webhook signatures are SHA-256 HMACs over the request body using the decrypted workspace secret. Inactive/unknown workspaces and service-account events are rejected. New conversations require an inferred repository; ambiguous inference causes a repository-selection comment. Existing conversations reuse stored issue-to-conversation mappings.
