# Tracker Featurizers Module

## Introduction

The Tracker Featurizers module is a core component of Rasa's dialogue management system, responsible for converting conversation histories (trackers) into numerical feature representations that can be used by dialogue policies for training and prediction. This module bridges the gap between the symbolic representation of dialogue states and the numerical representations required by machine learning models.

## Overview

Tracker featurizers transform `DialogueStateTracker` objects into sequences of feature vectors that represent the conversation history. These features capture various aspects of the dialogue state including user intents, entities, slot values, previous actions, and active loops. The module provides different featurization strategies optimized for various dialogue policy architectures.

## Architecture

### Core Components

```mermaid
classDiagram
    class TrackerFeaturizer {
        <<abstract>>
        -state_featurizer: SingleStateFeaturizer
        +training_states_labels_and_entities()
        +prediction_states()
        +featurize_trackers()
        +prepare_for_featurization()
    }
    
    class FullDialogueTrackerFeaturizer {
        +training_states_labels_and_entities()
        +prediction_states()
    }
    
    class MaxHistoryTrackerFeaturizer {
        -max_history: int
        -remove_duplicates: bool
        +slice_state_history()
        +_extract_examples()
    }
    
    class IntentMaxHistoryTrackerFeaturizer {
        +_convert_labels_to_ids()
        +_cleanup_last_user_state_with_action_listen()
    }
    
    class SingleStateFeaturizer {
        <<external>>
    }
    
    class DialogueStateTracker {
        <<external>>
    }
    
    class Domain {
        <<external>>
    }
    
    TrackerFeaturizer <|-- FullDialogueTrackerFeaturizer
    TrackerFeaturizer <|-- MaxHistoryTrackerFeaturizer
    MaxHistoryTrackerFeaturizer <|-- IntentMaxHistoryTrackerFeaturizer
    TrackerFeaturizer o-- SingleStateFeaturizer
    TrackerFeaturizer ..> DialogueStateTracker
    TrackerFeaturizer ..> Domain
```

### Module Dependencies

```mermaid
graph TD
    TF[Tracker Featurizers] --> SSF[Single State Featurizer]
    TF --> DST[Dialogue State Tracker]
    TF --> DOM[Domain]
    TF --> EV[Events]
    TF --> PC[Precomputation]
    
    SSF --> NLU[NLU Featurizers]
    DST --> CORE[Core Trackers]
    DOM --> DOMAIN[Domain Model]
    EV --> DIALOGUE_EVENTS[Dialogue Events]
    PC --> FEAT_PRECOMP[Featurization Precomputation]
    
    POLICIES[Dialogue Policies] --> TF
    TRAINER[Graph Trainer] --> TF
    
    style TF fill:#f9f,stroke:#333,stroke-width:4px
```

## Component Details

### TrackerFeaturizer (Abstract Base Class)

The base class that defines the interface for all tracker featurizers. It provides common functionality for:

- **State Creation**: Converting trackers to state representations
- **Feature Extraction**: Using state featurizers to encode states
- **Label Conversion**: Converting action/intent names to numerical IDs
- **Entity Tagging**: Handling entity features for user inputs
- **Serialization**: Persisting and loading featurizer configurations

Key responsibilities:
- Registry pattern for dynamic featurizer instantiation
- Common preprocessing and postprocessing logic
- Abstract methods for training and prediction state extraction

### FullDialogueTrackerFeaturizer

Creates training data for time-distributed architectures where each time step produces a prediction. This featurizer:

- **Preserves Full History**: Uses the entire dialogue history for each prediction
- **Time-Distributed**: Suitable for RNN-based policies like TED
- **Action-Based Labels**: Predicts the next action for each dialogue turn

Use cases:
- Policies that need complete conversation context
- Sequence-to-sequence dialogue modeling
- End-to-end conversation flow prediction

### MaxHistoryTrackerFeaturizer

Truncates dialogue history to a fixed window size (`max_history`), creating training examples that:

- **Limit Context**: Only considers the last N states for prediction
- **Sliding Window**: Creates multiple training examples from long conversations
- **Action Prediction**: Predicts the next action based on recent context

Key features:
- Configurable history length
- Duplicate removal for efficient training
- Suitable for memory-efficient policies

### IntentMaxHistoryTrackerFeaturizer

Specialized version of MaxHistoryTrackerFeaturizer that:

- **Predicts Intents**: Instead of actions, predicts user intents
- **Multi-Label Support**: Handles multiple possible intents per state
- **Action Listen Filtering**: Removes states where the last action was `action_listen`

