# TED Policy Module Documentation

## Overview

The TED (Transformer Embedding Dialogue) Policy is a sophisticated machine learning-based dialogue policy in Rasa that uses transformer architectures to predict the next best action in conversational AI systems. It represents a significant advancement in dialogue management by leveraging transformer embeddings and similarity-based learning approaches.

## Purpose and Core Functionality

The TED Policy serves as the primary neural dialogue policy in Rasa, designed to:

- Predict the next best action based on the current dialogue context
- Handle both intent-based and end-to-end (text-based) predictions
- Perform entity recognition within the same model architecture
- Learn from dialogue patterns using transformer-based embeddings
- Support both training from scratch and fine-tuning of pre-trained models

## Architecture Overview

### Core Components

```mermaid
graph TB
    subgraph "TED Policy Architecture"
        A[TEDPolicy] --> B[TED Model]
        A --> C[Tracker Featurizer]
        A --> D[Model Storage]
        B --> E[Transformer Layers]
        B --> F[Embedding Layers]
        B --> G[Similarity Computation]
        B --> H[Entity Recognition]
    end
    
    subgraph "Input Processing"
        I[Dialogue State] --> C
        J[Domain] --> C
        K[Precomputed Features] --> C
    end
    
    subgraph "Output"
        G --> L[Action Probabilities]
        H --> M[Entity Predictions]
    end
```

### Model Architecture Flow

```mermaid
sequenceDiagram
    participant User
    participant Tracker
    participant TEDPolicy
    participant Featurizer
    participant TEDModel
    participant Output
    
    User->>Tracker: Utterance/Action
    Tracker->>TEDPolicy: Dialogue State
    TEDPolicy->>Featurizer: Featurize Tracker
    Featurizer->>TEDPolicy: Feature Vectors
    TEDPolicy->>TEDModel: Model Data
    TEDModel->>TEDModel: Transformer Encoding
    TEDModel->>TEDModel: Similarity Computation
    TEDModel->>TEDPolicy: Predictions
    TEDPolicy->>Output: Action Probabilities
    TEDPolicy->>Output: Entity Predictions
```

## Detailed Component Architecture

### TEDPolicy Class

The main policy class that orchestrates the entire prediction pipeline:

```mermaid
classDiagram
    class TEDPolicy {
        -model: TED
        -featurizer: TrackerFeaturizer
        -config: Dict
        -entity_tag_specs: List[EntityTagSpec]
        -fake_features: Dict
        -label_data: RasaModelData
        +train()
        +predict_action_probabilities()
        +_create_model_data()
        +_prepare_for_training()
        +persist()
        +load()
    }
```

### TED Model Architecture

The neural network model implementing the transformer-based approach:

```mermaid
graph LR
    subgraph "Input Features"
        A[User Input] --> B[Intent/Text]
        C[Previous Actions] --> D[Action Name/Text]
        E[Context] --> F[Slots/Active Loop]
    end
    
    subgraph "Encoding Layers"
        B --> G[Embedding Layer]
        D --> H[Embedding Layer]
        F --> I[Embedding Layer]
    end
    
    subgraph "Transformer"
        G --> J[Concatenation]
        H --> J
        I --> J
        J --> K[Dialogue Transformer]
    end
    
    subgraph "Output"
        K --> L[Dialogue Embedding]
        M[Label Embeddings] --> N[Similarity Computation]
        L --> N
        N --> O[Action Probabilities]
    end
```

## Data Flow and Processing

### Training Data Flow

```mermaid
flowchart TD
    A[Training Trackers] --> B[Featurization]
    B --> C[Feature Extraction]
    C --> D[Model Data Creation]
    D --> E[Label Data Creation]
    E --> F[Batch Generation]
    F --> G[Model Training]
    
    subgraph "Feature Types"
        H[Intent Features]
        I[Text Features]
        J[Action Features]
        K[Entity Features]
        L[Slot Features]
        M[Active Loop Features]
    end
    
    C --> H
    C --> I
    C --> J
    C --> K
    C --> L
    C --> M
```

### Prediction Data Flow

```mermaid
flowchart LR
    A[Current Tracker] --> B[Featurize Tracker]
    B --> C[Create Model Data]
    C --> D[Model Inference]
    D --> E[Similarity Computation]
    E --> F[Confidence Scores]
    F --> G[Action Selection]
    
    subgraph "Entity Recognition"
        D --> H[Entity Layer]
        H --> I[Entity Predictions]
    end
```

## Key Features and Capabilities

### 1. Dual Input Support
- **Intent-based**: Uses NLU intent classification results
- **End-to-end**: Directly processes user text without intent classification
- **Hybrid approach**: Combines both methods with confidence-based selection

### 2. Entity Recognition
- Integrated entity extraction within the same model
- Supports BILOU tagging scheme
- Context-aware entity prediction using dialogue history

### 3. Transformer Architecture
- Multi-head attention mechanisms
- Configurable transformer layers and sizes
- Support for relative position embeddings

### 4. Similarity-based Learning
- StarSpace-inspired similarity computation
- Configurable similarity metrics (cosine, inner product)
- Margin-based and cross-entropy loss functions

## Configuration and Parameters

### Architecture Parameters
```yaml
# Transformer Configuration
transformer_size:
  text: 128
  action_text: 128
  dialogue: 128
num_transformer_layers:
  dialogue: 1
num_heads: 4

# Embedding Configuration
encoding_dimension: 50
embedding_dimension: 20

# Feature Processing
hidden_layers_sizes:
  text: []
  action_text: []
dense_dimension:
  text: 128
  intent: 20
```

