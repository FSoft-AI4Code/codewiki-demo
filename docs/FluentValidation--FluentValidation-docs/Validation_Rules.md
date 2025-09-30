# Validation Rules Module

## Introduction

The Validation Rules module is the core component of the FluentValidation framework that defines and manages validation rules. It provides the infrastructure for creating, configuring, and executing validation rules against object properties and collections. This module serves as the bridge between the validation engine and individual property validators, handling rule composition, conditional execution, and error message formatting.

## Architecture Overview

The Validation Rules module implements a hierarchical rule system where validation rules can be composed of multiple components, each containing individual validators. The architecture supports both synchronous and asynchronous validation, conditional rule execution, and complex scenarios like collection validation and dependent rules.

```mermaid
graph TB
    subgraph "Validation Rules Module"
        IValidationRule[IValidationRule<br/>Interface]
        IValidationRuleT[IValidationRule<T><br/>Interface]
        IValidationRuleTT[IValidationRule<T,TProperty><br/>Interface]
        IValidationRuleInternal[IValidationRuleInternal<T><br/>Interface]
        IValidationRuleInternalT[IValidationRuleInternal<T,TProperty><br/>Interface]
        
        PropertyRule[PropertyRule<T,TProperty><br/>Class]
        CollectionPropertyRule[CollectionPropertyRule<T,TElement><br/>Class]
        IncludeRule[IncludeRule<T><br/>Class]
        
        IRuleComponent[IRuleComponent<br/>Interface]
        IRuleComponentT[IRuleComponent<T,TProperty><br/>Interface]
        RuleComponent[RuleComponent<T,TProperty><br/>Class]
        RuleComponentNullable[RuleComponentForNullableStruct<T,TProperty><br/>Class]
        
        ICollectionRule[ICollectionRule<T,TElement><br/>Interface]
        IIncludeRule[IIncludeRule<br/>Interface]
    end
    
    subgraph "Core Validation Engine"
        ValidationContext[ValidationContext<T><br/>from Core_Validation_Engine]
        ValidationFailure[ValidationFailure<br/>from Core_Validation_Engine]
        ValidationResult[ValidationResult<br/>from Core_Validation_Engine]
    end
    
    subgraph "Property Validators"
        IPropertyValidator[IPropertyValidator<br/>from Property_Validators]
        IAsyncPropertyValidator[IAsyncPropertyValidator<br/>from Property_Validators]
    end
    
    IValidationRule --> IValidationRuleT
    IValidationRuleT --> IValidationRuleTT
    IValidationRule --> IValidationRuleInternal
    IValidationRuleT --> IValidationRuleInternalT
    
    PropertyRule -.->|implements| IValidationRuleInternalT
    CollectionPropertyRule -.->|implements| IValidationRuleInternalT
    CollectionPropertyRule -.->|implements| ICollectionRule
    IncludeRule -.->|implements| IIncludeRule
    
    RuleComponent -.->|implements| IRuleComponentT
    RuleComponentNullable -.->|extends| RuleComponent
    
    PropertyRule -->|uses| ValidationContext
    PropertyRule -->|produces| ValidationFailure
    CollectionPropertyRule -->|uses| ValidationContext
    CollectionPropertyRule -->|produces| ValidationFailure
    IncludeRule -->|uses| ValidationContext
    
    RuleComponent -->|contains| IPropertyValidator
    RuleComponent -->|contains| IAsyncPropertyValidator
```

## Core Components

### Rule Interfaces

#### IValidationRule Hierarchy

The module defines a comprehensive interface hierarchy for validation rules:

