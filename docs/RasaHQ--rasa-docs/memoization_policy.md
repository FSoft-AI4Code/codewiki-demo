# Memoization Policy Module

## Introduction

The memoization_policy module implements deterministic dialogue management policies that memorize and recall exact conversation patterns from training data. It provides two main implementations: `MemoizationPolicy` for exact pattern matching and `AugmentedMemoizationPolicy` for enhanced recall with progressive truncation capabilities.

This module is part of Rasa's policy framework and serves as a high-precision, low-recall component that ensures predictable behavior for known conversation flows while working in conjunction with other policies in the ensemble.

## Architecture Overview

```mermaid
graph TB
    subgraph "Memoization Policy Module"
        MP[MemoizationPolicy]
        AMP[AugmentedMemoizationPolicy]
        
        MP --> |inherits from| Policy[Policy Base Class]
        AMP --> |inherits from| MP
        
        MP --> |uses| Featurizer[TrackerFeaturizer]
        MP --> |creates| Lookup[Lookup Dictionary]
        MP --> |manages| States[State Representations]
        
        AMP --> |extends| Recall[Enhanced Recall Mechanism]
        AMP --> |implements| Truncation[Progressive Truncation]
    end
    
    subgraph "External Dependencies"
        Policy --> |part of| PolicyFramework[Policy Framework]
        Featurizer --> |from| FeaturizerModule[Tracker Featurizers]
        States --> |from| Domain[Domain Module]
        States --> |from| Tracker[DialogueStateTracker]
    end
    
    style MP fill:#e1f5fe
    style AMP fill:#e1f5fe
```

## Core Components

### MemoizationPolicy

The base memoization policy that memorizes exact conversation patterns from training stories. It creates a lookup dictionary mapping state sequences to actions, enabling deterministic prediction for previously seen dialogue flows.

**Key Characteristics:**
- **Precision-focused**: Achieves 100% precision on memorized patterns
- **Deterministic**: Returns probability of 1.0 for matched actions
- **Max history-based**: Considers only the last N turns (configurable)
- **State compression**: Optional compression of state representations

**Configuration Parameters:**
```python
{
    "enable_feature_string_compression": True,  # Compress state keys
    "use_nlu_confidence_as_score": False,       # Use NLU confidence as action score
    POLICY_PRIORITY: MEMOIZATION_POLICY_PRIORITY, # Priority in ensemble
    POLICY_MAX_HISTORY: DEFAULT_MAX_HISTORY,    # Number of turns to consider
}
```

### AugmentedMemoizationPolicy

An enhanced version that extends the base memoization policy with progressive truncation capabilities. It can recall actions even when the current dialogue state doesn't exactly match memorized patterns by progressively removing older events.

**Key Enhancement:**
- **Progressive truncation**: Iteratively removes oldest events to find matches
- **Back-to-the-future approach**: Modifies dialogue history to find memorized patterns
- **Fallback mechanism**: Falls back to truncation when exact recall fails

## Data Flow and Processing

```mermaid
sequenceDiagram
    participant Trainer as Training System
    participant MP as MemoizationPolicy
    participant Featurizer as TrackerFeaturizer
    participant Lookup as Lookup Dictionary
    participant Predictor as Prediction System
    
    Trainer->>MP: train(training_trackers, domain)
    MP->>Featurizer: training_states_and_labels()
    Featurizer-->>MP: states, actions
    MP->>MP: _create_lookup_from_states()
    MP->>Lookup: store state-action mappings
    MP->>MP: persist()
    
    Predictor->>MP: predict_action_probabilities()
    MP->>MP: _prediction_states()
    MP->>Lookup: recall(states)
    alt Match Found
        Lookup-->>MP: action_name
        MP->>MP: _prediction_result()
        MP-->>Predictor: PolicyPrediction with probability 1.0
    else No Match
        Lookup-->>MP: None
        MP-->>Predictor: default predictions
    end
```

## Training Process

```mermaid
flowchart TD
    A[Training Data] --> B[Filter Original Trackers]
    B --> C[Extract States and Actions]
    C --> D[Create Feature Keys]
    D --> E{Key Exists?}
    E -->|No| F[Add to Lookup]
    E -->|Yes| G{Same Action?}
    G -->|Yes| H[Keep Existing]
    G -->|No| I[Remove Ambiguous Key]
    F --> J[Continue Processing]
    H --> J
    I --> J
    J --> K{More Examples?}
    K -->|Yes| D
    K -->|No| L[Persist Lookup]
    
    style A fill:#c8e6c9
    style L fill:#c8e6c9
```

## Prediction Process

```mermaid
flowchart TD
    A[Current Tracker] --> B[Extract States]
    B --> C[Create Feature Key]
    C --> D[Lookup Action]
    D --> E{Match Found?}
    E -->|Yes| F[Return Action with Probability 1.0]
    E -->|No| G{Is Augmented?}
    G -->|Yes| H[Try Progressive Truncation]
    H --> I{Match Found?}
    I -->|Yes| F
    I -->|No| J[Return Default Predictions]
    G -->|No| J
    
    style F fill:#c8e6c9
    style J fill:#ffcdd2
```

