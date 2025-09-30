# AWS Compile Stream Events Module

## Introduction

The `aws-compile-stream-events` module is responsible for compiling AWS Lambda stream event source mappings into CloudFormation resources. It handles the configuration and deployment of Lambda functions that are triggered by DynamoDB and Kinesis streams, including support for enhanced fan-out consumers and advanced stream processing features.

This module is part of the AWS provider plugin ecosystem and integrates with the Serverless Framework's event-driven architecture to enable real-time data processing capabilities.

## Architecture Overview

```mermaid
graph TB
    subgraph "AWS Provider Plugin System"
        AP[AwsProvider]
        APC[AwsPackage]
        ACF[AwsCompileFunctions]
        ASE[AwsCompileStreamEvents]
        
        AP --> APC
        APC --> ACF
        APC --> ASE
    end
    
    subgraph "Serverless Core"
        S[Serverless]
        PS[PluginManager]
        CSFH[ConfigSchemaHandler]
        
        S --> PS
        PS --> AP
        CSFH --> ASE
    end
    
    subgraph "CloudFormation Output"
        ESM[AWS::Lambda::EventSourceMapping]
        SC[AWS::Kinesis::StreamConsumer]
        IAM[IAM Role Policies]
        
        ASE --> ESM
        ASE --> SC
        ASE --> IAM
    end
```

## Component Structure

### Core Component: AwsCompileStreamEvents

The `AwsCompileStreamEvents` class is the main component that handles stream event compilation. It integrates with the Serverless Framework through a hook-based architecture and schema validation system.

```mermaid
classDiagram
    class AwsCompileStreamEvents {
        -serverless: Serverless
        -provider: AwsProvider
        -hooks: Object
        +constructor(serverless)
        +compileStreamEvents()
        -processStreamEvent(event, functionName, functionObj)
        -createStreamResource(config)
        -createConsumerResource(config)
        -updateIamPolicies(statements)
    }
    
    class Serverless {
        +service: Service
        +configSchemaHandler: ConfigSchemaHandler
        +getProvider(name)
    }
    
    class AwsProvider {
        +naming: Naming
        +resolveFunctionIamRoleResourceName(functionObj)
    }
    
    class ConfigSchemaHandler {
        +defineFunctionEvent(provider, event, schema)
    }
    
    Serverless --> AwsCompileStreamEvents : uses
    AwsProvider --> AwsCompileStreamEvents : uses
    ConfigSchemaHandler --> AwsCompileStreamEvents : uses
```

## Event Processing Flow

```mermaid
sequenceDiagram
    participant SF as Serverless Framework
    participant ASE as AwsCompileStreamEvents
    participant AP as AwsProvider
    participant CF as CloudFormation Template
    participant IAM as IAM Policies
    
    SF->>ASE: package:compileEvents hook
    ASE->>ASE: compileStreamEvents()
    
    loop For each function
        ASE->>ASE: getFunction(functionName)
        ASE->>ASE: Process events array
        
        alt Stream event found
            ASE->>ASE: Parse stream configuration
            ASE->>ASE: Determine stream type (dynamodb/kinesis)
            ASE->>ASE: Create EventSourceMapping resource
            
            alt Kinesis with consumer
                ASE->>ASE: Create StreamConsumer resource
                ASE->>ASE: Update EventSourceMapping dependencies
            end
            
            ASE->>AP: getStreamLogicalId()
            ASE->>CF: Add resources to template
            ASE->>IAM: Update policy statements
        end
    end
    
    ASE->>SF: Return compiled resources
```

## Stream Event Configuration Schema

The module defines a comprehensive schema for stream events that supports both simple ARN-based configuration and advanced object-based configuration:

```mermaid
graph LR
    subgraph "Stream Event Schema"
        SE[Stream Event]
        SE --> ARN[ARN String]
        SE --> OBJ[Object Config]
        
        OBJ --> ARN2[arn]
        OBJ --> TYPE[type: dynamodb or kinesis]
        OBJ --> BS[batchSize: 1-10000]
        OBJ --> PF[parallelizationFactor: 1-10]
        OBJ --> SP[startingPosition]
        OBJ --> EN[enabled]
        OBJ --> CON[consumer]
        OBJ --> BW[batchWindow]
        OBJ --> MRA[maximumRetryAttempts]
        OBJ --> BB[bisectBatchOnFunctionError]
        OBJ --> MRA2[maximumRecordAgeInSeconds]
        OBJ --> FRT[functionResponseType]
        OBJ --> DEST[destinations]
        OBJ --> TW[tumblingWindowInSeconds]
        OBJ --> FP[filterPatterns]
    end
```

## Stream Processing Features

### 1. Stream Type Support

- **DynamoDB Streams**: Change data capture from DynamoDB tables
- **Kinesis Streams**: Real-time data streaming with enhanced fan-out support

### 2. Advanced Configuration Options

