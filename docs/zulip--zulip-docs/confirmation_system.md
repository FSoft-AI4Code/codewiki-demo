# Confirmation System Module Documentation

## Introduction

The confirmation system module is a critical security component in Zulip that manages secure confirmation links for various user actions and system operations. It provides a centralized framework for generating, validating, and managing confirmation tokens across different types of operations including user registration, email changes, invitations, realm creation, and billing operations.

## Architecture Overview

### Core Components

The confirmation system is built around two primary components:

1. **Confirmation Model** (`confirmation.models.Confirmation`): The central database model that stores confirmation records
2. **ConfirmationType** (`confirmation.models.ConfirmationType`): Configuration class that defines properties for different confirmation types

### System Architecture

```mermaid
graph TB
    subgraph "Confirmation System Core"
        CM[Confirmation Model]
        CT[ConfirmationType]
        GK[generate_key]
        CO[create_confirmation_object]
        CCL[create_confirmation_link]
        GOFK[get_object_from_key]
    end
    
    subgraph "Supported Object Types"
        MU[MultiuseInvite]
        PR[PreregistrationRealm]
        PU[PreregistrationUser]
        ECS[EmailChangeStatus]
        UP[UserProfile]
        RRS[RealmReactivationStatus]
        RCS[RealmCreationStatus]
        PRRBU[PreregistrationRemoteRealmBillingUser]
        PRSBU[PreregistrationRemoteServerBillingUser]
    end
    
    subgraph "External Dependencies"
        REALM[Realm Model]
        CT_MODEL[ContentType Model]
        SETTINGS[Django Settings]
    end
    
    CM --> CT
    CO --> CM
    CO --> GK
    CCL --> CO
    GOFK --> CM
    
    CM -.-> MU
    CM -.-> PR
    CM -.-> PU
    CM -.-> ECS
    CM -.-> UP
    CM -.-> RRS
    CM -.-> RCS
    CM -.-> PRRBU
    CM -.-> PRSBU
    
    CM --> REALM
    CM --> CT_MODEL
    CT --> SETTINGS
```

## Component Details

### Confirmation Model

The `Confirmation` model serves as the central storage mechanism for all confirmation-related data:

- **Generic Foreign Key**: Uses Django's contenttypes framework to associate with any model
- **Confirmation Key**: Unique 24-character base32-encoded token (120 bits of entropy)
- **Expiry Management**: Configurable expiration dates with database indexing for efficient cleanup
- **Realm Association**: Optional link to realms for realm-specific confirmations
- **Type System**: Integer-based type system for different confirmation categories

### Confirmation Types

The system supports 11 distinct confirmation types, each with specific use cases and validity periods:

```mermaid
graph LR
    subgraph "User Management"
        UR[USER_REGISTRATION<br/>Type: 1]
        INV[INVITATION<br/>Type: 2]
        EC[EMAIL_CHANGE<br/>Type: 3]
        NR[NEW_REALM_USER_REGISTRATION<br/>Type: 7]
    end
    
    subgraph "Realm Operations"
        RR[REALM_REACTIVATION<br/>Type: 8]
        CCR[CAN_CREATE_REALM<br/>Type: 11]
    end
    
    subgraph "Communication"
        UNS[UNSUBSCRIBE<br/>Type: 4]
        MI[MULTIUSE_INVITE<br/>Type: 6]
    end
    
    subgraph "Remote Server"
        RSL[REMOTE_SERVER_BILLING_LEGACY_LOGIN<br/>Type: 9]
        RRL[REMOTE_REALM_BILLING_LEGACY_LOGIN<br/>Type: 10]
    end
    
    subgraph "Legacy"
        SR[SERVER_REGISTRATION<br/>Type: 5]
    end
```

### Key Generation and Security

The system implements cryptographically secure key generation:

```python
def generate_key() -> str:
    # 24 characters * 5 bits of entropy/character = 120 bits of entropy
    return b32encode(secrets.token_bytes(15)).decode().lower()
```

Security features include:
- **High Entropy**: 120 bits of entropy using Python's `secrets` module
- **Length Validation**: Supports both 24-character (current) and 40-character (legacy) keys
- **Expiration Handling**: Configurable expiration with database-level indexing
- **Status Tracking**: Integration with object status fields for one-time use confirmations

## Data Flow

### Confirmation Creation Flow

```mermaid
sequenceDiagram
    participant Client
    participant System
    participant ConfirmationSystem
    participant Database
    
    Client->>System: Request operation requiring confirmation
    System->>ConfirmationSystem: create_confirmation_link(obj, type)
    ConfirmationSystem->>ConfirmationSystem: generate_key()
    ConfirmationSystem->>ConfirmationSystem: create_confirmation_object()
    ConfirmationSystem->>Database: Create Confirmation record
    ConfirmationSystem->>ConfirmationSystem: Build URL with confirmation_key
    ConfirmationSystem->>Client: Return confirmation link
    
    Note over Client,Database: Link sent to user via email/notification
```

