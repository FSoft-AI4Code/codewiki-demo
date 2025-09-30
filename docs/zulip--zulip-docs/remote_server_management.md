# Remote Server Management Module

## Introduction

The Remote Server Management module is a critical component of the Zulip ecosystem that enables the Mobile Push Notifications Service to manage and interact with self-hosted Zulip servers. This module provides the infrastructure for tracking remote servers, managing billing relationships, handling push device registrations, and synchronizing audit logs for billing purposes.

## Architecture Overview

The module serves as the bridge between Zulip's cloud infrastructure and self-hosted installations, facilitating secure communication, billing management, and push notification delivery for remote deployments.

```mermaid
graph TB
    subgraph "Remote Server Management"
        RZSM[RemoteZulipServer]
        RRM[RemoteRealm]
        RPBU[RemoteRealmBillingUser]
        RSBU[RemoteServerBillingUser]
        RPD[RemotePushDevice]
        RPT[RemotePushDeviceToken]
        RZAL[RemoteZulipServerAuditLog]
        RRA[RemoteRealmAuditLog]
        RIC[RemoteInstallationCount]
        RRC[RemoteRealmCount]
    end
    
    subgraph "Core Models"
        Realm[Realm]
        User[UserProfile]
        APD[AbstractPushDevice]
        APDT[AbstractPushDeviceToken]
        ARAL[AbstractRealmAuditLog]
    end
    
    subgraph "External Systems"
        Mobile[Mobile Devices]
        Remote[Remote Servers]
        Billing[Billing System]
    end
    
    RZSM -->|hosts| RRM
    RRM -->|has| RPBU
    RZSM -->|has| RSBU
    RPD -->|registers| Mobile
    RPD -->|belongs to| RRM
    RPD -->|belongs to| Realm
    RPT -->|legacy| RPD
    RZAL -->|tracks| RZSM
    RRA -->|syncs from| Remote
    RIC -->|counts| RZSM
    RRC -->|counts| RRM
    
    APD -->|extends| RPD
    APDT -->|extends| RPT
    ARAL -->|extends| RZAL
    ARAL -->|extends| RRA
    
    RZSM -.->|communicates| Remote
    RPBU -.->|manages| Billing
    RSBU -.->|manages| Billing
```

## Core Components

### RemoteZulipServer

The central entity representing a self-hosted Zulip server registered with the push notifications service. Each remote server is identified by a unique UUID and API key pair, and maintains metadata about the server's configuration, version, and billing status.

**Key Features:**
- Unique server identification via UUID and API key
- Plan type management for billing tiers
- Rate limiting integration
- Audit log tracking
- Contact information for abuse handling

**Billing Plan Types:**
- `PLAN_TYPE_SELF_MANAGED` (100): Default self-managed hosting
- `PLAN_TYPE_SELF_MANAGED_LEGACY` (101): Legacy self-managed
- `PLAN_TYPE_COMMUNITY` (102): Community edition
- `PLAN_TYPE_BASIC` (103): Basic commercial plan
- `PLAN_TYPE_BUSINESS` (104): Business plan
- `PLAN_TYPE_ENTERPRISE` (105): Enterprise plan

### RemoteRealm

Represents individual realms (organizations) hosted on remote Zulip servers. This model tracks realm-specific information including authentication methods, organization type, and registration status.

**Key Features:**
- Links realms to their hosting server
- Tracks realm-specific billing and configuration
- Manages registration and deactivation states
- Supports both pre-8.0 and modern server versions

### RemotePushDevice

The core table for managing mobile push notification registrations on the bouncer server. This model stores device tokens and links them to both cloud and self-hosted realms.

**Key Features:**
- End-to-end encryption support
- Multi-realm device support
- Token expiration handling
- Platform-specific configurations (iOS app IDs)

### RemotePushDeviceToken

Legacy model for non-E2EE mobile push tokens. Maintains backward compatibility while being deprecated in favor of RemotePushDevice.

### Billing User Models

#### RemoteRealmBillingUser
Manages billing users for specific realms on remote servers, including user preferences for email notifications and terms of service acceptance.

#### RemoteServerBillingUser
Manages billing users at the server level, similar to RemoteRealmBillingUser but for entire server installations.

### Audit Log Models

#### RemoteZulipServerAuditLog
Authoritative storage for server-level audit events, primarily for billing and registration tracking.

#### RemoteRealmAuditLog
Synced audit data from remote servers, used for billing calculations and user activity tracking.

### Analytics Models

#### RemoteInstallationCount
Tracks server-wide metrics and statistics, including push notification forwarding counts.

#### RemoteRealmCount
Tracks realm-specific metrics, supporting both synced data from remote servers and locally generated statistics.

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant RS as Remote Server
    participant RSM as Remote Server Management
    participant PN as Push Notification Service
    participant Mobile as Mobile Device
    
    RS->>RSM: Register server (UUID, API key)
    RSM->>RSM: Create RemoteZulipServer
    RS->>RSM: Sync realm data
    RSM->>RSM: Create/update RemoteRealm
    
    Mobile->>RS: Register for push notifications
    RS->>RSM: Forward registration
    RSM->>RSM: Create RemotePushDevice
    RSM->>RSM: Validate token
    
    RS->>RS: Generate notification
    RS->>RSM: Send to bouncer
    RSM->>PN: Forward to FCM/APNs
    PN->>Mobile: Deliver notification
    
    RSM->>RSM: Update audit logs
    RSM->>RSM: Update analytics counts
