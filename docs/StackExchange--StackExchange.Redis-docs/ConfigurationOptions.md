# ConfigurationOptions Module Documentation

## Overview

The ConfigurationOptions module is the central configuration system for StackExchange.Redis, providing a comprehensive and flexible way to configure Redis connections. It serves as the primary entry point for setting up connection parameters, security settings, timeouts, and behavior policies that govern how the Redis client operates.

## Purpose and Core Functionality

ConfigurationOptions acts as a configuration container and parser that:
- Defines connection parameters for Redis servers (endpoints, timeouts, authentication)
- Configures security settings (SSL/TLS, certificate validation, authentication)
- Sets behavior policies (retry logic, heartbeat intervals, command mapping)
- Provides both programmatic and string-based configuration capabilities
- Supports advanced features like proxy configuration, tunneling, and protocol selection

## Architecture

### Component Structure

```mermaid
graph TB
    subgraph "ConfigurationOptions Module"
        CO[ConfigurationOptions]
        
        subgraph "Core Properties"
            EP[EndPoints<br/>EndPointCollection]
            TO[Timeout Settings<br/>- SyncTimeout<br/>- AsyncTimeout<br/>- ConnectTimeout]
            AUTH[Authentication<br/>- User<br/>- Password<br/>- CertificateSelection]
            SSL[SSL/TLS Settings<br/>- Ssl<br/>- SslHost<br/>- SslProtocols]
            POL[Policies<br/>- ReconnectRetryPolicy<br/>- BacklogPolicy]
            CMD[Command Configuration<br/>- CommandMap<br/>- DefaultDatabase]
        end
        
        subgraph "Parsing System"
            OP[OptionKeys<br/>Static Parser]
            DP[DoParse Method]
            CS[Configuration String]
        end
        
        subgraph "Default Providers"
            DOP[DefaultOptionsProvider]
            AOP[AzureOptionsProvider]
        end
    end
    
    CS --> DP
    DP --> OP
    OP --> CO
    DOP --> CO
    AOP --> CO
```

### Key Dependencies

```mermaid
graph LR
    CO[ConfigurationOptions]
    
    subgraph "External Dependencies"
        CM[ConnectionMultiplexer]
        SM[SocketManager]
        TUN[Tunnel]
        RP[RedisProtocol]
        RC[RedisChannel]
    end
    
    subgraph "System Dependencies"
        EP[EndPoint]
        SSL[SSL Types]
        LOG[ILoggerFactory]
        CERT[X509Certificate2]
    end
    
    CO --> CM
    CO --> SM
    CO --> TUN
    CO --> RP
    CO --> RC
    CO --> EP
    CO --> SSL
    CO --> LOG
    CO --> CERT
```

## Configuration Flow

### Configuration Parsing Process

```mermaid
sequenceDiagram
    participant User
    participant Parse
    participant DoParse
    participant OptionKeys
    participant ConfigurationOptions
    
    User->>Parse: Configuration string
    Parse->>DoParse: Create new instance
    DoParse->>DoParse: Split by commas
    
    loop For each option
        DoParse->>OptionKeys: TryNormalize(key)
        OptionKeys->>DoParse: Normalized key
        DoParse->>ConfigurationOptions: Set property
    end
    
    DoParse->>ConfigurationOptions: Return configured instance
    ConfigurationOptions->>User: ConfigurationOptions object
```

### Property Resolution Hierarchy

```mermaid
graph TD
    subgraph "Property Resolution Order"
        A[Explicitly Set Value]
        B[DefaultOptionsProvider]
        C[Static Default]
        
        A -->|If null| B
        B -->|If null| C
        
        D[Final Value]
        
        A --> D
        B --> D
        C --> D
    end
```

## Core Components

### ConfigurationOptions Class

The main configuration class that encapsulates all Redis connection settings:

#### Connection Settings
- **EndPoints**: Collection of Redis server endpoints
- **DefaultDatabase**: Default database index (0-15)
- **ClientName**: Client identification name
- **ServiceName**: Sentinel service name for high availability

#### Timeout Configuration
- **SyncTimeout**: Timeout for synchronous operations (default: 5 seconds)
- **AsyncTimeout**: Timeout for asynchronous operations
- **ConnectTimeout**: Connection establishment timeout
- **KeepAlive**: Keep-alive ping interval

#### Security Settings
- **Ssl**: Enable SSL/TLS encryption
- **SslHost**: SSL certificate validation host
- **SslProtocols**: Allowed SSL/TLS protocols
- **User/Password**: Authentication credentials
- **CertificateSelection/Validation**: Certificate handling callbacks

#### Behavior Policies
- **ReconnectRetryPolicy**: Strategy for connection retries
- **BacklogPolicy**: Command queuing behavior during reconnection
- **CommandMap**: Redis command availability mapping
- **AbortOnConnectFail**: Fail-fast behavior on connection failure

### Configuration String Parsing

The module supports parsing configuration strings with the format:
```
server1:6379,server2:6379,password=pass,ssl=true,abortConnect=false
```

#### Supported Options
- Connection: `server`, `port`, `defaultDatabase`
- Authentication: `password`, `user`, `ssl`, `sslProtocols`
- Timeouts: `syncTimeout`, `asyncTimeout`, `connectTimeout`, `keepAlive`
- Behavior: `abortConnect`, `allowAdmin`, `resolveDns`, `proxy`
- Advanced: `tiebreaker`, `configChannel`, `channelPrefix`

