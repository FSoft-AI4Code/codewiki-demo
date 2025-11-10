# Rule Builder System

The Rule Builder System is the core fluent API interface of FluentValidation that provides a type-safe, chainable API for defining validation rules. It serves as the primary entry point for developers to specify validation logic through a readable, expressive syntax.

## Overview

The Rule Builder System provides a set of interfaces that enable developers to build validation rules using method chaining. It acts as the bridge between the fluent API syntax and the underlying validation rule implementations, offering a consistent and intuitive way to define complex validation logic.

## Architecture

### Core Components

The Rule Builder System consists of several key interfaces that form a hierarchical structure:

```mermaid
classDiagram
    class IRuleBuilderInternal {
        <<interface>>
        +AbstractValidator ParentValidator
    }
    
    class IRuleBuilderInternal~T, TProperty~ {
        <<interface>>
        +IValidationRule Rule
    }
    
    class IRuleBuilder~T, TProperty~ {
        <<interface>>
        +SetValidator(IPropertyValidator) IRuleBuilderOptions
        +SetAsyncValidator(IAsyncPropertyValidator) IRuleBuilderOptions
        +SetValidator(IValidator, string[]) IRuleBuilderOptions
        +SetValidator(Func~T, TValidator~, string[]) IRuleBuilderOptions
        +SetValidator(Func~T, TProperty, TValidator~, string[]) IRuleBuilderOptions
    }
    
    class IRuleBuilderInitial~T, TProperty~ {
        <<interface>>
    }
    
    class IRuleBuilderInitialCollection~T, TElement~ {
        <<interface>>
    }
    
    class IRuleBuilderOptions~T, TProperty~ {
        <<interface>>
        +DependentRules(Action) IRuleBuilderOptions
    }
    
    class IRuleBuilderOptionsConditions~T, TProperty~ {
        <<interface>>
        +DependentRules(Action) IRuleBuilderOptionsConditions
    }
    
    IRuleBuilderInternal~T, TProperty~ --|> IRuleBuilderInternal
    IRuleBuilder~T, TProperty~ --|> IRuleBuilderInternal~T, TProperty~
    IRuleBuilderInitial~T, TProperty~ --|> IRuleBuilder~T, TProperty~
    IRuleBuilderInitialCollection~T, TElement~ --|> IRuleBuilder~T, TElement~
    IRuleBuilderOptions~T, TProperty~ --|> IRuleBuilder~T, TProperty~
    IRuleBuilderOptionsConditions~T, TProperty~ --|> IRuleBuilder~T, TProperty~
```

### System Integration

```mermaid
graph TB
    subgraph "Rule Builder System"
        RB[IRuleBuilder]
        RBI[IRuleBuilderInitial]
        RBIC[IRuleBuilderInitialCollection]
        RBO[IRuleBuilderOptions]
        RBOC[IRuleBuilderOptionsConditions]
    end
    
    subgraph "Rule Implementation"
        VR[IValidationRule]
        PR[PropertyRule]
        RBImpl[RuleBuilder]
    end
    
    subgraph "Validator System"
        PV[IPropertyValidator]
        APV[IAsyncPropertyValidator]
        IV[IValidator]
    end
    
    subgraph "Condition System"
        CB[ConditionBuilder]
        ACB[AsyncConditionBuilder]
    end
    
    RB -->|"creates"| VR
    RB -->|"uses"| PV
    RB -->|"uses"| APV
    RB -->|"uses"| IV
    RBO -->|"supports"| CB
    RBO -->|"supports"| ACB
    RBI -->|"implemented by"| RBImpl
    RBIC -->|"specialized for"| PR
```

## Component Details

### IRuleBuilder<T, TProperty>
The core interface that provides the primary methods for associating validators with properties. It supports both synchronous and asynchronous validators, as well as nested validators.

**Key Methods:**
- `SetValidator(IPropertyValidator<T, TProperty>)` - Associates a property validator
- `SetAsyncValidator(IAsyncPropertyValidator<T, TProperty>)` - Associates an async property validator
- `SetValidator(IValidator<TProperty>, params string[])` - Associates a nested validator with optional rulesets
- `SetValidator(Func<T, TValidator>, params string[])` - Associates a validator provider
- `SetValidator(Func<T, TProperty, TValidator>, params string[])` - Associates a validator provider with property access

