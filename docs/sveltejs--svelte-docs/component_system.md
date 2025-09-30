# Component System Module

The component_system module serves as the primary interface for Svelte's component architecture, providing the core types and abstractions that define how components are created, instantiated, and interact within the Svelte ecosystem. This module bridges the gap between Svelte 4's class-based components and Svelte 5's function-based components while maintaining backward compatibility.

## Architecture Overview

```mermaid
graph TB
    subgraph "Component System Architecture"
        A[Component Interface] --> B[SvelteComponent Class]
        A --> C[ComponentConstructorOptions]
        B --> D[SvelteComponentTyped]
        
        E[Snippet System] --> F[EventDispatcher]
        F --> G[DispatchOptions]
        
        H[Mount System] --> I[MountOptions]
        
        A -.-> J[ComponentInternals]
        B -.-> K[Legacy Compatibility]
    end
    
    subgraph "External Dependencies"
        L[Compiler Core] --> A
        M[Client Runtime] --> A
        N[Template Types] --> E
        O[HTML Elements] --> C
    end
    
    style A fill:#e1f5fe
    style E fill:#f3e5f5
    style H fill:#e8f5e8
    style K fill:#fff3e0
```

## Core Components

### Component Interface (Svelte 5)

The modern `Component` interface represents the new function-based component architecture in Svelte 5:

```typescript
interface Component<
    Props extends Record<string, any> = {},
    Exports extends Record<string, any> = {},
    Bindings extends keyof Props | '' = string
>
```

**Key Features:**
- Function-based component signature
- Generic type parameters for props, exports, and bindings
- Internal component management through `ComponentInternals`
- Optional custom element support
- Type-only binding information

### SvelteComponent Class (Legacy)

The `SvelteComponent` class provides backward compatibility for Svelte 4 components:

```typescript
class SvelteComponent<
    Props extends Record<string, any> = Record<string, any>,
    Events extends Record<string, any> = any,
    Slots extends Record<string, any> = any
>
```

**Legacy Methods:**
- `$destroy()`: Component cleanup
- `$on()`: Event listener registration
- `$set()`: Reactive property updates

### Component Instantiation

```mermaid
sequenceDiagram
    participant App as Application
    participant Mount as Mount Function
    participant Comp as Component
    participant DOM as DOM Tree
    participant Runtime as Client Runtime
    
    App->>Mount: mount(Component, options)
    Mount->>Comp: Create component instance
    Mount->>DOM: Attach to target element
    Comp->>Runtime: Initialize reactivity
    Runtime->>DOM: Render initial state
    DOM-->>App: Component ready
```

## Component Lifecycle

### Modern Component Flow (Svelte 5)

```mermaid
flowchart TD
    A[Component Function Called] --> B[ComponentInternals Created]
    B --> C[Props Processed]
    C --> D[Component Logic Executed]
    D --> E[Exports Generated]
    E --> F[DOM Updates]
    F --> G[Component Active]
    
    G --> H[Props Updated?]
    H -->|Yes| C
    H -->|No| I[Component Destroyed?]
    I -->|Yes| J[Cleanup]
    I -->|No| G
    
    style A fill:#e1f5fe
    style G fill:#e8f5e8
    style J fill:#ffebee
```

### Legacy Component Flow (Svelte 4)

```mermaid
flowchart TD
    A["new SvelteComponent(options)"] --> B[Constructor Called]
    B --> C[Target Element Identified]
    C --> D[Props Applied]
    D --> E[Component Mounted]
    E --> F[Event Listeners Active]
    
    F --> G["Props Updated via $set?"]
    G -->|Yes| H["$set() Called"]
    H --> I[Reactive Updates]
    I --> F
    
    G -->|No| J[Component Destroyed?]
    J -->|Yes| K["$destroy() Called"]
    K --> L[Cleanup Complete]
    J -->|No| F
    
    style A fill:#fff3e0
    style E fill:#e8f5e8
    style L fill:#ffebee
```