```mermaid
classDiagram
    class IValidationRule {
        <<interface>>
        +Components: IEnumerable~IRuleComponent~
        +RuleSets: string[]
        +PropertyName: string
        +Member: MemberInfo
        +TypeToValidate: Type
        +HasCondition: bool
        +HasAsyncCondition: bool
        +Expression: LambdaExpression
        +DependentRules: IEnumerable~IValidationRule~
        +GetDisplayName(context): string
        +SetDisplayName(name): void
    }
    
    class IValidationRule~T~ {
        <<interface>>
        +ApplyCondition(predicate, applyConditionTo): void
        +ApplyAsyncCondition(predicate, applyConditionTo): void
        +ApplySharedCondition(condition): void
        +ApplySharedAsyncCondition(condition): void
        +GetPropertyValue(instance): object
        +TryGetPropertyValue~TProp~(instance, out value): bool
    }
    
    class IValidationRule~T,TProperty~ {
        <<interface>>
        +CascadeMode: CascadeMode
        +Current: IRuleComponent~T,TProperty~
        +MessageBuilder: Func~IMessageBuilderContext~T,TProperty~~,string~
        +SetDisplayName(factory): void
        +AddValidator(validator): void
        +AddAsyncValidator(asyncValidator, fallback): void
    }
    
    IValidationRule <|-- IValidationRule~T~
    IValidationRule~T~ <|-- IValidationRule~T,TProperty~
```

### Rule Implementations

#### PropertyRule<T, TProperty>

The primary implementation for validating individual properties:

```mermaid
classDiagram
    class PropertyRule~T,TProperty~ {
        -PropertyFunc: Func~T,TProperty~
        -CascadeModeThunk: Func~CascadeMode~
        +Create(expression, cascadeModeThunk, bypassCache): PropertyRule~T,TProperty~
        +ValidateAsync(context, cancellation): ValueTask
        +AddDependentRules(rules): void
    }
    
    class RuleBase~T,TProperty,TPropertyForValidation~ {
        <<abstract>>
        #Member: MemberInfo
        #PropertyFunc: Func~T,TProperty~
        #Expression: LambdaExpression
        #CascadeModeThunk: Func~CascadeMode~
        #TypeToValidate: Type
        #Components: List~RuleComponent~T,TPropertyForValidation~~
        #DependentRules: List~IValidationRuleInternal~T~~
        #Condition: Func~ValidationContext~T~,bool~
        #AsyncCondition: Func~ValidationContext~T~,CancellationToken,Task~bool~~
        #_displayNameFunc: Func~ValidationContext~T~,string~
        +PropertyName: string
        +CascadeMode: CascadeMode
        +GetDisplayName(context): string
        +SetDisplayName(name): void
        +SetDisplayName(factory): void
    }
    
    PropertyRule~T,TProperty~ --|> RuleBase~T,TProperty,TProperty~
    PropertyRule~T,TProperty~ ..|> IValidationRuleInternal~T,TProperty~
```

#### CollectionPropertyRule<T, TElement>

Specialized rule for validating collection properties:

```mermaid
classDiagram
    class CollectionPropertyRule~T,TElement~ {
        +Filter: Func~TElement,bool~
        +AsyncFilter: Func~TElement,Task~bool~~
        +IndexBuilder: Func~T,IEnumerable~TElement~,TElement,int,string~
        +Create(expression, cascadeModeThunk, bypassCache): CollectionPropertyRule~T,TElement~
        +ValidateAsync(context, cancellation): ValueTask
        -GetValidatorsToExecuteAsync(context, cancellation): ValueTask~List~RuleComponent~~
        -InferPropertyName(expression): string
    }
    
    CollectionPropertyRule~T,TElement~ --|> RuleBase~T,IEnumerable{TElement},TElement~
    CollectionPropertyRule~T,TElement~ ..|> IValidationRuleInternal~T,TElement~
    CollectionPropertyRule~T,TElement~ ..|> ICollectionRule~T,TElement~
```

#### IncludeRule<T>

Rule for including external validators:

```mermaid
classDiagram
    class IncludeRule~T~ {
        +Create(validator, cascadeModeThunk): IncludeRule~T~
        +Create~TValidator~(func, cascadeModeThunk): IncludeRule~T~
        +ValidateAsync(context, cancellation): ValueTask
    }
    
    IncludeRule~T~ --|> PropertyRule~T,T~
    IncludeRule~T~ ..|> IIncludeRule
```

