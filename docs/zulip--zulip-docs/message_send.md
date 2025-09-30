# Message Send Module Documentation

## Introduction

The `message_send` module is a core component of the Zulip messaging system responsible for handling the complete lifecycle of message sending. This module orchestrates the complex process of validating, processing, and delivering messages to recipients while managing notifications, mentions, permissions, and various message types including stream messages, direct messages, and group direct messages.

## Architecture Overview

The message sending system follows a multi-stage pipeline architecture that ensures reliable message delivery while maintaining data consistency and providing real-time notifications.

```mermaid
graph TB
    subgraph "Message Send Pipeline"
        A["Message Input"] --> B["Validation & Checks"]
        B --> C["Recipient Resolution"]
        C --> D["Content Rendering"]
        D --> E["Permission Checks"]
        E --> F["Notification Setup"]
        F --> G["Database Transaction"]
        G --> H["Event Generation"]
        H --> I["Real-time Delivery"]
    end
    
    subgraph "Core Functions"
        J["check_message"]
        K["build_message_send_dict"]
        L["do_send_messages"]
        M["get_recipient_info"]
    end
    
    A --> J
    J --> K
    K --> M
    M --> L
    L --> H
    H --> I
```

## Core Components

### RecipientInfoResult
A comprehensive data structure that encapsulates all recipient-related information for message delivery and notifications.

```mermaid
classDiagram
    class RecipientInfoResult {
        +active_user_ids: set[int]
        +online_push_user_ids: set[int]
        +dm_mention_email_disabled_user_ids: set[int]
        +dm_mention_push_disabled_user_ids: set[int]
        +stream_push_user_ids: set[int]
        +stream_email_user_ids: set[int]
        +topic_wildcard_mention_user_ids: set[int]
        +stream_wildcard_mention_user_ids: set[int]
        +followed_topic_email_user_ids: set[int]
        +followed_topic_push_user_ids: set[int]
        +topic_wildcard_mention_in_followed_topic_user_ids: set[int]
        +stream_wildcard_mention_in_followed_topic_user_ids: set[int]
        +muted_sender_user_ids: set[int]
        +um_eligible_user_ids: set[int]
        +long_term_idle_user_ids: set[int]
        +default_bot_user_ids: set[int]
        +service_bot_tuples: list[tuple[int, int]]
        +all_bot_user_ids: set[int]
        +topic_participant_user_ids: set[int]
        +sender_muted_stream: bool | None
    }
```

### ActiveUserDict
A lightweight representation of active user data for efficient processing.

```mermaid
classDiagram
    class ActiveUserDict {
        +id: int
        +enable_online_push_notifications: bool
        +enable_offline_email_notifications: bool
        +enable_offline_push_notifications: bool
        +long_term_idle: bool
        +is_bot: bool
        +bot_type: int | None
    }
```

### UserData
User-specific data structure for event delivery containing flags and mention information.

```mermaid
classDiagram
    class UserData {
        +id: int
        +flags: list[str]
        +mentioned_user_group_id: int | None
    }
```

## Message Types and Flows

### Stream Messages
Stream messages are sent to channels/topics and involve complex subscription and permission checks.

```mermaid
sequenceDiagram
    participant Client
    participant check_message
    participant validate_stream
    participant get_recipient_info
    participant do_send_messages
    participant EventSystem
    
    Client->>check_message: Send stream message
    check_message->>validate_stream: Validate stream access
    validate_stream->>check_message: Stream object
    check_message->>get_recipient_info: Get subscribers
    get_recipient_info->>check_message: RecipientInfoResult
    check_message->>do_send_messages: SendMessageRequest
    do_send_messages->>EventSystem: Generate events
    EventSystem->>Client: Real-time delivery
```

### Direct Messages
Private messages between users with permission and access control checks.

```mermaid
sequenceDiagram
    participant Sender
    participant check_can_send_direct_message
    participant check_sender_can_access_recipients
    participant do_send_messages
    participant Recipient
    
    Sender->>check_can_send_direct_message: Request DM
    check_can_send_direct_message->>check_sender_can_access_recipients: Verify access
    check_sender_can_access_recipients->>do_send_messages: Authorized
    do_send_messages->>Recipient: Message delivered
```

### Group Direct Messages
Messages sent to multiple users in a private group conversation.

## Key Functions

### get_recipient_info()
The core function for determining message recipients and their notification preferences.

