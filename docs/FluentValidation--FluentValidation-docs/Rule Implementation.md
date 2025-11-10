# Rule Implementation Module

## Introduction

The Rule Implementation module forms the core execution engine of the FluentValidation library, providing the fundamental infrastructure for defining, building, and executing validation rules. This module bridges the gap between the fluent API used to define validation rules and the actual validation execution, handling property access, condition evaluation, and validation result collection.

## Overview

The Rule Implementation module is responsible for:

- **Rule Definition**: Creating and configuring validation rules through the RuleBuilder
- **Property Validation**: Executing validation logic against object properties via PropertyRule
- **Component Management**: Managing validation components and their execution order
- **Condition Evaluation**: Handling both synchronous and asynchronous conditions
- **Result Collection**: Gathering and organizing validation failures
- **Dependent Rule Execution**: Managing rules that depend on the success of other rules

## Architecture

### Core Components

```mermaid
classDiagram
    class IValidationRule {
        <<interface>>
        +Components
        +CascadeMode
        +Condition
        +AsyncCondition
        +RuleSets
        +AddValidator()
        +AddAsyncValidator()
    }

    class IValidationRuleInternal {
        <<interface>>
        +ValidateAsync()
        +AddDependentRules()
    }

    class PropertyRule {
        -PropertyFunc
        -Member
        -Expression
        +Create()
        +ValidateAsync()
    }

    class RuleBuilder {
        -Rule
        -ParentValidator
        +SetValidator()
        +SetAsyncValidator()
        +SetValidator() with child validator
        +DependentRules()
        +AddComponent()
    }

    class RuleComponent {
        -Validator
        -Condition
        -AsyncCondition
        +ValidateAsync()
        +InvokeCondition()
        +InvokeAsyncCondition()
    }

    IValidationRule <|-- IValidationRuleInternal
    IValidationRuleInternal <|-- PropertyRule
    RuleBuilder ..> PropertyRule : creates
    PropertyRule o-- RuleComponent : contains
```

### Component Relationships

```mermaid
graph TD
    A[AbstractValidator] --> B[RuleBuilder]
    B --> C[PropertyRule]
    C --> D[RuleComponent]
    D --> E[IPropertyValidator]
    D --> F[IAsyncPropertyValidator]
    
    C --> G[ValidationContext]
    G --> H[ValidationResult]
    G --> I[ValidationFailure]
    
    C --> J[DependentRules]
    C --> K[Conditions]
    K --> L[Synchronous]
    K --> M[Asynchronous]
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style C fill:#bbf,stroke:#333,stroke-width:2px
    style D fill:#bfb,stroke:#333,stroke-width:2px
```

## Detailed Component Analysis

### PropertyRule

The `PropertyRule<T, TProperty>` class is the cornerstone of property validation in FluentValidation. It represents a validation rule associated with a specific property of an object and handles the complete validation lifecycle.

#### Key Responsibilities:

1. **Property Access**: Extracts property values using compiled lambda expressions for optimal performance
2. **Validation Execution**: Coordinates the execution of all validation components
3. **Condition Evaluation**: Evaluates both synchronous and asynchronous conditions
4. **Result Management**: Creates and manages validation failures
5. **Dependent Rule Handling**: Executes dependent rules when the primary rule succeeds

#### Validation Process Flow:

```mermaid
sequenceDiagram
    participant C as ValidationContext
    participant PR as PropertyRule
    participant RC as RuleComponent
    participant PV as PropertyValidator
    participant VF as ValidationFailure
    
    C->>PR: ValidateAsync(context, cancellation)
    PR->>PR: Build property path
    PR->>PR: Check selector permission
    PR->>PR: Evaluate conditions
    
    loop For each component
        PR->>RC: Validate component
        RC->>RC: Check component conditions
        RC->>PR: Get property value (first only)
        RC->>PV: ValidateAsync(context, value, cancellation)
        PV-->>RC: Validation result
        alt Validation failed
            RC->>VF: CreateValidationError()
            RC->>C: Add failure to context
        end
        
        alt CascadeMode.Stop && failures > 0
            PR->>PR: Break loop
        end
    end
    
    alt No failures && has dependent rules
        PR->>PR: Execute dependent rules
    end
    
    PR-->>C: Return (implicit)
```

