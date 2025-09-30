# AWS Compile Kafka Events Module

## Introduction

The `aws-compile-kafka-events` module is responsible for compiling and configuring AWS Lambda event source mappings for Apache Kafka events within the Serverless Framework. This module enables serverless functions to consume messages from self-managed Apache Kafka clusters as event sources, providing seamless integration between Kafka messaging systems and AWS Lambda functions.

## Architecture Overview

The module operates as part of the AWS event compilation pipeline, specifically handling Kafka event sources during the CloudFormation template generation process. It transforms Kafka event configurations defined in `serverless.yml` into AWS Lambda EventSourceMapping resources that establish the connection between Lambda functions and Kafka topics.

```mermaid
graph TB
    subgraph "Serverless Framework Core"
        CF[CloudFormation Template]
        PM[Plugin Manager]
        CS[Configuration Schema]
    end
    
    subgraph "AWS Events Module"
        AKE[AwsCompileKafkaEvents]
        ACE[AwsCompileActiveMQEvents]
        AMSE[AwsCompileMSKEvents]
        ARE[AwsCompileRabbitMQEvents]
        ASE[AwsCompileStreamEvents]
    end
    
    subgraph "AWS Provider"
        AP[AwsProvider]
        AC[AwsCommon]
    end
    
    subgraph "AWS Services"
        ES[EventSourceMapping]
        SM[Secrets Manager]
        EC2[EC2 Services]
        Lambda[Lambda Function]
    end
    
    subgraph "Kafka Infrastructure"
        KC[Kafka Cluster]
        KT[Kafka Topic]
        KCG[Kafka Consumer Group]
    end
    
    PM --> AKE
    CS --> AKE
    AKE --> CF
    AKE --> AP
    AKE --> ES
    AKE --> SM
    AKE --> EC2
    ES --> Lambda
    ES --> KC
    Lambda --> KT
    KCG --> KT
    
    style AKE fill:#f9f,stroke:#333,stroke-width:4px
```

## Component Structure

### Core Component: AwsCompileKafkaEvents

The `AwsCompileKafkaEvents` class is the primary component responsible for processing Kafka event configurations and generating the appropriate AWS resources.

```mermaid
classDiagram
    class AwsCompileKafkaEvents {
        -serverless: Serverless
        -provider: AwsProvider
        +constructor(serverless)
        +compileKafkaEvents()
        -validateConfiguration(functionName, event)
        -createEventSourceMapping(functionName, event)
        -configurePermissions(functionName, event)
    }
    
    class Serverless {
        +getProvider(name)
        +service
        +configSchemaHandler
    }
    
    class AwsProvider {
        +naming
        +resolveFunctionIamRoleResourceName()
    }
    
    class CloudFormationTemplate {
        +Resources
    }
    
    AwsCompileKafkaEvents --> Serverless : uses
    AwsCompileKafkaEvents --> AwsProvider : uses
    AwsCompileKafkaEvents --> CloudFormationTemplate : modifies
```

## Configuration Schema

The module defines a comprehensive schema for Kafka event configuration that supports various authentication methods and networking options:

```mermaid
graph LR
    subgraph "Kafka Event Configuration"
        KE[Kafka Event]
        AC[Access Configurations]
        BS[Bootstrap Servers]
        TP[Topic]
        
        subgraph "Access Configurations"
            VS[VPC Subnet]
            VSG[VPC Security Group]
            SPA[SASL Plain Auth]
            SS256[SASL SCRAM 256]
            SS512[SASL SCRAM 512]
            CCTA[Client Cert TLS]
            SRCC[Server Root CA]
        end
        
        subgraph "Optional Settings"
            BSZ[Batch Size]
            MBW[Max Batching Window]
            EN[Enabled]
            SP[Starting Position]
            SPT[Starting Position Timestamp]
            CGID[Consumer Group ID]
            FP[Filter Patterns]
        end
    end
    
    KE --> AC
    KE --> BS
    KE --> TP
    AC --> VS
    AC --> VSG
    AC --> SPA
    AC --> SS256
    AC --> SS512
    AC --> CCTA
    AC --> SRCC
    KE --> BSZ
    KE --> MBW
    KE --> EN
    KE --> SP
    KE --> SPT
    KE --> CGID
    KE --> FP
```

## Data Flow and Processing

### Event Compilation Process

```mermaid
sequenceDiagram
    participant SF as Serverless Framework
    participant AKE as AwsCompileKafkaEvents
    participant CF as CloudFormation
    participant AWS as AWS Services
    
    SF->>AKE: package:compileEvents hook
    AKE->>SF: getAllFunctions()
    loop For each function
        AKE->>SF: getFunction(functionName)
        loop For each event
            alt Event is Kafka
                AKE->>AKE: validateConfiguration()
                AKE->>AKE: createEventSourceMapping()
                AKE->>AKE: configurePermissions()
                AKE->>CF: add EventSourceMapping resource
            end
        end
    end
    AKE->>CF: update IAM role permissions
    CF->>AWS: deploy resources
```

### Permission Configuration Flow

