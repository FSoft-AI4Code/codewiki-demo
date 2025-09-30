# Training Orchestration Module

## Introduction

The training_orchestration module serves as the central coordination hub for training Rasa models. It provides high-level training functions that orchestrate the entire model training pipeline, handling both NLU (Natural Language Understanding) and Core (dialogue management) components. The module abstracts the complexity of the underlying training framework while providing flexible training options including full training, incremental training, and dry-run capabilities.

## Architecture Overview

The training orchestration module implements a layered architecture that coordinates between data importers, training frameworks, and model storage systems:

```mermaid
graph TB
    subgraph "Training Orchestration Layer"
        A[rasa.model_training.train]
        B[rasa.model_training.train_core]
        C[rasa.model_training.train_nlu]
        D[rasa.model_training._train_graph]
    end

    subgraph "Data Import Layer"
        E[rasa.shared.importers.importer.TrainingDataImporter]
        F[rasa.shared.core.domain.Domain]
        G[rasa.shared.core.training_data.structures.StoryGraph]
        H[rasa.shared.nlu.training_data.training_data.TrainingData]
    end

    subgraph "Training Framework Layer"
        I[rasa.engine.training.graph_trainer.GraphTrainer]
        J[rasa.engine.recipes.recipe.Recipe]
        K[rasa.engine.graph.GraphSchema]
    end

    subgraph "Storage & Execution Layer"
        L[rasa.engine.storage.storage.ModelStorage]
        M[rasa.engine.runner.dask.DaskGraphRunner]
        N[rasa.engine.caching.LocalTrainingCache]
    end

    A --> E
    A --> F
    A --> G
    A --> H
    A --> D
    B --> E
    B --> D
    C --> E
    C --> D
    D --> I
    D --> J
    D --> K
    D --> L
    I --> M
    I --> N
    L --> M
```

## Core Components

### Main Training Functions

#### `train()` - Unified Training Function
The primary entry point for training complete Rasa models that combines both NLU and Core training:

```mermaid
sequenceDiagram
    participant User
    participant train
    participant TrainingDataImporter
    participant _train_graph
    participant GraphTrainer
    participant ModelStorage

    User->>train: Provide domain, config, training files
    train->>TrainingDataImporter: Load training data
    TrainingDataImporter->>train: Return stories, NLU data, domain
    train->>train: Validate data and determine training type
    train->_train_graph: Delegate to graph trainer
    _train_graph->>GraphTrainer: Create trainer instance
    GraphTrainer->>ModelStorage: Initialize storage
    GraphTrainer->>GraphTrainer: Execute training pipeline
    GraphTrainer->>User: Return trained model
```

**Key Responsibilities:**
- Data validation and training type determination (BOTH, NLU, CORE, END_TO_END)
- Unresolved slot detection and validation
- Telemetry tracking for model training
- Delegation to the graph-based training framework

#### `train_core()` - Core-Specific Training
Specialized function for training dialogue management models:

- Validates Core-specific requirements (domain, stories)
- Ensures no e2e stories are present when training Core only
- Delegates to `_train_graph()` with `TrainingType.CORE`

#### `train_nlu()` - NLU-Specific Training
Dedicated function for training Natural Language Understanding models:

- Validates NLU data presence and format
- Supports optional domain integration
- Delegates to `_train_graph()` with `TrainingType.NLU`

### Graph-Based Training Engine

#### `_train_graph()` - Core Training Orchestrator
The central function that coordinates the graph-based training process:

```mermaid
flowchart TD
    A[Start _train_graph] --> B{Is finetuning?}
    B -->|Yes| C[Load model for finetuning]
    B -->|No| D[Create new model storage]
    C --> E[Get recipe configuration]
    D --> E
    E --> F[Generate graph configuration]
    F --> G[Validate model configuration]
    G --> H{Is dry run?}
    H -->|Yes| I[Run fingerprinting only]
    H -->|No| J[Create GraphTrainer]
    J --> K[Execute training pipeline]
    K --> L[Save trained model]
    I --> M[Return dry run results]
    L --> N[Return training result]
```

**Key Features:**
- Recipe-based configuration management
- Model fingerprinting for incremental training
- Support for finetuning existing models
- Integration with Dask-based parallel execution
- Comprehensive validation and error handling

## Data Flow Architecture

### Training Data Flow

```mermaid
graph LR
    subgraph "Input Sources"
        A[Domain File]
        B[Config File]
        C[Training Data Files]
    end

    subgraph "Data Import & Validation"
        D[TrainingDataImporter]
        E[Data Validation]
        F[Training Type Detection]
    end

    subgraph "Training Pipeline"
        G[Recipe Configuration]
        H[Graph Schema Generation]
        I[Component Training]
    end

    subgraph "Output"
        J[Trained Model]
        K[Training Metrics]
        L[Fingerprint Data]
    end

    A --> D
    B --> D
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    H --> I
    I --> J
    I --> K
    I --> L
```

### Training Type Determination Logic

The module automatically determines the appropriate training type based on data availability:

```mermaid
flowchart TD
    A[Load Training Data] --> B{Has Stories?}
    B -->|No| C{Has NLU Data?}
    B -->|Yes| D{Has NLU Data?}
    C -->|No| E[Error: No training data]
    C -->|Yes| F[TrainingType.NLU]
    D -->|No| G[TrainingType.CORE]
    D -->|Yes| H{Has e2e examples?}
    H -->|Yes| I[TrainingType.END_TO_END]
    H -->|No| J[TrainingType.BOTH]
```

## Integration Points

### Dependencies on Other Modules

The training orchestration module integrates with several key Rasa modules:

#### [engine_graph](engine_graph.md) Integration
- **GraphTrainer**: Executes the training pipeline using graph-based execution
- **Recipe System**: Provides configuration management and graph schema generation
- **ModelStorage**: Handles model persistence and finetuning capabilities
- **GraphRunner**: Enables parallel execution of training components

#### [data_importers](data_importers.md) Integration
- **TrainingDataImporter**: Loads and validates training data from various sources
- **Multi-project support**: Handles complex project structures and data aggregation

#### [shared_core](shared_core.md) Integration
- **Domain**: Validates domain configuration and slot definitions
- **StoryGraph**: Processes dialogue training data and detects unresolved slots
- **TrainingType**: Determines appropriate training strategy based on data composition

#### [shared_nlu](shared_nlu.md) Integration
- **TrainingData**: Processes NLU training examples and validates data format
- **Message**: Handles individual training examples and features

### External Dependencies

```mermaid
graph TB
    A[training_orchestration] --> B[engine_graph]
    A --> C[data_importers]
    A --> D[shared_core]
    A --> E[shared_nlu]
    A --> F[telemetry]
    A --> G[utils]
    
    B --> H[graph_trainer]
    B --> I[recipe_system]
    B --> J[storage_layer]
    
    C --> K[rasa_file_importer]
    C --> L[multi_project_importer]
    
    D --> M[domain]
    D --> N[events]
    D --> O[training_data_structures]
    
    E --> P[training_data]
    E --> Q[message]
```

## Key Features and Capabilities

### 1. Flexible Training Modes
- **Full Training**: Complete model training from scratch
- **Incremental Training**: Finetuning existing models with new data
- **Dry Run**: Validation and fingerprinting without actual training
- **Forced Training**: Override fingerprint checks and force retraining

### 2. Intelligent Data Validation
- **Slot Validation**: Detects unresolved slots in stories
- **Data Type Detection**: Automatically determines training requirements
- **Format Validation**: Ensures data compatibility with training pipeline

### 3. Advanced Training Features
- **End-to-End Training**: Supports combined NLU and Core training with e2e examples
- **Recipe-Based Configuration**: Flexible configuration management through recipes
- **Parallel Execution**: Dask-based parallel training for improved performance
- **Model Fingerprinting**: Efficient change detection for incremental training

### 4. Error Handling and Validation
- **Comprehensive Validation**: Multi-layer validation of inputs and configurations
- **Graceful Degradation**: Handles missing data and configuration issues
- **User-Friendly Messages**: Clear error messages and warnings

## Training Process Flow

### Complete Training Pipeline

```mermaid
sequenceDiagram
    participant User
    participant train_function
    participant data_importer
    participant validator
    participant graph_trainer
    participant model_storage
    participant output

    User->>train_function: Call train() with parameters
    train_function->>data_importer: Load training data
    data_importer-->>train_function: Return imported data
    train_function->>validator: Validate data integrity
    validator-->>train_function: Validation results
    
    alt Validation Failed
        train_function-->>User: Return error with message
    else Validation Passed
        train_function->>graph_trainer: Create trainer instance
        graph_trainer->>model_storage: Initialize storage
        graph_trainer->>graph_trainer: Execute training
        graph_trainer-->>train_function: Training completed
        train_function-->>output: Save model to path
        train_function-->>User: Return TrainingResult
    end
```

### Error Handling Flow

```mermaid
flowchart TD
    A[Training Request] --> B{Data Validation}
    B -->|Invalid| C[Check Data Type]
    C --> D[Generate Specific Error]
    D --> E[Return Error Code]
    
    B -->|Valid| F{Configuration Check}
    F -->|Invalid| G[Configuration Error]
    G --> E
    
    F -->|Valid| H{Resource Check}
    H -->|Failed| I[Resource Error]
    I --> E
    
    H -->|Success| J[Proceed with Training]
    J --> K{Training Result}
    K -->|Success| L[Return Success]
    K -->|Failure| M[Training Error]
    M --> E
```

## Configuration and Customization

### Training Parameters
The module supports extensive customization through training parameters:

- **Model Naming**: Custom model names with automatic timestamping
- **Output Paths**: Configurable model storage locations
- **Additional Arguments**: Component-specific training parameters
- **Finetuning Options**: Epoch fractions and model selection

### Recipe Integration
Training orchestration leverages the recipe system for flexible configuration:

```mermaid
graph LR
    A[Training Request] --> B[Recipe Selection]
    B --> C[Configuration Validation]
    C --> D[Graph Schema Generation]
    D --> E[Component Configuration]
    E --> F[Training Execution]
```

## Performance Considerations

### Optimization Strategies
1. **Fingerprinting**: Avoids unnecessary retraining of unchanged components
2. **Caching**: Local training cache for intermediate results
3. **Parallel Execution**: Dask-based distributed training
4. **Incremental Training**: Efficient finetuning capabilities

### Resource Management
- Temporary directory management for intermediate files
- Memory-efficient data processing
- Configurable parallel execution parameters
- Model storage optimization

## Monitoring and Telemetry

The module integrates with Rasa's telemetry system to track:
- Training duration and success rates
- Model performance metrics
- Component usage statistics
- Error patterns and frequencies

## Best Practices

### Training Workflow
1. **Data Preparation**: Ensure clean, validated training data
2. **Configuration Review**: Verify recipe and component configurations
3. **Dry Run Execution**: Use dry-run mode for validation before full training
4. **Incremental Training**: Leverage finetuning for model updates
5. **Monitoring**: Track training progress and resource usage

### Error Prevention
- Validate domain-slot consistency before training
- Use appropriate training types for data composition
- Monitor resource availability and constraints
- Implement proper error handling in calling code

This comprehensive orchestration system provides a robust foundation for training Rasa models while maintaining flexibility and extensibility for diverse use cases and deployment scenarios.