### Rule Components

Rule components represent individual validators within a rule chain:

```mermaid
classDiagram
    class IRuleComponent {
        <<interface>>
        +HasCondition: bool
        +HasAsyncCondition: bool
        +Validator: IPropertyValidator
        +ErrorCode: string
        +GetUnformattedErrorMessage(): string
    }
    
    class IRuleComponent~T,TProperty~ {
        <<interface>>
        +ErrorCode: string
        +CustomStateProvider: Func~ValidationContext~T~,TProperty,object~
        +SeverityProvider: Func~ValidationContext~T~,TProperty,Severity~
        +MessageBuilder: Func~IMessageBuilderContext~T,TProperty~~,string~
        +ApplyCondition(condition): void
        +ApplyAsyncCondition(condition): void
        +SetErrorMessage(errorFactory): void
        +SetErrorMessage(errorMessage): void
    }
    
    class RuleComponent~T,TProperty~ {
        -_propertyValidator: IPropertyValidator~T,TProperty~
        -_asyncPropertyValidator: IAsyncPropertyValidator~T,TProperty~
        -_condition: Func~ValidationContext~T~,bool~
        -_asyncCondition: Func~ValidationContext~T~,CancellationToken,Task~bool~~
        -_errorMessage: string
        -_errorMessageFactory: Func~ValidationContext~T~,TProperty,string~
        +ValidateAsync(context, value, cancellation): ValueTask~bool~
        +Validate(context, value): bool
        +InvokeCondition(context): bool
        +InvokeAsyncCondition(context, token): Task~bool~
    }
    
    class RuleComponentForNullableStruct~T,TProperty~ {
        -_propertyValidator: IPropertyValidator~T,TProperty~
        -_asyncPropertyValidator: IAsyncPropertyValidator~T,TProperty~
        +InvokePropertyValidator(context, value): bool
        +InvokePropertyValidatorAsync(context, value, cancellation): Task~bool~
    }
    
    IRuleComponent <|-- IRuleComponent~T,TProperty~
    RuleComponent~T,TProperty~ ..|> IRuleComponent~T,TProperty~
    RuleComponentForNullableStruct~T,TProperty~ --|> RuleComponent~T,TProperty?~
```

## Data Flow

### Validation Execution Flow

```mermaid
sequenceDiagram
    participant Validator as Validator
    participant Rule as ValidationRule
    participant Component as RuleComponent
    participant PropertyValidator as PropertyValidator
    participant Context as ValidationContext
    
    Validator->>Rule: ValidateAsync(context, cancellation)
    Rule->>Context: CanExecute(rule, propertyPath, context)
    Context-->>Rule: true/false
    
    alt Can Execute
        Rule->>Rule: Check Conditions
        Rule->>Rule: Get Property Value
        Rule->>Component: ValidateAsync(context, value, cancellation)
        
        Component->>Component: InvokeCondition(context)
        alt Condition Met
            Component->>PropertyValidator: IsValidAsync(context, value, cancellation)
            PropertyValidator-->>Component: true/false
            Component-->>Rule: true/false
        else Condition Not Met
            Component-->>Rule: true (skip)
        end
        
        Rule->>Context: Add Failure (if invalid)
        Rule->>Rule: Check CascadeMode
    end
    
    Rule-->>Validator: Validation Complete
```

### Collection Validation Flow