### Training Parameters
```yaml
# Training Configuration
batch_sizes: [64, 256]
batch_strategy: "balanced"
epochs: 1
learning_rate: 0.001

# Loss Configuration
loss_type: "cross_entropy"
similarity_type: "auto"
num_neg: 20
max_pos_sim: 0.8
max_neg_sim: -0.2
```

### Entity Recognition
```yaml
# Entity Configuration
entity_recognition: true
bilou_flag: true
split_entities_by_comma: true
```

## Integration with Rasa Core

### Policy Ensemble Integration

```mermaid
graph TB
    subgraph "Policy Ensemble"
        A[PolicyPredictionEnsemble] --> B[TEDPolicy]
        A --> C[RulePolicy]
        A --> D[MemoizationPolicy]
        
        B --> E[PolicyPrediction]
        C --> E
        D --> E
        
        E --> F[Final Prediction]
    end
    
    subgraph "Data Flow"
        G[DialogueStateTracker] --> B
        H[Domain] --> B
        I[Precomputations] --> B
    end
```

### Message Processing Pipeline

```mermaid
sequenceDiagram
    participant MessageProcessor
    participant Agent
    participant PolicyEnsemble
    participant TEDPolicy
    
    MessageProcessor->>Agent: Process User Message
    Agent->>PolicyEnsemble: Predict Next Action
    PolicyEnsemble->>TEDPolicy: Get Prediction
    TEDPolicy->>TEDPolicy: Featurize Tracker
    TEDPolicy->>TEDPolicy: Model Inference
    TEDPolicy->>PolicyEnsemble: Return Probabilities
    PolicyEnsemble->>Agent: Combined Prediction
    Agent->>MessageProcessor: Execute Action
```

## Model Persistence and Loading

### Persistence Process
```mermaid
flowchart TD
    A[Trained Model] --> B[Serialize Model Weights]
    B --> C[Save Configuration]
    C --> D[Save Feature Examples]
    D --> E[Save Label Data]
    E --> F[Save Entity Specs]
    F --> G[Model Storage]
```

### Loading Process
```mermaid
flowchart LR
    A[Model Storage] --> B[Load Configuration]
    B --> C[Load Model Weights]
    C --> D[Load Feature Examples]
    D --> E[Initialize Model]
    E --> F[Ready for Prediction]
```

## Advanced Features

### 1. Confidence Calibration
- Configurable confidence computation methods
- Support for confidence renormalization
- Threshold-based end-to-end prediction selection

### 2. Attention Mechanisms
- Diagnostic attention weight extraction
- Configurable attention dropout
- Support for relative position attention

### 3. Regularization Techniques
- Dropout at multiple levels (input, attention, dialogue)
- Connection density control
- Regularization constants for loss functions

### 4. Evaluation and Monitoring
- Built-in validation during training
- TensorBoard integration
- Model checkpointing support

## Dependencies and Interactions

### Core Dependencies
- **Policy Framework**: Inherits from base Policy class ([policy.md](policy.md))
- **Featurizers**: Uses TrackerFeaturizer for feature extraction ([tracker_featurizers.md](tracker_featurizers.md))
- **Model Storage**: Integrates with Rasa's model persistence system ([model_storage.md](model_storage.md))
- **TensorFlow**: Built on TensorFlow for neural network operations

### Related Components
- **MessageProcessor**: Processes incoming messages ([message_processor.md](message_processor.md))
- **DialogueStateTracker**: Maintains conversation state ([dialogue_state_tracker.md](dialogue_state_tracker.md))
- **Domain**: Defines assistant capabilities ([domain.md](domain.md))
- **PolicyEnsemble**: Combines multiple policy predictions ([policy_ensemble.md](policy_ensemble.md))

## Performance Considerations

### Memory Management
- Efficient batch processing
- Configurable batch sizes
- Memory-efficient feature handling

### Computational Optimization
- GPU support with configurable device placement
- Efficient tensor operations
- Optimized similarity computations

### Scalability
- Support for large action spaces
- Configurable ranking length
- Efficient label embedding management

## Error Handling and Robustness

### Training Robustness
- Graceful handling of empty training data
- Validation of configuration parameters
- Automatic parameter updates for compatibility

### Prediction Robustness
- Fallback mechanisms for model failures
- Handling of missing features
- Confidence-based decision making

## Future Enhancements and Extensibility

### Architecture Flexibility
- Modular layer design for easy extension
- Configurable model components
- Support for custom similarity functions

### Training Improvements
- Advanced loss functions
- Multi-task learning capabilities
- Transfer learning support

### Integration Enhancements
- Better integration with NLU components
- Enhanced end-to-end capabilities
- Improved entity recognition accuracy

## Conclusion

The TED Policy represents a state-of-the-art approach to dialogue management in Rasa, combining the power of transformer architectures with practical conversational AI requirements. Its flexible design, comprehensive feature set, and robust implementation make it suitable for a wide range of conversational AI applications, from simple task-oriented bots to complex, multi-domain assistants.

The policy's ability to handle both intent-based and end-to-end predictions, combined with integrated entity recognition and sophisticated similarity-based learning, positions it as a cornerstone of modern conversational AI systems built with Rasa.