### Confirmation Validation Flow

```mermaid
sequenceDiagram
    participant User
    participant WebApp
    participant ConfirmationSystem
    participant Database
    
    User->>WebApp: Click confirmation link
    WebApp->>ConfirmationSystem: get_object_from_key(key, types)
    ConfirmationSystem->>Database: Query Confirmation record
    Database-->>ConfirmationSystem: Return confirmation data
    
    alt Key invalid/expired
        ConfirmationSystem-->>User: Return error response
    else Key valid
        ConfirmationSystem->>ConfirmationSystem: Check object status
        ConfirmationSystem->>Database: Update object status (if applicable)
        ConfirmationSystem-->>WebApp: Return confirmed object
        WebApp-->>User: Proceed with confirmed operation
    end
```

## Integration Points

### Core Models Integration

The confirmation system integrates with multiple core Zulip models:

- **User Management**: [core_models.md](core_models.md#users)
  - `UserProfile`: For email change confirmations and unsubscribe links
  - `PreregistrationUser`: For user registration and invitation processes
  
- **Realm Management**: [core_models.md](core_models.md#realms)
  - `Realm`: For realm reactivation confirmations
  - `PreregistrationRealm`: For new realm creation confirmations
  - `RealmReactivationStatus`: For realm reactivation status tracking

- **Message System**: [core_models.md](core_models.md#messages)
  - `EmailChangeStatus`: For email change confirmation workflows

### Authentication Integration

The system works closely with authentication components:

- **Authentication Backends**: [authentication_and_backends.md](authentication_and_backends.md)
  - Provides secure confirmation for authentication-related operations
  - Integrates with external authentication methods

### API Integration

Confirmation links are generated and validated through API endpoints:

- **User API Views**: [api_views.md](api_views.md#users)
  - User registration and profile update confirmations
  - Email change confirmations
  
- **Authentication API Views**: [api_views.md](api_views.md#auth)
  - Login and registration confirmation flows
  - Two-factor authentication confirmations

## Configuration and Settings

### Validity Periods

Different confirmation types have configurable validity periods:

- **Default Validity**: `CONFIRMATION_LINK_DEFAULT_VALIDITY_DAYS` (typically 7 days)
- **Invitation Links**: `INVITATION_LINK_VALIDITY_DAYS` (typically 14 days)
- **Realm Creation**: `CAN_CREATE_REALM_LINK_VALIDITY_DAYS` (typically 7 days)
- **Unsubscribe Links**: 1,000,000 days (effectively never expires)

### Status Management

The system uses status constants for managing confirmation lifecycle:

- **STATUS_USED**: Marked when confirmation is successfully used
- **STATUS_REVOKED**: Marked when confirmation is manually revoked

## Error Handling

The system implements comprehensive error handling through `ConfirmationKeyError`:

```python
class ConfirmationKeyError(Exception):
    WRONG_LENGTH = 1    # Invalid key format
    EXPIRED = 2         # Key has expired
    DOES_NOT_EXIST = 3  # Key not found in database
```

Each error type maps to a specific user-facing error page for clear communication.

## Security Considerations

### Key Security
- **Cryptographic Randomness**: Uses `secrets.token_bytes()` for key generation
- **Sufficient Entropy**: 120 bits of entropy prevents brute force attacks
- **Database Indexing**: Efficient key lookups prevent timing attacks

### Access Control
- **Type Validation**: Confirmation types are validated against allowed lists
- **Status Checking**: Used/revoked confirmations are properly rejected
- **Realm Isolation**: Confirmations are scoped to appropriate realms

### Expiration Management
- **Configurable Expiration**: Different confirmation types have appropriate lifetimes
- **Database Indexing**: Expired confirmations can be efficiently cleaned up
- **Graceful Degradation**: Expired confirmations provide clear error messages

## Usage Examples

### Creating a User Registration Confirmation

```python
# Create confirmation for user registration
confirmation_link = create_confirmation_link(
    prereg_user,
    Confirmation.USER_REGISTRATION
)
```

### Validating an Email Change Confirmation

```python
# Validate email change confirmation
email_change_status = get_object_from_key(
    confirmation_key,
    [Confirmation.EMAIL_CHANGE],
    mark_object_used=True
)
```

### Generating an Unsubscribe Link

```python
# Create one-click unsubscribe link
unsubscribe_link = one_click_unsubscribe_link(
    user_profile,
    "marketing_emails"
)
```

## Dependencies

The confirmation system has minimal external dependencies:

- **Django Framework**: Core ORM and contenttypes framework
- **Zerver Models**: Integration with user, realm, and message models
- **Zilencer Models**: Optional integration for remote server billing (when enabled)
- **Django Settings**: Configuration for validity periods and status constants

## Future Considerations

The system is designed to be extensible for new confirmation types and can accommodate additional security features such as:

- Rate limiting for confirmation attempts
- Additional validation layers
- Integration with external confirmation services
- Enhanced audit logging for confirmation events