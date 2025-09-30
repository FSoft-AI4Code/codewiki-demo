# JNI Functions Module

The JNI Functions module provides a comprehensive framework for implementing custom SQL functions in Java that can be registered and executed within SQLite databases through the JNI (Java Native Interface) binding. This module enables developers to extend SQLite's functionality by creating scalar, aggregate, and window functions in Java.

## Architecture Overview

The JNI Functions module is built around a hierarchical interface design that provides type-safe abstractions for different categories of SQL functions while managing the complex lifecycle and state requirements of user-defined functions (UDFs).

```mermaid
graph TB
    subgraph "JNI Functions Module"
        SQLFunction[SQLFunction Interface]
        ScalarFunction[ScalarFunction]
        AggregateFunction[AggregateFunction&lt;T&gt;]
        WindowFunction[WindowFunction&lt;T&gt;]
        PrepareMultiCallback[PrepareMultiCallback]
        
        SQLFunction --> ScalarFunction
        SQLFunction --> AggregateFunction
        AggregateFunction --> WindowFunction
        
        subgraph "State Management"
            PerContextState[PerContextState&lt;T&gt;]
            ValueHolder[ValueHolder&lt;T&gt;]
        end
        
        subgraph "Utility Classes"
            StepAll[PrepareMultiCallback.StepAll]
            Finalize[PrepareMultiCallback.Finalize]
        end
        
        AggregateFunction --> PerContextState
        PerContextState --> ValueHolder
        PrepareMultiCallback --> StepAll
        PrepareMultiCallback --> Finalize
    end
    
    subgraph "Dependencies"
        sqlite3_context[sqlite3_context]
        sqlite3_value[sqlite3_value]
        CApi[CApi]
    end
    
    ScalarFunction --> sqlite3_context
    ScalarFunction --> sqlite3_value
    AggregateFunction --> sqlite3_context
    WindowFunction --> sqlite3_context
    PrepareMultiCallback --> CApi
```

## Core Components

### SQLFunction Interface

The `SQLFunction` interface serves as the base marker interface for all user-defined functions. It provides a common type hierarchy that the JNI layer can recognize and process.

**Purpose:**
- Establishes a common contract for all UDF implementations
- Enables type-safe registration with SQLite through the JNI binding
- Provides a foundation for the three specialized function types

### ScalarFunction

`ScalarFunction` implements scalar SQL functions that take input parameters and return a single result value.

**Key Features:**
- Abstract `xFunc()` method for function implementation
- Optional `xDestroy()` method for cleanup operations
- Direct parameter access through `sqlite3_value[]`
- Result setting through `sqlite3_context`

**Lifecycle:**
```mermaid
sequenceDiagram
    participant SQLite
    participant JNI
    participant ScalarFunction
    
    SQLite->>JNI: Function call
    JNI->>ScalarFunction: xFunc(context, args)
    ScalarFunction->>ScalarFunction: Process arguments
    ScalarFunction->>JNI: Set result via context
    JNI->>SQLite: Return result
    
    Note over SQLite,ScalarFunction: On function destruction
    SQLite->>JNI: Cleanup request
    JNI->>ScalarFunction: xDestroy()
```

### AggregateFunction<T>

`AggregateFunction<T>` provides the foundation for aggregate functions that accumulate values across multiple rows and produce a single result.

**Key Components:**
- **Generic Type Parameter T**: Defines the accumulator state type
- **State Management**: Built-in `PerContextState<T>` for managing per-invocation state
- **Lifecycle Methods**: `xStep()`, `xFinal()`, and optional `xDestroy()`

**State Management Architecture:**
```mermaid
graph LR
    subgraph "Multiple Function Calls"
        Call1["SELECT AGG(A)"]
        Call2["SELECT AGG(B)"]
    end
    
    subgraph "PerContextState Management"
        Map["HashMap&lt;Long, ValueHolder&lt;T&gt;&gt;"]
        Context1["Context Key 1"]
        Context2["Context Key 2"]
        State1["Accumulator State 1"]
        State2["Accumulator State 2"]
    end
    
    Call1 --> Context1
    Call2 --> Context2
    Context1 --> Map
    Context2 --> Map
    Map --> State1
    Map --> State2
```

