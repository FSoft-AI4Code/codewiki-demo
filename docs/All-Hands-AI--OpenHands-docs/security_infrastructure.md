# Security Infrastructure Module

The security_infrastructure module provides enterprise-grade authentication and authorization middleware for the OpenHands platform. This module is part of the enterprise server infrastructure and implements sophisticated cookie-based authentication, token management, and security policy enforcement.

## Overview

The security_infrastructure module serves as the primary security gateway for enterprise deployments, handling:

- **Authentication State Management**: Maintains and refreshes authentication tokens automatically
- **Cookie Security**: Implements secure cookie handling with domain and SameSite policies
- **Terms of Service Enforcement**: Ensures users have accepted current terms before accessing protected resources
- **Email Verification**: Enforces email verification requirements for sensitive operations
- **Token Lifecycle Management**: Handles token refresh, validation, and cleanup
- **Security Policy Enforcement**: Applies security rules consistently across all API endpoints

## Architecture

```mermaid
graph TB
    subgraph "Security Infrastructure"
        SACM[SetAuthCookieMiddleware]
        
        subgraph "Authentication Flow"
            KC[Keycloak Cookie]
            JWT[JWT Token]
            TOS[TOS Validation]
            EMAIL[Email Verification]
        end
        
        subgraph "Token Management"
            TM[Token Manager]
            RT[Refresh Token]
            AT[Access Token]
        end
        
        subgraph "Security Policies"
            SP[Security Policies]
            RLE[Rate Limiting]
            AUTH[Authorization]
        end
    end
    
    subgraph "External Dependencies"
        UA[UserAuth System]
        CONFIG[Server Config]
        KEYCLOAK[Keycloak IdP]
        GITLAB[GitLab Integration]
    end
    
    SACM --> KC
    SACM --> JWT
    SACM --> TOS
    SACM --> EMAIL
    SACM --> TM
    TM --> RT
    TM --> AT
    SACM --> SP
    
    SACM --> UA
    SACM --> CONFIG
    TM --> KEYCLOAK
    SACM --> GITLAB
    
    classDef middleware fill:#e1f5fe
    classDef auth fill:#f3e5f5
    classDef token fill:#e8f5e8
    classDef policy fill:#fff3e0
    classDef external fill:#fafafa
    
    class SACM middleware
    class KC,JWT,TOS,EMAIL auth
    class TM,RT,AT token
    class SP,RLE,AUTH policy
    class UA,CONFIG,KEYCLOAK,GITLAB external
```

## Core Components

### SetAuthCookieMiddleware

The `SetAuthCookieMiddleware` is the central component that orchestrates authentication and security policy enforcement for all incoming requests.

#### Key Responsibilities

1. **Authentication State Validation**
   - Validates Keycloak authentication cookies
   - Handles JWT token decoding and verification
   - Manages authentication state across requests

2. **Token Lifecycle Management**
   - Automatically refreshes expired tokens
   - Updates authentication cookies with new tokens
   - Handles token cleanup on authentication errors

3. **Security Policy Enforcement**
   - Enforces Terms of Service acceptance
   - Validates email verification status
   - Applies endpoint-specific security rules

4. **Error Handling and Recovery**
   - Graceful handling of authentication errors
   - Automatic logout on invalid tokens
   - Cookie cleanup on authentication failures

#### Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant Middleware as SetAuthCookieMiddleware
    participant UserAuth
    participant TokenManager
    participant Keycloak
    participant GitLab
    
    Client->>Middleware: Request with Cookie
    Middleware->>Middleware: Extract keycloak_auth cookie
    Middleware->>Middleware: Validate TOS acceptance
    Middleware->>UserAuth: Get user authentication
    
    alt Token needs refresh
        UserAuth->>TokenManager: Refresh tokens
        TokenManager->>Keycloak: Request new tokens
        Keycloak-->>TokenManager: New access/refresh tokens
        TokenManager-->>UserAuth: Updated tokens
        UserAuth->>UserAuth: Mark as refreshed
    end
    
    Middleware->>Middleware: Process request
    
    alt Authentication refreshed
        Middleware->>Client: Set updated cookie
        Middleware->>GitLab: Schedule repo sync
    end
    
    alt Email not verified
        Middleware-->>Client: 403 Forbidden
    end
    
    alt Authentication error
        Middleware->>TokenManager: Logout
        Middleware->>Client: Delete auth cookie
        Middleware-->>Client: 401 Unauthorized
    end
```

## Security Policies

### Terms of Service Enforcement

The middleware implements a three-state TOS acceptance model:

- **`null`**: User hasn't re-logged in since TOS changes (legacy state)
- **`false`**: User was shown TOS but hasn't accepted
- **`true`**: User has accepted current TOS

```mermaid
stateDiagram-v2
    [*] --> Legacy: accepted_tos = null
    [*] --> NotAccepted: accepted_tos = false
    [*] --> Accepted: accepted_tos = true
    
    Legacy --> Accepted: User re-authenticates
    NotAccepted --> Accepted: User accepts TOS
    Accepted --> [*]: Continue request
    NotAccepted --> TosError: Access protected endpoint
    
    state TosError {
        [*] --> Block: Return 403
    }