### RuleBuilder

The `RuleBuilder<T, TProperty>` class provides the fluent interface for configuring validation rules. It acts as a bridge between the user-friendly API and the internal rule representation.

#### Key Features:

1. **Validator Assignment**: Supports both synchronous and asynchronous validators
2. **Child Validator Integration**: Allows nesting validators for complex object graphs
3. **Dependent Rule Configuration**: Enables conditional rule execution
4. **Component Management**: Manages the addition of validation components to rules

#### Builder Pattern Implementation:

```mermaid
graph LR
    A["RuleFor(x =&gt; x.Property)"] --> B[RuleBuilder]
    B --> C[SetValidator]
    B --> D[SetAsyncValidator]
    B --> E[SetValidatorChild]
    B --> F[DependentRules]
    
    C --> G[PropertyValidator]
    D --> H[AsyncPropertyValidator]
    E --> I[ChildValidatorAdaptor]
    F --> J[DependentRuleCollection]
    
    style B fill:#f9f,stroke:#333,stroke-width:2px
    style I fill:#bbf,stroke:#333,stroke-width:2px
```

## Data Flow Architecture

### Validation Execution Flow

```mermaid
flowchart TD
    Start([Validation Request]) --> A[Create ValidationContext]
    A --> B[Execute PropertyRule.ValidateAsync]
    B --> C{Selector Allows?}
    C -->|No| Z[Skip Rule]
    C -->|Yes| D{Conditions Met?}
    D -->|No| Z
    D -->|Yes| E[Get Property Value]
    E --> F[Iterate Components]
    F --> G{Component Conditions}
    G -->|Failed| F
    G -->|Passed| H[Execute Validator]
    H --> I{Validation Result}
    I -->|Failed| J[Create ValidationFailure]
    J --> K[Add to Context.Failures]
    K --> L{CascadeMode Check}
    L -->|Stop| M[Break Execution]
    L -->|Continue| F
    I -->|Success| F
    F --> N{More Components?}
    N -->|Yes| F
    N -->|No| O{Failures == 0?}
    O -->|Yes| P[Execute Dependent Rules]
    O -->|No| Q[Complete]
    P --> Q
    Z --> Q
    Q --> End([Return ValidationResult])
```

### Component Interaction

```mermaid
graph TD
    subgraph "Rule Implementation"
        A[PropertyRule]
        B[RuleBuilder]
        C[RuleComponent]
    end
    
    subgraph "Validation Context"
        D[ValidationContext]
        E[ValidationFailure]
        F[ValidationResult]
    end
    
    subgraph "External Dependencies"
        G[IPropertyValidator]
        H[IAsyncPropertyValidator]
        I[ChildValidatorAdaptor]
        J[IValidatorSelector]
        K[AbstractValidator]
    end
    
    B -->|Creates| A
    A -->|Contains| C
    A -->|Uses| D
    C -->|Validates with| G
    C -->|Validates with| H
    A -->|Creates| E
    E -->|Added to| D
    D -->|Produces| F
    A -->|Checked by| J
    K -->|Contains| A
    I -->|Wraps| K
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style D fill:#bbf,stroke:#333,stroke-width:2px
    style B fill:#bfb,stroke:#333,stroke-width:2px
```

## Integration with Other Modules

### Core & Validation Execution Module
The Rule Implementation module heavily depends on the [Core & Validation Execution](Core & Validation Execution.md) module for:
- **ValidationContext**: Provides the execution context and failure collection
- **ValidationResult/ValidationFailure**: Manages validation outcomes
- **Validator Selection**: Uses selector components to determine rule execution eligibility
- **Configuration**: Leverages global validation settings

