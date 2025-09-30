# Credential Cloud Module Documentation

## Overview

The credential_cloud module is a critical component of the StarRocks system that manages cloud storage credentials and configurations. This module provides a unified interface for handling authentication across multiple cloud providers including AWS, Azure, GCP, Aliyun, and Tencent Cloud. It ensures secure credential management while supporting various storage services like S3, ADLS, GCS, and others.

## Purpose and Core Functionality

The primary purpose of the credential_cloud module is to:

1. **Centralize Cloud Credential Management**: Provide a single point of access for all cloud storage credentials across the system
2. **Support Multi-Cloud Environments**: Handle credentials for major cloud providers (AWS, Azure, GCP, Aliyun, Tencent)
3. **Ensure Security**: Implement credential masking and secure handling practices
4. **Enable Cloud Storage Integration**: Facilitate seamless integration with various cloud storage services
5. **Support Vended Credentials**: Handle temporary and session-based credentials from cloud services

## Architecture Overview

```mermaid
graph TB
    subgraph "Credential Cloud Module"
        CCF[CloudConfigurationFactory]
        CU[CredentialUtil]
        
        subgraph "Cloud Providers"
            AWS[AWS Provider]
            AZURE[Azure Provider]
            GCP[GCP Provider]
            ALIYUN[Aliyun Provider]
            TENCENT[Tencent Provider]
            HDFS[HDFS Provider]
        end
        
        subgraph "Credential Types"
            VC[Vended Credentials]
            SC[Static Credentials]
            TC[Temporary Credentials]
        end
        
        subgraph "Storage Services"
            S3[S3]
            ADLS[ADLS]
            GCS[GCS]
            OSS[OSS]
            COS[COS]
        end
    end
    
    CCF --> AWS
    CCF --> AZURE
    CCF --> GCP
    CCF --> ALIYUN
    CCF --> TENCENT
    CCF --> HDFS
    
    AWS --> VC
    AWS --> SC
    AZURE --> VC
    AZURE --> SC
    GCP --> VC
    GCP --> SC
    
    VC --> S3
    SC --> S3
    VC --> ADLS
    SC --> ADLS
    VC --> GCS
    SC --> GCS
    
    CU --> CCF
```

## Core Components

### 1. CloudConfigurationFactory

The `CloudConfigurationFactory` is the main factory class responsible for creating cloud configurations. It implements a chain of responsibility pattern to handle different cloud providers.

**Key Responsibilities:**
- Build cloud configurations for storage services
- Handle vended credentials from various sources
- Support both regular and strict mode configurations
- Integrate with Hive and Iceberg catalogs

**Key Methods:**
- `buildCloudConfigurationForStorage()`: Creates cloud configuration for storage services
- `buildCloudConfigurationForVendedCredentials()`: Handles vended/temporary credentials
- `buildGlueCloudCredential()`: Specifically handles AWS Glue credentials

### 2. CredentialUtil

The `CredentialUtil` class provides utility functions for credential management and security.

**Key Responsibilities:**
- Mask sensitive credential information in logs and displays
- Parse Azure storage paths with proper URI validation
- Handle credential validation and formatting
- Support multiple cloud storage URI formats

**Key Methods:**
- `maskCredential()`: Masks sensitive credential data across all supported cloud providers
- `parseAzureStoragePath()`: Parses Azure storage URIs with comprehensive validation

### 3. Cloud Configuration Provider Chain

The module implements a chain of responsibility pattern where multiple providers are tried in sequence until a suitable configuration is found.

**Provider Order:**
1. AWS Cloud Configuration Provider
2. Azure Cloud Configuration Provider  
3. GCP Cloud Configuration Provider
4. Aliyun Cloud Configuration Provider
5. Tencent Cloud Configuration Provider
6. HDFS Cloud Configuration Provider
7. Default Cloud Configuration (fallback)

**Strict Mode:**
In strict mode, an additional `StrictHDFSCloudConfigurationProvider` is included in the chain for enhanced security requirements.

## Vended Credentials Support

The module has specialized support for handling vended (temporary) credentials from various sources:

### AWS Vended Credentials
- **Source**: Iceberg S3FileIO properties, AWS client properties
- **Handling**: Extracts session tokens, access keys, and regions
- **Integration**: Works with Iceberg REST catalog and AWS Glue

### Azure Vended Credentials  
- **Source**: ADLS SAS tokens, Blob SAS tokens
- **Handling**: Parses endpoint-specific credentials with URI validation
- **Integration**: Supports both ADLS Gen2 and Blob storage

### GCP Vended Credentials
- **Source**: GCS access tokens with expiration
- **Handling**: Manages token lifecycle and expiration
- **Integration**: Works with GCS and BigQuery connectors

```mermaid
sequenceDiagram
    participant CloudService
    participant VendedCredentialHandler
    participant CloudConfigurationFactory
    participant CredentialUtil
    participant StorageSystem
    
    CloudService->>VendedCredentialHandler: Provide temporary credentials
    VendedCredentialHandler->>CloudConfigurationFactory: Extract credential properties
    CloudConfigurationFactory->>CredentialUtil: Request credential masking
    CredentialUtil->>CloudConfigurationFactory: Return masked credentials
    CloudConfigurationFactory->>StorageSystem: Provide secure configuration
    StorageSystem->>CloudService: Access with vended credentials
```

## Data Flow

```mermaid
sequenceDiagram
    participant Client
    participant CloudConfigurationFactory
    participant CloudConfigurationProvider
    participant CredentialUtil
    participant CloudStorage
    
    Client->>CloudConfigurationFactory: Request cloud configuration
    CloudConfigurationFactory->>CloudConfigurationProvider: Try provider chain
    CloudConfigurationProvider->>CloudConfigurationFactory: Return configuration
    CloudConfigurationFactory->>CredentialUtil: Mask credentials if needed
    CredentialUtil->>CloudConfigurationFactory: Return masked config
    CloudConfigurationFactory->>Client: Return secure configuration
    Client->>CloudStorage: Use configuration for access
```

## Integration with Other Modules

The credential_cloud module integrates with several other StarRocks modules:

### 1. Connector Framework
- Provides credentials for external table connectors
- Supports Hive, Iceberg, Delta Lake, and other table formats
- Integrates with connector framework for unified data access
- Handles authentication for JDBC connections to cloud databases

### 2. Storage Engine
- Supplies authentication for cloud storage access
- Works with storage engine for data persistence and retrieval
- Enables cloud-native storage integration for lakehouse architectures

### 3. Frontend Server
- Handles credential validation and management
- Integrates with frontend server for metadata operations
- Supports credential-based access control and authorization

### 4. Java Extensions
- Provides credential management for external Java-based connectors
- Supports Hadoop ecosystem integration with proper authentication
- Enables secure access to cloud-based data lakes and warehouses

## Security Considerations

### Credential Masking
The module implements comprehensive credential masking to prevent sensitive information from appearing in logs:
- AWS access keys and secret keys
- Azure shared keys and SAS tokens
- GCP service account private keys
- Aliyun OSS credentials
- JDBC passwords

### Best Practices
1. **Never log raw credentials**: All credentials are masked before logging
2. **Support temporary credentials**: Handles session tokens and temporary access
3. **Provider isolation**: Each cloud provider has its own configuration handler
4. **Validation**: URI parsing and validation for Azure storage paths

## Supported Cloud Providers

### AWS (Amazon Web Services)
- **Services**: S3, Glue, EMR
- **Authentication**: Access keys, secret keys, session tokens
- **Integration**: Hive, Iceberg, native S3 access

### Azure (Microsoft Azure)
- **Services**: Blob Storage, ADLS Gen1/Gen2
- **Authentication**: Shared keys, SAS tokens, OAuth2
- **URI Formats**: 
  - ADLS Gen2: `abfs[s]://<container>@<storage_account>.dfs.core.windows.net/`
  - Blob: `wasb[s]://<container>@<storage_account>.blob.core.windows.net/`

### GCP (Google Cloud Platform)
- **Services**: Cloud Storage (GCS)
- **Authentication**: Service account keys, access tokens
- **Integration**: BigQuery, Cloud Storage