### IRuleBuilderInitial<T, TProperty>
A marker interface that represents the starting point of a rule builder chain. It inherits from `IRuleBuilder<T, TProperty>` but doesn't add additional functionality.

### IRuleBuilderInitialCollection<T, TElement>
Specialized interface for building rules on collection properties. It provides the same functionality as `IRuleBuilder<T, TProperty>` but is specifically typed for collection elements.

### IRuleBuilderOptions<T, TProperty>
Extends the base rule builder with additional configuration options. Currently provides support for dependent rules through the `DependentRules(Action)` method.

### IRuleBuilderOptionsConditions<T, TProperty>
A specialized version of `IRuleBuilderOptions` that only supports conditional operations without other configuration options.

### Internal Interfaces

#### IRuleBuilderInternal<T>
Internal interface providing access to the parent validator instance, used for internal rule building operations.

#### IRuleBuilderInternal<T, TProperty>
Extends the internal interface with access to the underlying validation rule, enabling internal manipulation of rule components.

## Usage Patterns

### Basic Rule Definition
```csharp
RuleFor(x => x.Email)
    .NotEmpty()
    .EmailAddress();
```

### Nested Validator Association
```csharp
RuleFor(x => x.Address)
    .SetValidator(new AddressValidator());
```

### Conditional Rules with Dependent Rules
```csharp
RuleFor(x => x.Age)
    .GreaterThan(18)
    .DependentRules(() => {
        RuleFor(x => x.DriverLicense)
            .NotEmpty();
    });
```

## Data Flow

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant RB as RuleBuilder
    participant RBI as IRuleBuilder
    participant RBO as IRuleBuilderOptions
    participant VR as ValidationRule
    participant PV as PropertyValidator
    
    Dev->>RB: RuleFor(x => x.Property)
    RB->>RBI: Create IRuleBuilderInitial
    Dev->>RBI: .NotEmpty()
    RBI->>PV: Create PropertyValidator
    RBI->>VR: Associate validator with rule
    RBI->>RBO: Return IRuleBuilderOptions
    Dev->>RBO: .WithMessage("Required")
    RBO->>VR: Configure rule options
    RBO-->>Dev: Return builder for chaining
```

## Integration with Other Systems

### Rule Implementation System
The Rule Builder System works closely with the [Rule Implementation](Rule%20Implementation.md) system:
- Creates and configures `IValidationRule` instances
- Populates `PropertyRule` objects with validators
- Integrates with `RuleBuilder` for internal rule construction

### Condition System
Integration with the [Condition System](Condition%20System.md) provides:
- Conditional rule execution through `When`/`Unless` methods
- Async condition support through `WhenAsync`/`UnlessAsync`
- Dependent rules scoping

### Validator System
The Rule Builder System leverages the [Validator System](Core%20&%20Validation%20Execution.md) for:
- Associating nested validators via `SetValidator` methods
- Supporting both `IValidator<T>` and `IPropertyValidator<T, TProperty>`
- Enabling ruleset-based validator selection

## Design Principles

### Type Safety
The Rule Builder System maintains strong typing throughout the validation chain, ensuring compile-time safety for property access and validator associations.

### Fluent Interface
Method chaining is supported through careful interface design, allowing natural, readable validation rule definitions.

### Extensibility
The interface hierarchy allows for future extensions without breaking existing implementations, following the Open/Closed Principle.

### Separation of Concerns
Different interfaces handle different aspects of rule building (initial setup, options, conditions), maintaining clean separation of responsibilities.

## Best Practices

### Use Appropriate Interfaces
- Use `IRuleBuilderInitial` for starting rule chains
- Use `IRuleBuilderOptions` when additional configuration is needed
- Use `IRuleBuilderInitialCollection` for collection-specific rules

### Maintain Chain Consistency
Ensure that method returns maintain the appropriate interface type to support intended chaining operations.

### Leverage Type Safety
Take advantage of the generic type parameters to ensure compile-time validation of property types and validator compatibility.

## Related Documentation

- [Rule Implementation](Rule%20Implementation.md) - Details on how rules are implemented and executed
- [Condition System](Condition%20System.md) - Information on conditional rule execution
- [Core & Validation Execution](Core%20&%20Validation%20Execution.md) - Core validation framework components
- [Built-in Validators](Built-in%20Validators.md) - Available validator implementations