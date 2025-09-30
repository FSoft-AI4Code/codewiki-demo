# AWS Integration Module Documentation

## Overview

The AWS Integration module provides comprehensive Amazon Web Services integration capabilities for StarRocks, enabling seamless interaction with AWS services such as S3, Glue, and other AWS resources. This module is part of the java-extensions hadoop-ext package and serves as a bridge between StarRocks and AWS cloud services.

## Purpose and Core Functionality

The AWS Integration module is designed to:

- **Provide AWS Service Connectivity**: Establish secure connections to AWS services including S3, Glue, DynamoDB, and KMS
- **Manage Authentication and Authorization**: Handle various AWS authentication methods including IAM roles, access keys, and instance profiles
- **Enable Cloud Storage Access**: Facilitate reading and writing data to AWS S3 buckets with configurable access patterns
- **Support Data Lake Operations**: Integrate with AWS Glue Data Catalog for metadata management
- **Handle Credential Management**: Implement secure credential rotation and management strategies

## Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "StarRocks System"
        SR[StarRocks Engine]
        IC[Iceberg Connector]
    end
    
    subgraph "AWS Integration Layer"
        IACF[IcebergAwsClientFactory]
        CC[CloudConfigurationConstants]
        IAF[IcebergAwsClientFactory]
    end
    
    subgraph "AWS Services"
        S3[S3 Service]
        GLUE[Glue Service]
        STS[STS Service]
        KMS[KMS Service]
        DDB[DynamoDB Service]
    end
    
    subgraph "Authentication Methods"
        AK[Access Keys]
        IAR[IAM Role]
        IP[Instance Profile]
        WIT[Web Identity Token]
        DCP[Default Credentials]
    end
    
    SR --> IC
    IC --> IACF
    IACF --> S3
    IACF --> GLUE
    IACF --> STS
    IACF --> KMS
    IACF --> DDB
    
    IACF -.-> AK
    IACF -.-> IAR
    IACF -.-> IP
    IACF -.-> WIT
    IACF -.-> DCP
```

### Component Architecture

```mermaid
graph LR
    subgraph "IcebergAwsClientFactory"
        INIT[initialize\nmethod]
        S3[s3\nmethod]
        S3A[s3Async\nmethod]
        GLUE[glue\nmethod]
        KMS[kms\nmethod]
        DDB[dynamo\nmethod]
        GAR[getAssumeRole\nCredentialsProvider]
        GBCP[getBaseAWSCredentials\nProvider]
        ESI[ensureSchemeInEndpoint]
        TRR[tryToResolveRegion]
    end
    
    subgraph "Configuration"
        PROPS[Properties Map]
        AWS_PROPS[AWS Properties]
        S3_PROPS[S3 Properties]
        GLUE_PROPS[Glue Properties]
    end
    
    subgraph "AWS SDK Clients"
        S3_CLIENT[S3Client]
        S3A_CLIENT[S3AsyncClient]
        GLUE_CLIENT[GlueClient]
        KMS_CLIENT[KmsClient]
        DDB_CLIENT[DynamoDbClient]
        STS_CLIENT[StsClient]
    end
    
    PROPS --> INIT
    INIT --> AWS_PROPS
    INIT --> S3_PROPS
    INIT --> GLUE_PROPS
    
    AWS_PROPS --> S3
    AWS_PROPS --> S3A
    AWS_PROPS --> GLUE
    
    S3 --> S3_CLIENT
    S3A --> S3A_CLIENT
    GLUE --> GLUE_CLIENT
    KMS --> KMS_CLIENT
    DDB --> DDB_CLIENT
    
    GAR --> STS_CLIENT
    GBCP --> GAR
