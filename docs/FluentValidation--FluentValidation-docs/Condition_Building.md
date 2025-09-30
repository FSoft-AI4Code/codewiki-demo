# Condition Building Module

## Introduction

The Condition Building module is a core component of the FluentValidation library that provides sophisticated conditional validation capabilities. This module enables developers to apply validation rules conditionally based on runtime conditions, supporting both synchronous and asynchronous condition evaluation. It forms a critical part of the rule-building infrastructure within the validation engine.

## Overview

The Condition Building module provides a fluent API for creating conditional validation logic that can be applied to multiple validation rules. It supports:

- **Synchronous conditions**: Conditions evaluated immediately during validation
- **Asynchronous conditions**: Conditions that require async operations (e.g., database lookups)
- **Shared conditions**: Conditions that can be cached and reused across multiple rules for performance optimization
- **Otherwise clauses**: Alternative validation logic when conditions are not met
- **Inverse conditions**: Using `Unless` for negated conditions

## Architecture

### Core Components

The module consists of four primary components that work together to provide comprehensive conditional validation support:

```mermaid
classDiagram
    class ConditionBuilder~T~ {
        -TrackingCollection~IValidationRuleInternal~T~~ _rules
        +When(Func~T, ValidationContext~T~, bool~, Action) IConditionBuilder
        +Unless(Func~T, ValidationContext~T~, bool~, Action) IConditionBuilder
    }
    
    class AsyncConditionBuilder~T~ {
        -TrackingCollection~IValidationRuleInternal~T~~ _rules
        +WhenAsync(Func~T, ValidationContext~T~, CancellationToken, Task~bool~~, Action) IConditionBuilder
        +UnlessAsync(Func~T, ValidationContext~T~, CancellationToken, Task~bool~~, Action) IConditionBuilder
    }
    
    class ConditionOtherwiseBuilder~T~ {
        -TrackingCollection~IValidationRuleInternal~T~~ _rules
        -Func~IValidationContext, bool~ _condition
        +Otherwise(Action) void
    }
    
    class AsyncConditionOtherwiseBuilder~T~ {
        -TrackingCollection~IValidationRuleInternal~T~~ _rules
        -Func~IValidationContext, CancellationToken, Task~bool~~ _condition
        +Otherwise(Action) void
    }
    
    class IConditionBuilder {
        <<interface>>
        +Otherwise(Action) void
    }
    
    ConditionBuilder~T~ ..|> IConditionBuilder : returns
    AsyncConditionBuilder~T~ ..|> IConditionBuilder : returns
    ConditionOtherwiseBuilder~T~ ..|> IConditionBuilder : implements
    AsyncConditionOtherwiseBuilder~T~ ..|> IConditionBuilder : implements
```

### Module Dependencies

The Condition Building module integrates with several other modules within the FluentValidation ecosystem:

```mermaid
graph TD
    CB[Condition Building Module]
    TR[Tracking_Collection Module]
    VR[Validation_Rules Module]
    CV[Core_Validation_Engine Module]
    
    CB -->|uses| TR
    CB -->|manipulates| VR
    CB -->|depends on| CV
    
    CB -.->|creates conditions for| Property_Validators
    CB -.->|integrates with| Rule_Building_Core
    CB -.->|works within| AbstractValidator
```

## Component Details

### ConditionBuilder<T>

The `ConditionBuilder<T>` class provides synchronous conditional validation support. It tracks rules within its scope and applies shared conditions to them.

**Key Features:**
- **Rule Tracking**: Uses `TrackingCollection<IValidationRuleInternal<T>>` to monitor rule creation within condition scopes
- **Shared Condition Cache**: Implements caching mechanism to avoid redundant condition evaluations
- **Unique Condition IDs**: Generates GUID-based identifiers for condition caching
- **Context Awareness**: Works with `ValidationContext<T>` for type-safe validation

**Condition Caching Strategy:**
```mermaid
sequenceDiagram
    participant Client
    participant ConditionBuilder
    participant ValidationContext
    participant SharedConditionCache
    
    Client->>ConditionBuilder: When(predicate, action)
    ConditionBuilder->>ValidationContext: GetFromNonGenericContext(context)
    ValidationContext->>SharedConditionCache: TryGetValue(conditionId, cachedResults)
    alt Cache Hit
        SharedConditionCache-->>ConditionBuilder: Return cached result
    else Cache Miss
        ConditionBuilder->>ConditionBuilder: Execute predicate
        ConditionBuilder->>SharedConditionCache: Add new result
    end
    ConditionBuilder-->>Client: Return IConditionBuilder
```

### AsyncConditionBuilder<T>

The `AsyncConditionBuilder<T>` class extends conditional validation to support asynchronous operations, essential for scenarios involving I/O operations or external service calls.

