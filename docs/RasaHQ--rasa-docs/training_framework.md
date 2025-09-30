# Training Framework Module

## Introduction

The Training Framework module is the core training orchestration system in Rasa's engine architecture. It provides intelligent model training capabilities through a graph-based execution system that optimizes training performance using fingerprinting and caching mechanisms. The framework enables efficient retraining by identifying which components need to be retrained based on changes in data or configuration.

## Architecture Overview

The Training Framework serves as the central training coordinator in the Rasa engine graph system, working closely with the [engine_graph](engine_graph.md) module to execute training workflows efficiently.

```mermaid
graph TB
    subgraph "Training Framework"
        GT[GraphTrainer]
        TC[TrainingCache]
        MS[ModelStorage]
        GR[GraphRunner]
        TH[TrainingHook]
        LH[LoggingHook]
        FC[FingerprintComponent]
        PVP[PrecomputedValueProvider]
    end
    
    subgraph "Engine Graph Dependencies"
        GS[GraphSchema]
        GMC[GraphModelConfiguration]
        EC[ExecutionContext]
    end
    
    subgraph "Data Layer"
        TDI[TrainingDataImporter]
        DOM[Domain]
    end
    
    GT --> TC
    GT --> MS
    GT --> GR
    GT --> FC
    GT --> PVP
    
    GR --> GS
    GR --> GMC
    GR --> EC
    
    GT --> TDI
    GT --> DOM
    
    TH --> TC
    TH --> MS
    LH --> GT
```

## Core Components

### GraphTrainer

The `GraphTrainer` class is the central orchestrator for model training in Rasa. It coordinates the entire training pipeline from data ingestion to model packaging, utilizing intelligent caching and fingerprinting to optimize performance.

**Key Responsibilities:**
- Orchestrate the complete training pipeline
- Implement fingerprint-based change detection
- Manage training cache for performance optimization
- Coordinate graph execution through GraphRunner
- Package trained models for deployment

**Training Workflow:**

```mermaid
sequenceDiagram
    participant Client
    participant GraphTrainer
    participant FingerprintComponent
    participant GraphRunner
    participant TrainingCache
    participant ModelStorage
    
    Client->>GraphTrainer: train(model_config, importer, output_path)
    GraphTrainer->>GraphTrainer: Deep copy domain
    
    alt Force Retraining
        GraphTrainer->>GraphTrainer: Use full training schema
    else Normal Training
        GraphTrainer->>GraphTrainer: fingerprint()
        GraphTrainer->>FingerprintComponent: Create fingerprint schema
        GraphTrainer->>GraphRunner: Run fingerprint graph
        GraphRunner->>TrainingCache: Check fingerprints
        GraphRunner-->>GraphTrainer: Fingerprint results
        GraphTrainer->>GraphTrainer: _prune_schema()
    end
    
    GraphTrainer->>GraphTrainer: Create training hooks
    GraphTrainer->>GraphRunner: Create runner with pruned schema
    GraphTrainer->>GraphRunner: Run training graph
    GraphRunner->>TrainingCache: Cache results
    GraphRunner->>ModelStorage: Store components
    GraphTrainer->>ModelStorage: create_model_package()
    ModelStorage-->>Client: ModelMetadata
```

## Training Optimization Strategy

### Fingerprinting System

The framework implements a sophisticated fingerprinting mechanism to determine which components need retraining:

```mermaid
graph LR
    subgraph "Fingerprint Process"
        A[Input Data] --> B[Fingerprint Component]
        B --> C{Cache Hit?}
        C -->|Yes| D[Use Cached Output]
        C -->|No| E[Mark for Retraining]
        D --> F[PrecomputedValueProvider]
        E --> G[Keep in Schema]
    end
    
    subgraph "Schema Pruning"
        G --> H[Pruned Schema]
        F --> H
        H --> I[Minimal Graph]
    end
```

### Cache Management

The training framework leverages multiple caching strategies:

1. **Fingerprint Cache**: Stores component fingerprints to detect changes
2. **Output Cache**: Caches component outputs for reuse
3. **Model Storage**: Persistent storage for trained components

```mermaid
graph TB
    subgraph "Cache Layers"
        FC[Fingerprint Cache]
        OC[Output Cache]
        MS[Model Storage]
    end
    
    subgraph "Training Flow"
        GT[GraphTrainer]
        FC --> GT
        GT --> OC
        OC --> MS
        MS --> GT
    end
    
    subgraph "Cache Keys"
        FK[Fingerprint Keys]
        OK[Output Keys]
        MK[Model Keys]
    end
    
    FK --> FC
    OK --> OC
    MK --> MS
```

## Component Interactions

### Training Hook System

The framework implements a hook system to monitor and manage training execution:

```mermaid
graph LR
    subgraph "Hook Architecture"
        TH[TrainingHook]
        LH[LoggingHook]
        GR[GraphRunner]
    end
    
    subgraph "Hook Responsibilities"
        TH --> Cache[Manage Cache]
        TH --> Storage[Handle Storage]
        TH --> Schema[Process Schema]
        LH --> Log[Log Progress]
        LH --> Debug[Debug Info]
    end
    
    GR --> TH
    GR --> LH
```

### Graph Execution Flow

The training process follows a structured graph execution pattern:

```mermaid
graph TD
    Start[Training Start] --> Config[Load Configuration]
    Config --> Import[Import Training Data]
    Import --> Fingerprint{Fingerprint Check}
    
    Fingerprint -->|Changes Detected| Prune[Prune Schema]
    Fingerprint -->|No Changes| Cache[Use Cache]
    
    Prune --> Execute[Execute Graph]
    Cache --> Execute
    
    Execute --> Package[Package Model]
    Package --> End[Training Complete]
```

## Integration with Engine Graph

The Training Framework is deeply integrated with the [engine_graph](engine_graph.md) system:

### Graph Schema Management
- **GraphSchema**: Defines the training pipeline structure
- **GraphModelConfiguration**: Contains training and prediction schemas
- **ExecutionContext**: Provides runtime context for graph execution

### Component Lifecycle
- **GraphComponent**: Base class for all trainable components
- **GraphNode**: Individual nodes in the training graph
- **GraphRunner**: Executes the training graph

## Data Flow Architecture

```mermaid
graph TB
    subgraph "Input Data Flow"
        TDI[TrainingDataImporter] --> TD[Training Data]
        TD --> MSG[Message Processing]
        TD --> SG[Story Graph]
        TD --> DOM[Domain]
    end
    
    subgraph "Training Pipeline"
        MSG --> NLU[NLU Components]
        SG --> Core[Core Components]
        DOM --> Both[Both Systems]
        
        NLU --> Cache1[Cache Results]
        Core --> Cache2[Cache Results]
        Both --> Cache3[Cache Results]
    end
    
    subgraph "Output Generation"
        Cache1 --> Package[Model Package]
        Cache2 --> Package
        Cache3 --> Package
        Package --> Metadata[ModelMetadata]
    end
```

## Performance Optimization

### Intelligent Retraining

The framework minimizes unnecessary retraining through:

1. **Change Detection**: Fingerprinting identifies exactly what changed
2. **Dependency Analysis**: Only retrain affected components
3. **Cache Reuse**: Maximize use of previously computed results
4. **Graph Pruning**: Remove unnecessary nodes from execution

### Memory Management

```mermaid
graph LR
    subgraph "Memory Optimization"
        IM[Input Management]
        CM[Cache Management]
        GM[Garbage Collection]
    end
    
    subgraph "Strategies"
        IM --> Streaming[Streaming Data]
        CM --> LRU[LRU Cache]
        GM --> Cleanup[Cleanup Unused]
    end
```

## Error Handling and Recovery

The training framework implements robust error handling:

- **Validation**: Pre-training validation of schemas and data
- **Graceful Degradation**: Continue training even if some components fail
- **Recovery**: Rollback mechanisms for failed training runs
- **Logging**: Comprehensive logging for debugging and monitoring

## Dependencies

The Training Framework relies on several key modules:

- **[engine_graph](engine_graph.md)**: Core graph execution engine
- **[shared_core](shared_core.md)**: Core domain and event structures
- **[data_importers](data_importers.md)**: Training data ingestion
- **[storage_persistence](storage_persistence.md)**: Model and tracker storage

## Usage Patterns

### Basic Training
```python
trainer = GraphTrainer(model_storage, cache, graph_runner_class)
metadata = trainer.train(
    model_configuration=config,
    importer=training_data_importer,
    output_filename=output_path
)
```

### Fine-tuning
```python
metadata = trainer.train(
    model_configuration=config,
    importer=training_data_importer,
    output_filename=output_path,
    is_finetuning=True
)
```

### Force Retraining
```python
metadata = trainer.train(
    model_configuration=config,
    importer=training_data_importer,
    output_filename=output_path,
    force_retraining=True
)
```

## Best Practices

1. **Cache Management**: Regular cache cleanup to prevent storage bloat
2. **Fingerprinting**: Ensure component fingerprints are deterministic
3. **Schema Design**: Optimize graph schemas for parallel execution
4. **Error Handling**: Implement proper error handling in custom components
5. **Monitoring**: Use logging hooks for training monitoring and debugging

## Future Enhancements

The Training Framework is designed to support:

- **Distributed Training**: Multi-node training capabilities
- **Incremental Learning**: Online learning and model updates
- **Advanced Caching**: Machine learning-based cache prediction
- **Performance Analytics**: Detailed training performance metrics