**Aggregate Function Lifecycle:**
```mermaid
sequenceDiagram
    participant SQLite
    participant JNI
    participant AggregateFunction
    participant PerContextState
    
    loop For each row
        SQLite->>JNI: xStep call
        JNI->>AggregateFunction: xStep(context, args)
        AggregateFunction->>PerContextState: getAggregateState()
        PerContextState->>AggregateFunction: Return ValueHolder
        AggregateFunction->>AggregateFunction: Update accumulator
    end
    
    SQLite->>JNI: xFinal call
    JNI->>AggregateFunction: xFinal(context)
    AggregateFunction->>PerContextState: takeAggregateState()
    PerContextState->>AggregateFunction: Return final state
    AggregateFunction->>JNI: Set final result
```

### WindowFunction<T>

`WindowFunction<T>` extends `AggregateFunction<T>` to support SQL window functions with additional `xInverse()` and `xValue()` methods for sliding window operations.

**Extended Capabilities:**
- **xInverse()**: Removes values from the window frame
- **xValue()**: Returns current window result without finalization
- **Sliding Window Support**: Efficient frame-based calculations

**Window Function Processing:**
```mermaid
sequenceDiagram
    participant SQLite
    participant JNI
    participant WindowFunction
    
    Note over SQLite,WindowFunction: Window frame initialization
    loop For each row entering frame
        SQLite->>JNI: xStep call
        JNI->>WindowFunction: xStep(context, args)
    end
    
    loop For each row leaving frame
        SQLite->>JNI: xInverse call
        JNI->>WindowFunction: xInverse(context, args)
    end
    
    SQLite->>JNI: xValue call
    JNI->>WindowFunction: xValue(context)
    WindowFunction->>JNI: Return current result
```

### PrepareMultiCallback

`PrepareMultiCallback` provides a framework for processing multiple SQL statements from a single input string, commonly used for batch SQL execution.

**Built-in Implementations:**
- **StepAll**: Executes statements completely, ignoring results
- **Finalize**: Wrapper that ensures statement cleanup

**Multi-Statement Processing Flow:**
```mermaid
graph TD
    Input["SQL Input String"] --> Parse["sqlite3_prepare_multi"]
    Parse --> Stmt1["Statement 1"]
    Parse --> Stmt2["Statement 2"]
    Parse --> StmtN["Statement N"]
    
    Stmt1 --> Callback1["callback.call(stmt1)"]
    Stmt2 --> Callback2["callback.call(stmt2)"]
    StmtN --> CallbackN["callback.call(stmtN)"]
    
    Callback1 --> Result1["Process/Finalize"]
    Callback2 --> Result2["Process/Finalize"]
    CallbackN --> ResultN["Process/Finalize"]
```

## State Management System

### PerContextState<T>

The `PerContextState<T>` class provides sophisticated state management for aggregate and window functions, handling the complex mapping between SQLite execution contexts and Java object state.

**Key Features:**
- **Context Mapping**: Maps `sqlite3_context` aggregate contexts to Java objects
- **Lifecycle Management**: Automatic cleanup of state mappings
- **Type Safety**: Generic type parameter ensures type-safe state handling
- **Concurrent Access**: Thread-safe state management

**State Lifecycle:**
```mermaid
stateDiagram-v2
    [*] --> Uninitialized
    Uninitialized --> Initialized: getAggregateState(context, initialValue)
    Initialized --> Updated: getAggregateState(context, ignored)
    Updated --> Updated: Multiple xStep calls
    Updated --> Finalized: takeAggregateState(context)
    Finalized --> [*]
    
    note right of Initialized: ValueHolder<T> created with initial value
    note right of Updated: Same ValueHolder<T> returned
    note right of Finalized: State removed from map
```

### ValueHolder<T>

`ValueHolder<T>` provides a simple container for mutable state that can be safely passed between method calls while maintaining reference semantics.

## Integration with Core Systems

### JNI CAPI Integration

The JNI Functions module integrates deeply with the [jni_capi](jni_capi.md) module for core SQLite operations:

```mermaid
graph LR
    subgraph "JNI Functions"
        UDF[User-Defined Functions]
    end
    
    subgraph "JNI CAPI"
        sqlite3_create_function[sqlite3_create_function]
        sqlite3_context[sqlite3_context]
        sqlite3_value[sqlite3_value]
        CApi[CApi]
    end
    
    UDF --> sqlite3_create_function
    UDF --> sqlite3_context
    UDF --> sqlite3_value
    UDF --> CApi
```