**Key Features:**
- **Async Predicate Support**: Accepts `Func<T, ValidationContext<T>, CancellationToken, Task<bool>>`
- **Cancellation Support**: Full `CancellationToken` support for async operations
- **Same Caching Strategy**: Uses identical caching mechanism as synchronous version
- **Thread-Safe Operations**: Ensures thread safety in async contexts

### ConditionOtherwiseBuilder<T> and AsyncConditionOtherwiseBuilder<T>

These classes implement the `Otherwise` functionality, allowing developers to specify alternative validation logic when the primary condition is not met.

**Implementation Pattern:**
- **Condition Negation**: Applies the inverse of the original condition to "otherwise" rules
- **Rule Isolation**: Maintains separate rule collections for primary and alternative logic
- **Fluent Interface**: Returns `IConditionBuilder` for method chaining

## Data Flow

### Synchronous Condition Flow

```mermaid
flowchart LR
    A[Start] --> B[Create ConditionBuilder]
    B --> C[Define When Condition]
    C --> D[Execute Action with Rules]
    D --> E[Track Created Rules]
    E --> F[Apply Shared Condition]
    F --> G{Has Otherwise?}
    G -->|Yes| H[Define Otherwise Rules]
    G -->|No| I[End]
    H --> I
```

### Asynchronous Condition Flow

```mermaid
flowchart LR
    A[Start] --> B[Create AsyncConditionBuilder]
    B --> C[Define WhenAsync Condition]
    C --> D[Execute Action with Rules]
    D --> E[Track Created Rules]
    E --> F[Apply Shared Async Condition]
    F --> G{Has Otherwise?}
    G -->|Yes| H[Define Otherwise Rules]
    G -->|No| I[End]
    H --> I
```

## Integration with Validation Pipeline

The Condition Building module integrates seamlessly with the FluentValidation pipeline:

```mermaid
graph TD
    A[AbstractValidator<T>] -->|creates| B[RuleBuilder<T, TProperty>]
    B -->|can create| C[ConditionBuilder<T>]
    C -->|applies conditions to| D[PropertyRule<T, TProperty>]
    D -->|executes| E[Property Validators]
    E -->|produce| F[ValidationResult]
    
    G[ValidationContext<T>] -->|provides context to| C
    H[TrackingCollection<T>] -->|tracks rules for| C
    I[SharedConditionCache] -->|caches results for| C
```

## Usage Patterns

### Basic Conditional Validation

```csharp
// Synchronous condition
RuleFor(x => x.Email)
    .NotEmpty()
    .When(x => x.RequiresEmail);

// Multiple rules with shared condition
When(x => x.IsPremiumUser, () => {
    RuleFor(x => x.PremiumField1).NotEmpty();
    RuleFor(x => x.PremiumField2).GreaterThan(0);
});
```

### Advanced Conditional Scenarios

```csharp
// Asynchronous condition
WhenAsync(async (x, context, ct) => {
    return await userService.IsActiveAsync(x.UserId, ct);
}, () => {
    RuleFor(x => x.ActiveUserField).NotEmpty();
});

// Otherwise clause
When(x => x.UseAdvancedValidation, () => {
    RuleFor(x => x.AdvancedField).NotEmpty();
}).Otherwise(() => {
    RuleFor(x => x.BasicField).NotEmpty();
});
```

## Performance Considerations

### Condition Caching

The module implements intelligent caching to optimize performance:

- **Shared Condition Cache**: Conditions are cached per instance to avoid redundant evaluations
- **Memory Efficiency**: Cache entries are scoped to validation context instances
- **Thread Safety**: Cache operations are thread-safe for concurrent validation scenarios

### Memory Management

- **TrackingCollection Integration**: Automatic cleanup of tracked rules when conditions go out of scope
- **Disposable Pattern**: Proper resource management through `using` statements
- **Guid-based Keys**: Unique identifiers prevent cache collisions

## Error Handling

The Condition Building module handles various error scenarios:

- **Null Context Handling**: Graceful handling of null validation contexts
- **Async Operation Failures**: Proper exception propagation in async conditions
- **Cache Access Errors**: Fallback to direct condition evaluation if cache operations fail

## Related Documentation

- [Core_Validation_Engine](Core_Validation_Engine.md) - Core validation infrastructure
- [Validation_Rules](Validation_Rules.md) - Rule definition and management
- [Rule_Building_Core](Rule_Building_Core.md) - Basic rule building functionality
- [Property_Validators](Property_Validators.md) - Individual validator implementations
- [AbstractValidator](AbstractValidator.md) - Main validator class integration

## Conclusion

The Condition Building module provides a robust, performant, and flexible foundation for conditional validation in FluentValidation. Its design enables complex validation scenarios while maintaining clean, readable code through the fluent API pattern. The module's caching capabilities and async support make it suitable for high-performance applications and complex business rule validation scenarios.