# Message Edit Module Documentation

## Introduction

The message_edit module is a core component of the Zulip messaging system that handles all aspects of message editing functionality. This module provides comprehensive capabilities for editing message content, moving messages between streams and topics, resolving/unresolving topics, and managing the complex permission and notification systems that ensure message edits are handled securely and efficiently across the platform.

The module serves as the central orchestrator for message modifications, coordinating between database operations, real-time event propagation, user permissions, and notification systems to provide a seamless editing experience while maintaining data integrity and security constraints.

## Architecture Overview

### Core Components

The message_edit module is built around several key architectural components:

```mermaid
graph TB
    subgraph "Message Edit Core"
        UMR[UpdateMessageResult]
        CUM[check_update_message]
        DUM[do_update_message]
        BMER[build_message_edit_request]
    end
    
    subgraph "Validation Layer"
        VMEP[validate_message_edit_payload]
        VUCE[validate_user_can_edit_message]
        CTLC[check_time_limit_for_change_all_propagate_mode]
    end
    
    subgraph "Content Processing"
        UMC[update_message_content]
        UMF[update_user_message_flags]
        DUE[do_update_embedded_data]
    end
    
    subgraph "Notification System"
        MSRTN[maybe_send_resolve_topic_notifications]
        SMMB[send_message_moved_breadcrumbs]
        MDPRTN[maybe_delete_previous_resolve_topic_notification]
    end
    
    subgraph "Permission Management"
        CRP[can_resolve_topics]
        CET[can_edit_topic]
        CMMO[can_move_messages_out_of_channel]
        CSAB[check_stream_access_based_on_can_send_message_group]
    end
    
    UMR --> CUM
    CUM --> DUM
    CUM --> BMER
    CUM --> VMEP
    CUM --> VUCE
    DUM --> UMC
    DUM --> UMF
    DUM --> MSRTN
    DUM --> SMMB
```

### Module Dependencies

The message_edit module integrates with multiple system components:

```mermaid
graph LR
    subgraph "message_edit"
        ME[message_edit module]
    end
    
    subgraph "Core Dependencies"
        CM[core_models]
        MA[message_actions]
        ES[event_system]
        TR[tornado_realtime]
    end
    
    subgraph "Supporting Modules"
        CL[core_libraries]
        AB[authentication_and_backends]
        MW[middleware]
    end
    
    ME --> CM
    ME --> MA
    ME --> ES
    ME --> TR
    ME --> CL
    ME --> AB
    ME --> MW
    
    style ME fill:#f9f,stroke:#333,stroke-width:4px
```

## Data Flow Architecture

### Message Edit Request Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant check_update_message
    participant Validation
    participant do_update_message
    participant Database
    participant EventSystem
    participant RealTime
    
    Client->>API: Edit Request
    API->>check_update_message: check_update_message()
    check_update_message->>Validation: validate_message_edit_payload()
    check_update_message->>Validation: validate_user_can_edit_message()
    check_update_message->>check_update_message: build_message_edit_request()
    
    alt Content Edit
        check_update_message->>check_update_message: Render content
        check_update_message->>check_update_message: Check mentions
    end
    
    check_update_message->>do_update_message: do_update_message()
    do_update_message->>Database: Update message
    do_update_message->>Database: Update UserMessage flags
    do_update_message->>Database: Update edit history
    
    alt Topic/Stream Move
        do_update_message->>Database: Update related messages
        do_update_message->>do_update_message: Handle permissions
    end
    
    do_update_message->>EventSystem: Create update event
    EventSystem->>RealTime: send_event_on_commit()
    RealTime->>Client: Real-time update
    
    do_update_message-->>check_update_message: UpdateMessageResult
    check_update_message-->>API: Result
    API-->>Client: Response
```

### Content Edit Processing

```mermaid
graph TD
    A[Content Edit Request] --> B[validate_message_edit_payload]
    B --> C[validate_user_can_edit_message]
    C --> D[Render new content]
    D --> E[Check mentions & wildcards]
    E --> F[Update message content]
    F --> G[Update UserMessage flags]
    G --> H[Update edit history]
    H --> I[Create update event]
    I --> J[Send real-time notification]
    
    E --> K{Valid mentions?}
    K -->|Yes| F
    K -->|No| L[Throw error]
    
    style A fill:#bbf,stroke:#333
    style J fill:#bfb,stroke:#333
```

## Component Interactions

### Message Movement Operations

The module handles complex message movement scenarios with sophisticated permission and notification logic:

```mermaid
graph TB
    A[Message Move Request] --> B{Move Type}
    B -->|Topic Only| C[Topic Edit Path]
    B -->|Stream Only| D[Stream Edit Path]
    B -->|Both| E[Combined Edit Path]
    
    C --> F[Check topic permissions]
    F --> G[Update topic names]
    G --> H[Handle propagate mode]
    
    D --> I[Check stream permissions]
    I --> J[Handle access changes]
    J --> K[Update UserMessage rows]
    
    E --> F
    E --> I
    
    G --> L[Send notifications]
    H --> L
    K --> L
    J --> M[Handle attachment visibility]
    
    L --> N[Update user topic policies]
    M --> N
    N --> O[Send breadcrumb messages]
    
    style A fill:#fbb,stroke:#333
    style O fill:#bfb,stroke:#333