```

## Core Components

### IcebergAwsClientFactory

The `IcebergAwsClientFactory` class is the central component that implements the `AwsClientFactory` interface from Apache Iceberg. It provides factory methods for creating AWS service clients with proper authentication and configuration.

#### Key Features:

- **Multi-Service Support**: Creates clients for S3, Glue, KMS, and DynamoDB
- **Flexible Authentication**: Supports multiple authentication methods
- **Role-Based Access**: Implements IAM role assumption with STS
- **Endpoint Configuration**: Handles custom endpoints and regions
- **Async Operations**: Provides both synchronous and asynchronous S3 clients

#### Configuration Properties:

The factory supports extensive configuration through properties:

**S3 Configuration:**
- `aws.s3.use.aws.sdk.default.behavior`: Use AWS SDK default credential chain
- `aws.s3.use.instance.profile`: Use EC2 instance profile credentials
- `aws.s3.use.web.identity.token.file`: Use web identity token file
- `aws.s3.access.key`: S3 access key
- `aws.s3.secret.key`: S3 secret key
- `aws.s3.session.token`: S3 session token
- `aws.s3.iam.role.arn`: IAM role ARN for S3 access
- `aws.s3.region`: S3 region
- `aws.s3.endpoint`: Custom S3 endpoint
- `aws.s3.enable.path.style.access`: Enable path-style S3 access

**Glue Configuration:**
- `aws.glue.use.aws.sdk.default.behavior`: Use AWS SDK default credential chain
- `aws.glue.use.instance.profile`: Use EC2 instance profile credentials
- `aws.glue.use.web.identity.token.file`: Use web identity token file
- `aws.glue.access.key`: Glue access key
- `aws.glue.secret.key`: Glue secret key
- `aws.glue.iam.role.arn`: IAM role ARN for Glue access
- `aws.glue.region`: Glue region
- `aws.glue.endpoint`: Custom Glue endpoint

## Data Flow

### Authentication Flow

```mermaid
sequenceDiagram
    participant Client as StarRocks Client
    participant Factory as IcebergAwsClientFactory
    participant Config as Configuration
    participant Auth as AWS Credentials Provider
    participant STS as AWS STS
    participant Service as AWS Service
    
    Client->>Factory: Request AWS Service Client
    Factory->>Config: Load Properties
    Config-->>Factory: Return Configuration
    
    alt Use IAM Role
        Factory->>Auth: Get Base Credentials
        Auth-->>Factory: Return Base Provider
        Factory->>STS: Assume Role Request
        STS-->>Factory: Return Temporary Credentials
        Factory->>Auth: Create Role-based Provider
    else Use Access Keys
        Factory->>Auth: Create Static Provider
    else Use Instance Profile
        Factory->>Auth: Create Instance Profile Provider
    else Use Default Chain
        Factory->>Auth: Create Default Provider
    end
    
    Auth-->>Factory: Return Credentials Provider
    Factory->>Service: Create Service Client
    Service-->>Factory: Return Client
    Factory-->>Client: Return Configured Client
```

### Service Client Creation Flow

```mermaid
flowchart TD
    Start([Start]) --> LoadConfig[Load Configuration Properties]
    LoadConfig --> DetermineAuth{Determine Authentication Method}
    
    DetermineAuth -->|IAM Role| AssumeRole[Assume IAM Role via STS]
    DetermineAuth -->|Access Keys| UseKeys[Use Static Credentials]
    DetermineAuth -->|Instance Profile| UseProfile[Use Instance Profile]
    DetermineAuth -->|Web Identity| UseWebIdentity[Use Web Identity Token]
    DetermineAuth -->|Default| UseDefault[Use Default Credential Chain]
    
    AssumeRole --> CreateRoleProvider[Create Role-based Provider]
    UseKeys --> CreateStaticProvider[Create Static Provider]
    UseProfile --> CreateProfileProvider[Create Profile Provider]
    UseWebIdentity --> CreateWebIdentityProvider[Create Web Identity Provider]
    UseDefault --> CreateDefaultProvider[Create Default Provider]
    
    CreateRoleProvider --> BuildClient[Build Service Client]
    CreateStaticProvider --> BuildClient
    CreateProfileProvider --> BuildClient
    CreateWebIdentityProvider --> BuildClient
    CreateDefaultProvider --> BuildClient
    
    BuildClient --> ConfigureEndpoint[Configure Endpoint & Region]
    ConfigureEndpoint --> ApplyS3Config{Is S3 Client?}
    
    ApplyS3Config -->|Yes| ConfigureS3[Configure S3-specific Settings]
    ApplyS3Config -->|No| SkipS3[Skip S3 Configuration]
    
    ConfigureS3 --> ReturnClient[Return Configured Client]
    SkipS3 --> ReturnClient
    ReturnClient --> End([End])
```

## Dependencies

The AWS Integration module has dependencies on several other modules and external libraries:

### Internal Dependencies

- **[Cloud Configuration Constants](cloud_credential_management.md)**: Provides configuration constants for AWS services
- **[Iceberg Integration](iceberg_integration.md)**: Integrates with Apache Iceberg table format
- **[Connector Framework](connector_framework.md)**: Provides base connector functionality

### External Dependencies

- **AWS SDK for Java v2**: Core AWS service clients
  - `software.amazon.awssdk.services.s3`: S3 service client
  - `software.amazon.awssdk.services.glue`: Glue service client
  - `software.amazon.awssdk.services.sts`: STS service client for role assumption
  - `software.amazon.awssdk.services.kms`: KMS service client
  - `software.amazon.awssdk.services.dynamodb`: DynamoDB service client
- **Apache Iceberg**: Table format and AWS client factory interfaces
- **SLF4J**: Logging framework

## Integration Points

### With Iceberg Connector

The AWS Integration module works closely with the Iceberg connector to provide cloud storage access:

```mermaid
graph LR
    subgraph "Iceberg Connector"
        IC[IcebergCatalog]
        IMS[IcebergMetadataScanner]
        IFS[IcebergFileIO]
    end
    
    subgraph "AWS Integration"
        IACF[IcebergAwsClientFactory]
        S3C[S3Client]
        GC[GlueClient]
    end
    
    subgraph "AWS Services"
        S3[S3 Storage]
        GLUE[Glue Catalog]
    end
    
    IC --> IACF
    IMS --> IACF
    IFS --> IACF
    
    IACF --> S3C
    IACF --> GC
    
    S3C --> S3
    GC --> GLUE
