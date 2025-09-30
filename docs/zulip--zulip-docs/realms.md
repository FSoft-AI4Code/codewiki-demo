# Realms Module Documentation

## Introduction

The realms module is the foundational component of Zulip's multi-tenant architecture, managing organizations (called "realms") within a Zulip server. Each realm represents an isolated organization with its own users, streams, messages, and configuration settings. This module provides the core data models and functionality for realm management, authentication, permissions, and organization-level settings.

## Core Components

### Realm Model
The central `Realm` model represents an organization within Zulip, containing comprehensive configuration for:
- **Identity**: Name, description, subdomain, and unique identifiers
- **Authentication**: Supported authentication methods and domain restrictions
- **Permissions**: Granular permission groups for various actions
- **Features**: Message editing, video chat, notifications, and content policies
- **Limits**: Message retention, upload quotas, and user limits
- **Organization Type**: Business, education, open-source, etc.

### RealmDomain Model
Manages allowed email domains for organizations that restrict membership to specific domains, supporting subdomain allowances.

### RealmExport Model
Tracks data export operations with different export types (public, full with/without consent) and status tracking.

## Architecture

### Data Model Relationships

```mermaid
erDiagram
    Realm ||--o{ RealmDomain : "has many"
    Realm ||--o{ RealmExport : "has many"
    Realm ||--o{ UserProfile : "has many"
    Realm ||--o{ Stream : "has many"
    Realm ||--o{ RealmAuthenticationMethod : "has many"
    Realm ||--o{ UserGroup : "has many"
    
    RealmDomain {
        int id PK
        int realm_id FK
        string domain
        bool allow_subdomains
    }
    
    RealmExport {
        int id PK
        int realm_id FK
        int type
        int status
        datetime date_requested
        string export_path
    }
    
    Realm {
        int id PK
        string name
        string string_id
        uuid uuid
        string description
        bool deactivated
        int plan_type
        int org_type
    }
```

### Permission System Architecture

```mermaid
graph TD
    Realm[Realm] --> PermissionGroups[Permission Groups]
    PermissionGroups --> CanCreateBots[can_create_bots_group]
    PermissionGroups --> CanInviteUsers[can_invite_users_group]
    PermissionGroups --> CanDeleteMessages[can_delete_any_message_group]
    PermissionGroups --> CanCreateStreams[can_create_public_channel_group]
    PermissionGroups --> CanManageBilling[can_manage_billing_group]
    PermissionGroups --> CanModerate[can_mention_many_users_group]
    
    SystemGroups[System Groups] --> Owners[Owners]
    SystemGroups --> Admins[Administrators]
    SystemGroups --> Moderators[Moderators]
    SystemGroups --> FullMembers[Full Members]
    SystemGroups --> Members[Members]
    SystemGroups --> Everyone[Everyone]
    SystemGroups --> Nobody[Nobody]
    
    PermissionGroups -.-> SystemGroups
```

### Authentication Integration

```mermaid
sequenceDiagram
    participant User
    participant Realm
    participant AuthMethod[RealmAuthenticationMethod]
    participant Backend[Auth Backend]
    
    User->>Realm: Access realm
    Realm->>AuthMethod: Get enabled methods
    AuthMethod->>Backend: Check supported backends
    Backend-->>AuthMethod: Return available backends
    AuthMethod-->>Realm: Return enabled methods
    Realm-->>User: Present authentication options
```

## Key Features

### Multi-Tenant Architecture
- **Isolated Organizations**: Each realm operates independently with complete data isolation
- **Subdomain Support**: Realms are accessed via subdomains (e.g., `company.zulipchat.com`)
- **Custom Branding**: Per-realm icons, logos, and welcome messages
- **Domain Restrictions**: Optional email domain restrictions for membership

### Granular Permission System
The module implements a sophisticated permission system using UserGroup assignments:

- **25+ Permission Categories**: From basic actions like inviting users to advanced features like managing billing
- **System Groups Integration**: Leverages the system groups module for role-based permissions
- **Flexible Configuration**: Each permission can be assigned to any user group
- **Default Security**: Conservative defaults with administrators having most permissions

