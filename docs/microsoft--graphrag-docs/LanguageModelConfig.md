# LanguageModelConfig Module Documentation

## Introduction

The LanguageModelConfig module is a core configuration component in the GraphRAG system that manages language model settings and parameters. It provides a centralized configuration interface for various language model providers including OpenAI, Azure OpenAI, and other supported models. The module ensures proper validation of authentication credentials, API endpoints, and model-specific parameters while maintaining compatibility with the broader GraphRAG pipeline architecture.

## Architecture Overview

The LanguageModelConfig module serves as the configuration foundation for the [Language Model Abstraction](LanguageModelAbstraction.md) layer, providing validated settings that are consumed by model factories and managers throughout the system.

```mermaid
graph TB
    subgraph "Configuration Layer"
        LMC[LanguageModelConfig]
        GRC[GraphRagConfig]
        LMD[LanguageModelDefaults]
    end
    
    subgraph "Validation Layer"
        VE[Validation Errors]
        MV[Model Validator]
    end
    
    subgraph "Model Factory"
        MF[ModelFactory]
        CM[Chat Models]
        EM[Embedding Models]
    end
    
    subgraph "Language Model Abstraction"
        CMG[ChatModel Protocol]
        EMG[EmbeddingModel Protocol]
        MM[ModelManager]
    end
    
    LMC -->|provides config| MF
    LMC -->|validated by| MV
    MV -->|raises| VE
    MF -->|creates| CM
    MF -->|creates| EM
    CM -->|implements| CMG
    EM -->|implements| EMG
    CMG -->|managed by| MM
    EMG -->|managed by| MM
    GRC -->|contains| LMC
```

## Component Structure

### Core Configuration Class

The `LanguageModelConfig` class is a Pydantic BaseModel that encapsulates all language model configuration parameters with built-in validation logic.

```mermaid
classDiagram
    class LanguageModelConfig {
        +api_key: str|None
        +auth_type: AuthType
        +type: ModelType|str
        +model: str
        +encoding_model: str
        +api_base: str|None
        +api_version: str|None
        +deployment_name: str|None
        +organization: str|None
        +proxy: str|None
        +audience: str|None
        +model_supports_json: bool|None
        +request_timeout: float
        +tokens_per_minute: int|Literal["auto"]|None
        +requests_per_minute: int|Literal["auto"]|None
        +retry_strategy: str
        +max_retries: int
        +max_retry_wait: float
        +concurrent_requests: int
        +async_mode: AsyncType
        +responses: list[str|BaseModel]|None
        +max_tokens: int|None
        +temperature: float
        +max_completion_tokens: int|None
        +reasoning_effort: str|None
        +top_p: float
        +n: int
        +frequency_penalty: float
        +presence_penalty: float
        +_validate_api_key()
        +_validate_auth_type()
        +_validate_type()
        +_validate_encoding_model()
        +_validate_api_base()
        +_validate_api_version()
        +_validate_deployment_name()
        +_validate_tokens_per_minute()
        +_validate_requests_per_minute()
        +_validate_max_retries()
        +_validate_azure_settings()
        +_validate_model()
    }
```

## Configuration Parameters

### Authentication & Security

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `api_key` | `str \| None` | API key for LLM service | Required for API key auth |
| `auth_type` | `AuthType` | Authentication method | Validates against model type |
| `organization` | `str \| None` | Organization for LLM service | Optional |
| `audience` | `str \| None` | Azure resource URI for managed identity | Optional |

### Model Configuration

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `type` | `ModelType \| str` | LLM model type | Must be supported by ModelFactory |
| `model` | `str` | Specific LLM model name | Required |
| `encoding_model` | `str` | Token encoding model | Auto-derived if empty |
| `model_supports_json` | `bool \| None` | JSON output support | Optional |

### Azure OpenAI Specific

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `api_base` | `str \| None` | Azure OpenAI endpoint | Required for Azure models |
| `api_version` | `str \| None` | API version | Required for Azure models |
| `deployment_name` | `str \| None` | Deployment name | Required for Azure models |