```

### With Cloud Credential Management

The module integrates with the cloud credential management system for secure credential handling:

```mermaid
graph TD
    subgraph "Cloud Credential Management"
        CCC[CloudConfigurationConstants]
        CCF[CloudConfigurationFactory]
        CU[CredentialUtil]
    end
    
    subgraph "AWS Integration"
        IACF[IcebergAwsClientFactory]
        PROPS[Properties Configuration]
    end
    
    CCC --> PROPS
    CCF --> IACF
    CU --> IACF
    
    PROPS --> IACF
```

## Configuration Examples

### Basic S3 Access with Access Keys

```properties
aws.s3.access.key=AKIAIOSFODNN7EXAMPLE
aws.s3.secret.key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
aws.s3.region=us-west-2
```

### IAM Role Assumption for S3

```properties
aws.s3.iam.role.arn=arn:aws:iam::123456789012:role/S3AccessRole
aws.s3.external-id=unique-external-id
aws.s3.sts.region=us-west-2
aws.s3.region=us-west-2
```

### Glue Catalog Access with Instance Profile

```properties
aws.glue.use.instance.profile=true
aws.glue.region=us-west-2
```

### Custom Endpoint Configuration

```properties
aws.s3.endpoint=https://s3-compatible-storage.example.com
aws.s3.enable.path.style.access=true
aws.glue.endpoint=https://glue.example.com
```

## Security Considerations

### Credential Management

- **Secure Storage**: Credentials should be stored securely using StarRocks' credential management system
- **Rotation Support**: The module supports credential rotation through role assumption
- **Minimal Privileges**: Follow the principle of least privilege when configuring IAM roles and policies

### Network Security

- **HTTPS Enforcement**: All AWS service communications use HTTPS
- **Endpoint Validation**: Custom endpoints are validated to ensure proper scheme inclusion
- **Region Validation**: Regions are resolved through AWS SDK's default provider chain

### Authentication Best Practices

1. **Use IAM Roles**: Prefer IAM role assumption over static access keys
2. **External IDs**: Use external IDs when assuming roles for additional security
3. **Instance Profiles**: Leverage EC2 instance profiles when running on AWS infrastructure
4. **Web Identity Tokens**: Use web identity tokens for Kubernetes or other containerized environments

## Error Handling

The module implements comprehensive error handling for various scenarios:

- **Authentication Failures**: Graceful fallback to default credential providers
- **Network Issues**: Retry mechanisms for transient network failures
- **Configuration Errors**: Validation of configuration properties with informative error messages
- **Service Unavailability**: Proper error propagation for AWS service unavailability

## Performance Considerations

### Client Caching

- AWS service clients are created once and reused to minimize connection overhead
- Credential providers are cached to avoid repeated authentication requests

### Async Operations

- S3 async client support for non-blocking operations
- Configurable thread pools for async operations

### Regional Optimization

- Automatic region resolution for optimal latency
- Support for custom endpoints to reduce network hops

## Monitoring and Observability

### Logging

- Comprehensive logging using SLF4J framework
- Log levels configurable for different components
- Security-sensitive information is properly redacted

### Metrics

- Integration with StarRocks metrics system for monitoring AWS operations
- Performance metrics for client operations and authentication

## Future Enhancements

### Planned Features

- **Additional AWS Services**: Support for more AWS services like Redshift, Athena, and Kinesis
- **Advanced Authentication**: Support for AWS SSO and temporary credentials
- **Cross-Region Support**: Enhanced multi-region deployment support
- **Cost Optimization**: Intelligent request routing for cost optimization

### Integration Improvements

- **Native AWS SDK Integration**: Deeper integration with AWS SDK best practices
- **Custom Retry Policies**: Configurable retry policies for different AWS services
- **Connection Pooling**: Advanced connection pooling for high-throughput scenarios

## References

- [Cloud Credential Management](cloud_credential_management.md) - For credential configuration details
- [Iceberg Integration](iceberg_integration.md) - For Iceberg table format integration
- [Connector Framework](connector_framework.md) - For general connector architecture
- [AWS SDK for Java Documentation](https://docs.aws.amazon.com/sdk-for-java/)
- [Apache Iceberg AWS Integration](https://iceberg.apache.org/docs/latest/aws/)