## Event System

### EventDispatcher Architecture

```mermaid
graph LR
    subgraph "Event Dispatch Flow"
        A[Component] --> B[EventDispatcher]
        B --> C[Custom Event]
        C --> D[DOM Event System]
        D --> E[Parent Component]
    end
    
    subgraph "Event Configuration"
        F[DispatchOptions] --> G[cancelable: boolean]
        F --> B
    end
    
    subgraph "Type Safety"
        H[EventMap] --> I[Event Types]
        I --> B
        J[Parameter Validation] --> B
    end
    
    style B fill:#e1f5fe
    style F fill:#f3e5f5
    style H fill:#e8f5e8
```

The EventDispatcher provides type-safe event emission:

```typescript
interface EventDispatcher<EventMap extends Record<string, any>> {
    <Type extends keyof EventMap>(
        ...args: [type: Type, parameter: EventMap[Type], options?: DispatchOptions]
    ): boolean;
}
```

## Snippet System

### Snippet Architecture

```mermaid
graph TB
    subgraph "Snippet System"
        A[Snippet Interface] --> B[Parameter Validation]
        B --> C[Render Function]
        C --> D[Template Output]
        
        E[Component] --> F[Render Directive]
        F --> A
        
        G[Type Parameters] --> H[Compile-time Validation]
        H --> A
    end
    
    style A fill:#e1f5fe
    style F fill:#f3e5f5
    style H fill:#e8f5e8
```

Snippets provide reusable template fragments with type safety:

```typescript
interface Snippet<Parameters extends unknown[] = []> {
    (...args: Parameters): SnippetReturn;
}
```

## Component Mounting

### Mount Options Flow

```mermaid
flowchart TD
    A[MountOptions] --> B{Props Required?}
    B -->|Yes| C[Props: Required]
    B -->|No| D[Props: Optional]
    
    C --> E[Target Element]
    D --> E
    E --> F[Optional Anchor]
    F --> G[Context Map]
    G --> H[Event Handlers]
    H --> I[Intro Animations]
    I --> J[Component Mounted]
    
    style A fill:#e1f5fe
    style J fill:#e8f5e8
```

## Integration with Other Modules

### Compiler Integration

```mermaid
graph LR
    subgraph "Compilation Pipeline"
        A[Template Types] --> B[Component System]
        C[Compiler Core] --> B
        D[Transform Phase] --> B
    end
    
    subgraph "Runtime Integration"
        B --> E[Client Runtime]
        B --> F[Server Runtime]
        B --> G[Reactivity System]
    end
    
    subgraph "Developer Interface"
        B --> H[HTML Elements]
        B --> I[Actions]
        B --> J[Transitions]
    end
```

**Key Relationships:**
- **[Compiler Core](compiler_core.md)**: Transforms component definitions into executable code
- **[Client Runtime](client_runtime.md)**: Provides reactivity and DOM management
- **[Template Types](compiler_types.md)**: Defines the structure of component templates
- **[HTML Elements](html_elements.md)**: Provides type definitions for DOM elements

### Type System Dependencies

```mermaid
graph TB
    subgraph "Type Dependencies"
        A[ComponentProps] --> B[Component Interface]
        C[ComponentEvents] --> D[SvelteComponent]
        E[ComponentType] --> D
        
        F[Properties Utility] --> G[Slots Integration]
        G --> B
        
        H[Brand Types] --> I[ComponentInternals]
        I --> B
    end
    
    style B fill:#e1f5fe
    style D fill:#fff3e0
    style I fill:#f3e5f5
```

## Migration Considerations

### Svelte 4 to Svelte 5 Migration