```mermaid
graph TD
    subgraph "Stream Configuration Features"
        BC[Basic Configuration]
        AC[Advanced Configuration]
        EC[Enhanced Consumer]
        ED[Error Handling]
        FP[Filtering]
        
        BC --> ARN[ARN Reference]
        BC --> BS[Batch Size]
        BC --> SP[Starting Position]
        
        AC --> PF[Parallelization Factor]
        AC --> BW[Batch Window]
        AC --> TW[Tumbling Window]
        AC --> MRA[Max Retry Attempts]
        AC --> MRA2[Max Record Age]
        
        EC --> CON[Consumer Support]
        EC --> EFO[Enhanced Fan-Out]
        
        ED --> BB[Bisect Batch on Error]
        ED --> FR[Function Response Type]
        ED --> DEST[Failure Destinations]
        
        FP --> FPAT[Filter Patterns]
    end
```

### 3. IAM Policy Management

The module automatically generates appropriate IAM policy statements based on the stream configuration:

- **DynamoDB Streams**: `dynamodb:GetRecords`, `dynamodb:GetShardIterator`, `dynamodb:DescribeStream`, `dynamodb:ListStreams`
- **Kinesis Streams**: `kinesis:GetRecords`, `kinesis:GetShardIterator`, `kinesis:DescribeStream`, `kinesis:ListStreams`
- **Kinesis Enhanced Consumer**: `kinesis:GetRecords`, `kinesis:GetShardIterator`, `kinesis:DescribeStreamSummary`, `kinesis:ListShards`, `kinesis:SubscribeToShard`
- **Failure Destinations**: `sns:Publish`, `sqs:ListQueues`, `sqs:SendMessage`

## Integration with Serverless Framework

### Hook System Integration

```mermaid
graph LR
    subgraph "Serverless Hook System"
        INIT[initialize]
        PCE[package:compileEvents]
        
        INIT --> DEP[Deprecation Warning Check]
        PCE --> CSE[compileStreamEvents]
        
        CSE --> PF[Process Functions]
        CSE --> PE[Process Events]
        CSE --> CR[Create Resources]
        CSE --> UP[Update Policies]
    end
```

### Schema Registration

The module registers its event schema with the Serverless Framework's configuration schema handler, enabling validation and auto-completion for stream events in `serverless.yml` files.

## Dependencies and Relationships

### Direct Dependencies

- **[aws-provider](aws-provider.md)**: Provides AWS-specific functionality and naming conventions
- **[aws-package-compile](aws-package-compile.md)**: Parent compilation module for AWS packaging
- **[core-framework](core-framework.md)**: Core Serverless Framework services and utilities

### Related Modules

- **[aws-compile-kafka-events](aws-compile-kafka-events.md)**: Handles Kafka stream events
- **[aws-compile-msk-events](aws-compile-msk-events.md)**: Handles MSK stream events
- **[aws-compile-activemq-events](aws-compile-activemq-events.md)**: Handles ActiveMQ events
- **[aws-compile-rabbitmq-events](aws-compile-rabbitmq-events.md)**: Handles RabbitMQ events

## Error Handling and Validation

The module includes comprehensive validation for stream configurations:

- **Schema Validation**: Ensures all required fields are present and valid
- **Timestamp Validation**: Validates `startingPositionTimestamp` when `startingPosition` is `AT_TIMESTAMP`
- **Resource Validation**: Ensures ARNs are properly formatted and accessible
- **Dependency Validation**: Validates that consumer resources are properly linked

## CloudFormation Resource Generation

### Event Source Mapping Resource

```yaml
Type: AWS::Lambda::EventSourceMapping
Properties:
  BatchSize: integer
  Enabled: boolean
  EventSourceArn: string
  FunctionName: string
  ParallelizationFactor: integer
  StartingPosition: string
  # Optional properties based on configuration
```

### Kinesis Stream Consumer Resource

```yaml
Type: AWS::Kinesis::StreamConsumer
Properties:
  StreamARN: string
  ConsumerName: string
```

## Usage Examples

### Basic DynamoDB Stream

```yaml
functions:
  processDynamoDBStream:
    handler: handler.processStream
    events:
      - stream: arn:aws:dynamodb:region:account:table/table-name/stream/timestamp
```

### Advanced Kinesis Stream with Consumer

```yaml
functions:
  processKinesisStream:
    handler: handler.processStream
    events:
      - stream:
          arn: arn:aws:kinesis:region:account:stream/stream-name
          type: kinesis
          batchSize: 100
          startingPosition: LATEST
          consumer: true
          destinations:
            onFailure:
              arn: arn:aws:sns:region:account:topic/failure-topic
              type: sns
```

## Best Practices

1. **Batch Size Optimization**: Choose appropriate batch sizes based on processing requirements and Lambda timeout settings
2. **Error Handling**: Configure failure destinations for reliable error handling
3. **Consumer Usage**: Use enhanced consumers for improved performance with Kinesis streams
4. **Filtering**: Implement filter patterns to reduce unnecessary Lambda invocations
5. **Monitoring**: Configure appropriate retry attempts and record age limits for your use case

## Migration and Deprecation

The module includes deprecation warnings for legacy naming schemes, particularly for Kinesis consumer naming. Users should migrate to the new `serviceSpecific` naming mode by setting `provider.kinesis.consumerNamingMode` to `serviceSpecific`.