```

### Permission Validation System

```mermaid
graph TD
    A[Edit Request] --> B{Edit Type}
    B -->|Content| C[Content Permission Check]
    B -->|Topic| D[Topic Permission Check]
    B -->|Stream| E[Stream Permission Check]
    
    C --> F[User is sender?]
    F -->|No| G[Reject]
    F -->|Yes| H[Check time limits]
    
    D --> I[Check can_edit_topic]
    I --> J[Check time limits]
    J --> K[Check resolve permissions]
    
    E --> L[Check can_move_messages_out]
    L --> M[Check target stream access]
    M --> N[Check time limits]
    
    H --> O{Within limits?}
    J --> O
    N --> O
    O -->|Yes| P[Proceed]
    O -->|No| Q[Reject with error]
    
    style A fill:#bbf,stroke:#333
    style P fill:#bfb,stroke:#333
    style Q fill:#fbb,stroke:#333
```

## Key Functions and Processes

### Main Entry Point: `check_update_message`

This function serves as the primary entry point for all message editing operations. It orchestrates the entire edit process through several phases:

1. **Validation Phase**: Validates the edit request payload and user permissions
2. **Preparation Phase**: Builds the message edit request object and performs content rendering
3. **Execution Phase**: Calls `do_update_message` to perform the actual database operations
4. **Post-processing Phase**: Handles link embedding and stream activity updates

### Core Update Logic: `do_update_message`

This function handles the actual message modification with sophisticated logic for different edit types:

- **Content Edits**: Updates message content, re-renders markdown, updates mentions and flags
- **Topic Edits**: Updates topic names with proper propagation based on mode
- **Stream Edits**: Handles complex stream-to-stream moves with access control
- **Combined Edits**: Coordinates multiple edit types in a single operation

### Permission System

The module implements a comprehensive permission system that checks:

- **Content Editing**: User must be the original sender (with time limits)
- **Topic Editing**: Based on stream settings and user roles
- **Stream Moving**: Requires specific permissions and handles access changes
- **Topic Resolving**: Separate permission check for resolve/unresolve operations

## Integration with Other Modules

### Event System Integration

The module works closely with the [event_system](event_system.md) to propagate changes:

- Creates `update_message` events for real-time updates
- Handles `delete_message` events for users losing access
- Coordinates with notification systems for topic resolves

### Message Actions Coordination

Integrates with [message_actions](message_actions.md) for related operations:

- Uses message deletion functionality for access control
- Coordinates with message sending for notifications
- Shares recipient information and user data structures

### Core Models Dependency

Relies on [core_models](core_models.md) for data structures:

- Message and UserMessage models for message data
- Stream and Subscription models for permission checks
- UserProfile for user permissions and settings
- Realm for organization-level settings

## Security and Access Control

### Permission Validation

The module implements multiple layers of security checks:

```mermaid
graph LR
    A[Edit Request] --> B[User Authentication]
    B --> C[Realm Settings Check]
    C --> D[Stream Permissions]
    D --> E[Message Ownership]
    E --> F[Time Limits]
    F --> G[Content Validation]
    G --> H[Execute Edit]
    
    style A fill:#fbb,stroke:#333
    style H fill:#bfb,stroke:#333
```

### Access Control for Stream Moves

When moving messages between streams, the module carefully handles:

- **UserMessage Row Management**: Creates/deletes rows based on new access permissions
- **Attachment Visibility**: Updates public/private status of attachments
- **Guest User Handling**: Special logic for users with limited access
- **History Access**: Respects stream history visibility settings

## Error Handling

The module provides comprehensive error handling for various scenarios:

- **Permission Errors**: Clear messages when users lack required permissions
- **Time Limit Errors**: Specific error types for expired edit windows
- **Content Errors**: Validation errors for invalid content or formatting
- **Stream/Topic Errors**: Errors for invalid stream moves or topic names

## Performance Considerations

### Database Optimization

- Uses database transactions for atomic operations
- Implements efficient bulk updates for multiple messages
- Leverages database indexes for message queries
- Minimizes lock contention with strategic locking

### Real-time Performance

- Batches event notifications for efficiency
- Uses commit-time event queuing to reduce latency
- Implements selective notification to reduce client load
- Optimizes cache updates for message changes

## Notification and User Experience

### Breadcrumb Messages

The module generates contextual notification messages when topics are moved:

- **Old Thread**: Notifies users that messages were moved away
- **New Thread**: Informs users about newly arrived messages
- **Resolve Notifications**: Special handling for topic resolution

### User Topic Policy Management

Automatically manages user topic visibility policies during moves:

- **Policy Merging**: Intelligently combines policies when topics merge
- **Access-based Updates**: Removes policies for users losing stream access
- **Automatic Following**: Applies user preferences for new topics

This comprehensive approach ensures that message editing operations maintain consistency across the entire Zulip system while providing users with powerful and intuitive editing capabilities.