```mermaid
flowchart TD
    A[Start Collection Validation] --> B[Get Collection Property Value]
    B --> C{Collection Null?}
    C -->|Yes| D[Skip Validation]
    C -->|No| E[Iterate Collection]
    
    E --> F[Apply Filter/AsyncFilter]
    F --> G{Item Passes Filter?}
    G -->|No| H[Skip Item]
    G -->|Yes| I[Build Index Context]
    
    I --> J[Execute Rule Components]
    J --> K{Validation Failed?}
    K -->|Yes| L[Add Failure with Index]
    K -->|No| M[Continue]
    
    L --> N{Check CascadeMode}
    M --> N
    H --> N
    N -->|Stop| O[Break Loop]
    N -->|Continue| P{More Items?}
    P -->|Yes| E
    P -->|No| Q[Check Dependent Rules]
    
    Q --> R[Execute Dependent Rules]
    R --> S[End Validation]
    O --> S
    D --> S
```

## Key Features

### 1. Rule Composition

Rules can be composed of multiple components, each representing a specific validation check:

```csharp
// Example: RuleFor(x => x.Name).NotNull().NotEmpty().Length(1, 50)
// This creates one rule with three components: NotNull, NotEmpty, and Length validators
```

### 2. Conditional Execution

Rules support both synchronous and asynchronous conditions:

- **Rule-level conditions**: Applied to the entire rule
- **Component-level conditions**: Applied to individual validators
- **Shared conditions**: Pre-conditions that affect multiple rules

### 3. Collection Validation

Specialized support for validating collections with:
- Item filtering (sync/async)
- Custom index formatting
- Individual item validation within collection context

### 4. Dependent Rules

Rules can have dependent rules that only execute when the parent rule succeeds:

```mermaid
graph TD
    A[Parent Rule] -->|Success| B[Dependent Rule 1]
    A -->|Success| C[Dependent Rule 2]
    A -->|Failure| D[Skip Dependent Rules]
    
    B --> E[Continue Validation]
    C --> E
```

### 5. Include Rules

Support for including external validators within a rule definition, enabling code reuse and modular validation logic.

## Integration with Other Modules

### Core Validation Engine
- Uses [ValidationContext](Core_Validation_Engine.md) for execution context
- Produces [ValidationFailure](Core_Validation_Engine.md) objects
- Integrates with [ValidationResult](Core_Validation_Engine.md) collection

### Property Validators
- Contains [IPropertyValidator](Property_Validators.md) implementations
- Supports both sync and async validators via [IAsyncPropertyValidator](Property_Validators.md)
- Delegates actual validation logic to property validator instances

### Rule Building
- Integrates with [RuleBuilder](Rule_Building.md) for fluent API construction
- Supports conditional building via [ConditionBuilder](Rule_Building.md)

### Validator Selection
- Respects [IValidatorSelector](Validator_Selection.md) decisions
- Integrates with [MemberNameValidatorSelector](Validator_Selection.md) for property-specific validation

## Error Handling and Messaging

The module provides comprehensive error handling and message formatting:

1. **Error Message Templates**: Each component can have custom error messages
2. **Message Formatting**: Integration with [MessageFormatter](Localization.md) for placeholder replacement
3. **Custom State**: Support for attaching custom state to validation failures
4. **Severity Levels**: Configurable severity for validation failures

## Performance Considerations

1. **Caching**: Property accessors are cached for performance
2. **Lazy Evaluation**: Conditions are evaluated only when necessary
3. **Early Termination**: CascadeMode.Stop prevents unnecessary validation
4. **Async/Await**: Proper async pattern implementation to avoid thread blocking

## Usage Examples

### Basic Property Rule
```csharp
RuleFor(x => x.Email)
    .NotEmpty()
    .EmailAddress()
    .WithMessage("Please provide a valid email address");
```

### Collection Rule
```csharp
RuleForEach(x => x.Items)
    .Must(item => item.Quantity > 0)
    .WithMessage("Item quantity must be greater than 0");
```

### Conditional Rule
```csharp
RuleFor(x => x.ShippingAddress)
    .NotEmpty()
    .When(x => x.RequiresShipping);
```

### Include Rule
```csharp
RuleFor(x => x.Address)
    .SetValidator(new AddressValidator());
```

This module forms the backbone of the FluentValidation framework, providing the essential infrastructure for defining and executing validation rules with flexibility, performance, and extensibility in mind.