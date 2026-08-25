# Linear integration

Linear integration consumes signed GraphQL webhook events for `@openhands` comments and newly added `openhands` labels. `LinearManager` resolves the workspace from the actor URL, authenticates the Linear user, enriches the issue, infers a Git repository, and creates or resumes a conversation.

```mermaid
sequenceDiagram
    participant L as Linear
    participant M as LinearManager
    participant F as LinearFactory
    participant C as Conversation service
    L->>M: signed Comment/Issue webhook
    M->>M: HMAC and workspace validation
    M->>M: fetch issue via GraphQL
    M->>F: create new/existing view
    F->>M: normalized view
    M->>M: infer repository from issue text
    M->>C: create or resume
    C-->>M: conversation id
    M->>L: acknowledgement comment
```

`LinearManager` uses the service-account API key for issue queries and comments, while the user’s OpenHands authentication supplies provider tokens for repository discovery. Synced GitHub owner/repository metadata is appended to the issue description when available. Ambiguous repository inference produces a selection request. Conversation mappings are stored through `LinearIntegrationStore`.
