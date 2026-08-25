# Slack integration

Slack support starts conversations from bot mentions and continues them in threads. It correlates Slack users to OpenHands users, offers OAuth login for unknown users, infers repositories from text, and uses interactive repository selection when inference is ambiguous.

```mermaid
flowchart TD
    E[Slack event] --> AUTH[SlackUser lookup]
    AUTH --> KNOWN{Known and authenticated?}
    KNOWN -- no --> OAUTH[Signed OAuth state + ephemeral login link]
    KNOWN -- yes --> F[SlackFactory]
    F --> EXIST{Thread mapped?}
    EXIST -- yes --> U[Update existing conversation]
    EXIST -- no --> REPO{Repository in message?}
    REPO -- unique --> N[New conversation]
    REPO -- ambiguous --> FORM[Ephemeral select form]
    FORM --> N
    N --> STORE[Store Slack mapping]
    STORE --> POST[Thread acknowledgement]
    U --> POST
```

`SlackManager` posts ephemeral responses for login and repository selection, and normal messages in the originating thread. `SlackNewConversationView` fetches up to `CONTEXT_LIMIT` prior messages, strips the bot mention, and converts history into conversation instructions. `SlackUpdateExistingConversationView` verifies that the Slack user owns the mapped conversation, checks that it still exists, resumes the agent loop, and sends a new `MessageAction`.
