# Rule Policy Module Documentation

## Introduction

The Rule Policy module is a core component of Rasa's dialogue management system that implements deterministic rule-based conversation handling. It provides a way to define and enforce specific conversation flows through explicit rules, ensuring predictable behavior in scenarios where machine learning policies might be insufficient or unreliable.

The RulePolicy class extends MemoizationPolicy and serves as the authoritative source for handling rules in Rasa conversations. It processes rule-based training data, validates rule consistency, and makes predictions based on memorized rule patterns during conversation execution.

## Architecture Overview

### Core Components

```mermaid
graph TB
    subgraph "Rule Policy Architecture"
        RP[RulePolicy]
        MP[MemoizationPolicy]
        P[Policy]
        
        RP -->|extends| MP
        MP -->|extends| P
        
        RP -->|uses| TF[TrackerFeaturizer]
        RP -->|validates| Domain[Domain]
        RP -->|processes| Tracker[DialogueStateTracker]
        RP -->|creates| Lookup[Rule Lookup Tables]
    end
    
    subgraph "Rule Processing"
        RT[Rule Trackers]
        ST[Story Trackers]
        RL[Rule Lookup]
        RUP[Rule Unhappy Path]
        
        RT -->|input| RP
        ST -->|input| RP
        RP -->|creates| RL
        RP -->|creates| RUP
    end
    
    subgraph "Prediction Flow"
        Input[User Input]
        States[Feature States]
        Match[Rule Matching]
        Pred[Action Prediction]
        
        Input -->|featurized| States
        States -->|matched| Match
        Match -->|predicts| Pred
    end
```

### Module Dependencies

```mermaid
graph LR
    subgraph "Rule Policy Dependencies"
        RP[RulePolicy]
        
        RP -->|inherits| MP[MemoizationPolicy]
        RP -->|uses| TF[TrackerFeaturizer]
        RP -->|processes| DST[DialogueStateTracker]
        RP -->|validates| Domain[Domain]
        RP -->|creates| AF[ActionFingerprint]
        
        MP -->|base| Policy[Policy]
        TF -->|featurizes| Events[Events]
        DST -->|tracks| Conversation[Conversation History]
    end
    
    subgraph "External Dependencies"
        RP -->|registers| Recipe[DefaultV1Recipe]
        RP -->|stores| ModelStorage[ModelStorage]
        RP -->|executes| Context[ExecutionContext]
        RP -->|uses| Resource[Resource]
    end
```

## Component Details

### RulePolicy Class

The `RulePolicy` class is the main component that handles rule-based conversation management. It extends `MemoizationPolicy` and implements specific logic for rule processing, validation, and prediction.

#### Key Features:
- **Rule-based prediction**: Memorizes and applies conversation rules
- **Loop handling**: Manages form loops and their unhappy paths
- **Contradiction checking**: Validates rules against stories
- **Fallback support**: Provides configurable fallback actions
- **Default action mapping**: Handles system default actions

#### Configuration Options:
```python
{
    POLICY_PRIORITY: RULE_POLICY_PRIORITY,
    "core_fallback_threshold": DEFAULT_CORE_FALLBACK_THRESHOLD,
    "core_fallback_action_name": ACTION_DEFAULT_FALLBACK_NAME,
    "enable_fallback_prediction": True,
    "restrict_rules": True,
    "check_for_contradictions": True,
    "use_nlu_confidence_as_score": False,
}
```

### Rule Processing Flow

```mermaid
sequenceDiagram
    participant Trainer as RulePolicy
    participant Rules as Rule Trackers
    participant Stories as Story Trackers
    participant Validator as Rule Validator
    participant Lookup as Lookup Creator
    
    Trainer->>Rules: Collect rule trackers
    Trainer->>Stories: Collect story trackers
    
    alt restrict_rules enabled
        Trainer->>Validator: Check rule restrictions
        Validator-->>Trainer: Validation result
    end
    
    alt check_contradictions enabled
        Trainer->>Validator: Check incomplete rules
        Validator-->>Trainer: Validation result
    end
    
    Trainer->>Lookup: Create rule lookup tables
    Lookup-->>Trainer: Rules, unhappy paths, rule-only data
    
    alt check_contradictions enabled
        Trainer->>Validator: Analyze rules for contradictions
        Validator-->>Trainer: Contradiction report
    end
```

### Prediction Logic

```mermaid
graph TD
    Start[User Input] --> CheckDefault{Check Default Actions}
    CheckDefault -->|Match| PredictDefault[Predict Default Action]
    CheckDefault -->|No Match| CheckLoop{Check Active Loop}
    
    CheckLoop -->|Happy Path| PredictLoop[Predict Loop Action]
    CheckLoop -->|Not Happy Path| CheckText{Check Text Rules}
    
    CheckText -->|Match| PredictText[Predict from Text Rules]
    CheckText -->|No Match| CheckIntent{Check Intent Rules}
    
    CheckIntent -->|Match| PredictIntent[Predict from Intent Rules]
    CheckIntent -->|No Match| PredictFallback[Predict Fallback]
    
    PredictDefault --> Return[Return Prediction]
    PredictLoop --> Return
    PredictText --> Return
    PredictIntent --> Return
    PredictFallback --> Return
```

## Data Flow

### Training Data Flow

```mermaid
graph LR
    subgraph "Training Data Processing"
        RT[Rule Trackers] -->|featurize| RS[Rule States]
        ST[Story Trackers] -->|featurize| SS[Story States]
        
        RS -->|create| RLookup[Rule Lookup]
        RS -->|create| LULookup[Loop Unhappy Lookup]
        RS -->|compare| SS
        
        SS -->|identify| ROS[Rule-Only Slots]
        SS -->|identify| ROL[Rule-Only Loops]
    end
    
    subgraph "Validation"
        RS -->|validate| RC[Rule Consistency]
        RT -->|check| RR[Rule Restrictions]
        RS -->|check| IR[Incomplete Rules]
    end
```