### Callback System Integration

The module leverages the [jni_callbacks](jni_callbacks.md) infrastructure for event-driven operations and lifecycle management.

## Function Registration and Execution

### Registration Process

```mermaid
sequenceDiagram
    participant App[Application]
    participant CApi[CApi]
    participant SQLite[SQLite Engine]
    participant JNI[JNI Layer]
    
    App->>CApi: sqlite3_create_function(db, name, nArgs, flags, function)
    CApi->>JNI: Register function with native layer
    JNI->>SQLite: sqlite3_create_function_v2()
    SQLite->>JNI: Function registered
    JNI->>CApi: Registration complete
    CApi->>App: Return result code
```

### Execution Flow

```mermaid
sequenceDiagram
    participant SQL[SQL Query]
    participant SQLite[SQLite Engine]
    participant JNI[JNI Layer]
    participant Function[Java Function]
    
    SQL->>SQLite: SELECT custom_func(column)
    SQLite->>JNI: Call registered function
    JNI->>Function: Invoke appropriate method
    Function->>Function: Process arguments
    Function->>JNI: Set result
    JNI->>SQLite: Return result
    SQLite->>SQL: Query result
```

## Error Handling and Exception Management

The module provides comprehensive error handling that bridges Java exceptions with SQLite's C-style error reporting:

```mermaid
graph TD
    JavaException["Java Exception"] --> JNILayer["JNI Layer"]
    JNILayer --> SQLiteError["sqlite3_result_error"]
    SQLiteError --> SQLiteEngine["SQLite Engine"]
    SQLiteEngine --> ErrorCode["Error Code Return"]
    
    JavaException --> ExceptionToString["Exception.toString()"]
    ExceptionToString --> ErrorMessage["Error Message"]
    ErrorMessage --> SQLiteError
```

## Performance Considerations

### State Management Optimization

- **Lazy Initialization**: State objects created only when needed
- **Efficient Mapping**: HashMap-based context-to-state mapping
- **Memory Management**: Automatic cleanup prevents memory leaks

### JNI Overhead Mitigation

- **Batch Operations**: PrepareMultiCallback reduces JNI crossing overhead
- **Direct Memory Access**: Efficient parameter and result handling
- **Minimal Object Creation**: Reuse of context and value objects

## Usage Examples

### Scalar Function Implementation

```java
public class UpperCaseFunction extends ScalarFunction {
    @Override
    public void xFunc(sqlite3_context cx, sqlite3_value[] args) {
        if (args.length != 1) {
            sqlite3_result_error(cx, "upper() requires exactly 1 argument");
            return;
        }
        
        String input = sqlite3_value_text16(args[0]);
        if (input != null) {
            sqlite3_result_text(cx, input.toUpperCase());
        } else {
            sqlite3_result_null(cx);
        }
    }
}
```

### Aggregate Function Implementation

```java
public class SumFunction extends AggregateFunction<Double> {
    @Override
    public void xStep(sqlite3_context cx, sqlite3_value[] args) {
        ValueHolder<Double> state = getAggregateState(cx, 0.0);
        if (args.length > 0) {
            state.value += sqlite3_value_double(args[0]);
        }
    }
    
    @Override
    public void xFinal(sqlite3_context cx) {
        Double sum = takeAggregateState(cx);
        sqlite3_result_double(cx, sum != null ? sum : 0.0);
    }
}
```

## Security Considerations

- **Input Validation**: All function implementations should validate input parameters
- **Resource Management**: Proper cleanup through xDestroy() methods
- **Exception Handling**: Robust error handling prevents crashes
- **State Isolation**: Per-context state management prevents data leakage

## Future Enhancements

- **Performance Profiling**: Built-in performance monitoring for UDFs
- **Advanced State Management**: Support for more complex state patterns
- **Debugging Support**: Enhanced debugging capabilities for function development
- **Documentation Generation**: Automatic documentation from function annotations

The JNI Functions module represents a sophisticated bridge between Java's object-oriented programming model and SQLite's procedural function interface, providing developers with powerful tools for extending database functionality while maintaining performance and reliability.