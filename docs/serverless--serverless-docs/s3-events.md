# S3 Events Module Documentation

## Introduction

The S3 Events module is a critical component of the Serverless Framework's AWS provider plugin system, responsible for configuring and managing S3 bucket event triggers for AWS Lambda functions. This module enables developers to automatically invoke Lambda functions in response to S3 bucket events such as object creation, deletion, or modification.

The module handles both new S3 buckets created within the Serverless service and existing S3 buckets that need to be configured with Lambda event notifications. It generates the necessary CloudFormation resources and IAM permissions to establish secure, reliable event-driven architectures between S3 and Lambda services.

## Architecture Overview

```mermaid
graph TB
    subgraph "S3 Events Module"
        ACS[AwsCompileS3Events]
        
        subgraph "Core Methods"
            NB[newS3Buckets]
            EB[existingS3Buckets]
            CSR[addCustomResourceToService]
            RLT[resolveLambdaTarget]
        end
        
        subgraph "Schema Definition"
            SD[defineFunctionEvent Schema]
        end
    end
    
    subgraph "Serverless Framework"
        SM[Service Model]
        PM[Plugin Manager]
        CFT[CloudFormation Template]
        IAM[IAM Role Statements]
    end
    
    subgraph "AWS Services"
        S3[S3 Service]
        Lambda[Lambda Service]
        CF[CloudFormation]
    end
    
    ACS --> SD
    ACS --> NB
    ACS --> EB
    NB --> CFT
    EB --> CSR
    EB --> IAM
    CSR --> CF
    CFT --> S3
    CFT --> Lambda
    SM --> ACS
    PM --> ACS
```

## Component Relationships

```mermaid
graph LR
    subgraph "Dependencies"
        ACS[AwsCompileS3Events]
        SE[ServerlessError]
        RLT[resolveLambdaTarget]
        AC[addCustomResourceToService]
        _[lodash]
    end
    
    subgraph "Serverless Core"
        SCH[ConfigSchemaHandler]
        PN[Provider Naming]
        SM[Service Model]
    end
    
    subgraph "Generated Resources"
        S3B[S3 Bucket Resources]
        LP[Lambda Permissions]
        CR[Custom Resources]
        IRS[IAM Role Statements]
    end
    
    ACS --> SE
    ACS --> RLT
    ACS --> AC
    ACS --> _
    ACS --> SCH
    ACS --> PN
    ACS --> SM
    
    ACS --> S3B
    ACS --> LP
    ACS --> CR
    ACS --> IRS
```

## Data Flow

```mermaid
sequenceDiagram
    participant SF as Serverless Framework
    participant ACS as AwsCompileS3Events
    participant NB as newS3Buckets
    participant EB as existingS3Buckets
    participant CF as CloudFormation
    participant AWS as AWS Services
    
    SF->>ACS: package:compileEvents hook
    ACS->>ACS: Define S3 event schema
    
    alt New S3 Buckets
        ACS->>NB: Process new buckets
        NB->>NB: Parse function events
        NB->>NB: Validate bucket names
        NB->>NB: Generate bucket configurations
        NB->>CF: Create S3 bucket resources
        NB->>CF: Create Lambda permissions
    end
    
    alt Existing S3 Buckets
        ACS->>EB: Process existing buckets
        EB->>EB: Parse function events
        EB->>EB: Validate single bucket per function
        EB->>CF: Create custom resources
        EB->>CF: Generate IAM role statements
    end
    
    CF->>AWS: Deploy resources
    AWS->>AWS: Configure S3 notifications
    AWS->>AWS: Set Lambda permissions
```

## Core Functionality

### Event Schema Definition

The module defines a comprehensive schema for S3 function events that supports multiple configuration patterns:

```javascript
{
  anyOf: [
    { type: 'string' },                    // Simple bucket name
    {
      type: 'object',
      properties: {
        bucket: { /* string or CloudFormation function */ },
        event: { type: 'string', pattern: '^s3:.+$' },
        existing: { type: 'boolean' },      // Use existing bucket
        forceDeploy: { type: 'boolean' },   // Force deployment
        rules: [                            // Filter rules
          {
            type: 'object',
            properties: {
              prefix: { /* string or CF function */ },
              suffix: { /* string or CF function */ }
            },
            maxProperties: 1
          }
        ]
      },
      required: ['bucket']
    }
  ]
}
```

### New S3 Bucket Processing

The `newS3Buckets()` method handles the creation and configuration of new S3 buckets:

1. **Event Collection**: Iterates through all functions and collects S3 events
2. **Bucket Validation**: Validates bucket names against AWS naming patterns
3. **Configuration Aggregation**: Groups Lambda configurations by bucket name
4. **CloudFormation Generation**: Creates S3 bucket resources with notification configurations
5. **Permission Setup**: Generates Lambda permissions for S3 to invoke functions

### Existing S3 Bucket Processing

The `existingS3Buckets()` method manages configuration of pre-existing S3 buckets:

1. **Custom Resource Creation**: Uses CloudFormation custom resources to configure existing buckets
2. **IAM Role Management**: Creates necessary IAM permissions for bucket notification management
3. **Dependency Management**: Handles dependencies between multiple custom resources
4. **Validation**: Ensures only one S3 bucket per function for existing configurations

## Process Flow

```mermaid
flowchart TD
    Start([package:compileEvents Hook])
    --> Schema[Define S3 Event Schema]
    
    Schema --> NewBuckets{Process New Buckets?}
    NewBuckets -->|Yes| CollectNew[Collect New S3 Events]
    CollectNew --> ValidateNew[Validate Bucket Names]
    ValidateNew --> AggregateNew[Aggregate Configurations]
    AggregateNew --> GenerateNew[Generate CF Resources]
    GenerateNew --> PermissionsNew[Create Lambda Permissions]
    
    NewBuckets -->|No| ExistingBuckets{Process Existing Buckets?}
    ExistingBuckets -->|Yes| CollectExisting[Collect Existing S3 Events]
    CollectExisting --> ValidateExisting[Validate Single Bucket per Function]
    ValidateExisting --> CreateCustom[Create Custom Resources]
    CreateCustom --> GenerateIAM[Generate IAM Statements]
    GenerateIAM --> Dependencies[Manage Dependencies]
    
    ExistingBuckets -->|No| End([End])
    PermissionsNew --> End
    Dependencies --> End
```

## Integration Points

### Serverless Framework Integration

The module integrates deeply with the Serverless Framework's plugin system:

- **Hook Registration**: Registers for the `package:compileEvents` lifecycle hook
- **Schema Registration**: Defines event schemas through `configSchemaHandler`
- **Service Model Access**: Accesses function configurations and provider settings
- **CloudFormation Template**: Modifies the compiled CloudFormation template

### AWS Provider Dependencies

The module relies on several AWS provider components:

- **[aws-provider.md](aws-provider.md)**: Core AWS provider functionality
- **[aws-package-compile.md](aws-package-compile.md)**: Package compilation infrastructure
- **[aws-common.md](aws-common.md)**: Common AWS utilities and helpers

### Custom Resource Framework

For existing bucket management, the module leverages the custom resource framework:

- **Custom Resource Function**: Creates Lambda functions for bucket configuration
- **IAM Role Statements**: Generates necessary permissions for bucket management
- **Dependency Management**: Handles complex dependencies between resources

## Security Considerations

### IAM Permissions

The module generates minimal IAM permissions following the principle of least privilege:

- **S3 Permissions**: `s3:PutBucketNotification`, `s3:GetBucketNotification` for existing buckets
- **Lambda Permissions**: `lambda:AddPermission`, `lambda:RemovePermission` for permission management
- **Resource Scoping**: Permissions are scoped to specific buckets and functions

### Source ARN Validation

Lambda permissions include source ARN validation to ensure only authorized S3 buckets can invoke functions:

```javascript
SourceArn: {
  'Fn::Join': ['', ['arn:', { Ref: 'AWS::Partition' }, `:s3:::${bucketName}`]]
}
```

## Error Handling

The module implements comprehensive error handling for various scenarios:

### Validation Errors

- **Invalid Bucket Names**: Validates against AWS S3 bucket naming patterns
- **CloudFormation Function Restrictions**: Prevents CF functions for new buckets
- **Multiple Buckets per Function**: Enforces single bucket per function for existing configurations

### Custom Error Types

```javascript
throw new ServerlessError(
  'When specifying "s3.bucket" with CloudFormation intrinsic function, you need to specify that the bucket is existing via "existing: true" property.',
  'S3_INVALID_NEW_BUCKET_FORMAT'
)
```

## Best Practices

### Bucket Configuration

1. **Use Existing Buckets**: For production environments, use existing buckets with proper `existing: true` configuration
2. **Event Filtering**: Utilize prefix/suffix rules to minimize Lambda invocations
3. **Naming Conventions**: Follow AWS S3 bucket naming conventions and patterns

### Performance Optimization

1. **Batch Processing**: The module processes all S3 events in a single compilation pass
2. **Dependency Optimization**: Minimizes CloudFormation dependencies to reduce deployment time
3. **Resource Reuse**: Reuses custom resources for multiple functions targeting the same bucket

### Deployment Strategies

1. **Force Deploy**: Use `forceDeploy: true` for existing buckets when configuration changes don't trigger updates
2. **Staged Rollouts**: Consider bucket-specific deployments for large-scale applications
3. **Monitoring**: Implement proper monitoring for S3 event processing and Lambda invocations

## Related Documentation

- **[aws-events.md](aws-events.md)**: Overview of all AWS event types
- **[aws-package-compile.md](aws-package-compile.md)**: Package compilation process
- **[aws-provider.md](aws-provider.md)**: AWS provider configuration and setup
- **[core-framework.md](core-framework.md)**: Core Serverless Framework architecture