### Rate Limiting & Performance

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `tokens_per_minute` | `int \| "auto" \| None` | Token rate limit | Must be positive if numeric |
| `requests_per_minute` | `int \| "auto" \| None` | Request rate limit | Must be positive if numeric |
| `concurrent_requests` | `int` | Concurrent request limit | Default from defaults |
| `request_timeout` | `float` | Request timeout | Default from defaults |

### Retry & Error Handling

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `retry_strategy` | `str` | Retry strategy | Default from defaults |
| `max_retries` | `int` | Maximum retry attempts | Must be ≥ 1 |
| `max_retry_wait` | `float` | Maximum retry wait time | Default from defaults |

### Generation Parameters

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `max_tokens` | `int \| None` | Maximum tokens to generate | Optional |
| `temperature` | `float` | Generation temperature | Default from defaults |
| `max_completion_tokens` | `int \| None` | Max completion tokens (incl. reasoning) | Optional |
| `reasoning_effort` | `str \| None` | Reasoning effort level | Optional |
| `top_p` | `float` | Top-p sampling | Default from defaults |
| `n` | `int` | Number of completions | Default from defaults |
| `frequency_penalty` | `float` | Frequency penalty | Default from defaults |
| `presence_penalty` | `float` | Presence penalty | Default from defaults |

### Advanced Settings

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `proxy` | `str \| None` | Proxy configuration | Optional |
| `async_mode` | `AsyncType` | Async operation mode | Default from defaults |
| `responses` | `list[str \| BaseModel] \| None` | Static responses for mock mode | Optional |

## Validation Logic

The configuration implements comprehensive validation through multiple validator methods:

```mermaid
flowchart TD
    Start[Configuration Creation] --> TypeValidation[Model Type Validation]
    TypeValidation --> AuthValidation[Authentication Type Validation]
    AuthValidation --> APIKeyValidation[API Key Validation]
    APIKeyValidation --> AzureValidation[Azure Settings Validation]
    AzureValidation --> RateLimitValidation[Rate Limit Validation]
    RateLimitValidation --> RetryValidation[Retry Settings Validation]
    RetryValidation --> EncodingValidation[Encoding Model Validation]
    EncodingValidation --> End[Validation Complete]
    
    TypeValidation -->|Invalid| TypeError[KeyError: Unsupported Model]
    AuthValidation -->|Invalid| AuthError[ConflictingSettingsError]
    APIKeyValidation -->|Invalid| APIError[ApiKeyMissingError]
    AzureValidation -->|Invalid| AzureError[Azure*MissingError]
    RateLimitValidation -->|Invalid| RateError[ValueError]
    RetryValidation -->|Invalid| RetryError[ValueError]
```

### Validation Rules

1. **Model Type Validation**: Ensures the model type is supported by the ModelFactory
2. **Authentication Validation**: Validates auth type compatibility with model type
3. **API Key Validation**: Ensures API key is provided when required
4. **Azure Settings Validation**: Validates required Azure-specific parameters
5. **Rate Limiting Validation**: Ensures rate limits are positive values
6. **Retry Settings Validation**: Validates retry configuration
7. **Encoding Model Validation**: Auto-derives encoding model if not specified

## Integration with GraphRAG System

The LanguageModelConfig module integrates with multiple components throughout the GraphRAG system:

```mermaid
graph LR
    subgraph "Configuration Management"
        LMC[LanguageModelConfig]
        GRC[GraphRagConfig]
        LCD[language_model_defaults]
    end
    
    subgraph "Model Factory"
        MF[ModelFactory]
        OCM[OpenAIChatFNLLM]
        OEM[OpenAIEmbeddingFNLLM]
    end
    
    subgraph "Pipeline Components"
        GE[GraphExtractor]
        CE[ClaimExtractor]
        CRE[CommunityReportsExtractor]
        SE[SummarizeExtractor]
    end
    
    subgraph "Query Engine"
        LS[LocalSearch]
        GS[GlobalSearch]
        DS[DRIFTSearch]
    end
    
    LMC -->|configures| MF
    MF -->|creates| OCM
    MF -->|creates| OEM
    OCM -->|used by| GE
    OCM -->|used by| CE
    OCM -->|used by| CRE
    OCM -->|used by| SE
    OCM -->|used by| LS
    OCM -->|used by| GS
    OCM -->|used by| DS
    GRC -->|contains| LMC
    LCD -->|provides defaults| LMC
```