### Fluent API & Rule Definition Module
The Rule Implementation module is the target of the [Fluent API & Rule Definition](Fluent API & Rule Definition.md) module:
- **Rule Creation**: PropertyRule instances are created through the fluent API
- **Builder Integration**: RuleBuilder provides the implementation for fluent configuration methods
- **Component Registration**: Validation components are added through the builder interface

### Built-in Validators Module
The [Built-in Validators](Built-in Validators.md) module provides the actual validation logic:
- **Property Validators**: Concrete implementations of IPropertyValidator
- **Async Validators**: Support for asynchronous validation operations
- **Child Validators**: Nested validation through ChildValidatorAdaptor

## Key Design Patterns

### 1. Builder Pattern
The RuleBuilder implements the builder pattern to provide a fluent interface for rule configuration:

```csharp
RuleFor(x => x.Email)
    .NotEmpty()
    .EmailAddress()
    .When(x => x.RequiresEmail)
    .WithMessage("Please provide a valid email address");
```

### 2. Strategy Pattern
Different validator types (sync/async, child validators) are handled through a common interface:

```csharp
public interface IPropertyValidator<in T, in TProperty> {
    bool IsValid(ValidationContext<T> context, TProperty value);
}

public interface IAsyncPropertyValidator<in T, in TProperty> {
    Task<bool> IsValidAsync(ValidationContext<T> context, TProperty value, CancellationToken cancellation);
}
```

### 3. Chain of Responsibility
Validation components are executed in sequence, with cascade mode controlling continuation:

```csharp
foreach (var component in Components) {
    if (!await component.ValidateAsync(context, propValue, cancellation)) {
        // Handle failure
        if (cascade == CascadeMode.Stop) break;
    }
}
```

## Performance Considerations

### 1. Compiled Expression Caching
Property access expressions are compiled and cached for optimal performance:

```csharp
var compiled = AccessorCache<T>.GetCachedAccessor(member, expression, bypassCache);
```

### 2. Lazy Property Evaluation
Property values are only retrieved when needed (first component execution):

```csharp
if (first) {
    first = false;
    propValue = PropertyFunc(context.InstanceToValidate);
}
```

### 3. Early Termination
CascadeMode.Stop enables early termination on first failure, improving performance for validation-heavy scenarios.

## Error Handling

### 1. Null Reference Protection
Special handling for null reference exceptions with descriptive error messages:

```csharp
catch (NullReferenceException nre) {
    throw new NullReferenceException($"NullReferenceException occurred when executing rule for {Expression}. If this property can be null you should add a null check using a When condition", nre);
}
```

### 2. Async/Sync Consistency
The Zomp.SyncMethodGenerator ensures consistent behavior between sync and async execution paths.

## Usage Examples

### Basic Property Validation
```csharp
public class CustomerValidator : AbstractValidator<Customer> {
    public CustomerValidator() {
        RuleFor(x => x.Name)
            .NotEmpty()
            .Length(2, 50);
            
        RuleFor(x => x.Email)
            .NotEmpty()
            .EmailAddress();
    }
}
```

### Conditional Validation
```csharp
RuleFor(x => x.Discount)
    .GreaterThan(0)
    .When(x => x.IsPreferredCustomer)
    .WithMessage("Preferred customers must have a discount");
```

### Dependent Rules
```csharp
RuleFor(x => x.Password)
    .NotEmpty()
    .DependentRules(() => {
        RuleFor(x => x.ConfirmPassword)
            .NotEmpty()
            .Equal(x => x.Password);
    });
```

### Child Validator Integration
```csharp
RuleFor(x => x.Address)
    .SetValidator(new AddressValidator());
```

## Summary

The Rule Implementation module serves as the execution engine of FluentValidation, transforming high-level rule definitions into concrete validation operations. Through its sophisticated component model, it provides a flexible and extensible framework for property validation while maintaining excellent performance characteristics. The module's design enables complex validation scenarios including conditional execution, dependent rules, and nested validation, making it suitable for a wide range of validation requirements in enterprise applications.