# CloudWatch Event Events Module

## Introduction

The CloudWatch Event Events module is a specialized component within the Serverless Framework's AWS provider plugin system. It handles the compilation and configuration of AWS CloudWatch Events rules that trigger Lambda functions based on event patterns. This module enables serverless applications to respond to AWS service events, custom events, and scheduled events through the CloudWatch Events service.

## Architecture Overview

The CloudWatch Event Events module operates as part of the AWS events compilation pipeline, transforming serverless function event definitions into AWS CloudFormation resources.

```mermaid
graph TB
    subgraph "Serverless Framework Core"
        SF[Serverless Service]
        PM[Plugin Manager]
        CF[CloudFormation Template]
    end
    
    subgraph "AWS Provider Plugin"
        AP[AwsProvider]
        ACP[AwsCompileCloudWatchEventEvents]
        ACF[AWS CloudFormation Resources]
    end
    
    subgraph "AWS Services"
        CWE[CloudWatch Events]
        Lambda[Lambda Service]
    end
    
    SF -->|Function Definitions| PM
    PM -->|Load AWS Provider| AP
    AP -->|Register Event Compiler| ACP
    ACP -->|Compile Event Rules| CF
    CF -->|Deploy| ACF
    ACF -->|Create Rules| CWE
    CWE -->|Trigger| Lambda
```

## Core Components

### AwsCompileCloudWatchEventEvents

The primary class responsible for compiling CloudWatch Event configurations into CloudFormation resources.

**Location**: `lib/plugins/aws/package/compile/events/cloud-watch-event.js`

**Key Responsibilities**:
- Schema definition for CloudWatch Event configurations
- Validation of event properties and mutual exclusivity rules
- Generation of CloudFormation templates for Event Rules and Lambda permissions
- Input transformation and formatting

```mermaid
classDiagram
    class AwsCompileCloudWatchEventEvents {
        -serverless: Serverless
        -provider: AwsProvider
        +constructor(serverless)
        +compileCloudWatchEventEvents()
        -formatInputTransformer(inputTransformer)
    }
    
    class Serverless {
        +getProvider(name)
        +getAllFunctions()
        +getFunction(name)
        +configSchemaHandler
    }
    
    class AwsProvider {
        +naming: Naming
    }
    
    class CloudFormationTemplate {
        +Resources: Object
    }
    
    AwsCompileCloudWatchEventEvents --> Serverless
    AwsCompileCloudWatchEventEvents --> AwsProvider
    AwsCompileCloudWatchEventEvents --> CloudFormationTemplate
```

## Configuration Schema

The module defines a comprehensive schema for CloudWatch Event configurations with the following properties:

```javascript
{
  type: 'object',
  properties: {
    event: { type: 'object' },                    // Event pattern definition
    input: {                                       // Static input data
      anyOf: [
        { type: 'string', maxLength: 8192 },
        { type: 'object' }
      ]
    },
    inputPath: { type: 'string', minLength: 1, maxLength: 256 },
    inputTransformer: {                            // Input transformation rules
      type: 'object',
      properties: {
        inputPathsMap: { type: 'object' },
        inputTemplate: { type: 'string', minLength: 1, maxLength: 8192 }
      },
      required: ['inputTemplate']
    },
    description: { type: 'string', maxLength: 512 },
    name: {                                        // Rule name
      type: 'string',
      pattern: '[a-zA-Z0-9-_.]+',
      minLength: 1,
      maxLength: 64
    },
    enabled: { type: 'boolean' }                   // Rule state
  }
}
```

## Compilation Process

### Event Processing Flow

```mermaid
sequenceDiagram
    participant SF as Serverless Framework
    participant AC as AwsCompileCloudWatchEventEvents
    participant CF as CloudFormation Template
    participant AWS as AWS CloudWatch
    
    SF->>AC: Load function definitions
    AC->>AC: Validate event configurations
    AC->>AC: Generate Event Rule template
    AC->>AC: Generate Lambda Permission template
    AC->>CF: Merge resources into template
    CF->>AWS: Deploy CloudFormation stack
    AWS->>AWS: Create Event Rule
    AWS->>AWS: Set Lambda permissions
```

### Resource Generation

The module generates two primary CloudFormation resources for each CloudWatch Event:

1. **AWS::Events::Rule**: Defines the event pattern and target configuration
2. **AWS::Lambda::Permission**: Grants CloudWatch Events permission to invoke the Lambda function

```mermaid
graph LR
    subgraph "CloudFormation Resources"
        ER[AWS::Events::Rule]
        LP[AWS::Lambda::Permission]
    end
    
    subgraph "Rule Properties"
        EP[EventPattern]
        ST[State]
        TG[Targets]
        IT[InputTransformer]
    end
    
    subgraph "Permission Properties"
        FN[FunctionName]
        AC[Action]
        PR[Principal]
        SA[SourceArn]
    end
    
    ER --> EP
    ER --> ST
    ER --> TG
    ER --> IT
    
    LP --> FN
    LP --> AC
    LP --> PR
    LP --> SA
    
    TG -.->|References| LP
    SA -.->|References| ER
```