### Runtime Prediction Flow

```mermaid
graph TB
    subgraph "Prediction Pipeline"
        Input[User Input/Intent] --> Featurize[Featurize Tracker]
        Featurize --> CreateStates[Create States]
        
        CreateStates --> CheckRules{Check Rule Lookup}
        CheckRules -->|Match| FindBest[Find Best Rule]
        CheckRules -->|No Match| CheckFallback{Check Fallback}
        
        FindBest --> CheckLoopUnhappy{Check Loop Unhappy}
        CheckLoopUnhappy -->|Condition Met| ApplyCondition[Apply Condition]
        CheckLoopUnhappy -->|No Condition| ReturnAction[Return Action]
        
        CheckFallback -->|Enabled| ReturnFallback[Return Fallback]
        CheckFallback -->|Disabled| ReturnDefault[Return Default]
    end
```

## Rule Validation

### Contradiction Detection

The RulePolicy implements comprehensive validation to ensure rules don't contradict each other or stories:

1. **Rule Restrictions**: Ensures rules don't contain more than the allowed number of user inputs
2. **Incomplete Rules**: Checks that actions set consistent slots and active loops across rules
3. **Contradiction Analysis**: Compares rule predictions against story predictions

### Validation Process

```mermaid
graph TD
    Start[Rule Validation] --> CheckRestriction{Check Restrictions}
    CheckRestriction -->|Fail| Error1[Rule Restriction Error]
    CheckRestriction -->|Pass| CheckIncomplete{Check Incomplete}
    
    CheckIncomplete -->|Fail| Error2[Incomplete Rule Error]
    CheckIncomplete -->|Pass| CollectSources[Collect Rule Sources]
    
    CollectSources --> RunPredictions[Run Predictions on All Trackers]
    RunPredictions --> CheckContradictions{Check Contradictions}
    
    CheckContradictions -->|Found| Error3[Contradiction Error]
    CheckContradictions -->|None| Success[Validation Success]
```

## Loop Handling

### Loop Happy Path

The RulePolicy manages form loops by predicting:
1. **Loop Action**: When a loop is active and should continue
2. **Action Listen**: After successful loop execution

### Loop Unhappy Path

For loop interruptions and validations:
1. **Loop Interruption**: Detects when a loop was interrupted
2. **Skip Validation**: Prevents loop validation after unhappy path
3. **Do Not Predict**: Prevents loop prediction in certain conditions

## Integration Points

### Policy Ensemble Integration

The RulePolicy integrates with the [policy ensemble](policy_ensemble.md) system:
- Provides rule-based predictions with high priority
- Returns confidence scores for action selection
- Supports end-to-end and no-user predictions

### Domain Integration

Validates compatibility with the [domain](shared_core.md) configuration:
- Ensures fallback actions exist in domain
- Validates action names and slot configurations
- Checks loop definitions

### Tracker Integration

Works with [DialogueStateTracker](shared_core.md) for:
- State featurization
- Event processing
- Loop state management

## Error Handling

### Exception Types

- **InvalidRule**: Raised when rules are invalid or contradictory
- **InvalidDomain**: Raised when policy configuration conflicts with domain

### Error Messages

The policy provides detailed error messages for:
- Rule contradictions
- Incomplete rules
- Missing slots or active loops
- Domain incompatibilities

## Performance Considerations

### Optimization Strategies

1. **Feature Caching**: Caches rule key to state conversions
2. **Lookup Tables**: Uses efficient dictionary lookups for rule matching
3. **Early Termination**: Stops rule matching when best rule is found
4. **Selective Validation**: Allows disabling contradiction checks for faster training

### Scalability

- Rule lookup tables scale with the number of unique rule patterns
- Validation complexity increases with the number of rules and stories
- Memory usage depends on the complexity of rule states

## Configuration Examples

### Basic Configuration

```yaml
policies:
  - name: RulePolicy
    core_fallback_threshold: 0.3
    core_fallback_action_name: action_default_fallback
    enable_fallback_prediction: true
    restrict_rules: true
    check_for_contradictions: true
```

### Advanced Configuration

```yaml
policies:
  - name: RulePolicy
    core_fallback_threshold: 0.4
    core_fallback_action_name: custom_fallback_action
    enable_fallback_prediction: true
    restrict_rules: false  # Allow longer rules
    check_for_contradictions: false  # Skip validation for faster training
    use_nlu_confidence_as_score: true
```

## Best Practices

### Rule Design

1. **Keep rules simple**: Avoid complex multi-turn rules
2. **Use conversation starters**: Leverage `conversation_start: true` for initial rules
3. **Handle unhappy paths**: Define rules for loop interruptions
4. **Set appropriate slots**: Ensure slots are set consistently

### Validation

1. **Enable contradiction checking** during development
2. **Test rules thoroughly** with different conversation paths
3. **Monitor rule usage** to identify unused rules
4. **Document rule purposes** for maintainability

### Performance

1. **Disable contradiction checks** in production if rules are stable
2. **Use rule restrictions** to prevent state machine patterns
3. **Optimize fallback thresholds** based on confidence requirements
4. **Profile rule matching** for complex rule sets

## Related Documentation

- [Policy Framework](policy_framework.md) - General policy architecture
- [Memoization Policy](memoization_policy.md) - Base class for rule memorization
- [Policy Ensemble](policy_ensemble.md) - Policy selection and combination
- [Dialogue State Tracker](shared_core.md) - Conversation state management
- [Domain Configuration](shared_core.md) - Action and slot definitions