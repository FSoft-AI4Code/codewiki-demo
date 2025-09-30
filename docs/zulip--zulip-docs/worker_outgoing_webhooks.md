# Worker Outgoing Webhooks Module

## Introduction

The `worker_outgoing_webhooks` module is a specialized queue processing worker responsible for handling outgoing webhook integrations in Zulip. It processes webhook events from the `outgoing_webhooks` queue and makes HTTP requests to external services based on bot configurations. This module serves as a bridge between Zulip's internal messaging system and external webhook endpoints, enabling powerful integrations with third-party services.

## Architecture Overview

The module implements a queue-based architecture pattern where webhook events are processed asynchronously, ensuring reliable delivery to external services without blocking the main application flow.

```mermaid
graph TB
    subgraph "Zulip System"
        MQ[Message Queue<br/>outgoing_webhooks]
        OW[OutgoingWebhookWorker]
        BL[Bot Library]
        OWL[Outgoing Webhook Lib]
        DB[(Database)]
    end
    
    subgraph "External Services"
        ES1[External Service 1]
        ES2[External Service 2]
        ES3[External Service N]
    end
    
    MQ -->|consume event| OW
    OW -->|get bot profile| BL
    OW -->|get services| DB
    OW -->|make HTTP call| OWL
    OWL -->|POST request| ES1
    OWL -->|POST request| ES2
    OWL -->|POST request| ES3
    OW -->|flag processed| BL
```

## Core Components

### OutgoingWebhookWorker

The `OutgoingWebhookWorker` class is the main component that processes outgoing webhook events from the queue. It inherits from `QueueProcessingWorker` and is decorated with `@assign_queue("outgoing_webhooks")` to handle the specific queue.

**Key Responsibilities:**
- Consume webhook events from the `outgoing_webhooks` queue
- Retrieve bot configuration and associated services
- Execute HTTP requests to external webhook endpoints
- Mark messages as processed after successful webhook calls

**Process Flow:**
```mermaid
sequenceDiagram
    participant Q as Queue
    participant OW as OutgoingWebhookWorker
    participant DB as Database
    participant BL as Bot Library
    participant OWL as OutgoingWebhookLib
    participant ES as External Service
    
    Q->>OW: consume(event)
    OW->>DB: get_user_profile_by_id()
    OW->>DB: get_bot_services()
    loop For each service
        OW->>OWL: get_outgoing_webhook_service_handler()
        OW->>OWL: do_rest_call(base_url, event, handler)
        OWL->>ES: HTTP POST request
    end
    OW->>BL: do_flag_service_bots_messages_as_processed()
```

## Dependencies and Integration

### Internal Dependencies

The module relies on several key components from other Zulip modules:

1. **[worker_queue_system](worker_queue_system.md)**: Inherits from `QueueProcessingWorker` base class
2. **[core_libraries](core_libraries.md)**: Uses bot library functions for service management
3. **Outgoing Webhook Library**: Handles HTTP request logic and service handler management

### External Service Integration

The worker integrates with external services through:
- RESTful HTTP POST requests
- Configurable webhook endpoints per bot service
- Service-specific handlers for request formatting

## Data Flow

### Event Structure

Incoming events contain the following key data:
```json
{
    "message": {
        "id": "message_id",
        "content": "message content"
    },
    "user_profile_id": "bot_user_id"
}
```

### Processing Pipeline

```mermaid
graph LR
    A[Raw Event] --> B[Extract Message & Bot ID]
    B --> C[Retrieve Bot Profile]
    C --> D[Get Bot Services]
    D --> E[For Each Service]
    E --> F[Get Service Handler]
    F --> G[Make HTTP Request]
    G --> H[Process Response]
    H --> I[Flag as Processed]
```

## Configuration and Setup

### Queue Assignment

The worker is automatically assigned to the `outgoing_webhooks` queue through the `@assign_queue` decorator, ensuring it only processes relevant events.

### Bot Service Configuration

Bot services are configured through the database and retrieved using `get_bot_services()`, allowing dynamic configuration of webhook endpoints without worker restarts.

## Error Handling and Reliability

### Message Processing Guarantees

- Messages are flagged as processed only after all webhook calls complete
- Failed webhook calls are handled by the outgoing webhook library
- Queue-based processing ensures at-least-once delivery semantics

### Logging and Monitoring

The module includes comprehensive logging through Python's logging framework, with the logger named `zerver.worker.outgoing_webhooks` for easy identification and monitoring.

## Performance Considerations

### Scalability

- Asynchronous queue processing prevents blocking main application
- Multiple worker instances can process the queue in parallel
- Service lookups are optimized through database queries

### Resource Management

- HTTP connections are managed by the outgoing webhook library
- Database connections are handled through Django's ORM
- Memory usage is optimized by processing one event at a time

## Security Considerations

### Authentication

- Bot authentication is handled through user profile verification
- Service-specific authentication is managed by individual service handlers
- External webhook calls respect configured security settings

### Data Privacy

- Only necessary message data is sent to external services
- Bot permissions are verified before processing
- Sensitive information is filtered according to bot configuration

## Related Documentation

- [Worker Queue System](worker_queue_system.md) - Base queue processing infrastructure
- [Core Libraries](core_libraries.md) - Bot library and service management
- [Message Actions](message_actions.md) - Message processing and event generation
- [Event System](event_system.md) - Event types and handling mechanisms

## API Reference

### OutgoingWebhookWorker

```python
@assign_queue("outgoing_webhooks")
class OutgoingWebhookWorker(QueueProcessingWorker)
```

**Methods:**

- `consume(event: dict[str, Any]) -> None`: Process a webhook event from the queue

**Parameters:**
- `event`: Dictionary containing message data and bot user profile ID

**Returns:** None

**Raises:** Various exceptions handled by the queue processing system