### Default Options Provider System

```mermaid
graph LR
    subgraph "Default Options Hierarchy"
        CO[ConfigurationOptions]
        DOP[DefaultOptionsProvider]
        AOP[AzureOptionsProvider]
        
        CO -->|Defaults| DOP
        CO -->|Azure| AOP
        
        DOP -->|Base| CO
        AOP -->|Specialized| DOP
    end
```

## Integration with Other Modules

### ConnectionMultiplexer Integration

ConfigurationOptions is consumed by [ConnectionMultiplexer](ConnectionManagement.md) to establish and manage Redis connections:

```mermaid
graph LR
    CO[ConfigurationOptions]
    CM[ConnectionMultiplexer]
    PC[PhysicalConnection]
    
    CO -->|Configure| CM
    CM -->|Create| PC
    CO -->|Settings| PC
```

### Security Module Integration

Security settings flow to connection establishment:

```mermaid
graph TD
    CO[ConfigurationOptions]
    SSL[SSL Settings]
    CERT[Certificate Callbacks]
    AUTH[Authentication]
    
    CO --> SSL
    CO --> CERT
    CO --> AUTH
    
    SSL -->|Configure| PC[PhysicalConnection]
    CERT -->|Callbacks| PC
    AUTH -->|Credentials| PC
```

## Advanced Features

### Certificate Management

The module provides comprehensive certificate handling:

```csharp
// Trust specific issuer
config.TrustIssuer("path/to/ca.crt");

// Set client certificate (PFX)
config.SetUserPfxCertificate("client.pfx", "password");

// Set client certificate (PEM) - .NET 5+
config.SetUserPemCertificate("client.crt", "client.key");
```

### Protocol Selection

Supports both RESP2 and RESP3 protocols:

```csharp
// Explicit protocol selection
config.Protocol = RedisProtocol.Resp3;

// Automatic detection (currently RESP2 by default)
// RESP3 requires explicit opt-in due to API compatibility
```

### Tunnel Support

Supports HTTP proxy tunneling for restricted environments:

```csharp
// HTTP proxy configuration
config.Tunnel = Tunnel.HttpProxy(new DnsEndPoint("proxy.example.com", 8080));
```

## Configuration Best Practices

### Performance Tuning
```csharp
var config = new ConfigurationOptions
{
    // Connection pooling
    ConnectTimeout = 5000,
    SyncTimeout = 5000,
    AsyncTimeout = 5000,
    
    // Keep-alive for connection health
    KeepAlive = 60,
    
    // Retry policy for resilience
    ReconnectRetryPolicy = new LinearRetry(500),
    
    // Backlog for command queuing
    BacklogPolicy = BacklogPolicy.Default
};
```

### Security Configuration
```csharp
var config = new ConfigurationOptions
{
    // SSL/TLS encryption
    Ssl = true,
    SslProtocols = SslProtocols.Tls12 | SslProtocols.Tls13,
    
    // Certificate validation
    CertificateValidation += (sender, certificate, chain, sslPolicyErrors) =>
    {
        // Custom validation logic
        return true;
    }
};
```

### High Availability
```csharp
var config = new ConfigurationOptions
{
    // Sentinel configuration
    ServiceName = "mymaster",
    
    // Multiple endpoints
    EndPoints = { "sentinel1:26379", "sentinel2:26379", "sentinel3:26379" },
    
    // Tie-breaker for split-brain scenarios
    TieBreaker = "__Booksleeve_TieBreak"
};
```

## Error Handling and Validation

### Configuration Validation

The module performs extensive validation during parsing:
- **Type validation**: Ensures correct data types for each option
- **Range validation**: Validates numeric ranges (timeouts, retry counts)
- **Enum validation**: Ensures valid enumeration values
- **Format validation**: Validates endpoint formats and connection strings

### Error Recovery

```mermaid
graph TD
    subgraph "Error Handling Flow"
        A[Invalid Configuration]
        B[Parse Exception]
        C[Default Fallback]
        D[User Notification]
        
        A --> B
        B --> C
        B --> D
        
        C --> E[Continue with Defaults]
        D --> F[User Corrects Configuration]
    end
```

## Thread Safety and Immutability

ConfigurationOptions is designed to be:
- **Thread-safe for reading**: Properties can be safely read after creation
- **Immutable after use**: Once used by ConnectionMultiplexer, changes have no effect
- **Cloneable**: Supports deep cloning for configuration variations

## Migration and Compatibility

### Version Compatibility
- Maintains backward compatibility with older Redis versions
- Supports protocol negotiation for mixed-version clusters
- Provides deprecation warnings for obsolete options

### Migration Patterns
```csharp
// From connection string
var config = ConfigurationOptions.Parse("localhost:6379,password=pass");

// To programmatic configuration
var config = new ConfigurationOptions
{
    EndPoints = { "localhost:6379" },
    Password = "pass"
};
```

## References

- [ConnectionManagement](ConnectionManagement.md) - Uses ConfigurationOptions for connection establishment
- [CoreInterfaces](CoreInterfaces.md) - IReconnectRetryPolicy interface for retry policies
- [ValueTypes](ValueTypes.md) - RedisChannel and related configuration types