Primary use:
- [UnexpecTEDIntentPolicy](Dialogue Policies.md) for intent prediction
- Detecting unexpected user inputs
- Intent classification within dialogue context

## Data Flow

### Training Data Flow

```mermaid
sequenceDiagram
    participant Tracker as DialogueStateTracker
    participant Featurizer as TrackerFeaturizer
    participant StateFeaturizer as SingleStateFeaturizer
    participant Policy as DialoguePolicy
    
    Tracker->>Featurizer: training_states_labels_and_entities()
    Featurizer->>Tracker: _create_states()
    Tracker-->>Featurizer: List[State]
    Featurizer->>Featurizer: _extract_examples()
    Featurizer->>StateFeaturizer: encode_state()
    StateFeaturizer-->>Featurizer: Dict[Text, List[Features]]
    Featurizer->>Featurizer: _convert_labels_to_ids()
    Featurizer-->>Policy: (features, labels, entities)
```

### Prediction Data Flow

```mermaid
sequenceDiagram
    participant Tracker as DialogueStateTracker
    participant Featurizer as TrackerFeaturizer
    participant StateFeaturizer as SingleStateFeaturizer
    participant Policy as DialoguePolicy
    
    Policy->>Featurizer: create_state_features()
    Featurizer->>Tracker: prediction_states()
    Tracker-->>Featurizer: List[State]
    Featurizer->>StateFeaturizer: encode_state()
    StateFeaturizer-->>Featurizer: Dict[Text, List[Features]]
    Featurizer-->>Policy: features
```

## Integration with Dialogue Policies

Tracker featurizers are essential components that dialogue policies depend on:

```mermaid
graph LR
    subgraph "Training Phase"
        A[Training Stories] -->|create trackers| B[DialogueStateTracker]
        B --> C[TrackerFeaturizer]
        C -->|featurize| D[Features & Labels]
        D --> E[Policy Training]
    end
    
    subgraph "Prediction Phase"
        F[Current Tracker] --> G[TrackerFeaturizer]
        G -->|featurize| H[Features]
        H --> I[Policy Prediction]
        I --> J[Next Action]
    end
```

## Key Features

### Flexible State Representation
- Supports both intent-based and text-based user input featurization
- Handles entities, slots, and active loops
- Configurable history length for different policy requirements

### Efficient Training Data Generation
- Duplicate removal for memory efficiency
- Batch processing of multiple trackers
- Progress tracking for large datasets

### Multi-Label Support
- IntentMaxHistoryTrackerFeaturizer supports multiple labels per example
- Padding mechanism for variable-length label sequences
- Specialized for intent prediction policies

### Precomputation Support
- Integrates with [MessageContainerForCoreFeaturization](Featurization Precomputation.md)
- Avoids redundant feature computation
- Improves training performance

## Configuration and Usage

### Basic Configuration

```python
# Max history featurizer with 5-state history
featurizer = MaxHistoryTrackerFeaturizer(
    state_featurizer=SingleStateFeaturizer(),
    max_history=5,
    remove_duplicates=True
)
```

### Policy Integration

```python
# Used within a policy
policy = TEDPolicy(
    featurizer=FullDialogueTrackerFeaturizer(),
    # other policy parameters
)
```

### Serialization

```python
# Save featurizer
featurizer.persist("path/to/model")

# Load featurizer
loaded_featurizer = TrackerFeaturizer.load("path/to/model")
```

## Error Handling

The module includes specialized exceptions:

- **InvalidStory**: Raised when a story cannot be properly featurized
- **InvalidTrackerFeaturizerUsageError**: Raised when featurizer is misconfigured

## Performance Considerations

### Memory Efficiency
- MaxHistoryTrackerFeaturizer limits memory usage with fixed history windows
- Duplicate removal reduces training data size
- Streaming processing for large datasets

### Computational Efficiency
- Precomputation support avoids redundant calculations
- Batch processing of multiple trackers
- Optimized state slicing operations

## Related Modules

- [Single State Featurizer](Single State Featurizer.md): Handles individual state encoding
- [Dialogue Policies](Dialogue Policies.md): Use featurizers for training and prediction
- [Dialogue State Tracker](Dialogue Management Core.md): Provides conversation history
- [Domain Model](Domain & Training Data.md): Defines the conversation space

## Summary

The Tracker Featurizers module serves as the critical bridge between symbolic dialogue representations and numerical machine learning features. By providing multiple featurization strategies, it enables different dialogue policies to leverage conversation history in ways that best suit their architectural requirements. The module's flexibility, efficiency, and integration capabilities make it a foundational component of Rasa's dialogue management system.