```mermaid
flowchart TD
    A[get_recipient_info called] --> B{Recipient Type}
    B -->|PERSONAL| C[Handle DM recipients]
    B -->|STREAM| D[Process stream subscribers]
    B -->|DIRECT_MESSAGE_GROUP| E[Get group members]
    
    D --> F[Check subscriptions]
    F --> G[Apply notification settings]
    G --> H[Calculate wildcard mentions]
    H --> I[Filter by permissions]
    
    C --> J[Get user profiles]
    E --> K[Get group user IDs]
    
    J --> L[Combine results]
    K --> L
    I --> L
    L --> M[Return RecipientInfoResult]
```

### do_send_messages()
The main function that handles the actual message sending process.

```mermaid
flowchart TD
    A[do_send_messages called] --> B[Filter valid requests]
    B --> C[Bulk create messages]
    C --> D[Claim attachments]
    D --> E[Create UserMessage rows]
    E --> F[Process widgets]
    F --> G[Generate events]
    G --> H[Send real-time notifications]
    H --> I[Queue additional processing]
    I --> J[Return results]
```

### check_message()
Validates and prepares messages for sending, handling all permission and content checks.

## Notification System Integration

The message send module integrates with multiple notification systems:

```mermaid
graph LR
    A[Message Send] --> B[Push Notifications]
    A --> C[Email Notifications]
    A --> D[Service Bots]
    A --> E[Real-time Events]
    
    B --> F[Mobile Push]
    C --> G[Email Backend]
    D --> H[Webhook Queue]
    E --> I[Tornado Events]
    
    subgraph "Notification Types"
        J[Stream Notifications]
        K[DM Notifications]
        L[Wildcard Mentions]
        M[Followed Topics]
    end
    
    A --> J
    A --> K
    A --> L
    A --> M
```

## Permission and Security

### Stream Access Control
- Validates user permissions for stream access
- Handles archived channel notices
- Enforces stream-specific policies (empty topic restrictions)

### Direct Message Permissions
- Checks direct message permission groups
- Validates message initiation rights
- Enforces user access restrictions

### Mention Controls
- Validates stream wildcard mention permissions
- Checks topic wildcard mention rights
- Verifies user group mention access

## Data Flow and Dependencies

```mermaid
graph TB
    subgraph "External Dependencies"
        A[core_models.users]
        B[core_models.messages]
        C[core_models.streams]
        D[core_models.recipients]
        E[core_models.groups]
    end
    
    subgraph "Internal Processing"
        F[message_send]
        G[notification_data]
        H[mention_backend]
        I[stream_subscription]
    end
    
    subgraph "Output Systems"
        J[event_system]
        K[worker_queue_system]
        L[tornado_realtime]
    end
    
    A --> F
    B --> F
    C --> F
    D --> F
    E --> F
    
    F --> G
    F --> H
    F --> I
    
    F --> J
    F --> K
    F --> L
```

## Error Handling

The module implements comprehensive error handling for various scenarios:

- **StreamDoesNotExistError**: When attempting to send to non-existent streams
- **DirectMessagePermissionError**: When users lack DM permissions
- **StreamWildcardMentionNotAllowedError**: For unauthorized wildcard mentions
- **TopicWildcardMentionNotAllowedError**: For unauthorized topic mentions
- **MessagesNotAllowedInEmptyTopicError**: When empty topic messages are restricted
- **TopicsNotAllowedError**: When topic messages are not allowed

## Performance Optimizations

### Database Efficiency
- Uses bulk operations for message creation
- Implements query optimization for large recipient sets
- Leverages caching for user data and permissions

### Soft Deactivation Handling
- Optimizes UserMessage creation for inactive users
- Lazy creation of UserMessage rows for long-term idle users
- Special handling for notification-eligible users

### Mention Processing
- Efficient wildcard mention detection
- Optimized user group mention resolution
- Smart filtering of actual vs. potential mentions

## Integration Points

### Event System
Generates events for real-time message delivery through the [event_system](event_system.md) module.

### Worker Queue System
Integrates with [worker_queue_system](worker_queue_system.md) for background processing of notifications and webhooks.

### Tornado Real-time
Sends real-time updates through the [tornado_realtime](tornado_realtime.md) system for immediate client delivery.

### Core Models
Depends on [core_models](core_models.md) for user, message, stream, and recipient data management.

## Configuration and Settings

The module respects various user and realm settings:

- Notification preferences (push, email, online)
- Stream subscription settings
- Topic visibility policies
- Bot configuration and permissions
- Realm-level message policies

## Testing and Validation

The module includes comprehensive validation:

- Input sanitization and normalization
- Permission verification at multiple levels
- Content validation (widgets, attachments)
- Recipient access validation
- Rate limiting for bot notifications

This documentation provides a complete overview of the message sending subsystem, which is fundamental to Zulip's real-time communication capabilities.