### Aliyun (Alibaba Cloud)
- **Services**: Object Storage Service (OSS)
- **Authentication**: Access keys
- **Integration**: MaxCompute, OSS

### Tencent Cloud
- **Services**: Cloud Object Storage (COS)
- **Authentication**: Secret keys
- **Integration**: COS, EMR

## Configuration Examples

### AWS S3 Configuration
```properties
# Basic S3 access
aws.s3.access_key=AKIAIOSFODNN7EXAMPLE
aws.s3.secret_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
aws.s3.region=us-west-2
aws.s3.endpoint=s3.amazonaws.com
aws.s3.enable_path_style_access=false

# With session token (vended credentials)
aws.s3.access_key=ASIA...
aws.s3.secret_key=******
aws.s3.session_token=******
aws.s3.region=us-west-2
```

### Azure Blob Storage Configuration
```properties
# Shared key authentication
azure.blob.storage_account=mystorageaccount
azure.blob.container=mycontainer
azure.blob.shared_key=******

# SAS token authentication
azure.blob.storage_account=mystorageaccount
azure.blob.container=mycontainer
azure.blob.sas_token=******

# ADLS Gen2
azure.adls2.endpoint=mystorageaccount.dfs.core.windows.net
azure.adls2.shared_key=******
azure.adls2.oauth2_client_secret=******
```

### GCP Cloud Storage Configuration
```properties
# Service account authentication
gcp.gcs.service_account_private_key=******
gcp.gcs.project_id=my-project

# Access token (vended credentials)
gcp.gcs.access_token=******
gcp.gcs.access_token_expires_at=1234567890
```

### Aliyun OSS Configuration
```properties
aliyun.oss.access_key=LTAI5tExample
aliyun.oss.secret_key=******
aliyun.oss.endpoint=oss-cn-hangzhou.aliyuncs.com
aliyun.oss.region=cn-hangzhou
```

### Iceberg REST Catalog Configuration
```properties
# OAuth2 authentication
iceberg.rest.oauth2.credential=******
iceberg.rest.oauth2.token=******

# AWS REST authentication
iceberg.rest.access_key_id=ASIA...
iceberg.rest.secret_access_key=******
```

### JDBC Catalog Configuration
```properties
# Connection authentication (credentials are removed, not masked)
jdbc.uri=jdbc:postgresql://host:port/database
jdbc.driver=org.postgresql.Driver
jdbc.user=myuser
# Password is removed for security
```

## Testing and Validation

### Credential Validation Patterns
The module implements several validation patterns to ensure credential integrity:

1. **URI Validation**: Azure storage paths are validated using Java URI parsing
2. **Credential Format Validation**: Each provider validates its specific credential format
3. **Provider Chain Validation**: Ensures at least one provider can handle the given properties
4. **Masking Validation**: Verifies that sensitive data is properly masked

### Test Scenarios
Common test scenarios for the credential cloud module:

```java
// Test AWS credential building
Map<String, String> awsProps = new HashMap<>();
awsProps.put("aws.s3.access_key", "test-key");
awsProps.put("aws.s3.secret_key", "test-secret");
CloudConfiguration config = CloudConfigurationFactory.buildCloudConfigurationForStorage(awsProps);
assert config.getCloudType() == CloudType.AWS;

// Test credential masking
Map<String, String> sensitiveProps = new HashMap<>();
sensitiveProps.put("aws.s3.access_key", "AKIAIOSFODNN7EXAMPLE");
CredentialUtil.maskCredential(sensitiveProps);
assert sensitiveProps.get("aws.s3.access_key").contains("******");

// Test Azure path parsing
AzureStoragePath path = CredentialUtil.parseAzureStoragePath("abfs://container@account.dfs.core.windows.net/path");
assert path.getStorageAccount().equals("account");
assert path.getContainer().equals("container");
```

## Error Handling

The module implements comprehensive error handling:
- **URI Parsing Errors**: Handles malformed Azure storage URIs
- **Credential Validation**: Validates credential formats
- **Provider Chain Failures**: Falls back to default configurations
- **Logging**: Provides detailed error messages while maintaining security

## Performance Considerations