```mermaid
flowchart TD
    Start[Start Kafka Event Processing]
    CheckAuth{Authentication Type?}
    
    CheckAuth -->|VPC| VPCPerms[Add EC2 Permissions]
    CheckAuth -->|SASL/SCRAM| SecretPerms[Add Secrets Manager Permissions]
    CheckAuth -->|TLS| TLSPerm[Add Secrets Manager Permissions]
    
    VPCPerms --> AddEC2Statement[Add EC2 IAM Statement]
    SecretPerms --> AddSecretStatement[Add Secrets Manager IAM Statement]
    TLSPerm --> AddSecretStatement
    
    AddEC2Statement --> CheckResource{Has Resources?}
    AddSecretStatement --> CheckResource
    
    CheckResource -->|Yes| UpdateIAM[Update IAM Role]
    CheckResource -->|No| SkipIAM[Skip IAM Update]
    
    UpdateIAM --> End[End Processing]
    SkipIAM --> End
```

## Integration Points

### Dependencies

The module integrates with several other components within the Serverless Framework ecosystem:

1. **[aws-provider](aws-provider.md)**: Provides AWS-specific functionality and naming conventions
2. **[aws-package-compile](aws-package-compile.md)**: Parent module for AWS resource compilation
3. **[core-framework](core-framework.md)**: Core Serverless Framework services and configuration
4. **[aws-common](aws-common.md)**: Shared AWS utilities and helpers

### Resource Dependencies

```mermaid
graph BT
    subgraph "Generated Resources"
        ESM[EventSourceMapping]
        IAM[IAM Role]
        Lambda[Lambda Function]
    end
    
    subgraph "Dependencies"
        IR[IAM Role Resource]
        TA[Target Alias]
        BR[Bootstrap Servers]
        TP[Topic Configuration]
    end
    
    ESM --> IR
    ESM --> TA
    ESM --> Lambda
    ESM --> BR
    ESM --> TP
    IAM --> ESM
```

## Security and Authentication

### Authentication Methods

The module supports multiple authentication mechanisms for connecting to Kafka clusters:

1. **VPC-based Access**: Uses VPC subnets and security groups for network-level security
2. **SASL Authentication**: Supports PLAIN, SCRAM-256, and SCRAM-512 mechanisms
3. **TLS Authentication**: Client certificate and server root CA certificate validation
4. **Secrets Manager Integration**: Secure storage and retrieval of authentication credentials

### Permission Management

```mermaid
graph LR
    subgraph "IAM Permissions"
        EC2Perms[EC2 Permissions]
        SecretPerms[Secrets Manager]
        LambdaPerms[Lambda Execution]
    end
    
    subgraph "EC2 Permissions"
        CreateNI[Create Network Interface]
        DescribeNI[Describe Network Interfaces]
        DescribeVPC[Describe VPCs]
        DeleteNI[Delete Network Interface]
        DescribeSub[Describe Subnets]
        DescribeSG[Describe Security Groups]
    end
    
    subgraph "Secrets Manager"
        GetSecret[Get Secret Value]
    end
    
    EC2Perms --> CreateNI
    EC2Perms --> DescribeNI
    EC2Perms --> DescribeVPC
    EC2Perms --> DeleteNI
    EC2Perms --> DescribeSub
    EC2Perms --> DescribeSG
    SecretPerms --> GetSecret
```

## Configuration Examples

### Basic Kafka Event Configuration

```yaml
functions:
  processKafkaMessages:
    handler: handler.processKafka
    events:
      - kafka:
          accessConfigurations:
            vpcSubnet:
              - subnet-12345678
            vpcSecurityGroup:
              - sg-12345678
          bootstrapServers:
            - "broker1.kafka.example.com:9092"
            - "broker2.kafka.example.com:9092"
          topic: "my-topic"
          batchSize: 100
          startingPosition: LATEST
```

### SASL Authentication Configuration

```yaml
functions:
  processKafkaMessages:
    handler: handler.processKafka
    events:
      - kafka:
          accessConfigurations:
            saslScram512Auth:
              - "arn:aws:secretsmanager:region:account:secret:kafka-credentials"
          bootstrapServers:
            - "broker1.kafka.example.com:9092"
          topic: "secure-topic"
          consumerGroupId: "my-consumer-group"
```

## Error Handling

The module implements comprehensive validation and error handling for configuration issues:

- **VPC Configuration Validation**: Ensures both subnet and security group are specified
- **Starting Position Validation**: Validates timestamp requirements for AT_TIMESTAMP mode
- **Schema Validation**: Enforces configuration schema requirements
- **Resource Validation**: Validates AWS resource ARNs and formats

## Performance Considerations

### Batch Processing
- Supports batch sizes from 1 to 10,000 messages
- Configurable maximum batching window (0-300 seconds)
- Filter patterns for message preprocessing

### Scaling
- Consumer group ID configuration for parallel processing
- Starting position options for different consumption patterns
- Enable/disable functionality for event source management

## Related Documentation

- [AWS Provider Module](aws-provider.md) - Core AWS provider functionality
- [AWS Package Compile Module](aws-package-compile.md) - Parent compilation module
- [AWS Streaming Events Module](aws-streaming-events.md) - Related streaming event handlers
- [Core Framework Module](core-framework.md) - Serverless Framework core services