```

### Email Verification Requirements

Email verification is enforced for most API endpoints except:
- `/api/email/*` - Email management endpoints
- `/api/settings` - User settings
- `/api/logout` - Logout endpoint
- `/api/authenticate` - Authentication endpoint

### Endpoint Protection Strategy

The middleware applies different security policies based on request characteristics:

```mermaid
flowchart TD
    Request[Incoming Request] --> Method{Method = OPTIONS?}
    Method -->|Yes| Allow[Allow Request]
    Method -->|No| Path{Check Path}
    
    Path --> API{Starts with /api?}
    Path --> MCP{Starts with /mcp?}
    
    API -->|Yes| Excluded{Excluded endpoint?}
    API -->|No| Allow
    MCP -->|Yes| Protect[Apply Protection]
    MCP -->|No| Allow
    
    Excluded -->|Yes| Allow
    Excluded -->|No| Protect
    
    Protect --> Auth[Check Authentication]
    Auth --> TOS[Validate TOS]
    TOS --> Email[Check Email Verification]
    Email --> Process[Process Request]
    
    classDef decision fill:#fff2cc
    classDef action fill:#d5e8d4
    classDef protect fill:#f8cecc
    
    class Method,Path,API,MCP,Excluded decision
    class Allow,Process action
    class Protect,Auth,TOS,Email protect
```

## Integration Points

### Authentication System Integration

The security infrastructure integrates closely with the [authentication_system](authentication_system.md) module:

- **UserAuth Interface**: Leverages the abstract UserAuth system for authentication operations
- **Token Management**: Coordinates with token managers for refresh operations
- **Settings Integration**: Accesses user settings through the authentication system

### Server Infrastructure Integration

Integration with [web_infrastructure](web_infrastructure.md) components:

- **Rate Limiting**: Works alongside RateLimitMiddleware for comprehensive request control
- **Cookie Management**: Coordinates with server routing for secure cookie handling
- **Error Handling**: Integrates with FastAPI's error handling mechanisms

### Configuration Management

Relies on [security_configuration](security_configuration.md) for:

- **JWT Secret Management**: Secure token signing and validation
- **Security Analyzer Configuration**: Integration with security analysis tools
- **Confirmation Mode**: Enhanced security validation when enabled

## Security Features

### Token Security

1. **JWT Validation**
   - Cryptographic signature verification
   - Expiration time validation
   - Issuer and audience validation

2. **Secure Cookie Handling**
   - HttpOnly cookies for XSS protection
   - Secure flag for HTTPS enforcement
   - SameSite policies for CSRF protection
   - Domain-specific cookie scoping

3. **Token Refresh Strategy**
   - Automatic token refresh before expiration
   - Graceful handling of refresh failures
   - Background token cleanup

### Error Handling and Logging

```mermaid
graph LR
    subgraph "Error Types"
        ENE[EmailNotVerifiedError]
        NCE[NoCredentialsError]
        AE[AuthError]
        TNAE[TosNotAcceptedError]
    end
    
    subgraph "Response Actions"
        R403[403 Forbidden]
        R401[401 Unauthorized]
        LOGOUT[Automatic Logout]
        COOKIE[Delete Cookie]
    end
    
    subgraph "Logging"
        INFO[Info Level]
        WARN[Warning Level]
        DEBUG[Debug Level]
    end
    
    ENE --> R403
    TNAE --> R403
    NCE --> R401
    NCE --> INFO
    AE --> R401
    AE --> LOGOUT
    AE --> COOKIE
    AE --> WARN
    
    classDef error fill:#ffebee
    classDef response fill:#e3f2fd
    classDef log fill:#f1f8e9
    
    class ENE,NCE,AE,TNAE error
    class R403,R401,LOGOUT,COOKIE response
    class INFO,WARN,DEBUG log
```

## Configuration

### Environment Variables

The security infrastructure relies on several configuration parameters:

```yaml
# JWT Configuration
jwt_secret: "your-jwt-secret-key"

# Cookie Configuration
cookie_domain: "your-domain.com"
cookie_samesite: "lax"

# Security Features
confirmation_mode: false
security_analyzer: "default"
```

### Deployment Considerations

1. **HTTPS Requirements**
   - Secure cookies require HTTPS in production
   - Localhost development allows HTTP for testing

2. **Domain Configuration**
   - Proper cookie domain configuration for subdomain access
   - SameSite policy alignment with frontend architecture

3. **Token Expiration**
   - Balance between security and user experience
   - Automatic refresh reduces authentication friction

## Monitoring and Observability

### Security Metrics

The middleware provides comprehensive logging for security monitoring:

- **Authentication Events**: Login, logout, token refresh
- **Security Violations**: TOS violations, email verification failures
- **Error Patterns**: Authentication errors, token validation failures
- **Performance Metrics**: Middleware processing time, token refresh frequency

### Audit Trail

Security events are logged with structured data for audit purposes:

```json
{
  "event": "auth_error",
  "user_id": "user-123",
  "error_type": "InvalidTokenError",
  "endpoint": "/api/protected",
  "timestamp": "2024-01-01T12:00:00Z",
  "ip_address": "192.168.1.1"
}
```

## Best Practices

### Security Hardening

1. **Token Management**
   - Use strong JWT secrets with sufficient entropy
   - Implement proper token rotation policies
   - Monitor for token abuse patterns

2. **Cookie Security**
   - Always use Secure flag in production
   - Implement proper SameSite policies
   - Use HttpOnly to prevent XSS attacks

3. **Error Handling**
   - Avoid information disclosure in error messages
   - Implement consistent error responses
   - Log security events for monitoring

### Performance Optimization

1. **Caching Strategy**
   - Cache user authentication state appropriately
   - Minimize database queries for token validation
   - Use efficient JWT libraries

2. **Request Processing**
   - Optimize middleware order for performance
   - Implement early returns for excluded endpoints
   - Use async/await patterns consistently

## Related Documentation

- [authentication_system](authentication_system.md) - Core authentication interfaces and implementations
- [web_infrastructure](web_infrastructure.md) - Server middleware and request handling
- [security_configuration](security_configuration.md) - Security configuration management
- [enterprise_server](enterprise_server.md) - Enterprise server architecture overview