### Organization Types and Plans
Supports various organization types with tailored features:
- **Business**: Standard commercial organizations
- **Education**: Academic institutions with special considerations
- **Open Source**: Free for open-source projects
- **Non-profit**: Discounted pricing for non-profits
- **Government**: Public sector organizations

### Message and Content Policies
Comprehensive content management:
- **Message Retention**: Configurable retention policies with automatic cleanup
- **Edit History**: Control over message edit history visibility
- **Content Moderation**: Wildcard mention controls and message deletion policies
- **Topic Management**: Empty topic policies and topic resolution permissions

## Integration Points

### Authentication and Backends
Integrates with the [authentication_and_backends](authentication_and_backends.md) module to support multiple authentication methods:
- Email/password authentication
- LDAP integration
- SAML SSO
- Social authentication (Google, GitHub, GitLab, etc.)
- Custom authentication backends

### User Management
Works closely with the [core_models](core_models.md) module's UserProfile model:
- User creation and management within realms
- Role assignments (owner, admin, moderator, member, guest)
- User deactivation and reactivation
- Cross-realm user access controls

### Stream and Message System
Integrates with message and stream modules:
- Stream creation permissions
- Message visibility controls
- Web-public stream access
- Message retention and archiving

### Analytics and Billing
Connects to [corporate_billing](corporate_billing.md) and [analytics](analytics.md) modules:
- Usage tracking and reporting
- Plan limitations and quotas
- Billing management permissions
- Resource usage monitoring

## Configuration Management

### Realm Settings Categories

```mermaid
graph LR
    RealmSettings[Realm Settings] --> Authentication[Authentication]
    RealmSettings --> Permissions[Permissions]
    RealmSettings --> Features[Features]
    RealmSettings --> Limits[Limits]
    RealmSettings --> Appearance[Appearance]
    RealmSettings --> Notifications[Notifications]
    
    Authentication --> AuthMethods[Auth Methods]
    Authentication --> DomainRestrict[Domain Restrictions]
    Authentication --> InvitePolicy[Invite Policy]
    
    Permissions --> MessagePerms[Message Permissions]
    Permissions --> StreamPerms[Stream Permissions]
    Permissions --> UserPerms[User Management]
    Permissions --> AdminPerms[Admin Functions]
    
    Features --> VideoChat[Video Chat]
    Features --> Integrations[Integrations]
    Features --> Mobile[Mobile Features]
    Features --> WebPublic[Web Public Streams]
    
    Limits --> MessageRetention[Message Retention]
    Limits --> UploadQuota[Upload Quota]
    Limits --> UserLimits[User Limits]
    Limits --> RateLimits[Rate Limits]
```

### Dynamic Configuration
The module supports runtime configuration changes:
- **Hot Reloading**: Most settings take effect immediately
- **Cache Management**: Intelligent cache invalidation on configuration changes
- **Event Propagation**: Configuration changes are broadcast to connected clients
- **Validation**: Comprehensive validation for all configuration options

## Security Features

### Access Control
- **Domain Restrictions**: Email domain validation for organization membership
- **Invitation System**: Controlled user onboarding with invitation limits
- **Role-Based Permissions**: Hierarchical permission system
- **Guest Access**: Special guest user type with limited permissions

### Content Security
- **Message Retention**: Automatic message cleanup based on policies
- **Content Filtering**: GIPHY rating controls and content policies
- **Web Public Streams**: Controlled public access to selected streams
- **Export Controls**: Secure data export with audit trails

### Authentication Security
- **Multi-Factor Authentication**: Support for 2FA
- **Session Management**: Secure session handling
- **Rate Limiting**: Protection against brute force attacks
- **Audit Logging**: Comprehensive audit trails for security events

## Performance Considerations

### Caching Strategy
- **Realm Cache**: Aggressive caching of realm configuration
- **Permission Cache**: Cached permission calculations
- **Upload Space Cache**: Cached upload quota usage
- **Cache Invalidation**: Smart cache invalidation on changes