```

## Component Interactions

```mermaid
graph LR
    subgraph "Registration Flow"
        A[Remote Server] -->|register_server| B[RemoteZulipServer]
        B -->|create| C[RemoteRealm]
        C -->|setup| D[Billing Users]
    end
    
    subgraph "Notification Flow"
        E[Mobile Device] -->|register| F[RemotePushDevice]
        G[Remote Server] -->|send| H[Push Service]
        H -->|forward| I[Mobile Device]
    end
    
    subgraph "Billing Flow"
        J[RemoteRealmAuditLog] -->|sync| K[Analytics]
        K -->|calculate| L[Billing]
        L -->|update| M[Plan Type]
    end
```

## Key Functions and Utilities

### User Count Calculations

The module provides sophisticated user counting mechanisms for billing purposes:

```python
# Get user counts for entire server
get_remote_server_guest_and_non_guest_count(server_id, event_time)

# Get user counts for specific realm
get_remote_realm_guest_and_non_guest_count(remote_realm, event_time)

# Process audit logs for user counts
get_remote_customer_user_count(audit_logs)
```

### Rate Limiting

Remote servers are subject to rate limiting through the `RateLimitedRemoteZulipServer` class, which integrates with Zulip's rate limiting framework.

### Server Lookup

```python
# Find server by UUID
get_remote_server_by_uuid(uuid)
```

## Integration Points

### Corporate Billing Integration

The module integrates with the [corporate billing system](corporate_billing.md) through:
- Plan type management
- User count calculations
- Billing user management
- Audit log synchronization

### Core Models Integration

Leverages core Zulip models for:
- Realm and user management ([core_models.md](core_models.md))
- Push device abstractions
- Audit log frameworks
- Rate limiting infrastructure

### Analytics Integration

Works with the [analytics module](analytics.md) to provide:
- Installation-wide metrics
- Realm-specific statistics
- Push notification tracking
- Usage analytics

## Security Considerations

### Authentication
- API key-based authentication for remote servers
- UUID-based server identification
- Secure token handling for push notifications

### Data Privacy
- End-to-end encryption support for push notifications
- Secure handling of user data across server boundaries
- Audit trail for all server interactions

### Rate Limiting
- API rate limiting by remote server
- Protection against abuse and excessive requests
- Configurable rate limits per server

## Database Schema Design

### Key Constraints
- Unique server UUID and API key combinations
- Unique device token registrations
- Unique audit log entries per server/remote ID
- Complex unique constraints for analytics data

### Indexes
- Optimized queries for server and realm lookups
- Efficient audit log synchronization
- Fast analytics data retrieval
- Push device token queries

## Process Flows

### Server Registration Process

```mermaid
flowchart TD
    A[Remote Server] -->|submit registration| B[Validate UUID/API Key]
    B -->|valid| C[Create RemoteZulipServer]
    C -->|success| D[Setup Billing Users]
    D -->|complete| E[Enable Push Service]
    B -->|invalid| F[Reject Registration]
```

### Push Notification Delivery

```mermaid
flowchart LR
    A[Message Event] -->|trigger| B[Check Push Settings]
    B -->|enabled| C[Queue Notification]
    C -->|process| D[Send to Bouncer]
    D -->|validate| E[Forward to FCM/APNs]
    E -->|deliver| F[Mobile Device]
    D -->|invalid| G[Log Error]
```

### Audit Log Synchronization

```mermaid
flowchart TD
    A[Remote Server] -->|send audit logs| B[Validate Server]
    B -->|authorized| C[Process Audit Entries]
    C -->|deduplicate| D[Store in RemoteRealmAuditLog]
    D -->|update| E[Calculate User Counts]
    E -->|trigger| F[Update Billing]
```

## Dependencies

### Internal Dependencies
- **Core Models**: Extends abstract models for push devices and audit logs
- **Corporate Billing**: Integrates with billing session management
- **Analytics**: Shares base count models and analytics infrastructure
- **Rate Limiting**: Uses Zulip's rate limiting framework

### External Dependencies
- Django ORM for database operations
- Django authentication and validation
- Standard library datetime and UUID handling

## Future Considerations

### Migration Path
- Gradual deprecation of RemotePushDeviceToken in favor of RemotePushDevice
- Enhanced E2EE support for all push notifications
- Improved audit log synchronization efficiency

### Scalability
- Optimized queries for large-scale remote server deployments
- Efficient handling of bulk operations
- Caching strategies for frequently accessed data

### Security Enhancements
- Enhanced authentication mechanisms
- Improved token management
- Better abuse detection and prevention

This module forms the backbone of Zulip's ability to provide push notification services to self-hosted installations while maintaining security, billing accuracy, and operational efficiency across the entire ecosystem.