```mermaid
flowchart LR
    subgraph "Svelte 4 (Legacy)"
        A[Class Components] --> B["new Component()"]
        B --> C["$destroy(), $set(), $on()"]
        C --> D[ComponentConstructorOptions]
    end
    
    subgraph "Migration Path"
        E[Compatibility Helpers] --> F["asClassComponent()"]
        F --> G[Gradual Migration]
    end
    
    subgraph "Svelte 5 (Modern)"
        H[Function Components] --> I["mount()"]
        I --> J[Reactive Props]
        J --> K[MountOptions]
    end
    
    A -.-> E
    E -.-> H
    
    style A fill:#fff3e0
    style E fill:#f3e5f5
    style H fill:#e1f5fe
```

## Usage Patterns

### Component Definition

```typescript
// Svelte 5 Component Type
const MyComponent: Component<
    { title: string; count: number },  // Props
    { getValue: () => number },        // Exports
    'count'                           // Bindings
> = (internals, props) => {
    // Component implementation
    return {
        getValue: () => props.count
    };
};
```

### Component Mounting

```typescript
import { mount } from 'svelte';
import MyComponent from './MyComponent.svelte';

const instance = mount(MyComponent, {
    target: document.getElementById('app'),
    props: {
        title: 'Hello World',
        count: 42
    },
    intro: true
});
```

### Event Handling

```typescript
import { createEventDispatcher } from 'svelte';

const dispatch: EventDispatcher<{
    click: { x: number; y: number };
    change: string;
}> = createEventDispatcher();

// Type-safe event dispatch
dispatch('click', { x: 100, y: 200 });
dispatch('change', 'new value');
```

## Performance Considerations

### Component Optimization

```mermaid
graph TB
    subgraph "Performance Optimizations"
        A[Component Reuse] --> B[Instance Pooling]
        C[Lazy Loading] --> D[Dynamic Imports]
        E[Bundle Splitting] --> F[Code Splitting]
        
        G[Reactivity] --> H[Minimal Updates]
        I[Event Handling] --> J[Efficient Listeners]
        K[Memory Management] --> L[Cleanup Strategies]
    end
    
    style A fill:#e8f5e8
    style G fill:#e1f5fe
    style I fill:#f3e5f5
```

**Optimization Strategies:**
- Use function components (Svelte 5) for better performance
- Implement proper cleanup in component destruction
- Leverage type safety to prevent runtime errors
- Utilize snippet system for reusable template logic

## Error Handling

### Component Error Boundaries

```mermaid
sequenceDiagram
    participant Parent as Parent Component
    participant Child as Child Component
    participant Error as Error Handler
    participant Recovery as Recovery System
    
    Parent->>Child: Render child
    Child->>Child: Runtime error occurs
    Child->>Error: Error caught
    Error->>Recovery: Attempt recovery
    Recovery->>Parent: Fallback rendering
    Parent->>Parent: Display error state
```

## Best Practices

### Component Design Principles

1. **Type Safety**: Always use proper TypeScript types for props, events, and exports
2. **Single Responsibility**: Keep components focused on a single concern
3. **Composition**: Use snippets and slots for flexible component composition
4. **Performance**: Prefer function components over class components
5. **Migration**: Use compatibility helpers during gradual migration from Svelte 4 to 5

### Common Patterns

```typescript
// Generic component with constraints
interface ButtonProps {
    variant: 'primary' | 'secondary';
    size: 'small' | 'medium' | 'large';
    disabled?: boolean;
}

const Button: Component<ButtonProps> = (internals, props) => {
    // Component implementation
};

// Component with complex event handling
interface FormEvents {
    submit: { data: FormData };
    cancel: void;
    validate: { field: string; valid: boolean };
}

const Form: Component<FormProps, FormExports> = (internals, props) => {
    const dispatch: EventDispatcher<FormEvents> = createEventDispatcher();
    // Implementation
};
```

The component_system module serves as the foundation for all Svelte component interactions, providing a robust type system and flexible architecture that supports both legacy and modern component patterns while maintaining excellent developer experience and runtime performance.