## Input Handling

The module supports three mutually exclusive input methods:

### 1. Static Input (`input`)
- Direct JSON or string input passed to the Lambda function
- Maximum length: 8192 characters
- Objects are automatically stringified

### 2. Input Path (`inputPath`)
- JSONPath expression to extract data from the event
- Maximum length: 256 characters
- Used for selective data extraction

### 3. Input Transformer (`inputTransformer`)
- Advanced transformation using InputTemplate and optional InputPathsMap
- Maximum template length: 8192 characters
- Supports variable substitution and formatting

```mermaid
graph TD
    subgraph "Input Methods"
        I[Input]
        IP[InputPath]
        IT[InputTransformer]
    end
    
    subgraph "Validation"
        V{Mutual Exclusion}
        E[Error: Multiple inputs]
    end
    
    subgraph "Processing"
        SJ[Stringify JSON]
        EQ[Escape Quotes]
        FT[Format Transformer]
    end
    
    I --> V
    IP --> V
    IT --> V
    
    V -->|Multiple| E
    V -->|Single| SJ
    SJ --> EQ
    IT --> FT
```

## Dependencies and Integration

### Module Dependencies

The CloudWatch Event Events module integrates with several core components:

```mermaid
graph TB
    subgraph "Core Dependencies"
        SS[Serverless Service]
        AP[AwsProvider]
        CSH[ConfigSchemaHandler]
        SE[ServerlessError]
    end
    
    subgraph "Utility Dependencies"
        RLT[resolveLambdaTarget]
        LODASH[lodash]
    end
    
    subgraph "AWS Provider"
        CWE[AwsCompileCloudWatchEventEvents]
    end
    
    SS -->|Provides functions| CWE
    AP -->|Provides naming| CWE
    CSH -->|Defines schema| CWE
    SE -->|Error handling| CWE
    RLT -->|Resolve targets| CWE
    LODASH -->|Utilities| CWE
```

### Related Modules

- **[aws-provider](aws-provider.md)**: Parent AWS provider module
- **[aws-events](aws-events.md)**: Sibling event compilation modules
- **[aws-package-compile](aws-package-compile.md)**: Package compilation framework
- **[configuration-management](configuration-management.md)**: Configuration schema handling

## Error Handling

The module implements specific error handling for configuration validation:

### CloudWatch Multiple Input Properties Error
- **Code**: `CLOUDWATCH_MULTIPLE_INPUT_PROPERTIES`
- **Trigger**: When multiple input methods are specified simultaneously
- **Message**: "You can only set one of input, inputPath, or inputTransformer properties at the same time for cloudwatch events."

## Usage Examples

### Basic Event Pattern
```yaml
functions:
  myFunction:
    handler: index.handler
    events:
      - cloudwatchEvent:
          event:
            source:
              - aws.ec2
            detail-type:
              - EC2 Instance State-change Notification
            detail:
              state:
                - running
```

### Input Transformer Configuration
```yaml
functions:
  myFunction:
    handler: index.handler
    events:
      - cloudwatchEvent:
          event:
            source:
              - aws.ec2
          inputTransformer:
            inputPathsMap:
              instanceId: '$.detail.instance-id'
              state: '$.detail.state'
            inputTemplate: '{"instance": "<instanceId>", "status": "<state>"}'
```

## Best Practices

1. **Event Pattern Design**: Use specific event patterns to minimize unnecessary Lambda invocations
2. **Input Validation**: Validate input data in your Lambda function for security
3. **Error Handling**: Implement proper error handling in Lambda functions for failed event processing
4. **Resource Naming**: Use descriptive names for CloudWatch Event rules for better management
5. **State Management**: Consider rule state (enabled/disabled) for deployment scenarios

## CloudFormation Template Structure

The module generates CloudFormation resources with the following structure:

```json
{
  "Resources": {
    "FunctionNameCloudWatchEvent1": {
      "Type": "AWS::Events::Rule",
      "Properties": {
        "EventPattern": {...},
        "State": "ENABLED",
        "Targets": [{
          "Arn": {"Fn::GetAtt": ["FunctionNameLambdaFunction", "Arn"]},
          "Id": "function-name-target"
        }]
      }
    },
    "FunctionNameCloudWatchEventPermission1": {
      "Type": "AWS::Lambda::Permission",
      "Properties": {
        "FunctionName": {"Fn::GetAtt": ["FunctionNameLambdaFunction", "Arn"]},
        "Action": "lambda:InvokeFunction",
        "Principal": "events.amazonaws.com",
        "SourceArn": {"Fn::GetAtt": ["FunctionNameCloudWatchEvent1", "Arn"]}
      }
    }
  }
}
```

This comprehensive structure ensures proper integration between CloudWatch Events and Lambda functions while maintaining security through appropriate IAM permissions.