### Database Optimization
- **Indexed Fields**: Strategic indexing for common queries
- **Query Optimization**: Optimized queries for realm operations
- **Bulk Operations**: Efficient bulk operations for large datasets
- **Connection Pooling**: Database connection management

## Data Flow

### Realm Creation Process

```mermaid
sequenceDiagram
    participant Admin
    participant System
    participant RealmDB[Realm Database]
    participant UserGroupDB[UserGroup Database]
    participant StreamDB[Stream Database]
    
    Admin->>System: Create Realm
    System->>RealmDB: Create Realm Record
    RealmDB-->>System: Realm ID
    System->>UserGroupDB: Create System Groups
    UserGroupDB-->>System: Group IDs
    System->>RealmDB: Assign Permission Groups
    System->>StreamDB: Create Default Streams
    StreamDB-->>System: Stream IDs
    System-->>Admin: Realm Created
```

### Authentication Flow

```mermaid
flowchart TD
    User[User] -->|Access Realm| RealmCheck{Realm Exists?}
    RealmCheck -->|No| Error404[404 Error]
    RealmCheck -->|Yes| AuthCheck{Authentication Required?}
    AuthCheck -->|No| GuestAccess[Guest Access]
    AuthCheck -->|Yes| AuthMethods[Get Auth Methods]
    AuthMethods -->|Multiple| AuthChoice[Choose Auth Method]
    AuthMethods -->|Single| DirectAuth[Direct Authentication]
    AuthChoice --> Authenticate[Authenticate User]
    DirectAuth --> Authenticate
    Authenticate -->|Success| UserProfile[Load User Profile]
    Authenticate -->|Failure| AuthError[Authentication Error]
    UserProfile --> AccessGranted[Access Granted]
    GuestAccess --> AccessGranted
```

## Error Handling

### Validation Errors
- **Domain Validation**: Email domain validation with detailed error messages
- **Configuration Validation**: Comprehensive validation for all settings
- **Permission Validation**: Permission assignment validation
- **Quota Validation**: Upload and usage quota validation

### Exception Types
- `DomainNotAllowedForRealmError`: Domain restriction violations
- `DisposableEmailError`: Disposable email detection
- `EmailContainsPlusError`: Email format validation
- `InvalidFakeEmailDomainError`: Fake email domain issues
- `JsonableError`: General API error handling

## Testing and Development

### Test Utilities
- **Realm Creation**: Utilities for creating test realms
- **Permission Testing**: Helpers for testing permission scenarios
- **Configuration Testing**: Tools for testing configuration changes
- **Mock Data**: Sample data for development and testing

### Development Features
- **Debug Mode**: Enhanced logging and debugging capabilities
- **Test Configuration**: Special settings for testing environments
- **Cache Control**: Cache management for development
- **Hot Reloading**: Configuration changes without restart

## Deployment Considerations

### Multi-Server Deployment
- **Shared Database**: Realm data shared across application servers
- **Cache Consistency**: Cache synchronization across servers
- **Load Balancing**: Realm-aware load balancing
- **Failover**: Realm availability during server failures

### Scaling Considerations
- **Horizontal Scaling**: Realm data partitioning strategies
- **Vertical Scaling**: Resource allocation per realm
- **Geographic Distribution**: Realm placement strategies
- **Performance Monitoring**: Realm-specific performance metrics

## API Integration

### REST API Endpoints
The realms module provides comprehensive API endpoints for:
- Realm creation and management
- Configuration updates
- User and permission management
- Export operations
- Analytics and reporting

### WebSocket Events
Real-time updates for:
- Configuration changes
- Permission updates
- User status changes
- Realm-wide notifications

### Integration Hooks
- **External Authentication**: Integration with external auth systems
- **Directory Services**: LDAP/Active Directory integration
- **Analytics Platforms**: Usage and analytics data export
- **Monitoring Systems**: Health and performance monitoring

This comprehensive documentation covers the realms module's architecture, features, and integration points within the Zulip ecosystem. The module serves as the foundation for Zulip's multi-tenant architecture, providing robust organization management with extensive customization options and security features.