## Error Handling

The module defines specific error types for different validation failures:

- **ApiKeyMissingError**: Raised when API key is required but not provided
- **AzureApiBaseMissingError**: Raised when Azure API base URL is missing
- **AzureApiVersionMissingError**: Raised when Azure API version is missing
- **AzureDeploymentNameMissingError**: Raised when Azure deployment name is missing
- **ConflictingSettingsError**: Raised when settings conflict (e.g., API key with managed identity)

## Usage Examples

### Basic OpenAI Configuration

```python
from graphrag.config.models.language_model_config import LanguageModelConfig
from graphrag.config.enums import ModelType, AuthType

config = LanguageModelConfig(
    type=ModelType.OpenAIChat,
    model="gpt-4",
    api_key="your-api-key",
    auth_type=AuthType.APIKey,
    max_tokens=4096,
    temperature=0.7
)
```

### Azure OpenAI Configuration

```python
config = LanguageModelConfig(
    type=ModelType.AzureOpenAIChat,
    model="gpt-4",
    auth_type=AuthType.APIKey,
    api_key="your-azure-key",
    api_base="https://your-resource.openai.azure.com/",
    api_version="2024-02-15-preview",
    deployment_name="gpt-4-deployment"
)
```

### Managed Identity Configuration

```python
config = LanguageModelConfig(
    type=ModelType.AzureOpenAIChat,
    model="gpt-4",
    auth_type=AuthType.AzureManagedIdentity,
    api_base="https://your-resource.openai.azure.com/",
    api_version="2024-02-15-preview",
    deployment_name="gpt-4-deployment",
    audience="https://cognitiveservices.azure.com/"
)
```

## Dependencies

The LanguageModelConfig module has the following key dependencies:

- **graphrag.config.defaults**: Provides default values for all configuration parameters
- **graphrag.config.enums**: Defines enumeration types (ModelType, AuthType, AsyncType)
- **graphrag.config.errors**: Defines custom exception types
- **graphrag.language_model.factory**: Validates model type support
- **tiktoken**: Handles token encoding model resolution

## Related Modules

- [GraphRagConfig](GraphRagConfig.md): Parent configuration container
- [LanguageModelAbstraction](LanguageModelAbstraction.md): Model implementation layer
- [ModelFactory](LanguageModelAbstraction.md#modelfactory): Model creation and validation
- [Pipeline Configuration](PipelineConfiguration.md): Pipeline-specific settings

## Best Practices

1. **Always validate configuration**: Use the built-in validation to catch configuration errors early
2. **Use appropriate auth types**: Match authentication type to your deployment model
3. **Set reasonable rate limits**: Configure tokens_per_minute and requests_per_minute based on your service tier
4. **Handle Azure-specific settings**: Ensure all required Azure parameters are provided when using Azure OpenAI
5. **Leverage defaults**: Use the provided defaults when possible to reduce configuration complexity
6. **Secure API keys**: Never hardcode API keys in configuration files; use environment variables or secure key management

## Configuration Validation Flow

```mermaid
sequenceDiagram
    participant App as Application
    participant LMC as LanguageModelConfig
    participant MF as ModelFactory
    participant Val as Validators
    
    App->>LMC: Create configuration
    LMC->>Val: Validate model type
    Val->>MF: Check model support
    MF-->>Val: Model supported
    Val->>LMC: Type validation passed
    
    LMC->>Val: Validate auth type
    Val->>Val: Check auth compatibility
    Val->>LMC: Auth validation passed
    
    LMC->>Val: Validate API key
    Val->>Val: Check auth requirements
    Val->>LMC: API key validation passed
    
    LMC->>Val: Validate Azure settings
    Val->>Val: Check required fields
    Val->>LMC: Azure validation passed
    
    LMC->>Val: Validate rate limits
    Val->>LMC: Rate limit validation passed
    
    LMC->>App: Return validated config
```