## Progressive Truncation Algorithm

The AugmentedMemoizationPolicy implements a sophisticated fallback mechanism:

```mermaid
flowchart LR
    A[Original States] --> B[Exact Recall]
    B -->|Success| C[Return Action]
    B -->|Failure| D[Truncate Tracker]
    D --> E[Remove Leading Events]
    E --> F[Extract New States]
    F --> G{States Changed?}
    G -->|Yes| H[Recall with New States]
    H -->|Success| C
    H -->|Failure| I{More Events?}
    I -->|Yes| D
    I -->|No| J[Return None]
    G -->|No| J
    
    style C fill:#c8e6c9
    style J fill:#ffcdd2
```

## Integration with Policy Ensemble

```mermaid
graph LR
    subgraph "Policy Ensemble"
        MP[MemoizationPolicy]
        AMP[AugmentedMemoizationPolicy]
        TED[TEDPolicy]
        RP[RulePolicy]
        
        MP --> |high priority| Ensemble[PolicyPredictionEnsemble]
        AMP --> |high priority| Ensemble
        RP --> |highest priority| Ensemble
        TED --> |lower priority| Ensemble
        
        Ensemble --> |final decision| Action[Action Selection]
    end
    
    style MP fill:#e1f5fe
    style AMP fill:#e1f5fe
    style RP fill:#e1f5fe
```

## Key Features and Benefits

### 1. **Deterministic Behavior**
- Provides 100% confidence for memorized patterns
- Ensures consistent responses for known dialogue flows
- Eliminates uncertainty in predictable scenarios

### 2. **Efficient Storage**
- Optional compression of state representations
- Compact lookup table structure
- Fast retrieval with O(1) complexity

### 3. **Flexible Configuration**
- Configurable max history length
- Optional NLU confidence integration
- Priority-based ensemble integration

### 4. **Enhanced Recall (Augmented Version)**
- Handles partial state matches
- Progressive dialogue truncation
- Maintains context awareness

## Usage Patterns

### Basic Memoization
```python
# Standard memoization for exact matches
policy = MemoizationPolicy(
    config={
        "max_history": 5,
        "enable_feature_string_compression": True
    }
)
```

### Augmented Memoization
```python
# Enhanced memoization with truncation fallback
policy = AugmentedMemoizationPolicy(
    config={
        "max_history": 5,
        "enable_feature_string_compression": True
    }
)
```

## Performance Considerations

### Memory Usage
- Lookup table size grows with unique state sequences
- Compression reduces memory footprint
- Linear growth with training data complexity

### Prediction Speed
- O(1) lookup time for exact matches
- O(n) truncation attempts for augmented version
- Minimal overhead in ensemble predictions

### Training Time
- Linear processing of training trackers
- State extraction and key generation overhead
- Compression adds computational cost

## Error Handling and Edge Cases

### Ambiguous Patterns
- Automatically removes conflicting examples
- Maintains precision over recall
- Logs ambiguous state-action mappings

### Missing Data
- Graceful fallback to default predictions
- Handles empty state sequences
- Manages incomplete tracker information

### State Compression
- Robust encoding/decoding mechanisms
- Handles special characters in state strings
- Fallback to uncompressed representation

## Relationship to Other Modules

### Policy Framework Integration
- Inherits from [policy](policy.md) base class
- Integrates with [policy_ensemble](policy_ensemble.md) for final predictions
- Complements [ted_policy](ted_policy.md) and [rule_policy](rule_policy.md)

### Tracker Processing
- Works with [DialogueStateTracker](shared_core.md) for state extraction
- Uses [TrackerFeaturizer](tracker_featurizers.md) for state representation
- Integrates with [Domain](shared_core.md) for action validation

### Training Pipeline
- Participates in [model_training](model_training.md) process
- Stores models via [ModelStorage](engine_graph.md)
- Registered in [DefaultV1Recipe](engine_graph.md) system

## Best Practices

### When to Use Memoization Policies
1. **Predictable flows**: Standard conversation patterns
2. **High precision requirements**: Critical decision points
3. **Known edge cases**: Well-defined exception handling
4. **Rule-based behavior**: Deterministic business logic

### Configuration Guidelines
1. **Max history**: Balance between context and generalization
2. **Compression**: Enable for large training datasets
3. **Priority**: Set appropriately in policy ensemble
4. **Augmentation**: Use when partial matches are expected

### Training Considerations
1. **Data quality**: Ensure consistent training stories
2. **Coverage**: Include representative dialogue flows
3. **Ambiguity**: Minimize conflicting state-action pairs
4. **Validation**: Test memorization coverage thoroughly

## Conclusion

The memoization_policy module provides a robust foundation for deterministic dialogue management in Rasa. By memorizing exact conversation patterns and providing high-confidence predictions, it ensures predictable behavior for known scenarios while working seamlessly with other policies in the ensemble. The augmented version extends this capability with intelligent fallback mechanisms, making it suitable for more complex dialogue scenarios where exact matches may not always be available.