1. **Caching**: Cloud configurations are built on-demand and can be cached
2. **Lazy Loading**: Providers are tried in sequence until a match is found
3. **Minimal Overhead**: Credential masking is applied only when necessary
4. **Thread Safety**: Factory methods are thread-safe for concurrent access

## Best Practices

### 1. Security Best Practices
- **Never hardcode credentials**: Always use configuration files or environment variables
- **Use temporary credentials**: Prefer vended credentials when available for enhanced security
- **Implement credential rotation**: Regularly rotate access keys and tokens
- **Enable audit logging**: Track credential usage and access patterns
- **Use least privilege**: Grant minimal necessary permissions to credentials

### 2. Configuration Best Practices
- **Centralize credential management**: Use the factory pattern for consistent credential handling
- **Validate configurations**: Always test credential configurations before production use
- **Use consistent naming**: Follow established property naming conventions
- **Document credential requirements**: Maintain clear documentation of required credentials
- **Implement fallback mechanisms**: Have backup authentication methods available

### 3. Operational Best Practices
- **Monitor credential expiration**: Set up alerts for credential expiration
- **Test connectivity regularly**: Verify cloud storage access periodically
- **Implement error handling**: Handle credential failures gracefully
- **Use connection pooling**: Optimize cloud storage connection management
- **Cache configurations**: Cache cloud configurations to reduce overhead

### 4. Multi-Cloud Best Practices
- **Standardize authentication**: Use consistent authentication patterns across clouds
- **Implement cloud-agnostic code**: Write code that works across different cloud providers
- **Handle provider-specific features**: Account for unique features of each cloud provider
- **Test across environments**: Validate functionality in all supported cloud environments
- **Maintain provider independence**: Avoid vendor lock-in through abstraction layers

## Troubleshooting Guide

### Common Issues

1. **Credential Validation Failures**
   - Check credential format and completeness
   - Verify provider-specific requirements
   - Ensure proper property naming conventions

2. **Azure URI Parsing Errors**
   - Validate URI format according to Azure specifications
   - Check for proper container and account names
   - Verify endpoint suffixes (.blob.core.windows.net, .dfs.core.windows.net)

3. **Vended Credential Issues**
   - Verify token expiration times
   - Check for proper session token inclusion
   - Validate region and endpoint configurations

4. **Provider Chain Failures**
   - Ensure properties match at least one provider's requirements
   - Check for typos in property names
   - Verify that required properties are present

### Debug Steps

1. **Enable debug logging** for credential operations
2. **Test with minimal configurations** to isolate issues
3. **Use credential masking** to safely share configuration examples
4. **Validate URIs** using online tools for Azure storage paths
5. **Check cloud provider documentation** for specific requirements

## Future Enhancements

Potential areas for future development:
1. **Credential Rotation**: Automatic credential refresh and rotation
2. **Multi-Factor Authentication**: Support for MFA in cloud providers
3. **Credential Caching**: Intelligent caching with TTL and refresh
4. **Audit Logging**: Comprehensive audit trail for credential usage
5. **Key Management Service**: Integration with cloud KMS services
6. **Credential Health Monitoring**: Proactive monitoring of credential status
7. **Automated Credential Provisioning**: Integration with cloud IAM services
8. **Cross-Cloud Credential Federation**: Support for federated authentication

## Related Documentation

- **Connector Framework**: External table integration and unified data access
- **Storage Engine**: Data persistence layer and cloud storage integration
- **Frontend Server**: Metadata operations and credential validation
- **Java Extensions**: External connector support and Hadoop ecosystem integration
- **Common Utilities**: Shared utility functions and security implementations

## Summary

The credential_cloud module serves as the central authentication hub for StarRocks' cloud integrations. By providing a unified interface for multiple cloud providers, implementing robust security measures, and supporting various authentication methods, it enables secure and efficient cloud storage access across the entire system. The module's design emphasizes security, flexibility, and ease of use, making it a critical component for modern cloud-native data lakehouse architectures.

The comprehensive provider support, vended credential handling, and extensive security features make this module suitable for enterprise deployments requiring multi-cloud capabilities and stringent security requirements. Regular updates and enhancements ensure compatibility with evolving cloud services and security standards.